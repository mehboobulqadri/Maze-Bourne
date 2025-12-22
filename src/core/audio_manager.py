import pygame
import os
from src.core.constants import AUDIO_ENABLED, MASTER_VOLUME, SFX_VOLUME, MUSIC_VOLUME
from src.core.logger import get_logger

class AudioManager:
    def __init__(self):
        self.enabled = AUDIO_ENABLED
        self.sounds = {}
        self.master_volume = MASTER_VOLUME
        self.sfx_volume = SFX_VOLUME
        self.music_volume = MUSIC_VOLUME
        
        # Initialize mixer if not already done
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as e:
            get_logger().error(f"Failed to initialize audio mixer: {e}", exc_info=True)
            self.enabled = False
            return
            
        self.load_assets()
        
    def load_assets(self):
        """Load all sound files from assets/audio."""
        audio_dir = "assets/audio"
        try:
            if not os.path.exists(audio_dir):
                get_logger().warning(f"Audio directory not found: {audio_dir}")
                return
                
            for filename in os.listdir(audio_dir):
                if filename.endswith(".wav") or filename.endswith(".ogg"):
                    name = os.path.splitext(filename)[0]
                    path = os.path.join(audio_dir, filename)
                    try:
                        sound = pygame.mixer.Sound(path)
                        sound.set_volume(self.master_volume * self.sfx_volume)
                        self.sounds[name] = sound
                        get_logger().debug(f"Loaded audio: {name}")
                    except Exception as e:
                        get_logger().error(f"Failed to load {filename}: {e}")
        except OSError as e:
            get_logger().error(f"Error accessing audio directory {audio_dir}: {e}", exc_info=True)

    def play_sound(self, name: str, volume_scale: float = 1.0):
        """Play a sound effect by name."""
        if not self.enabled or name not in self.sounds:
            return
            
        try:
            sound = self.sounds[name]
            # Adjust volume dynamically based on current settings
            final_vol = self.master_volume * self.sfx_volume * volume_scale
            sound.set_volume(final_vol)
            sound.play()
        except Exception as e:
            get_logger().error(f"Failed to play sound {name}: {e}")

    def play_music(self, name: str, loop: bool = True):
        """Play background music by name."""
        if not self.enabled:
            return
            
        try:
            # Construct path (music files might be in assets/music or assets/audio)
            # Assuming they are in assets/audio for now based on load_assets, 
            # OR checking if they assume a specific path.
            # load_assets only loads into self.sounds (for SFX).
            # Music is streamed usually.
            
            # Let's try both locations.
            path = f"assets/audio/{name}.ogg"
            if not os.path.exists(path):
                path = f"assets/audio/{name}.wav"
            if not os.path.exists(path):
                 get_logger().warning(f"Music file not found: {name}")
                 return

            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
            pygame.mixer.music.play(-1 if loop else 0)
            get_logger().info(f"Playing music: {name}")
        except Exception as e:
            get_logger().error(f"Failed to play music {name}: {e}")

    def stop_music(self):
        """Stop currently playing music."""
        if not self.enabled: return
        pygame.mixer.music.stop()

    def set_master_volume(self, volume: float):
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
        
    def set_sfx_volume(self, volume: float):
        self.sfx_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
    
    def set_music_volume(self, volume: float):
        self.music_volume = max(0.0, min(1.0, volume))
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
            except: pass

    def _update_volumes(self):
        """Update volumes of loaded sounds."""
        for sound in self.sounds.values():
            sound.set_volume(self.master_volume * self.sfx_volume)
        
        # Also update music
        try:
             pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
        except: pass
