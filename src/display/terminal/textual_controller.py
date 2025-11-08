from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Static


class GraphCarController(App):
    """Textual TUI Controller"""
    CSS_PATH = None

    def __init__(self, command_queue):
        super().__init__()
        self.command_queue = command_queue
        self.status_widget = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Enter destination node", id="target")
        yield Button("Move", id="move_btn")
        yield Button("Quit", id="quit_btn")
        yield Static("", id="status")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        target_input = self.query_one("#target", Input)
        self.status_widget = self.query_one("#status", Static)
        if event.button.id == "move_btn":
            destino = target_input.value.strip()
            if destino:
                self.command_queue.put(("move", destino))
                self.status_widget.update(f"Sent move command to {destino}")
            else:
                self.status_widget.update("Please enter a node.")
        elif event.button.id == "quit_btn":
            self.command_queue.put(("quit", None))
            self.exit()