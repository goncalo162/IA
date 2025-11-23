from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
from typing import Optional
import matplotlib.patches as mpatches
from infra.grafo.node import TipoNodo
from infra.entidades.veiculos import VeiculoCombustao
from display.aplicacao.interacoes import register_interactions

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
        # Tempo real entre redesenhos em segundos
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
        self.velocidade_simulacao = 1.0  # Armazenar velocidade de simulação para exibir
        self.inicializado = False

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
        """
        Define a velocidade de simulação para exibição.

        Args:
            velocidade: Velocidade de simulação (ex: 1.0, 10.0, 500.0)
        """
        self.velocidade_simulacao = velocidade

    def _criar_grafo(self):
        """Cria o grafo NetworkX a partir do grafo do ambiente."""
        self.G = nx.DiGraph()
        grafo = self.ambiente.grafo

        # Adicionar nós (inclui x/y se disponíveis no Node)
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

        # Adicionar arestas usando nomes de nós
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

        '''  

        # Ler posições x/y dos atributos dos nós (fornecidos no JSON). Se
        # qualquer nó não tiver coordenadas, usar spring_layout apenas para
        # preencher os ausentes e manter os valores definidos no JSON.

        self.pos = {}
        missing = []
        for n, data in self.G.nodes(data=True):
            x = data.get('x')
            y = data.get('y')
            if x is None or y is None:
                missing.append(n)
            else:
                try:
                    self.pos[n] = (float(x), float(y))
                except Exception:
                    missing.append(n)

        if missing:
            layout = nx.spring_layout(self.G, k=2, iterations=50, seed=42)
            for n in missing:
                x, y = layout[n]
                self.G.nodes[n]['x'] = float(x)
                self.G.nodes[n]['y'] = float(y)
                self.pos[n] = (float(x), float(y))

        '''

        self.pos = nx.kamada_kawai_layout(self.G)

    def _inicializar_plot(self):
        """Inicializa a janela do Matplotlib."""
        # Desativar toolbar para a janela principal
        try:
            plt.rcParams['toolbar'] = 'None'
        except Exception:
            pass

        plt.ion()  # Modo interativo
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        # associar canvas para compatibilidade com handlers que usam app.canvas
        self.canvas = self.fig.canvas
        self.fig.canvas.manager.set_window_title(
            'Simulação de Frota - Visualização em Tempo Real')

        # Configurar axes
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # Criar janela separada para estatísticas
        try:
            self.stats_fig, self.stats_ax = plt.subplots(figsize=(4, 6))
            self.stats_fig.canvas.manager.set_window_title(
                'Estatísticas da Simulação')
            self.stats_ax.axis('off')
        except Exception:
            # Em ambientes headless a criação da janela pode falhar; usar None como fallback
            self.stats_fig = None
            self.stats_ax = None

        # Registrar interações (pan/zoom/drag) usando o module de interações
        try:
            # register_interactions espera app.canvas e app.ax etc.; our self.canvas is fig.canvas
            register_interactions(self)
        except Exception:
            # Não falhar se algo não for suportado no backend atual
            pass

    def atualizar_tempo_simulacao(self, tempo: datetime, viagens_ativas: list):
        """
        Atualiza a visualização com o tempo atual e viagens ativas.

        Args:
            tempo: Tempo atual da simulação
            viagens_ativas: Lista de objetos Viagem atualmente em andamento
        """
        if not self.inicializado:
            return

        # Controlar frequência de atualização
        agora = datetime.now()
        if self.ultimo_update and (agora - self.ultimo_update).total_seconds() < self.intervalo_update:
            return

        self.ultimo_update = agora
        self.tempo_atual = tempo
        self.viagens_ativas = viagens_ativas

        # Redesenhar o grafo
        self._desenhar_grafo()

    def _desenhar_grafo(self):
        """Desenha o grafo completo com veículos."""
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # Título com tempo atual
        tempo_str = self.tempo_atual.strftime(
            "%H:%M:%S") if self.tempo_atual else "00:00:00"
        self.ax.set_title(
            f' Simulação de Frota em Tempo Real\n'
            f'Tempo: {tempo_str} | Viagens Ativas: {len(self.viagens_ativas)} | '
            f'Velocidade: {self.velocidade_simulacao}x',
            fontsize=14,
            fontweight='bold',
            pad=20
        )

        # Desenhar arestas
        self._desenhar_arestas()

        # Desenhar nós
        self._desenhar_nos()

        # Desenhar veículos
        self._desenhar_veiculos()

        # Desenhar legenda
        self._desenhar_legenda()

        # Desenhar estatísticas
        self._desenhar_estatisticas()

        # Atualizar canvas
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _desenhar_arestas(self):
        """Desenha as arestas do grafo."""
        # Separar arestas por nível de trânsito
        edge_colors = []
        edge_widths = []

        for origem, destino, data in self.G.edges(data=True):
            transito = data.get('transito', 'NORMAL')

            # Cores baseadas no trânsito
            if transito == 'VAZIO':
                cor = '#90EE90'  # Verde claro
                largura = 1.0
            elif transito == 'NORMAL':
                cor = '#87CEEB'  # Azul claro
                largura = 1.0
            elif transito == 'ELEVADO':
                cor = '#FFD700'  # Dourado
                largura = 1.0
            elif transito == 'MUITO_ELEVADO':
                cor = '#FF8C00'  # Laranja escuro
                largura = 1.0
            elif transito == 'ACIDENTE':
                cor = '#FF0000'  # Vermelho
                largura = 1.0
            else:
                cor = '#808080'  # Cinza
                largura = 1.0

            edge_colors.append(cor)
            edge_widths.append(largura)

        # Desenhar todas as arestas
        nx.draw_networkx_edges(
            self.G,
            self.pos,
            edge_color=edge_colors,
            width=edge_widths,
            arrows=False,
            ax=self.ax,
            connectionstyle='arc3,rad=0'
        )

        # Labels de distância nas arestas
        edge_labels = {}
        for origem, destino, data in self.G.edges(data=True):
            distancia = data.get('distancia', 0)
            velocidade = data.get('velocidade', 0)
            edge_labels[(origem, destino)
                        ] = f'{distancia:.1f}km\n{velocidade}km/h'

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
        # Separar nós por tipo
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

        # Desenhar nós locais
        if nodes_local:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_local,
                node_color='#4169E1',  # Azul royal
                node_size=1000,
                node_shape='o',
                alpha=0.9,
                ax=self.ax
            )

        # Desenhar postos de gasolina
        if nodes_gasolina:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_gasolina,
                node_color='#FF4500',  # Laranja avermelhado
                node_size=1000,
                node_shape='s',  # Quadrado
                alpha=0.9,
                ax=self.ax
            )

        # Desenhar postos de carregamento
        if nodes_carregamento:
            nx.draw_networkx_nodes(
                self.G,
                self.pos,
                nodelist=nodes_carregamento,
                node_color='#32CD32',  # Verde lima
                node_size=1000,
                node_shape='^',  # Triângulo
                alpha=0.9,
                ax=self.ax
            )

        # Labels dos nós
        labels = {node_id: data['nome']
                  for node_id, data in self.G.nodes(data=True)}
        nx.draw_networkx_labels(
            self.G,
            self.pos,
            labels,
            font_size=4,
            font_color='black',
            ax=self.ax
        )

    def _desenhar_veiculos(self):
        """Desenha os veículos nas suas posições atuais (em viagem e parados)."""

        # Obter todos os veículos
        todos_veiculos = self.ambiente.listar_veiculos()

        for veiculo in todos_veiculos:
            # Determinar cor e marcador baseado no tipo
            if isinstance(veiculo, VeiculoCombustao):
                cor_veiculo = '#8B0000'  # Vermelho escuro (combustão)
                marcador = 'o'
            else:
                cor_veiculo = '#006400'  # Verde escuro (elétrico)
                marcador = 's'

            # Verificar se está em viagem ou parado
            if veiculo.viagem_ativa:
                # Veículo em movimento - calcular posição interpolada
                posicao = self._calcular_posicao_veiculo(veiculo)

                if posicao:
                    x, y = posicao

                    # Desenhar veículo em movimento (borda amarela)
                    self.ax.plot(
                        x, y,
                        marker=marcador,
                        markersize=15,
                        color=cor_veiculo,
                        markeredgecolor='yellow',
                        markeredgewidth=2,
                        zorder=10
                    )

                    # Label com progresso
                    progresso = veiculo.progresso_percentual
                    self.ax.text(
                        x, y + 0.08,
                        f'V{veiculo.id_veiculo}\n{progresso:.0f}%',
                        fontsize=8,
                        ha='center',
                        va='bottom',
                        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': 'yellow',
                              'alpha': 0.8, 'edgecolor': 'black'},
                        zorder=11,
                    )
            else:
                # Veículo parado - renderizar na localização atual
                node_nome = veiculo.localizacao_atual
                node_id = self.ambiente.grafo.getNodeId(node_nome)

                if node_id in self.pos:
                    x, y = self.pos[node_id]

                    # Desenhar veículo parado (borda branca, mais transparente)
                    self.ax.plot(
                        x, y,
                        marker=marcador,
                        markersize=12,
                        color=cor_veiculo,
                        markeredgecolor='white',
                        markeredgewidth=1.5,
                        alpha=0.7,
                        zorder=9
                    )

                    # Label com estado
                    estado_str = veiculo.estado.name
                    self.ax.text(
                        x, y + 0.08,
                        f'V{veiculo.id_veiculo}\n{estado_str}',
                        fontsize=7,
                        ha='center',
                        va='bottom',
                        bbox={'boxstyle': 'round,pad=0.3', 'facecolor': 'lightgray',
                              'alpha': 0.7, 'edgecolor': 'black'},
                        zorder=10,
                    )

    def _calcular_posicao_veiculo(self, veiculo) -> Optional[tuple]:
        """
        Calcula a posição interpolada de um veículo na sua rota.

        Args:
            veiculo: Objeto Veiculo com informações da viagem ativa

        Returns:
            Tupla (x, y) com a posição do veículo, ou None se não puder calcular
        """
        if not veiculo.viagem_ativa or not veiculo.viagem.rota or len(veiculo.viagem.rota) < 2:
            # Veículo está parado no nó inicial
            if veiculo.viagem.rota and len(veiculo.viagem.rota) == 1:
                node_nome = veiculo.viagem.rota[0]
                node_id = self.ambiente.grafo.getNodeId(node_nome)
                if node_id in self.pos:
                    return self.pos[node_id]
            return None

        # Obter progresso
        progresso_decimal = veiculo.progresso_percentual / 100.0

        # Encontrar em qual segmento da rota o veículo está
        num_segmentos = len(veiculo.viagem.rota) - 1
        posicao_segmento = progresso_decimal * num_segmentos
        indice_segmento = int(posicao_segmento)

        # Garantir que não ultrapassamos o último segmento
        if indice_segmento >= num_segmentos:
            indice_segmento = num_segmentos - 1
            progresso_no_segmento = 1.0
        else:
            progresso_no_segmento = posicao_segmento - indice_segmento

        # Obter nós de origem e destino do segmento atual
        origem_nome = veiculo.viagem.rota[indice_segmento]
        destino_nome = veiculo.viagem.rota[indice_segmento + 1]
        origem_id = self.ambiente.grafo.getNodeId(origem_nome)
        destino_id = self.ambiente.grafo.getNodeId(destino_nome)

        if origem_id not in self.pos or destino_id not in self.pos:
            return None

        # Interpolar posição
        x_origem, y_origem = self.pos[origem_id]
        x_destino, y_destino = self.pos[destino_id]

        x = x_origem + (x_destino - x_origem) * progresso_no_segmento
        y = y_origem + (y_destino - y_origem) * progresso_no_segmento

        return (x, y)

    def _desenhar_legenda(self):
        """Desenha a legenda do grafo."""
        legend_elements = [
            mpatches.Patch(facecolor='#4169E1',
                           edgecolor='black', label='Local'),
            mpatches.Patch(facecolor='#FF4500', edgecolor='black',
                           label=' Posto Gasolina'),
            mpatches.Patch(facecolor='#32CD32', edgecolor='black',
                           label=' Posto Carregamento'),
            mpatches.Patch(facecolor='#8B0000', edgecolor='yellow',
                           label=' Veículo Combustão'),
            mpatches.Patch(facecolor='#006400', edgecolor='yellow',
                           label=' Veículo Elétrico'),
            mpatches.Patch(facecolor='#90EE90', edgecolor='black',
                           label='─ Trânsito Vazio'),
            mpatches.Patch(facecolor='#87CEEB', edgecolor='black',
                           label='─ Trânsito Normal'),
            mpatches.Patch(facecolor='#FFD700', edgecolor='black',
                           label='─ Trânsito Elevado'),
            mpatches.Patch(facecolor='#FF8C00', edgecolor='black',
                           label='─ Trânsito Muito Elevado'),
            mpatches.Patch(facecolor='#FF0000',
                           edgecolor='black', label='─ Acidente'),
        ]

        self.ax.legend(
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

        # Preparar texto com as métricas
        stats_lines = [
            " ESTATÍSTICAS",
            "───────────────",
            f'Pedidos Atendidos: {self.metricas.pedidos_atendidos}',
            f'Pedidos Rejeitados: {self.metricas.pedidos_rejeitados}',
            f'Viagens Ativas: {len(self.viagens_ativas)}',
        ]

        if self.metricas.pedidos_atendidos > 0:
            tempo_medio = self.metricas.tempo_resposta_total / self.metricas.pedidos_atendidos
            stats_lines.append(f'Tempo Médio Resposta: {tempo_medio:.2f} min')

        # Se houver figura de estatísticas, desenhar lá; caso contrário desenhar no canto da figura principal
        stats_text = "\n".join(stats_lines)

        if self.stats_ax is not None:
            self.stats_ax.clear()
            self.stats_ax.axis('off')
            # usar monospace para alinhar melhor
            self.stats_ax.text(0.01, 0.99, stats_text, va='top',
                               ha='left', fontsize=10, family='monospace')
            try:
                self.stats_fig.canvas.draw()
                self.stats_fig.canvas.flush_events()
            except Exception:
                pass
        else:
            # Fallback: desenhar no eixo principal (antigo comportamento)
            bbox_stats = {
                'boxstyle': 'round,pad=0.8',
                'facecolor': 'white',
                'alpha': 0.9,
                'edgecolor': 'black',
                'linewidth': 2,
            }

            self.ax.text(
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

    # TODO: rever isto, ver se o que esta deve fazer ou passar o que esta na outra para esta
    def atualizar(self, pedido, veiculo, rota):
        """Atualiza o display com informações de um pedido processado."""
        # Para o display gráfico, a atualização acontece em atualizar_tempo_simulacao
        pass

    def set_metricas(self, metricas):
        """Define o objeto de métricas."""
        self.metricas = metricas

    def finalizar(self):
        """Finaliza o display e mostra métricas finais."""
        super().finalizar()

        # Fechar/limpar janelas de matplotlib criadas pelo display
        try:
            # Fechar janela de estatísticas se existir
            if getattr(self, 'stats_fig', None) is not None:
                try:
                    plt.close(self.stats_fig)
                except Exception:
                    pass

            # Mostrar/encerrar figura principal (mantém comportamento anterior)
            if getattr(self, 'fig', None) is not None:
                plt.ioff()
                plt.show()
        except Exception:
            # Não falhar na finalização por causa de problemas com GUI
            pass

    def mostrar_metricas_finais(self):
        """Mostra as métricas finais da simulação."""
        print("\n" + "="*80)
        print(" MÉTRICAS FINAIS DA SIMULAÇÃO")
        print("="*80)

        if self.metricas:
            print(f"Pedidos Atendidos: {self.metricas.pedidos_atendidos}")
            print(f"Pedidos Rejeitados: {self.metricas.pedidos_rejeitados}")

            if self.metricas.pedidos_atendidos > 0:
                tempo_medio = self.metricas.tempo_resposta_total / self.metricas.pedidos_atendidos
                print(f"Tempo Médio de Resposta: {tempo_medio:.2f} minutos")

            total_pedidos = self.metricas.pedidos_atendidos + self.metricas.pedidos_rejeitados
            if total_pedidos > 0:
                taxa_sucesso = (
                    self.metricas.pedidos_atendidos / total_pedidos) * 100
                print(f"Taxa de Sucesso: {taxa_sucesso:.1f}%")

        print("="*80)
