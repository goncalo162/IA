from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
from typing import Optional
import matplotlib.patches as mpatches
from infra.grafo.node import TipoNodo
from infra.entidades.veiculos import VeiculoCombustao

"""Display gráfico usando NetworkX e Matplotlib para visualizar a simulação em tempo real."""


class DisplayBase(ABC):
    """Interface base para componentes de display/visualização."""

    @abstractmethod
    def iniciar(self, ambiente):
        """Inicializa o display com o ambiente da simulação."""
        pass

    @abstractmethod
    def atualizar(self, pedido, veiculo, rota):
        """Atualiza o display com informações de um pedido processado."""
        pass

    @abstractmethod
    def finalizar(self):
        """Finaliza o display."""
        pass


class DisplayGrafico(DisplayBase):
    """Display gráfico que mostra veículos movendo-se no grafo usando NetworkX e Matplotlib."""

    def __init__(self, frequencia_display: float = 10.0):
        """
        Inicializa o display gráfico.

        Args:
            frequencia_display: Quantas vezes o display mostra informação atualizada por segundo real (Hz) (padrão: 10 Hz = 10 FPS)
        """
        self.ultimo_update = None
        self.frequencia_display = frequencia_display
        self.intervalo_update = 1.0 / frequencia_display

        # NetworkX graph
        self.G = None
        self.pos = None

        # Matplotlib figure e axes
        self.fig = None
        self.ax = None

        # Dados da simulação
        self.ambiente = None
        self.metricas = None
        self.tempo_atual = None
        self.viagens_ativas = []
        self.velocidade_simulacao = 1.0
        self.inicializado = False

        # Artists para atualização incremental (sem redesenhar tudo)
        self.edge_artists = []
        self.node_collections = []
        self.vehicle_artists = {}
        self.title_text = None
        self.legend_obj = None
        self.stats_text_obj = None

        # Flag para primeiro desenho
        self.primeiro_desenho = True

        # Variáveis para pan (arrastar)
        self.pan_ativo = False
        self.pan_start_pos = None
        self.pan_start_xlim = None
        self.pan_start_ylim = None

    def _conectar_eventos_interacao(self):
        """Conecta eventos de mouse para zoom e pan interativos."""
        # Zoom com scroll do rato
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)

        # Pan com botão esquerdo do rato
        self.fig.canvas.mpl_connect('button_press_event', self._on_button_press)
        self.fig.canvas.mpl_connect('button_release_event', self._on_button_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

    def _on_scroll(self, event):
        """Handler para zoom com scroll do rato."""
        if event.inaxes != self.ax:
            return

        # Fator de zoom
        if event.button == 'up':
            scale_factor = 0.9  # Zoom in
        elif event.button == 'down':
            scale_factor = 1.1  # Zoom out
        else:
            return

        # Obter limites atuais
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        # Coordenadas do cursor no sistema de dados
        xdata = event.xdata
        ydata = event.ydata

        if xdata is None or ydata is None:
            return

        # Calcular novos limites centralizados no cursor
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor

        relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
        rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

        new_xlim = [xdata - new_width * (1 - relx), xdata + new_width * relx]
        new_ylim = [ydata - new_height * (1 - rely), ydata + new_height * rely]

        # Aplicar novos limites
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)

        # Forçar atualização
        self.fig.canvas.draw_idle()

    def _on_button_press(self, event):
        """Handler para início do pan (arrastar)."""
        if event.inaxes != self.ax or event.button != 1:
            return

        self.pan_ativo = True
        self.pan_start_pos = (event.x, event.y)
        self.pan_start_xlim = self.ax.get_xlim()
        self.pan_start_ylim = self.ax.get_ylim()

    def _on_button_release(self, event):
        """Handler para fim do pan."""
        if event.button != 1:
            return

        self.pan_ativo = False
        self.pan_start_pos = None
        self.pan_start_xlim = None
        self.pan_start_ylim = None

    def _on_mouse_move(self, event):
        """Handler para movimento do rato durante pan."""
        if not self.pan_ativo or self.pan_start_pos is None:
            return

        if event.inaxes != self.ax:
            return

        # Calcular deslocamento em pixels
        dx = event.x - self.pan_start_pos[0]
        dy = event.y - self.pan_start_pos[1]

        # Converter para coordenadas de dados
        inv = self.ax.transData.inverted()
        start_data = inv.transform(self.pan_start_pos)
        current_data = inv.transform((event.x, event.y))

        dx_data = start_data[0] - current_data[0]
        dy_data = start_data[1] - current_data[1]

        # Aplicar deslocamento
        if self.pan_start_xlim and self.pan_start_ylim:
            new_xlim = [self.pan_start_xlim[0] + dx_data, self.pan_start_xlim[1] + dx_data]
            new_ylim = [self.pan_start_ylim[0] + dy_data, self.pan_start_ylim[1] + dy_data]

            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)

            # Forçar atualização
            self.fig.canvas.draw_idle()

    def iniciar(self, ambiente):
        """Inicializa o display com o ambiente da simulação."""
        self.ambiente = ambiente
        self._criar_grafo()
        self._inicializar_plot()
        self.inicializado = True

    def iniciar_ambiente(self, ambiente):
        """Inicializa o display com os dados do ambiente."""
        self.iniciar(ambiente)

    def set_velocidade_simulacao(self, velocidade: float):
        """Define a velocidade de simulação para exibição."""
        self.velocidade_simulacao = velocidade

    def _criar_grafo(self):
        """Cria o grafo NetworkX a partir do grafo do ambiente."""
        self.G = nx.DiGraph()
        grafo = self.ambiente.grafo

        # Adicionar nós
        for node in grafo.getNodes():
            node_id = node.getId()
            tipo = node.getTipoNodo()
            self.G.add_node(
                node_id,
                nome=node.getName(),
                tipo=tipo.name,
                tipo_enum=tipo,
                x=node.getX(),
                y=node.getY()
            )

        # Adicionar arestas
        for node in grafo.getNodes():
            origem_nome = node.getName()
            if origem_nome in grafo.m_graph:
                for destino_nome, aresta in grafo.m_graph[origem_nome]:
                    origem_id = grafo.getNodeId(origem_nome)
                    destino_id = grafo.getNodeId(destino_nome)
                    if origem_id is not None and destino_id is not None:
                        self.G.add_edge(
                            origem_id,
                            destino_id,
                            distancia=aresta.getQuilometro(),
                            velocidade=aresta.getVelocidadeMaxima(),
                            transito=aresta.getTransito().name
                        )

        self.pos = nx.kamada_kawai_layout(self.G)

    def _inicializar_plot(self):
        """Inicializa a janela do Matplotlib."""
        try:
            plt.rcParams['toolbar'] = 'None'  # Remover toolbar (vamos usar scroll)
        except Exception:
            pass

        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        self.canvas = self.fig.canvas
        self.fig.canvas.manager.set_window_title(
            'Simulação de Frota - Visualização em Tempo Real')

        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # Criar janela separada para estatísticas
        try:
            self.stats_fig, self.stats_ax = plt.subplots(figsize=(4, 6))
            self.stats_fig.canvas.manager.set_window_title(
                'Estatísticas da Simulação')
            self.stats_ax.axis('off')
        except Exception:
            self.stats_fig = None
            self.stats_ax = None

        # Conectar eventos de mouse para zoom/pan
        self._conectar_eventos_interacao()

    def atualizar_tempo_simulacao(self, tempo: datetime, viagens_ativas: list):
        """Atualiza a visualização com o tempo atual e viagens ativas."""
        if not self.inicializado:
            return

        # Controlar frequência de atualização
        agora = datetime.now()
        if self.ultimo_update and (
                agora - self.ultimo_update).total_seconds() < self.intervalo_update:
            return

        self.ultimo_update = agora
        self.tempo_atual = tempo
        self.viagens_ativas = viagens_ativas

        # Desenhar ou atualizar
        if self.primeiro_desenho:
            self._desenhar_grafo_completo()
            self.primeiro_desenho = False
        else:
            self._atualizar_elementos_dinamicos()

    def _desenhar_grafo_completo(self):
        """Desenha o grafo completo pela primeira vez (ou quando necessário)."""
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # Desenhar componentes estáticos
        self._desenhar_arestas()
        self._desenhar_nos()
        self._desenhar_legenda()

        # Desenhar título (será atualizado depois)
        tempo_str = self.tempo_atual.strftime("%H:%M:%S") if self.tempo_atual else "00:00:00"
        self.title_text = self.ax.set_title(
            f'🚕 Simulação de Frota em Tempo Real\n'
            f'Tempo: {tempo_str} | Viagens Ativas: {len(self.viagens_ativas)} | '
            f'Velocidade: {self.velocidade_simulacao}x',
            fontsize=14,
            fontweight='bold',
            pad=20
        )

        # Desenhar veículos (dinâmico)
        self._desenhar_veiculos()

        # Desenhar estatísticas
        self._desenhar_estatisticas()

        # Atualizar canvas
        try:
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception as e:
            if "application has been destroyed" not in str(e):
                print(f"Erro ao desenhar: {e}")

    def _atualizar_elementos_dinamicos(self):
        """Atualiza apenas elementos que mudam (veículos, título, estatísticas)."""
        # Atualizar título
        tempo_str = self.tempo_atual.strftime("%H:%M:%S") if self.tempo_atual else "00:00:00"
        if self.title_text:
            self.title_text.set_text(
                f'🚕 Simulação de Frota em Tempo Real\n'
                f'Tempo: {tempo_str} | Viagens Ativas: {len(self.viagens_ativas)} | '
                f'Velocidade: {self.velocidade_simulacao}x'
            )

        # Remover veículos antigos
        for artist in self.vehicle_artists.values():
            if isinstance(artist, list):
                for a in artist:
                    a.remove()
            else:
                artist.remove()
        self.vehicle_artists.clear()

        # Desenhar veículos em novas posições
        self._desenhar_veiculos()

        # Atualizar estatísticas
        self._desenhar_estatisticas()

        # Atualizar apenas o necessário (blit-like)
        try:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception as e:
            if "application has been destroyed" not in str(e):
                print(f"Erro ao atualizar: {e}")

    def _desenhar_arestas(self):
        """Desenha as arestas do grafo."""
        edge_colors = []
        edge_widths = []

        for origem, destino, data in self.G.edges(data=True):
            transito = data.get('transito', 'NORMAL')

            if transito == 'VAZIO':
                cor = '#90EE90'
                largura = 1.0
            elif transito == 'NORMAL':
                cor = '#87CEEB'
                largura = 1.0
            elif transito == 'ELEVADO':
                cor = '#FFD700'
                largura = 1.0
            elif transito == 'MUITO_ELEVADO':
                cor = '#FF8C00'
                largura = 1.0
            elif transito == 'ACIDENTE':
                cor = '#FF0000'
                largura = 1.0
            else:
                cor = '#808080'
                largura = 1.0

            edge_colors.append(cor)
            edge_widths.append(largura)

        # Desenhar arestas
        nx.draw_networkx_edges(
            self.G,
            self.pos,
            edge_color=edge_colors,
            width=edge_widths,
            arrows=False,
            ax=self.ax
        )

        # Labels de distância nas arestas
        edge_labels = {}
        for origem, destino, data in self.G.edges(data=True):
            distancia = data.get('distancia', 0)
            velocidade = data.get('velocidade', 0)
            edge_labels[(origem, destino)] = f'{distancia:.1f}km\n{velocidade}km/h'

        bbox_edge_labels = {
            'boxstyle': 'round,pad=0.3',
            'facecolor': 'white',
            'alpha': 0.7,
            'edgecolor': 'none',
        }

        nx.draw_networkx_edge_labels(
            self.G,
            self.pos,
            edge_labels,
            font_size=7,
            ax=self.ax,
            bbox=bbox_edge_labels,
        )

    def _desenhar_nos(self):
        """Desenha os nós do grafo."""
        nodes_local = []
        nodes_gasolina = []
        nodes_carregamento = []

        for node_id, data in self.G.nodes(data=True):
            tipo = data.get('tipo_enum')
            if tipo == TipoNodo.BOMBA_GASOLINA:
                nodes_gasolina.append(node_id)
            elif tipo == TipoNodo.POSTO_CARREGAMENTO:
                nodes_carregamento.append(node_id)
            else:
                nodes_local.append(node_id)

        if nodes_local:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_local,
                node_color='#4169E1',
                node_size=1000,
                node_shape='o',
                alpha=0.9,
                ax=self.ax
            )

        if nodes_gasolina:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_gasolina,
                node_color='#FF4500',
                node_size=1000,
                node_shape='s',
                alpha=0.9,
                ax=self.ax
            )

        if nodes_carregamento:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_carregamento,
                node_color='#32CD32',
                node_size=1000,
                node_shape='^',
                alpha=0.9,
                ax=self.ax
            )

        labels = {node_id: data['nome'] for node_id, data in self.G.nodes(data=True)}
        nx.draw_networkx_labels(
            self.G,
            self.pos,
            labels,
            font_size=4,
            font_color='black',
            ax=self.ax
        )

    def _desenhar_veiculos(self):
        """Desenha os veículos nas suas posições atuais."""
        todos_veiculos = self.ambiente.listar_veiculos()

        for veiculo in todos_veiculos:
            if isinstance(veiculo, VeiculoCombustao):
                cor_veiculo = '#8B0000'
                marcador = 'o'
            else:
                cor_veiculo = '#006400'
                marcador = 's'

            if veiculo.viagem_ativa:
                posicao = self._calcular_posicao_veiculo(veiculo)

                if posicao:
                    x, y = posicao

                    marker_obj = self.ax.plot(
                        x, y,
                        marker=marcador,
                        markersize=15,
                        color=cor_veiculo,
                        markeredgecolor='yellow',
                        markeredgewidth=2,
                        zorder=10
                    )[0]

                    # Escolher viagem representativa para exibir progresso
                    trip = self._get_trip_for_display(veiculo)
                    if trip is not None:
                        progresso = trip.progresso_percentual
                    else:
                        progresso = veiculo.progresso_percentual_medio

                    text_obj = self.ax.text(
                        x, y + 0.08,
                        f'V{veiculo.id_veiculo}\n{progresso:.0f}%',
                        fontsize=8,
                        ha='center',
                        va='bottom',
                        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': 'yellow',
                              'alpha': 0.8, 'edgecolor': 'black'},
                        zorder=11,
                    )

                    self.vehicle_artists[f"{veiculo.id_veiculo}_marker"] = marker_obj
                    self.vehicle_artists[f"{veiculo.id_veiculo}_text"] = text_obj
            else:
                node_nome = veiculo.localizacao_atual
                node_id = self.ambiente.grafo.getNodeId(node_nome)

                if node_id in self.pos:
                    x, y = self.pos[node_id]

                    marker_obj = self.ax.plot(
                        x, y,
                        marker=marcador,
                        markersize=12,
                        color=cor_veiculo,
                        markeredgecolor='white',
                        markeredgewidth=1.5,
                        alpha=0.7,
                        zorder=9
                    )[0]

                    estado_str = veiculo.estado.name
                    text_obj = self.ax.text(
                        x, y + 0.08,
                        f'V{veiculo.id_veiculo}\n{estado_str}',
                        fontsize=7,
                        ha='center',
                        va='bottom',
                        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': 'lightgray',
                              'alpha': 0.7, 'edgecolor': 'black'},
                        zorder=10,
                    )

                    self.vehicle_artists[f"{veiculo.id_veiculo}_marker"] = marker_obj
                    self.vehicle_artists[f"{veiculo.id_veiculo}_text"] = text_obj

    def _calcular_posicao_veiculo(self, veiculo) -> Optional[tuple]:
        """Calcula a posição interpolada de um veículo na sua rota."""
        if not veiculo.viagem_ativa:
            return None

        trip = self._get_trip_for_display(veiculo)
        if trip is None or not getattr(trip, 'rota', None) or len(trip.rota) < 2:
            if trip and getattr(trip, 'rota', None) and len(trip.rota) == 1:
                node_nome = trip.rota[0]
                node_id = self.ambiente.grafo.getNodeId(node_nome)
                if node_id in self.pos:
                    return self.pos[node_id]
            return None

        progresso_decimal = trip.progresso_percentual / 100.0
        num_segmentos = len(trip.rota) - 1
        posicao_segmento = progresso_decimal * num_segmentos
        indice_segmento = int(posicao_segmento)

        if indice_segmento >= num_segmentos:
            indice_segmento = num_segmentos - 1
            progresso_no_segmento = 1.0
        else:
            progresso_no_segmento = posicao_segmento - indice_segmento

        origem_nome = trip.rota[indice_segmento]
        destino_nome = trip.rota[indice_segmento + 1]
        origem_id = self.ambiente.grafo.getNodeId(origem_nome)
        destino_id = self.ambiente.grafo.getNodeId(destino_nome)

        if origem_id not in self.pos or destino_id not in self.pos:
            return None

        x_origem, y_origem = self.pos[origem_id]
        x_destino, y_destino = self.pos[destino_id]

        x = x_origem + (x_destino - x_origem) * progresso_no_segmento
        y = y_origem + (y_destino - y_origem) * progresso_no_segmento

        return (x, y)

    def _get_trip_for_display(self, veiculo):
        """Retorna a viagem a usar para exibir posição/progresso.

        Prioridade: reposicionamento > recarga > primeiro pedido ativo
        """
        # Reposicionamento tem prioridade
        if getattr(veiculo, 'viagem_reposicionamento', None) and veiculo.viagem_reposicionamento.viagem_ativa:
            return veiculo.viagem_reposicionamento

        # Recarga tem prioridade a seguir
        if getattr(veiculo, 'viagem_recarga', None) and veiculo.viagem_recarga.viagem_ativa:
            return veiculo.viagem_recarga

        # Caso contrário, usar a primeira viagem de pedido ativa
        for v in getattr(veiculo, 'viagens', []):
            if v.viagem_ativa:
                return v

        return None

    def _desenhar_legenda(self):
        """Desenha a legenda do grafo."""
        legend_elements = [
            mpatches.Patch(facecolor='#4169E1', edgecolor='black', label='Local'),
            mpatches.Patch(facecolor='#FF4500', edgecolor='black', label='⛽ Posto Gasolina'),
            mpatches.Patch(facecolor='#32CD32', edgecolor='black', label='🔌 Posto Carregamento'),
            mpatches.Patch(facecolor='#8B0000', edgecolor='yellow', label='🚗 Veículo Combustão'),
            mpatches.Patch(facecolor='#006400', edgecolor='yellow', label='🚙 Veículo Elétrico'),
            mpatches.Patch(facecolor='#90EE90', edgecolor='black', label='─ Trânsito Vazio'),
            mpatches.Patch(facecolor='#87CEEB', edgecolor='black', label='─ Trânsito Normal'),
            mpatches.Patch(facecolor='#FFD700', edgecolor='black', label='─ Trânsito Elevado'),
            mpatches.Patch(facecolor='#FF8C00', edgecolor='black', label='─ Trânsito Muito Elevado'),
            mpatches.Patch(facecolor='#FF0000', edgecolor='black', label='─ Acidente'),
        ]

        self.legend_obj = self.ax.legend(
            handles=legend_elements,
            loc='upper left',
            fontsize=9,
            framealpha=0.9,
            fancybox=True,
            shadow=True
        )

    def _desenhar_estatisticas(self):
        """Desenha as estatísticas da simulação."""
        if not self.metricas:
            return

        stats_lines = [
            "📊 ESTATÍSTICAS",
            "─────────────────",
            f'Pedidos Atendidos: {self.metricas.pedidos_atendidos}',
            f'Pedidos Rejeitados: {self.metricas.pedidos_rejeitados}',
            f'Viagens Ativas: {len(self.viagens_ativas)}',
        ]

        if self.metricas.pedidos_atendidos > 0:
            tempo_medio = self.metricas.tempo_resposta_total / self.metricas.pedidos_atendidos
            stats_lines.append(f'Tempo Médio Resposta: {tempo_medio:.2f} min')

        stats_text = "\n".join(stats_lines)

        if self.stats_ax is not None:
            self.stats_ax.clear()
            self.stats_ax.axis('off')
            self.stats_ax.text(0.01, 0.99, stats_text, va='top',
                               ha='left', fontsize=10, family='monospace')
            try:
                self.stats_fig.canvas.draw_idle()
                self.stats_fig.canvas.flush_events()
            except Exception:
                pass
        else:
            # Remover texto antigo se existir
            if self.stats_text_obj:
                self.stats_text_obj.remove()

            bbox_stats = {
                'boxstyle': 'round,pad=0.8',
                'facecolor': 'white',
                'alpha': 0.9,
                'edgecolor': 'black',
                'linewidth': 2,
            }

            self.stats_text_obj = self.ax.text(
                0.98,
                0.02,
                stats_text,
                transform=self.ax.transAxes,
                fontsize=10,
                verticalalignment='bottom',
                horizontalalignment='right',
                bbox=bbox_stats,
                fontfamily='monospace',
            )

    def atualizar(self, pedido, veiculo, rota):
        """Atualiza o display com informações de um pedido processado."""
        pass

    def set_metricas(self, metricas):
        """Define o objeto de métricas."""
        self.metricas = metricas

    def finalizar(self):
        """Finaliza o display e mostra métricas finais."""
        try:
            if getattr(self, 'stats_fig', None) is not None:
                try:
                    plt.close(self.stats_fig)
                except Exception:
                    pass

            if getattr(self, 'fig', None) is not None:
                plt.ioff()
                plt.show()
        except Exception:
            pass

    def mostrar_metricas_finais(self):
        """Mostra as métricas finais da simulação."""
        print("\n" + "=" * 80)
        print("📊 MÉTRICAS FINAIS DA SIMULAÇÃO")
        print("=" * 80)

        if self.metricas:
            print(f"Pedidos Atendidos: {self.metricas.pedidos_atendidos}")
            print(f"Pedidos Rejeitados: {self.metricas.pedidos_rejeitados}")

            if self.metricas.pedidos_atendidos > 0:
                tempo_medio = self.metricas.tempo_resposta_total / self.metricas.pedidos_atendidos
                print(f"Tempo Médio de Resposta: {tempo_medio:.2f} minutos")

            total_pedidos = self.metricas.pedidos_atendidos + self.metricas.pedidos_rejeitados
            if total_pedidos > 0:
                taxa_sucesso = (self.metricas.pedidos_atendidos / total_pedidos) * 100
                print(f"Taxa de Sucesso: {taxa_sucesso:.1f}%")

        print("=" * 80)
