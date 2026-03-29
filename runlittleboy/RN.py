import socket
import time
import threading
import random
import math
import psutil
import os

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


# --- Sound Manager ---

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
        if not os.path.exists("_sfx/animal_0.wav"):
            print("Generating Animal SFX...")
            SoundGenerator.generate_all()

        sfx_files = {
            'animal_0': '_sfx/animal_0.wav',
            'animal_1': '_sfx/animal_1.wav',
            'animal_2': '_sfx/animal_2.wav',
            'animal_3': '_sfx/animal_3.wav',
            'animal_4': '_sfx/animal_4.wav',
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

# --- Game Logic ---

class ScavengerHunt:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        self.state = "LOBBY" # LOBBY, WAITING_START, ACTIVE, WINNER
        self.num_players = 0
        self.players = {} # {id: {"score": 0, "misses": 0, "target": (w, l), "finished": False}}
        
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}

    def start_game(self, count):
        with self.lock:
            self.num_players = count
            self.players = {i: {"score": 0, "misses": 0, "target": None, "finished": False} for i in range(1, count + 1)}
            self.state = "WAITING_START"
            print(f"\n🎮 Game set for {count} players. Press TILE 5 on ANY active wall to start!")

    def _spawn_target(self, p_id):
        # Target appears on any wall EXCEPT the player's home wall
        other_walls = [w for w in range(1, 5) if w != p_id]
        self.players[p_id]["target"] = (random.choice(other_walls), random.randint(1, 10))

    def tick(self):
        now = time.time()
        with self.lock:
            self.active_leds.clear()

            if self.state in ["LOBBY", "WINNER"]:
                pulse = int(127 + 127 * math.sin(now * 3))
                color = (0, 255, 0) if self.state == "WINNER" else (pulse, 0, 0)
                for ch in range(1, 5): self.active_leds[(ch, 0)] = color
                return

            if self.state == "WAITING_START":
                pulse = int(127 + 127 * math.sin(now * 10))
                for p_id in self.players:
                    self.active_leds[(p_id, 0)] = (pulse, pulse, pulse) # Pulse eyes white
                
                # Check if Tile 5 is pressed on ANY active player wall (Simulator friendly)
                if any(self.button_states[(p, 5)] for p in self.players):
                    print("🚀 READY! GO!")
                    self.state = "ACTIVE"
                    for p_id in self.players: self._spawn_target(p_id)

            elif self.state == "ACTIVE":
                for p_id, data in self.players.items():
                    color = WALL_COLORS[p_id]
                    self.active_leds[(p_id, 0)] = color # Eye shows player's color
                    
                    if not data["finished"]:
                        t_w, t_l = data["target"]
                        self.active_leds[(t_w, t_l)] = color # Target is player's color
                    else:
                        # Home phase: pulse 5 & 6 to signal return
                        flash = color if int(now * 5) % 2 == 0 else (0, 0, 0)
                        self.active_leds[(p_id, 5)] = flash
                        self.active_leds[(p_id, 6)] = flash

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
                                    # Hit the exact target
                                    if (ch, led) == data["target"]:
                                        data["score"] += 1
                                        print(f"👤 Player {p_id}: {data['score']}/5 caught!")
                                        if data["score"] >= 5:
                                            data["finished"] = True
                                            print(f"🏃 Player {p_id} FINISHED! Run back to Wall {p_id}!")
                                        else:
                                            self._spawn_target(p_id)
                                    # Hit a tile on the target wall, but it's the wrong one (Miss)
                                    elif ch == data["target"][0]:
                                        data["misses"] += 1
                                        print(f"❌ Player {p_id} Missed! Total misses: {data['misses']}")
                                else:
                                    # Win by hitting home base (Tile 5 or 6 on YOUR wall)
                                    if ch == p_id and led in (5, 6):
                                        print(f"🏆 PLAYER {p_id} WINS THE GAME! (Total Misses: {data['misses']})")
                                        self.state = "WINNER"
                    
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