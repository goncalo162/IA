"""
Módulo com classes de abstração para funções de custo e heurísticas.

Define interfaces simples que os algoritmos podem receber para customizar
comportamento de custo (por exemplo, custo por km, penalizações) e heurística
para pesquisas informadas.
"""
from typing import List, Optional


class FuncaoCusto:
    """Interface para função de custo.

    Implementações devem fornecer `custo_rota(grafo, rota, veiculo)` que
    devolve o custo total de uma rota, e `custo_aresta(aresta, veiculo)` que
    devolve o custo de uma aresta individual.
    """

    # TODO: rever isto
    def custo_rota(self, grafo, rota: List[str], veiculo: Optional[object]) -> float:
        raise NotImplementedError()

    def custo_aresta(self, aresta, veiculo: Optional[object]) -> float:
        raise NotImplementedError()


class Heuristica:
    """Interface para heurísticas de busca.

    Implementações devem fornecer `estimativa(grafo, origem, destino)` que
    devolve uma estimativa (lower-bound) do custo entre dois nós.
    """

    def estimativa(self, grafo, origem: str, destino: str) -> float:
        raise NotImplementedError()


class CustoDefault(FuncaoCusto):
    """Custo por defeito baseado na soma das distâncias das arestas (km).

    Usa `aresta.getQuilometro()` quando disponível.
    """

    def custo_rota(self, grafo, rota: List[str], veiculo: Optional[object] = None) -> float:
        distancia = 0.0
        if not rota or len(rota) < 2:
            return 0.0
        for i in range(len(rota) - 1):
            aresta = grafo.getEdge(rota[i], rota[i + 1])
            if aresta:
                try:
                    distancia += self.custo_aresta(aresta, veiculo)
                except Exception:
                    pass
        return distancia

    def custo_aresta(self, aresta, veiculo: Optional[object] = None) -> float:
        try:
            return float(aresta.getQuilometro())
        except Exception:
            return 0.0


class CustoTempoPercurso(FuncaoCusto):
    """Custo baseado no tempo de percurso, tendo em conta o trânsito.

    Usa `aresta.getTempoPercorrer()` que considera o nível de trânsito.
    Arestas com acidente (retornam None) são penalizadas com custo infinito.
    """

    def custo_rota(self, grafo, rota: List[str], veiculo: Optional[object] = None) -> float:
        tempo_total = 0.0
        if not rota or len(rota) < 2:
            return 0.0
        for i in range(len(rota) - 1):
            aresta = grafo.getEdge(rota[i], rota[i + 1])
            if aresta:
                custo = self.custo_aresta(aresta, veiculo)
                if custo == float('inf'):
                    return float('inf')  # Rota impossível devido a acidente
                tempo_total += custo
        return tempo_total

    def custo_aresta(self, aresta, veiculo: Optional[object] = None) -> float:
        try:
            tempo = aresta.getTempoPercorrer()
            if tempo is None:  # Acidente na aresta
                return float('inf')
            return float(tempo)
        except Exception:
            return 0.0


class ZeroHeuristica(Heuristica):
    """Heurística neutra (retorna zero)."""

    def estimativa(self, grafo, origem: str, destino: str) -> float:
        return 0.0
