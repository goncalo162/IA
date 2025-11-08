import sys
import os
import threading
from datetime import datetime

# Garantir que o root do projecto está no path para imports relativos funcionarem
src_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(src_dir)
# garantir src e project root no path (origem de imports locais)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infra.grafo import Grafo
from infra.gestaoAmbiente import GestaoFrota
from infra.entidades.pedidos import Pedido
from infra.entidades.veiculos import VeiculoCombustao, VeiculoEletrico
from display.display import run_combined


def start_display(grafo, algoritmo):
    # run_combined bloqueia (Textual) — executá-lo numa thread para o main continuar
    run_combined(grafo, algoritmo)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 src/main.py <graph.json> <algorithm: bfs|dfs>")
        sys.exit(1)

    graph_path = sys.argv[1]
    algoritmo = sys.argv[2].lower()

    if not os.path.exists(graph_path):
        print(f"Ficheiro de grafo '{graph_path}' não encontrado")
        sys.exit(1)

    if algoritmo not in ("bfs", "dfs"):
        print("Algoritmo deve ser 'bfs' ou 'dfs'")
        sys.exit(1)

    try:
        grafo = Grafo.from_json_file(graph_path)
        print(f"Grafo carregado a partir de {graph_path}")
    except Exception as e:
        print(f"Falha ao carregar o grafo: {e}")
        sys.exit(1)

    # Instanciar gestor de frota
    gestor = GestaoFrota()

    # Adicionar alguns veículos de exemplo
    v1 = VeiculoCombustao(1, 500, 500, 4, 0, 0.12)
    v2 = VeiculoEletrico(2, 250, 250, 4, tempo_recarga_km=1, numero_passageiros=0, custo_operacional_km=0.05)
    gestor.adicionar_veiculo(v1)
    gestor.adicionar_veiculo(v2)

    # Iniciar display numa thread
    t = threading.Thread(target=start_display, args=(grafo, algoritmo), daemon=True)
    t.start()



if __name__ == '__main__':
    main()
