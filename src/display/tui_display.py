import sys
import os

# Add project root to Python path (so grafos can be imported)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
from textual.app import App, ComposeResult
from textual.widgets import Button, Label, Static, Header, Footer
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from graph.grafo import Grafo  # Correctly import Grafo from the display folder
from graph.node import Node  # Make sure Node is imported from the right location

HOST = "127.0.0.1"
PORT = 6000

class GraphCarController(App):
    car_position = reactive("A")
    status = reactive("🟢 Pronto")

    def __init__(self, grafo: Grafo):
        super().__init__()
        self.grafo = grafo  # Store the Grafo object
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
                pass  # You could add a retry message here if needed

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
            
            # Dynamically create buttons based on the Grafo nodes
            with Horizontal():
                for node in self.grafo.getNodes():
                    yield Button(f"Ir para {node.getName()}", id=f"btn-{node.getName()}")
            
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
    # Load the graph from a JSON file or use a default one
    graph_path = "dataset/grafo.json"  # Change this to your actual path
    try:
        grafo = Grafo.from_json_file(graph_path)  # This will load the graph from the JSON file
        print(f"✅ Loaded graph from JSON: {graph_path}")
    except Exception as e:
        print(f"⚠️ Failed to load JSON ({e}), using default graph.")
        grafo = Grafo()  # Use a default Grafo if loading fails

    # Pass the Grafo to the TUI controller
    app = GraphCarController(grafo)
    app.run()