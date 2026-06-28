"""Main entry point for multi-bot notebot."""
import json
import yaml
import sys
from utils import Logger, two_num
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
    """Main function for multi-bot setup."""
    config = load_config()
    
    num_workers = 4
    
    Logger.log("Starting Mineflayer Notebot v2.0 (Python Port)", Logger.INFO)
    Logger.log(f"Spawning {num_workers} worker bots", Logger.INFO)
    
    workers = []
    for i in range(1, num_workers + 1):
        username = f"notebot_worker{two_num(i)}"
        try:
            worker = NoteBot(username, config)
            workers.append(worker)
            Logger.log(f"Worker {username} initialized", Logger.DEBUG)
        except Exception as e:
            Logger.log(f"Failed to initialize worker {username}: {e}", Logger.ERROR)
    
    Logger.log(f"Started {len(workers)} bots successfully", Logger.INFO)
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        Logger.log("Shutting down...", Logger.INFO)
        sys.exit(0)


if __name__ == "__main__":
    main()
