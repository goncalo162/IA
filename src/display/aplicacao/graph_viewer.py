import tkinter as tk
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation

from .layout_utils import compute_layout
from .desenhar import draw_graph, update_graph_drawing
from .interacoes import register_interactions
from .queue_handler import process_queue


class AnimatedGraphApp:
    """Main Tkinter + Matplotlib animated graph viewer."""

    def __init__(self, grafo, search_algorithm, command_queue):
        self.root = tk.Tk()
        self.root.title(f"Graph Animation ({search_algorithm.upper()})")

        self.grafo = grafo
        self.search_algorithm = search_algorithm
        self.command_queue = command_queue

        # --- Matplotlib setup ---
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Disable grid
        self.ax.grid(False)
        self.ax.set_axis_on()

        # --- Build NetworkX graph ---
        self.G = nx.Graph()
        for node in grafo.getNodes():
            self.G.add_node(node.getName(), __node_obj=node)
        for origem, arestas in grafo.m_graph.items():
            for destino, aresta in arestas:
                self.G.add_edge(origem, destino, aresta=aresta)

        # --- Compute layout ---
        self.pos = compute_layout(self.G)

        # --- Initialize car ---
        start_node = list(self.G.nodes())[0]
        sx, sy = self.pos[start_node]
        self.car_info = dict(
            position=start_node, visual_x=sx, visual_y=sy,
            path=[], path_index=0, progress=0.0,
            is_moving=False, speed=0.03, use_visual_start=False
        )

        # --- Draw ---
        draw_graph(self)

        # --- Animation ---
        self.animation = FuncAnimation(self.fig, self.update_animation, interval=50, blit=False)

        # --- Interaction ---
        register_interactions(self)

        # --- Queue ---
        self.root.after(50, lambda: process_queue(self))

    def update_animation(self, _):
        """Move the 'car' dot smoothly along a path."""
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
            x1, y1 = self.pos[path[idx]]
        x2, y2 = self.pos[path[idx + 1]]

        car["progress"] += car["speed"]
        if car["progress"] >= 1.0:
            car["path_index"] += 1
            car["progress"] = 0.0
            car["position"] = path[idx + 1]
            car["visual_x"], car["visual_y"] = x2, y2
            update_graph_drawing(self)
            return

        t = car["progress"]
        vx = x1 + (x2 - x1) * t
        vy = y1 + (y2 - y1) * t
        car["visual_x"], car["visual_y"] = vx, vy
        self.car_point.set_data([vx], [vy])
        self.ax.set_title(f"Car at {car['position']}")
        self.canvas.draw_idle()

    def run(self):
        self.root.mainloop()