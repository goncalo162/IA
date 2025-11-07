import sys
import os

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import queue
import math
import tkinter as tk
import sys
import os
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Static

# --- Import your project modules ---
from infra.grafo import Grafo
from algoritmos.algoritmos_procura import bfs, dfs

# --- Shared command queue for communication between Textual and Tkinter ---
command_queue = queue.Queue()


def nearest_node_to_point(pos, x, y):
    """Find the nearest graph node (by coordinates) to a given point."""
    best, best_d = None, float("inf")
    for n, (nx_, ny_) in pos.items():
        d = (nx_ - x) ** 2 + (ny_ - y) ** 2
        if d < best_d:
            best, best_d = n, d
    return best


class AnimatedGraphApp:
    def __init__(self, grafo, search_algorithm="bfs"):
        self.root = tk.Tk()
        self.root.title(f"Graph Animation ({search_algorithm.upper()})")

        self.grafo = grafo
        self.search_algorithm = search_algorithm.lower()

        # --- Matplotlib setup ---
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Build NetworkX graph ---
        self.G = nx.Graph()
        for node in grafo.getNodes():
            self.G.add_node(node.getName())
        for origem, arestas in grafo.m_graph.items():
            for destino, aresta in arestas:
                self.G.add_edge(origem, destino, aresta=aresta)
        self.pos = nx.spring_layout(self.G, seed=42)

        # --- Initialize car info ---
        start_node = grafo.getNodes()[0].getName()
        sx, sy = self.pos[start_node]
        self.car_info = {
            "position": start_node,
            "path": [],
            "path_index": 0,
            "progress": 0.0,
            "is_moving": False,
            "speed": 0.03,
            "visual_x": sx,
            "visual_y": sy,
            "use_visual_start": False,
        }

        # --- Draw and animate ---
        self.draw_graph()
        self.animation = FuncAnimation(self.fig, self.update_animation, interval=50, blit=False)

        # --- Poll the shared queue for commands ---
        self.root.after(50, self.process_queue)

    # ---------------- GRAPH RENDERING ---------------- #
    def draw_graph(self):
        self.ax.clear()
        nx.draw(self.G, self.pos, with_labels=True, node_color="lightblue", ax=self.ax)
        vx, vy = self.car_info["visual_x"], self.car_info["visual_y"]
        self.car, = self.ax.plot(vx, vy, "ro", markersize=14)
        self.ax.set_title(f"Car at {self.car_info['position']}")
        self.canvas.draw()

    def update_animation(self, _):
        car = self.car_info
        if not car["is_moving"]:
            return

        path = car["path"]
        idx = car["path_index"]

        if idx >= len(path) - 1:
            car["is_moving"] = False
            fx, fy = self.pos[path[-1]]
            car["visual_x"], car["visual_y"] = fx, fy
            car["position"] = path[-1]
            return

        if idx == 0 and car.get("use_visual_start", False):
            x1, y1 = car["visual_x"], car["visual_y"]
        else:
            start_node = path[idx]
            x1, y1 = self.pos[start_node]

        end_node = path[idx + 1]
        x2, y2 = self.pos[end_node]

        car["progress"] += car["speed"]
        if car["progress"] >= 1.0:
            car["path_index"] += 1
            car["progress"] = 0.0
            car["position"] = end_node
            car["visual_x"], car["visual_y"] = x2, y2
            car["use_visual_start"] = False
            if car["path_index"] >= len(path) - 1:
                car["is_moving"] = False
            return

        t = car["progress"]
        vx = x1 + (x2 - x1) * t
        vy = y1 + (y2 - y1) * t
        car["visual_x"], car["visual_y"] = vx, vy

        self.car.set_data([vx], [vy])
        self.ax.set_title(f"Car at {car['position']}")
        self.canvas.draw_idle()

    # ---------------- COMMAND HANDLING ---------------- #
    def process_queue(self):
        try:
            while True:
                cmd, value = command_queue.get_nowait()
                if cmd == "move":
                    self._handle_move(value)
                elif cmd == "quit":
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(50, self.process_queue)

    def _handle_move(self, destino):
        car = self.car_info
        origin = nearest_node_to_point(self.pos, car["visual_x"], car["visual_y"])

        if car["is_moving"]:
            print("Already moving — ignoring new command.")
            return

        # Select algorithm
        if self.search_algorithm == "dfs":
            path = dfs(self.grafo, origin, destino)
        else:
            path = bfs(self.grafo, origin, destino)

        if not path:
            print(f"No path to {destino} from {origin}")
            return

        ox, oy = self.pos[origin]
        visual_at_origin = math.isclose(ox, car["visual_x"], rel_tol=1e-6, abs_tol=1e-6) and \
                           math.isclose(oy, car["visual_y"], rel_tol=1e-6, abs_tol=1e-6)

        car.update({
            "position": origin,
            "path": path,
            "path_index": 0,
            "progress": 0.0,
            "is_moving": True,
            "use_visual_start": not visual_at_origin,
        })

        print(f"🚗 Moving to {destino} via {'→'.join(path)} using {self.search_algorithm.upper()}")

    def run(self):
        self.root.mainloop()


class GraphCarController(App):
    """Textual TUI"""
    def __init__(self):
        super().__init__()
        self.status_widget = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Enter destination node", id="target")
        yield Button("Move", id="move_btn")
        yield Button("Quit", id="quit_btn")
        yield Static("", id="status")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        target_input = self.query_one("#target", Input)
        self.status_widget = self.query_one("#status", Static)
        if event.button.id == "move_btn":
            destino = target_input.value.strip()
            if destino:
                command_queue.put(("move", destino))
                self.status_widget.update(f"Sent move command to {destino}")
            else:
                self.status_widget.update("Please enter a node.")
        elif event.button.id == "quit_btn":
            command_queue.put(("quit", None))
            self.exit()


def run_combined(grafo, algorithm):
    tk_thread = threading.Thread(target=lambda: AnimatedGraphApp(grafo, algorithm).run(), daemon=True)
    tk_thread.start()
    GraphCarController().run()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <graph.json> <algorithm: bfs|dfs>")
        sys.exit(1)

    graph_path = sys.argv[1]
    algorithm = sys.argv[2].lower()

    if not os.path.exists(graph_path):
        print(f"⚠️ Graph file '{graph_path}' not found.")
        sys.exit(1)

    if algorithm not in ["bfs", "dfs"]:
        print("⚠️ Algorithm must be 'bfs' or 'dfs'.")
        sys.exit(1)

    try:
        grafo = Grafo.from_json_file(graph_path)
        print(f"✅ Loaded graph from {graph_path}")
    except Exception as e:
        print(f"⚠️ Failed to load graph: {e}")
        sys.exit(1)

    run_combined(grafo, algorithm)