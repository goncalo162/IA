from datetime import datetime

from infra.grafo.grafo import Grafo
from infra.grafo.node import Node
from infra.grafo.aresta import Aresta
from infra.entidades.veiculos import VeiculoCombustao
from infra.policies.reposicionamento_policy import ReposicionamentoAtratividade


def _criar_grafo_com_nodos():
    g = Grafo()

    # Criar 3 nós com diferentes atratividades e coordenadas
    nA = Node('A', x=0, y=0, atratividade=10)
    nB = Node('B', x=10, y=0, atratividade=5)
    nC = Node('C', x=20, y=0, atratividade=1)

    # Adicionar arestas para garantir nodes no grafo
    a_ab = Aresta(1, 50, 'A-B')
    a_bc = Aresta(1, 50, 'B-C')

    g.add_edge(nA, nB, a_ab)
    g.add_edge(nB, nC, a_bc)

    return g


def test_reposiciona_para_zona_mais_atrativa():
    g = _criar_grafo_com_nodos()

    v1 = VeiculoCombustao(1, 100, 100, 4, 0.1, localizacao_atual='C')
    v2 = VeiculoCombustao(2, 100, 100, 4, 0.1, localizacao_atual='C')

    policy = ReposicionamentoAtratividade(top_k_zonas=1, percentual_veiculos_reposicionar=0.5, distancia_maxima_reposicionamento=1000, intervalo_reposicionamento_minutos=0)

    now = datetime.now()
    repos = policy.decidir_reposicionamentos([v1, v2], g, tempo_simulacao=now)

    assert len(repos) == 1
    ve, destino = repos[0]
    assert destino == 'A'
    assert ve in (v1, v2)


def test_percentual_1_reposiciona_todos():
    g = _criar_grafo_com_nodos()

    v1 = VeiculoCombustao(1, 100, 100, 4, 0.1, localizacao_atual='C')
    v2 = VeiculoCombustao(2, 100, 100, 4, 0.1, localizacao_atual='B')

    # Reposiciona 100% dos veículos para top-2 zonas
    policy = ReposicionamentoAtratividade(top_k_zonas=2, percentual_veiculos_reposicionar=1.0, distancia_maxima_reposicionamento=1000, intervalo_reposicionamento_minutos=0)

    now = datetime.now()
    repos = policy.decidir_reposicionamentos([v1, v2], g, tempo_simulacao=now)

    assert len(repos) == 2
    destinos = {d for (_, d) in repos}
    assert destinos.issubset({'A', 'B'})


def test_respeita_distancia_maxima():
    g = _criar_grafo_com_nodos()

    # Colocar veículo muito longe ao forçar coords distantes
    v1 = VeiculoCombustao(1, 100, 100, 4, 0.1, localizacao_atual='C')

    # distância máxima muito pequena -> não deve haver reposicionamentos
    policy = ReposicionamentoAtratividade(top_k_zonas=1, percentual_veiculos_reposicionar=1.0, distancia_maxima_reposicionamento=0.1, intervalo_reposicionamento_minutos=0)

    now = datetime.now()
    repos = policy.decidir_reposicionamentos([v1], g, tempo_simulacao=now)

    assert repos == []
