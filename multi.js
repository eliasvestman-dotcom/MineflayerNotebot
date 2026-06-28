import fs from "fs";
import { read as readNBS } from "@nbsjs/core";
import chalk from "chalk";
import mineflayer from "mineflayer";
import parseSentence from "minimist-string";
import blockMapper from "./block_mapper.js";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const config = JSON.parse(fs.readFileSync("./config.json", "utf-8"));
const instruments = JSON.parse(fs.readFileSync("./instruments_map.json", "utf-8"));

export class NoteBot {
  constructor(username) {
    this.options = {
      username: username,
      host: config.bot.host || "localhost",
      port: config.bot.port || 25565,
      version: config.bot.version || "1.20.1",
    };
    this.bot = mineflayer.createBot(this.options);
    this.availableNoteblocks = {};
    this.currentSong = null;

    this.bot.on("login", () => {
      this.respond(this.options.username + " ONLINE");
    });

    this.bot.on("kicked", (reason) => {
      this.respond(`I got kicked for ${reason}`, 2);
      this.respond(`Rage Quitting`, 2);
    });

    this.bot.on("chat", (username, message) => {
      if (username === this.options.username) {
        this.respond(message);
      }
    });

    this.bot.on("whisper", (username, message) => {
      if (config.commands_perms.includes(username)) {
        this.handle(message, username);
      }
    });
  }

  respond(message, level = 0) {
    let mes = message;
    switch (level) {
      case -1:
        mes = chalk.green("[DEBUG] " + message);
        break;
      case 0:
        mes = chalk.blue("[INFO]  " + message);
        break;
      case 1:
        mes = chalk.yellow("[WARN]  " + message);
        break;
      case 2:
        mes = chalk.red("[ERROR] " + message);
        break;
    }
    console.log(mes);
  }

  handle(command, username) {
    const cmd = parseSentence(command.substring(1));
    delete cmd["_"];

    const action = Object.keys(cmd)[0];

    switch (action) {
      case "detect":
        this.detect();
        break;
      case "play":
        this.respond(`Playing ${cmd.play}`);
        if (!this.isValidFile(cmd.play)) {
          this.respond(`${cmd.play} is not a valid file!`, 1);
        } else {
          const songFile = fs.readFileSync("songs/" + cmd.play);
          const song = readNBS(new Uint8Array(songFile));
          this.play(song, cmd.speed || 100);
        }
        break;
      case "setup":
        if (!this.isValidFile(cmd.setup)) {
          this.respond(`${cmd.setup} is not a valid file!`, 1);
        } else {
          const songFileReq = fs.readFileSync("songs/" + cmd.setup);
          const songReq = readNBS(new Uint8Array(songFileReq));
          this.prettyRequirements(songReq);
        }
        break;
      case "tune":
        this.respond(`Tuning to ${cmd.tune}`);
        if (!this.isValidFile(cmd.tune)) {
          this.respond(`${cmd.tune} is not a valid file!`, 1);
        } else {
          const songFileTune = fs.readFileSync("songs/" + cmd.tune);
          const songTune = readNBS(new Uint8Array(songFileTune));
          this.tune(songTune);
        }
        break;
      case "stop":
        this.respond(`Stopping`);
        clearInterval(this.currentSong);
        break;
    }
  }

  stop() {
    clearInterval(this.currentSong);
  }

  isValidFile(name) {
    try {
      return fs.existsSync("songs/" + name);
    } catch (err) {
      return false;
    }
  }

  tune(songBuffer) {
    const req = this.findRequirements(songBuffer);
    const blocks = this.detect_noteblocks();

    Object.keys(req).forEach((instrument_id) => {
      const notes = req[instrument_id];
      notes.forEach((pitch) => {
        const availableBlocks = blocks[instrument_id];
        if (availableBlocks) {
          const blockToTune = availableBlocks.find((block) => !block.isTuned);

          if (blockToTune) {
            this.tuneNoteblock(blockToTune, pitch);
            blockToTune.isTuned = true;
          } else {
            this.respond(
              `No available block for instrument ${instrument_id} and pitch ${pitch}`,
              1
            );
          }
        } else {
          this.respond(
            `No available block for instrument ${instrument_id} and pitch ${pitch}`,
            1
          );
        }
      });
    });
  }

  tuneNoteblock(block, pitch) {
    if (block === null) {
      return;
    }
    if (block.pitch === pitch) {
      return;
    }

    let play_times = 0;
    if (pitch - block.pitch < 0) {
      play_times = 25 - (block.pitch - pitch);
    } else {
      play_times = pitch - block.pitch;
    }

    for (let i = 0; i < play_times; i++) {
      setTimeout(() => {
        this.bot._client.write("block_place", {
          location: block.position,
          direction: 1,
          hand: 0,
          cursorX: 0.5,
          cursorY: 0.5,
          cursorZ: 0.5,
        });
      }, config.settings.tune_speed * i);
    }

    block.pitch = pitch;
  }

  isTunedAndReady(songBuffer) {
    let goodToGo = true;

    const req = this.findNeededRequirements(songBuffer);
    Object.keys(req).forEach((instrument_id) => {
      if (req[instrument_id].length > 0) goodToGo = false;
    });

    return goodToGo;
  }

  play(songBuffer, speed) {
    if (this.currentSong) {
      clearInterval(this.currentSong);
    }

    if (this.isTunedAndReady(songBuffer)) {
      this.detect();
      let tick = 0;
      this.currentSong = setInterval(() => {
        this.runJob(songBuffer, tick);
        tick += 1;
      }, speed);
    } else {
      this.tune(songBuffer);
      setTimeout(() => {
        if (this.isTunedAndReady(songBuffer)) {
          this.play(songBuffer, speed);
        } else {
          this.prettyRequirements(songBuffer);
        }
      }, 3000);
    }
  }

  async runJob(songBuffer, tick) {
    for (let currentLayer = 0; currentLayer < songBuffer.layers.length; currentLayer++) {
      const layer = songBuffer.layers[currentLayer];
      const note = layer.notes[tick];

      if (note) {
        const pitch = note.key - 33;
        this.play_note(note.instrument, pitch);
      }
    }
  }

  findRequirements(songBuffer) {
    const needed = {};

    for (let currentLayer = 0; currentLayer < songBuffer.layers.length; currentLayer++) {
      const layer = songBuffer.layers[currentLayer];
      layer.notes.forEach((note) => {
        if (note) {
          const pitch = (note.key - 33).toString();

          if (!(note.instrument in needed)) {
            needed[note.instrument] = [];
          }

          if (!needed[note.instrument].includes(pitch)) {
            needed[note.instrument].push(pitch);
          }
        }
      });
    }

    return needed;
  }

  findNeededRequirements(songBuffer) {
    const needed = {};
    const myNoteblocks = {};

    const noteblocks = blockMapper.mapnoteblocks(this.bot);
    noteblocks.forEach((item) => {
      const instrument_id = item.instrumentid;
      const pitch = item.pitch.toString();

      if (!(instrument_id in myNoteblocks)) {
        myNoteblocks[instrument_id] = [];
      }

      myNoteblocks[instrument_id].push(pitch);
    });

    for (let currentLayer = 0; currentLayer < songBuffer.layers.length; currentLayer++) {
      const layer = songBuffer.layers[currentLayer];
      layer.notes.forEach((note) => {
        if (note) {
          const pitch = (note.key - 33).toString();

          if (!(note.instrument in needed)) {
            needed[note.instrument] = [];
          }

          if (!(note.instrument in myNoteblocks)) {
            myNoteblocks[note.instrument] = [];
          }

          if (
            !needed[note.instrument].includes(pitch) &&
            !myNoteblocks[note.instrument].includes(pitch)
          ) {
            needed[note.instrument].push(pitch);
          }
        }
      });
    }

    return needed;
  }

  prettyRequirements(songBuffer) {
    const needed = {};
    const myNoteblocks = {};

    const noteblocks = blockMapper.mapnoteblocks(this.bot);
    noteblocks.forEach((item) => {
      const instrument_id = item.instrumentid;
      const pitch = item.pitch.toString();

      if (!(instrument_id in myNoteblocks)) {
        myNoteblocks[instrument_id] = [];
      }

      myNoteblocks[instrument_id].push(pitch);
    });

    for (let currentLayer = 0; currentLayer < songBuffer.layers.length; currentLayer++) {
      const layer = songBuffer.layers[currentLayer];
      layer.notes.forEach((note) => {
        if (note) {
          const pitch = (note.key - 33).toString();

          if (!(note.instrument in needed)) {
            needed[note.instrument] = [];
          }

          if (!(note.instrument in myNoteblocks)) {
            myNoteblocks[note.instrument] = [];
          }

          if (
            !needed[note.instrument].includes(pitch) &&
            !myNoteblocks[note.instrument].includes(pitch)
          ) {
            needed[note.instrument].push(pitch);
          }
        }
      });
    }

    let list = "Add the following note blocks:\n";
    Object.keys(needed).forEach((instrument) => {
      list += `${instruments.blocks[instrument].toUpperCase()} x${this.twoNum(
        needed[instrument.toString()].length
      )} \n`;
    });

    this.respond(list, 1);
  }

  twoNum(num) {
    return num > 9 ? num.toString() : `0${num.toString()}`;
  }

  detect_noteblocks() {
    const myNoteblocks = {};
    const noteblocks = blockMapper.mapnoteblocks(this.bot);

    noteblocks.forEach((item) => {
      const instrument_id = item.instrumentid;
      const pitch = item.pitch;
      const position = item.position;

      if (!(instrument_id in myNoteblocks)) {
        myNoteblocks[instrument_id] = [];
      }

      const info = { position: position, pitch: pitch };
      myNoteblocks[instrument_id].push(info);
    });

    return myNoteblocks;
  }

  detect() {
    this.respond(`Detecting Nearby Noteblocks`);
    this.availableNoteblocks = this.detect_noteblocks();

    let numDetected = 0;
    const values = Object.keys(this.availableNoteblocks).map(
      (key) => this.availableNoteblocks[key]
    );
    values.forEach((instrument) => {
      numDetected += instrument.length;
    });

    this.respond(`Found ${numDetected}!`);
  }

  play_note(instrument_id, pitch) {
    if (instrument_id in this.availableNoteblocks) {
      let target = null;
      const blocks = this.availableNoteblocks[instrument_id.toString()];
      blocks.forEach((block) => {
        if (block.pitch.toString() === pitch.toString()) {
          target = block;
        }
      });
      if (target !== null) {
        this.play_note_by_block(target);
      } else {
        this.respond(
          `Pitch ${pitch} not available for instrument ${instrument_id}. (${instruments.blocks[instrument_id.toString()]})`,
          1
        );
        clearInterval(this.currentSong);
      }
      return;
    } else {
      this.respond(
        `Instrument ${instrument_id} not available. (${instruments.blocks[instrument_id.toString()]})`,
        1
      );
      return;
    }
  }

  play_note_by_block(block) {
    const position = block.position;
    this.bot.lookAt(position, true);

    this.bot._client.write("block_dig", {
      status: 0,
      location: position,
      face: 1,
    });
    this.bot._client.write("block_dig", {
      status: 1,
      location: position,
      face: 1,
    });
  }
}
