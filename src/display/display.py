
import threading
import queue

import sys
import os

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.grafo import Grafo
from graph.algoritmos_procura import bfs, dfs
from terminal.textual_controller import GraphCarController
from aplicacao.graph_viewer import AnimatedGraphApp


def run_combined(grafo, algorithm):
    """Run the Tkinter graph viewer + Textual TUI controller together."""
    command_queue = queue.Queue()
    tk_thread = threading.Thread(
        target=lambda: AnimatedGraphApp(grafo, algorithm, command_queue).run(),
        daemon=True
    )
    tk_thread.start()
    GraphCarController(command_queue).run()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python display.py <graph.json> <algorithm: bfs|dfs>")
        sys.exit(1)

    graph_path = sys.argv[1]
    algorithm = sys.argv[2].lower()

    if not os.path.exists(graph_path):
        print(f"⚠️ Graph file '{graph_path}' not found.")
        sys.exit(1)

    if algorithm not in ["bfs", "dfs"]:
        print("⚠️ Algorithm must be 'bfs' or 'dfs'.")
        sys.exit(1)

    grafo = Grafo.from_json_file(graph_path)
    print(f"✅ Loaded graph from {graph_path}")

    run_combined(grafo, algorithm)