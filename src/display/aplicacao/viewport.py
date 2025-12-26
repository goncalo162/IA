class Viewport:
    """Controla o zoom e pan do gráfico com persistência correta."""

    def __init__(self):
        self.xlim = None
        self.ylim = None
        self.zoom_level = 1.0
        self.is_auto_scale = True  # Auto-ajustar no primeiro draw

    def save_state(self, ax):
        """Guarda o estado atual do eixo."""
        try:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()

            # Apenas guardar se os limites são válidos
            if xlim and ylim and len(xlim) == 2 and len(ylim) == 2:
                self.xlim = xlim
                self.ylim = ylim
                self.zoom_level = (xlim[1] - xlim[0]) * (ylim[1] - ylim[0])
                # Garantir que não voltamos ao auto-scale
                self.is_auto_scale = False
                print(f"[Viewport] Estado guardado: xlim={self.xlim}, ylim={self.ylim}")
        except Exception as e:
            print(f"[Viewport] Erro ao salvar estado: {e}")

    def restore_state(self, ax):
        """Restaura o estado guardado."""
        if self.xlim is not None and self.ylim is not None:
            try:
                ax.set_xlim(self.xlim)
                ax.set_ylim(self.ylim)
                # Não reativar auto-scale ao restaurar
                self.is_auto_scale = False
                print(f"[Viewport] Estado restaurado: xlim={self.xlim}, ylim={self.ylim}")
            except Exception as e:
                print(f"[Viewport] Erro ao restaurar estado: {e}")

    def apply_auto_scale(self, ax, pos, margin=0.15):
        """Auto-escala inicial baseada nos nós."""
        # Apenas aplicar se é primeira vez (is_auto_scale == True)
        if not self.is_auto_scale or not pos:
            return

        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]

        if xs and ys:
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            dx = maxx - minx if maxx != minx else 1.0
            dy = maxy - miny if maxy != miny else 1.0

            margin_x = dx * margin
            margin_y = dy * margin

            self.xlim = (minx - margin_x, maxx + margin_x)
            self.ylim = (miny - margin_y, maxy + margin_y)

            ax.set_xlim(self.xlim)
            ax.set_ylim(self.ylim)

            # Marcar como já aplicado - nunca mais aplicar auto-scale
            self.is_auto_scale = False
            print(f"[Viewport] Auto-scale inicial aplicado: xlim={self.xlim}, ylim={self.ylim}")

    def reset(self):
        """Reseta o viewport para o estado inicial."""
        self.xlim = None
        self.ylim = None
        self.zoom_level = 1.0
        self.is_auto_scale = True
        print("[Viewport] Viewport resetado")
