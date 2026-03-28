import wave
import math
import random
import os

SFX_DIR = "_sfx"

def save_wav(filename, data, sample_rate=44100):
    if not os.path.exists(SFX_DIR):
        os.makedirs(SFX_DIR)
    path = os.path.join(SFX_DIR, filename)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(1)
        f.setframerate(sample_rate)
        f.writeframes(data)
    # print(f"Generated {path}")

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
    if not os.path.exists(SFX_DIR):
        os.makedirs(SFX_DIR)

    # 1. Step (Quick, high-pitched square blip)
    save_wav("step.wav", generate_tone(600, 0.05, vol=0.2, type='square'))

    # 2. Vanish (Low, descending saw wave as the floor drops)
    save_wav("vanish.wav", generate_tone(150, 0.15, vol=0.4, type='saw', slide=-800))

    # 3. Eliminate (Harsh noise/square crash)
    save_wav("eliminate.wav", generate_tone(200, 0.8, vol=0.5, type='saw', slide=-400))

    # 4. Tick (Countdown beep)
    save_wav("tick.wav", generate_tone(880, 0.1, vol=0.3, type='square'))

    # 5. Win (Triumphant fast arpeggio: C, E, G, C)
    n1 = generate_tone(523.25, 0.15, vol=0.3, type='square')
    n2 = generate_tone(659.25, 0.15, vol=0.3, type='square')
    n3 = generate_tone(783.99, 0.15, vol=0.3, type='square')
    n4 = generate_tone(1046.50, 0.6, vol=0.3, type='square', slide=200)
    save_wav("win.wav", n1 + n2 + n3 + n4)

    # 6. BGM (Fast, tense repeating bassline for TNT Run)
    bpm = 140
    beat_dur = 60 / bpm
    melody_notes = [
        (110, 0.25), (0, 0.25), (110, 0.25), (0, 0.25), # A2
        (130, 0.25), (0, 0.25), (146, 0.25), (0, 0.25), # C3, D3
    ]
    bgm_data = bytearray()
    for freq, dur_beats in melody_notes:
        dur_sec = dur_beats * beat_dur
        if freq == 0:
            audio = bytearray([128] * int(44100 * dur_sec))
        else:
            audio = generate_tone(freq, dur_sec, vol=0.2, type='saw')
        bgm_data += audio
    save_wav("bgm.wav", bgm_data * 8) # Loop it a few times to make a longer track

if __name__ == "__main__":
    generate_all()
    print("TNT Run Sounds generated successfully!")