import tkinter as tk
from tkinter import ttk
from datetime import datetime
import queue


class DashboardWindow:
    """
    Segunda janela Tkinter para mostrar informações da simulação:
      - Tempo e estado
      - Métricas
      - Viagens ativas
      - Logs de eventos
    """

    def __init__(self, command_queue: queue.Queue):
        self.command_queue = command_queue

        # --- Criar janela ---
        self.root = tk.Toplevel()
        self.root.title("Simulação - Painel de Controlo")
        self.root.geometry("600x700")

        # --- Dados ---
        self.logs = []
        self.max_logs = 100
        self.tempo_simulacao = "--:--:--"
        self.viagens_ativas = {}
        self.pedidos_atendidos = 0
        self.pedidos_rejeitados = 0
        self.veiculos_disponiveis = 0

        # --- Layout principal ---
        self._criar_widgets()

        # --- Loop de atualização ---
        self.root.after(100, self._check_queue)
        self.root.after(500, self._atualizar_display)

    # --------------------------------------------------------
    #   Construção da interface
    # --------------------------------------------------------
    def _criar_widgets(self):
        """Cria todos os painéis principais."""

        # Painel de tempo
        frame_tempo = ttk.LabelFrame(self.root, text="⏱ Simulação")
        frame_tempo.pack(fill="x", padx=10, pady=5)
        self.lbl_tempo = ttk.Label(frame_tempo, text="Tempo: --:--:--")
        self.lbl_tempo.pack(anchor="w", padx=10, pady=2)
        self.lbl_viagens = ttk.Label(frame_tempo, text="Viagens ativas: 0")
        self.lbl_viagens.pack(anchor="w", padx=10, pady=2)
        self.lbl_veiculos = ttk.Label(frame_tempo, text="Veículos disponíveis: 0")
        self.lbl_veiculos.pack(anchor="w", padx=10, pady=2)

        # Painel de métricas
        frame_metricas = ttk.LabelFrame(self.root, text="📊 Métricas")
        frame_metricas.pack(fill="x", padx=10, pady=5)
        self.lbl_atendidos = ttk.Label(frame_metricas, text="Pedidos atendidos: 0")
        self.lbl_atendidos.pack(anchor="w", padx=10, pady=2)
        self.lbl_rejeitados = ttk.Label(frame_metricas, text="Pedidos rejeitados: 0")
        self.lbl_rejeitados.pack(anchor="w", padx=10, pady=2)
        self.lbl_taxa = ttk.Label(frame_metricas, text="Taxa de sucesso: 0.0%")
        self.lbl_taxa.pack(anchor="w", padx=10, pady=2)

        # Tabela de viagens ativas
        frame_tabela = ttk.LabelFrame(self.root, text="🚗 Viagens ativas")
        frame_tabela.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(
            frame_tabela,
            columns=(
                "veiculo",
                "pedido",
                "origem",
                "destino",
                "progresso"),
            show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # Logs
        frame_logs = ttk.LabelFrame(self.root, text="📝 Registos de eventos")
        frame_logs.pack(fill="both", expand=True, padx=10, pady=5)
        self.txt_logs = tk.Text(frame_logs, height=10, wrap="word", state="disabled")
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)

    # --------------------------------------------------------
    #   Atualização dinâmica
    # --------------------------------------------------------
    def _check_queue(self):
        """Lê a fila de mensagens do simulador."""
        try:
            while not self.command_queue.empty():
                msg = self.command_queue.get_nowait()
                self._processar_mensagem(msg)
        except Exception as e:
            self._adicionar_log(f"[ERRO] {e}")
        self.root.after(100, self._check_queue)

    def _processar_mensagem(self, msg):
        """Processa cada mensagem vinda do simulador."""
        tipo = msg.get("type")

        if tipo == "update_time":
            tempo = msg.get("tempo")
            viagens = msg.get("viagens", {})
            self.viagens_ativas = viagens
            if isinstance(tempo, datetime):
                self.tempo_simulacao = tempo.strftime("%H:%M:%S")
            else:
                self.tempo_simulacao = str(tempo)

        elif tipo == "new_trip":
            pedido = msg.get("pedido")
            veiculo = msg.get("veiculo")
            rota = msg.get("rota", [])
            if pedido and veiculo:
                origem = rota[0] if len(rota) > 0 else "?"
                destino = rota[-1] if len(rota) > 0 else "?"
                self._adicionar_log(
                    f"✓ Viagem iniciada: Veículo {
                        veiculo.id_veiculo} → Pedido #{
                        pedido.id} ({origem} → {destino})")

        elif tipo == "reject":
            self.pedidos_rejeitados += 1
            self._adicionar_log("⚠ Pedido rejeitado")

        elif tipo == "metrics":
            self.pedidos_atendidos = msg.get("atendidos", 0)
            self.pedidos_rejeitados = msg.get("rejeitados", 0)
            self.veiculos_disponiveis = msg.get("disponiveis", 0)

        elif tipo == "log":
            self._adicionar_log(msg.get("message", ""))

        elif tipo == "close":
            self._adicionar_log("Simulação finalizada.")
            self.root.after(1000, self.root.destroy)

    def _atualizar_display(self):
        """Atualiza todos os widgets."""
        # Atualizar texto
        self.lbl_tempo.config(text=f"Tempo: {self.tempo_simulacao}")
        self.lbl_viagens.config(text=f"Viagens ativas: {len(self.viagens_ativas)}")
        self.lbl_veiculos.config(text=f"Veículos disponíveis: {self.veiculos_disponiveis}")
        self.lbl_atendidos.config(text=f"Pedidos atendidos: {self.pedidos_atendidos}")
        self.lbl_rejeitados.config(text=f"Pedidos rejeitados: {self.pedidos_rejeitados}")

        total = self.pedidos_atendidos + self.pedidos_rejeitados
        taxa = (self.pedidos_atendidos / total * 100) if total > 0 else 0.0
        self.lbl_taxa.config(text=f"Taxa de sucesso: {taxa:.1f}%")

        # Atualizar tabela de viagens
        for item in self.tree.get_children():
            self.tree.delete(item)
        for vid, veic in self.viagens_ativas.items():
            if hasattr(veic, "rota_viagem"):
                origem = veic.rota_viagem[0]
                destino = getattr(veic, "destino", veic.rota_viagem[-1])
                progresso = f"{getattr(veic, 'progresso_viagem', 0.0):.1%}"
                pid = getattr(veic, "pedido_id", "?")
                self.tree.insert("", "end", values=(vid, pid, origem, destino, progresso))

        self.root.after(500, self._atualizar_display)

    def _adicionar_log(self, texto):
        """Adiciona uma linha ao painel de logs."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {texto}\n"
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        self.txt_logs.config(state="normal")
        self.txt_logs.delete("1.0", tk.END)
        self.txt_logs.insert(tk.END, "".join(self.logs))
        self.txt_logs.config(state="disabled")
        self.txt_logs.see(tk.END)
