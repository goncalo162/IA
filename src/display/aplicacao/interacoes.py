# filename: graph_viewer/interaction.py
def register_interactions(app):
    """Attach all event handlers."""
    app.canvas.mpl_connect("scroll_event", lambda e: _on_scroll(app, e))
    app.canvas.mpl_connect("button_press_event", lambda e: _on_button_press(app, e))
    app.canvas.mpl_connect("button_release_event", lambda e: _on_button_release(app, e))
    app.canvas.mpl_connect("motion_notify_event", lambda e: _on_motion(app, e))


def _on_button_press(app, event):
    if event.inaxes != app.ax:
        return
    if event.button == 1:
        app._dragging = True
        app._drag_start = (event.x, event.y)
        app._xlim_start = app.ax.get_xlim()
        app._ylim_start = app.ax.get_ylim()


def _on_button_release(app, event):
    if event.button == 1:
        app._dragging = False


def _on_motion(app, event):
    if not app._dragging or event.inaxes != app.ax:
        return
    dx = event.x - app._drag_start[0]
    dy = event.y - app._drag_start[1]
    inv = app.ax.transData.inverted()
    x0, y0 = inv.transform(app._drag_start)
    x1, y1 = inv.transform((event.x, event.y))
    dx_data = x0 - x1
    dy_data = y0 - y1
    xlim0, xlim1 = app._xlim_start
    ylim0, ylim1 = app._ylim_start
    app.ax.set_xlim(xlim0 + dx_data, xlim1 + dx_data)
    app.ax.set_ylim(ylim0 + dy_data, ylim1 + dy_data)
    app.canvas.draw_idle()


def _on_scroll(app, event):
    """Zoom centered on mouse pointer."""
    if event.inaxes != app.ax:
        return
    base_scale = 1.15
    cur_xlim = app.ax.get_xlim()
    cur_ylim = app.ax.get_ylim()
    xdata, ydata = event.xdata, event.ydata
    scale_factor = 1 / base_scale if event.button == "up" else base_scale
    new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
    new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
    relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
    rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
    new_xmin = xdata - (1 - relx) * new_width
    new_xmax = xdata + (relx) * new_width
    new_ymin = ydata - (1 - rely) * new_height
    new_ymax = ydata + (rely) * new_height
    app.ax.set_xlim(new_xmin, new_xmax)
    app.ax.set_ylim(new_ymin, new_ymax)
    app.canvas.draw_idle()