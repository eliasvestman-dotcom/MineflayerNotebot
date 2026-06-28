"""Utility functions for the notebot."""
import os
import subprocess
import sys
from colorama import Fore, Style, init

# Initialize colorama for Windows compatibility
init(autoreset=True)


class Logger:
    """Logging utility with color support."""
    
    DEBUG = -1
    INFO = 0
    WARN = 1
    ERROR = 2
    
    @staticmethod
    def log(message, level=INFO):
        """Log a message with color based on level."""
        if level == Logger.DEBUG:
            print(f"{Fore.GREEN}[DEBUG] {message}{Style.RESET_ALL}")
        elif level == Logger.INFO:
            print(f"{Fore.BLUE}[INFO]  {message}{Style.RESET_ALL}")
        elif level == Logger.WARN:
            print(f"{Fore.YELLOW}[WARN]  {message}{Style.RESET_ALL}")
            Logger.beep()
        elif level == Logger.ERROR:
            print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
            Logger.beep()
    
    @staticmethod
    def beep():
        """Play a system beep sound."""
        try:
            if sys.platform == "win32":
                subprocess.run(['powershell.exe', '[console]::beep(500,600)'], 
                             capture_output=True, timeout=1)
            elif sys.platform == "darwin":
                subprocess.run(['printf', r'\a'], capture_output=True, timeout=1)
            else:
                subprocess.run(['sh', '-c', "echo -n $'\\a'"], 
                             capture_output=True, timeout=1)
        except Exception:
            pass  # Silent fail if beep not available


def two_num(num):
    """Format number with leading zero if less than 10."""
    return str(num).zfill(2) if num < 10 else str(num)


def is_valid_file(filename):
    """Check if song file exists."""
    try:
        path = f"songs/{filename}.nbs"
        return os.path.exists(path)
    except Exception:
        return False


def get_song_path(filename):
    """Get full path to song file."""
    return f"songs/{filename}.nbs"


def parse_command(command):
    """Parse a command string into action and arguments.
    
    Args:
        command: Command string like "@notebot --play song_name"
    
    Returns:
        dict with parsed command data
    """
    parts = command.split()
    result = {}
    
    i = 0
    while i < len(parts):
        if parts[i].startswith('--'):
            key = parts[i][2:]  # Remove --
            value = None
            
            if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                value = parts[i + 1]
                i += 2
            else:
                i += 1
            
            result[key] = value
        else:
            i += 1
    
    return result
