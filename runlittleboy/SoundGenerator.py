import wave
import struct
import math
import os

def synthesize_laser(filename, start_freq, end_freq, duration, wave_type='square', volume=0.3):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    # Ensure the _sfx folder exists
    os.makedirs('_sfx', exist_ok=True)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)       # Mono
        wav_file.setsampwidth(2)       # 16-bit audio
        wav_file.setframerate(sample_rate)
        
        phase = 0.0
        for i in range(num_samples):
            t = i / sample_rate
            
            # The "Pew" effect: Exponentially drop the frequency over time
            freq = start_freq * ((end_freq / start_freq) ** (t / duration))
            phase += 2 * math.pi * freq / sample_rate
            
            # Generate the waveform
            if wave_type == 'square':
                sample = 1.0 if math.sin(phase) > 0 else -1.0
            elif wave_type == 'sawtooth':
                sample = 2.0 * (phase / (2 * math.pi) - math.floor(phase / (2 * math.pi) + 0.5))
            else: # Sine wave (smoother)
                sample = math.sin(phase)
            
            # Envelope: Fast fade out so it sounds like a quick shot, not a continuous alarm
            envelope = max(0.0, 1.0 - (t / duration))
            
            # Convert to 16-bit PCM format
            audio_val = int(sample * envelope * volume * 32767)
            
            # Clamp values to prevent audio clipping/distortion
            audio_val = max(-32768, min(32767, audio_val))
            
            wav_file.writeframes(struct.pack('<h', audio_val))

def generate_all():
    print("Forging lightsabers and loading blasters... (Generating Sci-Fi SFX)")
    
    # 5 Distinct Blaster Shots (Varying pitches and lengths)
    synthesize_laser('_sfx/blaster_0.wav', 2000, 200, 0.25, 'square')
    synthesize_laser('_sfx/blaster_1.wav', 2200, 250, 0.25, 'square')
    synthesize_laser('_sfx/blaster_2.wav', 1800, 150, 0.30, 'square')
    synthesize_laser('_sfx/blaster_3.wav', 2500, 300, 0.20, 'square')
    synthesize_laser('_sfx/blaster_4.wav', 1500, 100, 0.35, 'square')
    
    # Game Events
    # Success: A rising, smooth sine wave (sounds like powering up)
    synthesize_laser('_sfx/success.wav', 400, 1200, 0.4, 'sine')
    # Eliminate/Miss: A low, harsh, descending sawtooth wave (sounds like an error/buzz)
    synthesize_laser('_sfx/eliminate.wav', 300, 50, 0.6, 'sawtooth')
    # Win: A long, high-pitched power-up sound
    synthesize_laser('_sfx/win.wav', 800, 2000, 1.5, 'sine')
    
    print("Sci-Fi SFX Generation Complete!")

if __name__ == "__main__":
    generate_all()