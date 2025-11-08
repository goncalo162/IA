# display/aplicacao/queue_handler.py
"""
Processes commands from the queue and updates the graph viewer.
"""

def process_queue(app):
    """
    Called periodically via Tk's after() to check for messages from the simulator.
    """
    try:
        while not app.command_queue.empty():
            message = app.command_queue.get_nowait()
            handle_message(app, message)
    except Exception as e:
        print(f"[queue_handler] Error processing queue: {e}")
    
    # Schedule next check
    app.root.after(100, lambda: process_queue(app))


def handle_message(app, message):
    """
    Route incoming messages to appropriate handlers.
    """
    msg_type = message.get("type")
    
    if msg_type == "update_time":
        # Update simulation time display
        tempo = message.get("tempo")
        viagens = message.get("viagens", {})
        app.update_time(tempo, viagens)
    
    elif msg_type == "new_trip":
        # Highlight a new trip route
        pedido = message.get("pedido")
        veiculo = message.get("veiculo")
        rota = message.get("rota", [])
        
        if rota:
            app.highlight_route(rota)
        
        print(f"[GraphViewer] New trip: Vehicle {veiculo.id_veiculo if veiculo else '?'} "
              f"for request #{pedido.id if pedido else '?'}")
    
    elif msg_type == "reject":
        # Visual feedback for rejected request
        print("[GraphViewer] Request rejected")
    
    elif msg_type == "close":
        # Close the viewer
        print("[GraphViewer] Received close command")
        app.root.quit()
    
    elif msg_type == "log":
        # Log message (could display in viewer if needed)
        log_msg = message.get("message", "")
        print(f"[GraphViewer] {log_msg}")
    
    else:
        print(f"[GraphViewer] Unknown message type: {msg_type}")