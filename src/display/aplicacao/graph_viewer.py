# display/aplicacao/graph_viewer.py
import tkinter as tk
import networkx as nx
import matplotlib
# ensure TkAgg backend (important when starting in threads on some platforms)
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle
from datetime import datetime

from display.aplicacao.layout_utils import compute_layout
from display.aplicacao.desenhar import draw_graph, update_graph_drawing
from display.aplicacao.interacoes import register_interactions
from display.aplicacao.queue_handler import process_queue


class AnimatedGraphApp:
    """
    Tkinter + Matplotlib viewer. Designed to be run in a background thread
    *only if* your platform permits it and you run Textual in the main thread.
    """

    def __init__(self, grafo, ambiente, command_queue):
        print("[GraphViewer] Initializing...")
        
        # NOTE: if this raises "Starting a Matplotlib GUI outside the main thread"
        # your platform/OS/Python configuration prevents background GUIs.
        # In that case you must run this in the main thread.
        self.root = tk.Tk()
        self.root.title("Simulação - Visualizador de Grafo")

        self.grafo = grafo
        self.ambiente = ambiente
        self.command_queue = command_queue

        # --- Matplotlib setup ---
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Build NetworkX graph from grafo
        self.G = nx.Graph()
        for node in grafo.getNodes():
            self.G.add_node(node.getName(), __node_obj=node)
        for origem, arestas in grafo.m_graph.items():
            for destino, aresta in arestas:
                self.G.add_edge(origem, destino, aresta=aresta)

        print(f"[GraphViewer] Graph has {len(self.G.nodes())} nodes and {len(self.G.edges())} edges")

        # compute layout (returns data coords in a reasonable span)
        self.pos = compute_layout(self.G, scale=1.0, k_factor=8.0)

        # Initialize car info (legacy compatibility)
        start_node = list(self.G.nodes())[0]
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

        # Initialize drawing structures
        self.edge_lines = {}
        self.node_patches = {}
        self.node_texts = {}
        self.vehicle_markers = {}
        self.car_point = None

        # Debug: check initial vehicles
        if self.ambiente is not None:
            veiculos = self.ambiente.listar_veiculos()
            print(f"[GraphViewer] Initial vehicles count: {len(veiculos)}")
            for v in veiculos:
                print(f"  - Vehicle {v.id_veiculo} at {v.localizacao_atual}")

        # Draw initial graph state
        print("[GraphViewer] Drawing initial graph...")
        draw_graph(self)
        
        # Register mouse/keyboard interactions
        register_interactions(self)

        # Start processing command queue
        self.root.after(100, lambda: process_queue(self))

        # Start animation loop (for smooth car movement if needed)
        self.animation = FuncAnimation(self.fig, self._animation_step, interval=50, blit=False)
        
        print("[GraphViewer] Initialization complete")

    def _animation_step(self, _):
        """Animation callback - updates visual elements if car is moving."""
        if self.car_info.get("is_moving"):
            update_graph_drawing(self)

    # --------------------------------------------------------
    # External API called by simulator via queue
    # --------------------------------------------------------
    
    def update_time(self, tempo_simulacao, viagens_ativas):
        """Called via queue -> 'update_time' messages."""
        # Format and display time in title
        if isinstance(tempo_simulacao, datetime):
            tstr = tempo_simulacao.strftime("%H:%M:%S")
        else:
            tstr = str(tempo_simulacao)
        
        self.ax.set_title(f"Simulação — Tempo {tstr} | Viagens ativas: {len(viagens_ativas)}")
        
        # Redraw to show updated vehicle positions
        update_graph_drawing(self)

    def highlight_route(self, rota):
        """Optional: draw a highlighted route (one-off)."""
        if not rota or len(rota) < 2:
            return
            
        for i in range(len(rota) - 1):
            u, v = rota[i], rota[i + 1]
            if u in self.pos and v in self.pos:
                x1, y1 = self.pos[u]
                x2, y2 = self.pos[v]
                self.ax.plot([x1, x2], [y1, y2], color="green", linewidth=3, alpha=0.6, zorder=1.5)
        
        self.canvas.draw_idle()

    def run(self):
        """Start Tk mainloop (blocks this thread)."""
        print("[GraphViewer] Starting mainloop...")
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"[GraphViewer] mainloop exited with error: {e}")
            import traceback
            traceback.print_exc()