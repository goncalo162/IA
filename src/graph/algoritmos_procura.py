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


#############
#   *greedy*
#############

def greedy(grafo: Grafo, origem: str, destino: str):
    if origem == destino:
        return [origem]

    fronteira = [(0, [origem])]  # (heuristic cost, path)
    visitados = set()

    while fronteira:
        fronteira.sort(key=lambda x: x[0])
        custo_atual, caminho = fronteira.pop(0)
        no_atual = caminho[-1]

        if no_atual in visitados:
            continue
        visitados.add(no_atual)

        if no_atual == destino:
            return caminho

        for vizinho, _ in grafo.getNeighbours(no_atual):
            if vizinho not in visitados:
                custo = grafo.get_arc_cost(no_atual, vizinho)
                novo_caminho = caminho + [vizinho]
                fronteira.append((custo, novo_caminho))

    return None