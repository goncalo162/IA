def register_interactions(app):
    """Registar handlers de interação do utilizador."""
    if not hasattr(app, "_dragging"):
        app._dragging = False
        app._drag_start = None
        app._xlim_start = None
        app._ylim_start = None

    app.canvas.mpl_connect("scroll_event", lambda e: _on_scroll(app, e))
    app.canvas.mpl_connect("button_press_event",
                           lambda e: _on_button_press(app, e))
    app.canvas.mpl_connect("button_release_event",
                           lambda e: _on_button_release(app, e))
    app.canvas.mpl_connect("motion_notify_event", lambda e: _on_motion(app, e))


def _on_button_press(app, event):
    """Iniciou drag - guardar estado antes de começar."""
    if event.inaxes != app.ax:
        return
    if getattr(event, "button", None) == 1:
        app._dragging = True
        app._drag_start = (event.x, event.y)
        try:
            app._xlim_start = app.ax.get_xlim()
            app._ylim_start = app.ax.get_ylim()
        except Exception:
            app._xlim_start = None
            app._ylim_start = None


def _on_button_release(app, event):
    """Libertou o drag - guardar novo estado."""
    if getattr(event, "button", None) == 1:
        app._dragging = False
        app._drag_start = None
        app._xlim_start = None
        app._ylim_start = None
        
        # Guardar viewport após pan terminar
        try:
            if hasattr(app, "viewport"):
                app.viewport.save_state(app.ax)
        except Exception as e:
            print(f"[InteractionHandler] Erro ao salvar viewport após pan: {e}")


def _on_motion(app, event):
    """Arrastar - atualizar limites do eixo em tempo real."""
    if not app._dragging or app._drag_start is None:
        return
    if event.inaxes != app.ax:
        return
    
    dx = event.x - app._drag_start[0]
    dy = event.y - app._drag_start[1]
    inv = app.ax.transData.inverted()
    x0, y0 = inv.transform(app._drag_start)
    x1, y1 = inv.transform((event.x, event.y))
    dx_data = x0 - x1
    dy_data = y0 - y1
    
    if app._xlim_start and app._ylim_start:
        xlim0, xlim1 = app._xlim_start
        ylim0, ylim1 = app._ylim_start
        app.ax.set_xlim(xlim0 + dx_data, xlim1 + dx_data)
        app.ax.set_ylim(ylim0 + dy_data, ylim1 + dy_data)
        app.canvas.draw_idle()


def _on_scroll(app, event):
    """Zoom com scroll do rato - guardar estado após zoom."""
    if event.inaxes != app.ax:
        return
    
    xdata, ydata = event.xdata, event.ydata
    if xdata is None or ydata is None:
        return
    
    base_scale = 1.15
    if getattr(event, "button", None) == "up":
        scale_factor = 1 / base_scale
    else:
        scale_factor = base_scale
    
    cur_xlim = app.ax.get_xlim()
    cur_ylim = app.ax.get_ylim()
    new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
    new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
    
    relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0]
                                    ) if cur_xlim[1] != cur_xlim[0] else 0.5
    rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0]
                                    ) if cur_ylim[1] != cur_ylim[0] else 0.5
    
    new_xmin = xdata - (1 - relx) * new_width
    new_xmax = xdata + (relx) * new_width
    new_ymin = ydata - (1 - rely) * new_height
    new_ymax = ydata + (rely) * new_height
    
    app.ax.set_xlim(new_xmin, new_xmax)
    app.ax.set_ylim(new_ymin, new_ymax)
    
    # Guardar viewport após zoom
    try:
        if hasattr(app, 'viewport'):
            app.viewport.save_state(app.ax)
    except Exception as e:
        print(f"[InteractionHandler] Erro ao salvar viewport no scroll: {e}")
    
    app.canvas.draw_idle()