from graph.algoritmos_procura import bfs, dfs

def process_queue(app):
    """Check command queue for move/quit actions."""
    try:
        while True:
            cmd, value = app.command_queue.get_nowait()
            if cmd == "move":
                _handle_move(app, value)
            elif cmd == "quit":
                app.root.destroy()
                return
    except Exception:
        pass
    app.root.after(50, lambda: process_queue(app))


def _handle_move(app, destino):
    car = app.car_info
    if car["is_moving"]:
        print("Already moving — ignoring new command.")
        return

    origin = car["position"]
    if app.search_algorithm == "dfs":
        path = dfs(app.grafo, origin, destino)
    else:
        path = bfs(app.grafo, origin, destino)

    if not path:
        print(f"No path to {destino} from {origin}")
        return

    car.update(dict(path=path, path_index=0, progress=0.0, is_moving=True))
    print(f"🚗 Moving to {destino} via {'→'.join(path)} using {app.search_algorithm.upper()}")