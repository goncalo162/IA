"""Módulo com implementações de heurísticas para procura informada."""
import math
from typing import Optional


class Heuristica:
    """Interface para heurísticas de busca.

    Implementações devem fornecer `estimativa(grafo, origem, destino)` que
    devolve uma estimativa (lower-bound) do custo entre dois nós.
    """

    def estimativa(self, grafo, origem: str, destino: str) -> float:
        raise NotImplementedError()


class ZeroHeuristica(Heuristica):
    """Heurística neutra (retorna zero)."""

    def estimativa(self, grafo, origem: str, destino: str) -> float:
        return 0.0


class HeuristicaEuclidiana(Heuristica):
    """Heurística baseada na distância euclidiana (distância em linha reta) entre dois nós."""

    def estimativa(self, grafo, origem: str, destino: str) -> float:
        try:
            node_o = grafo.get_node_by_name(origem)
            node_d = grafo.get_node_by_name(destino)

            if node_o is None or node_d is None:
                return 0.0

            x1 = node_o.getX()
            y1 = node_o.getY()
            x2 = node_d.getX()
            y2 = node_d.getY()

            if x1 is None or y1 is None or x2 is None or y2 is None:
                return 0.0

            return float(math.hypot(x2 - x1, y2 - y1))
        except Exception:
            return 0.0
