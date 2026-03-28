import librosa
import numpy as np
import json
import warnings

# Ignorăm avertismentele
warnings.filterwarnings('ignore')

def get_column_from_note(note_string):
    """ Mapăm nota la coloanele 0, 1, 2, 3 """
    base_note = note_string[0].upper()
    if base_note in ['C', 'D']:   return 0
    elif base_note in ['E', 'F']: return 1
    elif base_note in ['G', 'A']: return 2
    elif base_note == 'B':        return 3
    return np.random.randint(0, 4)

def generate_beatmap(audio_path, output_json):
    print(f"Analizez fișierul: {audio_path}...")
    print("Așteaptă puțin, extragem ritmul și notele...")

    # Încărcăm piesa
    y, sr = librosa.load(audio_path)

    # Detectare Onset-uri (metodă standard, mult mai permisivă)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, wait=2)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Extragem înălțimea sunetelor
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)

    beatmap = []
    last_time = -1.0 # Pentru a preveni tile-uri suprapuse imposibil de jucat

    for i, time_sec in enumerate(onset_times):
        # FILTRU DE JUCABILITATE: 
        # Ignorăm notele care sunt la mai puțin de 0.12 secunde de precedenta (aprox 8 note/secundă max)
        if time_sec - last_time < 0.12:
            continue
        
        last_time = time_sec

        frame = onset_frames[i]
        index = magnitudes[:, frame].argmax()
        pitch_hz = pitches[index, frame]

        if pitch_hz > 0:
            note_str = librosa.hz_to_note(pitch_hz)
            col = get_column_from_note(note_str)
        else:
            # Dacă e doar percuție pură (fără frecvență clară, comun în D&B)
            col = int(np.random.randint(0, 4))
            note_str = "Percussion"

        beatmap.append({
            "time": round(float(time_sec), 3),
            "column": int(col),
            "note": note_str
        })

    with open(output_json, 'w') as f:
        json.dump(beatmap, f, indent=4)

    print(f"Gata! Am generat {len(beatmap)} tile-uri jucabile.")
    print(f"Salvat în: {output_json}")

if __name__ == "__main__":
    # Pune aici numele exact al fișierului tău
    AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.wav" 
    JSON_OUTPUT = "level.json"
    
    generate_beatmap(AUDIO_FILE, JSON_OUTPUT)