import pygame
import os
import time

# Numele exact al melodiei tale
AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.mp3"

print("=== TEST AUDIO ===")

# 1. Testăm placa de sunet
try:
    pygame.mixer.init()
    print("[OK] Placa de sunet a fost găsită și conectată!")
except Exception as e:
    print(f"\n[X] EROARE: Nu pot accesa placa de sunet! (Eroare: {e})")
    print("-> EȘTI ÎN WSL! Închide terminalul ăsta, deschide 'Command Prompt' (CMD) normal din Windows și încearcă din nou.")
    exit()

# 2. Testăm dacă găsește fișierul
if not os.path.exists(AUDIO_FILE):
    print(f"\n[X] EROARE: Nu găsesc fișierul '{AUDIO_FILE}'")
    print(f"Verifică dacă e pus fix în folderul curent: {os.getcwd()}")
    exit()

# 3. Dăm Play
print(f"[PLAY] Melodia '{AUDIO_FILE}' ar trebui să se audă acum. Apasă CTRL+C ca să oprești.")
try:
    pygame.mixer.music.load(AUDIO_FILE)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    
    # Ținem scriptul deschis ca să cânte melodia
    while pygame.mixer.music.get_busy():
        time.sleep(1)
except Exception as e:
    print(f"[X] Eroare la redarea melodiei: {e}")