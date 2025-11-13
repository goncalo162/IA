import sys
import os

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime

from algoritmos.algoritmos_alocacao import AlocadorSimples
from algoritmos.algoritmos_navegacao import NavegadorBFS, NavegadorDFS
from infra.simulador import Simulador
from display.tentativaDisplay import DisplayGrafico

DURACAO_HORAS_DEFAULT = 8.0
FREQUENCIA_CALCULO_DEFAULT = 1.0
FREQUENCIA_DISPLAY_DEFAULT = 10.0
VELOCIDADE_SIMULACAO_DEFAULT = 1.0


def main():
    if len(sys.argv) < 5:
        print("Uso: python src/main.py <grafo.json> <veiculos.json> <pedidos.json> <algoritmo> [velocidade] [--no-display]")
        sys.exit(1)

    caminho_grafo, caminho_veiculos, caminho_pedidos, algoritmo_navegacao = sys.argv[1:5]
    no_display = '--no-display' in sys.argv

# Velocidade de visualização (opcional)
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
        "dfs": NavegadorDFS()
    }

    if algoritmo_navegacao not in navegadores:
        print("Algoritmo inválido. Use 'bfs' ou 'dfs'.")
        sys.exit(1)

    navegador = navegadores[algoritmo_navegacao]
    alocador = AlocadorSimples()

    tempo_inicial = datetime(2025, 1, 1, 8, 0, 0)
    simulador = Simulador(
        alocador=alocador,
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