# tui_controller.py
import socket
import threading
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, Static, Header, Footer
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

HOST = "127.0.0.1"
PORT = 6000


class GraphCarController(App):
    car_position = reactive("A")
    status = reactive("🟢 Pronto")

    def __init__(self):
        super().__init__()
        self.conn = None
        threading.Thread(target=self.connect_to_server, daemon=True).start()

    def connect_to_server(self):
        while True:
            try:
                self.conn = socket.create_connection((HOST, PORT))
                self.notify("✅ Connected to graph_display!", severity="success")
                threading.Thread(target=self.listen_server, daemon=True).start()
                break
            except ConnectionRefusedError:
                pass

    def listen_server(self):
        while True:
            data = self.conn.recv(1024)
            if not data:
                break
            for line in data.decode().splitlines():
                if line.startswith("position"):
                    _, pos = line.split(maxsplit=1)
                    self.car_position = pos
                elif line.startswith("status"):
                    _, msg = line.split(maxsplit=1)
                    self.status = msg
                self.update_display()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("🚗 Controlador do Carro", id="title")
            yield Static(id="car-info")
            yield Static(id="status-info")
            with Horizontal():
                for n in ["A", "B", "C", "D"]:
                    yield Button(f"Ir para {n}", id=f"btn-{n}")
            yield Button("🛑 Parar (encerra gráfico)", id="btn-stop", variant="error")
        yield Footer()

    def update_display(self):
        self.query_one("#car-info", Static).update(f"📍 Posição: {self.car_position}")
        self.query_one("#status-info", Static).update(f"Status: {self.status}")

    def on_button_pressed(self, event: Button.Pressed):
        if not self.conn:
            self.notify("❌ Not connected!", severity="error")
            return
        bid = event.button.id
        if bid == "btn-stop":
            self.conn.sendall(b"stop\n")
            self.notify("🛑 Stop sent — closing graph.", severity="error")
        else:
            target = bid.split("-")[1]
            self.conn.sendall(f"move_to {target}\n".encode())
            self.notify(f"🚗 Moving to {target}", severity="success")


if __name__ == "__main__":
    app = GraphCarController()
    app.run()