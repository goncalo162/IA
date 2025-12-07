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
from infra.logger import SimuladorLogger

# Carregar variáveis de ambiente
load_dotenv()
from infra.gestaoAmbiente import GestaoAmbiente
from infra.metricas import Metricas
from infra.evento import GestorEventos, TipoEvento
from infra.grafo.aresta import NivelTransito
from infra.entidades.veiculos import EstadoVeiculo

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
        self.logger = SimuladorLogger()
        
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

    def _log(self, mensagem: str):
        """Escreve mensagem no log."""
        self.logger.log(mensagem)

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
        # Carregar eventos de trânsito se o ficheiro for fornecido
        if caminho_eventos_transito:
            self._log(f"A carregar eventos de trânsito de {caminho_eventos_transito}...")
            num_eventos_carregados = self.gestor_eventos.carregar_eventos_transito(caminho_eventos_transito)
    
        self.logger.dados_carregados(num_nos_carregados, num_veiculos_carregados, num_pedidos_carregados, num_eventos_carregados)

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
        viagens_para_recalcular = self.ambiente.identificar_viagens_afetadas(
            self._arestas_alteradas,
            self.viagens_ativas
        )
        
        total_recalculadas = 0
        total_viagens_afetadas = 0
        
        for veiculo_id, veiculo, viagens_afetadas, aresta in viagens_para_recalcular:
            num_viagens = len(viagens_afetadas)
            total_viagens_afetadas += num_viagens
            
            self._log(f"[RECÁLCULO] Veículo {veiculo_id} tem {num_viagens} viagem(ns) afetada(s) por '{aresta}'")
            
            # Recalcular rotas usando o navegador
            recalculos = self._recalcular_rotas_veiculo(veiculo, viagens_afetadas)
            
            for rec in recalculos:
                self._log(f"[RECÁLCULO] Viagem #{rec['pedido_id']} recalculada. Diferença: {rec['delta_tempo']:+.1f} min")
                
                # Registar métricas
                self.metricas.registar_recalculo_rota(
                    pedido_id=rec['pedido_id'],
                    veiculo_id=veiculo_id,
                    diferenca_tempo=rec['delta_tempo'],
                    motivo="transito",
                    distancia_anterior=rec['distancia_anterior'],
                    distancia_nova=rec['distancia_nova']
                )
                total_recalculadas += 1
        
        if total_viagens_afetadas > 0:
            self.metricas.registar_evento_recalculo(total_viagens_afetadas)
            self._log(f"[RECÁLCULO] Total de {total_recalculadas} rota(s) recalculada(s)")
        
        # Limpar lista de arestas alteradas após recálculo
        self._arestas_alteradas.clear()
    
    def _recalcular_rotas_veiculo(self, veiculo, viagens_afetadas):
        """Recalcula rotas de viagens afetadas usando o navegador.
        
        Args:
            veiculo: Veículo com viagens a recalcular
            viagens_afetadas: Lista de viagens afetadas
            
        Returns:
            Lista de dicts com informações de recálculos
        """
        viagens_ativas = [v for v in viagens_afetadas if v.viagem_ativa]
        if not viagens_ativas:
            return []
        
        # Obter posição atual do veículo a partir da rota combinada
        rota_total = veiculo.rota_total_viagens()
        pos_atual = rota_total[0] if rota_total else None
        if not pos_atual:
            return []
        
        # Obter destinos
        destinos = veiculo.destinos_viagens_ativas()
        
        if len(destinos) == 0:
            return []
        
        # Caso simples: um destino
        if len(destinos) == 1:
            if pos_atual == destinos[0]:
                return []
            
            nova_rota = self.navegador.calcular_rota(self.ambiente.grafo, pos_atual, destinos[0])
            if nova_rota and len(nova_rota) >= 2:
                viagem = viagens_ativas[0]
                info = self.ambiente.aplicar_nova_rota(viagem, nova_rota)
                return [info] if info else []
            return []
        
        # Ride-sharing: rota combinada (múltiplos destinos)
        return self._recalcular_rota_ridesharing(veiculo, viagens_ativas, pos_atual, destinos)


    #TODO: rever isto e talvez arranjar forma mais eficiente de recalcular, por exemplo ir da ultima viagem para a primeira, ate deixar de ser uma viagem com rota afetada, e só recalcular a partir daí
    #em vez de recalcular todas as viagens afetadas ou não.
    
    def _recalcular_rota_ridesharing(self, veiculo, todas_viagens_ativas, pos_atual, destinos):
        """Recalcula rotas para ride-sharing com múltiplos destinos."""
        destinos_unicos = list(dict.fromkeys(destinos)) #TODO: não sei se deveriamos tirar os duplicados ou não REVER
        
        # Calcular rota combinada
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
            return []
        
        # Aplicar rota a cada viagem
        recalculos = []
        for viagem in todas_viagens_ativas:
            destino_viagem = viagem.destino
            
            if destino_viagem == pos_atual or destino_viagem not in rota_combinada:
                continue
            
            # A rota desta viagem vai até ao seu destino
            idx_destino = rota_combinada.index(destino_viagem)
            rota_viagem = rota_combinada[:idx_destino + 1]
            
            # Garantir que a rota tem pelo menos 2 nós
            if len(rota_viagem) < 2:
                continue
            
            info = self.ambiente.aplicar_nova_rota(viagem, rota_viagem)
            if info:
                recalculos.append(info)
        
        return recalculos


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
        self.logger.simulacao_concluida(fim=self.tempo_simulacao)

        # Gerar relatório de métricas
        self._log(self.metricas.gerar_relatorio())

        # Exportar estatísticas
        self._exportar_estatisticas()

        # Finalizar display se necessário
        if self.display:
            self.display.finalizar()

    #NOTA: talvez meter isto no logger ou nas metricas?
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
        self._log(f" Log da simulação guardado em: {self.logger.get_caminho_log()}")

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
    
    def _agendar_recarga(self, veiculo):
        """Agenda recarga/abastecimento de um veículo.
        
        Args:
            veiculo: Veículo que precisa de recarga
        """
        # Verificar se já está num posto adequado
        if veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
            self.gestor_eventos.agendar_evento(
                tempo=self.tempo_simulacao,
                tipo=TipoEvento.INICIO_RECARGA,
                callback=self._iniciar_recarga,
                dados={'veiculo': veiculo},
                prioridade=5
            )
            return
        
        # Precisa ir até um posto - obter lista de postos
        postos = self.ambiente.listar_postos_por_tipo(veiculo.tipo_posto_necessario())
        
        if not postos:
            tipo_posto = veiculo.tipo_posto_necessario()
            self._log(f"  [red]✗[/] Nenhum posto de tipo {tipo_posto.name} encontrado para veículo {veiculo.id_veiculo}")
            self.metricas.registar_veiculo_sem_autonomia(veiculo.id_veiculo)
            return
        
        # Encontrar posto mais próximo calculando rotas
        posto_nome = None
        rota_mais_curta = None
        distancia_mais_curta = float('inf')
        
        for p_nome in postos:
            rota_temp = self.navegador.calcular_rota(self.ambiente.grafo, veiculo.localizacao_atual, p_nome)
            if rota_temp and len(rota_temp) >= 2:
                dist_temp = self.ambiente.grafo.calcular_distancia_rota(rota_temp)
                if dist_temp < distancia_mais_curta:
                    distancia_mais_curta = dist_temp
                    rota_mais_curta = rota_temp
                    posto_nome = p_nome
        
        if not posto_nome or not rota_mais_curta:
            tipo_posto = veiculo.tipo_posto_necessario()
            self._log(f"  [red]✗[/] Nenhuma rota para posto de tipo {tipo_posto.name} encontrada para veículo {veiculo.id_veiculo}")
            self.metricas.registar_veiculo_sem_autonomia(veiculo.id_veiculo)
            return
        
        # Verificar autonomia
        if not veiculo.autonomia_suficiente_para(distancia_mais_curta, margem_seguranca=0):
            self._log(f"  [red]✗[/] Veículo {veiculo.id_veiculo} não tem autonomia para chegar ao posto mais próximo ({distancia_mais_curta:.1f} km)")
            veiculo.estado = EstadoVeiculo.INDISPONIVEL
            self.metricas.registar_veiculo_sem_autonomia(veiculo.id_veiculo)
            return
        
        # Iniciar viagem até o posto
        if veiculo.iniciar_viagem_recarga(rota_mais_curta, posto_nome, distancia_mais_curta, self.tempo_simulacao, self.ambiente.grafo):
            self.viagens_ativas[veiculo.id_veiculo] = veiculo
            tempo_viagem = self.ambiente._calcular_tempo_rota(rota_mais_curta)
            self._log(f"  [INFO] Veículo {veiculo.id_veiculo} a caminho do posto '{posto_nome}' ({distancia_mais_curta:.1f} km, ~{tempo_viagem*60:.1f} min)")
        else:
            self._log(f"  [red]✗[/] Falha ao iniciar viagem de recarga para veículo {veiculo.id_veiculo}")
            

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

        viagens_concluidas, veiculos_chegaram_posto = self.ambiente.atualizar_viagens_ativas(
            self.viagens_ativas,
            tempo_passo_horas
        )
        
        # Processar veículos que chegaram ao posto
        for veiculo_id, veiculo in veiculos_chegaram_posto:
            # Concluir a viagem de recarga (atualiza localização para o posto)
            veiculo.concluir_viagem_recarga()
            self._log(f"[INFO] Veículo {veiculo.id_veiculo} chegou ao posto em {veiculo.localizacao_atual}")
            
            if veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
                # Agendar início da recarga
                self.gestor_eventos.agendar_evento(
                    tempo=self.tempo_simulacao,
                    tipo=TipoEvento.INICIO_RECARGA,
                    callback=self._iniciar_recarga,
                    dados={'veiculo': veiculo},
                    prioridade=5
                )
            else:
                self._log(f"  [yellow]![/] Veículo {veiculo.id_veiculo} não pode reabastecer em {veiculo.localizacao_atual}")
                # Remover da lista de viagens ativas se não vai reabastecer
                if veiculo_id in self.viagens_ativas and not veiculo.viagem_ativa:
                    del self.viagens_ativas[veiculo_id]

        # Processar viagens concluídas
        for veiculo_id, veiculo, viagem in viagens_concluidas:
            self._concluir_viagem(veiculo, viagem)
            # Remover veículo da lista ativa apenas se não houver mais viagens ativas
            if not veiculo.viagem_ativa and veiculo_id in self.viagens_ativas:
                del self.viagens_ativas[veiculo_id]

    def _concluir_viagem(self, veiculo, viagem):
        """Processa a conclusão de uma viagem específica em um veículo."""
        pedido_id = viagem.pedido_id

        self.ambiente.concluir_pedido(pedido_id, viagem)

        log_msg = f"[green][/] Viagem concluída: Pedido #{pedido_id} | Veículo {veiculo.id_veiculo} em {veiculo.localizacao_atual}"
        self._log(log_msg)
        
        # Verificar necessidade de recarga após concluir viagem 
        #TODO: veiculo apenas está a verificar recarga se nao tiver mais viagens ativas, mas e se tiver mais viagens ativas e precisar de recarga?
        if not veiculo.viagem_ativa and veiculo.precisa_reabastecer():
            autonomia_pct = veiculo.percentual_autonomia_atual
            self._log(f"  [yellow]AVISO[/] Veículo {veiculo.id_veiculo} precisa recarga (autonomia: {veiculo.autonomia_atual:.1f}/{veiculo.autonomia_maxima} km, {autonomia_pct:.1f}%)")
            self._agendar_recarga(veiculo)

    def _validar_rota_pedido(self, pedido):
        """Valida e calcula a rota do pedido.
        
        Returns:
            Tupla (rota_viagem, distancia_viagem, origem_nome, destino_nome) ou (None, 0, origem, destino) se inválido
        """

        #NOTA: dar return de informação sobre postos de abastecimento também ou criar novo metodo auxiliar que trate disso?

        origem_nome, destino_nome = self.ambiente.obter_nomes_nos_pedido(pedido)
        
        rota_viagem = self.navegador.calcular_rota(self.ambiente.grafo, origem_nome, destino_nome)
        
        if rota_viagem is None or len(rota_viagem) < 2:
            self._log(f"  [red]✗[/] Rota pedido não encontrada ({origem_nome} -> {destino_nome})")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Rota pedido não encontrada")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return (None, 0, origem_nome, destino_nome)
        
        distancia_viagem = self.ambiente.grafo.calcular_distancia_rota(rota_viagem)
        
        return (rota_viagem, distancia_viagem, origem_nome, destino_nome)
    
    def _escolher_veiculo_para_pedido(self, pedido, rota_viagem, distancia_viagem):
        """Escolhe o veículo apropriado para o pedido.
        
        Returns:
            Veículo escolhido ou None se nenhum disponível
        """
        #TODO: confirmar se tem postos de abastecimento adequados na rota se necessário, e passar essa informação ao alocador?
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
            self._log(f"  [yellow][/] Nenhum veículo disponível/autónomo para o pedido #{pedido.id}")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Sem veículos com autonomia suficiente")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
        
        return veiculo
    
    def _ajustar_rotas_ridesharing(self, veiculo, origem_nome, destino_nome):
        """Ajusta rotas para ride-sharing se necessário.
        
        Returns:
            Tupla (rota_viagem_ajustada, distancia_viagem_ajustada) ou None se sem ajustes
        """
        #TODO: rever se queremos sem desvios (como está agora) ou permitir desvios pequenos
        #se permitir desvios tem que recalcular a rota toda de novo
        #senao, se o veiculo ja tem viagens ativas, a rota do pedido deve iniciar coincidente com o plano atual do veiculo
        #  e so depois estender até ao destino do pedido
    

        # Obter rota atual do veículo
        rota_atual = self.ambiente.obter_rota_atual_veiculo(veiculo)
        if not rota_atual or len(rota_atual) < 2:
            return None
        
        # Verificar se há viagens ativas
        viagens_ativas = [v for v in veiculo.viagens if v.viagem_ativa]
        if not viagens_ativas:
            return None
        
        # verificar se a origem do pedido está na rota atual do veiculo
        if rota_atual and origem_nome not in rota_atual:
            return None
        
        # Construir rota combinada
        idx_origem = rota_atual.index(origem_nome)
        #veiculo -> cliente: do inicio da rota até a origem do pedido
        nova_rota_ate_origem = rota_atual[:idx_origem + 1]
        #cliente -> destino: seguir rota tual e se necessário estender ate ao pedido
        tail_rota = rota_atual[idx_origem:]
        if destino_nome in tail_rota:
            idx_destino = tail_rota.index(destino_nome)
            nova_rota_viagem = tail_rota[:idx_destino + 1]
        else:
            extensao_rota = self.navegador.calcular_rota(self.ambiente.grafo, tail_rota[-1], destino_nome)
            if extensao_rota is None or len(extensao_rota) < 2:
                return None
            nova_rota_viagem = tail_rota + extensao_rota[1:]  # Sem repetir o nó de junção

        veiculo.rota_ate_cliente = nova_rota_ate_origem
        veiculo.distancia_ate_cliente = self.ambiente.grafo.calcular_distancia_rota(nova_rota_ate_origem)
        distancia_viagem = self.ambiente.grafo.calcular_distancia_rota(nova_rota_viagem)
        return (nova_rota_viagem, distancia_viagem)
    
    def _calcular_metricas_viagem(self, rota_ate_cliente, rota_viagem, veiculo, distancia_viagem):
        """Calcula métricas da viagem.
        
        Returns:
            Dict com tempo_ate_cliente, tempo_viagem, custo, emissoes
        """
        tempo_ate_cliente = self.ambiente._calcular_tempo_rota(rota_ate_cliente) * 60
        tempo_viagem = self.ambiente._calcular_tempo_rota(rota_viagem) * 60
        custo = distancia_viagem * veiculo.custo_operacional_km
        emissoes = self.ambiente._calcular_emissoes(veiculo, distancia_viagem)
        
        return {
            'tempo_ate_cliente': tempo_ate_cliente,
            'tempo_viagem': tempo_viagem,
            'custo': custo,
            'emissoes': emissoes
        }
    
    
    def _iniciar_viagem_pedido(self, veiculo, pedido, rota_ate_cliente, rota_viagem, distancia_ate_cliente, distancia_viagem):
        """Inicia a viagem do veículo.
        
        Returns:
            True se iniciou com sucesso, False caso contrário
        """
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
            self._log(f"  [yellow][/] Capacidade excedida para ride-sharing no veículo {veiculo.id_veiculo}")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Capacidade ride-sharing excedida")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
        
        return iniciou

    def _processar_pedido(self, pedido):
        """Processa um pedido individual no modo temporal."""
        horario_log = self.tempo_simulacao.strftime('%H:%M:%S')
        self._log(f"\n {horario_log} - [cyan]Processando Pedido #{pedido.id}[/]")
  
        # 1. Pré-calcular e validar rota do pedido (origem -> destino)
        rota_viagem, distancia_viagem, origem_nome, destino_nome = self._validar_rota_pedido(pedido)
        if rota_viagem is None:
            return

        # 2. Escolher veículo
        veiculo = self._escolher_veiculo_para_pedido(pedido, rota_viagem, distancia_viagem)
        if veiculo is None:
            return

        self._log(f"  [green][/] Veículo alocado: {veiculo.id_veiculo}")
        self.ambiente.atribuir_pedido_a_veiculo(pedido, veiculo)

        # 3. Ajustar rotas para ride-sharing se necessário 
        # #TODO rever porque o alocador se o veiculo tiver viagens já so verifica se la passa, 
        # e depois ao fazer este ajusto pode ficar mais custoso o veiculo escolhido do que outro que tivesse uma parte do percurso igual
        ajuste_ridesharing = self._ajustar_rotas_ridesharing(veiculo, origem_nome, destino_nome)
        if ajuste_ridesharing:
            rota_viagem, distancia_viagem = ajuste_ridesharing

        # 4. Recuperar rota veículo -> cliente
        rota_ate_cliente = veiculo.rota_ate_cliente
        distancia_ate_cliente = veiculo.distancia_ate_cliente
        distancia_total = distancia_ate_cliente + distancia_viagem

        # 5. Calcular métricas
        metricas_viagem = self._calcular_metricas_viagem(rota_ate_cliente, rota_viagem, veiculo, distancia_viagem)
        
        # 6. Log informações
        self.logger.info_viagem(rota_ate_cliente, rota_viagem, distancia_total, metricas_viagem)

        # 7. Iniciar viagem
        if not self._iniciar_viagem_pedido(veiculo, pedido, rota_ate_cliente, rota_viagem, distancia_ate_cliente, distancia_viagem):
            return

        self.viagens_ativas[veiculo.id_veiculo] = veiculo

        # 8. Registar métricas
        self.metricas.registar_pedido_atendido(
            pedido_id=pedido.id,
            veiculo_id=veiculo.id_veiculo,
            tempo_resposta=metricas_viagem['tempo_ate_cliente'],
            distancia=distancia_viagem,
            custo=metricas_viagem['custo'],
            emissoes=metricas_viagem['emissoes']
        )

        self._log(f"  [green][/] Viagem iniciada - ETA: {metricas_viagem['tempo_ate_cliente'] + metricas_viagem['tempo_viagem']:.1f} min")

        # 9. Atualizar displays #TODO: atualizar display para soportar ryde-sharing
        if self.display:
            nova_viagem_rota = veiculo.viagens[-1].rota if veiculo.viagens else []
            self.display.atualizar(pedido, veiculo, nova_viagem_rota)
    
    def _iniciar_recarga(self, veiculo):
        """Processa o início de recarga/abastecimento de um veículo.
        
        Args:
            veiculo: Veículo a reabastecer
        """
        # Verificar se está num posto adequado
        #NOTA: isto está a ser verificado antes de chamar esta função, ou seja, se não estiver num posto adequado, nem devia chegar aqui
        #decidir se é para deixar ou não esta verificação aqui, diria para verificar aqui assim, nao tinhna que verificar la em cima
        if not veiculo.pode_reabastecer_em(veiculo.localizacao_atual, self.ambiente.grafo):
            tipo_posto = veiculo.tipo_posto_necessario()
            self._log(f"  [red]✗[/] Veículo {veiculo.id_veiculo} não está num {tipo_posto.name}. Localização: {veiculo.localizacao_atual}")
            return
        
        veiculo.iniciar_recarga(self.tempo_simulacao, veiculo.localizacao_atual)
        
        # Calcular tempo de recarga
        tempo_recarga_minutos = veiculo.tempoReabastecimento()
        tempo_fim_recarga = self.tempo_simulacao + timedelta(minutes=tempo_recarga_minutos)
        
        self._log(f"[INFO] Veículo {veiculo.id_veiculo} iniciou recarga em {veiculo.localizacao_abastecimento}")
        self._log(f"    Tempo estimado: {tempo_recarga_minutos:.1f} min | Fim previsto: {tempo_fim_recarga.strftime('%H:%M:%S')}")
        
        # Agendar fim da recarga
        self.gestor_eventos.agendar_evento(
            tempo=tempo_fim_recarga,
            tipo=TipoEvento.FIM_RECARGA,
            callback=self._finalizar_recarga,
            dados={'veiculo': veiculo, 'tempo_recarga': tempo_recarga_minutos},
            prioridade=5
        )
    
    def _finalizar_recarga(self, veiculo, tempo_recarga: float):
        """Processa o fim de recarga/abastecimento de um veículo.
        
        Args:
            veiculo: Veículo que terminou a recarga
            tempo_recarga: Tempo gasto em recarga (minutos)
        """
        autonomia_anterior = veiculo.autonomia_atual
        autonomia_recarregada = self.ambiente.executar_recarga(veiculo)
        
        self._log(f"[green]OK[/] Veículo {veiculo.id_veiculo} terminou recarga")
        self._log(f"    Autonomia: {autonomia_anterior} km -> {veiculo.autonomia_atual} km ({veiculo.percentual_autonomia_atual:.1f}%)")
        
        self.metricas.registar_recarga(
            veiculo_id=veiculo.id_veiculo,
            tempo_recarga=tempo_recarga,
            autonomia_recarregada=autonomia_recarregada,
            localizacao=veiculo.localizacao_atual
        )
        
        # Remover veículo de viagens_ativas se não tiver mais viagens
        if not veiculo.viagem_ativa and veiculo.id_veiculo in self.viagens_ativas:
            del self.viagens_ativas[veiculo.id_veiculo]
