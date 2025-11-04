# graph_display.py
import socket
import threading
import tkinter as tk
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import math
import sys

HOST = "127.0.0.1"
PORT = 6000


class AnimatedGraphApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Graph Animation - Remote Controlled")

        # --- Tkinter setup ---
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Graph setup ---
        self.G = nx.Graph()
        self.G.add_edges_from([("A", "B"), ("B", "C"), ("C", "D"), ("A", "D")])
        self.pos = nx.spring_layout(self.G, seed=42)

        # --- Car info ---
        self.car_info = {
            "position": "A",
            "target": None,
            "path": [],
            "path_index": 0,
            "progress": 0.0,
            "is_moving": False,
            "speed": 0.02,  # interpolation step
        }

        # --- Draw ---
        self.draw_graph()
        self.animation = FuncAnimation(self.fig, self.update_animation, interval=50, blit=False)

        # --- Start server thread ---
        self.stop_flag = threading.Event()
        threading.Thread(target=self.server_loop, daemon=True).start()

    # --- Socket Server ---
    def server_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen(1)
            print(f"🔌 Listening for TUI commands on {HOST}:{PORT}")
            conn, _ = s.accept()
            with conn:
                print("✅ TUI connected.")
                self.conn = conn
                while not self.stop_flag.is_set():
                    data = conn.recv(1024)
                    if not data:
                        break
                    message = data.decode().strip()
                    self.handle_command(message)

    def handle_command(self, message):
        print("📥 Received:", message)
        if message.startswith("move_to"):
            target = message.split()[1]
            self.start_movement(target)
        elif message == "stop":
            print("🛑 Stop received, closing...")
            self.stop_flag.set()
            self.master.quit()
            sys.exit(0)

    def send_update(self, msg):
        if hasattr(self, "conn"):
            try:
                self.conn.sendall(f"{msg}\n".encode())
            except Exception:
                pass

    # --- Graph + Animation ---
    def draw_graph(self):
        self.ax.clear()
        nx.draw_networkx(self.G, self.pos, ax=self.ax, with_labels=True,
                         node_color="lightblue", node_size=800)
        x, y = self.pos[self.car_info["position"]]
        self.car, = self.ax.plot(x, y, "ro", markersize=20)
        self.ax.set_title(f"Carro em: {self.car_info['position']}")
        self.canvas.draw()

    def bfs(self, start, end):
        if start == end:
            return [start]
        visited = set()
        q = [[start]]
        while q:
            path = q.pop(0)
            node = path[-1]
            if node == end:
                return path
            if node not in visited:
                visited.add(node)
                for n in self.G.neighbors(node):
                    q.append(path + [n])
        return None

    def start_movement(self, target):
        if self.car_info["is_moving"]:
            self.send_update("status Already moving")
            return
        path = self.bfs(self.car_info["position"], target)
        if not path:
            self.send_update(f"status No path to {target}")
            return
        self.car_info.update({
            "target": target,
            "path": path,
            "path_index": 0,
            "progress": 0.0,
            "is_moving": True,
        })
        self.send_update(f"status Moving to {target} via {'→'.join(path)}")

    def update_animation(self, frame):
        car = self.car_info
        if not car["is_moving"]:
            return
        if car["path_index"] >= len(car["path"]) - 1:
            car["is_moving"] = False
            self.send_update(f"status Arrived at {car['position']}")
            return

        # Current and next node positions
        start_node = car["path"][car["path_index"]]
        end_node = car["path"][car["path_index"] + 1]
        x1, y1 = self.pos[start_node]
        x2, y2 = self.pos[end_node]

        # Linear interpolation
        car["progress"] += car["speed"]
        if car["progress"] >= 1.0:
            car["path_index"] += 1
            car["progress"] = 0.0
            car["position"] = end_node
            self.send_update(f"position {end_node}")
            if car["path_index"] >= len(car["path"]) - 1:
                car["is_moving"] = False
                self.send_update(f"status Arrived at {end_node}")
                return

        x = x1 + (x2 - x1) * car["progress"]
        y = y1 + (y2 - y1) * car["progress"]

        # Update car plot
        self.car.set_data([x], [y])
        self.canvas.draw_idle()


if __name__ == "__main__":
    root = tk.Tk()
    app = AnimatedGraphApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("🛑 Interrupted.")
        sys.exit(0)