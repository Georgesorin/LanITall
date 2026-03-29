import librosa
import numpy as np
import json
import warnings

warnings.filterwarnings('ignore')

def get_column_from_note(note_string):
    """ Mapăm nota la coloanele 0, 1, 2, 3 """
    base_note = note_string[0].upper()
    if base_note in ['C', 'D']:   return 0
    elif base_note in ['E', 'F']: return 1
    elif base_note in ['G', 'A']: return 2
    elif base_note == 'B':        return 3
    return np.random.randint(0, 4)

def generate_beatmap(audio_path, output_json, offset=0.0, beat_divider=1):
    print("Se extrage tempo-ul și ritmul...")

    # incarcare de piesa
    y, sr = librosa.load(audio_path)

    # extragere energie audio
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # det ritm
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
    
    # adaugam un fel de delay in cod, sar peste cateva esantioane
    beat_frames = beat_frames[::beat_divider]
    
    # trec in analog
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # mapez coloanele in functie de frecv lor maxima
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)

    beatmap = []
    last_time = -1.0 

    for i, time_sec in enumerate(beat_times):
        adjusted_time = time_sec + offset
        
        # oprim notele care se suprapun tehnic 
        if adjusted_time - last_time < 0.2:
            continue
        
        last_time = adjusted_time

        frame = beat_frames[i]
        index = magnitudes[:, frame].argmax()
        pitch_hz = pitches[index, frame]

        if pitch_hz > 0:
            note_str = librosa.hz_to_note(pitch_hz)
            col = get_column_from_note(note_str)
        else:
            col = int(np.random.randint(0, 4))
            note_str = "Percussion"

        beatmap.append({
            "time": round(float(adjusted_time), 3),
            "column": int(col),
            "note": note_str
        })

    with open(output_json, 'w') as f:
        json.dump(beatmap, f, indent=4)

    # tempo curat, indiferent de tipul de return
    bpm_val = tempo[0] if isinstance(tempo, (list, np.ndarray)) else tempo
    perceived_bpm = bpm_val / beat_divider

    print(f"S a generat {len(beatmap)} tile-uri perfect pe ritm.")
    print(f"BPM Original: {round(bpm_val, 2)} | BPM Jucabil: {round(perceived_bpm, 2)}")
    print(f"Salvat în: {output_json}")

if __name__ == "__main__":
    AUDIO_FILE = "Petre Stefan - PETER PARKER.wav" 
    JSON_OUTPUT = "level.json"
    
    # CALIBRARE HARDWARE - n am avut neaparat nevoie acum
    AUDIO_OFFSET = 0.0 
    
    # --- CONTROLUL DENSITĂȚII TILE-URILOR ---
    # 1 = Un pas pe fiecare beat (Foarte rapid pentru piese DnB/Nightcore)
    # 2 = Un pas la fiecare al doilea beat (Ritm de "Half-time", perfect pe toba mare, mult mai jucabil)
    # 4 = Un pas la fiecare al 4-lea beat (Foarte relaxant/ușor)
    DIVIDER = 2
    
    generate_beatmap(AUDIO_FILE, JSON_OUTPUT, offset=AUDIO_OFFSET, beat_divider=DIVIDER)