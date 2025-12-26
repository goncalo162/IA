#!/usr/bin/env python3
"""
Script de teste para verificar o sistema de recarga/abastecimento de veículos.
"""

from infra.entidades.veiculos import VeiculoCombustao, VeiculoEletrico
from datetime import datetime


def test_recarga():
    print("=" * 60)
    print("TESTE DO SISTEMA DE RECARGA/ABASTECIMENTO")
    print("=" * 60)
    print()

    # Criar veículo a combustão com baixa autonomia
    print("1. Testando Veículo a Combustão")
    print("-" * 40)
    veiculo_combustao = VeiculoCombustao(
        id_veiculo="V001",
        autonomia_maxima=500,
        autonomia_atual=50,  # 10% de autonomia
        capacidade_passageiros=4,
        custo_operacional_km=0.15,
        localizacao_atual="Braga Centro"
    )

    print(
        f"Autonomia atual: {veiculo_combustao.autonomia_atual}/{veiculo_combustao.autonomia_maxima} km")
    print(f"Percentual: {veiculo_combustao.percentual_autonomia_atual:.1f}%")
    print(f"Precisa reabastecer? {veiculo_combustao.precisa_reabastecer()}")
    print(f"Tem autonomia para 100 km? {veiculo_combustao.autonomia_suficiente_para(100)}")
    print(f"Tempo de reabastecimento: {veiculo_combustao.tempoReabastecimento()} min")

    # Simular recarga
    print("\nIniciando recarga...")
    veiculo_combustao.iniciar_recarga(datetime.now(), "Posto Central")
    print(f"Estado: {veiculo_combustao.estado}")
    print(f"Localização de abastecimento: {veiculo_combustao.localizacao_abastecimento}")

    veiculo_combustao.reabastecer()
    print(f"\nApós reabastecimento:")
    print(f"Autonomia: {veiculo_combustao.autonomia_atual}/{veiculo_combustao.autonomia_maxima} km")
    print(f"Estado: {veiculo_combustao.estado}")

    print("\n" + "=" * 60)
    print("2. Testando Veículo Elétrico")
    print("-" * 40)

    veiculo_eletrico = VeiculoEletrico(
        id_veiculo="V003",
        autonomia_maxima=400,
        autonomia_atual=60,  # 15% de autonomia
        capacidade_passageiros=5,
        custo_operacional_km=0.08,
        tempo_recarga_km=2.0,
        localizacao_atual="Estação de Carregamento"
    )

    print(
        f"Autonomia atual: {veiculo_eletrico.autonomia_atual}/{veiculo_eletrico.autonomia_maxima} km")
    print(f"Percentual: {veiculo_eletrico.percentual_autonomia_atual:.1f}%")
    print(f"Precisa reabastecer? {veiculo_eletrico.precisa_reabastecer()}")
    print(f"Tem autonomia para 100 km? {veiculo_eletrico.autonomia_suficiente_para(100)}")

    autonomia_a_recarregar = veiculo_eletrico.autonomia_maxima - veiculo_eletrico.autonomia_atual
    tempo_recarga = veiculo_eletrico.tempoReabastecimento()
    print(f"Autonomia a recarregar: {autonomia_a_recarregar} km")
    print(f"Tempo de recarga estimado: {tempo_recarga:.1f} min ({tempo_recarga / 60:.2f} horas)")

    # Simular recarga
    print("\nIniciando recarga...")
    veiculo_eletrico.iniciar_recarga(datetime.now(), "Estação de Carregamento")
    print(f"Estado: {veiculo_eletrico.estado}")

    veiculo_eletrico.reabastecer()
    print(f"\nApós recarga:")
    print(f"Autonomia: {veiculo_eletrico.autonomia_atual}/{veiculo_eletrico.autonomia_maxima} km")
    print(f"Estado: {veiculo_eletrico.estado}")

    print("\n" + "=" * 60)
    print("3. Testando simulação de consumo")
    print("-" * 40)

    # Criar veículo com boa autonomia
    veiculo_teste = VeiculoCombustao(
        id_veiculo="V999",
        autonomia_maxima=500,
        autonomia_atual=500,
        capacidade_passageiros=4,
        custo_operacional_km=0.15,
        localizacao_atual="Origem"
    )

    print(f"Autonomia inicial: {veiculo_teste.autonomia_atual} km")
    print(f"Precisa reabastecer? {veiculo_teste.precisa_reabastecer()}")

    # Simular viagens
    distancias = [50, 100, 150, 200]
    for dist in distancias:
        veiculo_teste.atualizar_autonomia(dist)
        print(f"\nApós percorrer {dist} km:")
        print(
            f"  Autonomia: {
                veiculo_teste.autonomia_atual} km ({
                veiculo_teste.percentual_autonomia_atual:.1f}%)")
        print(f"  Precisa reabastecer? {veiculo_teste.precisa_reabastecer()}")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO COM SUCESSO! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_recarga()
