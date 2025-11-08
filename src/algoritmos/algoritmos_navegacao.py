from collections import deque
from algoritmos.navegador_base import NavegadorBase
from infra.grafo.grafo import Grafo

#Implementação dos algoritmos de navegação

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

    def nome_algoritmo(self) -> str:
        return "BFS"

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