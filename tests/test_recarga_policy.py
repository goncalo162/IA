#!/usr/bin/env python3
import os
from types import SimpleNamespace

from infra.entidades.veiculos import VeiculoCombustao
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


def test_automatica_policy_blocks_with_viagem_ativa():
    ve = make_low_fuel_vehicle()
    # Simular viagem ativa qualquer
    ve.viagens.append(SimpleNamespace(viagem_ativa=True))

    policy = RecargaAutomaticaPolicy()
    assert not policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_allows_with_viagem_ativa():
    ve = make_low_fuel_vehicle()
    ve.viagens.append(SimpleNamespace(
        viagem_ativa=True,
        distancia_restante_km=lambda: 5.0  # Small remaining distance
    ))

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
    os.environ['RECARGA_POLICY'] = 'durante_viagem'
    try:
        policy = Config.get_recarga_policy()
        assert isinstance(policy, RecargaDuranteViagemPolicy)
    finally:
        del os.environ['RECARGA_POLICY']


def test_durante_viagem_policy_schedules_when_autonomia_insuficiente_for_remaining():
    # Veículo com autonomia suficiente para critério, mas insuficiente para viagem ativa
    ve = VeiculoCombustao(
        id_veiculo="V200",
        autonomia_maxima=200,
        autonomia_atual=50,  # 50 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Viagem com 100 km restantes
    ve.viagens.append(SimpleNamespace(
        viagem_ativa=True,
        distancia_total=100.0,
        distancia_percorrida=0.0,
        distancia_restante_km=lambda: 100.0
    ))

    policy = RecargaDuranteViagemPolicy()
    assert policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_does_not_schedule_when_autonomia_suficiente():
    ve = VeiculoCombustao(
        id_veiculo="V201",
        autonomia_maxima=200,
        autonomia_atual=150,  # 150 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Viagem com 100 km restantes (margem de segurança = 10 km)
    ve.viagens.append(SimpleNamespace(
        viagem_ativa=True,
        distancia_total=100.0,
        distancia_percorrida=0.0,
        distancia_restante_km=lambda: 100.0
    ))

    policy = RecargaDuranteViagemPolicy()
    assert not policy.deve_agendar_recarga(ve)


def test_durante_viagem_policy_uses_only_last_active_trip():
    # Autonomia 60 km; last trip has 50 km remaining -> with margem 10 => 60 required
    ve = VeiculoCombustao(
        id_veiculo="V300",
        autonomia_maxima=200,
        autonomia_atual=60,  # 60 km
        capacidade_passageiros=4,
        custo_operacional_km=0.1,
    )

    # Primeira viagem: 100 km restantes
    ve.viagens.append(SimpleNamespace(
        viagem_ativa=True,
        distancia_total=100.0,
        distancia_percorrida=0.0,
        distancia_restante_km=lambda: 100.0
    ))
    # Segunda viagem (continuação): 50 km restantes (deve ser usada)
    ve.viagens.append(SimpleNamespace(
        viagem_ativa=True,
        distancia_total=50.0,
        distancia_percorrida=0.0,
        distancia_restante_km=lambda: 50.0
    ))

    policy = RecargaDuranteViagemPolicy()
    # Não deve agendar porque considera apenas a última viagem (50 + margem 10 = 60 -> suficiente)
    assert not policy.deve_agendar_recarga(ve)
