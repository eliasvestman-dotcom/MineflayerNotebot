"""Block mapper for detecting note blocks around the bot."""
import json
from utils import Logger


class BlockMapper:
    """Maps note blocks around the player."""
    
    def __init__(self):
        try:
            with open("instruments_map.json", "r") as f:
                self.instruments_map = json.load(f)
        except Exception as e:
            Logger.log(f"Error loading instruments map: {e}", Logger.ERROR)
            self.instruments_map = {}
    
    def map_noteblocks(self, bot):
        """Map all note blocks around the bot within a 5 block radius.
        
        Args:
            bot: Bot connection object
        
        Returns:
            List of note block information dicts
        """
        result = []
        
        if not bot:
            return result
        
        try:
            # Scan 5 blocks in each direction
            for x in range(-5, 6):
                for y in range(-8, 9):
                    for z in range(-5, 6):
                        try:
                            pos = self._get_block_at_offset(bot, x, y, z)
                            block_above = self._get_block_at_offset(bot, x, y + 1, z)
                            
                            if pos and pos.get("name") == "note_block":
                                if block_above and block_above.get("name") in ["air", "cave_air", "void_air"]:
                                    nb_info = self.get_note_block_info(pos)
                                    if nb_info:
                                        result.append({
                                            "position": pos.get("position"),
                                            "pitch": nb_info.get("pitch", 0),
                                            "instrumentid": nb_info.get("instrumentid", 0),
                                            "metadata": pos.get("metadata", 0)
                                        })
                        except Exception:
                            continue
        except Exception as e:
            Logger.log(f"Error mapping noteblocks: {e}", Logger.ERROR)
        
        return result
    
    @staticmethod
    def _get_block_at_offset(bot, x, y, z):
        """Get block at offset from bot position."""
        try:
            if hasattr(bot, 'blockAt') and hasattr(bot, 'entity'):
                block = bot.blockAt(bot.entity.position.offset(x, y, z))
                if block:
                    return {
                        "name": getattr(block, 'name', None),
                        "metadata": getattr(block, 'metadata', 0),
                        "position": getattr(block, 'position', None)
                    }
            return None
        except Exception:
            return None
    
    def get_note_block_info(self, block):
        """Get note block information from block metadata."""
        if not block:
            return None
        
        name = block.get("name")
        metadata = block.get("metadata", 0)
        
        if name != "note_block":
            return None
        
        return self.noteblock_info_from_metadata(metadata)
    
    def noteblock_info_from_metadata(self, metadata):
        """Extract instrument and pitch from metadata."""
        try:
            instrument_id = int(metadata / 50)
            
            if metadata % 2 == 0:
                pitch = int(metadata / 2)
            else:
                pitch = int((metadata - 1) / 2) + 1
            
            pitch = pitch - (instrument_id * 25) - 1
            
            lowercase_map = self.instruments_map.get("lowercase", {})
            instrument = lowercase_map.get(str(instrument_id), f"instrument_{instrument_id}")
            
            return {
                "instrument": instrument,
                "instrumentid": instrument_id,
                "pitch": pitch
            }
        except Exception as e:
            Logger.log(f"Error extracting noteblock info: {e}", Logger.ERROR)
            return None
