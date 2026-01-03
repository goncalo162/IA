"""
Motor principal da simulação.
Coordena ambiente, algoritmos, métricas e display através de gestores modulares.
"""
from infra.policies import (
    RideSharingPolicy, SimplesRideSharingPolicy,
    RecargaPolicy, RecargaAutomaticaPolicy
)
from infra.policies.reposicionamento_policy import (
    ReposicionamentoPolicy, ReposicionamentoNulo, ReposicionamentoEstatistico
)
from infra.gestores import GestorPedidos, GestorViagens, GestorRecargas, GestorRotas
from infra.gestores.gestor_reposicionamento import GestorReposicionamento
from infra.grafo.aresta import NivelTransito
from infra.evento import GestorEventos, TipoEvento
from infra.metricas import Metricas
from infra.gestaoAmbiente import GestaoAmbiente
from typing import Optional, Dict
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from infra.simuladorAleatorio import SimuladorAleatorio
from infra.logger import SimuladorLogger

# Carregar variáveis de ambiente
load_dotenv()


# Constante: velocidade máxima com sincronização em tempo real
VELOCIDADE_MAXIMA_SINCRONIZADA = float(os.getenv('VELOCIDADE_MAXIMA_SINCRONIZADA', 100.0))


class Simulador:
    """
    Classe principal que orquestra toda a simulação.
    Permite trocar algoritmos de alocação, navegação e políticas de forma modular.
    """

    def __init__(self, alocador, navegador, display=None,
                 tempo_inicial: Optional[datetime] = None,
                 frequencia_calculo: float = 10.0,
                 velocidade_simulacao: float = 1.0,
                 ridesharing_policy: Optional[RideSharingPolicy] = None,
                 recarga_policy: Optional[RecargaPolicy] = None,
                 reposicionamento_policy: Optional[ReposicionamentoPolicy] = None):
        """
        Inicializa o simulador com os componentes necessários.

        Args:
            alocador: Algoritmo de alocação de veículos
            navegador: Algoritmo de navegação/roteamento
            display: Interface de visualização (opcional)
            tempo_inicial: Tempo de início da simulação
            frequencia_calculo: Frequência de atualização (Hz)
            velocidade_simulacao: Multiplicador de velocidade
            ridesharing_policy: Política de ride-sharing (padrão: SimplesRideSharingPolicy)
            recarga_policy: Política de recarga (padrão: RecargaAutomaticaPolicy)
            reposicionamento_policy: Política de reposicionamento (padrão: ReposicionamentoNulo)
        """
        self.alocador = alocador
        self.navegador = navegador
        self.display = display
        self.pedidoIdAtual = 0

        self.ambiente = GestaoAmbiente()
        self.metricas = Metricas()
        self.gestor_eventos = GestorEventos()
        self.logger = SimuladorLogger()

        # Carregar configurações do simulador dinâmico do .env
        chance_troca_tempo = float(os.getenv('CHANCE_TROCA_TEMPO', 0.4))
        chance_pedido_aleatorio = float(os.getenv('CHANCE_PEDIDO_ALEATORIO', 0.3))
        self.simuladorAleatorio = SimuladorAleatorio(chance_troca_tempo, chance_pedido_aleatorio)

        self.tempo_simulacao = tempo_inicial or datetime.now()
        self.velocidade_simulacao = velocidade_simulacao
        self.frequencia_calculo = frequencia_calculo
        self.passo_tempo = timedelta(
            seconds=velocidade_simulacao / frequencia_calculo)

        self.em_execucao = False
        self.pedidos_agendados = []

        # Inicializar gestores modulares com políticas configuráveis
        self.gestor_viagens = GestorViagens(
            ambiente=self.ambiente,
            metricas=self.metricas,
            logger=self.logger
        )

        self.gestor_recargas = GestorRecargas(
            ambiente=self.ambiente,
            navegador=self.navegador,
            gestor_eventos=self.gestor_eventos,
            metricas=self.metricas,
            logger=self.logger,
            recarga_policy=recarga_policy or RecargaAutomaticaPolicy()
        )

        self.gestor_pedidos = GestorPedidos(
            ambiente=self.ambiente,
            alocador=self.alocador,
            navegador=self.navegador,
            metricas=self.metricas,
            logger=self.logger,
            ridesharing_policy=ridesharing_policy or SimplesRideSharingPolicy(),
            gestor_recargas=self.gestor_recargas  # Injetar gestor_recargas
        )

        self.gestor_rotas = GestorRotas(
            ambiente=self.ambiente,
            navegador=self.navegador,
            metricas=self.metricas,
            logger=self.logger
        )

        self.gestor_reposicionamento = GestorReposicionamento(
            ambiente=self.ambiente,
            navegador=self.navegador,
            metricas=self.metricas,
            logger=self.logger,
            reposicionamento_policy=reposicionamento_policy or ReposicionamentoNulo()
        )

        # Configurar coordenação entre gestores
        self.gestor_recargas.configurar_callbacks(
            adicionar_viagem_fn=self.gestor_viagens.adicionar_viagem,
            remover_viagem_fn=self.gestor_viagens.remover_viagem
        )
        self.gestor_viagens.configurar_gestor_recargas(self.gestor_recargas)
        self.gestor_reposicionamento.configurar_agendador(self.gestor_viagens.adicionar_viagem)
        self.gestor_pedidos.configurar_display(self.display)

        if self.alocador is not None:
            self.alocador.configurar_gestor_recargas(self.gestor_recargas)

    ##### MÉTODO AUXILIAR DE CARREGAMENTO DE DADOS #####

    def carregar_dados(self, caminho_grafo: str, caminho_veiculos: str,
                       caminho_pedidos: str, caminho_eventos_transito: str = None):
        """Carrega todos os dados necessários para a simulação."""
        self._log(f"A carregar grafo de {caminho_grafo}...")
        num_nos_carregados = self.ambiente.carregar_grafo(caminho_grafo)

        self._log(f"A carregar veículos de {caminho_veiculos}...")
        num_veiculos_carregados = self.ambiente.carregar_veiculos(caminho_veiculos)

        self._log(f"A carregar pedidos de {caminho_pedidos}...")
        num_pedidos_carregados = self.ambiente.carregar_pedidos(caminho_pedidos)

        num_eventos_carregados = 0

        if caminho_eventos_transito:
            self._log(f"A carregar eventos de trânsito de {caminho_eventos_transito}...")
            num_eventos_carregados = self.gestor_eventos.carregar_eventos_transito(
                caminho_eventos_transito)

        self.logger.dados_carregados(
            num_nos_carregados,
            num_veiculos_carregados,
            num_pedidos_carregados,
            num_eventos_carregados)

    ##### MÉTODO PRINCIPAL DE EXECUÇÃO DA SIMULAÇÃO #####

    def executar(self, duracao_horas: float = 8.0):
        """Executa a simulação temporal."""
        self.em_execucao = True
        tempo_final = self.tempo_simulacao + timedelta(hours=duracao_horas)

        self.logger.simulacao_iniciada(
            duracao_horas=duracao_horas,
            inicio=self.tempo_simulacao,
            velocidade_simulacao=self.velocidade_simulacao,
            frequencia_calculo=self.frequencia_calculo,
            passo_tempo=self.passo_tempo
        )

        # Iniciar display se disponível
        if self.display:
            self.display.iniciar(self.ambiente)

        # Agendar chegada de todos os pedidos
        self._agendar_pedidos()

        # Agendar eventos de trânsito
        # NOTA: depois se houver mais tipos de eventos, fazer um metodo generico de agendar eventos
        self._agendar_eventos_transito()

        # Loop principal da simulação
        tempo_inicio_real = time.time()
        tempo_decorrido_simulacao = timedelta(0)

        while self.tempo_simulacao < tempo_final and self.em_execucao:
            # 1. Processar eventos agendados e adicionar eventos novos aleatórios se
            # chances permitirem
            chuveu, novo_pedido = self.simuladorAleatorio.simulacaoAleatoria(
                self.ambiente, self.tempo_simulacao)
            if (chuveu):
                self._log("[DIN]Trocou de tempo")

            if novo_pedido:
                self._log(f"[DIN] Pedido dinâmico gerado #{novo_pedido.id}")

                self.gestor_eventos.agendar_evento(
                    tempo=self.tempo_simulacao,
                    tipo=TipoEvento.CHEGADA_PEDIDO,
                    callback=self._processar_pedido,
                    dados={'pedido': novo_pedido},
                    prioridade=novo_pedido.prioridade
                )

            self.gestor_eventos.processar_eventos_ate(self.tempo_simulacao)

            # 2. Recalcular rotas afetadas por eventos (ex: alterações de trânsito)
            self.gestor_rotas.recalcular_rotas_afetadas(self.gestor_viagens.viagens_ativas)

            # 3. Planear reposicionamentos proativos (se política permitir)
            num_reposicionados = self.gestor_reposicionamento.planear_reposicionamentos(
                tempo_simulacao=self.tempo_simulacao
            )

            # 4. Determinar passo do ciclo (limitado pelo passo padrão e pelo tempo restante)
            restante = tempo_final - self.tempo_simulacao
            passo_atual = self.passo_tempo if self.passo_tempo <= restante else restante

            # Se houver um próximo evento antes do fim deste passo, reduzir o passo
            # para que não passemos por cima do instante do evento (o evento será
            # processado na próxima iteração, que começa com processar_eventos_ate).
            try:
                proximo_evento = self.gestor_eventos.fila_temporal.espiar_proximo()
                if proximo_evento is not None and proximo_evento.tempo > self.tempo_simulacao:
                    delta_para_evento = proximo_evento.tempo - self.tempo_simulacao
                    if delta_para_evento < passo_atual:
                        passo_atual = delta_para_evento
            except Exception:
                pass

            # 5. Calcular e aplicar efeitos do passo (atualizar progresso das viagens e recargas)
            tempo_passo_horas = passo_atual.total_seconds() / 3600 if passo_atual.total_seconds() > 0 else 0

            veiculos_chegaram_posto = self.gestor_viagens.atualizar_viagens_ativas(
                tempo_passo_horas, self.tempo_simulacao
            )

            for _, veiculo in veiculos_chegaram_posto:
                self.gestor_recargas.processar_chegada_posto(
                    veiculo, self.tempo_simulacao
                )

            # 6. Atualizar eventos dinâmicos
            self.gestor_eventos.atualizar(self.tempo_simulacao)

            # 7. Atualizar display
            if self.display and hasattr(self.display, 'atualizar_tempo_simulacao'):
                self.display.atualizar_tempo_simulacao(
                    self.tempo_simulacao, self.gestor_viagens.viagens_ativas)

            # 8. Sincronizar com tempo real (apenas para velocidades moderadas)
            if self.velocidade_simulacao <= VELOCIDADE_MAXIMA_SINCRONIZADA:
                tempo_decorrido_simulacao += passo_atual
                tempo_esperado_real = tempo_decorrido_simulacao.total_seconds() / \
                    self.velocidade_simulacao
                tempo_decorrido_real = time.time() - tempo_inicio_real
                tempo_espera = tempo_esperado_real - tempo_decorrido_real

                if tempo_espera > 0:
                    time.sleep(tempo_espera)

            # 9. Finalmente, avançar o relógio de simulação (usar passo_atual)
            self.tempo_simulacao += passo_atual

        # Finalizar simulação
        self.em_execucao = False
        self.logger.simulacao_concluida(fim=self.tempo_simulacao)

        # Gerar relatório de métricas
        self._log(self.metricas.gerar_relatorio())

        # Exportar estatísticas
        self._exportar_estatisticas()

        # Finalizar display se necessário
        if self.display:
            self.display.finalizar()

    ### MÉTODOS AUXILIARES DE EXPORTAÇÃO DE ESTATISTICAS E LOGGING ###

    def _log(self, mensagem: str):
        """Escreve mensagem no log."""
        self.logger.log(mensagem)

    def _exportar_estatisticas(self):
        """Exporta as métricas para CSV cumulativo (delegado para `Metricas`)."""

        config = {
            'navegador': self.navegador.nome_algoritmo(),
            'alocador': self.alocador.nome_algoritmo(),
            'velocidade': self.velocidade_simulacao,
            'recarga_policy': self.gestor_recargas.recarga_policy.nome_politica(),
            'recarga_permitida': self.gestor_recargas.recarga_policy.permite_recarga(),
            'ridesharing_policy': self.gestor_pedidos.ridesharing_policy.nome_politica(),
            'ridesharing_permitida': self.gestor_pedidos.ridesharing_policy.permite_ridesharing(),
            'reposicionamento_policy': self.gestor_reposicionamento.reposicionamento_policy.nome_politica()
        }

        csv_ficheiro = self.metricas.exportar_csv(None, config)

        self._log(f"\n Estatísticas exportadas para: {csv_ficheiro}")
        self._log(f" Log da simulação guardado em: {self.logger.get_caminho_log()}")

    ### MÉTODOS AUXILIARES DE AGENDAMENTO DE EVENTOS ###

    def _agendar_pedidos(self):
        """Agenda todos os pedidos para chegarem no horário pretendido."""
        pedidos_pendentes = self.ambiente.listar_pedidos_pendentes()
        self._log(f"Agendando {len(pedidos_pendentes)} pedidos...")

        for pedido in pedidos_pendentes:
            self.gestor_eventos.agendar_evento(
                tempo=pedido.horario_pretendido,
                tipo=TipoEvento.CHEGADA_PEDIDO,
                callback=self._processar_pedido,
                dados={'pedido': pedido},
                prioridade=pedido.prioridade
            )

        self._log(f" {len(pedidos_pendentes)} pedidos agendados\n")

    def _agendar_eventos_transito(self):
        """Agenda todos os eventos de trânsito carregados."""
        num_eventos = self.gestor_eventos.agendar_eventos_transito(
            tempo_inicial=self.tempo_simulacao,
            callback_alterar_transito=self._alterar_transito
        )
        self._log(f"Agendando {num_eventos} eventos de trânsito...")

    ### MÉTODOS AUXILIARES PARA CALLBACKS DE EVENTOS ###

    def _alterar_transito(self, aresta: str, nivel: str) -> bool:
        """
        Altera o nível de trânsito de uma aresta.
        Callback usado pelo gestor de eventos para manter modularidade.

        Args:
            aresta: Nome da aresta a alterar
            nivel: Nível de trânsito como string (ex: "ELEVADO", "ACIDENTE")

        Returns:
            True se alteração bem sucedida, False caso contrário
        """
        try:
            nivel_enum = NivelTransito[nivel]
            sucesso = self.ambiente.grafo.alterarTransitoAresta(aresta, nivel_enum)

            if sucesso:
                self._log(f"[TRÂNSITO] Aresta '{aresta}' alterada para {nivel}")
                # Registar aresta alterada no gestor de rotas
                self.gestor_rotas.registar_aresta_alterada(aresta)

            return sucesso
        except KeyError:
            self._log(f"[AVISO] Nível de trânsito inválido: {nivel}")
            return False

    def _processar_pedido(self, pedido):
        """
        Processa um pedido individual delegando ao gestor de pedidos.

        Args:
            pedido: Pedido a processar
        """
        veiculo = self.gestor_pedidos.processar_pedido(
            pedido=pedido,
            tempo_simulacao=self.tempo_simulacao
        )

        # Se um veículo foi alocado, adicionar às viagens ativas
        if veiculo:
            self.gestor_viagens.adicionar_viagem(veiculo)
