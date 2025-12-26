"""Testes para exportação e relatório de reposicionamentos nas métricas."""
import csv

from infra.metricas import Metricas


def test_registar_reposicionamentos_e_relatorio():
    m = Metricas()

    # Registar alguns reposicionamentos
    m.registar_reposicionamento(veiculo_id=1, origem="A", destino="B", distancia=2.5)
    m.registar_reposicionamento(veiculo_id=2, origem="C", destino="A", distancia=3.0)

    assert m.reposicionamentos_totais == 2
    assert abs(m.distancia_reposicionamento_total - 5.5) < 1e-6
    assert m.reposicionamentos_por_veiculo[1] == 1
    assert m.reposicionamentos_por_veiculo[2] == 1

    rel = m.gerar_relatorio()
    assert "Total de reposicionamentos: 2" in rel
    assert "Distância total em reposicionamentos" in rel


def test_exportar_json_e_csv(tmp_path):
    m = Metricas()
    m.registar_reposicionamento(veiculo_id=1, origem="A", destino="B", distancia=2.5)

    j = m.exportar_json()
    assert 'reposicionamentos' in j
    r = j['reposicionamentos']
    assert r['total_reposicionamentos'] == 1
    assert abs(r['distancia_total_km'] - 2.5) < 1e-6
    assert isinstance(r['historico_reposicionamentos'], list)

    # CSV export should include the reposicionamentos_totais column header
    csv_file = tmp_path / "test_stats.csv"
    path = m.exportar_csv(ficheiro_csv=str(csv_file), config={})

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert 'reposicionamentos_totais' in headers
        assert 'distancia_reposicionamento_total' in headers

    # também deve incluir o nome da política de reposicionamento quando fornecido
    path2 = m.exportar_csv(ficheiro_csv=str(csv_file), config={'reposicionamento_policy': 'MinhaPol'})
    with open(path2, newline='', encoding='utf-8') as f2:
        headers2 = csv.DictReader(f2).fieldnames
        assert 'reposicionamento_policy' in headers2
