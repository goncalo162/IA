from collections import deque
from graph.grafo import Grafo

#############
#   *dfs*   
#############

def dfsAux(grafo: Grafo, origem: str, destino: str, visitados: list[str]):
    if origem == destino:
        return [origem]

    visitados.append(origem)

    for (vizinho, _) in grafo.getNeighbours(origem):
        if vizinho not in visitados:
            resultado = dfsAux(grafo, vizinho, destino, visitados)
            if resultado:
                return [origem] + resultado

    return None


def dfs(grafo: Grafo, origem: str, destino: str):
    return dfsAux(grafo, origem, destino, [])


#############
#   *bfs*
#############

def bfs(grafo: Grafo, origem: str, destino: str):
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