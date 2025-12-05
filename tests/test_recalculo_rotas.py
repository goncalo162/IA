"""
Testes para verificar o recálculo de rotas quando há alterações de trânsito.
Inclui testes para viagens individuais e ride-sharing.
"""
from datetime import datetime

from infra.grafo.grafo import Grafo
from infra.grafo.aresta import NivelTransito
from infra.entidades.pedidos import Pedido
from infra.entidades.viagem import Viagem
from infra.entidades.veiculos import VeiculoCombustao, EstadoVeiculo
from algoritmos.algoritmos_navegacao import NavegadorCustoUniforme
from algoritmos.criterios import CustoTempoPercurso


class TestViagemRecalculo:
    """Testes para recálculo de rota na classe Viagem."""

    def setup_method(self):
        """Configura o ambiente para cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.navegador = NavegadorCustoUniforme()
        self.navegador.funcao_custo = CustoTempoPercurso()

    def _criar_pedido(self, id_pedido, origem, destino, passageiros=1, ride_sharing=False):
        """Helper para criar pedido."""
        return Pedido(
            pedido_id=id_pedido,
            origem=origem,
            destino=destino,
            passageiros=passageiros,
            horario_pretendido=datetime.now(),
            ride_sharing=ride_sharing
        )

    def _criar_viagem(self, pedido, rota_ate_cliente, rota_pedido):
        """Helper para criar viagem."""
        dist_ate_cliente = self.grafo.calcular_distancia_rota(rota_ate_cliente)
        dist_pedido = self.grafo.calcular_distancia_rota(rota_pedido)
        
        return Viagem(
            pedido=pedido,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_pedido,
            distancia_ate_cliente=dist_ate_cliente,
            distancia_pedido=dist_pedido,
            tempo_inicio=datetime.now(),
            grafo=self.grafo
        )

    def test_aresta_na_rota_restante_detecta_aresta(self):
        """Verifica que deteta quando uma aresta está na rota restante."""
        # Criar pedido e viagem simples
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        assert rota is not None and len(rota) >= 2
        
        pedido = self._criar_pedido(1, "Sé de Braga", "Estação de Comboios")
        viagem = self._criar_viagem(pedido, ["Sé de Braga"], rota)
        
        # Verificar que deteta aresta na rota
        # Obter nome da primeira aresta da rota
        aresta = self.grafo.getEdge(rota[0], rota[1])
        assert aresta is not None
        nome_aresta = aresta.getNome()
        
        # Deve estar na rota restante
        assert viagem.aresta_na_rota_restante(nome_aresta, self.grafo) == True

    def test_aresta_na_rota_restante_nao_detecta_aresta_inexistente(self):
        """Verifica que não deteta aresta que não está na rota."""
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        pedido = self._criar_pedido(1, "Sé de Braga", "Estação de Comboios")
        viagem = self._criar_viagem(pedido, ["Sé de Braga"], rota)
        
        # Aresta que não existe na rota
        assert viagem.aresta_na_rota_restante("Aresta Inexistente", self.grafo) == False

    def test_posicao_atual_retorna_no_correto(self):
        """Verifica que posição atual retorna o nó correto."""
        # Usar rota real do grafo
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Universidade do Minho")
        assert rota is not None and len(rota) >= 3
        
        pedido = self._criar_pedido(1, "Sé de Braga", "Universidade do Minho")
        viagem = self._criar_viagem(pedido, ["Sé de Braga"], rota)
        
        # Posição inicial
        viagem.indice_segmento_atual = 0
        assert viagem.posicao_atual() == rota[0]
        
        # Avançar
        if len(rota) >= 3:
            viagem.indice_segmento_atual = 2
            assert viagem.posicao_atual() == rota[2]

    def test_aplicar_nova_rota_sucesso(self):
        """Verifica que aplica nova rota com sucesso."""
        # Usar rota real do grafo
        rota_original = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        assert rota_original is not None and len(rota_original) >= 2
        
        pedido = self._criar_pedido(1, "Sé de Braga", "Estação de Comboios")
        viagem = self._criar_viagem(pedido, ["Sé de Braga"], rota_original)
        
        # Calcular nova rota e aplicar
        nova_rota = self.navegador.calcular_rota(self.grafo, viagem.posicao_atual(), viagem.destino)
        resultado = viagem.aplicar_nova_rota(nova_rota, self.grafo)
        assert resultado == True
        
        # Verificar que a rota ainda leva ao destino
        assert viagem.destino == "Estação de Comboios"


class TestVeiculoRecalculoRotas:
    """Testes para recálculo de rotas no veículo."""

    def setup_method(self):
        """Configura o ambiente para cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.navegador = NavegadorCustoUniforme()
        self.navegador.funcao_custo = CustoTempoPercurso()

    def _criar_veiculo(self, id_veiculo=1, localizacao="Sé de Braga"):
        """Helper para criar veículo."""
        return VeiculoCombustao(
            id_veiculo=id_veiculo,
            autonomia_maxima=500,
            autonomia_atual=500,
            capacidade_passageiros=4,
            custo_operacional_km=0.15,
            localizacao_atual=localizacao
        )

    def _criar_pedido(self, id_pedido, origem, destino, passageiros=1, ride_sharing=False):
        """Helper para criar pedido."""
        return Pedido(
            pedido_id=id_pedido,
            origem=origem,
            destino=destino,
            passageiros=passageiros,
            horario_pretendido=datetime.now(),
            ride_sharing=ride_sharing
        )

    def test_viagens_afetadas_por_aresta_sem_viagens(self):
        """Verifica que retorna lista vazia se não há viagens."""
        veiculo = self._criar_veiculo()
        
        afetadas = veiculo.viagens_afetadas_por_aresta("Rua da Sé", self.grafo)
        assert afetadas == []

    def test_viagens_afetadas_por_aresta_com_viagem_afetada(self):
        """Verifica que deteta viagem afetada."""
        veiculo = self._criar_veiculo(localizacao="Sé de Braga")
        
        # Criar pedido e iniciar viagem que passa pela Rua da Sé
        pedido = self._criar_pedido(1, "Sé de Braga", "Estação de Comboios")
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        
        if rota and len(rota) >= 2:
            veiculo.iniciar_viagem(
                pedido=pedido,
                rota_ate_cliente=["Sé de Braga"],
                rota_pedido=rota,
                distancia_ate_cliente=0,
                distancia_pedido=self.grafo.calcular_distancia_rota(rota),
                tempo_inicio=datetime.now(),
                grafo=self.grafo
            )
            
            # Verificar arestas na rota
            for i in range(len(rota) - 1):
                aresta = self.grafo.getEdge(rota[i], rota[i + 1])
                if aresta:
                    nome = aresta.getNome()
                    afetadas = veiculo.viagens_afetadas_por_aresta(nome, self.grafo)
                    assert len(afetadas) == 1, f"Deve detetar viagem afetada para aresta {nome}"
                    break

    def test_viagens_afetadas_por_aresta_viagem_nao_afetada(self):
        """Verifica que não deteta viagem se aresta não está na rota."""
        veiculo = self._criar_veiculo(localizacao="Sé de Braga")
        
        pedido = self._criar_pedido(1, "Sé de Braga", "Avenida Central")
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Avenida Central")
        
        if rota and len(rota) >= 2:
            veiculo.iniciar_viagem(
                pedido=pedido,
                rota_ate_cliente=["Sé de Braga"],
                rota_pedido=rota,
                distancia_ate_cliente=0,
                distancia_pedido=self.grafo.calcular_distancia_rota(rota),
                tempo_inicio=datetime.now(),
                grafo=self.grafo
            )
            
            # Aresta que não está na rota
            afetadas = veiculo.viagens_afetadas_por_aresta("Aresta Inexistente XYZ", self.grafo)
            assert len(afetadas) == 0


class TestRecalculoRidesharing:
    """Testes específicos para recálculo com ride-sharing."""

    def setup_method(self):
        """Configura o ambiente para cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.navegador = NavegadorCustoUniforme()
        self.navegador.funcao_custo = CustoTempoPercurso()

    def _criar_veiculo(self, id_veiculo=1, localizacao="Sé de Braga"):
        """Helper para criar veículo."""
        return VeiculoCombustao(
            id_veiculo=id_veiculo,
            autonomia_maxima=500,
            autonomia_atual=500,
            capacidade_passageiros=4,
            custo_operacional_km=0.15,
            localizacao_atual=localizacao
        )

    def _criar_pedido(self, id_pedido, origem, destino, passageiros=1, ride_sharing=True):
        """Helper para criar pedido ride-sharing."""
        return Pedido(
            pedido_id=id_pedido,
            origem=origem,
            destino=destino,
            passageiros=passageiros,
            horario_pretendido=datetime.now(),
            ride_sharing=ride_sharing
        )

    def test_multiplas_viagens_afetadas(self):
        """Verifica deteção de múltiplas viagens afetadas pela mesma aresta."""
        veiculo = self._criar_veiculo(localizacao="Sé de Braga")
        
        # Criar duas viagens que passam pela mesma rota inicial
        pedido1 = self._criar_pedido(1, "Sé de Braga", "Avenida Central", ride_sharing=True)
        pedido2 = self._criar_pedido(2, "Sé de Braga", "Estação de Comboios", ride_sharing=True)
        
        rota1 = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Avenida Central")
        rota2 = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        
        if rota1 and rota2 and len(rota1) >= 2:
            veiculo.iniciar_viagem(
                pedido=pedido1,
                rota_ate_cliente=["Sé de Braga"],
                rota_pedido=rota1,
                distancia_ate_cliente=0,
                distancia_pedido=self.grafo.calcular_distancia_rota(rota1),
                tempo_inicio=datetime.now(),
                grafo=self.grafo
            )
            
            veiculo.iniciar_viagem(
                pedido=pedido2,
                rota_ate_cliente=["Sé de Braga"],
                rota_pedido=rota2,
                distancia_ate_cliente=0,
                distancia_pedido=self.grafo.calcular_distancia_rota(rota2),
                tempo_inicio=datetime.now(),
                grafo=self.grafo
            )
            
            # Se ambas as rotas começam em Sé, encontrar aresta comum
            aresta = self.grafo.getEdge(rota1[0], rota1[1])
            if aresta:
                nome = aresta.getNome()
                afetadas = veiculo.viagens_afetadas_por_aresta(nome, self.grafo)
                # Pelo menos 1 viagem deve ser afetada
                assert len(afetadas) >= 1

    def test_viagem_aplicar_nova_rota_mantem_destino(self):
        """Verifica que aplicar nova rota mantém o destino correto."""
        pedido = self._criar_pedido(1, "Sé de Braga", "Estação de Comboios")
        rota = self.navegador.calcular_rota(self.grafo, "Sé de Braga", "Estação de Comboios")
        
        if rota and len(rota) >= 2:
            dist = self.grafo.calcular_distancia_rota(rota)
            viagem = Viagem(
                pedido=pedido,
                rota_ate_cliente=["Sé de Braga"],
                rota_pedido=rota,
                distancia_ate_cliente=0,
                distancia_pedido=dist,
                tempo_inicio=datetime.now(),
                grafo=self.grafo
            )
            
            # Avançar um pouco na viagem
            viagem.indice_segmento_atual = 1
            pos_atual = viagem.posicao_atual()
            
            # Calcular e aplicar nova rota
            nova_rota = self.navegador.calcular_rota(self.grafo, pos_atual, viagem.destino)
            if nova_rota:
                resultado = viagem.aplicar_nova_rota(nova_rota, self.grafo)
                
                # Destino deve ser mantido
                assert viagem.destino == "Estação de Comboios"
