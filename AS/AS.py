import socket
import time
import threading
import random
import math
import psutil
import os
import tkinter as tk

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

import SoundGenerator

# --- Evil Eye Constants ---
UDP_SEND_PORT = 4626
UDP_LISTEN_PORT = 7800

PASSWORD_ARRAY = [
    35, 63, 187, 69, 107, 178, 92, 76, 39, 69, 205, 37, 223, 255, 165, 231, 16, 220, 99, 61, 25, 203, 203, 
    155, 107, 30, 92, 144, 218, 194, 226, 88, 196, 190, 67, 195, 159, 185, 209, 24, 163, 65, 25, 172, 126, 
    63, 224, 61, 160, 80, 125, 91, 239, 144, 25, 141, 183, 204, 171, 188, 255, 162, 104, 225, 186, 91, 232, 
    3, 100, 208, 49, 211, 37, 192, 20, 99, 27, 92, 147, 152, 86, 177, 53, 153, 94, 177, 200, 33, 175, 195, 
    15, 228, 247, 18, 244, 150, 165, 229, 212, 96, 84, 200, 168, 191, 38, 112, 171, 116, 121, 186, 147, 203, 
    30, 118, 115, 159, 238, 139, 60, 57, 235, 213, 159, 198, 160, 50, 97, 201, 253, 242, 240, 77, 102, 12, 
    183, 235, 243, 247, 75, 90, 13, 236, 56, 133, 150, 128, 138, 190, 140, 13, 213, 18, 7, 117, 255, 45, 69, 
    214, 179, 50, 28, 66, 123, 239, 190, 73, 142, 218, 253, 5, 212, 174, 152, 75, 226, 226, 172, 78, 35, 93, 
    250, 238, 19, 32, 247, 223, 89, 123, 86, 138, 150, 146, 214, 192, 93, 152, 156, 211, 67, 51, 195, 165, 
    66, 10, 10, 31, 1, 198, 234, 135, 34, 128, 208, 200, 213, 169, 238, 74, 221, 208, 104, 170, 166, 36, 76, 
    177, 196, 3, 141, 167, 127, 56, 177, 203, 45, 107, 46, 82, 217, 139, 168, 45, 198, 6, 43, 11, 57, 88, 
    182, 84, 189, 29, 35, 143, 138, 171
]

def calculate_checksum(data: bytearray) -> int:
    return PASSWORD_ARRAY[sum(data) & 0xFF]

# --- Discovery ---
def get_local_interfaces():
    interfaces = []
    for iface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                interfaces.append((iface_name, addr.address, addr.broadcast or "255.255.255.255"))
    return interfaces

def build_discovery_packet():
    r1, r2 = random.randint(0, 127), random.randint(0, 127)
    payload = bytearray([0x0A, 0x02, *b"KX-HC04", 0x03, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x14])
    pkt = bytearray([0x67, r1, r2, len(payload)]) + payload
    pkt.append(calculate_checksum(pkt))
    return pkt, r1, r2

def run_discovery_flow():
    interfaces = get_local_interfaces()
    if not interfaces: return None
    print("\n--- Network Selection ---")
    for i, (iface, ip, _) in enumerate(interfaces): print(f"[{i}] {iface} - {ip}")
    try: sel = interfaces[int(input("\nSelect interface number: "))]
    except: sel = interfaces[0]
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try: sock.bind((sel[1], 7800))
    except: pass
    
    pkt, r1, r2 = build_discovery_packet()
    try: sock.sendto(pkt, (sel[2], 4626))
    except: return None
    
    sock.settimeout(0.5)
    end_time = time.time() + 3
    devices = []
    while time.time() < end_time:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) >= 30 and data[0] == 0x68 and data[1] == r1 and data[2] == r2:
                devices.append(addr[0])
                print(f" Found Evil Eye at {addr[0]}")
        except: pass
    sock.close()
    return devices[0] if devices else "127.0.0.1"


# --- Sound Manager ---
class SoundManager:
    def __init__(self):
        self.enabled = PYGAME_AVAILABLE
        if self.enabled:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.sounds = {}
            if not os.path.exists("_sfx/success.wav"): SoundGenerator.generate_all()
            for sfx in ['animal_0', 'animal_1', 'animal_2', 'animal_3', 'animal_4', 'success', 'eliminate', 'win']:
                try: self.sounds[sfx] = pygame.mixer.Sound(f"_sfx/{sfx}.wav")
                except Exception as e: 
                    print(f"WARNING: Corrupted or unsupported format for {sfx}.wav -> {e}")

    def play(self, name):
        if self.enabled and name in self.sounds:
            try: self.sounds[name].play()
            except Exception as e: print(f"Audio playback error: {e}")


# --- Game Logic ---
class AnimalSoundsGame:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        self.sound = SoundManager()
        
        self.state = "LOBBY" 
        self.difficulty = "EASY" 
        
        self.active_players = {} 
        self.started_with = 0
        
        self.sequence = []
        self.show_index = 0
        self.show_timer = 0
        self.played_step_sound = False
        
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}
        
        self.COLORS = [
            (255, 0, 0),   # 0 - Red
            (0, 255, 0),   # 1 - Green
            (0, 0, 255),   # 2 - Blue
            (255, 255, 0), # 3 - Yellow
            (255, 0, 255)  # 4 - Magenta
        ]

    def tick(self):
        now = time.time()
        with self.lock:
            self.active_leds.clear()

            # --- 1. Base Layer ---
            if self.state != "LOBBY":
                for pid in range(8):
                    wall = (pid // 2) + 1
                    is_left = (pid % 2 == 0)
                    leds = range(1, 6) if is_left else range(6, 11)

                    if pid >= self.started_with: 
                        for led in leds: self.active_leds[(wall, led)] = (128, 128, 0)
                    elif pid not in self.active_players:
                        pulse = int(127 + 127 * math.sin(now * 5))
                        for led in leds: self.active_leds[(wall, led)] = (pulse, 0, 0)
                    elif self.state == "WINNER":
                        for led in leds:
                            r = int(127 + 127 * math.sin(now * 4 + led * 0.5))
                            g = int(127 + 127 * math.sin(now * 4 + led * 0.5 + 2))
                            b = int(127 + 127 * math.sin(now * 4 + led * 0.5 + 4))
                            self.active_leds[(wall, led)] = (r, g, b)

            # --- 2. The Eye Logic ---
            if self.state in ["LOBBY", "GAMEOVER"]:
                pulse = int(127 + 127 * math.sin(now * 3))
                for ch in range(1, 5): self.active_leds[(ch, 0)] = (pulse, 0, 0)
            elif self.state in ["WINNER", "ROUND_SUCCESS", "WAITING_READY"]:
                for ch in range(1, 5): self.active_leds[(ch, 0)] = (0, 255, 0)

            if self.state in ["LOBBY", "WINNER", "GAMEOVER"]:
                self.process_inputs()
                return

            # --- 3. Active Game Logic ---
            if self.state == "WAITING_READY":
                for pid, p in self.active_players.items():
                    ready_led = 3 if p['side'] == 'left' else 8
                    if p['ready']:
                        pulse = int(127 + 127 * math.sin(now * 6))
                        self.active_leds[(p['wall'], ready_led)] = (0, pulse, pulse)
                    else:
                        self.active_leds[(p['wall'], ready_led)] = (0, 255, 0)
                self.process_inputs()
                return

            if self.state == "ROUND_SUCCESS":
                if now - self.show_timer > 1.5:
                    self.state = "SHOWING_SEQUENCE"
                    self.show_index = 0
                    self.show_timer = now
                    self.played_step_sound = False
                self.process_inputs()
                return

            if self.state == "INTRO_SEQUENCE":
                if now - self.show_timer > 2.5:
                    self.show_index += 1
                    self.show_timer = now
                    self.played_step_sound = False

                if self.show_index < 10:
                    val = self.show_index % 5 
                    if not self.played_step_sound:
                        self.sound.play(f'animal_{val}')
                        self.played_step_sound = True
                    
                    for pid, p in self.active_players.items():
                        led_idx = val + 1 if p['side'] == 'left' else val + 6
                        self.active_leds[(p['wall'], led_idx)] = self.COLORS[val]
                else:
                    self.sequence = [random.randint(0, 4)]
                    self.state = "SHOWING_SEQUENCE"
                    self.show_index = 0
                    self.show_timer = time.time()
                    self.played_step_sound = False
                return

            if self.state == "SHOWING_SEQUENCE":
                if now - self.show_timer > 1.0:
                    self.show_index += 1
                    self.show_timer = now
                    self.played_step_sound = False
                
                is_gap = (now - self.show_timer) > 0.7 
                
                if self.show_index < len(self.sequence):
                    if not is_gap:
                        val = self.sequence[self.show_index]
                        if not self.played_step_sound:
                            self.sound.play(f'animal_{val}')
                            self.played_step_sound = True
                        
                        if self.difficulty == "EASY":
                            col = self.COLORS[val]
                            for pid, p in self.active_players.items():
                                led_idx = val + 1 if p['side'] == 'left' else val + 6
                                self.active_leds[(p['wall'], led_idx)] = col
                else:
                    self.state = "WAITING_INPUT"
                    for p in self.active_players.values():
                        p['input_index'] = 0
                        p['done'] = False

            elif self.state == "WAITING_INPUT":
                for ch in range(1, 5):
                    for led in range(11):
                        if led == 0: continue 
                        if self.button_states[(ch, led)]:
                            side = 'left' if led <= 5 else 'right'
                            val = led - 1 if side == 'left' else led - 6
                            pid = (ch - 1) * 2 + (0 if side == 'left' else 1)
                            if pid in self.active_players:
                                self.active_leds[(ch, led)] = self.COLORS[val]
                            
        self.process_inputs()

    def process_inputs(self):
        with self.lock:
            for ch in range(1, 5):
                for led in range(11):
                    is_pressed = self.button_states[(ch, led)]
                    was_pressed = self.prev_states[(ch, led)]
                    if is_pressed and not was_pressed:
                        self.handle_new_step(ch, led)
                    self.prev_states[(ch, led)] = is_pressed

    def handle_new_step(self, ch, led):
        if led == 0: return 

        side = 'left' if led <= 5 else 'right'
        val = led - 1 if side == 'left' else led - 6
        pid = (ch - 1) * 2 + (0 if side == 'left' else 1)

        if pid not in self.active_players: return 
        p = self.active_players[pid]

        if self.state == "WAITING_READY":
            ready_led = 3 if p['side'] == 'left' else 8
            if led == ready_led and not p['ready']:
                p['ready'] = True
                self.sound.play('animal_0') 
                if all(player['ready'] for player in self.active_players.values()):
                    self.sound.play('success')
                    self.state = "INTRO_SEQUENCE"
                    self.show_index = 0
                    self.show_timer = time.time()
                    self.played_step_sound = False
            return

        if self.state != "WAITING_INPUT": return
        if p['done']: return 

        expected_val = self.sequence[p['input_index']]

        if val == expected_val:
            self.sound.play(f'animal_{val}')
            p['input_index'] += 1
            if p['input_index'] == len(self.sequence):
                p['done'] = True
                self.check_round_end()
        else:
            self.sound.play('eliminate')
            del self.active_players[pid]
            self.check_round_end()

    def check_round_end(self):
        if len(self.active_players) == 0:
            self.state = "GAMEOVER"
            return
            
        if len(self.active_players) == 1 and self.started_with > 1:
            self.sound.play('win')
            self.state = "WINNER"
            return

        all_done = all(p['done'] for p in self.active_players.values())
        if all_done:
            self.sound.play('success')
            self.sequence.append(random.randint(0, 4)) 
            self.state = "ROUND_SUCCESS"
            self.show_timer = time.time()

    def render(self):
        frame = bytearray(132)
        with self.lock:
            for (ch, led), (r, g, b) in self.active_leds.items():
                if 1 <= ch <= 4 and 0 <= led <= 10:
                    idx = ch - 1
                    frame[led * 12 + idx] = g
                    frame[led * 12 + 4 + idx] = r
                    frame[led * 12 + 8 + idx] = b
        return frame

    def start_game(self, num_players, difficulty="EASY"):
        with self.lock:
            if num_players > 8: num_players = 8
            if num_players < 1: num_players = 1
            
            self.started_with = num_players
            self.difficulty = difficulty 
            self.active_players.clear()
            
            for i in range(num_players):
                wall = (i // 2) + 1
                side = 'left' if i % 2 == 0 else 'right'
                self.active_players[i] = {
                    'wall': wall, 'side': side,
                    'input_index': 0, 'done': False, 'ready': False
                }
            self.state = "WAITING_READY"


# --- Network Manager ---
class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.running = True
        self.sequence_number = 0
        self.target_ip = run_discovery_flow()
            
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_recv.bind(("0.0.0.0", UDP_LISTEN_PORT))
        except Exception as e:
            self.running = False

    def send_loop(self):
        while self.running:
            self.send_packet(self.game.render())
            time.sleep(0.02) 

    def build_packet(self, cmd_h, cmd_l, payload=b""):
        internal = bytearray([0x02, 0x00, 0x00, cmd_h, cmd_l]) + payload
        length = len(internal) - 1
        r1, r2 = random.randint(0, 127), random.randint(0, 127)
        pkt = bytearray([0x75, r1, r2, (length >> 8) & 0xFF, length & 0xFF]) + internal
        pkt.append(calculate_checksum(pkt))
        return pkt

    def send_packet(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1
        seq_h, seq_l = (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF
        
        p1 = self.build_packet(0x33, 0x44, bytearray([seq_h, seq_l, 0x00, 0x00, 0x00]))
        p2 = self.build_packet(0xFF, 0xF0, b'\x00\x0B' * 4)
        p3 = self.build_packet(0x88, 0x77, bytearray([0x00, 0x01, (len(frame_data) >> 8) & 0xFF, len(frame_data) & 0xFF]) + frame_data)
        p4 = self.build_packet(0x55, 0x66, bytearray([seq_h, seq_l, 0x00, 0x00, 0x00]))
        
        try:
            target = (self.target_ip, UDP_SEND_PORT)
            for p in [p1, p2, p3, p4]:
                self.sock_send.sendto(p, target)
                time.sleep(0.008)
        except: pass

    def recv_loop(self):
        while self.running:
            try:
                data, _ = self.sock_recv.recvfrom(2048)
                if len(data) == 687 and data[0] == 0x88:
                    with self.game.lock:
                        for ch in range(1, 5):
                            base = 2 + (ch - 1) * 171
                            for led in range(11):
                                self.game.button_states[(ch, led)] = (data[base + 1 + led] == 0xCC)
            except: pass

    def start_bg(self):
        threading.Thread(target=self.send_loop, daemon=True).start()
        threading.Thread(target=self.recv_loop, daemon=True).start()


def game_thread_func(game):
    while game.running:
        game.tick()
        time.sleep(0.01)

# --- GUI Manager ---
class AnimalSoundsGUI:
    def __init__(self, root, game, net):
        self.root = root
        self.game = game
        self.net = net
        
        # --- Screen 1: Outside Control Panel ---
        self.root.title("OUTSIDE SCREEN - Animal Sounds")
        self.root.geometry("1920x1080") 
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

        # Difficulty Selection Frame
        diff_frame = tk.Frame(self.container, bg=self.bg_color)
        diff_frame.pack(pady=10)
        
        self.diff_var = tk.StringVar(value="EASY") 
        tk.Radiobutton(
            diff_frame, text="EASY (Colors + Sound)", variable=self.diff_var, 
            value="EASY", font=("Arial", 20, "bold"), bg=self.bg_color, fg="#00FF44", 
            selectcolor="#111111", activebackground=self.bg_color, activeforeground="#00FF44"
        ).grid(row=0, column=0, padx=30)
        
        tk.Radiobutton(
            diff_frame, text="HARD (Sound Only)", variable=self.diff_var, 
            value="HARD", font=("Arial", 20, "bold"), bg=self.bg_color, fg="#FF0044", 
            selectcolor="#111111", activebackground=self.bg_color, activeforeground="#FF0044"
        ).grid(row=0, column=1, padx=30)

        tk.Label(self.container, text="SELECT PLAYERS TO START", font=("Arial", 24, "bold"), bg=self.bg_color, fg="#FFFFFF").pack(pady=10)

        control_frame = tk.Frame(self.container, bg=self.bg_color)
        control_frame.pack(pady=20)

        btn_colors = ["#FF0044", "#00FF44", "#0088FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FF8800", "#FFFFFF"]

        for i in range(1, 9):
            idx = i - 1
            btn = tk.Button(
                control_frame, text=f"{i} PLAYER{'S' if i > 1 else ''}", font=("Arial", 18, "bold"), 
                bg=btn_colors[idx], fg="#000000", activebackground="#FFFFFF", activeforeground="#000000",
                width=14, height=3, bd=6, command=lambda num=i: self.start_game(num)
            )
            if idx < 4: btn.grid(row=0, column=idx, padx=15, pady=15)
            else: btn.grid(row=1, column=idx-4, padx=15, pady=15)

        action_frame = tk.Frame(self.container, bg=self.bg_color)
        action_frame.pack(pady=50)

        tk.Button(action_frame, text="RESTART", font=("Arial", 20, "bold"), bg="#FFFFFF", fg="#000000", width=15, height=2, bd=6, command=self.restart_round).grid(row=0, column=0, padx=30)
        tk.Button(action_frame, text="QUIT", font=("Arial", 20, "bold"), bg="#444444", fg="#FFFFFF", width=15, height=2, bd=6, command=self.quit_app).grid(row=0, column=1, padx=30)

        # --- Screen 2: Inside Live Scoreboard ---
        self.score_window = tk.Toplevel(self.root)
        self.score_window.title("INSIDE SCREEN - Animal Sounds")
        self.score_window.geometry("1920x1080")
        self.score_window.configure(bg="#050505")
        
        tk.Label(self.score_window, text="ANIMAL SOUNDS", font=("Consolas", 64, "bold"), bg="#050505", fg="#00FFFF").pack(pady=20)
        
        self.inside_timer_var = tk.StringVar(value="--")
        self.inside_timer_label = tk.Label(self.score_window, textvariable=self.inside_timer_var, font=("Consolas", 72, "bold"), bg="#050505", fg="#FFFF00")
        self.inside_timer_label.pack(pady=10)

        self.score_frame = tk.Frame(self.score_window, bg="#050505")
        self.score_frame.pack(expand=True)

        self.score_vars = []
        self.score_labels = []

        for i in range(8):
            var = tk.StringVar(value=f"PLAYER {i+1}\nWAITING")
            lbl = tk.Label(self.score_frame, textvariable=var, font=("Consolas", 42, "bold"), bg="#111111", fg="#555555", width=10, height=3, relief="ridge", bd=6)
            lbl.grid(row=i//4, column=i%4, padx=25, pady=25)
            self.score_vars.append(var)
            self.score_labels.append(lbl)

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.score_window.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.update_loop()

    def start_game(self, num_players): 
        self.game.start_game(num_players, difficulty=self.diff_var.get())
        
    def restart_round(self): 
        self.game.start_game(max(1, self.game.started_with), difficulty=self.diff_var.get())
        
    def quit_app(self):
        self.game.running = False
        self.net.running = False
        self.root.destroy()

    def update_loop(self):
        with self.game.lock: # ADDED SAFETY LOCK!
            state = self.game.state
            
            # --- Update OUTSIDE Control Panel ---
            if state == "LOBBY":
                display_text = "LOBBY\nReady to start!"
                self.status_label.config(fg="#00FFFF") 
                self.inside_timer_var.set("WAITING")
                self.inside_timer_label.config(fg="#00FFFF")
            elif state == "WAITING_READY":
                ready = sum(1 for p in self.game.active_players.values() if p['ready'])
                total = len(self.game.active_players)
                display_text = f"WAITING FOR PLAYERS\n{ready} / {total} Ready"
                self.status_label.config(fg="#FFFF00") 
                self.inside_timer_var.set(f"READY UP: {ready}/{total}")
                self.inside_timer_label.config(fg="#FFFF00")
            elif state == "INTRO_SEQUENCE":
                display_text = "INTRO\nMemorize the sounds!"
                self.status_label.config(fg="#FF00FF") 
                self.inside_timer_var.set("MEMORIZE!")
                self.inside_timer_label.config(fg="#FF00FF")
            elif state == "SHOWING_SEQUENCE":
                diff_text = "(EASY)" if self.game.difficulty == "EASY" else "(HARD)"
                display_text = f"LISTEN! {diff_text}\nMemorize the sequence"
                self.status_label.config(fg="#FF8800") 
                self.inside_timer_var.set("LISTEN!")
                self.inside_timer_label.config(fg="#FF8800")
            elif state == "WAITING_INPUT":
                display_text = f"YOUR TURN!\nPlayers Left: {len(self.game.active_players)}"
                self.status_label.config(fg="#00FF44") 
                self.inside_timer_var.set("YOUR TURN!")
                self.inside_timer_label.config(fg="#00FF44")
            elif state == "ROUND_SUCCESS":
                display_text = "SUCCESS!\nGet ready for next..."
                self.status_label.config(fg="#00FF44") 
                self.inside_timer_var.set("SUCCESS!")
                self.inside_timer_label.config(fg="#00FF44")
            elif state == "WINNER":
                display_text = "WE HAVE A WINNER!"
                self.status_label.config(fg="#00FF44") 
                self.inside_timer_var.set("WINNER!")
                self.inside_timer_label.config(fg="#00FF44")
            elif state == "GAMEOVER":
                display_text = "GAME OVER\nEveryone Eliminated"
                self.status_label.config(fg="#FF0044") 
                self.inside_timer_var.set("GAME OVER")
                self.inside_timer_label.config(fg="#FF0044")
            else:
                display_text = state

            self.status_var.set(display_text)
            
            # --- Update INSIDE Scoreboard ---
            for i in range(8):
                if state == "LOBBY":
                    self.score_vars[i].set(f"PLAYER {i+1}\n--")
                    self.score_labels[i].config(fg="#555555")
                else:
                    if i >= self.game.started_with:
                        self.score_vars[i].set(f"PLAYER {i+1}\nN/A")
                        self.score_labels[i].config(fg="#333333") 
                    elif i in self.game.active_players:
                        if state == "WAITING_READY":
                            ready_status = "READY!" if self.game.active_players[i]['ready'] else "PRESS GREEN"
                            self.score_vars[i].set(f"PLAYER {i+1}\n{ready_status}")
                            self.score_labels[i].config(fg="#00FF44" if self.game.active_players[i]['ready'] else "#FFFF00")
                        else:
                            self.score_vars[i].set(f"PLAYER {i+1}\nALIVE")
                            self.score_labels[i].config(fg="#00FFFF") 
                    else:
                        self.score_vars[i].set(f"PLAYER {i+1}\nOUT")
                        self.score_labels[i].config(fg="#FF0044") 

        self.root.after(100, self.update_loop)

# --- Execution ---
if __name__ == "__main__":
    game = AnimalSoundsGame()
    net = NetworkManager(game)
    net.start_bg()
    
    threading.Thread(target=game_thread_func, args=(game,), daemon=True).start()
    
    root = tk.Tk()
    gui = AnimalSoundsGUI(root, game, net)
    print("GUI Running. Two windows have been created!")
    root.mainloop()
    print("Exiting...")