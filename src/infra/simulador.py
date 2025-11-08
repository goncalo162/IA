"""
Motor principal da simulação.
Coordena ambiente, algoritmos, métricas e display.
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import os
import sys
import time

from infra.gestaoAmbiente import GestaoAmbiente
from infra.metricas import Metricas
from infra.evento import GestorEventos, TipoEvento
from infra.entidades.veiculos import EstadoVeiculo

# Constante: velocidade máxima com sincronização em tempo real
# Acima deste valor, a simulação executa o mais rápido possível sem esperar
VELOCIDADE_MAXIMA_SINCRONIZADA = 100.0


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
        
        Args:
            alocador: Instância de AlocadorBase para escolher veículos
            navegador: Instância de NavegadorBase para calcular rotas
            display: Instância opcional de Display para visualização
            tempo_inicial: Tempo inicial da simulação (padrão: agora)
            frequencia_calculo: Quantas vezes os cálculos são feitos por segundo real (Hz)
            velocidade_simulacao: Velocidade com que é mostrada a simulação relativa ao tempo real (1.0 = tempo real)
        """
        self.alocador = alocador
        self.navegador = navegador
        self.display = display
        
        self.ambiente = GestaoAmbiente()
        self.metricas = Metricas()
        self.gestor_eventos = GestorEventos()
        
        self.tempo_simulacao = tempo_inicial or datetime.now()
        self.velocidade_simulacao = velocidade_simulacao
        self.frequencia_calculo = frequencia_calculo
        # Calcular o passo de tempo simulado: velocidade_simulacao / frequencia_calculo
        # Ex: 1.0x / 10Hz = 0.1s simulado por atualização; 10.0x / 10Hz = 1.0s simulado por atualização
        self.passo_tempo = timedelta(seconds=velocidade_simulacao / frequencia_calculo)
        
        self.em_execucao = False
        self.viagens_ativas: Dict = {}  # veiculo_id -> Veiculo (em viagem)
        self.pedidos_agendados = []  # Lista de pedidos a processar
        
        # Configurar logging com timestamp
        self._configurar_logging()
    
    def _configurar_logging(self):
        """Configura sistema de logging com timestamp para ficheiro."""
        # Criar timestamp para esta run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Definir caminho do ficheiro de log
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(project_root, 'runs', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_ficheiro = os.path.join(log_dir, f'run_{timestamp}.log')
        self.run_timestamp = timestamp
        
        # Criar ficheiro de log
        with open(self.log_ficheiro, 'w', encoding='utf-8') as f:
            f.write(f"=== SIMULAÇÃO DE GESTÃO DE FROTA ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
    
    def _log(self, mensagem: str):
        """Escreve mensagem no log e no stdout."""
        # Escrever em stdout
        print(mensagem)  #TODO: tirar daqui e meter a imprimir no display

        # Escrever no ficheiro de log para mantermos as informações mesmo depois de acabar a simulação
        with open(self.log_ficheiro, 'a', encoding='utf-8') as f:
            f.write(mensagem + '\n')
    
    def carregar_dados(self, caminho_grafo: str, caminho_veiculos: str, 
                      caminho_pedidos: str):
        """
        Carrega todos os dados necessários para a simulação.
        
        Args:
            caminho_grafo: Caminho para o ficheiro JSON do grafo
            caminho_veiculos: Caminho para o ficheiro JSON dos veículos
            caminho_pedidos: Caminho para o ficheiro JSON dos pedidos
        """
        self._log(f"A carregar grafo de {caminho_grafo}...")
        self.ambiente.carregar_grafo(caminho_grafo)
        
        self._log(f"A carregar veículos de {caminho_veiculos}...")
        self.ambiente.carregar_veiculos(caminho_veiculos)
        
        self._log(f"A carregar pedidos de {caminho_pedidos}...")
        self.ambiente.carregar_pedidos(caminho_pedidos)

        #TODO: falta carregar eventos
        
        self._log("Dados carregados com sucesso!")
        self._log(f"  - Veículos: {len(self.ambiente.listar_veiculos())}")
        self._log(f"  - Pedidos: {len(self.ambiente.listar_pedidos())}")
    
    def executar(self, duracao_horas: float = 8.0):
        """
        Executa a simulação temporal.
        Pedidos chegam conforme horario_pretendido, veículos movem-se ao longo do tempo.
        
        Args:
            duracao_horas: Duração da simulação em horas
        """
        self.em_execucao = True
        tempo_final = self.tempo_simulacao + timedelta(hours=duracao_horas)
        
        self._log("\n" + "="*60)
        self._log("INICIANDO SIMULAÇÃO TEMPORAL")
        self._log("="*60)
        self._log(f"Tempo inicial: {self.tempo_simulacao.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Duração: {duracao_horas} horas")
        self._log(f"Velocidade de simulação: {self.velocidade_simulacao}x")
        
        if self.velocidade_simulacao > VELOCIDADE_MAXIMA_SINCRONIZADA:
            self._log(f"⚡ MODO TURBO ATIVADO: Velocidade > {VELOCIDADE_MAXIMA_SINCRONIZADA}x")
            self._log(f"   → Execução máxima sem sincronização temporal")
        
        self._log(f"Frequência de cálculo: {self.frequencia_calculo} Hz")
        self._log(f"Passo temporal simulado: {self.passo_tempo.total_seconds()} segundos")
        self._log("="*60 + "\n")
        
        if self.display:
            self.display.iniciar(self.ambiente)
        
        # Agendar chegada de todos os pedidos
        self._agendar_pedidos()
        
        # Loop principal da simulação
        tempo_inicio_real = time.time()  # Tempo real de início
        tempo_decorrido_simulacao = timedelta(0)  # Tempo simulado decorrido


        
        while self.tempo_simulacao < tempo_final and self.em_execucao:
            # 1. Processar eventos agendados até o tempo atual
            #TODO: até agora nao há nenhum sitio onde adicione os eventos, falta fazer isso, sugeria ler os eventos de um ficheiro, para depois ser mais facil analisar o que acontece conforme os eventos acontecidos
            self.gestor_eventos.processar_eventos_ate(self.tempo_simulacao)
            
            # 2. Atualizar viagens ativas
            self._atualizar_viagens_ativas()
            
            # 3. Atualizar eventos dinâmicos (trânsito, falhas, etc.)
            self.gestor_eventos.atualizar(self.tempo_simulacao)
            
            # 4. Atualizar display animado (se disponível)
            if self.display and hasattr(self.display, 'atualizar_tempo_simulacao'):
                self.display.atualizar_tempo_simulacao(self.tempo_simulacao, self.viagens_ativas) #NOTA: adaptar display a isto
            
            # 5. Sincronizar com tempo real (apenas para velocidades moderadas)
            # Para velocidades > VELOCIDADE_MAXIMA_SINCRONIZADA, executa o mais rápido possível
            if self.velocidade_simulacao <= VELOCIDADE_MAXIMA_SINCRONIZADA:
                tempo_decorrido_simulacao += self.passo_tempo
                tempo_esperado_real = tempo_decorrido_simulacao.total_seconds() / self.velocidade_simulacao
                tempo_decorrido_real = time.time() - tempo_inicio_real
                tempo_espera = tempo_esperado_real - tempo_decorrido_real
                
                if tempo_espera > 0:
                    time.sleep(tempo_espera)
            
            # 6. Avançar tempo
            self.tempo_simulacao += self.passo_tempo
        
        # Finalizar simulação
        self.em_execucao = False
        self._log("\n" + "="*60)
        self._log("SIMULAÇÃO CONCLUÍDA")
        self._log("="*60)
        self._log(f"Tempo final: {self.tempo_simulacao.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Pedidos processados: {self.metricas.pedidos_atendidos}")
        self._log(f"Pedidos rejeitados: {self.metricas.pedidos_rejeitados}")
        self._log("="*60 + "\n")
        
        # Gerar relatório de métricas
        self._log(self.metricas.gerar_relatorio())
        
        # Exportar estatísticas para CSV
        self._exportar_estatisticas()
        
        if self.display:
            self.display.finalizar()
    
    def _exportar_estatisticas(self):
        """Exporta as métricas para CSV cumulativo."""
        # Definir caminho do ficheiro CSV
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_ficheiro = os.path.join(project_root, 'runs', 'stats', 'statistics.csv')
        
        # Preparar configuração da run
        config = {
            'navegador': self.navegador.nome_algoritmo(),
            'alocador': self.alocador.__class__.__name__,
            'velocidade': self.velocidade_simulacao
        }
        
        # Exportar para CSV
        self.metricas.exportar_csv(csv_ficheiro, config)
        
        self._log(f"\n✓ Estatísticas exportadas para: {csv_ficheiro}")
        self._log(f"✓ Log da simulação guardado em: {self.log_ficheiro}")
    
    def _agendar_pedidos(self):
        """Agenda todos os pedidos para chegarem no horário pretendido."""
        pedidos_pendentes = self.ambiente.listar_pedidos_pendentes()
        self._log(f"Agendando {len(pedidos_pendentes)} pedidos...")
        
        for pedido in pedidos_pendentes:
            # Agendar evento de chegada do pedido
            self.gestor_eventos.agendar_evento(
                tempo=pedido.horario_pretendido,
                tipo=TipoEvento.CHEGADA_PEDIDO,
                callback=self._processar_pedido,
                dados={'pedido': pedido}
            )
        
        self._log(f"✓ {len(pedidos_pendentes)} pedidos agendados\n")
    
    def _atualizar_viagens_ativas(self):
        """Atualiza o progresso de todas as viagens em curso."""
        if not self.viagens_ativas:
            return
        
        # Calcular tempo decorrido neste passo (em horas)
        tempo_passo_horas = self.passo_tempo.total_seconds() / 3600
        
        viagens_concluidas = []
        
        for veiculo_id, veiculo in self.viagens_ativas.items():
            # Atualizar progresso baseado no tempo (o veículo tem os métodos de viagem)
            concluiu = veiculo.atualizar_progresso_viagem(tempo_passo_horas)
            
            if concluiu:
                viagens_concluidas.append((veiculo_id, veiculo))
        
        # Processar viagens concluídas
        for veiculo_id, veiculo in viagens_concluidas:
            self._concluir_viagem(veiculo_id, veiculo)
            del self.viagens_ativas[veiculo_id]
    
    def _concluir_viagem(self, veiculo_id: str, veiculo):
        """Processa a conclusão de uma viagem."""
        # Guardar pedido_id antes de limpar
        pedido_id = veiculo.pedido_id
        
        # Atualizar localização do veículo para o destino (usar nome para consistência)
        destino_nome = veiculo.destino
        veiculo.localizacao_atual = destino_nome
        veiculo.estado = EstadoVeiculo.DISPONIVEL
        veiculo.concluir_viagem()
        
        print(f"   Viagem concluída: Pedido #{pedido_id}")
        print(f"      Veículo {veiculo_id} agora em {destino_nome}")

    def _processar_pedido(self, pedido):
        """
        Processa um pedido individual no modo temporal.
        Aloca veículo, calcula rota, inicia viagem.
        """
        print(f"\n {self.tempo_simulacao.strftime('%H:%M:%S')} - Processando {pedido}")
        
        # 1. Escolher veículo usando o algoritmo de alocação
        veiculo = self.alocador.escolher_veiculo(
            pedido=pedido,
            veiculos_disponiveis=self.ambiente.listar_veiculos_disponiveis(),
            grafo=self.ambiente.grafo
        )
        
        if veiculo is None:
            print(f"  Nenhum veículo disponível para o pedido #{pedido.id}")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Sem veículos disponíveis")
            if self.display and hasattr(self.display, 'registrar_rejeicao'):
                self.display.registrar_rejeicao()
            return
        
        print(f"  ✓ Veículo alocado: {veiculo.id_veiculo}")
        
        # 2. Calcular rota da localização atual do veículo até o cliente
        # localizacao_atual pode ser nome (string) ou ID (int)
        if isinstance(veiculo.localizacao_atual, str):
            origem_veiculo_nome = veiculo.localizacao_atual
        else:
            origem_veiculo_nome = self.ambiente.grafo.getNodeName(veiculo.localizacao_atual)
        
        origem_pedido_nome = self.ambiente.grafo.getNodeName(pedido.origem)
        destino_nome = self.ambiente.grafo.getNodeName(pedido.destino)
        
        # Rota 1: Veículo -> Cliente
        rota_ate_cliente = self.navegador.calcular_rota(
            grafo=self.ambiente.grafo,
            origem=origem_veiculo_nome,
            destino=origem_pedido_nome
        )
        
        if rota_ate_cliente is None:
            print(f"  Não foi possível calcular rota até o cliente")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Rota até cliente não encontrada")
            return
        
        # Rota 2: Cliente -> Destino
        rota_viagem = self.navegador.calcular_rota(
            grafo=self.ambiente.grafo,
            origem=origem_pedido_nome,
            destino=destino_nome
        )
        
        if rota_viagem is None:
            print(f"  Não foi possível calcular rota")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Rota não encontrada")
            return
        
        # Rota completa: Veículo -> Cliente -> Destino
        rota_completa = rota_ate_cliente + rota_viagem[1:]  # Remove duplicação do nó cliente
        print(f"  ✓ Rota calculada: {' → '.join(rota_completa)}")
        
        # 3. Calcular métricas da viagem
        distancia_ate_cliente = self._calcular_distancia_rota(rota_ate_cliente)
        distancia_viagem = self._calcular_distancia_rota(rota_viagem)
        distancia_total = distancia_ate_cliente + distancia_viagem
        
        # Usar tempo real baseado nas velocidades das arestas
        tempo_ate_cliente = self._calcular_tempo_rota(rota_ate_cliente) * 60  # converter para minutos
        tempo_viagem = self._calcular_tempo_rota(rota_viagem) * 60  # converter para minutos
        
        custo = distancia_viagem * veiculo.custo_operacional_km
        emissoes = self._calcular_emissoes(veiculo, distancia_viagem)
        
        print(f"   Distância até cliente: {distancia_ate_cliente:.2f} km ({tempo_ate_cliente:.1f} min)")
        print(f"   Distância da viagem: {distancia_viagem:.2f} km ({tempo_viagem:.1f} min)")
        print(f"   Custo: €{custo:.2f}")
        print(f"   Emissões: {emissoes:.2f} kg CO₂")
        
        # 4. Verificar autonomia. 
        #TODO: em vez de rejeitar por ser insuficiente, podiamos recalcular tendo em conta o abastecimento.
        if veiculo.autonomia_atual < distancia_total:
            print(f"   Autonomia insuficiente ({veiculo.autonomia_atual} km < {distancia_total} km)")
            self.metricas.registar_pedido_rejeitado(pedido.id, "Autonomia insuficiente")
            return
        

        #TODO: meter esta logica de iniciar viagem do veiculo a passar pela gestao de ambiente em vez de estar aqui a ocupar espaço

        # 5. Iniciar viagem no veículo
        veiculo.estado = EstadoVeiculo.EM_ANDAMENTO
        pedido.estado = pedido._estado.__class__.EM_CURSO
        veiculo.atualizar_autonomia(int(distancia_total))
        
        # Iniciar viagem diretamente no veículo
        veiculo.iniciar_viagem(
            pedido_id=pedido.id,
            rota=rota_completa,
            distancia_total=distancia_total,
            tempo_inicio=self.tempo_simulacao,
            grafo=self.ambiente.grafo
        )
        
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
        
        print(f"  Viagem iniciada - ETA: {tempo_ate_cliente + tempo_viagem:.1f} minutos")
        
        if self.display:
            self.display.atualizar(pedido, veiculo, rota_completa)
    

##TODO: organizar melhor

    def _calcular_distancia_rota(self, rota) -> float:
        """Calcula a distância total de uma rota."""
        if len(rota) < 2:
            return 0.0
        
        distancia_total = 0.0
        for i in range(len(rota) - 1):
            aresta = self.ambiente.grafo.getEdge(rota[i], rota[i + 1])
            if aresta:
                distancia_total += aresta.getQuilometro()
        
        return distancia_total
    
    def _calcular_tempo_rota(self, rota) -> float:
        """
        Calcula o tempo total para percorrer uma rota em horas.
        Usa a velocidade máxima de cada aresta e considera o trânsito.
        """
        if len(rota) < 2:
            return 0.0
        
        tempo_total_horas = 0.0
        for i in range(len(rota) - 1):
            aresta = self.ambiente.grafo.getEdge(rota[i], rota[i + 1])
            if aresta:
                tempo_segmento = aresta.getTempoPercorrer()
                if tempo_segmento is None:
                    raise ValueError(
                        f"Aresta {rota[i]} -> {rota[i+1]} não tem informação de tempo. "
                        "Verifique se o grafo está corretamente carregado."
                    )
                tempo_total_horas += tempo_segmento
        
        return tempo_total_horas
    
    def _calcular_emissoes(self, veiculo, distancia: float) -> float:
        """
        Calcula as emissões de CO₂ de uma viagem.
        Veículos elétricos: 0 kg CO₂
        Veículos a combustão: ~0.12 kg CO₂/km (média)
        """
        from infra.entidades.veiculos import VeiculoEletrico
        
        if isinstance(veiculo, VeiculoEletrico):
            return 0.0
        else:
            return distancia * 0.12  # kg CO₂ por km
