import socket
import time
import threading
import random
import math
import psutil
import os
import wave
import struct
import tkinter as tk
from tkinter import font as tkfont

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# --- Evil Eye Constants ---
UDP_SEND_PORT = 4626   # Simulator Port IN
UDP_LISTEN_PORT = 7800 # Simulator Port OUT

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

WALL_COLORS = {
    1: (255, 0, 0),    # Wall 1: Red
    2: (0, 255, 0),    # Wall 2: Green
    3: (0, 0, 255),    # Wall 3: Blue
    4: (255, 255, 0)   # Wall 4: Yellow
}

def calculate_checksum(data: bytearray) -> int:
    idx = sum(data) & 0xFF
    return PASSWORD_ARRAY[idx]

# --- SFX Generation Logic ---

def synthesize_laser(filename, start_freq, end_freq, duration, wave_type='square', volume=0.3):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    os.makedirs('_sfx', exist_ok=True)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        phase = 0.0
        for i in range(num_samples):
            t = i / sample_rate
            freq = start_freq * ((end_freq / start_freq) ** (t / duration))
            phase += 2 * math.pi * freq / sample_rate
            
            if wave_type == 'square':
                sample = 1.0 if math.sin(phase) > 0 else -1.0
            elif wave_type == 'sawtooth':
                sample = 2.0 * (phase / (2 * math.pi) - math.floor(phase / (2 * math.pi) + 0.5))
            else: 
                sample = math.sin(phase)
            
            envelope = max(0.0, 1.0 - (t / duration))
            audio_val = int(sample * envelope * volume * 32767)
            audio_val = max(-32768, min(32767, audio_val))
            
            wav_file.writeframes(struct.pack('<h', audio_val))

def generate_all_sfx():
    print("Generating Sci-Fi SFX...")
    synthesize_laser('_sfx/blaster_0.wav', 2000, 200, 0.25, 'square')
    synthesize_laser('_sfx/blaster_1.wav', 2200, 250, 0.25, 'square')
    synthesize_laser('_sfx/blaster_2.wav', 1800, 150, 0.30, 'square')
    synthesize_laser('_sfx/blaster_3.wav', 2500, 300, 0.20, 'square')
    synthesize_laser('_sfx/blaster_4.wav', 1500, 100, 0.35, 'square')
    synthesize_laser('_sfx/success.wav', 400, 1200, 0.4, 'sine')
    synthesize_laser('_sfx/eliminate.wav', 300, 50, 0.6, 'sawtooth')
    synthesize_laser('_sfx/win.wav', 800, 2000, 1.5, 'sine')

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
                print("Pygame disabled.")
        except Exception as e:
            self.enabled = False

    def _load_sounds(self):
        if not os.path.exists("_sfx/blaster_0.wav"):
            generate_all_sfx()

        sfx_files = {
            'animal_0': '_sfx/blaster_0.wav',
            'animal_1': '_sfx/blaster_1.wav',
            'animal_2': '_sfx/blaster_2.wav',
            'animal_3': '_sfx/blaster_3.wav',
            'animal_4': '_sfx/blaster_4.wav',
            'success': '_sfx/success.wav',
            'eliminate': '_sfx/eliminate.wav',
            'win': '_sfx/win.wav',
        }
        
        for name, path in sfx_files.items():
            if os.path.exists(path):
                try: self.sounds[name] = pygame.mixer.Sound(path)
                except: pass

    def play(self, name):
        if not self.enabled: return
        if name in self.sounds:
            try: self.sounds[name].play()
            except: pass

# --- Discovery Flow ---
def get_local_interfaces():
    interfaces = []
    for iface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                bcast = addr.broadcast if addr.broadcast else "255.255.255.255"
                interfaces.append((iface_name, addr.address, bcast))
    return interfaces

def build_discovery_packet():
    r1, r2 = random.randint(0, 127), random.randint(0, 127)
    payload = bytearray([0x0A, 0x02, *b"KX-HC04", 0x03, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x14])
    pkt = bytearray([0x67, r1, r2, len(payload)]) + payload
    pkt.append(calculate_checksum(pkt))
    return pkt, r1, r2

def run_discovery_flow():
    interfaces = get_local_interfaces()
    if not interfaces: return "127.0.0.1"
        
    print("\n--- Network Selection ---")
    for i, (iface, ip, bcast) in enumerate(interfaces):
        print(f"[{i}] {iface} - {ip}")
        
    try:
        choice = int(input("\nSelect interface number: "))
        sel = interfaces[choice]
    except:
        sel = interfaces[0]
        
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try: sock.bind((sel[1], 7800))
    except: pass
    
    pkt, r1, r2 = build_discovery_packet()
    try: sock.sendto(pkt, (sel[2], 4626))
    except: return "127.0.0.1"
    
    sock.settimeout(0.5)
    end_time = time.time() + 2
    while time.time() < end_time:
        try:
            data, addr = sock.recvfrom(1024)
            if data[0] == 0x68 and data[1] == r1 and data[2] == r2:
                sock.close()
                return addr[0]
        except: pass
    sock.close()
    return "127.0.0.1"

# --- Game Logic ---

class ScavengerHunt:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        self.sound = SoundManager()
         
        self.state = "LOBBY"
        self.num_players = 0
        self.current_round = 1
        self.max_rounds = 8
        self.round_winner = None
        self.overall_winners = []
        self.anim_timer = 0
        self.round_history = [] 
        
        self.players = {} 
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}

    def start_game(self, count):
        with self.lock:
            self.num_players = count
            self.current_round = 1
            self.round_history.clear()
            self.players = {i: {"score": 0, "misses": 0, "round_wins": 0, "target": None, "finished": False} for i in range(1, count + 1)}
            self.state = "WAITING_START"

    def _spawn_target(self, p_id):
        other_walls = [w for w in range(1, 5) if w != p_id]
        valid_leds = [1, 2, 3, 4, 7, 8, 9, 10] 
        
        while True:
            target_candidate = (random.choice(other_walls), random.choice(valid_leds))
            is_occupied = False
            for other_p, data in self.players.items():
                if other_p != p_id and data.get("target") == target_candidate:
                    is_occupied = True
                    break
                    
            if not is_occupied:
                self.players[p_id]["target"] = target_candidate
                break

    def tick(self):
        now = time.time()
        with self.lock:
            self.active_leds.clear()

            if self.state == "LOBBY":
                pulse = int(127 + 127 * math.sin(now * 3))
                color = (pulse, 0, 0)
                for ch in range(1, 5): self.active_leds[(ch, 0)] = color
                return

            if self.state == "WAITING_START":
                pulse = int(127 + 127 * math.sin(now * 10))
                for p_id in self.players:
                    self.active_leds[(p_id, 0)] = (pulse, pulse, pulse) 
                    base_color = WALL_COLORS[p_id]
                    
                    if self.button_states[(p_id, 6)]:
                        dark_color = (base_color[0] // 4, base_color[1] // 4, base_color[2] // 4)
                        self.active_leds[(p_id, 6)] = dark_color 
                    else:
                        self.active_leds[(p_id, 6)] = base_color
                
                if all(self.button_states[(p, 6)] for p in self.players):
                    self.sound.play('success')
                    self.state = "ACTIVE"
                    for p_id in self.players: 
                        self.players[p_id]["score"] = 0
                        self.players[p_id]["finished"] = False
                        self._spawn_target(p_id)

            elif self.state == "ACTIVE":
                for p_id, data in self.players.items():
                    color = WALL_COLORS[p_id]
                    self.active_leds[(p_id, 0)] = color 
                    
                    if not data["finished"]:
                        t_w, t_l = data["target"]
                        self.active_leds[(t_w, t_l)] = color 
                    else:
                        flash = color if int(now * 5) % 2 == 0 else (0, 0, 0)
                        self.active_leds[(p_id, 6)] = flash

            elif self.state == "ROUND_WIN_ANIM":
                elapsed = now - self.anim_timer
                if elapsed < 3.0:
                    blink = WALL_COLORS[self.round_winner] if int(now * 10) % 2 == 0 else (0,0,0)
                    for led in range(11): 
                        self.active_leds[(self.round_winner, led)] = blink
                        
                    pulse = int(50 + 50 * math.sin(now * 5))
                    for p in self.players:
                        if p != self.round_winner:
                            self.active_leds[(p, 0)] = (pulse, pulse, pulse)
                else:
                    if self.current_round < self.max_rounds:
                        self.current_round += 1
                        self.state = "WAITING_START"
                    else:
                        self.state = "GAME_OVER"
                        best_score = max(p["round_wins"] for p in self.players.values())
                        self.overall_winners = [p for p, data in self.players.items() if data["round_wins"] == best_score]
                        self.sound.play('win')

            elif self.state == "GAME_OVER":
                rainbow = (int(127+127*math.sin(now)), int(127+127*math.sin(now+2)), int(127+127*math.sin(now+4)))
                for win_id in self.overall_winners:
                    for led in range(11):
                        self.active_leds[(win_id, led)] = rainbow

            self.process_inputs()

    def process_inputs(self):
        with self.lock:
            for ch in range(1, 5):
                for led in range(1, 11):
                    is_pressed = self.button_states[(ch, led)]
                    was_pressed = self.prev_states[(ch, led)]
                    
                    if is_pressed and not was_pressed:
                        if self.state == "ACTIVE":
                            for p_id, data in self.players.items():
                                if not data["finished"]:
                                    if (ch, led) == data["target"]:
                                        data["score"] += 1
                                        self.sound.play(f'animal_{random.randint(0, 4)}')
                                        if data["score"] >= 5:
                                            data["finished"] = True
                                            self.sound.play('success')
                                        else:
                                            self._spawn_target(p_id)
                                    elif ch == data["target"][0]:
                                        data["misses"] += 1
                                        self.sound.play('eliminate')
                                else:
                                    if ch == p_id and led == 6:
                                        self.round_winner = p_id
                                        data["round_wins"] += 1
                                        self.sound.play('win')
                                        self.round_history.append(f"Runda {self.current_round}: Jucătorul {p_id}")
                                        self.state = "ROUND_WIN_ANIM"
                                        self.anim_timer = time.time()
                    
                    self.prev_states[(ch, led)] = is_pressed

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
        except:
            self.running = False

    def send_loop(self):
        while self.running:
            frame = self.game.render()
            self.send_packet(frame)
            time.sleep(0.02) 

    def build_packet(self, cmd_h, cmd_l, payload=b""):
        internal = bytearray([0x02, 0x00, 0x00, cmd_h, cmd_l]) + payload
        length = len(internal) - 1
        header = bytearray([0x75, random.randint(0, 127), random.randint(0, 127), (length >> 8) & 0xFF, length & 0xFF])
        pkt = header + internal
        pkt.append(calculate_checksum(pkt))
        return pkt

    def send_packet(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1
        seq_h, seq_l = (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF
        
        p1 = self.build_packet(0x33, 0x44, bytearray([seq_h, seq_l, 0x00, 0x00, 0x00]))
        p2 = self.build_packet(0xFF, 0xF0, bytes([0x00, 11] * 4))
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

# --- Graphical User Interfaces ---
def build_gui(game, net):
    # Fereastra 1: Control (Game Master)
    root = tk.Tk()
    root.title("Control Panel - Scavenger Hunt")
    root.geometry("600x500")
    root.configure(bg="#1e1e2e")
    root.resizable(False, False)

    # Fereastra 2: Ecranul Jucătorilor (Camera)
    player_screen = tk.Toplevel(root)
    player_screen.title("Ecran Cameră Jucători")
    player_screen.geometry("1000x600")
    player_screen.configure(bg="#11111b")

    # Fonturi
    title_font = tkfont.Font(family="Helvetica", size=24, weight="bold")
    body_font = tkfont.Font(family="Helvetica", size=14)
    btn_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
    
    # --- UI Ecran Control (Root) ---
    tk.Label(root, text="Scavenger Hunt Control", font=title_font, bg="#1e1e2e", fg="#cdd6f4").pack(pady=(20, 10))

    frame_btns = tk.Frame(root, bg="#1e1e2e")
    frame_btns.pack(pady=20)

    def start_match(num):
        game.start_game(num)

    tk.Button(frame_btns, text="2 Players", font=btn_font, bg="#89b4fa", fg="#1e1e2e", activebackground="#b4befe", width=10, command=lambda: start_match(2)).grid(row=0, column=0, padx=10, pady=10)
    tk.Button(frame_btns, text="3 Players", font=btn_font, bg="#f9e2af", fg="#1e1e2e", activebackground="#f5e0dc", width=10, command=lambda: start_match(3)).grid(row=0, column=1, padx=10, pady=10)
    tk.Button(frame_btns, text="4 Players", font=btn_font, bg="#f38ba8", fg="#1e1e2e", activebackground="#f5c2e7", width=10, command=lambda: start_match(4)).grid(row=0, column=2, padx=10, pady=10)

    frame_winners = tk.Frame(root, bg="#1e1e2e")
    frame_winners.pack(pady=10)
    tk.Label(frame_winners, text="Istoric Rânde (GM View):", font=btn_font, bg="#1e1e2e", fg="#cdd6f4").pack()
    lbl_control_winners = tk.Label(frame_winners, text="Așteptăm startul...", font=body_font, bg="#1e1e2e", fg="#bac2de")
    lbl_control_winners.pack(pady=10)

    def quit_server():
        game.running = False
        net.running = False
        root.destroy()

    tk.Button(root, text="Oprește Jocul", font=tkfont.Font(family="Helvetica", size=12, weight="bold"), bg="#313244", fg="#f38ba8", width=15, command=quit_server).pack(side="bottom", pady=20)
    root.protocol("WM_DELETE_WINDOW", quit_server)
    player_screen.protocol("WM_DELETE_WINDOW", quit_server)

    # --- UI Ecran Jucători (Player Screen) ---
    player_title_font = tkfont.Font(family="Helvetica", size=48, weight="bold")
    player_inst_font = tkfont.Font(family="Helvetica", size=32)
    player_data_font = tkfont.Font(family="Helvetica", size=24)

    lbl_player_status = tk.Label(player_screen, text="Așteptăm Jucătorii", font=player_title_font, bg="#11111b", fg="#cdd6f4", wraplength=900, justify="center")
    lbl_player_status.pack(pady=(80, 20), expand=True)

    lbl_player_inst = tk.Label(player_screen, text="", font=player_inst_font, bg="#11111b", fg="#a6adc8", wraplength=900, justify="center")
    lbl_player_inst.pack(pady=20, expand=True)

    lbl_player_stats = tk.Label(player_screen, text="", font=player_data_font, bg="#11111b", fg="#f38ba8", justify="center")
    lbl_player_stats.pack(pady=20, expand=True)

    # --- Funcția de Polling ---
    def update_gui():
        with game.lock:
            # Update Control Panel
            if game.state == "LOBBY":
                lbl_control_winners.config(text="În lobby.")
            elif not game.round_history and game.state != "LOBBY":
                lbl_control_winners.config(text="Runda 1 în desfășurare...")
            else:
                lbl_control_winners.config(text=" | ".join(game.round_history))

            # Update Player Screen
            lbl_player_stats.config(text="") # Curățăm stats by default
            
            if game.state == "LOBBY":
                lbl_player_status.config(text="SCAVENGER HUNT", fg="#cdd6f4")
                lbl_player_inst.config(text="Jocul va începe curând.\nAșteptați instrucțiunile Game Master-ului.")
                
            elif game.state == "WAITING_START":
                lbl_player_status.config(text=f"RUNDA {game.current_round}", fg="#f9e2af")
                lbl_player_inst.config(text="Mergeți la zidul vostru și țineți apăsat\nTILE 6 (Butonul Central) pentru a începe!")
                
            elif game.state == "ACTIVE":
                lbl_player_status.config(text="CĂUTAȚI-VĂ CULOAREA!", fg="#89b4fa")
                lbl_player_inst.config(text="Loviți de 5 ori, apoi întoarceți-vă rapid\nla TILE 6 pentru a câștiga runda!")
                
            elif game.state == "ROUND_WIN_ANIM":
                lbl_player_status.config(text=f"RUNDA CÂȘTIGATĂ!", fg="#a6e3a1")
                lbl_player_inst.config(text=f"Jucătorul {game.round_winner} a fost cel mai rapid!")
                
            elif game.state == "GAME_OVER":
                lbl_player_status.config(text="JOC TERMINAT!", fg="#f38ba8")
                winners_str = ", ".join([str(w) for w in game.overall_winners])
                lbl_player_inst.config(text=f"Câștigător Final: Jucătorul {winners_str}!")
                
                # Afișăm Scorurile și Ratările la final
                stats_text = "Statistici Finale:\n\n"
                for p, d in game.players.items():
                    stats_text += f"Jucătorul {p}: {d['round_wins']} Runde Câștigate | {d['misses']} Ratări\n"
                lbl_player_stats.config(text=stats_text)

        root.after(200, update_gui)

    update_gui()
    root.mainloop()

# --- Execution ---
if __name__ == "__main__":
    game = ScavengerHunt()
    net = NetworkManager(game)
    net.start_bg()
    
    gt = threading.Thread(target=game_thread_func, args=(game,), daemon=True)
    gt.start()
    
    build_gui(game, net)
    print("Exiting...")