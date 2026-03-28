import socket
import time
import threading
import math
import os
import json
import random
import wave
import struct

<<<<<<< HEAD
=======
os.environ['SDL_AUDIODRIVER'] = 'pulse'

>>>>>>> 5d42ae70b2c7be5bda282b9091cc5938232f6570
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# --- Configurație Rețea ---
<<<<<<< HEAD
UDP_IP = "127.0.0.1"
UDP_PORT_SEND = 1067
UDP_PORT_RECV = 1069
=======
UDP_IP = "255.255.255.255"
UDP_PORT_SEND = 4626
UDP_PORT_RECV = 7800
>>>>>>> 5d42ae70b2c7be5bda282b9091cc5938232f6570
WIDTH, HEIGHT = 16, 32
FRAME_DATA_LENGTH = 8 * 64 * 3

# --- Configurație Fișiere ---
BEATMAP_FILE = "level.json"
<<<<<<< HEAD
AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.wav"
=======
AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.mp3"
>>>>>>> 5d42ae70b2c7be5bda282b9091cc5938232f6570

# Culori
PURPLE  = (154, 66, 255)
CYAN    = (0, 255, 255)
GREEN   = (0, 255, 0)
YELLOW  = (255, 220, 0)
BLACK   = (0, 0, 0)

TILE_COLS_M1 = [2, 5, 9, 12]
TILE_COLS_M2 = [6, 7, 8, 9] 

HIT_ZONE_BOTTOM = (26, 29)
HIT_ZONE_TOP    = (2, 5)
FLASH_DURATION  = 0.15

# ==========================================
# 1. GENERATOR DE EFECTE AUDIO (8-BIT)
# ==========================================
class SFXGenerator:
    SFX_DIR = "_sfx"

    @classmethod
    def save_wav(cls, filename, data, sample_rate=44100):
        if not os.path.exists(cls.SFX_DIR):
            os.makedirs(cls.SFX_DIR)
            
        path = os.path.join(cls.SFX_DIR, filename)
        with wave.open(path, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(1) # 8-bit audio
            f.setframerate(sample_rate)
            f.writeframes(data)

    @classmethod
    def generate_tone(cls, freq, duration, vol=0.5, type='sine', slide=0):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        data = bytearray()
        
        for i in range(n_samples):
            t = i / sample_rate
            cur_freq = freq + slide * t
            
            if type == 'sine':
                val = math.sin(2 * math.pi * cur_freq * t)
            elif type == 'square':
                val = 1.0 if math.sin(2 * math.pi * cur_freq * t) > 0 else -1.0
            elif type == 'saw':
                val = 2.0 * (t * cur_freq - math.floor(0.5 + t * cur_freq))
            elif type == 'noise':
                val = random.uniform(-1, 1)
                
            scaled = int((val * vol + 1.0) * 127.5)
            scaled = max(0, min(255, scaled))
            data.append(scaled)
            
        return data

    @classmethod
    def generate_all(cls):
        if not os.path.exists(cls.SFX_DIR):
            os.makedirs(cls.SFX_DIR)
            
        # Generăm sunet de HIT (un ping scurt și ascuțit)
        hit_sound = cls.generate_tone(600, 0.05, vol=0.3, type='square', slide=500)
        cls.save_wav("hit.wav", hit_sound)

        # Generăm sunet de MISS (un buzz grav și scurt)
        miss_sound = cls.generate_tone(150, 0.15, vol=0.4, type='saw', slide=-50)
        cls.save_wav("miss.wav", miss_sound)

# ==========================================
# 2. MANAGER AUDIO (Pygame)
# ==========================================
class SoundManager:
    def __init__(self, bgm_file):
        self.enabled = False
        self.music_playing = False
        self.sounds = {}
        self.bgm_file = bgm_file
        
        if PYGAME_AVAILABLE:
            try:
                # Inițializăm mixerul
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self.enabled = True
                
                # Verificăm dacă fișierele generate există. Dacă nu, le creăm acum!
                if not os.path.exists("_sfx/hit.wav") or not os.path.exists("_sfx/miss.wav"):
                    print("[SFX] Generez efectele audio 8-bit...")
                    SFXGenerator.generate_all()
                
                # Încărcăm efectele în memorie
                try:
                    self.sounds['hit'] = pygame.mixer.Sound("_sfx/hit.wav")
                    self.sounds['miss'] = pygame.mixer.Sound("_sfx/miss.wav")
                    # Dăm volumul la efecte un pic mai încet să nu acopere piesa
                    self.sounds['hit'].set_volume(0.5) 
                    self.sounds['miss'].set_volume(0.6)
                except Exception as e:
                    print(f"[SFX] Eroare la încărcarea SFX-urilor: {e}")
                    
            except pygame.error as e:
                print(f"[AVERTISMENT] Audio indisponibil (posibil limitare WSL/Linux). Jocul va fi silențios. Eroare: {e}")

    def play_sfx(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except: pass

    def play_bgm(self):
        if self.enabled and not self.music_playing:
            try:
                if os.path.exists(self.bgm_file):
                    pygame.mixer.music.load(self.bgm_file)
                    pygame.mixer.music.set_volume(0.8)
                    pygame.mixer.music.play()
                    self.music_playing = True
                    print(f"[AUDIO] Redau melodia: {self.bgm_file}")
            except Exception as e:
                print(f"[AUDIO] Eroare BGM: {e}")

    def stop_bgm(self):
        if self.enabled and self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False


# ==========================================
# 3. ENGINE PIANO TILES
# ==========================================
class PianoTilesEngine:
    def __init__(self):
        self.running = True
        self.mode = None       
        self.start_time = 0
        self.is_pulsing = False
        self.speed = 15 # Rânduri per secundă

        self.button_states = [False] * 64
        self.prev_button_states = [False] * 64

        # Inițializăm noul manager de sunet!
        self.sound = SoundManager(AUDIO_FILE)

        self.beatmap = []
        self.load_level(BEATMAP_FILE)

        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {} 

        self.score_p1 = 0; self.misses_p1 = 0 
        self.score_p2 = 0; self.misses_p2 = 0 

    def load_level(self, filename):
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.beatmap = data[::2] 
            else: pass
        except Exception: pass

    def _reset_state(self):
        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {}
        self.score_p1 = 0; self.misses_p1 = 0
        self.score_p2 = 0; self.misses_p2 = 0
        
        self.sound.stop_bgm()

    def get_score_report(self):
        if self.mode == '1':
            return f"--- SCOR CO-OP ---\nHits: {self.score_p2}\nMisses: {self.misses_p2}\n------------------"
        elif self.mode == '2':
            return (f"--- SCOR 1v1 ---\n"
                    f"P1 (SUS): {self.score_p1} Hits | {self.misses_p1} Misses\n"
                    f"P2 (JOS): {self.score_p2} Hits | {self.misses_p2} Misses\n"
                    f"-----------------")
        return "[!] Jocul este în așteptare."

    def process_input(self):
        if self.mode is None or self.is_pulsing:
            self.prev_button_states = list(self.button_states)
            return
        t = time.time()
        for i in range(64):
            if self.button_states[i] and not self.prev_button_states[i]:
                col = i % 4 
                self._try_hit(col, t)
        self.prev_button_states = list(self.button_states)

    def _try_hit(self, col, current_t):
        song_time = current_t - self.start_time
        HIT_WINDOW = 0.25 

        for tile_id, tile in enumerate(self.beatmap):
            if tile['column'] != col: continue
            
            time_diff = song_time - tile['time']
            if abs(time_diff) <= HIT_WINDOW:
                if self.mode == '1':
                    if tile_id not in self.hit_tiles[col]:
                        self.hit_tiles[col].add(tile_id)
                        self.flash_hits[(col, tile_id, 'down')] = current_t
                        self.score_p2 += 1 
                        self.sound.play_sfx('hit') # SUNET DE HIT!
                        return 
                elif self.mode == '2':
                    uid_d = f"d_{tile_id}"
                    if uid_d not in self.hit_tiles[col]:
                        self.hit_tiles[col].add(uid_d)
                        self.flash_hits[(col, tile_id, 'down')] = current_t
                        self.score_p2 += 1
                        self.sound.play_sfx('hit') # SUNET DE HIT!
                        
                    uid_u = f"u_{tile_id}"
                    if uid_u not in self.hit_tiles[col]:
                        self.hit_tiles[col].add(uid_u)
                        self.flash_hits[(col, tile_id, 'up')] = current_t
                        self.score_p1 += 1
                        self.sound.play_sfx('hit') # SUNET DE HIT!
                    return

    def _update_logic(self):
        t = time.time()
        expired = [k for k, start_t in self.flash_hits.items() if t - start_t > FLASH_DURATION]
        for k in expired: del self.flash_hits[k]

        if self.mode is None or self.is_pulsing: return
        song_time = t - self.start_time

        # Detecție Miss-uri automate
        for tile_id, tile in enumerate(self.beatmap):
            if song_time > tile['time'] + 0.3:
                col = tile['column']
                if self.mode == '1':
                    if tile_id not in self.hit_tiles[col] and tile_id not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(tile_id)
                        self.misses_p2 += 1
                        self.sound.play_sfx('miss') # SUNET DE MISS!
                elif self.mode == '2':
                    uid_d = f"d_{tile_id}"
                    if uid_d not in self.hit_tiles[col] and uid_d not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(uid_d)
                        self.misses_p2 += 1
                        self.sound.play_sfx('miss') # SUNET DE MISS!
                    uid_u = f"u_{tile_id}"
                    if uid_u not in self.hit_tiles[col] and uid_u not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(uid_u)
                        self.misses_p1 += 1
                        self.sound.play_sfx('miss') # SUNET DE MISS!

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)
        t = time.time()
        self._update_logic()

        if self.mode and self.is_pulsing:
            if t - self.start_time > 2.0: 
                self.is_pulsing = False
                self.start_time = time.time() 
                self.sound.play_bgm() # START MUZICĂ FUNDAL

        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self.mode is None:
                    self.set_led(buffer, x, y, (int(127+127*math.sin(t*2+y*0.3)), 50, 200))
                    continue

                is_frame = (y < 2 or y >= HEIGHT - 2)
                if self.mode == '2' and (y == 15 or y == 16): is_frame = True
                if is_frame:
                    c = PURPLE
                    if self.is_pulsing:
                        f = 0.7 + 0.3 * math.sin(t * 12)
                        c = tuple(int(ch*f) for ch in PURPLE)
                    self.set_led(buffer, x, y, c)
                    continue

                if self.is_pulsing: continue

                song_time = t - self.start_time
                active_cols = TILE_COLS_M1 if self.mode == '1' else TILE_COLS_M2

                for tile_id, tile in enumerate(self.beatmap):
                    json_col = tile['column']
                    target_time = tile['time']
                    
                    if json_col >= len(active_cols): continue
                    sx = active_cols[json_col]

                    if self.mode == '1':
                        if not (sx <= x <= sx + 1): continue
                        if tile_id in self.miss_tiles[json_col]: continue
                        
                        py_f = 27 - (target_time - song_time) * self.speed
                        py = int(py_f)
                        
                        if py <= y <= py + 1:
                            if tile_id in self.hit_tiles[json_col]:
                                if (json_col, tile_id, 'down') in self.flash_hits: 
                                    self.set_led(buffer, x, y, GREEN)
                            else:
                                color = YELLOW if (HIT_ZONE_BOTTOM[0] <= py_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                self.set_led(buffer, x, y, color)
                                
                    elif self.mode == '2':
                        if x != sx: continue 
                        
                        uid_d = f"d_{tile_id}"
                        if uid_d not in self.miss_tiles[json_col]:
                            pd_f = 27 - (target_time - song_time) * self.speed
                            pd = int(pd_f)
                            if y == pd:
                                if uid_d in self.hit_tiles[json_col]:
                                    if (json_col, tile_id, 'down') in self.flash_hits: self.set_led(buffer, x, y, GREEN)
                                else:
                                    color = YELLOW if (HIT_ZONE_BOTTOM[0] <= pd_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                    self.set_led(buffer, x, y, color)
                                    
                        uid_u = f"u_{tile_id}"
                        if uid_u not in self.miss_tiles[json_col]:
                            pu_f = 4 + (target_time - song_time) * self.speed
                            pu = int(pu_f)
                            if y == pu:
                                if uid_u in self.hit_tiles[json_col]:
                                    if (json_col, tile_id, 'up') in self.flash_hits: self.set_led(buffer, x, y, GREEN)
                                else:
                                    color = YELLOW if (HIT_ZONE_TOP[0] <= pu_f <= HIT_ZONE_TOP[1]) else CYAN
                                    self.set_led(buffer, x, y, color)
        return buffer

    def set_led(self, buffer, x, y, color):
        if not (0 <= x < 16 and 0 <= y < 32): return
        ch = y // 4; ri = y % 4
        idx = ri * 16 + (x if ri % 2 == 0 else 15 - x)
        off = idx * 24 + ch
        if off + 16 < len(buffer):
            buffer[off], buffer[off+8], buffer[off+16] = color[1], color[0], color[2]


# ==========================================
# 4. NETWORK MANAGER
# ==========================================
class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("0.0.0.0", UDP_PORT_RECV))
        self.recv_sock.setblocking(False)

    def run(self):
        seq = 0
        while self.game.running:
            try:
                data, _ = self.recv_sock.recvfrom(2048)
                if data and data[0] == 0x88:
                    ch8 = data[2 + (7 * 171) + 1 : 2 + (7 * 171) + 65]
                    for idx, v in enumerate(ch8): self.game.button_states[idx] = (v == 0xCC)
            except: pass
            
            self.game.process_input()
            frame = self.game.render()
            seq = (seq + 1) & 0xFFFF
            
            self.sock.sendto(bytearray([0x75, 0,0,0, 8, 2, 0,0, 0x33, 0x44, seq>>8, seq&0xFF, 0,0,0, 0x0E, 0]), (UDP_IP, UDP_PORT_SEND))
            header = bytearray([0x75, 0,0, 0x03, 0xD8, 0x02, 0,0, 0x88, 0x77, 0, 1, 0x03, 0xD8])
            self.sock.sendto(header + frame + bytearray([0x36, 0]), (UDP_IP, UDP_PORT_SEND))
            self.sock.sendto(bytearray([0x75, 0,0,0, 8, 2, 0,0, 0x55, 0x66, seq>>8, seq&0xFF, 0,0,0, 0x0E, 0]), (UDP_IP, UDP_PORT_SEND))
            time.sleep(0.04)

# ==========================================
# 5. CLI MENU
# ==========================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu(message=""):
    clear_screen()
    print("=== PIANO TILES (FULL SYNC + AUDIO) ===")
    print("Comenzi disponibile:")
    print("  1     - Pornește Mod Co-op (2x2)")
    print("  2     - Pornește Mod 1v1 (1x1)")
    print("  0     - Resetare / Oprire Joc")
    print("  score - Afișează scorul curent")
    print("  q     - Ieșire")
    print("=======================================")
    
    if message:
        print(f"\n{message}")

if __name__ == "__main__":
    game = PianoTilesEngine()
    net = NetworkManager(game)
    threading.Thread(target=net.run, daemon=True).start()
    
    print_menu(f"[OK] Sistem pregătit. Tile-uri reținute: {len(game.beatmap)}")
    
    try:
        while game.running:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q': 
                game.running = False
            elif cmd == 'score': 
                print_menu(game.get_score_report())
            elif cmd in ['1', '2']:
                game.mode = cmd
                game.is_pulsing = True
                game._reset_state()
                game.start_time = time.time()
                mode_name = "Co-op" if cmd == '1' else "1v1"
                print_menu(f"[*] Modul {mode_name} a fost pornit! Pregătește-te...")
            elif cmd == '0':
                game.mode = None
                game._reset_state()
                print_menu("[*] Jocul a fost resetat și este în așteptare.")
            else:
                print_menu("[!] Comandă necunoscută. Folosește comenzile din listă.")
                
    except KeyboardInterrupt: 
        game.running = False
    finally:
        if game.sound.enabled:
            pygame.mixer.quit()