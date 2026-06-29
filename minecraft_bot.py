"""Minecraft bot connection handler using mineflayer bridge."""
import json
import subprocess
import sys
import os
import time
import threading
from pathlib import Path
from utils import Logger


class MinecraftBot:
    """Wrapper for connecting to Minecraft via Node.js mineflayer bridge."""
    
    def __init__(self, config, command_handler):
        """Initialize bot connection.
        
        Args:
            config: Configuration dict with bot settings
            command_handler: Callback function for handling commands
        """
        self.config = config
        self.command_handler = command_handler
        self.process = None
        self.bot_data = {
            "entity": {"position": {"x": 0, "y": 0, "z": 0}},
            "noteblocks": []
        }
        self.is_running = False
        self.lock = threading.Lock()
        
    def connect(self):
        """Start the bot connection using Node.js bridge."""
        try:
            # Check if bridge exists
            if not os.path.exists("bot_bridge.js"):
                self._create_bridge()
            
            Logger.log("Attempting to connect to Minecraft server...", Logger.INFO)
            
            # Start bot bridge process
            self.process = subprocess.Popen(
                ["node", "bot_bridge.js"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.is_running = True
            
            # Start reader thread
            reader_thread = threading.Thread(target=self._read_output, daemon=True)
            reader_thread.start()
            
            time.sleep(2)  # Give server time to connect
            Logger.log("Bot connection initiated", Logger.INFO)
            return True
            
        except Exception as e:
            Logger.log(f"Failed to connect: {e}", Logger.ERROR)
            return False
    
    def disconnect(self):
        """Disconnect the bot."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                Logger.log(f"Error disconnecting: {e}", Logger.DEBUG)
    
    def _create_bridge(self):
        """Create minimal Node.js bridge for mineflayer communication."""
        bridge_code = '''const fs = require("fs");
const mineflayer = require("mineflayer");

const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));

const options = {
    username: config.bot.username || "notebot",
    host: config.bot.host || "localhost",
    port: config.bot.port || 25565,
    version: config.bot.version || "1.20.1"
};

const bot = mineflayer.createBot(options);

bot.on("login", () => {
    console.log("BOT_LOGIN:" + bot.username);
});

bot.on("kicked", (reason) => {
    console.log("BOT_KICKED:" + reason);
    process.exit(1);
});

bot.on("error", (err) => {
    console.log("BOT_ERROR:" + err.message);
});

bot.on("chat", (username, message) => {
    console.log("BOT_CHAT:" + username + ":" + message);
});

bot.on("whisper", (username, message) => {
    console.log("BOT_WHISPER:" + username + ":" + message);
});

// Keep process alive
setInterval(() => {}, 1000);
'''
        
        try:
            with open("bot_bridge.js", "w") as f:
                f.write(bridge_code)
            Logger.log("Created bot_bridge.js", Logger.DEBUG)
        except Exception as e:
            Logger.log(f"Error creating bridge: {e}", Logger.ERROR)
    
    def _read_output(self):
        """Read and process bot output."""
        try:
            while self.is_running and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                self._process_message(line)
                
        except Exception as e:
            Logger.log(f"Error reading output: {e}", Logger.DEBUG)
    
    def _process_message(self, message):
        """Process messages from bot bridge."""
        try:
            if message.startswith("BOT_LOGIN:"):
                username = message.replace("BOT_LOGIN:", "")
                Logger.log(f"Bot logged in: {username}", Logger.INFO)
                
            elif message.startswith("BOT_CHAT:"):
                parts = message.replace("BOT_CHAT:", "").split(":", 1)
                if len(parts) == 2:
                    username, chat = parts
                    Logger.log(f"[{username}] {chat}", Logger.INFO)
                    
            elif message.startswith("BOT_WHISPER:"):
                parts = message.replace("BOT_WHISPER:", "").split(":", 1)
                if len(parts) == 2:
                    username, cmd = parts
                    if self.command_handler:
                        self.command_handler(cmd, username)
                        
            elif message.startswith("BOT_ERROR:"):
                error = message.replace("BOT_ERROR:", "")
                Logger.log(f"Bot error: {error}", Logger.ERROR)
                
            elif message.startswith("BOT_KICKED:"):
                reason = message.replace("BOT_KICKED:", "")
                Logger.log(f"Bot kicked: {reason}", Logger.ERROR)
                self.is_running = False
                
        except Exception as e:
            Logger.log(f"Error processing message: {e}", Logger.DEBUG)
    
    def send_chat(self, message):
        """Send chat message via bot."""
        if self.process and self.is_running:
            try:
                self.process.stdin.write(f"CHAT:{message}\n")
                self.process.stdin.flush()
            except Exception as e:
                Logger.log(f"Error sending chat: {e}", Logger.DEBUG)
    
    def get_blocks_around(self):
        """Get blocks around bot (from detection)."""
        with self.lock:
            return self.bot_data.get("noteblocks", [])
    
    def set_blocks(self, blocks):
        """Update detected blocks."""
        with self.lock:
            self.bot_data["noteblocks"] = blocks
