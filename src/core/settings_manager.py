import json
import os
from typing import Dict, Any
from src.core.logger import get_logger

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "audio": {
        "master_volume": 0.7,
        "music_volume": 0.5,
        "sfx_volume": 0.8,
        "enabled": True
    },
    "gameplay": {
        "difficulty": "normal",  # easy, normal, hard
        "enemy_speed_multiplier": 1.0,
        "enemy_vision_multiplier": 1.0,
        "enemy_smartness": 1.0  # 0.5 = dumb, 1.0 = normal, 1.5 = smart
    }
}

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()
    
    def load(self):
        """Load settings from file."""
        if not os.path.exists(SETTINGS_FILE):
            return
            
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._recursive_update(self.settings, saved)
            get_logger().info("Settings loaded")
        except Exception as e:
            get_logger().error(f"Failed to load settings: {e}")
    
    def save(self):
        """Save settings to file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
            get_logger().info("Settings saved")
        except Exception as e:
            get_logger().error(f"Failed to save settings: {e}")
            
    def _recursive_update(self, base: Dict, update: Dict):
        """Update dictionary recursively, preserving structure."""
        for k, v in update.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._recursive_update(base[k], v)
            else:
                base[k] = v
                
    def get(self, category: str, key: str) -> Any:
        return self.settings.get(category, {}).get(key)
    
    def set(self, category: str, key: str, value: Any):
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save()  # Auto-save on change simple for now
