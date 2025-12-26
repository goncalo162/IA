"""Testes para políticas de reposicionamento baseadas em atratividade."""
from datetime import datetime

from infra.grafo.grafo import Grafo
from infra.grafo.node import Node
from infra.grafo.aresta import Aresta
from infra.entidades.veiculos import VeiculoCombustao
from infra.policies.reposicionamento_policy import ReposicionamentoAtratividade



def _criar_grafo_com_nodos(nodos):
    g = Grafo()
    # conectar nodos sequencialmente para que fiquem registados no grafo
    prev = None
    for n in nodos:
        if prev is not None:
            g.add_edge(prev, n, Aresta(quilometro=1, velocidadeMaxima=50, nome=f"e_{prev.getName()}_{n.getName()}"))
        prev = n
    return g


def test_atratividade_reposiciona_para_zona_top():
    # Criar grafo com três zonas com diferentes atratividades
    a = Node("A", x=0, y=0, atratividade=10)
    b = Node("B", x=10, y=0, atratividade=5)
    c = Node("C", x=20, y=0, atratividade=1)

    g = _criar_grafo_com_nodos([a, b, c])

    # Criar 5 veículos em posições variadas
    veiculos = [
        VeiculoCombustao(i, 500, 500, 4, 0.15, localizacao_atual="C") for i in range(1, 4)
    ]
    veiculos += [
        VeiculoCombustao(4, 500, 500, 4, 0.15, localizacao_atual="B"),
        VeiculoCombustao(5, 500, 500, 4, 0.15, localizacao_atual="A"),
    ]

    policy = ReposicionamentoAtratividade(top_k_zonas=3, percentual_veiculos_reposicionar=0.3, distancia_maxima_reposicionamento=1000)

    repos = policy.decidir_reposicionamentos(veiculos, g, ambiente=None, tempo_simulacao=datetime.now())

    # Com 5 veículos e percentual 0.3 => deve escolher 1 veículo e a zona de destino deve ser a de maior atratividade (A)
    assert len(repos) == 1
    _, destino = repos[0]
    assert destino == "A"


def test_atratividade_sem_areas_retorna_vazio():
    # nodos sem atratividade não devem gerar reposicionamentos
    a = Node("A", x=0, y=0, atratividade=0)
    b = Node("B", x=10, y=0, atratividade=0)

    g = _criar_grafo_com_nodos([a, b])

    veiculos = [VeiculoCombustao(1, 500, 500, 4, 0.15, localizacao_atual="A")]

    policy = ReposicionamentoAtratividade()
    repos = policy.decidir_reposicionamentos(veiculos, g, ambiente=None, tempo_simulacao=datetime.now())

    assert repos == []
