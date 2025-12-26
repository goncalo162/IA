from infra.grafo.grafo import Grafo
from infra.grafo.node import Node
from infra.grafo.aresta import Aresta
from algoritmos.algoritmos_navegacao import NavegadorBidirecional


def _build_chain_graph():
    g = Grafo(directed=False)
    nA = Node('A')
    nB = Node('B')
    nC = Node('C')
    nD = Node('D')

    aAB = Aresta(1, 1, 'AB')
    aBC = Aresta(1, 1, 'BC')
    aCD = Aresta(1, 1, 'CD')

    g.add_edge(nA, nB, aAB)
    g.add_edge(nB, nC, aBC)
    g.add_edge(nC, nD, aCD)

    return g


def test_bidirecional_chain():
    g = _build_chain_graph()
    nav = NavegadorBidirecional()

    rota = nav.calcular_rota(g, 'A', 'D')
    assert rota == ['A', 'B', 'C', 'D']


def test_bidirecional_same_as_bfs_on_shortest():
    g = _build_chain_graph()
    nav = NavegadorBidirecional()

    # shortest by edges A->C
    rota = nav.calcular_rota(g, 'A', 'C')
    assert rota == ['A', 'B', 'C']


def test_bidirecional_no_path_returns_none():
    g = Grafo(directed=False)
    nA = Node('A')
    nB = Node('B')
    nC = Node('C')
    nD = Node('D')

    # two components: A-B and C-D
    g.add_edge(nA, nB, Aresta(1, 1, 'AB'))
    g.add_edge(nC, nD, Aresta(1, 1, 'CD'))

    nav = NavegadorBidirecional()
    assert nav.calcular_rota(g, 'A', 'D') is None
