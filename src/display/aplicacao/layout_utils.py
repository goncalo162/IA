"""Algoritmos de layout com melhor espaçamento."""

import networkx as nx
import math


def compute_layout_circular(G, scale=1.0):
    """Layout circular - bom para grafo pequeno."""
    return nx.circular_layout(G, scale=scale * 10.0)


def compute_layout_spring(G, scale=1.0, k_factor=6.0):
    """Layout spring com espaçamento configurável."""
    n = max(1, G.number_of_nodes())
    base_k = math.sqrt(1.0 / n)
    k_value = base_k * k_factor
    layout_scale = 10.0 * scale

    pos = nx.spring_layout(G, seed=42, k=k_value, scale=layout_scale, iterations=300)
    return pos


def compute_layout_kamada_kawai(G, scale=1.0):
    """Layout Kamada-Kawai - melhor para visualização."""
    pos = nx.kamada_kawai_layout(G)
    return pos * (scale * 10.0)


def compute_layout_best(G, scale=1.0):
    """
    Escolhe o melhor layout baseado no tamanho do grafo.

    scale: multiplicador de espaçamento (1.0 = normal, 2.0 = 2x mais espaço)
    """
    n = G.number_of_nodes()

    if n < 10:
        # Pequeno grafo: circular é bom
        return compute_layout_circular(G, scale)
    elif n < 50:
        # Médio: Kamada-Kawai é melhor
        return compute_layout_kamada_kawai(G, scale)
    else:
        # Grande: Spring com espaçamento maior
        return compute_layout_spring(G, scale, k_factor=12.0)  # k_factor aumentado


def compute_layout_spacious(G, scale=1.0):
    """Layout com MUITO espaçamento (use isto para visualização confortável)."""
    n = G.number_of_nodes()

    # Aumentar k_factor significativamente
    if n < 10:
        return compute_layout_circular(G, scale * 2.0)
    elif n < 50:
        return compute_layout_kamada_kawai(G, scale * 2.0)
    else:
        return compute_layout_spring(G, scale * 2.5, k_factor=15.0)


def compute_layout_compact(G, scale=1.0):
    """Layout compacto (use isto para muitos nós)."""
    n = G.number_of_nodes()

    if n < 10:
        return compute_layout_circular(G, scale * 0.7)
    elif n < 50:
        return compute_layout_kamada_kawai(G, scale * 0.7)
    else:
        return compute_layout_spring(G, scale * 0.5, k_factor=4.0)
