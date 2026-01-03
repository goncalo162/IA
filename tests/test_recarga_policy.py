#!/usr/bin/env python3
import os
from datetime import datetime

from infra.entidades.veiculos import VeiculoCombustao
from infra.entidades.pedidos import Pedido
from infra.entidades.viagem import Viagem
from infra.grafo.grafo import Grafo
from infra.grafo.node import Node
from infra.grafo.aresta import Aresta, NivelTransito
from infra.policies.recarga_policy import RecargaAutomaticaPolicy, RecargaDuranteViagemPolicy
from config import Config


def make_low_fuel_vehicle():
    return VeiculoCombustao(
        id_veiculo="V100",
        autonomia_maxima=100,
        autonomia_atual=10,  # 10% -> precisa reabastecer (critico 20%)
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )


def make_simple_grafo():
    """Cria um grafo simples para testes."""
    grafo = Grafo()

    # Criar nós e arestas (add_edge adiciona nós automaticamente)
    node_a = Node("A", 0, 0)
    node_b = Node("B", 10, 0)
    node_c = Node("C", 20, 0)

    aresta_ab = Aresta(10.0, 50.0, "A-B", NivelTransito.NORMAL)
    aresta_bc = Aresta(10.0, 50.0, "B-C", NivelTransito.NORMAL)

    grafo.add_edge(node_a, node_b, aresta_ab)
    grafo.add_edge(node_b, node_c, aresta_bc)

    return grafo


def make_viagem(grafo, distancia_total=100.0, distancia_percorrida=0.0):
    """Cria uma viagem real para testes."""
    pedido = Pedido(
        pedido_id=1,
        origem="A",
        destino="C",
        passageiros=1,
        horario_pretendido=datetime.now(),
        prioridade=1
    )

    viagem = Viagem(
        pedido=pedido,
        rota_ate_cliente=["A"],
        rota_pedido=["A", "B", "C"],
        distancia_ate_cliente=0.0,
        distancia_pedido=distancia_total,
        tempo_inicio=datetime.now(),
        grafo=grafo
    )

    # Ajustar distâncias manualmente para controlar testes
    viagem.distancia_total = distancia_total
    viagem.distancia_percorrida = distancia_percorrida

    return viagem


def test_automatica_policy_blocks_with_viagem_ativa():
    grafo = make_simple_grafo()
    ve = make_low_fuel_vehicle()

    # Adicionar viagem ativa real
    viagem = make_viagem(grafo)
    ve.viagens.append(viagem)

    policy = RecargaAutomaticaPolicy()
    assert not policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_allows_with_viagem_ativa():
    grafo = make_simple_grafo()
    ve = make_low_fuel_vehicle()

    # Viagem com distância restante de 15 km (autonomia atual é 10 km, não suficiente com margem)
    viagem = make_viagem(grafo, distancia_total=20.0, distancia_percorrida=5.0)
    ve.viagens.append(viagem)

    policy = RecargaDuranteViagemPolicy()
    assert policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_respects_precisa_reabastecer():
    # Se não precisa, não agenda
    ve = VeiculoCombustao(
        id_veiculo="V101",
        autonomia_maxima=100,
        autonomia_atual=80,  # 80% -> não precisa
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    policy = RecargaDuranteViagemPolicy()
    assert not policy.deve_agendar_recarga(ve)


def test_config_returns_durante_viagem_policy():
    os.environ['POLITICA_RECARGA'] = 'durante_viagem'
    try:
        policy = Config.get_recarga_policy()
        assert isinstance(policy, RecargaDuranteViagemPolicy)
    finally:
        os.environ.pop('POLITICA_RECARGA', None)


def test_durante_viagem_policy_schedules_when_autonomia_insuficiente_for_remaining():
    grafo = make_simple_grafo()

    # Veículo com autonomia suficiente para critério, mas insuficiente para viagem ativa
    ve = VeiculoCombustao(
        id_veiculo="V200",
        autonomia_maxima=200,
        autonomia_atual=50,  # 50 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Viagem com 100 km restantes
    viagem = make_viagem(grafo, distancia_total=100.0, distancia_percorrida=0.0)
    ve.viagens.append(viagem)

    policy = RecargaDuranteViagemPolicy()
    assert policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_does_not_schedule_when_autonomia_suficiente():
    grafo = make_simple_grafo()

    ve = VeiculoCombustao(
        id_veiculo="V201",
        autonomia_maxima=200,
        autonomia_atual=150,  # 150 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Viagem com 100 km restantes (margem de segurança = 10 km)
    viagem = make_viagem(grafo, distancia_total=100.0, distancia_percorrida=0.0)
    ve.viagens.append(viagem)

    policy = RecargaDuranteViagemPolicy()
    assert not policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_uses_only_last_active_trip():
    grafo = make_simple_grafo()

    # Autonomia 60 km; last trip has 50 km remaining -> with margem 10 => 60 required
    ve = VeiculoCombustao(
        id_veiculo="V300",
        autonomia_maxima=200,
        autonomia_atual=60,  # 60 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Primeira viagem: 100 km restantes
    viagem1 = make_viagem(grafo, distancia_total=100.0, distancia_percorrida=0.0)
    ve.viagens.append(viagem1)

    # Segunda viagem (continuação): 50 km restantes (deve ser usada)
    viagem2 = make_viagem(grafo, distancia_total=50.0, distancia_percorrida=0.0)
    ve.viagens.append(viagem2)

    policy = RecargaDuranteViagemPolicy()
    # Não deve agendar porque considera apenas a última viagem (50 + margem 10 = 60 -> suficiente)
    assert not policy.deve_agendar_recarga(ve)
