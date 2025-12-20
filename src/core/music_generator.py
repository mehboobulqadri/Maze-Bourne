"""
Maze Bourne - Procedural Music Generation
Simple ambient/sci-fi background music using pygame mixer
"""

import pygame
import numpy as np
import random


class ProceduralMusicGenerator:
    """Generates simple procedural ambient music for the game."""
    
    def __init__(self, sample_rate=22050):
        self.sample_rate = sample_rate
        self.is_playing = False
        self.current_track = None
        
    def generate_ambient_track(self, duration=30.0, seed=None):
        """
        Generate an ambient sci-fi track.
        
        Args:
            duration: Track length in seconds
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        
        samples = int(duration * self.sample_rate)
        track = np.zeros(samples, dtype=np.float32)
        
        # Bass drone (fundamental)
        bass_freq = random.choice([55, 65, 73, 82])  # A1, C2, D2, E2
        t = np.linspace(0, duration, samples)
        track += 0.3 * np.sin(2 * np.pi * bass_freq * t)
        
        # Add harmonics
        for harmonic in [2, 3, 5]:
            track += (0.15 / harmonic) * np.sin(2 * np.pi * bass_freq * harmonic * t)
        
        # Pad chords (slow evolving)
        chord_frequencies = [
            [220, 277, 330],  # Am
            [246, 311, 370],  # Bm
            [196, 247, 294],  # G
        ]
        
        chord_duration = duration / len(chord_frequencies)
        for i, chord in enumerate(chord_frequencies):
            start_idx = int(i * chord_duration * self.sample_rate)
            end_idx = int((i + 1) * chord_duration * self.sample_rate)
            chunk_t = np.linspace(0, chord_duration, end_idx - start_idx)
            
            # Fade in/out envelope
            envelope = np.sin(np.pi * chunk_t / chord_duration)
            
            for freq in chord:
                track[start_idx:end_idx] += 0.1 * envelope * np.sin(2 * np.pi * freq * chunk_t)
        
        # Ambient texture (filtered noise)
        noise = np.random.normal(0, 0.05, samples)
        # Simple lowpass (moving average)
        kernel_size = 100
        kernel = np.ones(kernel_size) / kernel_size
        filtered_noise = np.convolve(noise, kernel, mode='same')
        track += filtered_noise
        
        # Occasional high pings/beeps for sci-fi feel
        num_pings = random.randint(3, 8)
        for _ in range(num_pings):
            ping_time = random.uniform(0, duration)
            ping_freq = random.choice([880, 1100, 1320, 1760])  # A5, C#6, E6, A6
            ping_idx = int(ping_time * self.sample_rate)
            ping_duration = 0.15
            ping_samples = int(ping_duration * self.sample_rate)
            
            if ping_idx + ping_samples < samples:
                ping_t = np.linspace(0, ping_duration, ping_samples)
                ping_envelope = np.exp(-5 * ping_t)  # Fast decay
                ping = 0.2 * ping_envelope * np.sin(2 * np.pi * ping_freq * ping_t)
                track[ping_idx:ping_idx + ping_samples] += ping
        
        # Normalize
        max_val = np.max(np.abs(track))
        if max_val > 0:
            track = track / max_val * 0.7
        
        # Convert to 16-bit PCM
        track_int = (track * 32767).astype(np.int16)
        
        # Stereo (duplicate mono to both channels)
        stereo = np.column_stack((track_int, track_int))
        
        return pygame.sndarray.make_sound(stereo)
    
    def play(self, volume=0.3, loops=-1):
        """Play the generated track."""
        if not self.current_track:
            print("[MusicGenerator] Generating ambient track...")
            self.current_track = self.generate_ambient_track(duration=45.0, seed=42)
        
        if pygame.mixer.get_init():
            self.current_track.set_volume(volume)
            self.current_track.play(loops=loops)
            self.is_playing = True
            print("[MusicGenerator] Music started")
    
    def stop(self):
        """Stop playing music."""
        if self.is_playing and self.current_track:
            self.current_track.stop()
            self.is_playing = False
            print("[MusicGenerator] Music stopped")
    
    def set_volume(self, volume):
        """Set music volume (0.0 - 1.0)."""
        if self.current_track:
            self.current_track.set_volume(volume)
