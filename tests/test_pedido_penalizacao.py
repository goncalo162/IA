from infra.metricas import Metricas


def test_registar_pedido_rejeitado_aplica_penalidade():
    m = Metricas()

    assert m.pedidos_rejeitados == 0
    assert m.custo_total == 0.0
    assert m.custo_penalizacoes == 0.0

    # Registar rejeição com penalidade
    m.registar_pedido_rejeitado(42, "motivo qualquer", penalidade=50.0)

    assert m.pedidos_rejeitados == 1
    assert m.custo_total == 50.0
    assert m.custo_penalizacoes == 50.0
    # Histórico contém a penalidade registada
    entry = m.historico_pedidos[-1]
    assert entry['pedido_id'] == 42
    assert entry['rejeitado'] is True
    assert entry['penalidade'] == 50.0
