from matplotlib.patches import Circle
import math


class GraphDrawer:
    """Responsável por desenhar elementos do grafo."""

    def __init__(self):
        self.edge_lines = {}
        self.node_patches = {}
        self.node_texts = {}
        self.vehicle_markers = {}

    def compute_node_radius(self, pos, relative_factor=0.03, min_radius=0.01, max_radius=0.18):
        """Calcula raio apropriado para nós."""
        xs = [p[0] for p in pos.values()] if pos else [0.0]
        ys = [p[1] for p in pos.values()] if pos else [0.0]
        xrange = (max(xs) - min(xs)) if xs else 1.0
        yrange = (max(ys) - min(ys)) if ys else 1.0
        span = max(xrange, yrange, 1e-6)
        r = span * relative_factor
        return max(min_radius, min(max_radius, r))

    def draw_edges(self, ax, G, pos):
        """Desenha arestas."""
        self.edge_lines = {}
        for u, v in G.edges():
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            line = ax.plot([x1, x2], [y1, y2], color="gray", linewidth=1.2, zorder=1)[0]
            self.edge_lines[(u, v)] = line

    def draw_nodes(self, ax, G, pos):
        """Desenha nós com labels."""
        self.node_patches = {}
        self.node_texts = {}
        node_radius = self.compute_node_radius(pos)

        for n, (x, y) in pos.items():
            # Círculo do nó
            circ = Circle((x, y), node_radius, zorder=2, ec="black", lw=0.8, facecolor="lightblue")
            ax.add_patch(circ)
            self.node_patches[n] = circ

            # Tamanho de fonte adaptativo
            try:
                trans = ax.transData.transform
                px_center = trans((x, y))
                px_edge = trans((x + node_radius, y))
                pixel_radius = abs(px_edge[0] - px_center[0])
                fontsize = max(6, min(12, int(pixel_radius * 0.5)))
            except Exception:
                fontsize = 8

            # Texto
            txt = ax.text(
                x, y, str(n),
                ha="center", va="center", zorder=3,
                fontsize=fontsize, color="black", weight="bold"
            )
            self.node_texts[n] = txt

    def draw_vehicles(self, ax, pos, ambiente, node_radius):
        """Desenha veículos nos nós."""
        self.vehicle_markers = {}

        if not ambiente:
            return

        veiculos = ambiente.listar_veiculos()

        for v in veiculos:
            vid = v.id_veiculo
            node_name = v.localizacao_atual

            if node_name not in pos:
                continue

            x, y = pos[node_name]

            # Cor baseada no tipo
            try:
                clsname = v.__class__.__name__.lower()
                color = "red" if ("eletric" in clsname or "eletrico" in clsname) else "orange"
            except Exception:
                color = "orange"

            # Criar ou atualizar marcador
            if vid not in self.vehicle_markers:
                marker, = ax.plot(
                    [x], [y], marker="D", color=color, markersize=max(8, int(node_radius * 50)),
                    markeredgecolor="black", markeredgewidth=1.5, zorder=5
                )
                self.vehicle_markers[vid] = marker
            else:
                self.vehicle_markers[vid].set_data([x], [y])

    def update_positions(self, pos):
        """Atualiza posições de todos os elementos."""
        # Arestas
        for (u, v), line in self.edge_lines.items():
            if u in pos and v in pos:
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                line.set_data([x1, x2], [y1, y2])

        # Nós
        for n, circ in self.node_patches.items():
            if n in pos:
                x, y = pos[n]
                circ.center = (x, y)
                if n in self.node_texts:
                    self.node_texts[n].set_position((x, y))

        # Veículos
        for vid, marker in self.vehicle_markers.items():
            # A posição será atualizada por outro módulo se em movimento
            pass
