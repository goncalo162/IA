"""
Motor principal da simulação.
Coordena ambiente, algoritmos, métricas e display.
"""
from typing import Optional, Dict
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from infra.simuladorDinamico import SimuladorDinamico

# Carregar variáveis de ambiente
load_dotenv()
from infra.gestaoAmbiente import GestaoAmbiente
from infra.metricas import Metricas
from infra.evento import GestorEventos, TipoEvento

# Constante: velocidade máxima com sincronização em tempo real
VELOCIDADE_MAXIMA_SINCRONIZADA = float(os.getenv('VELOCIDADE_MAXIMA_SINCRONIZADA', 100.0))


class Simulador:
    """
    Classe principal que orquestra toda a simulação.
    Permite trocar algoritmos de alocação e navegação de forma modular.
    """

    def __init__(self, alocador, navegador, display=None,
                 tempo_inicial: Optional[datetime] = None,
                 frequencia_calculo: float = 10.0,
                 velocidade_simulacao: float = 1.0):
        """
        Inicializa o simulador com os componentes necessários.
        """
        self.alocador = alocador
        self.navegador = navegador
        self.display = display
        self.pedidoIdAtual = 0

        self.ambiente = GestaoAmbiente()
        self.metricas = Metricas()
        self.gestor_eventos = GestorEventos()
        
        # Carregar configurações do simulador dinâmico do .env
        chance_troca_tempo = float(os.getenv('CHANCE_TROCA_TEMPO', 0.4))
        chance_pedido_aleatorio = float(os.getenv('CHANCE_PEDIDO_ALEATORIO', 0.3))
        self.simuladorDinamico = SimuladorDinamico(chance_troca_tempo, chance_pedido_aleatorio)
        
        self.tempo_simulacao = tempo_inicial or datetime.now()
        self.velocidade_simulacao = velocidade_simulacao
        self.frequencia_calculo = frequencia_calculo
        self.passo_tempo = timedelta(
            seconds=velocidade_simulacao / frequencia_calculo)

        self.em_execucao = False
        self.viagens_ativas: Dict = {}
        self.pedidos_agendados = []

        self._configurar_logging()

    def _configurar_logging(self):
        """Configura sistema de logging com timestamp para ficheiro."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(project_root, 'runs', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        self.log_ficheiro = os.path.join(log_dir, f'run_{timestamp}.log')
        self.run_timestamp = timestamp

        with open(self.log_ficheiro, 'w', encoding='utf-8') as f:
            f.write(f"=== SIMULAÇÃO DE GESTÃO DE FROTA ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(
                f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")

    def _log(self, mensagem: str):
        """Escreve mensagem no log e envia para o display."""
        # Escrever no ficheiro de log
        with open(self.log_ficheiro, 'a', encoding='utf-8') as f:
            f.write(mensagem + '\n')

    def carregar_dados(self, caminho_grafo: str, caminho_veiculos: str,
                       caminho_pedidos: str):
        """Carrega todos os dados necessários para a simulação."""
        self._log(f"A carregar grafo de {caminho_grafo}...")
        self.ambiente.carregar_grafo(caminho_grafo)

        self._log(f"A carregar veículos de {caminho_veiculos}...")
        self.ambiente.carregar_veiculos(caminho_veiculos)

        self._log(f"A carregar pedidos de {caminho_pedidos}...")
        self.ambiente.carregar_pedidos(caminho_pedidos)

        self._log("Dados carregados com sucesso!")
        self._log(f"  - Nós no grafo: {len(self.ambiente.grafo.getNodes())}")
        self._log(f"  - Veículos: {len(self.ambiente.listar_veiculos())}")
        self._log(f"  - Pedidos: {len(self.ambiente.listar_pedidos())}")

    def executar(self, duracao_horas: float = 8.0):
        """Executa a simulação temporal."""
        self.em_execucao = True
        tempo_final = self.tempo_simulacao + timedelta(hours=duracao_horas)

        self._log("\n" + "="*60)
        self._log("INICIANDO SIMULAÇÃO TEMPORAL")
        self._log("="*60)
        self._log(
            f"Tempo inicial: {self.tempo_simulacao.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Duração: {duracao_horas} horas")
        self._log(f"Velocidade de simulação: {self.velocidade_simulacao}x")

        if self.velocidade_simulacao > VELOCIDADE_MAXIMA_SINCRONIZADA:
            self._log(
                f" MODO TURBO ATIVADO: Velocidade > {VELOCIDADE_MAXIMA_SINCRONIZADA}x")

        self._log(f"Frequência de cálculo: {self.frequencia_calculo} Hz")
        self._log(
            f"Passo temporal simulado: {self.passo_tempo.total_seconds()} segundos")
        self._log("="*60 + "\n")

        # Iniciar display se disponível
        if self.display:
            self.display.iniciar(self.ambiente)

        # Agendar chegada de todos os pedidos
        self._agendar_pedidos()

        # TODO: Iniciar e adicionar outros eventos dinâmicos

        # Loop principal da simulação
        tempo_inicio_real = time.time()
        tempo_decorrido_simulacao = timedelta(0)

        while self.tempo_simulacao < tempo_final and self.em_execucao:
            # 1. Processar eventos agendados e adicionar eventos novos ne necessário
            chuveu, novo_pedido = self.simuladorDinamico.simulacaoDinamica(self.ambiente, self.tempo_simulacao)
            if(chuveu == True):
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

            # 2. Determinar passo do ciclo (limitado pelo passo padrão e pelo tempo restante)
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

            # 3. Calcular e aplicar efeitos do passo (atualizar progresso das viagens)
            tempo_passo_horas = passo_atual.total_seconds() / 3600 if passo_atual.total_seconds() > 0 else 0
            self._atualizar_viagens_ativas(tempo_passo_horas)


            # 4. Atualizar eventos dinâmicos
            self.gestor_eventos.atualizar(self.tempo_simulacao)

            # 5. Atualizar display e métricas
            if self.display and hasattr(self.display, 'atualizar_tempo_simulacao'):
                self.display.atualizar_tempo_simulacao(
                    self.tempo_simulacao, self.viagens_ativas)

            # 6. Sincronizar com tempo real (apenas para velocidades moderadas)
            if self.velocidade_simulacao <= VELOCIDADE_MAXIMA_SINCRONIZADA:
                tempo_decorrido_simulacao += passo_atual
                tempo_esperado_real = tempo_decorrido_simulacao.total_seconds() / \
                    self.velocidade_simulacao
                tempo_decorrido_real = time.time() - tempo_inicio_real
                tempo_espera = tempo_esperado_real - tempo_decorrido_real

                if tempo_espera > 0:
                    time.sleep(tempo_espera)

            # 7. Finalmente, avançar o relógio de simulação (usar passo_atual)
            self.tempo_simulacao += passo_atual
            

        # Finalizar simulação
        self.em_execucao = False
        self._log("\n" + "="*60)
        self._log("SIMULAÇÃO CONCLUÍDA")
        self._log("="*60)
        self._log(
            f"Tempo final: {self.tempo_simulacao.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Pedidos processados: {self.metricas.pedidos_atendidos}")
        self._log(f"Pedidos rejeitados: {self.metricas.pedidos_rejeitados}")
        self._log("="*60 + "\n")

        # Gerar relatório de métricas
        self._log(self.metricas.gerar_relatorio())

        # Exportar estatísticas
        self._exportar_estatisticas()

        # Finalizar display se necessário
        if self.display:
            self.display.finalizar()

    def _exportar_estatisticas(self):
        """Exporta as métricas para CSV cumulativo."""
        project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        csv_ficheiro = os.path.join(
            project_root, 'runs', 'stats', 'statistics.csv')

        config = {
            'navegador': self.navegador.nome_algoritmo(),
            'alocador': self.alocador.__class__.__name__,
            'velocidade': self.velocidade_simulacao
        }

        self.metricas.exportar_csv(csv_ficheiro, config)

        self._log(f"\n Estatísticas exportadas para: {csv_ficheiro}")
        self._log(f" Log da simulação guardado em: {self.log_ficheiro}")

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

    def _atualizar_viagens_ativas(self, tempo_passo_horas: float = None):
        """Atualiza o progresso de todas as viagens em curso.

        Args:
            tempo_passo_horas: tempo simulado decorrido neste passo, em horas.
                Se None, usa `self.passo_tempo` para calcular.
        """
        if not self.viagens_ativas:
            return

        if tempo_passo_horas is None:
            tempo_passo_horas = self.passo_tempo.total_seconds() / 3600

        viagens_concluidas = []

        for veiculo_id, veiculo in list(self.viagens_ativas.items()):
            concluidas = veiculo.atualizar_progresso_viagem(tempo_passo_horas)
            for v in concluidas:
                viagens_concluidas.append((veiculo_id, veiculo, v))

        # Processar viagens concluídas (por viagem específica)
        for veiculo_id, veiculo, viagem in viagens_concluidas:
            self._concluir_viagem(veiculo, viagem)
            # Remover veículo da lista ativa apenas se não houver mais viagens ativas
            if not veiculo.viagem_ativa and veiculo_id in self.viagens_ativas: #REVER ISTO porque sem a segunda condição nao funciona sempre, mas devia, ou seja, pode estar a apagar em sitios que nao devia
                    del self.viagens_ativas[veiculo_id]

    def _concluir_viagem(self, veiculo, viagem):
        """Processa a conclusão de uma viagem específica em um veículo."""
        pedido_id = viagem.pedido_id

        self.ambiente.concluir_pedido(pedido_id, viagem)

        log_msg = f"[green][/] Viagem concluída: Pedido #{pedido_id} | Veículo {veiculo.id_veiculo} em {veiculo.localizacao_atual}"
        self._log(log_msg)

    def _processar_pedido(self, pedido):
        """Processa um pedido individual no modo temporal."""
        horario_log = self.tempo_simulacao.strftime('%H:%M:%S')
        self._log(
            f"\n {horario_log} - [cyan]Processando Pedido #{pedido.id}[/]")
  
        # 1. Pré-calcular rota do pedido (origem -> destino)
        origem_pedido_nome = self.ambiente.grafo.getNodeName(pedido.origem)
        destino_nome = self.ambiente.grafo.getNodeName(pedido.destino)
        rota_viagem = self.navegador.calcular_rota(
            grafo=self.ambiente.grafo,
            origem=origem_pedido_nome,
            destino=destino_nome
        )

        if rota_viagem is None:
            self._log(
                f"  [red]✗[/] Rota pedido não encontrada ({origem_pedido_nome} -> {destino_nome})")
            self.metricas.registar_pedido_rejeitado(
                pedido.id, "Rota pedido não encontrada")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return

        distancia_viagem = self.ambiente._calcular_distancia_rota(rota_viagem)

        # NOTA: se calhar depois de calcularmos a rota da origem do pedido ate ao fim do pedido, e virmos se tem algum posto de abastecimento pelo caminho e onde,
        # podiamos considerar ir abastecer antes de ir buscar o cliente ou durante a viagem, ou seja, escolher um carro depois de calcular a rota do pedido
        # so depois calcular a rota do carro escolhido ate ao inicio do pedido.

        # 2. Escolher veículo considerando autonomia e rota até cliente
        # Escolher a lista de veículos apropriada (ride-sharing inclui em andamento)
        lista_veiculos = (self.ambiente.listar_veiculos_ridesharing()
                          if pedido.ride_sharing
                          else self.ambiente.listar_veiculos_disponiveis())

        veiculo = self.alocador.escolher_veiculo(
            pedido=pedido,
            veiculos_disponiveis=lista_veiculos,
            grafo=self.ambiente.grafo,
            rota_pedido=rota_viagem,
            distancia_pedido=distancia_viagem,
        )

        if veiculo is None:
            self._log(
                f"  [yellow][/] Nenhum veículo disponível/autónomo para o pedido #{pedido.id}")
            self.metricas.registar_pedido_rejeitado(
                pedido.id, "Sem veículos com autonomia suficiente")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return

        self._log(f"  [green][/] Veículo alocado: {veiculo.id_veiculo}")
        self.ambiente.atribuir_pedido_a_veiculo(pedido, veiculo)

        # TODO: decidir se as localizações são nomes ou IDs
        #TODO: REVER ISTO TUDO ABAIXO

        # Ajuste de rotas para ride-sharing sem desvios:

        #todo: rever se queremos sem desvios ou se pode fazer desvios e tem que recalcular a rota
        # Se o veículo já tem viagens ativas, a rota do pedido deve iniciar
        # coincidente com o plano atual do veículo e só depois estender até ao destino.
        if pedido.ride_sharing and veiculo.estado == veiculo.estado.EM_ANDAMENTO:
            try:
                rota_total = veiculo.rota_total_viagens()
            except Exception:
                rota_total = []

            if rota_total and origem_pedido_nome in rota_total:
                idx_origem = rota_total.index(origem_pedido_nome)
                # veículo -> cliente: do início do plano até à origem (inclui a origem)
                nova_rota_ate_cliente = rota_total[:idx_origem+1]

                # cliente -> destino: seguir o plano e, se necessário, estender até ao destino
                tail = rota_total[idx_origem:]
                if destino_nome in tail:
                    dest_idx = tail.index(destino_nome)
                    nova_rota_viagem = tail[:dest_idx+1]
                else:
                    rota_extra = self.navegador.calcular_rota(
                        grafo=self.ambiente.grafo,
                        origem=tail[-1],
                        destino=destino_nome
                    )
                    if rota_extra and len(rota_extra) > 0:
                        nova_rota_viagem = tail + (rota_extra[1:] if len(rota_extra) > 1 else [])
                    else:
                        nova_rota_viagem = rota_viagem  # fallback se não houver rota de extensão

                # Atualizar distâncias e valores utilizados adiante
                veiculo.rota_ate_cliente = nova_rota_ate_cliente
                veiculo.distancia_ate_cliente = self.ambiente._calcular_distancia_rota(nova_rota_ate_cliente)
                rota_viagem = nova_rota_viagem
                distancia_viagem = self.ambiente._calcular_distancia_rota(rota_viagem)

        # 3. Recuperar rota veículo -> cliente e distância calculadas pelo alocador
        rota_ate_cliente = veiculo.rota_ate_cliente
        distancia_ate_cliente = veiculo.distancia_ate_cliente

        distancia_total = distancia_ate_cliente + distancia_viagem

        tempo_ate_cliente = self.ambiente._calcular_tempo_rota(rota_ate_cliente) * 60
        tempo_viagem = self.ambiente._calcular_tempo_rota(rota_viagem) * 60

        # NOTA: rever se devia ser com a distancia total
        custo = distancia_viagem * veiculo.custo_operacional_km
        emissoes = self.ambiente._calcular_emissoes(veiculo, distancia_viagem)

        self._log(
            f"  [green][/] Rota veículo->cliente: {' → '.join(rota_ate_cliente)}")
        self._log(
            f"  [green][/] Rota cliente->destino: {' → '.join(rota_viagem)}")
        self._log(
            f"    Distância: {distancia_total:.2f} km ({tempo_ate_cliente + tempo_viagem:.1f} min)")
        self._log(
            f"    Custo: €{custo:.2f} |  Emissões: {emissoes:.2f} kg CO₂")

        # 5. Iniciar viagem
        iniciou = veiculo.iniciar_viagem(
            pedido=pedido,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_viagem,
            distancia_ate_cliente=distancia_ate_cliente,
            distancia_pedido=distancia_viagem,
            tempo_inicio=self.tempo_simulacao,
            grafo=self.ambiente.grafo
        )
        if not iniciou:
            self._log(
                f"  [yellow][/] Capacidade excedida para ride-sharing no veículo {veiculo.id_veiculo}")
            self.metricas.registar_pedido_rejeitado(
                pedido.id, "Capacidade ride-sharing excedida")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return

        self.viagens_ativas[veiculo.id_veiculo] = veiculo

        # 6. Registar métricas
        self.metricas.registar_pedido_atendido(
            pedido_id=pedido.id,
            veiculo_id=veiculo.id_veiculo,
            tempo_resposta=tempo_ate_cliente,
            distancia=distancia_viagem,
            custo=custo,
            emissoes=emissoes
        )

        self._log(
            f"  [green][/] Viagem iniciada - ETA: {tempo_ate_cliente + tempo_viagem:.1f} min")

        # Atualizar displays
        if self.display:
            # Atualizar display com a rota desta nova viagem
            nova_viagem_rota = veiculo.viagens[-1].rota if veiculo.viagens else []
            self.display.atualizar(pedido, veiculo, nova_viagem_rota)
