"""
Testes para verificar que o sistema recalcula rotas quando há acidentes
e que os veículos não ficam presos.
"""
import pytest
from infra.grafo.grafo import Grafo
from infra.grafo.aresta import NivelTransito
from algoritmos.algoritmos_navegacao import NavegadorAEstrela
from algoritmos.funcoes_custo import CustoTempoPercurso
from algoritmos.heuristicas import HeuristicaEuclidiana


class TestAcidentesRecalculoRotas:
    """Testes para garantir que acidentes não prendem veículos."""

    def setup_method(self):
        """Configura ambiente de teste antes de cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.navegador = NavegadorAEstrela(
            funcao_custo=CustoTempoPercurso(),
            heuristica=HeuristicaEuclidiana()
        )

    def test_rota_bloqueada_retorna_infinito(self):
        """Verifica que uma rota com acidente retorna tempo infinito."""
        # Calcular rota normal
        rota = ['Avenida Central', 'Braga Parque', 'Universidade do Minho']
        tempo_normal = self.grafo.calcular_tempo_rota(rota)
        
        assert tempo_normal > 0 and tempo_normal < float('inf'), \
            "Rota normal deve ter tempo finito"
        
        # Aplicar acidente
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ACIDENTE)
        
        # Verificar que rota retorna infinito
        tempo_bloqueado = self.grafo.calcular_tempo_rota(rota)
        assert tempo_bloqueado == float('inf'), \
            "Rota com acidente deve retornar tempo infinito"

    def test_get_arc_cost_acidente_retorna_infinito(self):
        """Verifica que get_arc_cost retorna infinito para aresta com acidente."""
        # Custo normal
        custo_normal = self.grafo.get_arc_cost('Avenida Central', 'Braga Parque')
        assert custo_normal > 0 and custo_normal < float('inf'), \
            "Custo normal deve ser finito"
        
        # Aplicar acidente
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ACIDENTE)
        
        # Custo com acidente
        custo_acidente = self.grafo.get_arc_cost('Avenida Central', 'Braga Parque')
        assert custo_acidente == float('inf'), \
            "Custo de aresta com acidente deve ser infinito"

    def test_navegador_encontra_rota_alternativa(self):
        """Verifica que o navegador encontra rota alternativa quando há acidente."""
        origem = 'Avenida Central'
        destino = 'Universidade do Minho'
        
        # Rota normal
        rota_normal = self.navegador.calcular_rota(self.grafo, origem, destino)
        assert rota_normal is not None, "Deve encontrar rota normal"
        assert 'Braga Parque' in rota_normal, "Rota normal deve passar por Braga Parque"
        
        # Aplicar acidente na aresta principal
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ACIDENTE)
        
        # Calcular rota alternativa
        rota_alternativa = self.navegador.calcular_rota(self.grafo, origem, destino)
        assert rota_alternativa is not None, "Deve encontrar rota alternativa"
        
        # Verificar que a rota alternativa é válida
        tempo = self.grafo.calcular_tempo_rota(rota_alternativa)
        assert tempo < float('inf'), "Rota alternativa deve ter tempo finito"
        
        # Verificar que chegou ao destino
        assert rota_alternativa[-1] == destino, "Rota deve chegar ao destino"

    def test_rota_alternativa_evita_acidente(self):
        """Verifica que a rota alternativa não passa pela aresta com acidente."""
        origem = 'Avenida Central'
        destino = 'Universidade do Minho'
        aresta_acidente = 'Av. da Liberdade'
        
        # Aplicar acidente
        self.grafo.alterarTransitoAresta(aresta_acidente, NivelTransito.ACIDENTE)
        
        # Calcular rota
        rota = self.navegador.calcular_rota(self.grafo, origem, destino)
        assert rota is not None, "Deve encontrar rota"
        
        # Verificar que não passa pela aresta bloqueada
        passa_por_acidente = False
        for i in range(len(rota) - 1):
            aresta = self.grafo.getEdge(rota[i], rota[i + 1])
            if aresta and aresta.getNome() == aresta_acidente:
                passa_por_acidente = True
                break
        
        assert not passa_por_acidente, \
            "Rota alternativa não deve passar pela aresta com acidente"

    def test_multiplos_acidentes_simultaneos(self):
        """Verifica comportamento com múltiplos acidentes simultâneos."""
        origem = 'Avenida Central'
        destino = 'Universidade do Minho'
        
        # Aplicar múltiplos acidentes
        acidentes = ['Av. da Liberdade', 'Av. João XXI']
        for aresta in acidentes:
            self.grafo.alterarTransitoAresta(aresta, NivelTransito.ACIDENTE)
        
        # Tentar calcular rota
        rota = self.navegador.calcular_rota(self.grafo, origem, destino)
        
        # Se encontrou rota, deve ser válida
        if rota:
            tempo = self.grafo.calcular_tempo_rota(rota)
            # Pode ser infinito se não há caminho alternativo, ou finito se há
            assert tempo >= 0, "Tempo deve ser não-negativo ou infinito"
            
            if tempo < float('inf'):
                # Se tem tempo finito, verificar que evita os acidentes
                for i in range(len(rota) - 1):
                    aresta = self.grafo.getEdge(rota[i], rota[i + 1])
                    if aresta:
                        assert aresta.getNome() not in acidentes, \
                            "Rota não deve passar por arestas com acidente"

    def test_acidente_removido_restaura_rota_direta(self):
        """Verifica que quando acidente é removido, rota direta volta a estar disponível."""
        origem = 'Avenida Central'
        destino = 'Universidade do Minho'
        
        # Rota inicial
        rota_inicial = self.navegador.calcular_rota(self.grafo, origem, destino)
        
        # Aplicar acidente
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ACIDENTE)
        
        # Rota com acidente (alternativa)
        rota_acidente = self.navegador.calcular_rota(self.grafo, origem, destino)
        tempo_acidente = self.grafo.calcular_tempo_rota(rota_acidente)
        
        # Verificar que encontrou rota alternativa diferente
        assert rota_acidente != rota_inicial or tempo_acidente == float('inf'), \
            "Com acidente, deve usar rota alternativa ou ter tempo infinito"
        
        # Remover acidente (restaurar para o nível original - ELEVADO neste caso)
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ELEVADO)
        
        # Rota após remoção
        rota_final = self.navegador.calcular_rota(self.grafo, origem, destino)
        tempo_final = self.grafo.calcular_tempo_rota(rota_final)
        
        assert rota_final == rota_inicial, \
            "Após remover acidente, rota direta deve voltar a ser escolhida"
        assert tempo_final < float('inf'), \
            "Rota deve ter tempo finito após remover acidente"

    def test_veiculo_nao_fica_preso_sem_rota(self):
        """Verifica que mesmo sem rota possível, sistema não lança exceção."""
        origem = 'Sé de Braga'
        destino = 'Bom Jesus do Monte'
        
        # Bloquear todas as saídas possíveis da Sé de Braga
        arestas_bloquear = ['Rua da Sé', 'Rua Dom Diogo de Sousa', 
                           'Rua do Raio', 'Rua da Ponte', 'Rua do Souto',
                           'Rua Arcebispo']
        
        for aresta in arestas_bloquear:
            self.grafo.alterarTransitoAresta(aresta, NivelTransito.ACIDENTE)
        
        # Tentar calcular rota - não deve lançar exceção
        rota = self.navegador.calcular_rota(self.grafo, origem, destino)
        
        # Pode ser None ou ter tempo infinito, mas não deve crashar
        if rota:
            tempo = self.grafo.calcular_tempo_rota(rota)
            # Se retornou rota, aceitar qualquer valor (inclusive infinito)
            assert tempo >= 0 or tempo == float('inf'), \
                "Sistema deve lidar graciosamente com falta de rotas"

    def test_diferentes_niveis_transito_custos(self):
        """Verifica que diferentes níveis de trânsito têm custos diferentes."""
        origem = 'Avenida Central'
        destino = 'Braga Parque'
        
        # Tempo com trânsito vazio
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.VAZIO)
        custo_vazio = self.grafo.get_arc_cost(origem, destino)
        
        # Tempo com trânsito normal
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.NORMAL)
        custo_normal = self.grafo.get_arc_cost(origem, destino)
        
        # Tempo com trânsito elevado
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ELEVADO)
        custo_elevado = self.grafo.get_arc_cost(origem, destino)
        
        # Tempo com trânsito muito elevado
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.MUITO_ELEVADO)
        custo_muito_elevado = self.grafo.get_arc_cost(origem, destino)
        
        # Tempo com acidente
        self.grafo.alterarTransitoAresta('Av. da Liberdade', NivelTransito.ACIDENTE)
        custo_acidente = self.grafo.get_arc_cost(origem, destino)
        
        # Verificar ordem crescente de custos
        assert custo_vazio < custo_normal < custo_elevado < custo_muito_elevado, \
            "Custos devem aumentar com nível de trânsito"
        assert custo_acidente == float('inf'), \
            "Acidente deve ter custo infinito"
