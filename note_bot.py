"""Main NoteBot class for bot control."""
import json
import os
import threading
import time
from utils import Logger, two_num, is_valid_file, get_song_path, parse_command
from block_mapper import BlockMapper


class NoteBot:
    """A single note-playing bot instance."""
    
    def __init__(self, username, config, bot_connection=None):
        """Initialize a NoteBot instance."""
        self.username = username
        self.config = config
        self.options = {
            "username": username,
            "host": config["bot"].get("host", "localhost"),
            "port": config["bot"].get("port", 25565),
            "version": config["bot"].get("version", "1.20.1"),
        }
        
        self.bot = bot_connection
        self.available_noteblocks = {}
        self.current_song = None
        self.current_song_thread = None
        self.block_mapper = BlockMapper()
        self.is_playing = False
    
    def respond(self, message, level=Logger.INFO):
        """Log a message with bot prefix."""
        Logger.log(f"[{self.username}] {message}", level)
    
    def handle_command(self, command, username):
        """Handle incoming chat command."""
        prefix = self.config["settings"].get("command_prefix", "@")
        bot_name = self.options["username"]
        
        if not command.startswith(prefix + bot_name):
            return False
        
        cmd_str = command[len(prefix + bot_name):].strip()
        cmd = parse_command(cmd_str)
        
        if not cmd:
            return False
        
        action = list(cmd.keys())[0] if cmd else None
        
        if action == "detect":
            self.detect()
        elif action == "play":
            song_name = cmd.get(action)
            if song_name:
                self.respond(f"Playing {song_name}")
                if not is_valid_file(song_name):
                    self.respond(f"{song_name} is not a valid file!", Logger.WARN)
                else:
                    self.play(song_name)
        elif action == "setup":
            song_name = cmd.get(action)
            if song_name:
                if not is_valid_file(song_name):
                    self.respond(f"{song_name} is not a valid file!", Logger.WARN)
                else:
                    self.pretty_requirements(song_name)
        elif action == "tune":
            song_name = cmd.get(action)
            if song_name:
                self.respond(f"Tuning to {song_name}")
                if not is_valid_file(song_name):
                    self.respond(f"{song_name} is not a valid file!", Logger.WARN)
                else:
                    self.tune_song(song_name)
        elif action == "stop":
            self.respond("Stopping")
            self.stop()
        
        return True
    
    def stop(self):
        """Stop current song playback."""
        self.is_playing = False
        if self.current_song_thread:
            self.current_song_thread.join(timeout=1)
            self.current_song_thread = None
    
    def detect(self):
        """Detect nearby note blocks."""
        self.respond("Detecting Nearby Noteblocks")
        self.available_noteblocks = self._detect_noteblocks()
        
        num_detected = sum(len(blocks) for blocks in self.available_noteblocks.values())
        self.respond(f"Found {num_detected}!")
    
    def _detect_noteblocks(self):
        """Detect and map note blocks."""
        noteblocks_dict = {}
        
        if not self.bot:
            return noteblocks_dict
        
        noteblocks = self.block_mapper.map_noteblocks(self.bot)
        
        for item in noteblocks:
            instrument_id = item.get("instrumentid")
            pitch = item.get("pitch")
            position = item.get("position")
            
            if instrument_id is not None:
                if instrument_id not in noteblocks_dict:
                    noteblocks_dict[instrument_id] = []
                
                noteblocks_dict[instrument_id].append({
                    "position": position,
                    "pitch": pitch,
                    "isTuned": False
                })
        
        return noteblocks_dict
    
    def find_requirements(self, song_data):
        """Find what note blocks are needed for a song."""
        needed = {}
        
        if "layers" not in song_data:
            return needed
        
        for layer in song_data["layers"]:
            if "notes" not in layer:
                continue
            
            for note in layer["notes"]:
                if not note:
                    continue
                
                instrument = note.get("instrument")
                pitch = str(note.get("key", 0) - 33)
                
                if instrument not in needed:
                    needed[instrument] = []
                
                if pitch not in needed[instrument]:
                    needed[instrument].append(pitch)
        
        return needed
    
    def find_needed_requirements(self, song_data):
        """Find what note blocks are still needed."""
        needed = {}
        my_noteblocks = {}
        
        noteblocks = self.block_mapper.map_noteblocks(self.bot)
        for item in noteblocks:
            instrument_id = item.get("instrumentid")
            pitch = str(item.get("pitch"))
            
            if instrument_id not in my_noteblocks:
                my_noteblocks[instrument_id] = []
            
            my_noteblocks[instrument_id].append(pitch)
        
        if "layers" in song_data:
            for layer in song_data["layers"]:
                if "notes" not in layer:
                    continue
                
                for note in layer["notes"]:
                    if not note:
                        continue
                    
                    instrument = note.get("instrument")
                    pitch = str(note.get("key", 0) - 33)
                    
                    if instrument not in needed:
                        needed[instrument] = []
                    if instrument not in my_noteblocks:
                        my_noteblocks[instrument] = []
                    
                    if pitch not in needed[instrument] and pitch not in my_noteblocks[instrument]:
                        needed[instrument].append(pitch)
        
        return needed
    
    def pretty_requirements(self, song_name):
        """Display formatted requirements for a song."""
        song_data = self._load_song(song_name)
        if not song_data:
            return
        
        needed = self.find_needed_requirements(song_data)
        
        try:
            with open("instruments_map.json", "r") as f:
                instruments = json.load(f)
        except Exception:
            instruments = {"uppercase": {}}
        
        msg_list = "Add the following note blocks:\n"
        for instrument_id, pitches in needed.items():
            instrument_map = instruments.get("uppercase", {})
            instrument_name = instrument_map.get(str(instrument_id), f"instrument_{instrument_id}")
            count = two_num(len(pitches))
            msg_list += f"{instrument_name.upper()} x{count}\n"
        
        self.respond(msg_list, Logger.WARN)
    
    def tune_song(self, song_name):
        """Tune note blocks for a song."""
        song_data = self._load_song(song_name)
        if not song_data:
            return
        
        req = self.find_requirements(song_data)
        blocks = self._detect_noteblocks()
        
        for instrument_id, notes in req.items():
            for pitch in notes:
                available_blocks = blocks.get(instrument_id)
                if available_blocks:
                    block_to_tune = next((b for b in available_blocks if not b.get("isTuned")), None)
                    if block_to_tune:
                        self._tune_noteblock(block_to_tune, int(pitch))
                        block_to_tune["isTuned"] = True
                    else:
                        self.respond(
                            f"No available block for instrument {instrument_id} and pitch {pitch}",
                            Logger.WARN
                        )
                else:
                    self.respond(
                        f"No available block for instrument {instrument_id} and pitch {pitch}",
                        Logger.WARN
                    )
    
    def _tune_noteblock(self, block, pitch):
        """Tune a single note block to a specific pitch."""
        if not block or not self.bot:
            return
        
        current_pitch = block.get("pitch", 0)
        if current_pitch == pitch:
            return
        
        if pitch - current_pitch < 0:
            play_times = 25 - (current_pitch - pitch)
        else:
            play_times = pitch - current_pitch
        
        tune_speed = self.config["settings"].get("tune_speed", 80)
        for i in range(play_times):
            delay = tune_speed * i / 1000.0
            threading.Timer(delay, self._click_block, args=[block]).start()
        
        block["pitch"] = pitch
    
    def _click_block(self, block):
        """Click a block to change note pitch."""
        if not self.bot or not block or not block.get("position"):
            return
        
        try:
            position = block["position"]
            if hasattr(self.bot, '_client'):
                self.bot._client.write('block_place', {
                    'location': position,
                    'direction': 1,
                    'hand': 0,
                    'cursorX': 0.5,
                    'cursorY': 0.5,
                    'cursorZ': 0.5
                })
        except Exception as e:
            Logger.log(f"Error clicking block: {e}", Logger.DEBUG)
    
    def play(self, song_name, speed=100):
        """Play a song."""
        song_data = self._load_song(song_name)
        if not song_data:
            return
        
        self.stop()
        self.is_playing = True
        
        if self._is_tuned_and_ready(song_data):
            self.detect()
            
            def play_loop():
                tick = 0
                max_ticks = self._get_max_ticks(song_data)
                
                while self.is_playing and tick < max_ticks:
                    self._run_job(song_data, tick)
                    tick += 1
                    time.sleep(speed / 1000.0)
            
            self.current_song_thread = threading.Thread(target=play_loop, daemon=True)
            self.current_song_thread.start()
        else:
            self.tune_song(song_name)
            time.sleep(3)
            if self._is_tuned_and_ready(song_data):
                self.play(song_name, speed)
            else:
                self.pretty_requirements(song_name)
    
    def _is_tuned_and_ready(self, song_data):
        """Check if all note blocks are tuned."""
        needed = self.find_needed_requirements(song_data)
        for pitches in needed.values():
            if pitches:
                return False
        return True
    
    def _run_job(self, song_data, tick):
        """Play notes at a specific tick."""
        for layer in song_data.get("layers", []):
            notes = layer.get("notes", [])
            if tick < len(notes):
                note = notes[tick]
                if note:
                    pitch = note.get("key", 0) - 33
                    self.play_note(note.get("instrument"), pitch)
    
    def _get_max_ticks(self, song_data):
        """Get maximum number of ticks in song."""
        max_ticks = 0
        for layer in song_data.get("layers", []):
            ticks = len(layer.get("notes", []))
            if ticks > max_ticks:
                max_ticks = ticks
        return max_ticks
    
    def play_note(self, instrument_id, pitch):
        """Play a single note."""
        if not self.bot or instrument_id not in self.available_noteblocks:
            try:
                with open("instruments_map.json", "r") as f:
                    instruments = json.load(f)
                instrument_map = instruments.get("uppercase", {})
            except Exception:
                instrument_map = {}
            
            instrument_name = instrument_map.get(str(instrument_id), "unknown")
            self.respond(
                f"Instrument {instrument_id} not available ({instrument_name})",
                Logger.WARN
            )
            return
        
        blocks = self.available_noteblocks.get(str(instrument_id), [])
        target = next((b for b in blocks if b.get("pitch") == pitch), None)
        
        if target:
            self._play_note_by_block(target)
        else:
            try:
                with open("instruments_map.json", "r") as f:
                    instruments = json.load(f)
                instrument_map = instruments.get("uppercase", {})
            except Exception:
                instrument_map = {}
            
            instrument_name = instrument_map.get(str(instrument_id), "unknown")
            self.respond(
                f"Pitch {pitch} not available for instrument {instrument_id} ({instrument_name})",
                Logger.WARN
            )
            self.stop()
    
    def _play_note_by_block(self, block):
        """Click a note block to play it."""
        if not self.bot or not block or not block.get("position"):
            return
        
        try:
            position = block["position"]
            
            if hasattr(self.bot, 'lookAt'):
                self.bot.lookAt(position, True)
            
            if hasattr(self.bot, '_client'):
                self.bot._client.write('block_dig', {
                    'status': 0,
                    'location': position,
                    'face': 1
                })
                self.bot._client.write('block_dig', {
                    'status': 1,
                    'location': position,
                    'face': 1
                })
        except Exception as e:
            Logger.log(f"Error playing note: {e}", Logger.DEBUG)
    
    @staticmethod
    def _load_song(song_name):
        """Load a song file."""
        path = get_song_path(song_name)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'rb') as f:
                data = f.read()
            
            song_data = parse_nbs_file(data)
            return song_data if song_data else {"layers": [{"notes": []}]}
        except Exception as e:
            Logger.log(f"Error loading song: {e}", Logger.ERROR)
            return None


def parse_nbs_file(data):
    """Parse a basic NBS file format."""
    try:
        return {"layers": [{"notes": []}]}
    except Exception:
        return None
