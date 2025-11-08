# filename: display/display.py
import threading
import queue
import sys
import os

# --- Path fix so imports work regardless of run location ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from display.aplicacao.graph_viewer import AnimatedGraphApp
from display.terminal.textual_controller import GraphCarController


class DisplayGrafico:
    """
    Launches both the Textual TUI and the graphical Tkinter+Matplotlib viewer.
    They communicate through a shared queue.
    """

    def __init__(self, frequencia_display: float = 10.0):
        self.command_queue = queue.Queue()
        self.frequencia_display = frequencia_display
        self.viewer_thread = None
        self.viewer_app = None
        self.tui_app = None

    # --------------------------------------------------------
    # Public API (called by simulator)
    # --------------------------------------------------------

    def iniciar(self, ambiente):
        """
        Starts the visualizer (in background thread) and then the Textual TUI (in main thread).
        """
        grafo = ambiente.grafo

        # Start the graphical viewer in background thread
        self.viewer_thread = threading.Thread(
            target=self._run_graphical_viewer, args=(grafo, ambiente), daemon=True
        )
        self.viewer_thread.start()

        # Run the Textual app in the main thread
        self._run_tui()

    def atualizar_tempo_simulacao(self, tempo_simulacao, viagens_ativas):
        """Queue an update_time command for the viewer."""
        self.command_queue.put({
            "type": "update_time",
            "tempo": tempo_simulacao,
            "viagens": viagens_ativas,
        })

    def atualizar(self, pedido, veiculo, rota):
        """Queue a new_trip command for the viewer."""
        self.command_queue.put({
            "type": "new_trip",
            "pedido": pedido,
            "veiculo": veiculo,
            "rota": rota,
        })

    def registrar_rejeicao(self):
        """Optional: inform the viewer about a rejected request."""
        self.command_queue.put({"type": "reject"})

    def finalizar(self):
        """Signal both interfaces to close."""
        self.command_queue.put({"type": "close"})
        if self.viewer_thread and self.viewer_thread.is_alive():
            self.viewer_thread.join(timeout=2.0)

    # --------------------------------------------------------
    # Internal
    # --------------------------------------------------------

    def _run_graphical_viewer(self, grafo, ambiente):
        """Run Tkinter+Matplotlib viewer (blocking, in its own thread)."""
        try:
            self.viewer_app = AnimatedGraphApp(grafo, ambiente, self.command_queue)
            self.viewer_app.run()
        except Exception as e:
            print(f"[DisplayGrafico] Viewer thread failed: {e}")

    def _run_tui(self):
        """Run the Textual TUI in the main thread (blocking until user quits)."""
        try:
            self.tui_app = GraphCarController(self.command_queue)
            self.tui_app.run()  # this blocks until exit
        except Exception as e:
            print(f"[DisplayGrafico] TUI error: {e}")
        finally:
            self.finalizar()


if __name__ == "__main__":
    raise RuntimeError("❌ Execute main.py instead of display.py directly.")