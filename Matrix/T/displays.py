import json
import socket
import threading
import tkinter as tk
import queue

# --- Setari Retea GUI ---
GUI_SEND_PORT = 1071
GUI_LISTEN_PORT = 1072
LOCAL_IP = "127.0.0.1"

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

if __name__ == "__main__":
    root = tk.Tk()
    app = GameDisplays(root)
    root.protocol("WM_DELETE_WINDOW", app.send_quit)
    root.mainloop()