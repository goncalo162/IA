"""
Sistema de logging para a simulação.
Centraliza toda a lógica de escrita de logs.
"""
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
# Constante: velocidade máxima com sincronização em tempo real
VELOCIDADE_MAXIMA_SINCRONIZADA = float(os.getenv('VELOCIDADE_MAXIMA_SINCRONIZADA', 100.0))


class SimuladorLogger:
    """Classe responsável por gerir logs da simulação."""
    
    def __init__(self, project_root: str = None):
        """Inicializa o logger.
        
        Args:
            project_root: Caminho raiz do projeto. Se None, usa o diretório atual.
        """
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))
        
        self.project_root = project_root
        self.log_ficheiro = None
        self.run_timestamp = None
        self._configurar_logging()
    
    def _configurar_logging(self):
        """Configura sistema de logging com timestamp para ficheiro."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.join(self.project_root, 'runs', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        self.log_ficheiro = os.path.join(log_dir, f'run_{timestamp}.log')
        self.run_timestamp = timestamp

        with open(self.log_ficheiro, 'w', encoding='utf-8') as f:
            f.write(f"=== SIMULAÇÃO DE GESTÃO DE FROTA ===\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
    
    def log(self, mensagem: str):
        """Escreve mensagem no log.
        
        Args:
            mensagem: Mensagem a ser escrita no log
        """
        with open(self.log_ficheiro, 'a', encoding='utf-8') as f:
            f.write(mensagem + '\n')
    
    def log_separador(self, caractere: str = "=", tamanho: int = 60):
        """Escreve um separador no log.
        
        Args:
            caractere: Caractere a usar no separador
            tamanho: Tamanho do separador
        """
        self.log(caractere * tamanho)
    
    def log_secao(self, titulo: str):
        """Escreve uma seção no log com separadores.
        
        Args:
            titulo: Título da seção
        """
        self.log("\n" + "="*60)
        self.log(titulo)
        self.log("="*60)
    
    def get_caminho_log(self) -> str:
        """Retorna o caminho do ficheiro de log."""
        return self.log_ficheiro
    
    def dados_carregados(self, num_nos: int, num_veiculos: int, num_pedidos: int, num_eventos: int = 0):
        """Registra no log os dados carregados.
        
        Args:
            num_nos: Número de nós carregados
            num_veiculos: Número de veículos carregados
            num_pedidos: Número de pedidos carregados
            num_eventos: Número de eventos carregados (opcional)
        """
        self.log("Dados carregados com sucesso!")
        self.log(f"- Número de nós no grafo: {num_nos}")
        self.log(f"- Número de veículos: {num_veiculos}")
        self.log(f"- Número de pedidos: {num_pedidos}")
        if num_eventos > 0:
            self.log(f"-  Número de eventos: {num_eventos}") #NOTA: não sei se depois tivermos mais tipos de eventos querem separá-los
        self.log_separador()

    def simulacao_iniciada(self, duracao_horas: float, inicio: datetime, velocidade_simulacao: float, frequencia_calculo: float, passo_tempo: timedelta):
        """Registra no log o início da simulação.
        
        Args:
            duracao_horas: Duração total da simulação em horas
        """

        self.log_secao("INÍCIO DA SIMULAÇÃO")
        self.log(f"Tempo inicial: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Duração: {duracao_horas} horas")
        self.log(f"Velocidade de simulação: {velocidade_simulacao}x")

        if velocidade_simulacao > VELOCIDADE_MAXIMA_SINCRONIZADA:
            self.log(f" MODO TURBO ATIVADO: Velocidade > {VELOCIDADE_MAXIMA_SINCRONIZADA}x")

        self.log(f"Frequência de cálculo: {frequencia_calculo} Hz")
        self.log(f"Passo temporal simulado: {passo_tempo.total_seconds()} segundos")
        self.log_separador()

    def simulacao_concluida(self, fim: datetime):
        self.log_secao("SIMULAÇÃO CONCLUÍDA")
        self.log(f"Tempo final: {fim.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_separador()

    def info_viagem(self, rota_ate_cliente, rota_viagem, distancia_total, metricas_viagem):
        """Loga informações da viagem."""
        self.log(f"  [green][/] Rota veículo->cliente: {' → '.join(rota_ate_cliente)}")
        self.log(f"  [green][/] Rota cliente->destino: {' → '.join(rota_viagem)}")
        self.log(f"    Distância: {distancia_total:.2f} km ({metricas_viagem['tempo_ate_cliente'] + metricas_viagem['tempo_viagem']:.1f} min)")
        self.log(f"    Custo: €{metricas_viagem['custo']:.2f} |  Emissões: {metricas_viagem['emissoes']:.2f} kg CO₂")
        