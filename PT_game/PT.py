import socket
import time
import threading
import math
import os

# --- Configurație Rețea ---
UDP_IP = "127.0.0.1"
UDP_PORT_SEND = 1067
UDP_PORT_RECV = 1069
WIDTH, HEIGHT = 16, 32
FRAME_DATA_LENGTH = 8 * 64 * 3

# Culori
PURPLE  = (154, 66, 255)
CYAN    = (0, 255, 255)
GREEN   = (0, 255, 0)
YELLOW  = (255, 220, 0)
BLACK   = (0, 0, 0)

# Configurație Mod 1 (2x2)
TILE_COLS_M1 = [2, 5, 9, 12]
# Configurație Mod 2 (1x1 central)
TILE_COLS_M2 = [6, 7, 8, 9] 

HIT_ZONE_BOTTOM = (26, 29)
HIT_ZONE_TOP    = (2, 5)
FLASH_DURATION  = 0.15

class PianoTilesEngine:
    def __init__(self):
        self.running = True
        self.mode = None       
        self.start_time = 0
        self.is_pulsing = False
        self.speed = 8

        self.button_states = [False] * 64
        self.prev_button_states = [False] * 64

        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {} 

        self.score_p1 = 0; self.misses_p1 = 0
        self.score_p2 = 0; self.misses_p2 = 0

    def _reset_state(self):
        self.hit_tiles = {i: set() for i in range(4)}
        self.miss_tiles = {i: set() for i in range(4)}
        self.flash_hits = {}
        self.score_p1 = 0; self.misses_p1 = 0
        self.score_p2 = 0; self.misses_p2 = 0

    def _get_tile_info(self, col_idx, t, mode):
        if mode == '1':
            raw = (t * self.speed + col_idx * 6)
            return (raw % HEIGHT), int(raw // HEIGHT)
        elif mode == 'up': 
            raw = (t * self.speed + col_idx * 4)
            return (14 - (raw % 13)), int(raw // 13)
        elif mode == 'down': 
            raw = (t * self.speed + col_idx * 4)
            return (17 + (raw % 13)), int(raw // 13)
        return 0, 0

    def process_input(self):
        if self.mode is None or self.is_pulsing:
            self.prev_button_states = list(self.button_states)
            return
        t = time.time()
        for i in range(64):
            if self.button_states[i] and not self.prev_button_states[i]:
                # Mapare: butoanele din simulator pe coloane 0-3
                col = i % 4 
                self._try_hit(col, t)
        self.prev_button_states = list(self.button_states)

    def _try_hit(self, col, t):
        if self.mode == '1':
            py, tid = self._get_tile_info(col, t, '1')
            if tid not in self.hit_tiles[col] and HIT_ZONE_BOTTOM[0] <= py <= HIT_ZONE_BOTTOM[1]:
                self.hit_tiles[col].add(tid)
                self.flash_hits[(col, tid, 'down')] = t
                self.score_p2 += 1 

        elif self.mode == '2':
            # Verifică Player Jos (P2)
            pd, tid_d = self._get_tile_info(col, t, 'down')
            if tid_d not in self.hit_tiles[col] and HIT_ZONE_BOTTOM[0] <= pd <= HIT_ZONE_BOTTOM[1]:
                # Folosim un prefix 'd_' pentru ID-uri ca să nu se bată cu cele de sus
                unique_id = f"d_{tid_d}"
                if unique_id not in self.hit_tiles[col]:
                    self.hit_tiles[col].add(unique_id)
                    self.flash_hits[(col, tid_d, 'down')] = t
                    self.score_p2 += 1
                    return
            
            # Verifică Player Sus (P1)
            pu, tid_u = self._get_tile_info(col, t, 'up')
            if tid_u not in self.hit_tiles[col] and HIT_ZONE_TOP[0] <= pu <= HIT_ZONE_TOP[1]:
                unique_id = f"u_{tid_u}"
                if unique_id not in self.hit_tiles[col]:
                    self.hit_tiles[col].add(unique_id)
                    self.flash_hits[(col, tid_u, 'up')] = t
                    self.score_p1 += 1

    def _update_logic(self):
        t = time.time()
        expired = [k for k, start_t in self.flash_hits.items() if t - start_t > FLASH_DURATION]
        for k in expired: del self.flash_hits[k]

        if self.mode == '1':
            for i in range(4):
                py, tid = self._get_tile_info(i, t, '1')
                if py > HIT_ZONE_BOTTOM[1] + 0.5:
                    if tid not in self.hit_tiles[i] and tid not in self.miss_tiles[i]:
                        self.miss_tiles[i].add(tid); self.misses_p2 += 1
        elif self.mode == '2':
            for i in range(4):
                # Miss Jos
                pd, tid_d = self._get_tile_info(i, t, 'down')
                uid_d = f"d_{tid_d}"
                if pd > HIT_ZONE_BOTTOM[1] + 0.5:
                    if uid_d not in self.hit_tiles[i] and uid_d not in self.miss_tiles[i]:
                        self.miss_tiles[i].add(uid_d); self.misses_p2 += 1
                # Miss Sus
                pu, tid_u = self._get_tile_info(i, t, 'up')
                uid_u = f"u_{tid_u}"
                if pu < HIT_ZONE_TOP[0] - 0.5:
                    if uid_u not in self.hit_tiles[i] and uid_u not in self.miss_tiles[i]:
                        self.miss_tiles[i].add(uid_u); self.misses_p1 += 1

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)
        t = time.time()
        self._update_logic()

        if self.mode and self.is_pulsing:
            if t - self.start_time > 2.0: self.is_pulsing = False

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

                # TILE RENDERING
                active_cols = TILE_COLS_M1 if self.mode == '1' else TILE_COLS_M2
                for i, sx in enumerate(active_cols):
                    if self.mode == '1':
                        if not (sx <= x <= sx + 1): continue
                        py_f, tid = self._get_tile_info(i, t, '1')
                        if int(py_f) <= y <= int(py_f) + 1 and tid not in self.miss_tiles[i]:
                            if tid in self.hit_tiles[i]:
                                if (i, tid, 'down') in self.flash_hits: self.set_led(buffer, x, y, GREEN)
                            else:
                                color = YELLOW if (HIT_ZONE_BOTTOM[0] <= py_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                self.set_led(buffer, x, y, color)
                    else: # Mod 2 (1x1)
                        if x != sx: continue
                        # Jucator JOS (P2)
                        pd_f, tid_d = self._get_tile_info(i, t, 'down')
                        if y == int(pd_f) and f"d_{tid_d}" not in self.miss_tiles[i]:
                            if f"d_{tid_d}" in self.hit_tiles[i]:
                                if (i, tid_d, 'down') in self.flash_hits: self.set_led(buffer, x, y, GREEN)
                            else:
                                color = YELLOW if (HIT_ZONE_BOTTOM[0] <= pd_f <= HIT_ZONE_BOTTOM[1]) else CYAN
                                self.set_led(buffer, x, y, color)
                        # Jucator SUS (P1)
                        pu_f, tid_u = self._get_tile_info(i, t, 'up')
                        if y == int(pu_f) and f"u_{tid_u}" not in self.miss_tiles[i]:
                            if f"u_{tid_u}" in self.hit_tiles[i]:
                                if (i, tid_u, 'up') in self.flash_hits: self.set_led(buffer, x, y, GREEN)
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

if __name__ == "__main__":
    game = PianoTilesEngine()
    net = NetworkManager(game)
    threading.Thread(target=net.run, daemon=True).start()
    print("=== PIANO TILES 1v1 ===\n1=Solo(2x2), 2=1v1(1x1), 0=Reset")
    try:
        while game.running:
            cmd = input("> ").strip().lower()
            if cmd == 'q': game.running = False
            elif cmd in ['1', '2']:
                game.mode = cmd; game.start_time = time.time(); game.is_pulsing = True; game._reset_state()
            elif cmd == '0': game.mode = None
    except: game.running = False