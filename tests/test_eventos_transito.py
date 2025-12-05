"""
Testes para verificar que os eventos de alteração de trânsito
são executados corretamente e restauram o nível original após a duração.
"""
import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta

from infra.grafo.grafo import Grafo
from infra.grafo.aresta import NivelTransito
from infra.evento import GestorEventos, TipoEvento


class TestAlteracaoTransitoGrafo:
    """Testes para o método alterarTransitoAresta do Grafo."""

    def setup_method(self):
        """Carrega o grafo antes de cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')

    def test_alterar_transito_aresta_existente(self):
        """Verifica que consegue alterar o trânsito de uma aresta existente."""
        # Aresta "Rua da Sé" existe no grafo
        aresta = self.grafo.getEdgeByName("Rua da Sé")
        assert aresta is not None, "Aresta 'Rua da Sé' deve existir"
        
        nivel_original = aresta.getTransito()
        
        # Alterar para MUITO_ELEVADO
        resultado = self.grafo.alterarTransitoAresta("Rua da Sé", NivelTransito.MUITO_ELEVADO)
        assert resultado == True, "Deve retornar True ao alterar aresta existente"
        assert aresta.getTransito() == NivelTransito.MUITO_ELEVADO
        
        # Restaurar para NORMAL
        resultado = self.grafo.alterarTransitoAresta("Rua da Sé", NivelTransito.NORMAL)
        assert resultado == True
        assert aresta.getTransito() == NivelTransito.NORMAL

    def test_alterar_transito_aresta_inexistente(self):
        """Verifica que retorna False para aresta inexistente."""
        resultado = self.grafo.alterarTransitoAresta("Aresta Que Nao Existe", NivelTransito.ELEVADO)
        assert resultado == False, "Deve retornar False para aresta inexistente"

    def test_alterar_transito_acidente(self):
        """Verifica que consegue definir ACIDENTE e que afeta o tempo de percurso."""
        aresta = self.grafo.getEdgeByName("Rua da Sé")
        assert aresta is not None
        
        # Tempo normal
        tempo_normal = aresta.getTempoPercorrer()
        assert tempo_normal is not None and tempo_normal > 0
        
        # Definir acidente
        self.grafo.alterarTransitoAresta("Rua da Sé", NivelTransito.ACIDENTE)
        tempo_acidente = aresta.getTempoPercorrer()
        assert tempo_acidente is None, "Com ACIDENTE, tempo de percorrer deve ser None"
        
        # Restaurar
        self.grafo.alterarTransitoAresta("Rua da Sé", NivelTransito.NORMAL)
        tempo_restaurado = aresta.getTempoPercorrer()
        assert tempo_restaurado == tempo_normal


class TestCarregarEventosTransito:
    """Testes para carregar eventos de trânsito do JSON."""

    def setup_method(self):
        """Cria gestor de eventos antes de cada teste."""
        self.gestor = GestorEventos()

    def test_carregar_eventos_ficheiro_valido(self):
        """Verifica que carrega eventos do ficheiro JSON corretamente."""
        num_eventos = self.gestor.carregar_eventos_transito('dataset/eventos_transito.json')
        assert num_eventos > 0, "Deve carregar pelo menos um evento"
        assert self.gestor.contar_eventos_transito() == num_eventos

    def test_carregar_eventos_ficheiro_inexistente(self):
        """Verifica que retorna 0 para ficheiro inexistente."""
        num_eventos = self.gestor.carregar_eventos_transito('ficheiro_que_nao_existe.json')
        assert num_eventos == 0

    def test_carregar_eventos_json_invalido(self):
        """Verifica que retorna 0 para JSON inválido."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("isto não é json válido {{{")
            temp_path = f.name
        
        try:
            num_eventos = self.gestor.carregar_eventos_transito(temp_path)
            assert num_eventos == 0
        finally:
            os.unlink(temp_path)

    def test_eventos_carregados_tem_dados_corretos(self):
        """Verifica que os eventos carregados têm os dados esperados."""
        self.gestor.carregar_eventos_transito('dataset/eventos_transito.json')
        
        eventos_transito = [e for e in self.gestor.eventos if e.tipo == TipoEvento.ALTERACAO_TRANSITO]
        assert len(eventos_transito) > 0
        
        for evento in eventos_transito:
            assert 'aresta' in evento.dados_extra
            assert 'nivel' in evento.dados_extra
            assert 'minuto_simulacao' in evento.dados_extra


class TestAgendarEventosTransito:
    """Testes para agendar e executar eventos de trânsito."""

    def setup_method(self):
        """Prepara grafo e gestor antes de cada teste."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.gestor = GestorEventos()
        self.tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
        
        # Callback para alterar trânsito
        def alterar_transito(aresta: str, nivel: str) -> bool:
            try:
                nivel_enum = NivelTransito[nivel]
                return self.grafo.alterarTransitoAresta(aresta, nivel_enum)
            except KeyError:
                return False
        
        self.callback_alterar = alterar_transito

    def test_agendar_eventos_transito(self):
        """Verifica que os eventos são agendados corretamente."""
        self.gestor.carregar_eventos_transito('dataset/eventos_transito.json')
        num_agendados = self.gestor.agendar_eventos_transito(
            self.tempo_inicial, 
            self.callback_alterar
        )
        
        assert num_agendados > 0, "Deve agendar pelo menos um evento"
        assert self.gestor.fila_temporal.tem_eventos()

    def test_executar_evento_altera_transito(self):
        """Verifica que executar um evento altera o trânsito da aresta."""
        # Criar JSON temporário com evento simples
        eventos_json = {
            "eventos": [
                {
                    "minuto_simulacao": 5,
                    "aresta": "Rua da Sé",
                    "nivel": "MUITO_ELEVADO",
                    "duracao_minutos": None,
                    "descricao": "Teste"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(eventos_json, f)
            temp_path = f.name
        
        try:
            # Verificar nível inicial
            aresta = self.grafo.getEdgeByName("Rua da Sé")
            nivel_inicial = aresta.getTransito()
            
            # Carregar e agendar
            self.gestor.carregar_eventos_transito(temp_path)
            self.gestor.agendar_eventos_transito(self.tempo_inicial, self.callback_alterar)
            
            # Avançar tempo e processar
            tempo_apos_evento = self.tempo_inicial + timedelta(minutes=10)
            self.gestor.processar_eventos_ate(tempo_apos_evento)
            
            # Verificar que o trânsito mudou
            assert aresta.getTransito() == NivelTransito.MUITO_ELEVADO
        finally:
            os.unlink(temp_path)

    def test_evento_com_duracao_restaura_transito(self):
        """Verifica que evento com duração restaura o trânsito para NORMAL."""
        # Criar JSON com evento que tem duração
        eventos_json = {
            "eventos": [
                {
                    "minuto_simulacao": 5,
                    "aresta": "Rua da Sé",
                    "nivel": "MUITO_ELEVADO",
                    "duracao_minutos": 10,
                    "descricao": "Teste com duração"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(eventos_json, f)
            temp_path = f.name
        
        try:
            aresta = self.grafo.getEdgeByName("Rua da Sé")
            
            # Carregar e agendar
            self.gestor.carregar_eventos_transito(temp_path)
            self.gestor.agendar_eventos_transito(self.tempo_inicial, self.callback_alterar)
            
            # Avançar para depois do evento inicial (minuto 5)
            tempo_durante = self.tempo_inicial + timedelta(minutes=7)
            self.gestor.processar_eventos_ate(tempo_durante)
            assert aresta.getTransito() == NivelTransito.MUITO_ELEVADO, "Deve estar MUITO_ELEVADO após evento"
            
            # Avançar para depois da restauração (minuto 5 + 10 = 15)
            tempo_apos_restauracao = self.tempo_inicial + timedelta(minutes=20)
            self.gestor.processar_eventos_ate(tempo_apos_restauracao)
            assert aresta.getTransito() == NivelTransito.NORMAL, "Deve voltar a NORMAL após duração"
        finally:
            os.unlink(temp_path)

    def test_multiplos_eventos_sequenciais(self):
        """Verifica que múltiplos eventos são processados na ordem correta."""
        eventos_json = {
            "eventos": [
                {
                    "minuto_simulacao": 5,
                    "aresta": "Rua da Sé",
                    "nivel": "ELEVADO",
                    "duracao_minutos": 5,
                    "descricao": "Primeiro evento"
                },
                {
                    "minuto_simulacao": 15,
                    "aresta": "Rua da Sé",
                    "nivel": "ACIDENTE",
                    "duracao_minutos": 10,
                    "descricao": "Segundo evento"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(eventos_json, f)
            temp_path = f.name
        
        try:
            aresta = self.grafo.getEdgeByName("Rua da Sé")
            
            self.gestor.carregar_eventos_transito(temp_path)
            self.gestor.agendar_eventos_transito(self.tempo_inicial, self.callback_alterar)
            
            # Minuto 7: deve estar ELEVADO
            self.gestor.processar_eventos_ate(self.tempo_inicial + timedelta(minutes=7))
            assert aresta.getTransito() == NivelTransito.ELEVADO
            
            # Minuto 12: deve estar NORMAL (após restauração do primeiro)
            self.gestor.processar_eventos_ate(self.tempo_inicial + timedelta(minutes=12))
            assert aresta.getTransito() == NivelTransito.NORMAL
            
            # Minuto 17: deve estar ACIDENTE
            self.gestor.processar_eventos_ate(self.tempo_inicial + timedelta(minutes=17))
            assert aresta.getTransito() == NivelTransito.ACIDENTE
            
            # Minuto 30: deve estar NORMAL (após restauração do segundo)
            self.gestor.processar_eventos_ate(self.tempo_inicial + timedelta(minutes=30))
            assert aresta.getTransito() == NivelTransito.NORMAL
        finally:
            os.unlink(temp_path)


class TestEventosTransitoComGrafoReal:
    """Testes de integração com o ficheiro de eventos real."""

    def setup_method(self):
        """Prepara ambiente completo."""
        self.grafo = Grafo.from_json_file('dataset/grafo.json')
        self.gestor = GestorEventos()
        self.tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
        
        def alterar_transito(aresta: str, nivel: str) -> bool:
            try:
                nivel_enum = NivelTransito[nivel]
                return self.grafo.alterarTransitoAresta(aresta, nivel_enum)
            except KeyError:
                return False
        
        self.callback_alterar = alterar_transito

    def test_eventos_reais_sao_executados(self):
        """Verifica que os eventos do ficheiro real são executados sem erros."""
        self.gestor.carregar_eventos_transito('dataset/eventos_transito.json')
        self.gestor.agendar_eventos_transito(self.tempo_inicial, self.callback_alterar)
        
        # Processar todos os eventos (simular 4 horas)
        tempo_final = self.tempo_inicial + timedelta(hours=4)
        eventos_processados = self.gestor.processar_eventos_ate(tempo_final)
        
        assert len(eventos_processados) > 0, "Deve processar pelo menos um evento"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
