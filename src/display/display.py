from display.aplicacao.graph_viewer import AnimatedGraphApp
from display.aplicacao.dashboard_window import DashboardWindow

class DisplayGrafico:
    def __init__(self, frequencia_display: float = 10.0):
        import queue
        self.command_queue = queue.Queue()
        self.frequencia_display = frequencia_display
        self.viewer_app = None
        self.dashboard = None

    def iniciar(self, ambiente):
        """Inicia as duas janelas Tkinter na thread principal."""
        grafo = ambiente.grafo

        # Cria a janela principal (gráfico)
        self.viewer_app = AnimatedGraphApp(grafo, ambiente, self.command_queue)

        # Cria a segunda janela (painel de controlo)
        self.dashboard = DashboardWindow(self.command_queue)

        # Inicia o loop Tkinter (bloqueante)
        print("[DisplayGrafico] Iniciando Tkinter mainloop...")
        self.viewer_app.root.mainloop()

    def atualizar_tempo_simulacao(self, tempo_simulacao, viagens_ativas):
        self.command_queue.put({
            "type": "update_time",
            "tempo": tempo_simulacao,
            "viagens": viagens_ativas,
        })

    def atualizar(self, pedido, veiculo, rota):
        self.command_queue.put({
            "type": "new_trip",
            "pedido": pedido,
            "veiculo": veiculo,
            "rota": rota,
        })

    def registrar_rejeicao(self):
        self.command_queue.put({"type": "reject"})

    def finalizar(self):
        self.command_queue.put({"type": "close"})