from display.tentativaDisplay import DisplayGrafico
from infra.simulador import Simulador
from algoritmos.algoritmos_navegacao import NavegadorBFS, NavegadorCustoUniforme, NavegadorDFS
from algoritmos.algoritmos_alocacao import AlocadorHeuristico, AlocadorSimples

from datetime import datetime
from dotenv import load_dotenv
import sys
import os

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregar variáveis de ambiente do ficheiro .env
load_dotenv()

# Carregar configurações do .env com valores default
DURACAO_HORAS_DEFAULT = float(os.getenv('DURACAO_HORAS', 8.0))
FREQUENCIA_CALCULO_DEFAULT = float(os.getenv('FREQUENCIA_CALCULO', 1.0))
FREQUENCIA_DISPLAY_DEFAULT = float(os.getenv('FREQUENCIA_DISPLAY', 10.0))
VELOCIDADE_SIMULACAO_DEFAULT = float(os.getenv('VELOCIDADE_SIMULACAO', 1.0))


def main():

    #TODO: REVER porque se calhar nao vale a pena passar argumentos por linha de comando apenas no .env, fica mais limpo e parametrizado
    # Verificar se foram passados argumentos via linha de comando ou usar .env
    if len(sys.argv) >= 6:
        caminho_grafo, caminho_veiculos, caminho_pedidos, algoritmo_navegacao, algoritmo_alocacao = sys.argv[1:6]
    elif len(sys.argv) == 1:
        # Usar valores do .env
        caminho_grafo = os.getenv('CAMINHO_GRAFO', 'dataset/grafo.json')
        caminho_veiculos = os.getenv('CAMINHO_VEICULOS', 'dataset/veiculos.json')
        caminho_pedidos = os.getenv('CAMINHO_PEDIDOS', 'dataset/pedidos.json')
        algoritmo_navegacao = os.getenv('ALGORITMO_NAVEGACAO', 'bfs')
        algoritmo_alocacao = os.getenv('ALGORITMO_ALOCACAO', 'simples')
    else:
        print(
            "Uso: python src/main.py <grafo.json> <veiculos.json> <pedidos.json> <algoritmo_nav> <algoritmo_aloc> [velocidade] [--no-display]")
        print("Ou configure as variáveis no ficheiro .env e execute sem argumentos.")
        sys.exit(1)

    # Verificar primeiro o .env para display
    display_env = os.getenv('MOSTRAR_DISPLAY', 'true').lower()
    no_display = display_env in ('false', '0', 'no', 'off')
    
    # Linha de comando pode sobrepor (--no-display força sem display)
    if '--no-display' in sys.argv:
        no_display = True

    # Velocidade de visualização (opcional - linha de comando ou .env)
    velocidade_display = VELOCIDADE_SIMULACAO_DEFAULT
    for arg in sys.argv[5:]:
        if arg != '--no-display':
            try:
                velocidade_display = float(arg)
            except ValueError:
                pass

    if not no_display:
        display = DisplayGrafico(frequencia_display=FREQUENCIA_DISPLAY_DEFAULT)
        display.set_velocidade_simulacao(velocidade_display)
    else:
        display = None
        print("Modo sem display ativado (execução mais rápida)")

    navegadores = {
        "bfs": NavegadorBFS(),
        "dfs": NavegadorDFS(),
        "ucs": NavegadorCustoUniforme(),
    }

    if algoritmo_navegacao not in navegadores:
        print("Algoritmo inválido. Use 'bfs', 'dfs' ou 'ucs'.")
        sys.exit(1)

    navegador = navegadores[algoritmo_navegacao]
    
    alocadores = {
        "Heuristico": AlocadorHeuristico(navegador),
        "simples": AlocadorSimples(navegador),
    }


    if algoritmo_alocacao not in alocadores:
        print("Algoritmo inválido. Use 'heuristico', 'simples'.")
        sys.exit(1)

    alocador = alocadores[algoritmo_alocacao]

    tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
    simulador = Simulador(
        alocador= alocador,
        navegador=navegador,
        display=display,
        tempo_inicial=tempo_inicial,
        frequencia_calculo=FREQUENCIA_CALCULO_DEFAULT,
        velocidade_simulacao=velocidade_display
    )

    if display is not None:
        display.set_metricas(simulador.metricas)

    simulador.carregar_dados(caminho_grafo, caminho_veiculos, caminho_pedidos)
    simulador.executar(duracao_horas=DURACAO_HORAS_DEFAULT)


if __name__ == '__main__':
    main()
