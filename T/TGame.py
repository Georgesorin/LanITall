import socket
import time
import threading
import random
import math
import json
import tkinter as tk
import queue
import pygame

# Inițializare modul de sunet
pygame.mixer.init()

# --- Setări de Rețea UDP Matrice ---
UDP_SEND_IP = "255.255.255.255"
UDP_SEND_PORT = 1068
UDP_LISTEN_PORT = 1070

# --- Setari Retea GUI (Local IPC) ---
GUI_SEND_PORT = 1071
GUI_LISTEN_PORT = 1072
LOCAL_IP = "127.0.0.1"

# --- Parametri Matrice ---
NUM_CHANNELS = 8
LEDS_PER_CHANNEL = 64
FRAME_DATA_LENGTH = NUM_CHANNELS * LEDS_PER_CHANNEL * 3 # 1536 bytes
BOARD_WIDTH = 16
BOARD_HEIGHT = 32

# --- Culori Statice (R, G, B) ---
BLACK   = (0, 0, 0)
GREEN   = (0, 255, 0)
MAGENTA = (255, 0, 255)
RED     = (255, 0, 0)
BLUE    = (0, 0, 255)
YELLOW  = (255, 255, 0)
CYAN    = (0, 255, 255)
WHITE   = (255, 255, 255)

# --- Font Data ---
FONT = {
    1: [(3,0), (4,0), (2,1), (3,1), (4,1), (1,2), (2,2), (3,2), (4,2), (3,3), (4,3), (3,4), (4,4), (3,5), (4,5), (3,6), (4,6), (3,7), (4,7), (3,8), (4,8), (3,9), (4,9), (3,10), (4,10), (1,11), (2,11), (3,11), (4,11), (5,11), (6,11)],
    2: [(1,0), (2,0), (3,0), (4,0), (5,0), (6,0), (0,1), (1,1), (6,1), (7,1), (0,2), (1,2), (6,2), (7,2), (6,3), (7,3), (5,4), (6,4), (4,5), (5,5), (3,6), (4,6), (2,7), (3,7), (1,8), (2,8), (0,9), (1,9), (0,10), (1,10), (0,11), (1,11), (2,11), (3,11), (4,11), (5,11), (6,11), (7,11)],
    3: [(1,0), (2,0), (3,0), (4,0), (5,0), (6,0), (0,1), (1,1), (6,1), (7,1), (0,2), (1,2), (6,2), (7,2), (6,3), (7,3), (4,4), (5,4), (6,4), (2,5), (3,5), (4,5), (5,5), (4,6), (5,6), (6,6), (6,7), (7,7), (6,8), (7,8), (0,9), (1,9), (6,9), (7,9), (0,10), (1,10), (6,10), (7,10), (1,11), (2,11), (3,11), (4,11), (5,11), (6,11)],
    'W': [(0,0),(0,1),(0,2),(0,3),(0,4), (4,0),(4,1),(4,2),(4,3),(4,4), (1,3),(2,2),(3,3)],
    'I': [(0,0),(1,0),(2,0), (1,1),(1,2),(1,3), (0,4),(1,4),(2,4)],
    'N': [(0,0),(0,1),(0,2),(0,3),(0,4), (3,0),(3,1),(3,2),(3,3),(3,4), (1,1),(2,2)],
    'P': [(0,0),(1,0),(2,0), (0,1),(2,1), (0,2),(1,2),(2,2), (0,3), (0,4)],
    '+': [(1,1), (0,2),(1,2),(2,2), (1,3)],
    '1': [(1,0), (0,1),(1,1), (1,2), (1,3), (0,4),(1,4),(2,4)],
    '2': [(0,0),(1,0),(2,0), (2,1), (0,2),(1,2),(2,2), (0,3), (0,4),(1,4),(2,4)],
    '3': [(0,0),(1,0),(2,0), (2,1), (0,2),(1,2),(2,2), (2,3), (0,4),(1,4),(2,4)],
    '4': [(0,0),(2,0), (0,1),(2,1), (0,2),(1,2),(2,2), (2,3), (2,4)],
    '5': [(0,0),(1,0),(2,0), (0,1), (0,2),(1,2),(2,2), (2,3), (0,4),(1,4),(2,4)],
    '6': [(0,0),(1,0),(2,0), (0,1), (0,2),(1,2),(2,2), (0,3),(2,3), (0,4),(1,4),(2,4)],
    '7': [(0,0),(1,0),(2,0), (2,1), (1,2), (1,3), (1,4)],
    '8': [(0,0),(1,0),(2,0), (0,1),(2,1), (0,2),(1,2),(2,2), (0,3),(2,3), (0,4),(1,4),(2,4)]
}

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

def calculate_checksum(data_bytes):
    return PASSWORD_ARRAY[sum(data_bytes) & 0xFF]

def set_pixel(buffer, target_x, target_y, r, g, b):
    if target_x < 0 or target_x >= 16 or target_y < 0 or target_y >= 32: return
    channel = target_y // 4
    row = target_y % 4
    idx = (row * 16 + target_x) if row % 2 == 0 else (row * 16 + (15 - target_x))
    offset = idx * 24 + channel
    if offset + 16 < len(buffer):
        buffer[offset] = g
        buffer[offset + 8] = r
        buffer[offset + 16] = b

def get_xy_from_flat(flat_idx):
    ch = flat_idx // 64
    led_idx = flat_idx % 64
    row = led_idx // 16
    col = led_idx % 16
    y = ch * 4 + row
    x = col if row % 2 == 0 else 15 - col
    return x, y

def is_playable(x, y):
    return 2 <= x <= 13 and 2 <= y <= 29

def draw_symbol(buffer, symbol, offset_x, offset_y, color):
    if symbol in FONT:
        for px, py in FONT[symbol]:
            set_pixel(buffer, offset_x + px, offset_y + py, *color)

def generate_playable_spiral():
    coords = []
    top, bottom = 2, 29
    left, right = 2, 13
    while top <= bottom and left <= right:
        for x in range(left, right + 1): coords.append((x, top))
        top += 1
        for y in range(top, bottom + 1): coords.append((right, y))
        right -= 1
        if top <= bottom:
            for x in range(right, left - 1, -1): coords.append((x, bottom))
            bottom -= 1
        if left <= right:
            for y in range(bottom, top - 1, -1): coords.append((left, y))
            left += 1
    return coords

SPIRAL_PATH = generate_playable_spiral()

class SequenceGame:
    def __init__(self):
        self.running = True
        self.button_states = [False] * 512
        self.prev_button_states = [False] * 512

        self.num_players = 0
        self.active_players = []
        self.current_player_idx = 0

        self.scores = []
        self.sequence = []
        self.current_step = 0

        self.state = "WAITING_FOR_START"
        self.state_time = 0.0
        self.wrong_tile = None

        self.is_final_win = False
        self.round_winner = 1

    def play_sound(self, filename):
        try:
            pygame.mixer.Sound(f"_sfx/{filename}").play()
        except Exception:
            pass

    def start_game(self, num_players, reset_scores=True):
        if not (2 <= num_players <= 8):
            print("Jocul necesită între 2 și 8 jucători!")
            return

        self.num_players = num_players
        self.active_players = [True] * num_players
        self.current_player_idx = 0
        self.sequence = []
        self.current_step = 0

        if reset_scores or len(self.scores) != num_players:
            self.scores = [0] * num_players
            self.is_final_win = False
            print("\n=== Scoruri resetate. Primul la 3 puncte câștigă jocul! ===")

        self.state = "COUNTDOWN"
        self.state_time = time.time()
        print(f"\nRunda începe pentru {num_players} jucători!")

    def restart_game(self):
        if self.num_players >= 2:
            print(f"\n--- Se pregătește o nouă rundă ---")
            self.state = "RESTARTING"
            self.state_time = time.time()
        else:
            print("Niciun joc nu a fost început încă. Folosește mai întâi 'start <num_jucători>'.")

    def advance_to_next_player(self):
        for _ in range(self.num_players):
            self.current_player_idx = (self.current_player_idx + 1) % self.num_players
            if self.active_players[self.current_player_idx]:
                self.current_step = 0
                self.state = "PLAYER_TURN"
                print(f"\nEste rândul Jucătorului {self.current_player_idx + 1}. Secvența are {len(self.sequence)} tile-uri.")
                return

    def eliminate_current_player(self):
        print(f"\n❌ Jucătorul {self.current_player_idx + 1} a fost eliminat!")
        self.active_players[self.current_player_idx] = False

        remaining = self.active_players.count(True)
        if remaining == 1:
            winner_idx = self.active_players.index(True)
            self.round_winner = winner_idx + 1
            self.scores[winner_idx] += 1
            winner_num = self.round_winner

            if self.scores[winner_idx] >= 3:
                print(f"\n🎉 JUCĂTORUL {winner_num} A AJUNS LA 3 PUNCTE ȘI A CÂȘTIGAT JOCUL SUPREM! 🎉")
                self.is_final_win = True
                self.play_sound("game_win.wav")
            else:
                print(f"\n🏆 Jucătorul {winner_num} a câștigat runda! (Scor curent: {self.scores[winner_idx]}/3) 🏆")
                self.is_final_win = False
                self.play_sound("round_win.wav")

            self.state = "SHOW_WIN"
            self.state_time = time.time()
        else:
            print("Secvența se păstrează! Următorul jucător o continuă.")
            self.advance_to_next_player()

    def tick(self):
        just_pressed = []
        for i in range(512):
            if self.button_states[i] and not self.prev_button_states[i]:
                just_pressed.append(i)
            self.prev_button_states[i] = self.button_states[i]

        now = time.time()
        elapsed = now - self.state_time

        if self.state == "COUNTDOWN":
            if elapsed >= 6.0:
                self.state = "PLAYER_TURN"
                print(f"Start! Este rândul Jucătorului {self.current_player_idx + 1}.")

        elif self.state == "RESTARTING":
            if elapsed >= 3.0:
                self.start_game(self.num_players, reset_scores=False)

        elif self.state == "SHOW_WIN":
            if elapsed >= 5.0:
                if self.is_final_win:
                    print("Jocul s-a încheiat complet. Așteptare comenzi...")
                    self.state = "WAITING_FOR_START"
                else:
                    self.restart_game()

        elif self.state == "PLAYER_TURN":
            for flat_idx in just_pressed:
                x, y = get_xy_from_flat(flat_idx)

                if not is_playable(x, y):
                    continue

                if self.current_step < len(self.sequence):
                    expected_tile = self.sequence[self.current_step]
                    if (x, y) == expected_tile:
                        # Redă sunetul din secvența existentă
                        self.play_sound(f"note_{self.current_step}.wav")
                        self.current_step += 1
                    elif (x, y) in self.sequence:
                        pass
                    else:
                        self.state = "TURN_FAIL"
                        self.state_time = now
                        self.wrong_tile = (x, y)
                        print(f"Greșeală! S-a apăsat {(x, y)} în loc de {expected_tile}.")
                        self.play_sound("fail.wav")
                        break
                else:
                    if (x, y) in self.sequence:
                        pass
                    else:
                        # S-a adăugat un tile nou la secvență. Va reda DOAR nota din gamă.
                        self.sequence.append((x, y))
                        self.play_sound(f"note_{self.current_step}.wav")
                        self.current_step += 1
                        self.state = "TURN_SUCCESS"
                        self.state_time = now
                        print(f"Secvență extinsă! Lungime curentă: {len(self.sequence)}.")
                        break

        elif self.state == "TURN_SUCCESS":
            if elapsed > 3.0:
                self.advance_to_next_player()

        elif self.state == "TURN_FAIL":
            if elapsed > 3.0:
                self.eliminate_current_player()

    def render(self):
        buffer = bytearray(FRAME_DATA_LENGTH)

        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if not is_playable(x, y):
                    set_pixel(buffer, x, y, *GREEN)

        if self.state == "COUNTDOWN":
            elapsed = time.time() - self.state_time
            if elapsed < 2.0:
                draw_symbol(buffer, 3, 4, 10, WHITE)
            elif elapsed < 4.0:
                draw_symbol(buffer, 2, 4, 10, WHITE)
            elif elapsed < 6.0:
                draw_symbol(buffer, 1, 4, 10, WHITE)

        elif self.state == "SHOW_WIN":
            elapsed_ms = int((time.time() - self.state_time) * 10)

            if self.is_final_win:
                anim_color = MAGENTA if elapsed_ms % 2 == 0 else WHITE

                draw_symbol(buffer, 'W', 1, 8, anim_color)
                draw_symbol(buffer, 'I', 7, 8, anim_color)
                draw_symbol(buffer, 'N', 11, 8, anim_color)

                draw_symbol(buffer, 'P', 4, 18, anim_color)
                draw_symbol(buffer, str(self.round_winner), 9, 18, anim_color)
            else:
                anim_color = MAGENTA if elapsed_ms % 4 < 2 else WHITE

                draw_symbol(buffer, 'P', 4, 10, anim_color)
                draw_symbol(buffer, str(self.round_winner), 9, 10, anim_color)

                draw_symbol(buffer, '+', 4, 18, anim_color)
                draw_symbol(buffer, '1', 9, 18, anim_color)

        elif self.state == "RESTARTING":
            now = time.time()
            elapsed = now - self.state_time
            progress = min(1.0, elapsed / 3.0)
            tiles_to_draw = int(progress * len(SPIRAL_PATH))

            for i in range(tiles_to_draw):
                px, py = SPIRAL_PATH[i]
                wave = (math.sin(now * 5.0 - i * 0.15) + 1.0) / 2.0
                r = int(255 * wave)
                b = int(255 * wave)
                set_pixel(buffer, px, py, r, 0, b)

        elif self.state == "PLAYER_TURN":
            for i in range(self.current_step):
                px, py = self.sequence[i]
                set_pixel(buffer, px, py, *MAGENTA)

        elif self.state == "TURN_SUCCESS":
            for px, py in self.sequence:
                set_pixel(buffer, px, py, *MAGENTA)

        elif self.state == "TURN_FAIL":
            for i in range(self.current_step):
                px, py = self.sequence[i]
                set_pixel(buffer, px, py, *MAGENTA)
            if self.wrong_tile:
                set_pixel(buffer, self.wrong_tile[0], self.wrong_tile[1], *RED)

        return buffer

# --- Networking Matrice ---
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
            self.sock_recv.bind(("0.0.0.0", UDP_LISTEN_PORT))
        except Exception as e:
            print(f"Eroare la binding pentru portul {UDP_LISTEN_PORT}: {e}")
            self.running = False

    def build_and_send(self, packet_bytes):
        chk = calculate_checksum(packet_bytes)
        packet_bytes.append(chk)
        packet_bytes.append(0x00)
        self.sock_send.sendto(packet_bytes, (UDP_SEND_IP, UDP_SEND_PORT))

    def send_loop(self):
        while self.running and self.game.running:
            frame = self.game.render()
            self.send_frame(frame)
            time.sleep(0.05)

    def send_frame(self, frame_data):
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        if self.sequence_number == 0: self.sequence_number = 1

        start_pkt = bytearray([
            0x75, random.randint(0,127), random.randint(0,127), 0x00, 0x08,
            0x02, 0x00, 0x00, 0x33, 0x44,
            (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF,
            0x00, 0x00, 0x00
        ])
        self.build_and_send(start_pkt)

        fff0_payload = bytearray()
        for _ in range(NUM_CHANNELS):
            fff0_payload += bytes([(LEDS_PER_CHANNEL >> 8) & 0xFF, LEDS_PER_CHANNEL & 0xFF])

        fff0_internal = bytearray([
            0x02, 0x00, 0x00, 0x88, 0x77, 0xFF, 0xF0,
            (len(fff0_payload) >> 8) & 0xFF, (len(fff0_payload) & 0xFF)
        ]) + fff0_payload

        fff0_len = len(fff0_internal) - 1
        fff0_pkt = bytearray([0x75, random.randint(0,127), random.randint(0,127), (fff0_len >> 8) & 0xFF, (fff0_len & 0xFF)]) + fff0_internal
        self.build_and_send(fff0_pkt)

        chunk_size = 984
        data_idx = 1
        for i in range(0, len(frame_data), chunk_size):
            chunk = frame_data[i:i+chunk_size]
            internal_data = bytearray([
                0x02, 0x00, 0x00, 0x88, 0x77,
                (data_idx >> 8) & 0xFF, (data_idx & 0xFF),
                (len(chunk) >> 8) & 0xFF, (len(chunk) & 0xFF)
            ]) + chunk

            p_len = len(internal_data) - 1
            pkt = bytearray([0x75, random.randint(0,127), random.randint(0,127), (p_len >> 8) & 0xFF, (p_len & 0xFF)]) + internal_data
            self.build_and_send(pkt)
            data_idx += 1
            time.sleep(0.002)

        end_pkt = bytearray([
            0x75, random.randint(0,127), random.randint(0,127), 0x00, 0x08,
            0x02, 0x00, 0x00, 0x55, 0x66,
            (self.sequence_number >> 8) & 0xFF, self.sequence_number & 0xFF,
            0x00, 0x00, 0x00
        ])
        self.build_and_send(end_pkt)

    def recv_loop(self):
        while self.running and self.game.running:
            try:
                data, _ = self.sock_recv.recvfrom(2048)
                if len(data) >= 1373 and data[0] == 0x88:
                    for ch in range(8):
                        offset = 3 + (ch * 171)
                        for led_idx in range(64):
                            is_pressed = (data[offset + led_idx] == 0xCC)
                            flat_idx = ch * 64 + led_idx
                            self.game.button_states[flat_idx] = is_pressed
            except Exception:
                pass

    def start_bg(self):
        t1 = threading.Thread(target=self.send_loop, daemon=True)
        t2 = threading.Thread(target=self.recv_loop, daemon=True)
        t1.start()
        t2.start()

# --- Threads Interne Server ---
def game_logic_thread_func(game):
    while game.running:
        game.tick()
        time.sleep(0.01)

def gui_communication_thread(game):
    gui_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gui_sock.bind((LOCAL_IP, GUI_SEND_PORT))
    gui_sock.settimeout(0.1)

    while game.running:
        winner_idx = None
        if game.state == "SHOW_WIN" and game.active_players.count(True) > 0:
            winner_idx = game.active_players.index(True) + 1

        state_data = {
            "state": game.state,
            "turn": game.current_player_idx + 1 if game.state == "PLAYER_TURN" else None,
            "scores": game.scores,
            "winner": winner_idx,
            "num_players": game.num_players
        }

        try:
            gui_sock.sendto(json.dumps(state_data).encode(), (LOCAL_IP, GUI_LISTEN_PORT))
        except Exception:
            pass

        try:
            data, _ = gui_sock.recvfrom(1024)
            cmd_data = json.loads(data.decode())
            cmd = cmd_data.get("cmd")

            if cmd == "start":
                players = cmd_data.get("players", 2)
                print(f"Comanda GUI: Start cu {players} jucatori.")
                game.start_game(players)
            elif cmd == "restart":
                print("Comanda GUI: Restart joc.")
                game.restart_game()
            elif cmd == "quit":
                print("Comanda GUI: Iesire.")
                game.running = False
        except socket.timeout:
            pass
        except Exception as e:
            pass

        time.sleep(0.1)

# --- GUI / Display ---
class GameDisplays:
    def __init__(self, root):
        self.root = root
        self.root.title("Control Panel (Touch)")
        self.root.geometry("400x450")
        self.root.configure(bg="#2c3e50")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LOCAL_IP, GUI_LISTEN_PORT))
        self.sock.settimeout(0.1)

        self.msg_queue = queue.Queue()
        self.running = True

        self.setup_control_panel()
        self.setup_scoreboard()

        self.listener_thread = threading.Thread(target=self.listen_to_game, daemon=True)
        self.listener_thread.start()

        self.process_queue()

    def setup_control_panel(self):
        title = tk.Label(self.root, text="🎮 Panou Control", font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=20)

        frame_players = tk.Frame(self.root, bg="#2c3e50")
        frame_players.pack(pady=10)
        tk.Label(frame_players, text="Selectează numărul de jucători:", font=("Arial", 14), bg="#2c3e50", fg="white").pack(pady=10)

        self.players_var = tk.IntVar(value=2)
        self.player_buttons = []

        btn_frame = tk.Frame(frame_players, bg="#2c3e50")
        btn_frame.pack()

        for i in range(2, 9):
            btn = tk.Button(btn_frame, text=str(i), font=("Arial", 16, "bold"), width=2, height=1,
                            bg="#3498db" if i == 2 else "#95a5a6", fg="white",
                            command=lambda num=i: self.select_players(num))
            btn.pack(side=tk.LEFT, padx=4)
            self.player_buttons.append(btn)

        btn_start = tk.Button(self.root, text="▶ START JOC", font=("Arial", 16, "bold"), bg="#27ae60", fg="white", command=self.send_start)
        btn_start.pack(fill=tk.X, padx=50, pady=20)

        btn_restart = tk.Button(self.root, text="🔄 RESTART", font=("Arial", 16, "bold"), bg="#f39c12", fg="white", command=self.send_restart)
        btn_restart.pack(fill=tk.X, padx=50, pady=10)

        btn_quit = tk.Button(self.root, text="❌ QUIT", font=("Arial", 16, "bold"), bg="#c0392b", fg="white", command=self.send_quit)
        btn_quit.pack(fill=tk.X, padx=50, pady=10)

    def select_players(self, num):
        self.players_var.set(num)
        for i, btn in enumerate(self.player_buttons):
            if i + 2 == num:
                btn.config(bg="#3498db")
            else:
                btn.config(bg="#95a5a6")

    def setup_scoreboard(self):
        self.score_window = tk.Toplevel(self.root)
        self.score_window.title("Scoreboard (Non-Touch)")
        self.score_window.geometry("500x500")
        self.score_window.configure(bg="#000000")

        self.lbl_state = tk.Label(self.score_window, text="Așteptare Start...", font=("Arial", 24, "bold"), bg="black", fg="#f1c40f")
        self.lbl_state.pack(pady=20)

        self.lbl_turn = tk.Label(self.score_window, text="-", font=("Arial", 30, "bold"), bg="black", fg="#3498db")
        self.lbl_turn.pack(pady=10)

        self.lbl_scores = tk.Label(self.score_window, text="Scoruri:\n-", font=("Arial", 18), bg="black", fg="white", justify=tk.LEFT)
        self.lbl_scores.pack(pady=20)

        self.lbl_winner = tk.Label(self.score_window, text="", font=("Arial", 28, "bold"), bg="black", fg="#2ecc71")
        self.lbl_winner.pack(pady=20)

    def send_command(self, cmd_dict):
        try:
            self.sock.sendto(json.dumps(cmd_dict).encode(), (LOCAL_IP, GUI_SEND_PORT))
        except Exception as e:
            print(f"Eroare trimitere comandă: {e}")

    def send_start(self):
        self.send_command({"cmd": "start", "players": self.players_var.get()})

    def send_restart(self):
        self.send_command({"cmd": "restart"})

    def send_quit(self):
        self.send_command({"cmd": "quit"})
        self.running = False
        self.root.destroy()

    def listen_to_game(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                state = json.loads(data.decode())
                self.msg_queue.put(state)
            except socket.timeout:
                continue
            except Exception:
                pass

    def process_queue(self):
        try:
            while not self.msg_queue.empty():
                state = self.msg_queue.get_nowait()
                self.update_scoreboard(state)
        except queue.Empty:
            pass
        if self.running:
            self.root.after(100, self.process_queue)

    def update_scoreboard(self, state):
        game_state = state.get("state", "")
        self.lbl_state.config(text=f"Stare: {game_state}")

        turn = state.get("turn")
        if turn:
            self.lbl_turn.config(text=f"👉 Este rândul Jucătorului {turn} 👈")
        else:
            self.lbl_turn.config(text="")

        scores = state.get("scores", [])
        if scores:
            score_text = "🏆 Scoruri 🏆\n" + "\n".join([f"Jucător {i+1}: {score} pct" for i, score in enumerate(scores)])
            self.lbl_scores.config(text=score_text)
        else:
            self.lbl_scores.config(text="Scoruri:\n-")

        winner = state.get("winner")
        if game_state == "SHOW_WIN" and winner:
            self.lbl_winner.config(text=f"🎉 JUCĂTORUL {winner} A CÂȘTIGAT! 🎉")
        else:
            self.lbl_winner.config(text="")


# --- Main Execuție Combinație ---
if __name__ == "__main__":
    game = SequenceGame()
    net = NetworkManager(game)
    net.start_bg()

    gt = threading.Thread(target=game_logic_thread_func, args=(game,), daemon=True)
    gt.start()

    gui_thread = threading.Thread(target=gui_communication_thread, args=(game,), daemon=True)
    gui_thread.start()

    print("=== Joc & Panou de Control Activat ===")

    root = tk.Tk()
    app = GameDisplays(root)

    def on_closing():
        print("Se închide jocul...")
        app.send_quit()
        game.running = False
        net.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()