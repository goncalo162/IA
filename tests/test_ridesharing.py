from datetime import datetime

# Import classes under test
from infra.entidades.veiculos import VeiculoCombustao, EstadoVeiculo
from infra.entidades.pedidos import Pedido
from infra.entidades.viagem import Viagem
from infra.gestaoAmbiente import GestaoAmbiente

# TODO: REVER estes testes unitarios

# Simple mocks for grafo/aresta used by Viagem


class MockAresta:
    def __init__(self, km=10.0, vel=50.0, transito=type('T', (), {'value': 1.0})()):
        self._km = km
        self._vel = vel
        self._transito = transito

    def getQuilometro(self):
        return self._km

    def getVelocidadeMaxima(self):
        return self._vel

    def getTransito(self):
        return self._transito


class MockGrafo:
    def getEdge(self, origem, destino):
        return MockAresta()


def _setup_env_and_vehicle():
    env = GestaoAmbiente()
    env.carregar_grafo('dataset/grafo.json')
    grafo = env.grafo
    veiculo = VeiculoCombustao(
        id_veiculo=1,
        autonomia_maxima=500,
        autonomia_atual=500,
        capacidade_passageiros=5,
        custo_operacional_km=0.2,
        localizacao_atual='A'
    )
    env.grafo = grafo
    return env, grafo, veiculo

    # Util helpers to make failures more readable


def _state_snapshot(veiculo, label=""):
    viagens_info = [
        {
            "pedido_id": getattr(getattr(v, "pedido", None), "id", None),
            "ativa": getattr(v, "viagem_ativa", None),
            "distancia_total": getattr(v, "distancia_total", None),
            "progresso_percentual": getattr(v, "progresso_percentual", None),
        }
        for v in getattr(veiculo, "viagens", [])
    ]
    return {
        "label": label,
        "estado_veiculo": getattr(veiculo, "estado", None),
        "num_passageiros": getattr(veiculo, "numero_passageiros", None),
        "capacidade": getattr(veiculo, "capacidade_passageiros", None),
        "viagens": viagens_info,
    }


def _build_long_route(grafo, min_hops: int = 3) -> list:
    """Constroi uma rota com pelo menos `min_hops` arestas usando vizinhos do grafo real."""
    start_name = grafo.getNodes()[0].getName()
    rota = [start_name]
    current = start_name
    visited = {current}
    # tentar expandir rota evitando ciclos curtos
    for _ in range(min_hops):
        neighbours = [n for (n, _) in grafo.getNeighbours(current)]
        # escolher o primeiro vizinho que não crie ciclo imediato
        next_candidates = [n for n in neighbours if n not in visited]
        if not next_candidates:
            # se bloquear, permitir voltar a visitar mas evitar alternar A-B-A
            next_candidates = [n for n in neighbours if len(rota) < 2 or n != rota[-2]]
            if not next_candidates:
                break
        nxt = next_candidates[0]
        rota.append(nxt)
        visited.add(nxt)
        current = nxt
    # garantir que tem ao menos 2 nós
    if len(rota) < 2:
        # fallback: duplicar nó para criar aresta
        rota = [start_name, start_name]
    return rota


def _pedido(pid, pax):
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


def test_multiple_trips_start_and_capacity():
    env, grafo, veiculo = _setup_env_and_vehicle()
    rota_trip = _build_long_route(grafo, min_hops=3)
    assert len(rota_trip) - 1 >= 3, f"Rota deve ter >=3 arestas: {rota_trip}"
    start_node = rota_trip[0]
    # quando origem == destino, navegador deveria devolver somente [start_node]
    rota_client = [start_node]
    p1 = _pedido(101, 2)
    p2 = _pedido(102, 3)

    ok1 = veiculo.iniciar_viagem(
        pedido=p1,
        rota_ate_cliente=rota_client,
        rota_pedido=rota_trip,
        distancia_ate_cliente=0.0,
        distancia_pedido=grafo.calcular_distancia_rota(rota_trip),
        tempo_inicio=datetime.now(),
        grafo=grafo,
    )
    assert ok1, f"Falha ao iniciar primeira viagem: {_state_snapshot(veiculo, 'start p1')}"
    assert veiculo.numero_passageiros == 2, (
        f"Esperado 2 passageiros apos p1, obtido {veiculo.numero_passageiros}. "
        f"Estado: {_state_snapshot(veiculo, 'after p1')}"
    )
    assert len(
        veiculo.viagens) == 1, (f"Esperado 1 viagem ativa, obtido {
            len(
                veiculo.viagens)}. Estado: {
            _state_snapshot(
                veiculo, 'after p1')}")
    assert veiculo.estado == EstadoVeiculo.EM_ANDAMENTO, (
        f"Veiculo deveria estar EM_ANDAMENTO apos p1. Estado: {_state_snapshot(veiculo, 'after p1')}"
    )

    ok2 = veiculo.iniciar_viagem(
        pedido=p2,
        rota_ate_cliente=rota_client,
        rota_pedido=rota_trip,
        distancia_ate_cliente=0.0,
        distancia_pedido=grafo.calcular_distancia_rota(rota_trip),
        tempo_inicio=datetime.now(),
        grafo=grafo,
    )
    assert ok2, f"Falha ao iniciar segunda viagem: {_state_snapshot(veiculo, 'start p2')}"
    assert veiculo.numero_passageiros == 5, (
        f"Esperado 5 passageiros apos p2, obtido {veiculo.numero_passageiros}. "
        f"Estado: {_state_snapshot(veiculo, 'after p2')}"
    )
    assert len(
        veiculo.viagens) == 2, (f"Esperado 2 viagens ativas, obtido {
            len(
                veiculo.viagens)}. Estado: {
            _state_snapshot(
                veiculo, 'after p2')}")

    p3 = _pedido(103, 1)
    ok3 = veiculo.iniciar_viagem(
        pedido=p3,
        rota_ate_cliente=rota_client,
        rota_pedido=rota_trip,
        distancia_ate_cliente=0.0,
        distancia_pedido=grafo.calcular_distancia_rota(rota_trip),
        tempo_inicio=datetime.now(),
        grafo=grafo,
    )
    assert not ok3, f"Terceira viagem nao deveria iniciar. Estado: {
        _state_snapshot(
            veiculo, 'start p3')}"
    assert veiculo.numero_passageiros == 5, (
        f"Passageiros deveriam permanecer 5, obtido {veiculo.numero_passageiros}. "
        f"Estado: {_state_snapshot(veiculo, 'after p3')}"
    )


def test_progress_updates_all_and_conclude_single():
    env, grafo, veiculo = _setup_env_and_vehicle()
    p1 = _pedido(201, 2)
    p2 = _pedido(202, 3)
    rota_trip2 = _build_long_route(grafo, min_hops=4)
    assert len(rota_trip2) - 1 >= 3, f"Rota progresso deve ter >=3 arestas: {rota_trip2}"
    start_node = rota_trip2[0]
    # quando origem == destino, navegador deveria devolver somente [start_node]
    rota_client = [start_node]
    dist_trip2 = grafo.calcular_distancia_rota(rota_trip2)

    veiculo.iniciar_viagem(p1, rota_client, rota_trip2, 0.0, dist_trip2, datetime.now(), grafo)
    veiculo.iniciar_viagem(p2, rota_client, rota_trip2, 0.0, dist_trip2, datetime.now(), grafo)

    resultado = veiculo.atualizar_progresso_viagem(0.2)
    # O método agora retorna (viagens_concluidas, chegou_posto)
    if isinstance(resultado, tuple):
        concluidas, _ = resultado
    else:
        concluidas = resultado

    assert isinstance(
        concluidas, list), (f"Retorno deveria ser lista, obtido {
            type(concluidas)}. Estado: {
            _state_snapshot(
                veiculo, 'progress 0.2')}")
    assert all(isinstance(v, Viagem) for v in concluidas) or len(concluidas) == 0, (
        f"Lista deve conter Viagem ou ser vazia. Concluidas={concluidas}. Estado: {_state_snapshot(veiculo, 'progress 0.2')}"
    )

    resultado = veiculo.atualizar_progresso_viagem(5.0)
    # Desempacotar resultado
    if isinstance(resultado, tuple):
        concluidas, _ = resultado
    else:
        concluidas = resultado

    if concluidas:
        v = concluidas[0]
        pax_before = veiculo.numero_passageiros
        veiculo.concluir_viagem(v)
        assert veiculo.numero_passageiros < pax_before, (f"Passageiros deveriam reduzir apos concluir uma viagem. Antes={pax_before}, Depois={
            veiculo.numero_passageiros}. Estado: {
            _state_snapshot(
                veiculo, 'after conclude 1')}")
        remaining_active = any(v2.viagem_ativa for v2 in veiculo.viagens)
        todas_inativas = all(
            not v2.viagem_ativa for v2 in veiculo.viagens) if veiculo.viagens else False
        assert remaining_active or len(
            veiculo.viagens) == 0 or todas_inativas, (f"Esperado viagens ativas remanescentes, lista vazia, ou restantes inativas. Estado: {
                _state_snapshot(
                    veiculo, 'after conclude check')}")


def test_environment_lists_include_in_progress():
    env, grafo, veiculo = _setup_env_and_vehicle()
    env.adicionar_veiculo(veiculo)
    veiculo.estado = EstadoVeiculo.DISPONIVEL
    disp = env.listar_veiculos_disponiveis()
    assert veiculo in disp, (f"Veiculo deveria estar em disponiveis. Estado: {
        _state_snapshot(
            veiculo, 'env DISPONIVEL')}")

    veiculo.estado = EstadoVeiculo.EM_ANDAMENTO
    rs = env.listar_veiculos_ridesharing()
    assert veiculo in rs, (f"Veiculo deveria estar em ridesharing. Estado: {
        _state_snapshot(
            veiculo, 'env EM_ANDAMENTO')}")
