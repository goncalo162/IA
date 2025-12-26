import heapq
from typing import Optional, List, Dict
from collections import deque
from algoritmos.navegador_base import NavegadorBase
from infra.grafo.grafo import Grafo


# Implementação dos algoritmos de navegação

#############
#   *dfs*
#############

class NavegadorDFS(NavegadorBase):
    """
    Implementação de DFS (Depth-First Search) para procura de caminhos.
    DFS explora em profundidade antes de explorar outros ramos.
    """

    def dfsAux(self, grafo: Grafo, origem: str, destino: str, visitados: list[str]):
        if origem == destino:
            return [origem]

        visitados.append(origem)

        for (vizinho, _) in grafo.getNeighbours(origem):
            if vizinho not in visitados:
                resultado = self.dfsAux(grafo, vizinho, destino, visitados)
                if resultado:
                    return [origem] + resultado

        return None

    def dfs(self, grafo: Grafo, origem: str, destino: str):
        return self.dfsAux(grafo, origem, destino, [])

    def calcular_rota(self, grafo: Grafo, origem: str, destino: str):
        return self.dfs(grafo, origem, destino)

    def nome_algoritmo(self) -> str:
        return "DFS (Depth-First Search)"


#############
#   *bfs*
#############


class NavegadorBFS(NavegadorBase):
    """
    Implementação de BFS (Breadth-First Search) para procura de caminhos.
    BFS garante o caminho com menor número de arestas (não necessariamente o mais curto em distância).
    """

    def bfs(self, grafo: Grafo, origem: str, destino: str):
        if origem == destino:
            return [origem]

        fila = deque([[origem]])
        visitados = set([origem])

        while fila:
            caminho = fila.popleft()
            no_atual = caminho[-1]

            for vizinho, _ in grafo.getNeighbours(no_atual):
                if vizinho not in visitados:
                    novo_caminho = caminho + [vizinho]
                    if vizinho == destino:
                        return novo_caminho
                    fila.append(novo_caminho)
                    visitados.add(vizinho)

        return None

    def calcular_rota(self, grafo: Grafo, origem: str, destino: str):
        return self.bfs(grafo, origem, destino)

    def nome_algoritmo(self) -> str:
        return "BFS (Breadth-First Search)"

#############
#   *ucs*
#############


class NavegadorCustoUniforme(NavegadorBase):
    """
    Implementação do algoritmo Uniform Cost Search (UCS).
    Usa apenas custos reais das arestas (sem heurística).
    """

    def calcular_rota(self, grafo: Grafo, origem: str, destino: str, veiculo: Optional[object] = None) -> Optional[List[str]]:
        if origem == destino:
            return [origem]

        # Fila de prioridade com tuplos (custo acumulado, nó atual, caminho)
        fronteira = [(0.0, origem, [origem])]
        melhor_custo = {origem: 0.0}

        while fronteira:
            custo_atual, no_atual, caminho = heapq.heappop(fronteira)

            # Se chegámos ao destino, devolvemos o caminho
            if no_atual == destino:
                return caminho

            # Garantia de optimalidade: se já vimos este nó com custo menor, ignoramos
            if custo_atual > melhor_custo.get(no_atual, float("inf")):
                continue

            # Percorrer todas as arestas que saem do nó atual
            # getNeighbours retorna lista de tuplos (nome_vizinho, aresta)
            vizinhos = grafo.getNeighbours(no_atual)
            if vizinhos is None:
                continue

            for (no_destino, aresta) in vizinhos:
                if veiculo is None:
                    custo_aresta = self.funcao_custo.custo_aresta(aresta)
                else:
                    custo_aresta = self.funcao_custo.custo_aresta(
                        aresta, veiculo)

                novo_custo = custo_atual + custo_aresta

                # Só expandimos caminhos melhores
                if novo_custo < melhor_custo.get(no_destino, float("inf")):
                    melhor_custo[no_destino] = novo_custo
                    heapq.heappush(
                        fronteira,
                        (novo_custo, no_destino, caminho + [no_destino])
                    )

        return None  # Sem caminho possível

    def nome_algoritmo(self) -> str:
        return "Custo Uniforme"

#############
#   *a star*
#############


class NavegadorAEstrela(NavegadorBase):
    """
    Implementação do algoritmo A* Informed Search.
    Combina custo acumulado (g) com uma heurística (h)
    para minimizar f = g + h.
    """

    def nome_algoritmo(self) -> str:
        return "A* Informed"

    def calcular_rota(self, grafo: Grafo, origem: str, destino: str, veiculo: Optional[object] = None) -> Optional[List[str]]:
        if origem == destino:
            return [origem]

        # Priority queue storing (f(n), g(n), node, path)
        fronteira = []

        # custo acumulado g(origem) = 0
        custoAcumulado_inicial = 0.0

        # f(origem) = g + h
        custoEstimado_inicial = custoAcumulado_inicial + \
            self.heuristica.estimativa(grafo, origem, destino)

        heapq.heappush(fronteira, (custoEstimado_inicial,
                       custoAcumulado_inicial, origem, [origem]))

        # Guarda o menor custo já encontrado para cada nó (g(n))
        melhor_g = {origem: 0.0}

        while fronteira:
            custoEstimado_atual, custoAcumulado_atual, no_atual, caminho = heapq.heappop(
                fronteira)

            # Se chegámos ao destino → devolvemos o caminho ótimo
            if no_atual == destino:
                return caminho

            # Expandir vizinhos
            # getNeighbours retorna lista de tuplos (nome_vizinho, aresta)
            for (no_vizinho, aresta) in grafo.getNeighbours(no_atual):
                # custo da aresta (pode depender do veículo)
                custo_aresta = self.funcao_custo.custo_aresta(aresta, veiculo)
                custoAcumulado_novo = custoAcumulado_atual + custo_aresta

                # Se este caminho for pior do que outro já encontrado, ignora
                if custoAcumulado_novo >= melhor_g.get(no_vizinho, float("inf")):
                    continue

                melhor_g[no_vizinho] = custoAcumulado_novo

                # calcular h(n)
                heuristica_nova = self.heuristica.estimativa(
                    grafo, no_vizinho, destino)

                # f(n) = g(n) + h(n)
                custoEstimado_novo = custoAcumulado_novo + heuristica_nova

                heapq.heappush(
                    fronteira,
                    (custoEstimado_novo, custoAcumulado_novo,
                     no_vizinho, caminho + [no_vizinho])
                )

        return None  # Sem caminho

#NOTA: REVER ESTE ALGORITMO
class NavegadorBidirecional(NavegadorBase):
    """
    Procura bidirecional: expande simultaneamente a partir da origem e do destino.

    Funciona melhor em grafos não dirigidos; em grafos dirigidos a expansão "para trás"
    utiliza uma verificação por predecessores (mais custosa).
    """

    def nome_algoritmo(self) -> str:
        return "Bidirecional"

    def _predecessors(self, grafo: Grafo, nodo: str):
        """Retorna lista de tuplos (nome_nodo, aresta) que apontam para `nodo`.

        Nota: Grafo não fornece API direta para predecessores; percorremos as
        adjacências. Em grafos não dirigidos isso é equivalente a neighbours.
        """
        preds = []
        try:
            for n, adj in grafo.m_graph.items():
                for (dest, aresta) in adj:
                    if dest == nodo:
                        preds.append((n, aresta))
        except Exception:
            return []
        return preds

    def calcular_rota(self, grafo: Grafo, origem: str, destino: str):
        if origem == destino:
            return [origem]

        # fronteiras: mapa nodo -> caminho (lista de nomes) desde a origem/destino
        fronteira_frente = {origem: [origem]}
        fronteira_tras = {destino: [destino]}

        visitados_frente = {origem: [origem]}
        visitados_tras = {destino: [destino]}

        while fronteira_frente and fronteira_tras:
            # Expandir a fronteira com menos nós (heurística simples)
            if len(fronteira_frente) <= len(fronteira_tras):
                # expandir frente
                nodo_atual, caminho = fronteira_frente.popitem()

                for (vizinho, _) in grafo.getNeighbours(nodo_atual):
                    if vizinho in visitados_frente:
                        continue

                    novo_caminho = caminho + [vizinho]
                    visitados_frente[vizinho] = novo_caminho
                    fronteira_frente[vizinho] = novo_caminho

                    if vizinho in visitados_tras:
                        # encontro — combinar caminhos
                        caminho_destino = visitados_tras[vizinho]
                        caminho_dest_rev = caminho_destino[::-1]
                        return novo_caminho + caminho_dest_rev[1:]
            else:
                # expandir trás (usar predecessores para grafos dirigidos)
                nodo_atual, caminho = fronteira_tras.popitem()

                preds = self._predecessors(grafo, nodo_atual)
                # se grafo não for dirigido, preds equivale a getNeighbours
                if not preds:
                    preds = [(n, a) for (n, a) in grafo.getNeighbours(nodo_atual)]

                for (vizinho, _) in preds:
                    if vizinho in visitados_tras:
                        continue

                    novo_caminho = caminho + [vizinho]
                    visitados_tras[vizinho] = novo_caminho
                    fronteira_tras[vizinho] = novo_caminho

                    if vizinho in visitados_frente:
                        caminho_frente = visitados_frente[vizinho]
                        caminho_tras_rev = novo_caminho[::-1]
                        return caminho_frente + caminho_tras_rev[1:]

        return None
