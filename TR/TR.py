import socket
import struct
import time
import threading
import random
import copy
import psutil
import os
import json
import math
import tkinter as tk
from tkinter import ttk

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# --- Configuration ---
_CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tetris_config.json")

def _load_config():
    defaults = {
        "device_ip": "255.255.255.255",
        "send_port": 4626,
        "recv_port": 7800,
        "bind_ip": "0.0.0.0"
    }
    try:
        if os.path.exists(_CFG_FILE):
            with open(_CFG_FILE, encoding="utf-8") as f:
                return {**defaults, **json.load(f)}
    except: pass
    return defaults

CONFIG = _load_config()

# --- Networking Constants ---
UDP_SEND_IP = CONFIG.get("device_ip", "255.255.255.255")
UDP_SEND_PORT = CONFIG.get("send_port", 4626)
UDP_LISTEN_PORT = CONFIG.get("recv_port", 7800)

# --- Matrix Constants ---
NUM_CHANNELS = 8
LEDS_PER_CHANNEL = 64
FRAME_DATA_LENGTH = NUM_CHANNELS * LEDS_PER_CHANNEL * 3

# --- Password for Checksum ---
PASSWORD_ARRAY = [
    35, 63, 187, 69, 107, 178, 92, 76, 39, 69, 205, 37, 223, 255, 165, 231, 16, 220, 99, 61, 25, 203, 203, 
    155, 107, 30, 92, 144, 218, 194, 226, 88, 196, 190, 67, 195, 159, 185, 209, 24, 163, 65, 25, 172, 126, 
    63, 224, 61, 160, 80, 125, 91, 239, 144, 25, 141, 183, 204, 171, 188, 255, 162, 104, 225, 186, 91, 232, 
    3, 100, 208, 49, 211, 37, 192, 20, 99, 27, 92, 147, 152, 86, 177, 53, 153, 94, 177, 200, 33, 175, 195, 
    15, 228, 247, 18, 244, 150, 165, 229, 212, 96, 84, 200, 168, 191, 38, 112, 171, 116, 121, 186, 147, 203, 
    30, 118, 115, 159, 238, 139, 60, 57, 235, 213, 159, 198, 160, 50, 97, 201, 242, 240, 77, 102, 12, 
    183, 235, 243, 247, 75, 90, 13, 236, 56, 133, 150, 128, 138, 190, 140, 13, 213, 18, 7, 117, 255, 45, 69, 
    214, 179, 50, 28, 66, 123, 239, 190, 73, 142, 218, 253, 5, 212, 174, 152, 75, 226, 226, 172, 78, 35, 93, 
    250, 238, 19, 32, 247, 233, 89, 123, 86, 138, 150, 146, 214, 192, 93, 152, 156, 211, 67, 51, 195, 165, 
    66, 10, 10, 31, 1, 198, 234, 135, 34, 128, 208, 200, 213, 169, 238, 74, 221, 208, 104, 170, 166, 36, 76, 
    177, 196, 3, 141, 167, 127, 56, 177, 203, 45, 107, 46, 82, 217, 139, 168, 45, 198, 6, 43, 11, 57, 88, 
    182, 84, 189, 29, 35, 143, 138, 171
]

# --- Font Data ---
FONT = {
    1: [(1,0), (1,1), (1,2), (1,3), (1,4)], 
    2: [(0,0), (1,0), (2,0), (2,1), (1,2), (0,2), (0,3), (0,4), (1,4), (2,4)],
    3: [(0,0), (1,0), (2,0), (2,1), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
    4: [(0,0), (0,1), (0,2), (1,2), (2,2), (2,0), (2,1), (2,3), (2,4)],
    5: [(0,0), (1,0), (2,0), (0,1), (0,2), (1,2), (2,2), (2,3), (0,4), (1,4), (2,4)],
    'W': [(0,0),(0,1),(0,2),(0,3),(0,4), (4,0),(4,1),(4,2),(4,3),(4,4), (1,3),(2,2),(3,3)], 
    'I': [(0,0),(1,0),(2,0), (1,1),(1,2),(1,3), (0,4),(1,4),(2,4)],
    'N': [(0,0),(0,1),(0,2),(0,3),(0,4), (3,0),(3,1),(3,2),(3,3),(3,4), (1,1),(2,2)] 
}

def calculate_checksum(data):
    acc = sum(data)
    idx = acc & 0xFF
    return PASSWORD_ARRAY[idx] if idx < len(PASSWORD_ARRAY) else 0

# --- Classes ---
import SoundGenerator

class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            if PYGAME_AVAILABLE:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                self.enabled = True
                self.sounds = {}
                self._load_sounds()
            else:
                print("Pygame module not found. Audio disabled.")
        except Exception as e:
            print(f"Audio init failed: {e}")
            self.enabled = False

    def _load_sounds(self):
        if not os.path.exists("_sfx/step.wav"):
            print("Generating TNT SFX...")
            SoundGenerator.generate_all()

        sfx_files = {
            'step': '_sfx/step.wav',
            'vanish': '_sfx/vanish.wav',
            'eliminate': '_sfx/eliminate.wav',
            'tick': '_sfx/tick.wav',
            'win': '_sfx/win.wav',
        }
        
        for name, path in sfx_files.items():
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except:
                    print(f"Failed to load {path}")
            else:
                print(f"Warning: Missing SFX {path}")
        
        if os.path.exists("_sfx/bgm.wav"):
            try:
                pygame.mixer.music.load("_sfx/bgm.wav")
                pygame.mixer.music.set_volume(0.5)
            except:
                print("Failed to load BGM")

    def play(self, name):
        if not self.enabled: return
        if name in self.sounds:
            try: self.sounds[name].play()
            except: pass

    def start_bgm(self):
        if not self.enabled: return
        try:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1) 
        except: pass
    
    def stop_bgm(self):
        if not self.enabled: return
        try: pygame.mixer.music.stop()
        except: pass

class TRGame:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        
        self.sound = SoundManager() 
        
        self.state = "LOBBY" 
        self.players_remaining = 0
        self.pause_time_start = 0
        self.countdown_start = 0
        self.last_played_tick = 0 
        self.killer_tile = None 
        
        # --- Timer Logic Added Here ---
        self.total_play_time = 0.0
        self.last_tick_time = time.time()
        
        self.death_pattern_zone = [] 
        self.void_zone = []          
        self.win_text_coords = (1, 13) 

        self.BOARD_WIDTH = 16
        self.BOARD_HEIGHT = 32
        self.PULSE_DURATION = 2.0  
        self.PEAK_TIME = 1.0       
        self.COUNTDOWN_DURATION = 3.0
        self.STARTUP_DURATION = 5.0 
        
        self.RESUME_TILES = [(0, 18), (0, 19)]
        
        self.COLOR_ACTIVE_PURPLE = (128, 0, 128)
        self.COLOR_ACTIVE_YELLOW = (128, 128, 0)  
        self.COLOR_LUMINOUS_YELLOW = (255, 255, 0) 
        self.COLOR_DEAD   = (0, 0, 0)
        self.COLOR_LOSS   = (255, 0, 0) 
        self.COLOR_RESUME = (0, 255, 0) 
        self.COLOR_WHITE  = (255, 255, 255)
        
        self.tile_states = [[{'status': 'ACTIVE', 'start_time': 0} for _ in range(self.BOARD_WIDTH)] for _ in range(self.BOARD_HEIGHT)]
        self.button_states = [False] * 512
        self.prev_button_states = [False] * 512

    def tick(self):
        now = time.time()
        delta = now - self.last_tick_time
        self.last_tick_time = now

        with self.lock:
            # Advance the timer only during active play
            if self.state == "PLAYING":
                self.total_play_time += delta

            if self.state == "LOBBY" or self.state == "WINNER": return

            if self.state == "STARTUP" or self.state == "COUNTDOWN":
                duration = self.STARTUP_DURATION if self.state == "STARTUP" else self.COUNTDOWN_DURATION
                seconds_left = int(duration - (now - self.countdown_start)) + 1
                
                if seconds_left != self.last_played_tick and seconds_left > 0:
                    self.sound.play('tick')
                    self.last_played_tick = seconds_left

                if now - self.countdown_start >= duration:
                    if self.state == "STARTUP":
                        self.state = "PLAYING"
                    else:
                        self.resume_game()
                return

            if self.state == "PAUSED":
                for rx, ry in self.RESUME_TILES:
                    if self.is_tile_pressed(rx, ry):
                        self.state = "COUNTDOWN"
                        self.countdown_start = time.time()
                        self.last_played_tick = 0 
                return 

            for y in range(self.BOARD_HEIGHT):
                for x in range(self.BOARD_WIDTH):
                    tile = self.tile_states[y][x]
                    if tile['status'] == 'PULSING' and now - tile['start_time'] >= self.PULSE_DURATION:
                        tile['status'] = 'DEAD'
                        self.sound.play('vanish') 
                    
                    if tile['status'] == 'DEAD' and self.is_tile_pressed(x, y):
                        self.trigger_loss(x, y)
                        return
        self.process_inputs()

    def trigger_loss(self, x, y):
        self.state = "PAUSED"
        self.pause_time_start = time.time()
        self.killer_tile = (x, y)
        self.players_remaining -= 1
        
        self.sound.play('eliminate') 
        
        self.death_pattern_zone = []
        self.void_zone = []
        
        def add_red(tx, ty):
            if 0 <= tx < self.BOARD_WIDTH and 0 <= ty < self.BOARD_HEIGHT:
                self.death_pattern_zone.append((tx, ty))

        add_red(x, y) 
        add_red(x - 2, y - 2); add_red(x - 1, y - 2); add_red(x - 2, y - 1)
        add_red(x + 2, y - 2); add_red(x + 1, y - 2); add_red(x + 2, y - 1) 
        add_red(x - 2, y + 2); add_red(x - 1, y + 2); add_red(x - 2, y + 1) 
        add_red(x + 2, y + 2); add_red(x + 1, y + 2); add_red(x + 2, y + 1) 
        
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.BOARD_WIDTH and 0 <= ny < self.BOARD_HEIGHT:
                    if (nx, ny) not in self.death_pattern_zone:
                        self.void_zone.append((nx, ny))
        
        self.win_text_coords = self.get_safe_text_coordinates(y)

        if self.players_remaining <= 1:
            self.state = "WINNER"
            self.sound.stop_bgm() 
            self.sound.play('win') 

    def get_safe_text_coordinates(self, killer_y):
        void_top = killer_y - 3
        void_bottom = killer_y + 3
        
        candidates = [3, 13, 23]
        safe_zones = []
        
        for cy in candidates:
            text_top = cy
            text_bottom = cy + 4 
            if not (text_top <= void_bottom and text_bottom >= void_top):
                safe_zones.append(cy)
                
        chosen_y = random.choice(safe_zones) if safe_zones else 3
        return (1, chosen_y)

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)
        now = time.time()
        with self.lock:
            if self.state == "LOBBY": return buffer

            if self.state == "STARTUP":
                self.fill_buffer(buffer, self.COLOR_LUMINOUS_YELLOW)
                num = int(self.STARTUP_DURATION - (now - self.countdown_start)) + 1
                if num > 0: 
                    self.draw_scaled_glyph(buffer, num, 3, 8, self.COLOR_WHITE, scale=3)
                return buffer

            if self.state == "WINNER":
                self.render_rainbow(buffer, now)
                for vx, vy in self.void_zone: self.set_led(buffer, vx, vy, self.COLOR_DEAD)
                for dx, dy in self.death_pattern_zone: self.set_led(buffer, dx, dy, self.COLOR_LOSS)
                
                tx, ty = self.win_text_coords
                
                # 1. Draw Solid Black Banner
                for fill_y in range(ty - 1, ty + 6):
                    for fill_x in range(tx - 1, tx + 16):
                        self.set_led(buffer, fill_x, fill_y, self.COLOR_DEAD)
                
                # 2. Draw Bright White Text
                self.draw_glyph(buffer, 'W', tx, ty, self.COLOR_WHITE)
                self.draw_glyph(buffer, 'I', tx+6, ty, self.COLOR_WHITE) 
                self.draw_glyph(buffer, 'N', tx+10, ty, self.COLOR_WHITE)
                
                return buffer

            is_frozen = (self.state != "PLAYING")
            hb = 1.0 + ((math.sin((now - self.countdown_start) * math.pi * 2 - (math.pi / 2)) + 1) / 2 * 0.4) if self.state == "COUNTDOWN" else 1.0

            for y in range(self.BOARD_HEIGHT):
                for x in range(self.BOARD_WIDTH):
                    tile = self.tile_states[y][x]
                    if is_frozen and (x, y) in self.RESUME_TILES: color = self.COLOR_RESUME
                    elif is_frozen and (x, y) in self.death_pattern_zone: color = self.COLOR_LOSS
                    elif tile['status'] == 'DEAD': color = self.COLOR_DEAD
                    else:
                        base = self.COLOR_ACTIVE_YELLOW if is_frozen else self.COLOR_ACTIVE_PURPLE
                        if tile['status'] == 'ACTIVE': color = base
                        else:
                            e = (self.pause_time_start if is_frozen else now) - tile['start_time']
                            color = self.calculate_dynamic_color(base, e)
                        if self.state == "COUNTDOWN": color = tuple(min(255, int(c * hb)) for c in color)
                    self.set_led(buffer, x, y, color)
        return buffer

    def resume_game(self):
        with self.lock:
            pause_len = time.time() - self.pause_time_start
            for row in self.tile_states:
                for tile in row:
                    if tile['status'] == 'PULSING': tile['start_time'] += pause_len
            self.state = "PLAYING"
            self.killer_tile = None
            self.death_pattern_zone = []
            self.void_zone = []

    def handle_new_step(self, sensor_idx):
        if self.state != "PLAYING": return
        channel, local = sensor_idx // 64, sensor_idx % 64
        row, col_raw = local // 16, local % 16
        y, x = (channel * 4) + row, (col_raw if row % 2 == 0 else 15 - col_raw)
        if 0 <= y < self.BOARD_HEIGHT and 0 <= x < self.BOARD_WIDTH:
            tile = self.tile_states[y][x]
            if tile['status'] == 'ACTIVE':
                tile['status'] = 'PULSING'
                tile['start_time'] = time.time()
                self.sound.play('step') 
            elif tile['status'] == 'DEAD': 
                self.trigger_loss(x, y)

    def process_inputs(self):
        with self.lock:
            for i in range(512):
                if self.button_states[i] and not self.prev_button_states[i]: self.handle_new_step(i)
                self.prev_button_states[i] = self.button_states[i]

    def render_rainbow(self, buffer, now):
        for y in range(self.BOARD_HEIGHT):
            for x in range(self.BOARD_WIDTH):
                r = int(127 + 127 * math.sin(now * 2 + x * 0.3))
                g = int(127 + 127 * math.sin(now * 2 + y * 0.3 + 2))
                b = int(127 + 127 * math.sin(now * 2 + (x+y) * 0.3 + 4))
                self.set_led(buffer, x, y, (r, g, b))

    def calculate_dynamic_color(self, base, elapsed):
        if elapsed < self.PEAK_TIME: f = 1.0 + (elapsed / self.PEAK_TIME)
        elif elapsed < self.PULSE_DURATION: f = (self.PULSE_DURATION - elapsed) / (self.PULSE_DURATION - self.PEAK_TIME)
        else: return (0, 0, 0)
        return tuple(min(255, int(c * f)) for c in base)

    def is_tile_pressed(self, x, y):
        ch, row = y // 4, y % 4
        idx = (ch * 64) + (row * 16 + (x if row % 2 == 0 else 15 - x))
        return self.button_states[idx]

    def set_led(self, buffer, x, y, color):
        if x < 0 or x >= 16 or y < 0 or y >= 32: return
        ch, row = y // 4, y % 4
        idx = row * 16 + (x if row % 2 == 0 else 15 - x)
        off = idx * (NUM_CHANNELS * 3) + ch
        if off + NUM_CHANNELS * 2 < len(buffer):
            buffer[off], buffer[off+NUM_CHANNELS], buffer[off+NUM_CHANNELS*2] = color[1], color[0], color[2]

    def draw_glyph(self, buffer, key, ox, oy, color):
        if key in FONT:
            for dx, dy in FONT[key]: self.set_led(buffer, ox + dx, oy + dy, color)

    def draw_scaled_glyph(self, buffer, key, ox, oy, color, scale):
        if key in FONT:
            for dx, dy in FONT[key]:
                for sx in range(scale):
                    for sy in range(scale):
                        self.set_led(buffer, ox + (dx * scale) + sx, oy + (dy * scale) + sy, color)

    def fill_buffer(self, buffer, color):
        for y in range(self.BOARD_HEIGHT):
            for x in range(self.BOARD_WIDTH): self.set_led(buffer, x, y, color)

    def start_game(self, num_players):
        with self.lock:
            self.players_remaining = num_players
            self.state = "STARTUP"
            
            # Reset timer variables for new game
            self.total_play_time = 0.0
            self.last_tick_time = time.time()
            
            self.countdown_start = time.time()
            self.last_played_tick = 0
            self.killer_tile = None
            self.death_pattern_zone = []; self.void_zone = []
            self.tile_states = [[{'status': 'ACTIVE', 'start_time': 0} for _ in range(self.BOARD_WIDTH)] for _ in range(self.BOARD_HEIGHT)]
            
            self.sound.start_bgm()

    def restart_round(self): 
        self.start_game(self.players_remaining if self.players_remaining > 0 else 2)

class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_send.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        self.sequence_number = 0
        self.prev_button_states = [False] * 64
        
        bind_ip = CONFIG.get("bind_ip", "0.0.0.0")
        if bind_ip != "0.0.0.0":
            try: self.sock_send.bind((bind_ip, 0))
            except Exception as e: print(f"Warning: Could not bind send socket: {e}")
        
        try:
            self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_recv.bind(("0.0.0.0", UDP_LISTEN_PORT))
        except Exception as e:
            print(f"Critical Error: Could not bind receive socket: {e}")
            self.running = False

    def send_loop(self):
        while self.running:
            frame = self.game.render()
            self.send_packet(frame)
            time.sleep(0.05) 

    def send_packet(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1
        
        target_ip = UDP_SEND_IP
        port = UDP_SEND_PORT
        
        # --- 1. Start Packet ---
        rand1, rand2 = random.randint(0, 127), random.randint(0, 127)
        start_packet = bytearray([0x75, rand1, rand2, 0x00, 0x08, 0x02, 0x00, 0x00, 0x33, 0x44, (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF, 0x00, 0x00, 0x00, 0x0E, 0x00])
        try: 
            self.sock_send.sendto(start_packet, (target_ip, port))
            self.sock_send.sendto(start_packet, ("127.0.0.1", port))
        except: pass

        # --- 2. FFF0 Packet ---
        fff0_payload = bytearray()
        for _ in range(NUM_CHANNELS): fff0_payload += bytes([(LEDS_PER_CHANNEL >> 8) & 0xFF, LEDS_PER_CHANNEL & 0xFF])
        fff0_internal = bytearray([0x02, 0x00, 0x00, 0x88, 0x77, 0xFF, 0xF0, (len(fff0_payload) >> 8) & 0xFF, (len(fff0_payload) & 0xFF)]) + fff0_payload
        fff0_len = len(fff0_internal) - 1
        fff0_packet = bytearray([0x75, random.randint(0, 127), random.randint(0, 127), (fff0_len >> 8) & 0xFF, (fff0_len & 0xFF)]) + fff0_internal + bytearray([0x1E, 0x00])
        try: 
            self.sock_send.sendto(fff0_packet, (target_ip, port))
            self.sock_send.sendto(fff0_packet, ("127.0.0.1", port))
        except: pass
        
        # --- 3. Data Packets ---
        chunk_size = 984 
        data_packet_index = 1
        for i in range(0, len(frame_data), chunk_size):
            chunk = frame_data[i:i+chunk_size]
            internal_data = bytearray([0x02, 0x00, 0x00, (0x8877 >> 8) & 0xFF, (0x8877 & 0xFF), (data_packet_index >> 8) & 0xFF, (data_packet_index & 0xFF), (len(chunk) >> 8) & 0xFF, (len(chunk) & 0xFF)]) + chunk
            payload_len = len(internal_data) - 1 
            packet = bytearray([0x75, random.randint(0, 127), random.randint(0, 127), (payload_len >> 8) & 0xFF, (payload_len & 0xFF)]) + internal_data
            packet.append(0x1E if len(chunk) == 984 else 0x36)
            packet.append(0x00)
            try: 
                self.sock_send.sendto(packet, (target_ip, port))
                self.sock_send.sendto(packet, ("127.0.0.1", port))
            except: pass
            data_packet_index += 1
            time.sleep(0.005) 

        # --- 4. End Packet ---
        end_packet = bytearray([0x75, random.randint(0, 127), random.randint(0, 127), 0x00, 0x08, 0x02, 0x00, 0x00, 0x55, 0x66, (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF, 0x00, 0x00, 0x00, 0x0E, 0x00])
        try: 
            self.sock_send.sendto(end_packet, (target_ip, port))
            self.sock_send.sendto(end_packet, ("127.0.0.1", port))
        except: pass

    def recv_loop(self):
        while self.running:
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
        t2 = threading.Thread(target=self.recv_loop, daemon=True)
        t1.start()
        t2.start()

def game_thread_func(game):
    while game.running:
        game.tick()
        time.sleep(0.01)

# --- GUI Manager ---

class TNTRunGUI:
    def __init__(self, root, game, net):
        self.root = root
        self.game = game
        self.net = net
        
        # --- Screen 1: Outside Control Panel ---
        self.root.title("OUTSIDE SCREEN - TNT Run Control")
        self.root.geometry("1920x1080")
        self.root.resizable(False, False)

        self.bg_color = "#050505"
        self.root.configure(bg=self.bg_color)

        self.container = tk.Frame(root, bg=self.bg_color)
        self.container.pack(expand=True)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            self.container, textvariable=self.status_var, 
            font=("Consolas", 48, "bold"), 
            bg="#111111", fg="#00FF00", 
            width=25, height=3, relief="ridge", bd=8
        )
        self.status_label.pack(pady=50)

        tk.Label(
            self.container, text="SELECT PLAYERS TO START", 
            font=("Arial", 24, "bold"), 
            bg=self.bg_color, fg="#FFFFFF"
        ).pack(pady=10)

        # Control Frame (Grid for Players)
        control_frame = tk.Frame(self.container, bg=self.bg_color)
        control_frame.pack(pady=20)

        btn_colors = [
            "#FF0044", "#00FF44", "#0088FF", 
            "#FFFF00", "#FF00FF", "#00FFFF", 
            "#FF8800", "#A6E3A1", "#CBA6F7"
        ]

        # Generate buttons 2 through 10
        for i in range(2, 11):
            idx = i - 2
            btn = tk.Button(
                control_frame, text=f"{i} PLAYERS", 
                font=("Arial", 18, "bold"), 
                bg=btn_colors[idx], fg="#000000",
                activebackground="#FFFFFF", activeforeground="#000000",
                width=14, height=3, bd=6,
                command=lambda num=i: self.start_game(num)
            )
            btn.grid(row=idx//3, column=idx%3, padx=15, pady=15)

        action_frame = tk.Frame(self.container, bg=self.bg_color)
        action_frame.pack(pady=50)

        tk.Button(
            action_frame, text="RESTART", font=("Arial", 20, "bold"), 
            bg="#FFFFFF", fg="#000000", width=15, height=2, bd=6, 
            command=self.restart_round
        ).grid(row=0, column=0, padx=30)
        
        tk.Button(
            action_frame, text="QUIT", font=("Arial", 20, "bold"), 
            bg="#444444", fg="#FFFFFF", width=15, height=2, bd=6, 
            command=self.quit_app
        ).grid(row=0, column=1, padx=30)

        # --- Screen 2: Inside Live Scoreboard ---
        self.score_window = tk.Toplevel(self.root)
        self.score_window.title("INSIDE SCREEN - TNT Run Live Stats")
        self.score_window.geometry("1920x1080")
        self.score_window.configure(bg="#050505")

        self.inner_container = tk.Frame(self.score_window, bg="#050505")
        self.inner_container.pack(expand=True)

        tk.Label(self.inner_container, text="TNT RUN", font=("Consolas", 100, "bold"), bg="#050505", fg="#00FFFF").pack(pady=50)

        # Huge Players Alive Tracker
        self.inside_players_var = tk.StringVar(value="PLAYERS: --")
        self.inside_players_label = tk.Label(self.inner_container, textvariable=self.inside_players_var, font=("Consolas", 80, "bold"), bg="#050505", fg="#555555")
        self.inside_players_label.pack(pady=30)

        # Huge Time Tracker
        self.inside_timer_var = tk.StringVar(value="TIME: --:--")
        self.inside_timer_label = tk.Label(self.inner_container, textvariable=self.inside_timer_var, font=("Consolas", 80, "bold"), bg="#050505", fg="#555555")
        self.inside_timer_label.pack(pady=30)

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.score_window.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.update_loop()

    def start_game(self, num_players):
        self.game.start_game(num_players)

    def restart_round(self):
        self.game.restart_round()

    def quit_app(self):
        self.game.running = False
        self.net.running = False
        self.root.destroy()

    def update_loop(self):
        with self.game.lock: # Safety lock for multi-threading
            state = self.game.state
            players = self.game.players_remaining
            
            # Format elapsed time
            total_seconds = int(self.game.total_play_time)
            mins, secs = divmod(total_seconds, 60)
            time_str = f"{mins:02d}:{secs:02d}"

            # --- Update OUTSIDE Control Panel ---
            if state == "LOBBY":
                display_text = "LOBBY\nReady to start!"
                self.status_label.config(fg="#00FFFF") 
            elif state == "STARTUP":
                display_text = "STARTING...\nGet ready!"
                self.status_label.config(fg="#FFFF00") 
            elif state == "PLAYING":
                display_text = f"PLAYING\nPlayers Left: {players}"
                self.status_label.config(fg="#00FF44") 
            elif state in ["PAUSED", "COUNTDOWN"]:
                display_text = f"PAUSED (Elimination!)\nPlayers Left: {players}"
                self.status_label.config(fg="#FF8800") 
            elif state == "WINNER":
                display_text = "WE HAVE A WINNER!"
                self.status_label.config(fg="#FF00FF") 
            else:
                display_text = state

            self.status_var.set(display_text)
            
            # --- Update INSIDE Live Scoreboard ---
            if state == "LOBBY":
                self.inside_players_var.set("WAITING")
                self.inside_players_label.config(fg="#555555")
                self.inside_timer_var.set("TIME: --:--")
                self.inside_timer_label.config(fg="#555555")
            elif state == "STARTUP":
                self.inside_players_var.set("GET READY!")
                self.inside_players_label.config(fg="#FFFF00")
                self.inside_timer_var.set("TIME: 00:00")
                self.inside_timer_label.config(fg="#FFFF00")
            elif state in ["PLAYING", "PAUSED", "COUNTDOWN"]:
                self.inside_players_var.set(f"ALIVE: {players}")
                # Color code players left: Red if only 1 (or 0), otherwise Green
                self.inside_players_label.config(fg="#FF0044" if players <= 1 else "#00FF44")
                
                self.inside_timer_var.set(f"TIME: {time_str}")
                self.inside_timer_label.config(fg="#00FFFF")
            elif state == "WINNER":
                self.inside_players_var.set("WINNER!")
                self.inside_players_label.config(fg="#FF00FF")
                self.inside_timer_var.set(f"SURVIVED: {time_str}")
                self.inside_timer_label.config(fg="#00FFFF")

        self.root.after(100, self.update_loop)


if __name__ == "__main__":
    game = TRGame()
    net = NetworkManager(game)
    net.start_bg()
    
    gt = threading.Thread(target=game_thread_func, args=(game,))
    gt.daemon = True
    gt.start()
    
    root = tk.Tk()
    gui = TNTRunGUI(root, game, net)
    
    print("TNT Run GUI Running. Two screens active!")
    root.mainloop()
    print("Exiting...")