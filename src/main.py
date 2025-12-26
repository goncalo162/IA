from display.tentativaDisplay import DisplayGrafico
from infra.simulador import Simulador
from config import Config
from datetime import datetime
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # Processar configurações
    config = Config.parse_args()
    
    # Configurar display
    display = None
    if not config['no_display']:
        display = DisplayGrafico(frequencia_display=Config.FREQUENCIA_DISPLAY)
        display.set_velocidade_simulacao(config['velocidade_display'])
    else:
        print("Modo sem display ativado (execução mais rápida)")
    
    # Obter navegador, alocador e políticas
    navegador = Config.get_navegador(config['algoritmo_navegacao'])
    alocador = Config.get_alocador(navegador, config['algoritmo_alocacao'])
    ride_sharing_policy = Config.get_ride_sharing_policy()
    recarga_policy = Config.get_recarga_policy()
    
    # Criar simulador
    tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
    simulador = Simulador(
        alocador=alocador,
        navegador=navegador,
        display=display,
        tempo_inicial=tempo_inicial,
        frequencia_calculo=Config.FREQUENCIA_CALCULO,
        velocidade_simulacao=config['velocidade_display'],
        ridesharing_policy=ride_sharing_policy,
        recarga_policy=recarga_policy
    )
    
    if display is not None:
        display.set_metricas(simulador.metricas)
    
    # Carregar dados e executar
    simulador.carregar_dados(
        config['caminho_grafo'],
        config['caminho_veiculos'],
        config['caminho_pedidos'],
        config['caminho_eventos_transito']
    )
    
    simulador.executar(duracao_horas=Config.DURACAO_HORAS)


if __name__ == '__main__':
    main()
