import sys
import os
import threading
from datetime import datetime

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algoritmos.algoritmos_alocacao import AlocadorSimples
from algoritmos.algoritmos_navegacao import NavegadorBFS, NavegadorDFS
from infra.simulador import Simulador
from display.display import DisplayGrafico

DURACAO_HORAS_DEFAULT = 8.0
FREQUENCIA_CALCULO_DEFAULT = 10.0
FREQUENCIA_DISPLAY_DEFAULT = 10.0
VELOCIDADE_SIMULACAO_DEFAULT = 1.0


def main():
    if len(sys.argv) < 5:
        print("Uso: python src/main.py <grafo.json> <veiculos.json> <pedidos.json> <algoritmo> [velocidade] [--no-display]")
        sys.exit(1)

    caminho_grafo, caminho_veiculos, caminho_pedidos, algoritmo_navegacao = sys.argv[1:5]
    no_display = '--no-display' in sys.argv

    velocidade_display = VELOCIDADE_SIMULACAO_DEFAULT
    for arg in sys.argv[5:]:
        if arg != '--no-display':
            try:
                velocidade_display = float(arg)
            except ValueError:
                pass

    if not no_display:
        display = DisplayGrafico(frequencia_display=FREQUENCIA_DISPLAY_DEFAULT)
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

    simulador.carregar_dados(caminho_grafo, caminho_veiculos, caminho_pedidos)

    # 🚀 Se o display estiver ativo, o simulador corre numa thread secundária
    if display is not None:
        print("[Main] Iniciando simulador em thread separada...")
        sim_thread = threading.Thread(
            target=lambda: simulador.iniciar_com_display(duracao_horas=velocidade_display),
            daemon=True,
            name="SimuladorThread"
        )
        sim_thread.start()

        # O display deve correr na thread principal
        print("[Main] Iniciando interface gráfica (Tkinter na main thread)...")
        display.iniciar(simulador.ambiente)
    else:
        # Modo sem display: corre tudo na thread principal
        simulador.iniciar_com_display(duracao_horas=velocidade_display)


if __name__ == '__main__':
    main()