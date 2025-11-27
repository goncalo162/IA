"""Viewer principal - integra os módulos."""

import tkinter as tk
import networkx as nx
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from datetime import datetime
import traceback

from display.aplicacao.viewport import Viewport
from display.aplicacao.desenhar import GraphDrawer
from display.aplicacao.interacoes import register_interactions
from display.aplicacao.layout_utils import compute_layout_best
from display.aplicacao.queue_handler import process_queue


class AnimatedGraphApp:
    """Viewer principal com modularização."""

    def __init__(self, grafo, ambiente, command_queue):
        print("[GraphViewer] Inicializando...")
        
        self.root = tk.Tk()
        self.root.title("Simulação - Visualizador de Grafo")

        self.grafo = grafo
        self.ambiente = ambiente
        self.command_queue = command_queue

        # ========== MÓDULOS ==========
        self.viewport = Viewport()
        self.drawer = GraphDrawer()
        self.interaction_handler = None

        # ========== MATPLOTLIB SETUP ==========
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # ========== NETWORKX GRAPH ==========
        self.G = nx.Graph()
        for node in grafo.getNodes():
            self.G.add_node(node.getName(), __node_obj=node)
        for origem, arestas in grafo.m_graph.items():
            for destino, aresta in arestas:
                self.G.add_edge(origem, destino, aresta=aresta)

        print(f"[GraphViewer] Grafo: {len(self.G.nodes())} nós, {len(self.G.edges())} arestas")

        # ========== LAYOUT ==========
        # Aumentar espaçamento: aumenta k_factor de 6 para 12, e scale de 10 para 20
        self.pos = compute_layout_best(self.G, scale=2.0)
        
        # ========== INFORMAÇÕES DO CARRO ==========
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
        self.car_point = None

        # ========== DEBUG VEÍCULOS ==========
        if self.ambiente is not None:
            veiculos = self.ambiente.listar_veiculos()
            print(f"[GraphViewer] {len(veiculos)} veículos iniciais")

        # ========== DESENHAR E CONFIGURAR ==========
        print("[GraphViewer] Desenhando grafo inicial...")
        self._draw_complete_graph()
        
        # Registar interações (ANTES de aplicar auto-scale)
        self.interaction_handler = InteractionHandler(self)
        self.interaction_handler.register(self.canvas, self.ax)

        # Aplicar auto-scale inicial
        self.viewport.apply_auto_scale(self.ax, self.pos, margin=0.15)

        # ========== LOOPS ==========
        self.root.after(100, lambda: process_queue(self))
        self.animation = FuncAnimation(self.fig, self._animation_step, interval=50, blit=False)
        
        print("[GraphViewer] Inicialização completa")

    def _draw_complete_graph(self):
        """Desenha o grafo completo (primeira vez)."""
        self.ax.cla()
        self.ax.grid(False)
        self.ax.set_aspect("equal", adjustable="datalim")

        node_radius = self.drawer.compute_node_radius(self.pos)

        # Desenhar arestas, nós e veículos
        self.drawer.draw_edges(self.ax, self.G, self.pos)
        self.drawer.draw_nodes(self.ax, self.G, self.pos)
        self.drawer.draw_vehicles(self.ax, self.pos, self.ambiente, node_radius)

        # Handle legacy car_point
        if self.car_point is None:
            vx = self.car_info.get("visual_x", 0.0)
            vy = self.car_info.get("visual_y", 0.0)
            self.car_point, = self.ax.plot(
                [vx], [vy], "ro", markersize=max(6, int(node_radius * 40)), zorder=5
            )

        self.canvas.draw_idle()

    def _animation_step(self, _):
        """Passo de animação - atualizar se há movimento."""
        if self.car_info.get("is_moving"):
            self._update_drawing()

    def _update_drawing(self):
        """Atualiza posições mantendo viewport."""
        # Guardar viewport antes de atualizar
        self.viewport.save_state(self.ax)

        # Atualizar posições
        self.drawer.update_positions(self.pos)

        # Atualizar veículos (se em movimento)
        node_radius = self.drawer.compute_node_radius(self.pos)
        self.drawer.draw_vehicles(self.ax, self.pos, self.ambiente, node_radius)

        # Atualizar título com tempo e viagens
        tempo_str = self.car_info.get("tempo", "--:--:--")
        viagens_ativas = len(self.car_info.get("viagens", []))
        self.ax.set_title(f"Simulação — Tempo {tempo_str} | Viagens ativas: {viagens_ativas}")

        # Update car_point if needed
        if self.car_point is not None:
            vx = self.car_info.get("visual_x", 0.0)
            vy = self.car_info.get("visual_y", 0.0)
            self.car_point.set_data([vx], [vy])

        # Restaurar viewport
        self.viewport.restore_state(self.ax)
        self.canvas.draw_idle()
        print("[GraphViewer] Atualização concluída.")

    # ========== API PÚBLICA (chamada via queue) ==========

    def update_time(self, tempo_simulacao, viagens_ativas):
        """Atualizar tempo e viagens."""
        if isinstance(tempo_simulacao, datetime):
            tstr = tempo_simulacao.strftime("%H:%M:%S")
        else:
            tstr = str(tempo_simulacao)
        
        self.ax.set_title(f"Simulação — Tempo {tstr} | Viagens ativas: {len(viagens_ativas)}")
        self._update_drawing()

    def highlight_route(self, rota):
        """Destaca uma rota."""
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
        """Inicia o mainloop."""
        print("[GraphViewer] Iniciando mainloop...")
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"[GraphViewer] Erro: {e}")
            traceback.print_exc()