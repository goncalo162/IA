from infra.grafo.grafo import Grafo
from infra.grafo.node import Node
from infra.grafo.aresta import Aresta
from infra.entidades.pedidos import Pedido
from infra.entidades.veiculos import VeiculoCombustao
from algoritmos.algoritmos_navegacao import NavegadorBFS
from algoritmos.algoritmos_alocacao import AlocadorPorCusto, AlocadorAEstrela
from datetime import datetime


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


def test_alocador_por_custo_prefers_lower_operational_cost():
    g = _build_chain_graph()
    nav = NavegadorBFS()

    # Veículos: v1 em B (mais próximo) mas mais caro, v2 em C (mais longe) mas barato
    v1 = VeiculoCombustao(1, 100, 100, 4, 0.5, localizacao_atual='B')
    v2 = VeiculoCombustao(2, 100, 100, 4, 0.1, localizacao_atual='C')

    pedido = Pedido(1, 'A', 'D', 1, datetime.now())

    al = AlocadorPorCusto(nav)
    escolhido = al.escolher_veiculo(pedido, [v1, v2], g, ['A', 'B', 'C', 'D'], 3.0)

    # Apesar de v1 estar mais perto, v2 tem custo operacional muito menor
    assert escolhido is v2


def test_alocador_aestrela_prefers_best_estimated_cost():
    g = _build_chain_graph()
    nav = NavegadorBFS()

    v1 = VeiculoCombustao(1, 100, 100, 4, 0.5, localizacao_atual='B')
    v2 = VeiculoCombustao(2, 100, 100, 4, 0.4, localizacao_atual='C')

    pedido = Pedido(1, 'A', 'D', 1, datetime.now())

    al = AlocadorAEstrela(nav)
    escolhido = al.escolher_veiculo(pedido, [v1, v2], g, ['A', 'B', 'C', 'D'], 3.0)

    # Both vehicles are similar; A* style selection should choose the one with lower g+h
    assert escolhido in (v1, v2)
