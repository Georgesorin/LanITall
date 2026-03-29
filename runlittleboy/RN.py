import socket
import time
import threading
import random
import math
import psutil
import os
import wave
import struct

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
    print("Forging lightsabers and loading blasters... (Generating Sci-Fi SFX)")
    synthesize_laser('_sfx/blaster_0.wav', 2000, 200, 0.25, 'square')
    synthesize_laser('_sfx/blaster_1.wav', 2200, 250, 0.25, 'square')
    synthesize_laser('_sfx/blaster_2.wav', 1800, 150, 0.30, 'square')
    synthesize_laser('_sfx/blaster_3.wav', 2500, 300, 0.20, 'square')
    synthesize_laser('_sfx/blaster_4.wav', 1500, 100, 0.35, 'square')
    synthesize_laser('_sfx/success.wav', 400, 1200, 0.4, 'sine')
    synthesize_laser('_sfx/eliminate.wav', 300, 50, 0.6, 'sawtooth')
    synthesize_laser('_sfx/win.wav', 800, 2000, 1.5, 'sine')
    print("Sci-Fi SFX Generation Complete!")

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
                except: print(f"Failed to load {path}")
            else: print(f"Warning: Missing SFX {path}")

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
    if not interfaces:
        print("No active network interfaces found.")
        return None
        
    print("\n--- Network Selection ---")
    for i, (iface, ip, bcast) in enumerate(interfaces):
        print(f"[{i}] {iface} - {ip}")
        
    try:
        choice = int(input("\nSelect interface number: "))
        sel = interfaces[choice]
    except:
        sel = interfaces[0]
        print("Invalid choice, defaulting to 0.")
        
    print(f"Using {sel[0]} ({sel[1]})")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try: sock.bind((sel[1], 7800))
    except: pass
    
    pkt, r1, r2 = build_discovery_packet()
    try: sock.sendto(pkt, (sel[2], 4626))
    except: return None
    
    print(" Listening for Evil Eye devices...")
    sock.settimeout(0.5)
    end_time = time.time() + 3
    devices = []
    
    while time.time() < end_time:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) >= 30 and data[0] == 0x68 and data[1] == r1 and data[2] == r2:
                if addr[0] not in [d['ip'] for d in devices]:
                    model = data[6:13].decode(errors='ignore').strip('\x00')
                    devices.append({'ip': addr[0], 'model': model})
                    print(f" ✅ Found {model} at {addr[0]}")
        except socket.timeout: continue
        except: pass
        
    sock.close()
    
    if devices:
        print(f"🎯 Targeting {devices[0]['ip']}\n")
        return devices[0]['ip']
        
    print("❌ No devices found, using default 127.0.0.1\n")
    return "127.0.0.1"


# --- Game Logic ---

class ScavengerHunt:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        self.sound = SoundManager()
        
        # Extended Game States
        self.state = "LOBBY" # LOBBY, WAITING_START, ACTIVE, ROUND_WIN_ANIM, GAME_OVER
        self.num_players = 0
        self.current_round = 1
        self.max_rounds = 5
        self.round_winner = None
        self.overall_winners = []
        self.anim_timer = 0
        
        self.players = {} 
        
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}

    def start_game(self, count):
        with self.lock:
            self.num_players = count
            self.current_round = 1
            self.players = {i: {"score": 0, "misses": 0, "round_wins": 0, "target": None, "finished": False} for i in range(1, count + 1)}
            self.state = "WAITING_START"
            
            print(f"\n🎮 Game set for {count} players. Match is {self.max_rounds} rounds!")
            print(f"👉 Round {self.current_round}: Press and hold TILE 5 on ALL active walls to start!")

    def _spawn_target(self, p_id):
        other_walls = [w for w in range(1, 5) if w != p_id]
        # Exclude 5 and 6 so targets NEVER overlap with the Start/Finish tiles
        valid_leds = [1, 2, 3, 4, 7, 8, 9, 10] 
        
        while True:
            target_candidate = (random.choice(other_walls), random.choice(valid_leds))
            
            # Ensure this tile isn't already someone else's active target
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
                    
                    # Color the start tile (Tile 5)
                    if self.button_states[(p_id, 5)]:
                        # Tile turns into a significantly darker version of their assigned color when held
                        dark_color = (base_color[0] // 4, base_color[1] // 4, base_color[2] // 4)
                        self.active_leds[(p_id, 5)] = dark_color 
                    else:
                        # Glows bright with the player's normal assigned color when waiting
                        self.active_leds[(p_id, 5)] = base_color
                
                if all(self.button_states[(p, 5)] for p in self.players):
                    print(f"🚀 ROUND {self.current_round} START!")
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
                        self.active_leds[(p_id, 5)] = flash
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
                        print(f"\n🟢 Round {self.current_round} / {self.max_rounds}")
                        print("👉 Press and hold TILE 5 on ALL active walls to start the round!")
                    else:
                        self.state = "GAME_OVER"
                        best_score = max(p["round_wins"] for p in self.players.values())
                        self.overall_winners = [p for p, data in self.players.items() if data["round_wins"] == best_score]
                        
                        self.sound.play('win')
                        print("\n🏁 MATCH COMPLETE!")
                        for p, d in self.players.items():
                            print(f"  Player {p} -> {d['round_wins']} Round Wins | {d['misses']} Misses")
                        print(f"🏆 Overall Winner(s): {self.overall_winners}")

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
                                        print(f"👤 Player {p_id}: {data['score']}/5 caught!")
                                        if data["score"] >= 5:
                                            data["finished"] = True
                                            self.sound.play('success')
                                            print(f"🏃 Player {p_id} FINISHED! Run back to Wall {p_id}!")
                                        else:
                                            self._spawn_target(p_id)
                                    elif ch == data["target"][0]:
                                        data["misses"] += 1
                                        self.sound.play('eliminate')
                                        print(f"❌ Player {p_id} Missed! Total misses: {data['misses']}")
                                else:
                                    if ch == p_id and led in (5, 6):
                                        self.round_winner = p_id
                                        data["round_wins"] += 1
                                        self.sound.play('win')
                                        print(f"🎉 PLAYER {p_id} WINS ROUND {self.current_round}!")
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
        except Exception as e:
            print(f"Error binding recv socket: {e}")
            self.running = False

    def send_loop(self):
        while self.running:
            frame = self.game.render()
            self.send_packet(frame)
            time.sleep(0.02) 

    def build_packet(self, cmd_h, cmd_l, payload=b""):
        internal = bytearray([0x02, 0x00, 0x00, cmd_h, cmd_l]) + payload
        length = len(internal) - 1
        
        rand1 = random.randint(0, 127)
        rand2 = random.randint(0, 127)
        header = bytearray([0x75, rand1, rand2, (length >> 8) & 0xFF, length & 0xFF])
        
        pkt = header + internal
        pkt.append(calculate_checksum(pkt))
        return pkt

    def send_packet(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1
        seq_h, seq_l = (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF
        
        p1 = self.build_packet(0x33, 0x44, bytearray([seq_h, seq_l, 0x00, 0x00, 0x00]))
        
        fff0_payload = bytearray()
        for _ in range(4): fff0_payload += bytes([0x00, 11])
        p2 = self.build_packet(0xFF, 0xF0, fff0_payload)
        
        data_payload = bytearray([0x00, 0x01, (len(frame_data) >> 8) & 0xFF, len(frame_data) & 0xFF]) + frame_data
        p3 = self.build_packet(0x88, 0x77, data_payload)
        
        p4 = self.build_packet(0x55, 0x66, bytearray([seq_h, seq_l, 0x00, 0x00, 0x00]))
        
        try:
            target = (self.target_ip, UDP_SEND_PORT)
            self.sock_send.sendto(p1, target); time.sleep(0.008)
            self.sock_send.sendto(p2, target); time.sleep(0.008)
            self.sock_send.sendto(p3, target); time.sleep(0.008)
            self.sock_send.sendto(p4, target); time.sleep(0.008) 
        except:
            pass

    def recv_loop(self):
        while self.running:
            try:
                data, _ = self.sock_recv.recvfrom(2048)
                if len(data) == 687 and data[0] == 0x88:
                    with self.game.lock:
                        for ch in range(1, 5):
                            base = 2 + (ch - 1) * 171
                            for led in range(11):
                                is_pressed = (data[base + 1 + led] == 0xCC)
                                self.game.button_states[(ch, led)] = is_pressed
            except:
                pass

    def start_bg(self):
        t1 = threading.Thread(target=self.send_loop, daemon=True)
        t2 = threading.Thread(target=self.recv_loop, daemon=True)
        t1.start()
        t2.start()

def game_thread_func(game):
    while game.running:
        game.tick()
        time.sleep(0.01)

# --- Execution ---
if __name__ == "__main__":
    game = ScavengerHunt()
    net = NetworkManager(game)
    net.start_bg()
    
    gt = threading.Thread(target=game_thread_func, args=(game,), daemon=True)
    gt.start()
    
    print("\n🏃 Scavenger Hunt Console Server Running.")
    print("Commands: 'start <num_players>' (max 4), 'quit'")
    
    try:
        while game.running:
            cmd = input("> ").strip().lower()
            if cmd in ['quit', 'exit']:
                game.running = False
                break
            elif cmd.startswith('start'):
                try:
                    num = int(cmd.split()[1])
                    if 2 <= num <= 4:
                        game.start_game(num)
                    else:
                        print("Please enter a number between 2 and 4.")
                except:
                    print("Usage: start <num_players>")
            else:
                 print("Unknown command.")
    except KeyboardInterrupt:
        game.running = False

    net.running = False
    print("Exiting...")