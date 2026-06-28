"""Main entry point for single-bot notebot."""
import json
import yaml
import sys
from utils import Logger
from note_bot import NoteBot


def load_config():
    """Load configuration from YAML file."""
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        Logger.log(f"Error loading config: {e}", Logger.ERROR)
        sys.exit(1)


def main():
    """Main function for single-bot setup."""
    config = load_config()
    
    # Create main bot
    username = config["bot"].get("username", "notebot")
    Logger.log("Starting Mineflayer Notebot v2.0 (Python Port)", Logger.INFO)
    Logger.log(f"Connecting as {username}", Logger.INFO)
    
    try:
        bot = NoteBot(username, config)
        Logger.log(f"Connected as {username}", Logger.INFO)
        
        # Keep alive
        while True:
            pass
    except KeyboardInterrupt:
        Logger.log("Shutting down...", Logger.INFO)
        sys.exit(0)
    except Exception as e:
        Logger.log(f"Fatal error: {e}", Logger.ERROR)
        sys.exit(1)


if __name__ == "__main__":
    main()
