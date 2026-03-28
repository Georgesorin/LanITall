import socket
import time
import threading
import math
import os
import json
import pygame

# --- Configurație Rețea Conform Documentației ---
UDP_IP = "127.0.0.1"
UDP_PORT_SEND = 4626 # Portul oficial de trimitere Matrix
UDP_PORT_RECV = 7800 # Portul oficial de primire touch-events

# Structura hardware
NUM_CHANNELS = 8
LEDS_PER_CHANNEL = 64
FRAME_DATA_LENGTH = NUM_CHANNELS * LEDS_PER_CHANNEL * 3 
WIDTH, HEIGHT = 16, 32

# --- Configurație Fișiere ---
BEATMAP_FILE = "level.json"
AUDIO_FILE = "Rockefeller Street, Nightcore Version (8-bitRockDrum & Bass) Remix.mp3"

# --- Culori ---
PURPLE  = (154, 66, 255)
CYAN    = (0, 255, 255)
GREEN   = (0, 255, 0)
YELLOW  = (255, 220, 0)
BLACK   = (0, 0, 0)

# --- Configurație Moduri Piano Tiles ---
TILE_COLS_M1 = [2, 5, 9, 12]
TILE_COLS_M2 = [6, 7, 8, 9] 

HIT_ZONE_BOTTOM = (24, 29)
HIT_ZONE_TOP    = (2, 7)
FLASH_DURATION  = 0.20

# --- Securitate Matrix (Checksum Array) ---
PASSWORD_ARRAY = [
    35, 63, 187, 69, 107, 178, 92, 76, 39, 69, 205, 37, 223, 255, 165, 231, 16, 220, 99, 61, 25, 203, 203, 155, 107, 30, 92, 144, 218, 194, 226, 88, 196, 190, 67, 195, 159, 185, 209, 24, 163, 65, 25, 172, 126, 63, 224, 61, 160, 80, 125, 91, 239, 144, 25, 141, 183, 204, 171, 188, 255, 162, 104, 225, 186, 91, 232, 3, 100, 208, 49, 211, 37, 192, 20, 99, 27, 92, 147, 152, 86, 177, 53, 153, 94, 177, 200, 33, 175, 195, 15, 228, 247, 18, 244, 150, 165, 229, 212, 96, 84, 200, 168, 191, 38, 112, 171, 116, 121, 186, 147, 203, 30, 118, 115, 159, 238, 139, 60, 57, 235, 213, 159, 198, 160, 50, 97, 201, 253, 242, 240, 77, 102, 12, 183, 235, 243, 247, 75, 90, 13, 236, 56, 133, 150, 128, 138, 190, 140, 13, 213, 18, 7, 117, 255, 45, 69, 214, 179, 50, 28, 66, 123, 239, 190, 73, 142, 218, 253, 5, 212, 174, 152, 75, 226, 226, 172, 78, 35, 93, 250, 238, 19, 32, 247, 223, 89, 123, 86, 138, 150, 146, 214, 192, 93, 152, 156, 211, 67, 51, 195, 165, 66, 10, 10, 31, 1, 198, 234, 135, 34, 128, 208, 200, 213, 169, 238, 74, 221, 208, 104, 170, 166, 36, 76, 177, 196, 3, 141, 167, 127, 56, 177, 203, 45, 107, 46, 82, 217, 139, 168, 45, 198, 6, 43, 11, 57, 88, 182, 84, 189, 29, 35, 143, 138, 171
]

def calc_checksum(data: bytes) -> int:
    """Calculează indexul de paritate validând buffer-ul."""
    idx = sum(data) & 0xFF
    return PASSWORD_ARRAY[idx]


class PianoTilesEngine:
    def __init__(self):
        self.running = True
        self.mode = None       
        self.start_time = 0
        self.is_pulsing = False
        self.speed = 5 

        self.button_states = [False] * 64
        self.prev_button_states = [False] * 64

        self.audio_enabled = False
        self.music_playing = False
        try:
            pygame.mixer.init()
            self.audio_enabled = True
        except pygame.error as e:
            print(f"[AVERTISMENT] Nu s-a putut inițializa audio: {e}")

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
        except Exception:
            pass

    def _reset_state(self):
        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {}
        self.score_p1 = 0; self.misses_p1 = 0
        self.score_p2 = 0; self.misses_p2 = 0
        
        if self.audio_enabled and self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False

    def get_score_report(self):
        if self.mode == '1':
            missed_p2_list = [tile for col in self.miss_tiles.values() for tile in col]
            return (f"\n--- SCOR CO-OP ---\n"
                    f"Hits: {self.score_p2}\n"
                    f"Misses: {self.misses_p2}\n"
                    f"Tile-uri ratate (ID-uri): {sorted(missed_p2_list)}\n"
                    f"------------------")
        elif self.mode == '2':
            missed_p1_list = [t for col in self.miss_tiles.values() for t in col if str(t).startswith('u_')]
            missed_p2_list = [t for col in self.miss_tiles.values() for t in col if str(t).startswith('d_')]
            return (f"\n--- SCOR 1v1 ---\n"
                    f"P1 (SUS): {self.score_p1} Hits | {self.misses_p1} Misses\n"
                    f"  -> Tile-uri ratate: {sorted([int(t.split('_')[1]) for t in missed_p1_list])}\n"
                    f"P2 (JOS): {self.score_p2} Hits | {self.misses_p2} Misses\n"
                    f"  -> Tile-uri ratate: {sorted([int(t.split('_')[1]) for t in missed_p2_list])}\n"
                    f"-----------------")
        return "Jocul este în așteptare."

    def process_inputs(self):
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
        best_t1 = None; min_diff_1 = 999
        best_d  = None; min_diff_d = 999
        best_u  = None; min_diff_u = 999

        for tile_id, tile in enumerate(self.beatmap):
            if tile['column'] != col: continue
            target_time = tile['time']
            time_diff = abs(song_time - target_time)
            
            if time_diff > 0.3: continue 

            if self.mode == '1':
                if tile_id not in self.hit_tiles[col]:
                    py = int(27 - (target_time - song_time) * self.speed)
                    if HIT_ZONE_BOTTOM[0] <= py <= HIT_ZONE_BOTTOM[1]:
                        if time_diff < min_diff_1:
                            min_diff_1 = time_diff; best_t1 = tile_id
                            
            elif self.mode == '2':
                uid_d = f"d_{tile_id}"
                if uid_d not in self.hit_tiles[col]:
                    pd = int(27 - (target_time - song_time) * self.speed)
                    if HIT_ZONE_BOTTOM[0] <= pd <= HIT_ZONE_BOTTOM[1]:
                        if time_diff < min_diff_d:
                            min_diff_d = time_diff; best_d = tile_id
                            
                uid_u = f"u_{tile_id}"
                if uid_u not in self.hit_tiles[col]:
                    pu = int(4 + (target_time - song_time) * self.speed)
                    if HIT_ZONE_TOP[0] <= pu <= HIT_ZONE_TOP[1]:
                        if time_diff < min_diff_u:
                            min_diff_u = time_diff; best_u = tile_id

        if self.mode == '1' and best_t1 is not None:
            self.hit_tiles[col].add(best_t1)
            self.flash_hits[(col, best_t1, 'down')] = current_t
            self.score_p2 += 1 
            
        elif self.mode == '2':
            if best_d is not None:
                self.hit_tiles[col].add(f"d_{best_d}")
                self.flash_hits[(col, best_d, 'down')] = current_t
                self.score_p2 += 1
            if best_u is not None:
                self.hit_tiles[col].add(f"u_{best_u}")
                self.flash_hits[(col, best_u, 'up')] = current_t
                self.score_p1 += 1

    def _update_logic(self):
        t = time.time()
        expired = [k for k, start_t in self.flash_hits.items() if t - start_t > FLASH_DURATION]
        for k in expired: del self.flash_hits[k]

        if self.mode is None or self.is_pulsing: return
        song_time = t - self.start_time

        for tile_id, tile in enumerate(self.beatmap):
            if song_time > tile['time'] + 0.3:
                col = tile['column']
                if self.mode == '1':
                    if tile_id not in self.hit_tiles[col] and tile_id not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(tile_id); self.misses_p2 += 1
                elif self.mode == '2':
                    uid_d = f"d_{tile_id}"
                    if uid_d not in self.hit_tiles[col] and uid_d not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(uid_d); self.misses_p2 += 1
                    uid_u = f"u_{tile_id}"
                    if uid_u not in self.hit_tiles[col] and uid_u not in self.miss_tiles[col]:
                        self.miss_tiles[col].add(uid_u); self.misses_p1 += 1

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)
        t = time.time()
        self._update_logic()

        if self.mode and self.is_pulsing:
            if t - self.start_time > 2.0: 
                self.is_pulsing = False
                self.start_time = time.time() 
                
                if self.audio_enabled and not self.music_playing:
                    try:
                        if os.path.exists(AUDIO_FILE):
                            pygame.mixer.music.load(AUDIO_FILE)
                            pygame.mixer.music.play()
                            self.music_playing = True
                    except Exception: pass

        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self.mode is None:
                    self.set_pixel(buffer, x, y, int(127+127*math.sin(t*2+y*0.3)), 50, 200)
                    continue

                is_frame = (y < 2 or y >= HEIGHT - 2)
                if self.mode == '2' and (y == 15 or y == 16): is_frame = True
                if is_frame:
                    c = PURPLE
                    if self.is_pulsing:
                        f = 0.7 + 0.3 * math.sin(t * 12)
                        c = tuple(int(ch*f) for ch in PURPLE)
                    self.set_pixel(buffer, x, y, c[0], c[1], c[2])
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
                                    self.set_pixel(buffer, x, y, *GREEN)
                            else:
                                color = YELLOW if (HIT_ZONE_BOTTOM[0] <= py_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                self.set_pixel(buffer, x, y, *color)
                                
                    elif self.mode == '2':
                        if x != sx: continue 
                        
                        uid_d = f"d_{tile_id}"
                        if uid_d not in self.miss_tiles[json_col]:
                            pd_f = 27 - (target_time - song_time) * self.speed
                            pd = int(pd_f)
                            
                            if pd > 16 and y == pd:
                                if uid_d in self.hit_tiles[json_col]:
                                    if (json_col, tile_id, 'down') in self.flash_hits: 
                                        self.set_pixel(buffer, x, y, *GREEN)
                                else:
                                    color = YELLOW if (HIT_ZONE_BOTTOM[0] <= pd_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                    self.set_pixel(buffer, x, y, *color)
                                    
                        uid_u = f"u_{tile_id}"
                        if uid_u not in self.miss_tiles[json_col]:
                            pu_f = 4 + (target_time - song_time) * self.speed
                            pu = int(pu_f)
                            
                            if pu < 15 and y == pu:
                                if uid_u in self.hit_tiles[json_col]:
                                    if (json_col, tile_id, 'up') in self.flash_hits: 
                                        self.set_pixel(buffer, x, y, *GREEN)
                                else:
                                    color = YELLOW if (HIT_ZONE_TOP[0] <= pu_f <= HIT_ZONE_TOP[1]) else CYAN
                                    self.set_pixel(buffer, x, y, *color)
        return buffer

    def set_pixel(self, buffer, target_x, target_y, r, g, b):
        """Scrierea datelor de ecran per pixel, respectând aliniamentul Zig-Zag GRB (Secțiunea 2)."""
        if target_x < 0 or target_x >= WIDTH or target_y < 0 or target_y >= HEIGHT: return
        channel = target_y // 4
        if channel >= NUM_CHANNELS: return
        
        row = target_y % 4
        idx = (row * 16 + target_x) if row % 2 == 0 else (row * 16 + (15 - target_x))
        
        offset = idx * 24 + channel 
        if offset + 16 < len(buffer):
            buffer[offset] = g      
            buffer[offset + 8] = r
            buffer[offset + 16] = b


# --- NETWORK MANAGER (Actualizat pentru Port 4626/7800 și Verificare Paritate) ---
class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        
        try:
            self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Secțiunea 4: Receptorul ascultă exclusiv portul 7800
            self.sock_recv.bind(("0.0.0.0", UDP_PORT_RECV))
        except Exception as e:
            print(f"[EROARE] Nu s-a putut lega portul de intrare {UDP_PORT_RECV}: {e}")
            self.running = False

    def _transmit_payload(self, payload: bytes):
        """Aplică Checksum-ul dinamic la finalul payload-ului (Secțiunea 1)"""
        chk = calc_checksum(payload)
        packet = payload + bytes([chk])
        try:
            self.sock_send.sendto(packet, (UDP_IP, UDP_PORT_SEND))
        except Exception:
            pass

    def send_loop(self):
        """Ciclul de trimitere, izolând pachetele cu Chunking de 984 bytes și delay (Secțiunea 3)"""
        while self.running and self.game.running:
            self.game.process_inputs()
            frame = self.game.render()
            
            self._transmit_payload(b"start")
            self._transmit_payload(b"fff0")
            
            for i in range(0, len(frame), 984):
                chunk = frame[i:i+984]
                self._transmit_payload(b"data" + chunk)
                time.sleep(0.002) # Sub-chunk delay strict 2ms conform documentației
                
            self._transmit_payload(b"end")
            time.sleep(0.03) # Menținem un delay adițional minimal pentru frame-rate (aprox 30 FPS)

    def listen_loop(self):
        """Buclează constant așteptând interacțiunile fizice (Touch Matrix) (Secțiunea 4)"""
        while self.running and self.game.running:
            try:
                data, _ = self.sock_recv.recvfrom(2048)
                # Parsează doar pachetele corecte (lungime 1400, header 0x88)
                if len(data) == 1400 and data[0] == 0x88:
                    offset = 1200
                    for i in range(64):
                        # Înregistrăm atingerea dacă flag-ul 0xCC este validat pe index
                        self.game.button_states[i] = (data[offset + i] == 0xCC)
            except Exception:
                pass

    def start_bg(self):
        """Rulează procesele strict în background de tip Daemon (Secțiunea 6)"""
        t1 = threading.Thread(target=self.send_loop, daemon=True)
        t2 = threading.Thread(target=self.listen_loop, daemon=True)
        t1.start()
        t2.start()


# --- Interfața din Terminal ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu(message=""):
    clear_screen()
    print("=== PIANO TILES (MATRIX SYNC) ===")
    print("Comenzi disponibile:")
    print("  1     - Pornește Mod Co-op (2x2)")
    print("  2     - Pornește Mod 1v1 (1x1)")
    print("  0     - Resetare / Oprire Joc")
    print("  score - Afișează scorul curent")
    print("  q     - Ieșire")
    print("=================================")
    
    if message:
        print(f"\n{message}")

if __name__ == "__main__":
    game = PianoTilesEngine()
    net = NetworkManager(game)
    net.start_bg()
    
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
        net.running = False
        if game.audio_enabled:
            pygame.mixer.quit()