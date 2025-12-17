import pygame
import os
from src.core.constants import AUDIO_ENABLED, MASTER_VOLUME, SFX_VOLUME, MUSIC_VOLUME

class AudioManager:
    def __init__(self):
        self.enabled = AUDIO_ENABLED
        self.sounds = {}
        self.master_volume = MASTER_VOLUME
        self.sfx_volume = SFX_VOLUME
        self.music_volume = MUSIC_VOLUME
        
        # Initialize mixer if not already done
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        self.load_assets()
        
    def load_assets(self):
        """Load all sound files from assets/audio."""
        audio_dir = "assets/audio"
        if not os.path.exists(audio_dir):
            print(f"[AudioManager] Audio directory not found: {audio_dir}")
            return
            
        for filename in os.listdir(audio_dir):
            if filename.endswith(".wav") or filename.endswith(".ogg"):
                name = os.path.splitext(filename)[0]
                path = os.path.join(audio_dir, filename)
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(self.master_volume * self.sfx_volume)
                    self.sounds[name] = sound
                    print(f"[AudioManager] Loaded {name}")
                except Exception as e:
                    print(f"[AudioManager] Failed to load {filename}: {e}")

    def play_sound(self, name: str, volume_scale: float = 1.0):
        """Play a sound effect by name."""
        if not self.enabled or name not in self.sounds:
            return
            
        sound = self.sounds[name]
        # Adjust volume dynamically based on current settings
        final_vol = self.master_volume * self.sfx_volume * volume_scale
        sound.set_volume(final_vol)
        sound.play()

    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
        
    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
    
    def _update_volumes(self):
        """Update volumes of loaded sounds."""
        for sound in self.sounds.values():
            sound.set_volume(self.master_volume * self.sfx_volume)
