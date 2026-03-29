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

def generate_beatmap(audio_path, output_json, offset=0.0):
    print(f"Analizez piesa: {audio_path}...")
    print("Așteaptă puțin, extragem tempo-ul și ritmul...")

    # Încărcăm piesa
    y, sr = librosa.load(audio_path)

    # 1. Extragem energia audio
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    
    # 2. GĂSIM RITMUL (Aici este secretul pentru a fi 'pe beat')
    # beat_track găsește BPM-ul și aliniază cadrele exact pe ritmul principal (kick/snare)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
    
    # Transformăm cadrele de beat în timp real (secunde)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Extragem înălțimea sunetelor pentru maparea coloanelor
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)

    beatmap = []
    last_time = -1.0 

    for i, time_sec in enumerate(beat_times):
        # 3. Aplicăm calibrarea hardware-ului
        adjusted_time = time_sec + offset
        
        # Oprim notele care se suprapun tehnic (deși beaturile sunt natural spațiate corect)
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

    # Formatăm tempo-ul curat, indiferent dacă librosa returnează array sau float
    bpm_val = tempo[0] if isinstance(tempo, (list, np.ndarray)) else tempo

    print(f"Gata! Am generat {len(beatmap)} tile-uri perfect pe ritm.")
    print(f"BPM Detectat: {round(bpm_val, 2)}")
    print(f"Salvat în: {output_json}")

if __name__ == "__main__":
    # Pune aici numele exact al fișierului tău
    AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.wav" 
    JSON_OUTPUT = "level.json"
    
    # CALIBRARE HARDWARE:
    # Dacă tile-urile ajung JOS puțin *înainte* de a se auzi bass-ul, pune o valoare pozitivă (ex: 0.1)
    # Dacă tile-urile ajung JOS puțin *după* ce se aude bass-ul, pune o valoare negativă (ex: -0.1)
    AUDIO_OFFSET = 0.0 
    
    generate_beatmap(AUDIO_FILE, JSON_OUTPUT, offset=AUDIO_OFFSET)