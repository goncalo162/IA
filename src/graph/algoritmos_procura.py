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
    caminhos = [[origem]]
    
    return dfsAux(grafo, origem, destino, [])