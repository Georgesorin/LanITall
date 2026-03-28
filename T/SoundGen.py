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

def generate_tone(freq, duration, vol=0.5, wave_type='sine', slide=0):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    data = bytearray()

    for i in range(n_samples):
        t = i / sample_rate
        cur_freq = freq + slide * t

        if wave_type == 'sine': val = math.sin(2 * math.pi * cur_freq * t)
        elif wave_type == 'square': val = 1.0 if math.sin(2 * math.pi * cur_freq * t) > 0 else -1.0
        elif wave_type == 'saw': val = 2.0 * (t * cur_freq - math.floor(0.5 + t * cur_freq))
        elif wave_type == 'noise': val = random.uniform(-1, 1)

        scaled = int((val * vol + 1.0) * 127.5)
        data.append(max(0, min(255, scaled)))
    return data

def generate_sequence_sounds():
    if not os.path.exists(SFX_DIR):
        os.makedirs(SFX_DIR)

    # Gama Do major (28 de note / 4 octave)
    base_freqs = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]
    for i in range(28):
        octave_multiplier = 2 ** (i // 7)
        freq = base_freqs[i % 7] * octave_multiplier
        note_data = generate_tone(freq, 0.35, vol=0.4, wave_type='sine')
        save_wav(f"note_{i}.wav", note_data)

    # 1. Fail (Sunet grav)
    save_wav("fail.wav", generate_tone(150, 0.6, vol=0.5, wave_type='saw', slide=-500))

    # 2. Tick (Countdown)
    save_wav("tick.wav", generate_tone(880, 0.1, vol=0.2, wave_type='square'))

    # 3. Round Win (+1 punct) - Vesel, dar scurt
    rw1 = generate_tone(523.25, 0.15, vol=0.3, wave_type='square')
    rw2 = generate_tone(659.25, 0.15, vol=0.3, wave_type='square')
    rw3 = generate_tone(783.99, 0.4, vol=0.3, wave_type='square')
    save_wav("round_win.wav", rw1 + rw2 + rw3)

    # 4. Game Win (Victorie finală) - Mai lung și impunător
    gw1 = generate_tone(523.25, 0.2, vol=0.3, wave_type='square')
    gw2 = generate_tone(659.25, 0.2, vol=0.3, wave_type='square')
    gw3 = generate_tone(783.99, 0.2, vol=0.3, wave_type='square')
    gw4 = generate_tone(1046.50, 0.4, vol=0.3, wave_type='square')
    gw5 = generate_tone(1046.50, 0.9, vol=0.3, wave_type='square', slide=150) # Tensiune pe final
    save_wav("game_win.wav", gw1 + gw2 + gw3 + gw4 + gw5)

if __name__ == "__main__":
    generate_sequence_sounds()
    print("Sunetele au fost re-generate cu succes!")