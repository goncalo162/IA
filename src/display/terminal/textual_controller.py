# display/terminal/textual_controller.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.containers import Container, Vertical
from textual.reactive import reactive
from datetime import datetime


class GraphCarController(App):
    """
    Textual TUI Dashboard - Displays simulation information in real-time.
    No commands, only monitoring.
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main_container {
        height: 100%;
        width: 100%;
    }
    
    .info_panel {
        height: auto;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #simulation_info {
        height: 8;
    }
    
    #metrics_panel {
        height: 12;
    }
    
    #active_trips_table {
        height: 1fr;
    }
    
    #logs_panel {
        height: 15;
        overflow-y: scroll;
    }
    
    .title {
        text-style: bold;
        color: $accent;
    }
    
    .log_entry {
        margin: 0 1;
    }
    """
    
    # Reactive attributes for auto-update
    tempo_simulacao = reactive("--:--:--")
    pedidos_atendidos = reactive(0)
    pedidos_rejeitados = reactive(0)
    viagens_ativas_count = reactive(0)
    veiculos_disponiveis = reactive(0)
    
    def __init__(self, command_queue):
        super().__init__()
        self.command_queue = command_queue
        self.logs = []
        self.max_logs = 50
        self.active_trips_data = {}
    
    def compose(self) -> ComposeResult:
        """Build the dashboard layout."""
        yield Header()
        
        with Container(id="main_container"):
            # Simulation time and status
            with Vertical(id="simulation_info", classes="info_panel"):
                yield Static("[bold cyan]═══ SIMULAÇÃO ═══[/]", classes="title")
                yield Static("", id="time_display")
                yield Static("", id="status_display")
            
            # Metrics panel
            with Vertical(id="metrics_panel", classes="info_panel"):
                yield Static("[bold cyan]═══ MÉTRICAS ═══[/]", classes="title")
                yield Static("", id="metrics_display")
            
            # Active trips table
            with Vertical(id="active_trips_container", classes="info_panel"):
                yield Static("[bold cyan]═══ VIAGENS ATIVAS ═══[/]", classes="title")
                yield DataTable(id="active_trips_table")
            
            # Logs panel
            with Vertical(id="logs_panel", classes="info_panel"):
                yield Static("[bold cyan]═══ REGISTRO DE EVENTOS ═══[/]", classes="title")
                yield Static("", id="logs_display")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the dashboard components."""
        # Setup active trips table
        table = self.query_one("#active_trips_table", DataTable)
        table.add_columns("Veículo", "Pedido", "Origem", "Destino", "Progresso")
        
        # Start update timer (refresh every 100ms)
        self.set_interval(0.1, self.check_queue)
        self.set_interval(0.5, self.update_display)
    
    def check_queue(self):
        """Check command queue for updates from simulator."""
        try:
            while not self.command_queue.empty():
                message = self.command_queue.get_nowait()
                self.process_message(message)
        except Exception as e:
            self.add_log(f"[red]Erro ao processar mensagem: {e}[/]")
    
    def process_message(self, message):
        """Process incoming messages from the simulator."""
        msg_type = message.get("type")
        
        if msg_type == "update_time":
            tempo = message.get("tempo")
            viagens = message.get("viagens", {})
            
            if isinstance(tempo, datetime):
                self.tempo_simulacao = tempo.strftime("%H:%M:%S")
            else:
                self.tempo_simulacao = str(tempo)
            
            self.viagens_ativas_count = len(viagens)
            self.update_active_trips(viagens)
        
        elif msg_type == "new_trip":
            pedido = message.get("pedido")
            veiculo = message.get("veiculo")
            rota = message.get("rota", [])
            
            if pedido and veiculo:
                origem = rota[0] if len(rota) > 0 else "?"
                destino = rota[-1] if len(rota) > 0 else "?"
                log_msg = (
                    f"[green]✓[/] Viagem iniciada: Veículo {veiculo.id_veiculo} - "
                    f"Pedido #{pedido.id} ({origem} → {destino})"
                )
                self.add_log(log_msg)
        
        elif msg_type == "reject":
            self.pedidos_rejeitados += 1
            self.add_log("[yellow]⚠[/] Pedido rejeitado")
        
        elif msg_type == "metrics":
            self.pedidos_atendidos = message.get("atendidos", 0)
            self.pedidos_rejeitados = message.get("rejeitados", 0)
            self.veiculos_disponiveis = message.get("disponiveis", 0)
        
        elif msg_type == "log":
            log_msg = message.get("message", "")
            self.add_log(log_msg)
        
        elif msg_type == "close":
            self.add_log("[bold red]Simulação finalizada[/]")
            self.set_timer(2.0, self.exit)
    
    def update_active_trips(self, viagens_dict):
        """Update the active trips table."""
        table = self.query_one("#active_trips_table", DataTable)
        
        # Clear existing rows
        table.clear()
        
        # Add current active trips
        for veiculo_id, veiculo in viagens_dict.items():
            if hasattr(veiculo, 'rota_viagem') and veiculo.rota_viagem:
                origem = veiculo.rota_viagem[0]
                destino = veiculo.destino if hasattr(veiculo, 'destino') else veiculo.rota_viagem[-1]
                progresso = f"{veiculo.progresso_viagem:.1%}" if hasattr(veiculo, 'progresso_viagem') else "0%"
                pedido_id = veiculo.pedido_id if hasattr(veiculo, 'pedido_id') else "?"
                
                table.add_row(
                    veiculo_id,
                    str(pedido_id),
                    str(origem),
                    str(destino),
                    progresso
                )
    
    def add_log(self, message: str):
        """Add a log entry to the logs panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[dim]{timestamp}[/] {message}"
        
        self.logs.append(log_entry)
        
        # Keep only last N logs
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
    
    def update_display(self):
        """Update all display widgets with current data."""
        # Update time display
        time_widget = self.query_one("#time_display", Static)
        time_widget.update(
            f"[bold]Tempo:[/] {self.tempo_simulacao}\n"
            f"[bold]Viagens ativas:[/] {self.viagens_ativas_count}"
        )
        
        # Update status display
        status_widget = self.query_one("#status_display", Static)
        status_widget.update(
            f"[bold]Veículos disponíveis:[/] {self.veiculos_disponiveis}"
        )
        
        # Update metrics display
        metrics_widget = self.query_one("#metrics_display", Static)
        total_pedidos = self.pedidos_atendidos + self.pedidos_rejeitados
        taxa_sucesso = (self.pedidos_atendidos / total_pedidos * 100) if total_pedidos > 0 else 0
        
        metrics_widget.update(
            f"[green]✓ Pedidos atendidos:[/] {self.pedidos_atendidos}\n"
            f"[red]✗ Pedidos rejeitados:[/] {self.pedidos_rejeitados}\n"
            f"[cyan]📊 Taxa de sucesso:[/] {taxa_sucesso:.1f}%\n"
            f"[yellow]📋 Total:[/] {total_pedidos}"
        )
        
        # Update logs display
        logs_widget = self.query_one("#logs_display", Static)
        logs_text = "\n".join(self.logs[-15:])  # Show last 15 logs
        logs_widget.update(logs_text)