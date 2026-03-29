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

import SoundGenerator

# --- Evil Eye Constants ---
UDP_SEND_PORT = 4626
UDP_LISTEN_PORT = 7800

# Custom checksum array from the documentation
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
    idx = sum(data) & 0xFF
    return PASSWORD_ARRAY[idx]


# --- Network Discovery Flow ---

def get_local_interfaces():
    """Identifies active network interfaces for discovery."""
    interfaces = []
    for iface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                bcast = addr.broadcast if addr.broadcast else "255.255.255.255"
                interfaces.append((iface_name, addr.address, bcast))
    return interfaces

def build_discovery_packet():
    rand1, rand2 = random.randint(0, 127), random.randint(0, 127)
    payload = bytearray([0x0A, 0x02, *b"KX-HC04", 0x03, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x14])
    pkt = bytearray([0x67, rand1, rand2, len(payload)]) + payload
    pkt.append(calculate_checksum(pkt))
    return pkt, rand1, rand2

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

class AnimalSoundsGame:
    def __init__(self):
        self.running = True
        self.lock = threading.RLock()
        
        self.sound = SoundManager()
        
        # --- Game States ---
        # LOBBY, INTRO_SEQUENCE, SHOWING_SEQUENCE, WAITING_INPUT, ROUND_SUCCESS, WINNER, GAMEOVER
        self.state = "LOBBY" 
        
        self.active_players = {} 
        self.started_with = 0
        
        self.sequence = []
        self.show_index = 0
        self.show_timer = 0
        self.played_step_sound = False
        
        # 4 Walls, 11 LEDs per wall (Index 0 is the Eye, 1-10 are buttons)
        self.button_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.prev_states = {(ch, led): False for ch in range(1, 5) for led in range(11)}
        self.active_leds = {}
        
        # 5 distinct colors for the 5 buttons
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

            if self.state in ["LOBBY", "WINNER", "GAMEOVER"]:
                pulse = int(127 + 127 * math.sin(now * 3))
                color = (0, 255, 0) if self.state == "WINNER" else (pulse, 0, 0)
                for ch in range(1, 5): self.active_leds[(ch, 0)] = color # Eye is at index 0
                return

            if self.state == "INTRO_SEQUENCE":
                # Show each animal sound to the players for 1 second each
                if now - self.show_timer > 1.0:
                    self.show_index += 1
                    self.show_timer = now
                    self.played_step_sound = False

                if self.show_index < 5:
                    val = self.show_index
                    if not self.played_step_sound:
                        self.sound.play(f'animal_{val}')
                        self.played_step_sound = True
                    
                    for pid, p in self.active_players.items():
                        # Left side uses 1-5, Right side uses 6-10
                        led_idx = val + 1 if p['side'] == 'left' else val + 6
                        self.active_leds[(p['wall'], led_idx)] = self.COLORS[val]
                else:
                    # Intro finished, start the actual game sequence
                    self.sequence = [random.randint(0, 4)]
                    self.state = "SHOWING_SEQUENCE"
                    self.show_index = 0
                    self.show_timer = time.time()
                    self.played_step_sound = False
                return

            if self.state == "ROUND_SUCCESS":
                for ch in range(1, 5): self.active_leds[(ch, 0)] = (0, 255, 0)
                
                if now - self.show_timer > 1.5:
                    self.state = "SHOWING_SEQUENCE"
                    self.show_index = 0
                    self.show_timer = now
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
                        if led == 0: continue # Ignore the Eye
                        if self.button_states[(ch, led)]:
                            side = 'left' if led <= 5 else 'right'
                            val = led - 1 if side == 'left' else led - 6
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
        if self.state != "WAITING_INPUT": return
        if led == 0: return 

        side = 'left' if led <= 5 else 'right'
        val = led - 1 if side == 'left' else led - 6
        pid = (ch - 1) * 2 + (0 if side == 'left' else 1)

        if pid not in self.active_players: return 
        
        p = self.active_players[pid]
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
            print(f"❌ Player {pid} Eliminated!")
            del self.active_players[pid]
            self.check_round_end()

    def check_round_end(self):
        if len(self.active_players) == 0:
            print("💀 GAME OVER! Everyone was eliminated.")
            self.state = "GAMEOVER"
            return
            
        if len(self.active_players) == 1 and self.started_with > 1:
            winner_id = list(self.active_players.keys())[0]
            print(f"🏆 WE HAVE A WINNER: Player {winner_id}!")
            self.sound.play('win')
            self.state = "WINNER"
            return

        all_done = all(p['done'] for p in self.active_players.values())
        if all_done:
            print(f"✅ Round Passed! {len(self.active_players)} players surviving.")
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

    def start_game(self, num_players):
        with self.lock:
            if num_players > 8: num_players = 8
            if num_players < 1: num_players = 1
            
            self.started_with = num_players
            self.active_players.clear()
            
            for i in range(num_players):
                wall = (i // 2) + 1
                side = 'left' if i % 2 == 0 else 'right'
                self.active_players[i] = {
                    'wall': wall,
                    'side': side,
                    'input_index': 0,
                    'done': False
                }
                
            print(f"\n🎮 Started Animal Sounds with {num_players} players.")
            
            # Start the 5-step Intro Sequence
            self.state = "INTRO_SEQUENCE"
            self.show_index = 0
            self.show_timer = time.time()
            self.played_step_sound = False


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
    game = AnimalSoundsGame()
    net = NetworkManager(game)
    net.start_bg()
    
    gt = threading.Thread(target=game_thread_func, args=(game,), daemon=True)
    gt.start()
    
    print("\n🦁 Animal Sounds Console Server Running.")
    print("Commands: 'start <num_players>' (max 8), 'quit'")
    
    try:
        while game.running:
            cmd = input("> ").strip().lower()
            if cmd in ['quit', 'exit']:
                game.running = False
                break
            elif cmd.startswith('start'):
                try:
                    num = int(cmd.split()[1])
                    game.start_game(num)
                except:
                    print("Usage: start <num_players>")
            else:
                 print("Unknown command.")
    except KeyboardInterrupt:
        game.running = False

    net.running = False
    print("Exiting...")