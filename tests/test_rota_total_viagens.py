import pytest
from datetime import datetime

from infra.entidades.veiculos import VeiculoCombustao, EstadoVeiculo
from infra.entidades.pedidos import Pedido
from infra.entidades.viagem import Viagem


class DummyGrafo:
    def getEdge(self, origem, destino):
        class E:
            def getQuilometro(self):
                return 1.0

            def getVelocidadeMaxima(self):
                return 50.0

            def getTransito(self):
                class T:
                    value = 1.0
                return T()
        return E()


def pedido(pid, pax=1):
    return Pedido(
        pedido_id=pid,
        origem=0,
        destino=1,
        passageiros=pax,
        horario_pretendido=datetime.now(),
        prioridade=1,
        preferencia_ambiental=0,
        ride_sharing=True,
    )


def build_viagem(rota_ate_cliente, rota_pedido):
    # Distâncias fictícias para não interferirem
    return Viagem(
        pedido=pedido(999),
        rota_ate_cliente=rota_ate_cliente,
        rota_pedido=rota_pedido,
        distancia_ate_cliente=0.0,
        distancia_pedido=float(len(rota_pedido) - 1),
        tempo_inicio=datetime.now(),
        grafo=DummyGrafo(),
        velocidade_media=50.0,
    )


def new_vehicle():
    return VeiculoCombustao(
        id_veiculo=1,
        autonomia_maxima=500,
        autonomia_atual=500,
        capacidade_passageiros=5,
        custo_operacional_km=0.2,
        localizacao_atual='A'
    )


def test_single_trip_returns_remaining_route():
    v = new_vehicle()
    trip = build_viagem(['A', 'B'], ['B', 'C', 'D'])
    v.viagens.append(trip)
    v.estado = EstadoVeiculo.EM_ANDAMENTO

    # indice_segmento_atual=0 -> rota_restante = ['A','B','C','D']
    expected = ['A', 'B', 'C', 'D']
    assert v.rota_total_viagens() == expected


def test_two_trips_simple_boundary_duplication_removed():
    v = new_vehicle()
    # Viagem 1 restante: ['A','B','C']
    t1 = build_viagem([], ['A', 'B', 'C'])
    # Viagem 2 restante: ['C','D','E'] (primeiro nó igual ao último de t1)
    t2 = build_viagem([], ['C', 'D', 'E'])
    v.viagens.extend([t1, t2])
    v.estado = EstadoVeiculo.EM_ANDAMENTO

    expected = ['A', 'B', 'C', 'D', 'E']
    assert v.rota_total_viagens() == expected


def test_two_trips_no_boundary_overlap():
    v = new_vehicle()
    # Viagem 1 restante: ['A','B','C']
    t1 = build_viagem([], ['A', 'B', 'C'])
    # Viagem 2 restante: ['X','Y'] (não coincide com 'C')
    t2 = build_viagem([], ['X', 'Y'])
    v.viagens.extend([t1, t2])
    v.estado = EstadoVeiculo.EM_ANDAMENTO

    expected = ['A', 'B', 'C', 'X', 'Y']
    assert v.rota_total_viagens() == expected


def test_multiple_node_overlap_not_collapsed_in_simple_logic():
    v = new_vehicle()
    # Viagem 1: ['A','B','C','D']
    t1 = build_viagem([], ['A', 'B', 'C', 'D'])
    # Viagem 2: ['C','D','E'] -> o algoritmo simples só remove duplicação do primeiro nó
    t2 = build_viagem([], ['C', 'D', 'E'])
    v.viagens.extend([t1, t2])
    v.estado = EstadoVeiculo.EM_ANDAMENTO

    expected = ['A', 'B', 'C', 'D', 'E']
    assert v.rota_total_viagens() == expected
