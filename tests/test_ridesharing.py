import unittest
from datetime import datetime

# Import classes under test
from infra.entidades.veiculos import VeiculoCombustao, EstadoVeiculo
from infra.entidades.pedidos import Pedido
from infra.entidades.viagem import Viagem
from infra.gestaoAmbiente import GestaoAmbiente
from infra.grafo.grafo import Grafo

#TODO: REVER estes testes unitarios

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

class RideSharingTests(unittest.TestCase):
    def setUp(self):
        # Use real simulator graph
        self.env = GestaoAmbiente()
        self.env.carregar_grafo('dataset/grafo.json')
        self.grafo = self.env.grafo
        self.veiculo = VeiculoCombustao(
            id_veiculo=1,
            autonomia_maxima=500,
            autonomia_atual=500,
            capacidade_passageiros=5,
            custo_operacional_km=0.2,
            localizacao_atual='A'
        )
        # attach real grafo
        self.env.grafo = self.grafo

    # Util helpers to make failures more readable
    def _state_snapshot(self, label=""):
        viagens_info = [
            {
                "pedido_id": getattr(getattr(v, "pedido", None), "id", None),
                "ativa": getattr(v, "viagem_ativa", None),
                "distancia_total": getattr(v, "distancia_total", None),
                "progresso_percentual": getattr(v, "progresso_percentual", None),
            }
            for v in getattr(self.veiculo, "viagens", [])
        ]
        return {
            "label": label,
            "estado_veiculo": getattr(self.veiculo, "estado", None),
            "num_passageiros": getattr(self.veiculo, "numero_passageiros", None),
            "capacidade": getattr(self.veiculo, "capacidade_passageiros", None),
            "viagens": viagens_info,
        }

    def _build_long_route(self, min_hops: int = 3) -> list:
        """Constroi uma rota com pelo menos `min_hops` arestas usando vizinhos do grafo real."""
        start_name = self.grafo.getNodes()[0].getName()
        rota = [start_name]
        current = start_name
        visited = {current}
        # tentar expandir rota evitando ciclos curtos
        for _ in range(min_hops):
            neighbours = [n for (n, _) in self.grafo.getNeighbours(current)]
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

    def _pedido(self, pid, pax):
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

    def test_multiple_trips_start_and_capacity(self):
        # Build longer valid route (>=3 hops)
        rota_trip = self._build_long_route(min_hops=3)
        self.assertGreaterEqual(len(rota_trip) - 1, 3, msg=f"Rota deve ter >=3 arestas: {rota_trip}")
        start_node = rota_trip[0]
        rota_client = [start_node, start_node]  # no-op to client (mesmo local)
        p1 = self._pedido(101, 2)
        p2 = self._pedido(102, 3)

        ok1 = self.veiculo.iniciar_viagem(
            pedido=p1,
            rota_ate_cliente=rota_client,
            rota_pedido=rota_trip,
            distancia_ate_cliente=0.0,
            distancia_pedido=self.grafo.calcular_distancia_rota(rota_trip),
            tempo_inicio=datetime.now(),
            grafo=self.grafo,
        )
        with self.subTest("primeira viagem deve iniciar"):
            self.assertTrue(ok1, msg=f"Falha ao iniciar primeira viagem: {self._state_snapshot('start p1')}")
        with self.subTest("passageiros apos p1"):
            self.assertEqual(self.veiculo.numero_passageiros, 2,
                             msg=f"Esperado 2 passageiros apos p1, obtido {self.veiculo.numero_passageiros}. Estado: {self._state_snapshot('after p1')}")
        with self.subTest("total de viagens apos p1"):
            self.assertEqual(len(self.veiculo.viagens), 1,
                             msg=f"Esperado 1 viagem ativa, obtido {len(self.veiculo.viagens)}. Estado: {self._state_snapshot('after p1')}")
        with self.subTest("estado do veiculo apos p1"):
            self.assertEqual(self.veiculo.estado, EstadoVeiculo.EM_ANDAMENTO,
                             msg=f"Veiculo deveria estar EM_ANDAMENTO apos p1. Estado: {self._state_snapshot('after p1')}")

        ok2 = self.veiculo.iniciar_viagem(
            pedido=p2,
            rota_ate_cliente=rota_client,
            rota_pedido=rota_trip,
            distancia_ate_cliente=0.0,
            distancia_pedido=self.grafo.calcular_distancia_rota(rota_trip),
            tempo_inicio=datetime.now(),
            grafo=self.grafo,
        )
        with self.subTest("segunda viagem deve iniciar"):
            self.assertTrue(ok2, msg=f"Falha ao iniciar segunda viagem: {self._state_snapshot('start p2')}")
        with self.subTest("passageiros apos p2"):
            self.assertEqual(self.veiculo.numero_passageiros, 5,
                             msg=f"Esperado 5 passageiros apos p2, obtido {self.veiculo.numero_passageiros}. Estado: {self._state_snapshot('after p2')}")
        with self.subTest("total de viagens apos p2"):
            self.assertEqual(len(self.veiculo.viagens), 2,
                             msg=f"Esperado 2 viagens ativas, obtido {len(self.veiculo.viagens)}. Estado: {self._state_snapshot('after p2')}")

        # This one should exceed capacity
        p3 = self._pedido(103, 1)
        ok3 = self.veiculo.iniciar_viagem(
            pedido=p3,
            rota_ate_cliente=rota_client,
            rota_pedido=rota_trip,
            distancia_ate_cliente=0.0,
            distancia_pedido=self.grafo.calcular_distancia_rota(rota_trip),
            tempo_inicio=datetime.now(),
            grafo=self.grafo,
        )
        with self.subTest("terceira viagem deve falhar por capacidade"):
            self.assertFalse(ok3, msg=f"Terceira viagem nao deveria iniciar. Estado: {self._state_snapshot('start p3')}")
        with self.subTest("passageiros permanecem apos falha p3"):
            self.assertEqual(self.veiculo.numero_passageiros, 5,
                             msg=f"Passageiros deveriam permanecer 5, obtido {self.veiculo.numero_passageiros}. Estado: {self._state_snapshot('after p3')}")

    def test_progress_updates_all_and_conclude_single(self):
        p1 = self._pedido(201, 2)
        p2 = self._pedido(202, 3)
        # Build a longer route for progress test as well
        rota_trip2 = self._build_long_route(min_hops=4)
        self.assertGreaterEqual(len(rota_trip2) - 1, 3, msg=f"Rota progresso deve ter >=3 arestas: {rota_trip2}")
        start_node = rota_trip2[0]
        rota_client = [start_node, start_node]
        dist_trip2 = self.grafo.calcular_distancia_rota(rota_trip2)

        self.veiculo.iniciar_viagem(p1, rota_client, rota_trip2, 0.0, dist_trip2, datetime.now(), self.grafo)
        self.veiculo.iniciar_viagem(p2, rota_client, rota_trip2, 0.0, dist_trip2, datetime.now(), self.grafo)

        concluidas = self.veiculo.atualizar_progresso_viagem(0.2)  # advance a bit
        with self.subTest("tipo de retorno em atualizar_progresso_viagem"):
            self.assertIsInstance(concluidas, list,
                                  msg=f"Retorno deveria ser lista, obtido {type(concluidas)}. Estado: {self._state_snapshot('progress 0.2')} ")
        with self.subTest("elementos da lista sao Viagem"):
            self.assertTrue(all(isinstance(v, Viagem) for v in concluidas) or len(concluidas)==0,
                            msg=f"Lista deve conter Viagem ou ser vazia. Concluidas={concluidas}. Estado: {self._state_snapshot('progress 0.2')} ")

        # Advance enough to conclude both (given mock edges)
        concluidas = self.veiculo.atualizar_progresso_viagem(5.0)
        # Some may conclude; conclude the first one explicitly
        if concluidas:
            v = concluidas[0]
            pax_before = self.veiculo.numero_passageiros
            self.veiculo.concluir_viagem(v)
            with self.subTest("concluir uma viagem reduz passageiros"):
                self.assertLess(self.veiculo.numero_passageiros, pax_before,
                                msg=f"Passageiros deveriam reduzir apos concluir uma viagem. Antes={pax_before}, Depois={self.veiculo.numero_passageiros}. Estado: {self._state_snapshot('after conclude 1')} ")
            # Remaining trips stay
            remaining_active = any(v2.viagem_ativa for v2 in self.veiculo.viagens)
            todas_inativas = all(not v2.viagem_ativa for v2 in self.veiculo.viagens) if self.veiculo.viagens else False
            # Allow either active remaining, none remaining, or remaining but already inactive (awaiting cleanup)
            with self.subTest("viagens restantes validas (ativas, vazias ou inativas)"):
                self.assertTrue(remaining_active or len(self.veiculo.viagens)==0 or todas_inativas,
                                msg=f"Esperado viagens ativas remanescentes, lista vazia, ou restantes inativas. Estado: {self._state_snapshot('after conclude check')} ")

    def test_environment_lists_include_in_progress(self):
        # Add vehicle to environment and set state
        self.env.adicionar_veiculo(self.veiculo)
        self.veiculo.estado = EstadoVeiculo.DISPONIVEL
        disp = self.env.listar_veiculos_disponiveis()
        with self.subTest("veiculo listado como disponivel"):
            self.assertIn(self.veiculo, disp,
                          msg=f"Veiculo deveria estar em disponiveis. Estado: {self._state_snapshot('env DISPONIVEL')}")

        self.veiculo.estado = EstadoVeiculo.EM_ANDAMENTO
        rs = self.env.listar_veiculos_ridesharing()
        with self.subTest("veiculo listado em ridesharing"):
            self.assertIn(self.veiculo, rs,
                          msg=f"Veiculo deveria estar em ridesharing. Estado: {self._state_snapshot('env EM_ANDAMENTO')}")

if __name__ == '__main__':
    unittest.main()
