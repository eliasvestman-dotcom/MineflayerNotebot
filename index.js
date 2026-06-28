import fs from "fs";
import { read as readNBS } from "@nbsjs/core";
import chalk from "chalk";
import mineflayer from "mineflayer";
import parseSentence from "minimist-string";
import { createRequire } from "module";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { NoteBot } from "./multi.js";

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const config = JSON.parse(fs.readFileSync("./config.json", "utf-8"));

const numWorkers = 4;
let currentSong = null;

const options = {
  username: config.bot.username || "notebot",
  host: config.bot.host || "localhost",
  port: config.bot.port || 25565,
  version: config.bot.version || "1.20.1",
};

const bot = mineflayer.createBot(options);
const workers = [];

bot.on("login", () => {
  bot.chat(`Mineflayer Notebot by @meeplabsdev on github (Updated v2.0)`);

  for (let i = 1; i <= numWorkers; i++) {
    const username = `notebot_worker${twoNum(i)}`;
    workers.push(new NoteBot(username));
  }
});

bot.on("kicked", (reason) => {
  respond(`I got kicked for ${reason}`, 2);
  respond(`Rage Quitting`, 2);
  process.exit();
});

bot.on("chat", (username, message) => {
  if (username === options.username) {
    respond(message);
  }
});

bot.on("whisper", (username, message) => {
  if (config.commands_perms.includes(username)) {
    handle(message, username);
  }
});

function respond(message, level = 0) {
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
  if (level >= 1) {
    beep();
  }
}

function beep() {
  // Platform-specific beep implementation
  if (process.platform === "win32") {
    require("child_process").exec('powershell.exe [console]::beep(500,600)');
  } else if (process.platform === "darwin") {
    require("child_process").exec("printf '\\\\a'");
  } else {
    require("child_process").exec("echo -n $'\\\\a'");
  }
}

function handle(command, username) {
  if (!command.startsWith(config.settings.command_prefix + options.username))
    return false;
  const cmd = parseSentence(command.substring(1));
  delete cmd["_"];

  const action = Object.keys(cmd)[0];

  switch (action) {
    case "detect":
      workers.forEach((worker) => {
        setTimeout(() => {
          worker.detect();
        }, 100);
      });
      break;
    case "play":
      respond(`Playing ${cmd.play}`);
      if (!isValidFile(cmd.play)) {
        respond(`${cmd.play} is not a valid file!`, 1);
      } else {
        const songFile = fs.readFileSync("songs/" + cmd.play);
        const song = readNBS(new Uint8Array(songFile));
        play(song, cmd.speed || 100);
      }
      break;
    case "setup":
      if (!isValidFile(cmd.setup)) {
        respond(`${cmd.setup} is not a valid file!`, 1);
      } else {
        const songFileReq = fs.readFileSync("songs/" + cmd.setup);
        const songReq = readNBS(new Uint8Array(songFileReq));
        workers.forEach((worker) => {
          setTimeout(() => {
            worker.handle(command, username);
          }, 500);
        });
      }
      break;
    case "tune":
      respond(`Tuning to ${cmd.tune}`);
      if (!isValidFile(cmd.tune)) {
        respond(`${cmd.tune} is not a valid file!`, 1);
      } else {
        const songFileTune = fs.readFileSync("songs/" + cmd.tune);
        const songTune = readNBS(new Uint8Array(songFileTune));
        workers.forEach((worker) => {
          setTimeout(() => {
            worker.handle(command, username);
          }, 500);
        });
      }
      break;
    case "stop":
      respond(`Stopping`);
      stop();
      break;
  }
}

function isValidFile(name) {
  try {
    return fs.existsSync("songs/" + name);
  } catch (err) {
    return false;
  }
}

function stop() {
  clearInterval(currentSong);
}

function play(songBuffer, speed) {
  stop();

  let ready = true;
  workers.forEach((worker) => {
    if (!worker.isTunedAndReady(songBuffer)) ready = false;
  });

  if (ready) {
    workers.forEach((worker) => {
      worker.detect();
    });

    let tick = 0;
    currentSong = setInterval(() => {
      runJob(songBuffer, tick);
      tick += 1;
    }, speed);
  } else {
    workers.forEach((worker) => {
      worker.tune(songBuffer);
      respond("Worker " + worker.options.username + ":", 2);
      worker.prettyRequirements(songBuffer);
    });
  }
}

async function runJob(songBuffer, tick) {
  for (let currentLayer = 0; currentLayer < songBuffer.layers.length; currentLayer++) {
    const layer = songBuffer.layers[currentLayer];
    const note = layer.notes[tick];

    if (note) {
      const pitch = note.key - 33;
      workers.forEach((worker) => {
        worker.play_note(note.instrument, pitch);
      });
    }
  }
}

function twoNum(num) {
  return num > 9 ? num.toString() : `0${num.toString()}`;
}

export { bot, currentSong };
