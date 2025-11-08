import networkx as nx
import math

def compute_layout(G):
    """Generate wide-spaced, full-screen layout."""
    n = max(1, G.number_of_nodes())
    base_k = math.sqrt(1.0 / n)
    k_value = base_k * 8.0
    layout_scale = 25.0

    pos = nx.spring_layout(G, seed=42, k=k_value, scale=layout_scale, iterations=300)

    # Normalize coordinates to fit screen space (-1 to 1)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    for k, (x, y) in pos.items():
        pos[k] = ((x - minx) / (maxx - minx) * 2 - 1, (y - miny) / (maxy - miny) * 2 - 1)

    return pos