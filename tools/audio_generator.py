import wave
import math
import random
import struct
import os

OUTPUT_DIR = "assets/audio"

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_wave(filename, samples, sample_rate=44100):
    ensure_dir(OUTPUT_DIR)
    path = os.path.join(OUTPUT_DIR, filename)
    with wave.open(path, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Convert to 16-bit integers
        data = []
        for s in samples:
            # Clip
            s = max(-1.0, min(1.0, s))
            data.append(int(s * 32767.0))
            
        wav_file.writeframes(struct.pack('h' * len(data), *data))
    print(f"Generated {path}")

def generate_tone(frequency, duration, volume=0.5, sample_rate=44100, fade_out=True):
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = float(i) / sample_rate
        val = math.sin(2.0 * math.pi * frequency * t)
        
        # Envelope
        env = 1.0
        if fade_out:
            env = 1.0 - (i / num_samples)
            
        samples.append(val * volume * env)
    return samples

def generate_noise(duration, volume=0.5, sample_rate=44100, fade_out=True):
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        val = random.uniform(-1.0, 1.0)
        
        # Envelope
        env = 1.0
        if fade_out:
            env = 1.0 - (i / num_samples)
            
        samples.append(val * volume * env)
    return samples

def generate_slide(start_freq, end_freq, duration, volume=0.5, sample_rate=44100):
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = float(i) / sample_rate
        progress = i / num_samples
        freq = start_freq + (end_freq - start_freq) * progress
        # Phase accumulation would be better but simple param update works for short SFX
        val = math.sin(2.0 * math.pi * freq * t)
        samples.append(val * volume * (1.0 - progress))
    return samples

def main():
    print("Generating procedural audio assets...")
    
    # 1. Alert (High pitch warble)
    samples = generate_tone(880, 0.1, 0.5) + generate_tone(1100, 0.2, 0.5)
    save_wave("sfx_alert.wav", samples)
    
    # 2. Dash (White noise slide)
    samples = generate_noise(0.3, 0.3)
    save_wave("sfx_dash.wav", samples)
    
    # 3. Footstep (Short low thud)
    samples = generate_noise(0.05, 0.2)
    save_wave("sfx_step.wav", samples)
    
    # 4. UI Hover (Very short high blip)
    samples = generate_tone(1200, 0.03, 0.1)
    save_wave("sfx_ui_hover.wav", samples)
    
    # 5. UI Select (Positive beep)
    samples = generate_slide(440, 880, 0.1, 0.3)
    save_wave("sfx_ui_select.wav", samples)
    
    # 6. Enemy Spotted (Startle sound)
    samples = generate_slide(200, 800, 0.2, 0.4)
    save_wave("sfx_spotted.wav", samples)

if __name__ == "__main__":
    main()
