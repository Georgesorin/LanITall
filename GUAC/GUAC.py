import socket
import time
import threading
import random
import math
import psutil
import os
import tkinter as tk
from tkinter import ttk

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

import SoundGenerator

# --- Evil Eye Constants ---
UDP_SEND_PORT = 4626
UDP_LISTEN_PORT = 7800
ROUND_DURATION = 60.0 # 1 minute per round

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
                print(f" ✅ Found Evil Eye at {addr[0]}")
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
            if not os.path.exists("_sfx/good_hit.wav"): SoundGenerator.generate_all()
            for sfx in ['good_hit', 'bad_hit', 'success', 'eliminate', 'win']:
                try: self.sounds[sfx] = pygame.mixer.Sound(f"_sfx/{sfx}.wav")
                except: pass

    def play(self, name):
        if self.enabled and name in self.sounds:
            try: self.sounds[name].play()
            except: pass


# --- Game Logic ---
class WhackAMoleGame:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        self.sound = SoundManager()
        
        self.state = "LOBBY" 
        self.active_players = {} 
        self.started_with = 0
        self.round_end_time = 0
        
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}

    def spawn_mole(self, pid):
        """Spawns a new target for a specific player."""
        p = self.active_players[pid]
        leds = [1, 2, 3, 4, 5] if p['side'] == 'left' else [6, 7, 8, 9, 10]
        
        # 20% chance it's a trap (Red), 80% chance it's good (Green)
        p['target_is_red'] = (random.random() < 0.2)
        
        # Pick a random LED that isn't currently the active one
        choices = [l for l in leds if l != p.get('target_led')]
        p['target_led'] = random.choice(choices)
        
        p['target_time'] = time.time()
        # Moles stay active between 1.0 and 1.8 seconds before disappearing
        p['target_duration'] = random.uniform(1.0, 1.8)

    def tick(self):
        now = time.time()
        with self.lock:
            self.active_leds.clear()

            # --- 1. Base Background Layer ---
            if self.state != "LOBBY":
                for pid in range(8):
                    wall = (pid // 2) + 1
                    is_left = (pid % 2 == 0)
                    leds = range(1, 6) if is_left else range(6, 11)

                    if pid >= self.started_with: # UNUSED = Yellow
                        for led in leds: self.active_leds[(wall, led)] = (128, 128, 0)
                    elif pid not in self.active_players: # ELIMINATED = Red Pulse
                        pulse = int(127 + 127 * math.sin(now * 5))
                        for led in leds: self.active_leds[(wall, led)] = (pulse, 0, 0)
                    elif self.state == "WINNER": # WINNER = Rainbow
                        for led in leds:
                            r = int(127 + 127 * math.sin(now * 4 + led * 0.5))
                            g = int(127 + 127 * math.sin(now * 4 + led * 0.5 + 2))
                            b = int(127 + 127 * math.sin(now * 4 + led * 0.5 + 4))
                            self.active_leds[(wall, led)] = (r, g, b)

            # --- 2. The Eye Logic ---
            if self.state in ["LOBBY", "GAMEOVER"]:
                pulse = int(127 + 127 * math.sin(now * 3))
                for ch in range(1, 5): self.active_leds[(ch, 0)] = (pulse, 0, 0)
            elif self.state in ["WINNER", "ROUND_OVER", "WAITING_READY"]:
                for ch in range(1, 5): self.active_leds[(ch, 0)] = (0, 255, 0)

            # --- 3. Active Game States ---
            if self.state == "WAITING_READY":
                for pid, p in self.active_players.items():
                    ready_led = 3 if p['side'] == 'left' else 8
                    if p['ready']:
                        pulse = int(127 + 127 * math.sin(now * 6))
                        self.active_leds[(p['wall'], ready_led)] = (0, pulse, pulse)
                    else:
                        self.active_leds[(p['wall'], ready_led)] = (0, 255, 0)

            elif self.state == "PLAYING":
                # Check Round Timer
                if now >= self.round_end_time:
                    self.end_round()
                    self.process_inputs()
                    return

                # Render Moles & Handle Timeouts
                for pid, p in self.active_players.items():
                    # Has the mole expired?
                    if now - p['target_time'] > p['target_duration']:
                        if not p['target_is_red']:
                            # Missed a Green Mole! Lose a point.
                            p['score'] -= 1
                        self.spawn_mole(pid)
                    
                    # Draw the active mole
                    color = (255, 0, 0) if p['target_is_red'] else (0, 255, 0)
                    self.active_leds[(p['wall'], p['target_led'])] = color

            elif self.state == "ROUND_OVER":
                if now > self.round_end_time + 3.0: # Wait 3 seconds to show elimination
                    self.state = "WAITING_READY"
                            
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
        if led == 0: return # Ignore Eye
        side = 'left' if led <= 5 else 'right'
        pid = (ch - 1) * 2 + (0 if side == 'left' else 1)

        if pid not in self.active_players: return 
        p = self.active_players[pid]

        if self.state == "WAITING_READY":
            ready_led = 3 if p['side'] == 'left' else 8
            if led == ready_led and not p['ready']:
                p['ready'] = True
                self.sound.play('good_hit')
                if all(player['ready'] for player in self.active_players.values()):
                    self.sound.play('success')
                    self.state = "PLAYING"
                    self.round_end_time = time.time() + ROUND_DURATION
                    # Spawn the first mole for everyone
                    for alive_pid in self.active_players: self.spawn_mole(alive_pid)
            return

        if self.state == "PLAYING":
            if led == p['target_led']:
                if p['target_is_red']:
                    p['score'] -= 1
                    self.sound.play('bad_hit')
                else:
                    p['score'] += 1
                    self.sound.play('good_hit')
                self.spawn_mole(pid)
            else:
                # Hit the wrong blank tile
                p['score'] -= 1
                self.sound.play('bad_hit')

    def end_round(self):
        print("\n--- ROUND OVER SCORES ---")
        for pid, p in self.active_players.items():
            print(f"Player {pid}: {p['score']} pts")
            
        # Find the player with the lowest score
        lowest_pid = min(self.active_players.keys(), key=lambda k: self.active_players[k]['score'])
        
        print(f"❌ Player {lowest_pid} Eliminated with the lowest score!")
        self.sound.play('eliminate')
        del self.active_players[lowest_pid]
        
        if len(self.active_players) == 1:
            winner_id = list(self.active_players.keys())[0]
            print(f"🏆 WE HAVE A WINNER: Player {winner_id}!")
            self.sound.play('win')
            self.state = "WINNER"
        else:
            # Reset scores and ready state for survivors
            for p in self.active_players.values():
                p['score'] = 0
                p['ready'] = False
            self.state = "ROUND_OVER"
            self.round_end_time = time.time() # Used to delay 3 seconds before next WAITING_READY

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

    def start_game(self, num_players):
        with self.lock:
            if num_players > 8: num_players = 8
            if num_players < 2: num_players = 2 # Need at least 2 for elimination!
            
            self.started_with = num_players
            self.active_players.clear()
            
            for i in range(num_players):
                wall = (i // 2) + 1
                side = 'left' if i % 2 == 0 else 'right'
                self.active_players[i] = {
                    'wall': wall, 'side': side,
                    'score': 0, 'ready': False,
                    'target_led': 0, 'target_is_red': False, 
                    'target_time': 0, 'target_duration': 0
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
class WhackAMoleGUI:
    def __init__(self, root, game, net):
        self.root = root
        self.game = game
        self.net = net
        self.root.title("Whack-A-Mole Control Panel")
        self.root.geometry("450x450") 
        self.root.resizable(False, False)

        self.bg_color = "#1E1E2E"
        self.root.configure(bg=self.bg_color)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            root, textvariable=self.status_var, 
            font=("Consolas", 15, "bold"), 
            bg="#313244", fg="#A6E3A1", 
            width=30, height=3, relief="sunken", bd=4
        )
        self.status_label.pack(pady=20)

        tk.Label(root, text="Select Players to Start (Min 2, Max 8):", font=("Arial", 12, "bold"), bg=self.bg_color, fg="#CDD6F4").pack(pady=5)

        control_frame = tk.Frame(root, bg=self.bg_color)
        control_frame.pack(pady=5)

        btn_colors = ["#89B4FA", "#74C7EC", "#89DCEB", "#F9E2AF", "#FAB387", "#F38BA8", "#EBA0AC", "#F5C2E7"]

        # Note: Start from 2 players since 1 player can't be eliminated
        for i in range(2, 9):
            idx = i - 1
            btn = tk.Button(
                control_frame, text=f"{i} Players", 
                font=("Arial", 11, "bold"), bg=btn_colors[idx], fg="#11111B",
                width=10, height=2, bd=3, command=lambda num=i: self.start_game(num)
            )
            btn.grid(row=(i-2)//3, column=(i-2)%3, padx=5, pady=5)

        action_frame = tk.Frame(root, bg=self.bg_color)
        action_frame.pack(pady=15)

        tk.Button(action_frame, text="↻ Restart", font=("Arial", 11, "bold"), bg="#F9E2AF", fg="#11111B", width=12, height=2, bd=3, command=self.restart_round).grid(row=0, column=0, padx=10)
        tk.Button(action_frame, text="✖ Quit", font=("Arial", 11, "bold"), bg="#F38BA8", fg="#11111B", width=12, height=2, bd=3, command=self.quit_app).grid(row=0, column=1, padx=10)

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.update_loop()

    def start_game(self, num_players): self.game.start_game(num_players)
    def restart_round(self): self.game.start_game(max(2, self.game.started_with))
    def quit_app(self):
        self.game.running = False
        self.net.running = False
        self.root.destroy()

    def update_loop(self):
        state = self.game.state
        
        if state == "LOBBY":
            display_text = "LOBBY\nReady to start!"
            self.status_label.config(fg="#89B4FA") 
        elif state == "WAITING_READY":
            ready = sum(1 for p in self.game.active_players.values() if p['ready'])
            total = len(self.game.active_players)
            display_text = f"WAITING FOR PLAYERS\n{ready} / {total} Ready"
            self.status_label.config(fg="#89DCEB") 
        elif state == "PLAYING":
            time_left = max(0, int(self.game.round_end_time - time.time()))
            display_text = f"WHACK THOSE MOLES!\nTime Left: {time_left}s"
            # Turn text orange in the last 10 seconds!
            self.status_label.config(fg="#FAB387" if time_left <= 10 else "#A6E3A1")
        elif state == "ROUND_OVER":
            display_text = "ROUND OVER!\nEliminating Lowest Score..."
            self.status_label.config(fg="#F38BA8") 
        elif state == "WINNER":
            display_text = "WE HAVE A WINNER!"
            self.status_label.config(fg="#F38BA8") 
        else:
            display_text = state

        self.status_var.set(display_text)
        self.root.after(100, self.update_loop)

# --- Execution ---
if __name__ == "__main__":
    game = WhackAMoleGame()
    net = NetworkManager(game)
    net.start_bg()
    
    threading.Thread(target=game_thread_func, args=(game,), daemon=True).start()
    
    root = tk.Tk()
    gui = WhackAMoleGUI(root, game, net)
    print("\n🔨 Whack-A-Mole GUI Running. Check the new window!")
    root.mainloop()
    print("Exiting...")