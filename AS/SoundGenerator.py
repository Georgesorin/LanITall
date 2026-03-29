import wave
import math
import random
import os

SFX_DIR = "_sfx"

def save_wav(filename, data, sample_rate=44100):
    if not os.path.exists(SFX_DIR): os.makedirs(SFX_DIR)
    path = os.path.join(SFX_DIR, filename)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(1)
        f.setframerate(sample_rate)
        f.writeframes(data)

def generate_tone(freq, duration, vol=0.5, type='sine', slide=0):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    data = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        cur_freq = freq + slide * t
        if type == 'sine': val = math.sin(2 * math.pi * cur_freq * t)
        elif type == 'square': val = 1.0 if math.sin(2 * math.pi * cur_freq * t) > 0 else -1.0
        elif type == 'saw': val = 2.0 * (t * cur_freq - math.floor(0.5 + t * cur_freq))
        elif type == 'noise': val = random.uniform(-1, 1)
        scaled = int((val * vol + 1.0) * 127.5)
        data.append(max(0, min(255, scaled)))
    return data

def generate_all():
    if not os.path.exists(SFX_DIR): os.makedirs(SFX_DIR)

    # 5 Distinct "Animal" Sounds
    save_wav("animal_0.wav", generate_tone(800, 0.2, vol=0.3, type='sine', slide=500))  # Bird Chirp
    save_wav("animal_1.wav", generate_tone(150, 0.3, vol=0.4, type='square', slide=50)) # Frog Croak
    save_wav("animal_2.wav", generate_tone(100, 0.4, vol=0.4, type='saw', slide=-20))   # Cow Moo
    save_wav("animal_3.wav", generate_tone(400, 0.2, vol=0.3, type='square', slide=-200)) # Dog Bark
    save_wav("animal_4.wav", generate_tone(1200, 0.1, vol=0.2, type='noise'))           # Cricket

    # Game States
    save_wav("success.wav", generate_tone(600, 0.3, vol=0.2, type='sine', slide=400))
    save_wav("eliminate.wav", generate_tone(200, 0.8, vol=0.5, type='saw', slide=-400))
    
    n1 = generate_tone(523.25, 0.15, vol=0.3, type='square')
    n2 = generate_tone(659.25, 0.15, vol=0.3, type='square')
    n3 = generate_tone(783.99, 0.15, vol=0.3, type='square')
    n4 = generate_tone(1046.50, 0.6, vol=0.3, type='square', slide=200)
    save_wav("win.wav", n1 + n2 + n3 + n4)

if __name__ == "__main__":
    generate_all()
    print("Animal sounds generated successfully!")