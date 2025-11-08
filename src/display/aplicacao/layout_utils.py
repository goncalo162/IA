import networkx as nx
import math

def compute_layout(G, scale=1.0, k_factor=6.0):
    """Compute spring layout with tunable spacing."""

    n = max(1, G.number_of_nodes())
    base_k = math.sqrt(1.0 / n)
    k_value = base_k * k_factor
    layout_scale = 10.0 * scale

    pos = nx.spring_layout(G, seed=42, k=k_value, scale=layout_scale, iterations=300)
    return pos