# MineflayerNotebot - Python Version

A Python port of the Mineflayer Notebot that plays `.nbs` (Note Block Studio) files using a Minecraft bot.

## Installation

### Requirements
- Python 3.8+
- pip (Python package manager)

### Setup

1. **Clone or download the repository**
   ```bash
   git clone https://github.com/eliasvestman-dotcom/MineflayerNotebot.git
   cd MineflayerNotebot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot** (edit `config.yaml`):
   ```yaml
   bot:
     username: "notebot"
     host: "localhost"
     port: 25565
     version: "1.20.1"
   
   settings:
     command_prefix: "@"
     tune_speed: 80
   
   commands_perms:
     - your_username
   ```

4. **Add song files** to the `songs/` directory (`.nbs` files)

## Usage

### Single Bot Mode
Run a single bot that handles both leading and playing:
```bash
python main_single.py
```

### Multi-Bot Mode
Run multiple worker bots (default: 4 players):
```bash
python main_multi.py
```

To change the number of workers, edit `main_multi.py`:
```python
num_workers = 4  # Change this value
```

## In-Game Commands

Once the bot is running, use these chat commands:

### Setup a Song
```
/tell notebot @notebot --setup songName
```
Where `songName` is the name of the song file (without `.nbs` extension).

### Play a Song
```
/tell notebot @notebot --play songName
```

### Tune Note Blocks
```
/tell notebot @notebot --tune songName
```

### Detect Note Blocks
```
/tell notebot @notebot --detect
```

### Stop Playback
```
/tell notebot @notebot --stop
```

## File Structure

```
.
├── main_single.py        # Single bot entry point
├── main_multi.py         # Multi-bot entry point
├── note_bot.py          # Main NoteBot class
├── block_mapper.py      # Note block detection
├── utils.py             # Utility functions and logging
├── config.yaml          # Configuration file
├── instruments_map.json # Instrument definitions
├── requirements.txt     # Python dependencies
├── songs/               # Directory for .nbs song files
└── README.md            # This file
```

## Configuration

Edit `config.yaml` to customize:
- **Bot connection**: host, port, version, username
- **Tuning speed**: How fast to tune note blocks
- **Command permissions**: Which players can control the bot
- **Command prefix**: Prefix for commands (default: `@`)

## Authors

- Original JavaScript version by [@meeplabsdev](https://github.com/meeplabsdev)
- Python port by eliasvestman-dotcom

## License

ISC
