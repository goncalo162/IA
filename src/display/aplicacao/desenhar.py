# display/aplicacao/desenhar.py
import math
from matplotlib.patches import Circle

def _compute_node_radius(pos, relative_factor=0.03, min_radius=0.01, max_radius=0.18):
    """Compute appropriate node radius based on graph span."""
    xs = [p[0] for p in pos.values()] if pos else [0.0]
    ys = [p[1] for p in pos.values()] if pos else [0.0]
    xrange = (max(xs) - min(xs)) if xs else 1.0
    yrange = (max(ys) - min(ys)) if ys else 1.0
    span = max(xrange, yrange, 1e-6)
    r = span * relative_factor
    r = max(min_radius, min(max_radius, r))
    return r


def draw_graph(app):
    """Draw the complete graph with nodes, edges, and vehicles."""
    ax, pos, G = app.ax, app.pos, app.G

    ax.cla()
    ax.grid(False)
    ax.set_aspect("equal", adjustable="datalim")

    node_radius = _compute_node_radius(pos)

    # Draw edges first (so they appear behind nodes)
    app.edge_lines = {}
    for u, v in G.edges():
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        line = ax.plot([x1, x2], [y1, y2], color="gray", linewidth=1.2, zorder=1)[0]
        app.edge_lines[(u, v)] = line

    # Draw nodes with text labels inside
    app.node_patches = {}
    app.node_texts = {}
    for n, (x, y) in pos.items():
        # Create circle for node
        circ = Circle((x, y), node_radius, zorder=2, ec="black", lw=0.8, facecolor="lightblue")
        ax.add_patch(circ)
        app.node_patches[n] = circ

        # Calculate appropriate font size for text to fit inside circle
        # Get pixel radius to scale font appropriately
        try:
            trans = ax.transData.transform
            px_center = trans((x, y))
            px_edge = trans((x + node_radius, y))
            pixel_radius = abs(px_edge[0] - px_center[0])
            # Font size should be proportional to circle size
            fontsize = max(6, min(12, int(pixel_radius * 0.5)))
        except Exception:
            fontsize = 8
        
        # Create text centered in the circle
        txt = ax.text(
            x, y, str(n),
            ha="center", va="center",
            zorder=3,
            fontsize=fontsize,
            color="black",
            weight="bold"
        )
        app.node_texts[n] = txt

    # Initialize vehicle markers dictionary if needed
    if not hasattr(app, "vehicle_markers"):
        app.vehicle_markers = {}

    # Draw vehicles from ambiente
    if hasattr(app, "ambiente") and app.ambiente is not None:
        veiculos = app.ambiente.listar_veiculos()
        print(f"[DEBUG] Drawing {len(veiculos)} vehicles")  # Debug output
        
        for v in veiculos:
            vid = v.id_veiculo
            node_name = v.localizacao_atual
            
            print(f"[DEBUG] Vehicle {vid} at node {node_name}")  # Debug output
            
            if node_name not in pos:
                print(f"[WARNING] Node {node_name} not in position dictionary")
                continue
            
            x, y = pos[node_name]
            
            # Determine vehicle color based on type
            try:
                clsname = v.__class__.__name__.lower()
                if "eletric" in clsname or "eletrico" in clsname:
                    color = "red"
                else:
                    color = "orange"
            except Exception:
                color = "orange"
            
            # Create or update vehicle marker
            if vid not in app.vehicle_markers:
                # Create new marker (diamond shape for visibility)
                marker, = ax.plot(
                    [x], [y],
                    marker="D",  # Diamond shape
                    color=color,
                    markersize=max(8, int(node_radius * 50)),
                    markeredgecolor="black",
                    markeredgewidth=1.5,
                    zorder=5  # Draw on top of nodes
                )
                app.vehicle_markers[vid] = marker
                print(f"[DEBUG] Created marker for vehicle {vid}")
            else:
                # Update existing marker position
                app.vehicle_markers[vid].set_data([x], [y])
                print(f"[DEBUG] Updated marker for vehicle {vid}")

    # Handle legacy car_point if it exists
    if hasattr(app, "car_info"):
        if getattr(app, "car_point", None) is None:
            vx = app.car_info.get("visual_x", 0.0)
            vy = app.car_info.get("visual_y", 0.0)
            app.car_point, = ax.plot(
                [vx], [vy],
                "ro",
                markersize=max(6, int(node_radius * 40)),
                zorder=5
            )
        else:
            vx = app.car_info.get("visual_x", app.car_point.get_xdata()[0])
            vy = app.car_info.get("visual_y", app.car_point.get_ydata()[0])
            app.car_point.set_data([vx], [vy])

    # Set axis limits with margin for better viewing
    xs = [p[0] for p in pos.values()] if pos else [0.0]
    ys = [p[1] for p in pos.values()] if pos else [0.0]
    if xs and ys:
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        dx = maxx - minx if maxx != minx else node_radius * 2
        dy = maxy - miny if maxy != miny else node_radius * 2
        margin_x = dx * 0.15
        margin_y = dy * 0.15
        ax.set_xlim(minx - margin_x, maxx + margin_x)
        ax.set_ylim(miny - margin_y, maxy + margin_y)

    # Force canvas redraw
    app.canvas.draw_idle()


def update_graph_drawing(app):
    """Update positions of all graph elements (for animation/panning/zooming)."""
    
    # Update edges
    for (u, v), line in app.edge_lines.items():
        if u in app.pos and v in app.pos:
            x1, y1 = app.pos[u]
            x2, y2 = app.pos[v]
            line.set_data([x1, x2], [y1, y2])

    # Update nodes and their labels
    for n, circ in app.node_patches.items():
        if n in app.pos:
            x, y = app.pos[n]
            circ.center = (x, y)
            if n in app.node_texts:
                app.node_texts[n].set_position((x, y))

    # Update vehicles
    if hasattr(app, "vehicle_markers") and hasattr(app, "ambiente") and app.ambiente is not None:
        veiculos = app.ambiente.listar_veiculos()
        
        for v in veiculos:
            vid = v.id_veiculo
            node_name = v.localizacao_atual
            
            if node_name in app.pos and vid in app.vehicle_markers:
                x, y = app.pos[node_name]
                app.vehicle_markers[vid].set_data([x], [y])

    # Update legacy car point if it exists
    if getattr(app, "car_point", None) is not None and hasattr(app, "car_info"):
        vx = app.car_info.get("visual_x", 0.0)
        vy = app.car_info.get("visual_y", 0.0)
        app.car_point.set_data([vx], [vy])

    # Force canvas redraw
    app.canvas.draw_idle()