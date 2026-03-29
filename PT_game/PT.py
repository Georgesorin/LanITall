import socket
import time
import threading
import math
import os
import json
import random
import pygame

# --- Configurație Rețea Conform Documentației ---
UDP_IP_BROADCAST = "255.255.255.255"
UDP_IP_LOCAL = "127.0.0.1"           
UDP_PORT_SEND = 1067
UDP_PORT_RECV = 1069

NUM_CHANNELS = 8
LEDS_PER_CHANNEL = 64
FRAME_DATA_LENGTH = NUM_CHANNELS * LEDS_PER_CHANNEL * 3 
WIDTH, HEIGHT = 16, 32

BEATMAP_FILE = "level.json"
AUDIO_FILE = "Nightcore - Rockefeller Street (Lyrics).mp3"

PURPLE  = (154, 66, 255)
CYAN    = (0, 255, 255)
GREEN   = (0, 255, 0)
YELLOW  = (255, 220, 0)
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GRAY    = (40, 40, 40)
LIGHT_GRAY = (200, 200, 200)

TILE_COLS_M1 = [2, 5, 9, 12]
TILE_COLS_M2 = [6, 7, 8, 9] 

HIT_ZONE_BOTTOM_COOP = (16, 31) 
HIT_ZONE_BOTTOM = (22, 31)      
HIT_ZONE_TOP    = (0, 9)        
FLASH_DURATION  = 0.20

# Pixel Art pentru Countdown
DIGITS = {
    3: [(0,0), (1,0), (2,0), (2,1), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
    2: [(0,0), (1,0), (2,0), (2,1), (1,2), (0,2), (0,3), (0,4), (1,4), (2,4)],
    1: [(1,0), (1,1), (1,2), (1,3), (1,4), (0,1)]
}

class PianoTilesEngine:
    def __init__(self):
        self.running = True
        self.mode = None       
        self.start_time = 0
        self.is_pulsing = False
        self.speed = 15 
        self.game_over = False
        self.song_duration = 0
        self.stars = []

        self.button_states = [False] * 512
        self.prev_button_states = [False] * 512

        self.display_matrix = [[BLACK for _ in range(WIDTH)] for _ in range(HEIGHT)]

        self.audio_enabled = False
        self.music_playing = False
        try:
            pygame.mixer.init()
            self.audio_enabled = True
        except pygame.error as e:
            print(f" Nu s-a putut initializa audio: {e}")

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
                    self.beatmap = data[::1]
                    if self.beatmap:
                        self.song_duration = max(t['time'] for t in self.beatmap)
        except Exception:
            pass

    def _reset_state(self):
        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {}
        self.score_p1 = 0; self.misses_p1 = 0
        self.score_p2 = 0; self.misses_p2 = 0
        self.game_over = False
        
        self.stars = []
        for _ in range(25):
            self.stars.append([
                random.uniform(0, WIDTH), 
                random.uniform(0, HEIGHT), 
                random.uniform(2, 6),
                random.uniform(0, math.pi * 2)
            ])
        
        if self.audio_enabled and self.music_playing:
            pygame.mixer.music.stop()
            self.music_playing = False

    def process_inputs(self):
        if self.mode is None or self.is_pulsing or self.game_over:
            self.prev_button_states = list(self.button_states)
            return
            
        t = time.time()
        active_cols = TILE_COLS_M1 if self.mode == '1' else TILE_COLS_M2
        
        for i in range(512):
            if self.button_states[i] and not self.prev_button_states[i]:
                channel, local = i // 64, i % 64
                row, col_raw = local // 16, local % 16
                x = col_raw if row % 2 == 0 else 15 - col_raw
                y = (channel * 4) + row
                
                target_col_idx = None
                
                if self.mode == '1':
                    for idx, ac in enumerate(active_cols):
                        if ac - 1 <= x <= ac + 2:
                            target_col_idx = idx
                            break
                else:
                    if x in active_cols:
                        target_col_idx = active_cols.index(x)
                    else:
                        for idx, ac in enumerate(active_cols):
                            if abs(x - ac) == 1:
                                target_col_idx = idx
                                break
                            
                if target_col_idx is not None:
                    self._try_hit(target_col_idx, t, y) 
                    
        self.prev_button_states = list(self.button_states)

    def _try_hit(self, col, current_t, press_y):
        song_time = current_t - self.start_time
        best_t1 = None; min_diff_1 = 999
        best_d  = None; min_diff_d = 999
        best_u  = None; min_diff_u = 999

        is_top_half = (press_y < 16)
        is_bottom_half = (press_y >= 16)

        for tile_id, tile in enumerate(self.beatmap):
            if tile['column'] != col: continue
            target_time = tile['time']
            time_diff = abs(song_time - target_time)

            if self.mode == '1':
                if time_diff > 0.6: continue 
                if is_bottom_half and tile_id not in self.hit_tiles[col]:
                    py = int(32 - (target_time - song_time) * self.speed)
                    if HIT_ZONE_BOTTOM_COOP[0] <= py <= HIT_ZONE_BOTTOM_COOP[1]:
                        if time_diff < min_diff_1:
                            min_diff_1 = time_diff; best_t1 = tile_id
                            
            elif self.mode == '2':
                if time_diff > 0.4: continue 
                
                if is_bottom_half:
                    uid_d = f"d_{tile_id}"
                    if uid_d not in self.hit_tiles[col]:
                        pd = int(25 - (target_time - song_time) * self.speed)
                        if HIT_ZONE_BOTTOM[0] <= pd <= HIT_ZONE_BOTTOM[1]:
                            if time_diff < min_diff_d:
                                min_diff_d = time_diff; best_d = tile_id
                                
                if is_top_half:
                    uid_u = f"u_{tile_id}"
                    if uid_u not in self.hit_tiles[col]:
                        pu = int(3 + (target_time - song_time) * self.speed)
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

        if self.mode is None or self.is_pulsing or self.game_over: return
        song_time = t - self.start_time

        if self.song_duration > 0 and song_time > self.song_duration + 3.0: 
            self.game_over = True
            return

        for tile_id, tile in enumerate(self.beatmap):
            allowance = 0.6 if self.mode == '1' else 0.4
            if song_time > tile['time'] + allowance:
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

    def draw_digit(self, buffer, digit, offset_x, offset_y, color, scale=2):
        if digit in DIGITS:
            for dx, dy in DIGITS[digit]:
                for sx in range(scale):
                    for sy in range(scale):
                        self.set_pixel(buffer, offset_x + (dx * scale) + sx, offset_y + (dy * scale) + sy, *color)

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)
        t = time.time()
        self._update_logic()

        if self.game_over:
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    self.set_pixel(buffer, x, y, *BLACK)
                    
            for star in self.stars:
                star[0] -= star[2] * 0.05
                if star[0] < 0:
                    star[0] = WIDTH
                    star[1] = random.uniform(0, HEIGHT)
                
                x, y = int(star[0]), int(star[1])
                brightness = int(127 + 127 * math.sin(t * 8 + star[3]))
                self.set_pixel(buffer, x, y, brightness, brightness, brightness)
                if x + 1 < WIDTH:
                    self.set_pixel(buffer, x + 1, y, int(brightness*0.3), int(brightness*0.3), int(brightness*0.3))
            return buffer

        if self.mode and self.is_pulsing:
            elapsed = t - self.start_time
            
            # --- NUMĂRĂTOAREA INVERSĂ (5 secunde total) ---
            # 0-2 secunde: Pulsul mov de pregătire
            # 2-3 secunde: "3"
            # 3-4 secunde: "2"
            # 4-5 secunde: "1"
            
            if elapsed > 5.0: 
                self.is_pulsing = False
                self.start_time = time.time() 
                
                if self.audio_enabled and not self.music_playing:
                    try:
                        if os.path.exists(AUDIO_FILE):
                            pygame.mixer.music.load(AUDIO_FILE)
                            pygame.mixer.music.play()
                            self.music_playing = True
                    except Exception: pass
                    
            # Randăm matricea neagră ca bază pentru countdown
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    self.set_pixel(buffer, x, y, *BLACK)
                    
            if elapsed < 2.0:
                # Arată frame-ul mov care pulsează
                for y in range(HEIGHT):
                    for x in range(WIDTH):
                        is_frame = (y < 2 or y >= HEIGHT - 2)
                        if self.mode == '2' and (y == 15 or y == 16): is_frame = True
                        if is_frame:
                            f = 0.7 + 0.3 * math.sin(t * 12)
                            c = tuple(int(ch*f) for ch in PURPLE)
                            self.set_pixel(buffer, x, y, c[0], c[1], c[2])
            elif 2.0 <= elapsed < 3.0:
                self.draw_digit(buffer, 3, 5, 11, WHITE, scale=2)
            elif 3.0 <= elapsed < 4.0:
                self.draw_digit(buffer, 2, 5, 11, WHITE, scale=2)
            elif 4.0 <= elapsed < 5.0:
                self.draw_digit(buffer, 1, 5, 11, WHITE, scale=2)
                
            return buffer

        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self.mode is None:
                    self.set_pixel(buffer, x, y, int(127+127*math.sin(t*2+y*0.3)), 50, 200)
                    continue

                is_frame = (y < 2 or y >= HEIGHT - 2)
                if self.mode == '2' and (y == 15 or y == 16): is_frame = True
                if is_frame:
                    self.set_pixel(buffer, x, y, PURPLE[0], PURPLE[1], PURPLE[2])
                    continue

                self.set_pixel(buffer, x, y, *BLACK)

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
                        
                        if y == py:
                            if tile_id in self.hit_tiles[json_col]:
                                if (json_col, tile_id, 'down') in self.flash_hits: 
                                    self.set_pixel(buffer, x, y, *GREEN)
                            else:
                                color = YELLOW if (HIT_ZONE_BOTTOM_COOP[0] <= py_f <= HIT_ZONE_BOTTOM_COOP[1]) else CYAN
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
        if target_x < 0 or target_x >= WIDTH or target_y < 0 or target_y >= HEIGHT: return
        self.display_matrix[target_y][target_x] = (r, g, b)
        channel = target_y // 4
        if channel >= NUM_CHANNELS: return
        row = target_y % 4
        idx = (row * 16 + target_x) if row % 2 == 0 else (row * 16 + (15 - target_x))
        offset = idx * 24 + channel 
        if offset + 16 < len(buffer):
            buffer[offset] = g      
            buffer[offset + 8] = r
            buffer[offset + 16] = b


# --- NETWORK MANAGER ---
class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_send.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        self.sequence_number = 0
        
        try:
            self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_recv.bind(("0.0.0.0", UDP_PORT_RECV))
        except Exception as e:
            print(f"[EROARE] Nu s-a putut lega portul de intrare {UDP_PORT_RECV}: {e}")
            self.running = False

    def send_loop(self):
        while self.running and self.game.running:
            self.game.process_inputs()
            frame = self.game.render()
            self.send_packet(frame)
            time.sleep(0.05) 

    def send_packet(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1
        port = UDP_PORT_SEND
        
        rand1 = random.randint(0, 127)
        rand2 = random.randint(0, 127)
        start_packet = bytearray([
            0x75, rand1, rand2, 0x00, 0x08, 
            0x02, 0x00, 0x00, 0x33, 0x44,   
            (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF,
            0x00, 0x00, 0x00 
        ])
        start_packet.append(0x0E) 
        start_packet.append(0x00) 
        try: 
            self.sock_send.sendto(start_packet, (UDP_IP_BROADCAST, port))
            self.sock_send.sendto(start_packet, (UDP_IP_LOCAL, port))
        except: pass

        fff0_payload = bytearray()
        for _ in range(NUM_CHANNELS):
            fff0_payload += bytes([(LEDS_PER_CHANNEL >> 8) & 0xFF, LEDS_PER_CHANNEL & 0xFF])

        fff0_internal = bytearray([
            0x02, 0x00, 0x00, 0x88, 0x77, 0xFF, 0xF0, 
            (len(fff0_payload) >> 8) & 0xFF, (len(fff0_payload) & 0xFF)
        ]) + fff0_payload
        
        fff0_len = len(fff0_internal) - 1
        fff0_packet = bytearray([
            0x75, rand1, rand2, (fff0_len >> 8) & 0xFF, (fff0_len & 0xFF)
        ]) + fff0_internal
        fff0_packet.append(0x1E) 
        fff0_packet.append(0x00) 
        try: 
            self.sock_send.sendto(fff0_packet, (UDP_IP_BROADCAST, port))
            self.sock_send.sendto(fff0_packet, (UDP_IP_LOCAL, port))
        except: pass
        
        chunk_size = 984 
        data_packet_index = 1
        
        for i in range(0, len(frame_data), chunk_size):
            chunk = frame_data[i:i+chunk_size]
            internal_data = bytearray([
                0x02, 0x00, 0x00, 
                (0x8877 >> 8) & 0xFF, (0x8877 & 0xFF), 
                (data_packet_index >> 8) & 0xFF, (data_packet_index & 0xFF), 
                (len(chunk) >> 8) & 0xFF, (len(chunk) & 0xFF) 
            ]) + chunk
            
            payload_len = len(internal_data) - 1 
            packet = bytearray([
                0x75, rand1, rand2, (payload_len >> 8) & 0xFF, (payload_len & 0xFF)
            ]) + internal_data
            
            if len(chunk) == 984: packet.append(0x1E) 
            else: packet.append(0x36) 
            packet.append(0x00)
            try: 
                self.sock_send.sendto(packet, (UDP_IP_BROADCAST, port))
                self.sock_send.sendto(packet, (UDP_IP_LOCAL, port))
            except: pass
            
            data_packet_index += 1
            time.sleep(0.005) 

        end_packet = bytearray([
            0x75, rand1, rand2, 0x00, 0x08,
            0x02, 0x00, 0x00, 0x55, 0x66,
            (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF,
            0x00, 0x00, 0x00 
        ])
        end_packet.append(0x0E) 
        end_packet.append(0x00) 
        try: 
            self.sock_send.sendto(end_packet, (UDP_IP_BROADCAST, port))
            self.sock_send.sendto(end_packet, (UDP_IP_LOCAL, port))
        except: pass

    def listen_loop(self):
        while self.running and self.game.running:
            try:
                data, _ = self.sock_recv.recvfrom(2048)
                if len(data) >= 1373 and data[0] == 0x88:
                    for ch in range(8):
                        offset = 2 + (ch * 171) + 1 
                        ch_data = data[offset : offset + 64] 
                        for led_idx, val in enumerate(ch_data):
                            global_idx = (ch * 64) + led_idx
                            self.game.button_states[global_idx] = (val == 0xCC)
            except Exception: pass

    def start_bg(self):
        t1 = threading.Thread(target=self.send_loop, daemon=True)
        t2 = threading.Thread(target=self.listen_loop, daemon=True)
        t1.start()
        t2.start()


# --- GUI PYGAME ---
class VisualInterface:
    def __init__(self, game):
        self.game = game
        pygame.init()
        
        self.cell_size = 20
        self.grid_w = WIDTH * self.cell_size
        self.grid_h = HEIGHT * self.cell_size
        self.panel_w = 300
        
        self.screen = pygame.display.set_mode((self.grid_w + self.panel_w, self.grid_h))
        pygame.display.set_caption("Matrix Piano Tiles - Control Panel")
        
        self.font_large = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI", 16)
        self.clock = pygame.time.Clock()

    def draw_text(self, text, font, color, x, y):
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def run(self):
        while self.game.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.game.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.game.mode = '1'
                        self.game.speed = 7      
                        self.game.is_pulsing = True
                        self.game._reset_state()
                        self.game.start_time = time.time()
                    elif event.key == pygame.K_2:
                        self.game.mode = '2'
                        self.game.speed = 12     
                        self.game.is_pulsing = True
                        self.game._reset_state()
                        self.game.start_time = time.time()
                    elif event.key == pygame.K_0:
                        self.game.mode = None
                        self.game._reset_state()
                    elif event.key == pygame.K_q:
                        self.game.running = False

            self.screen.fill((20, 20, 20))

            for y in range(HEIGHT):
                for x in range(WIDTH):
                    color = self.game.display_matrix[y][x]
                    rect = (x * self.cell_size, y * self.cell_size, self.cell_size - 1, self.cell_size - 1)
                    pygame.draw.rect(self.screen, color, rect)
                    
            pygame.draw.line(self.screen, GRAY, (self.grid_w, 0), (self.grid_w, self.grid_h), 2)

            px = self.grid_w + 20
            self.draw_text("PIANO TILES MATRIX", self.font_large, CYAN, px, 20)
            
            mode_str = "Co-op (2x2)" if self.game.mode == '1' else "1v1 (1x1)" if self.game.mode == '2' else "Așteptare"
            self.draw_text(f"Status: {mode_str}", self.font_small, YELLOW, px, 60)
            self.draw_text(f"Tiles Rămase/Total: {len(self.game.beatmap)}", self.font_small, WHITE, px, 85)

            if self.game.mode == '1':
                self.draw_text("Scor CO-OP:", self.font_large, GREEN, px, 140)
                self.draw_text(f"Hits: {self.game.score_p2}", self.font_small, WHITE, px, 180)
                self.draw_text(f"Misses: {self.game.misses_p2}", self.font_small, WHITE, px, 205)
                
                missed_p2_list = [t for col in self.game.miss_tiles.values() for t in col]
                if missed_p2_list:
                    self.draw_text("Tile-uri ratate (ID):", self.font_small, (255, 100, 100), px, 240)
                    self.draw_text(str(sorted(missed_p2_list)[:15]) + ("..." if len(missed_p2_list)>15 else ""), self.font_small, WHITE, px, 260)

            elif self.game.mode == '2':
                self.draw_text("Scor P1 (Sus):", self.font_large, PURPLE, px, 140)
                self.draw_text(f"Hits: {self.game.score_p1} | Misses: {self.game.misses_p1}", self.font_small, WHITE, px, 180)
                missed_p1_list = sorted([int(t.split('_')[1]) for col in self.game.miss_tiles.values() for t in col if str(t).startswith('u_')])
                if missed_p1_list: self.draw_text(f"Ratări: {str(missed_p1_list[:10])}", self.font_small, WHITE, px, 205)

                self.draw_text("Scor P2 (Jos):", self.font_large, CYAN, px, 250)
                self.draw_text(f"Hits: {self.game.score_p2} | Misses: {self.game.misses_p2}", self.font_small, WHITE, px, 290)
                missed_p2_list = sorted([int(t.split('_')[1]) for col in self.game.miss_tiles.values() for t in col if str(t).startswith('d_')])
                if missed_p2_list: self.draw_text(f"Ratări: {str(missed_p2_list[:10])}", self.font_small, WHITE, px, 315)

            if self.game.game_over:
                self.draw_text("SONG COMPLETE!", self.font_large, YELLOW, px, 370)

            self.draw_text("Comenzi Tastatură:", self.font_large, WHITE, px, 450)
            self.draw_text("[1] - Start Mod Co-op", self.font_small, LIGHT_GRAY, px, 490)
            self.draw_text("[2] - Start Mod 1v1", self.font_small, LIGHT_GRAY, px, 515)
            self.draw_text("[0] - Oprește / Așteptare", self.font_small, LIGHT_GRAY, px, 540)
            self.draw_text("[Q] - Închide Aplicația", self.font_small, LIGHT_GRAY, px, 565)
            
            pygame.display.flip()
            self.clock.tick(30) 

if __name__ == "__main__":
    game = PianoTilesEngine()
    net = NetworkManager(game)
    
    net.start_bg()
    
    try:
        gui = VisualInterface(game)
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        game.running = False
        net.running = False
        if game.audio_enabled:
            pygame.mixer.quit()
        pygame.quit()