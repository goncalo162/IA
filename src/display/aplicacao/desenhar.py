# filename: graph_viewer/drawing.py
import math
from matplotlib.patches import Circle

def draw_graph(app):
    """Draw all nodes and edges."""
    ax, pos, G = app.ax, app.pos, app.G
    ax.clear()
    ax.grid(False)
    ax.set_title(f"Car at {app.car_info['position']}")

    app.edge_lines = {}
    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        line = ax.plot([x1, x2], [y1, y2], color="gray", linewidth=1.2, zorder=1)[0]
        app.edge_lines[(u, v)] = line

    app.node_patches = {}
    app.node_texts = {}

    for n, (x, y) in pos.items():
        circ = Circle((x, y), 0.05, zorder=2, ec="black", lw=0.8, facecolor="lightblue")
        ax.add_patch(circ)
        app.node_patches[n] = circ
        ax.text(x, y, str(n), ha="center", va="center", fontsize=10, zorder=3)

    vx, vy = app.car_info["visual_x"], app.car_info["visual_y"]
    app.car_point, = ax.plot([vx], [vy], "ro", markersize=10, zorder=4)
    ax.set_aspect("equal", adjustable="datalim")
    app.canvas.draw_idle()


def update_graph_drawing(app):
    """Update positions of edges, nodes, and car after movement."""
    for (u, v), line in app.edge_lines.items():
        x1, y1 = app.pos[u]
        x2, y2 = app.pos[v]
        line.set_data([x1, x2], [y1, y2])

    for n, circ in app.node_patches.items():
        circ.center = app.pos[n]

    vx, vy = app.car_info["visual_x"], app.car_info["visual_y"]
    app.car_point.set_data([vx], [vy])
    app.canvas.draw_idle()