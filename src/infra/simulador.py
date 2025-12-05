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
from infra.grafo.aresta import NivelTransito

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
        self._arestas_alteradas = set()  # Arestas alteradas para recálculo de rotas

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
                       caminho_pedidos: str, caminho_eventos_transito: str = None):
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

        # Carregar eventos de trânsito se o ficheiro for fornecido
        if caminho_eventos_transito:
            self._log(f"A carregar eventos de trânsito de {caminho_eventos_transito}...")
            num_eventos = self.gestor_eventos.carregar_eventos_transito(ficheiro_json=caminho_eventos_transito)
            self._log(f"  - Eventos de trânsito: {num_eventos}")


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
                self._arestas_alteradas.add(aresta) # Marcar aresta para recálculo posterior
                
            return sucesso
        except KeyError:
            self._log(f"[AVISO] Nível de trânsito inválido: {nivel}")
            return False

    def _recalcular_rotas_afetadas(self):
        """
        Verifica todas as viagens ativas e recalcula as rotas que passam pelas arestas alteradas.
        Chamado no loop principal após processar eventos.
        """
        if not self.viagens_ativas or not self._arestas_alteradas:
            return
        
        total_recalculadas = 0
        total_viagens_afetadas = 0
        
        for aresta in self._arestas_alteradas:
            for veiculo_id, veiculo in self.viagens_ativas.items():
                # Verificar se alguma viagem deste veículo passa pela aresta
                viagens_afetadas = veiculo.viagens_afetadas_por_aresta(aresta, self.ambiente.grafo)
                
                if viagens_afetadas:
                    total_viagens_afetadas += len(viagens_afetadas)
                    self._log(f"[RECÁLCULO] Veículo {veiculo_id} tem {len(viagens_afetadas)} viagem(ns) afetada(s) por '{aresta}'")
                    
                    num_recalculadas = self._recalcular_rotas_veiculo(veiculo, viagens_afetadas)
                    total_recalculadas += num_recalculadas
        
        # Registar evento de recálculo nas métricas
        if total_viagens_afetadas > 0:
            self.metricas.registar_evento_recalculo(total_viagens_afetadas)
        
        # Limpar lista de arestas alteradas após recálculo
        self._arestas_alteradas.clear()
        
        if total_recalculadas > 0:
            self._log(f"[RECÁLCULO] Total de {total_recalculadas} rota(s) recalculada(s)")

    #TODO: rever isto _recalcular_rotas_veiculo e talvez arranjar forma mais eficiente de recalcular, por exemplo ir da ultima viagem para a primeira, ate deixar de ser uma viagem com rota afetada, e só recalcular a partir daí
    #em vez de recalcular todas as viagens afetadas ou não.

    def _recalcular_rotas_veiculo(self, veiculo, viagens_afetadas) -> int:
        """
        Recalcula as rotas das viagens afetadas de um veículo.
        
        No ride-sharing, todas as viagens ativas partilham a mesma rota base,
        por isso calculamos uma rota combinada que passa por todos os destinos
        e depois atualizamos cada viagem com a parte correspondente.
        """
        viagens_ativas = [v for v in viagens_afetadas if v.viagem_ativa]
        if not viagens_ativas:
            return 0
        
        # Obter posição atual do veículo a partir da rota combinada
        rota_total = veiculo.rota_total_viagens()
        pos_atual = rota_total[0] if rota_total else None
        if not pos_atual:
            return 0
        
        # Obter todos os destinos das viagens ativas do veículo (não só as afetadas)
        todas_viagens_ativas = [v for v in veiculo.viagens if v.viagem_ativa]
        destinos = [v.destino for v in todas_viagens_ativas if v.destino]
        
        if not destinos:
            return 0
        
        # Se só há um destino, calcular rota simples
        if len(destinos) == 1:
            # Se já estamos no destino, não há nada a recalcular
            if pos_atual == destinos[0]:
                return 0
            
            nova_rota = self.navegador.calcular_rota(self.ambiente.grafo, pos_atual, destinos[0])
            if nova_rota and len(nova_rota) >= 2:
                viagem = viagens_ativas[0]
                tempo_anterior = viagem.tempo_restante_horas()
                distancia_anterior = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
                
                if viagem.aplicar_nova_rota(nova_rota, self.ambiente.grafo):
                    tempo_novo = viagem.tempo_restante_horas()
                    distancia_nova = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
                    delta = (tempo_novo - tempo_anterior) * 60
                    
                    # Registar métricas de recálculo
                    self.metricas.registar_recalculo_rota(
                        pedido_id=viagem.pedido_id,
                        veiculo_id=veiculo.id_veiculo,
                        diferenca_tempo=delta,
                        motivo="transito",
                        distancia_anterior=distancia_anterior,
                        distancia_nova=distancia_nova
                    )
                    
                    self._log(f"[RECÁLCULO] Viagem #{viagem.pedido_id} recalculada. Diferença: {delta:+.1f} min")
                    return 1
            return 0
        
        # Para ride-sharing com múltiplos destinos: calcular rota combinada
        # Ordenar destinos por chegada estimada atual para manter a ordem
        destinos_unicos = list(dict.fromkeys(destinos))  # Remove duplicados mantendo ordem
        
        # Calcular rota que passa por todos os destinos na ordem
        rota_combinada = [pos_atual]
        ponto_atual = pos_atual
        
        for destino in destinos_unicos:
            if destino == ponto_atual:
                continue
            segmento = self.navegador.calcular_rota(self.ambiente.grafo, ponto_atual, destino)
            if segmento and len(segmento) > 1:
                rota_combinada.extend(segmento[1:])  # Sem repetir o nó de junção
                ponto_atual = destino
        
        if len(rota_combinada) < 2:
            return 0
        
        # Aplicar a rota apropriada a cada viagem
        recalculadas = 0
        for viagem in todas_viagens_ativas:
            destino_viagem = viagem.destino
            
            # Se já estamos no destino desta viagem, não recalcular
            if destino_viagem == pos_atual:
                continue
            
            if destino_viagem not in rota_combinada:
                continue
            
            # A rota desta viagem vai até ao seu destino
            idx_destino = rota_combinada.index(destino_viagem)
            rota_viagem = rota_combinada[:idx_destino + 1]
            
            # Garantir que a rota tem pelo menos 2 nós
            if len(rota_viagem) < 2:
                continue
            
            tempo_anterior = viagem.tempo_restante_horas()
            distancia_anterior = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
            
            if viagem.aplicar_nova_rota(rota_viagem, self.ambiente.grafo):
                tempo_novo = viagem.tempo_restante_horas()
                distancia_nova = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
                delta = (tempo_novo - tempo_anterior) * 60
                
                # Registar métricas de recálculo
                self.metricas.registar_recalculo_rota(
                    pedido_id=viagem.pedido_id,
                    veiculo_id=veiculo.id_veiculo,
                    diferenca_tempo=delta,
                    motivo="transito",
                    distancia_anterior=distancia_anterior,
                    distancia_nova=distancia_nova
                )
                
                self._log(f"[RECÁLCULO] Viagem #{viagem.pedido_id} recalculada. Diferença: {delta:+.1f} min")
                recalculadas += 1
        
        return recalculadas

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

        # Agendar eventos de trânsito 
        #NOTA: depois se houver mais tipos de eventos, fazer um metodo generico de agendar eventos
        self._agendar_eventos_transito()

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

            # 2. Recalcular rotas afetadas por eventos (ex: alterações de trânsito)
            self._recalcular_rotas_afetadas()

            # 3. Determinar passo do ciclo (limitado pelo passo padrão e pelo tempo restante)
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

            # 4. Calcular e aplicar efeitos do passo (atualizar progresso das viagens)
            tempo_passo_horas = passo_atual.total_seconds() / 3600 if passo_atual.total_seconds() > 0 else 0
            self._atualizar_viagens_ativas(tempo_passo_horas)


            # 5. Atualizar eventos dinâmicos
            self.gestor_eventos.atualizar(self.tempo_simulacao)

            # 6. Atualizar display e métricas
            if self.display and hasattr(self.display, 'atualizar_tempo_simulacao'):
                self.display.atualizar_tempo_simulacao(
                    self.tempo_simulacao, self.viagens_ativas)

            # 7. Sincronizar com tempo real (apenas para velocidades moderadas)
            if self.velocidade_simulacao <= VELOCIDADE_MAXIMA_SINCRONIZADA:
                tempo_decorrido_simulacao += passo_atual
                tempo_esperado_real = tempo_decorrido_simulacao.total_seconds() / \
                    self.velocidade_simulacao
                tempo_decorrido_real = time.time() - tempo_inicio_real
                tempo_espera = tempo_esperado_real - tempo_decorrido_real

                if tempo_espera > 0:
                    time.sleep(tempo_espera)

            # 8. Finalmente, avançar o relógio de simulação (usar passo_atual)
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

    def _agendar_eventos_transito(self):
        """Agenda todos os eventos de trânsito carregados."""
        num_eventos = self.gestor_eventos.agendar_eventos_transito(
            tempo_inicial=self.tempo_simulacao,
            callback_alterar_transito=self._alterar_transito
        )
        self._log(f"Agendando {num_eventos} eventos de trânsito...")

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
