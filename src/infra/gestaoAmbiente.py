"""
Módulo de gestão do ambiente da simulação.
Contém o grafo da cidade, frota de veículos e pedidos.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime

from infra.grafo.grafo import Grafo
from infra.entidades.veiculos import Veiculo, VeiculoCombustao, VeiculoEletrico, EstadoVeiculo
from infra.entidades.pedidos import Pedido, EstadoPedido
from infra.entidades.viagem import Viagem


class GestaoAmbiente:
    """
    Classe que representa o ambiente completo da simulação:
    - Grafo da cidade
    - Frota de veículos
    - Lista de pedidos
    """

    def __init__(self):
        self.grafo: Optional[Grafo] = None
        self._veiculos: Dict[int, Veiculo] = {}
        self._pedidos: Dict[int, Pedido] = {}

    # -------------------- Carregar dados --------------------

    def carregar_grafo(self, caminho: str) -> int:
        """Carrega o grafo a partir de um ficheiro JSON."""
        self.grafo = Grafo.from_json_file(caminho)
        return len(self.grafo.getNodes())

    def carregar_veiculos(self, caminho: str) -> int:
        """Carrega a frota de veículos a partir de um ficheiro JSON."""
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        num_veiculos_carregados = 0

        for v_data in dados.get('veiculos', []):
            tipo = v_data.get('tipo', '').lower()
            estado_str = v_data.get('estado', 'DISPONIVEL')
            estado = EstadoVeiculo[estado_str]

            # Localização inicial (pode ser nome do nó ou ID)
            localizacao_inicial = v_data.get('localizacao_atual', 0)
            # Se for string (nome do nó), manter como string
            # O código será atualizado para aceitar ambos

            if tipo == 'combustao':
                veiculo = VeiculoCombustao(
                    id_veiculo=v_data['id_veiculo'],
                    autonomia_maxima=v_data['autonomia_maxima'],
                    autonomia_atual=v_data['autonomia_atual'],
                    capacidade_passageiros=v_data['capacidade_passageiros'],
                    custo_operacional_km=v_data['custo_operacional_km'],
                    localizacao_atual=localizacao_inicial
                )
            elif tipo == 'eletrico':
                veiculo = VeiculoEletrico(
                    id_veiculo=v_data['id_veiculo'],
                    autonomia_maxima=v_data['autonomia_maxima'],
                    autonomia_atual=v_data['autonomia_atual'],
                    capacidade_passageiros=v_data['capacidade_passageiros'],
                    custo_operacional_km=v_data['custo_operacional_km'],
                    tempo_recarga_km=v_data.get('tempo_recarga_km', 2),
                    localizacao_atual=localizacao_inicial
                )
            else:
                continue

            veiculo._estado = estado
            self._veiculos[veiculo.id_veiculo] = veiculo
            num_veiculos_carregados += 1

        return num_veiculos_carregados

    def carregar_pedidos(self, caminho: str) -> int:
        """Carrega os pedidos de transporte a partir de um ficheiro JSON."""
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        num_pedidos_carregados = 0

        for p_data in dados.get('pedidos', []):
            horario_str = p_data.get('horario_pretendido', '')
            horario = datetime.fromisoformat(horario_str)
            estado_str = p_data.get('estado', 'PENDENTE')
            estado = EstadoPedido[estado_str]

            pedido = Pedido(
                pedido_id=p_data['pedido_id'],
                origem=p_data['origem'],
                destino=p_data['destino'],
                passageiros=p_data['passageiros'],
                horario_pretendido=horario,
                prioridade=p_data.get('prioridade', 1),
                preferencia_ambiental=p_data.get('preferencia_ambiental', 0),
                ride_sharing=p_data.get('ride_sharing', False)
            )
            pedido._estado = estado
            self._pedidos[pedido.id] = pedido
            num_pedidos_carregados += 1
        
        return num_pedidos_carregados

    # -------------------- Veículos --------------------
    def adicionar_veiculo(self, veiculo: Veiculo):
        """Adiciona um veículo à frota."""
        self._veiculos[veiculo.id_veiculo] = veiculo

    def obter_veiculo(self, id_veiculo: int) -> Optional[Veiculo]:
        """Obtém um veículo pelo ID."""
        return self._veiculos.get(id_veiculo)

    def listar_veiculos(self) -> List[Veiculo]:
        """Retorna lista de todos os veículos."""
        return list(self._veiculos.values())

    def listar_veiculos_disponiveis(self) -> List[Veiculo]:
        """Retorna apenas veículos disponíveis."""
        return [v for v in self._veiculos.values()
                if v.estado == EstadoVeiculo.DISPONIVEL]

    def listar_veiculos_ridesharing(self) -> List[Veiculo]:
        """Retorna veículos elegíveis para ride-sharing:
        - Veículos disponíveis
        - Veículos em andamento onde TODOS os pedidos das viagens ativas permitem ride-sharing
        """
        return [v for v in self._veiculos.values()
                if v.estado in (EstadoVeiculo.DISPONIVEL, EstadoVeiculo.EM_ANDAMENTO)
                and v.aceita_ridesharing]

    def remover_veiculo(self, id_veiculo: int) -> Optional[Veiculo]:
        """Remove um veículo da frota pelo ID."""
        return self._veiculos.pop(id_veiculo, None)

    # -------------------- Pedidos --------------------
    def adicionar_pedido(self, pedido: Pedido):
        """Adiciona um pedido."""
        self._pedidos[pedido.id] = pedido

    def arranjaId_pedido(self):
        """Gera um novo ID único para um pedido."""
        if not self._pedidos:
            return 1
        return max(self._pedidos.keys()) + 1

    def obter_pedido(self, id_pedido: int) -> Optional[Pedido]:
        """Obtém um pedido pelo ID."""
        return self._pedidos.get(id_pedido)

    def listar_pedidos(self) -> List[Pedido]:
        """Retorna lista de todos os pedidos."""
        return list(self._pedidos.values())

    def listar_pedidos_pendentes(self) -> List[Pedido]:
        """Retorna apenas pedidos pendentes."""
        return [p for p in self._pedidos.values()
                if p.estado == EstadoPedido.PENDENTE]

    def remover_pedido(self, pedido_id: int) -> Optional[Pedido]:
        """Remove um pedido pelo ID."""
        return self._pedidos.pop(pedido_id, None)

    # -------------------- Atribuição de Pedidos a Veículos --------------------
    def atribuir_pedido_a_veiculo(self, pedido: Pedido, veiculo: Veiculo) -> bool:
        """Atribui um pedido a um veículo já escolhido e atualiza os estados."""
        if pedido is None or veiculo is None:
            return False

        pedido.atribuir_a = veiculo.id_veiculo
        pedido.estado = pedido.estado.EM_CURSO
        veiculo.estado = veiculo.estado.EM_ANDAMENTO

        return True

    def iniciar_viagem(self, pedido: Pedido, veiculo: Veiculo,
                       rota_ate_cliente: List[str], rota_pedido: List[str],
                       distancia_ate_cliente: float, distancia_pedido: float,
                       tempo_inicio, velocidade_media: float = 50.0) -> bool:
        """Inicia uma nova viagem no veículo e regista como ativa no ambiente."""
        iniciou = veiculo.iniciar_viagem(
            pedido=pedido,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_pedido,
            distancia_ate_cliente=distancia_ate_cliente,
            distancia_pedido=distancia_pedido,
            tempo_inicio=tempo_inicio,
            grafo=self.grafo,
            velocidade_media=velocidade_media,
        )
        return iniciou

    def marcar_pedido_concluido(self, pedido: Pedido) -> bool:
        """Marca um pedido como concluído (sem manipular viagens diretamente)."""
        if pedido is None:
            return False
        pedido.estado = pedido.estado.CONCLUIDO
        return True
    
    def concluir_pedido(self, pedido_id: int, viagem: Viagem) -> bool:
        """Marca um pedido como concluído e atualiza o veículo associado.
        """
        pedido = self.obter_pedido(pedido_id)
        if pedido is None or pedido.atribuir_a is None:
            return False

        veiculo = self.obter_veiculo(pedido.atribuir_a)
        if veiculo is None:
            return False

        self.marcar_pedido_concluido(pedido)
        veiculo.concluir_viagem(viagem)
        return True

    # -------------------- Cálculos Auxiliares --------------------

    def _calcular_distancia_rota(self, rota) -> float:
        """Cálculo de distância delegando no grafo."""
        if not self.grafo:
            return 0.0
        return self.grafo.calcular_distancia_rota(rota)

    def _calcular_tempo_rota(self, rota) -> float:
        """Cálculo de tempo delegando no grafo."""
        if not self.grafo:
            return 0.0
        return self.grafo.calcular_tempo_rota(rota)

    def _calcular_emissoes(self, veiculo, distancia: float) -> float:
        """Calcula as emissões de CO₂ de uma viagem."""
        if isinstance(veiculo, VeiculoEletrico):
            return 0.0
        else:
            return distancia * 0.12 #NOTA: valor fictício de emissões por km para veículos a combustão pode ser ajustado conforme necessário
        
    def getRandomNodePair(self):
        inicio = self.grafo.getRandomNodo()
        inicio_nome = inicio.getName()

        vizinhos = [v for (v, _) in self.grafo.getNeighbours(inicio_nome)]

        fim = self.grafo.getRandomNodo()
        while fim.getName() in vizinhos:
            fim = self.grafo.getRandomNodo()

        return (inicio, fim)

    
    # -------------------- Recálculo de Rotas --------------------
    
    def identificar_viagens_afetadas(self, arestas_alteradas: set, viagens_ativas: dict):
        """Identifica viagens afetadas por alterações de trânsito.
        
        Args:
            arestas_alteradas: Set de arestas que tiveram alteração de trânsito
            viagens_ativas: Dicionário de veículos com viagens ativas
            
        Returns:
            Lista de tuplas (veiculo_id, veiculo, viagens_afetadas, aresta)
        """
        if not viagens_ativas or not arestas_alteradas:
            return []
        
        viagens_para_recalcular = []
        
        for aresta in arestas_alteradas:
            for veiculo_id, veiculo in viagens_ativas.items():
                viagens_afetadas = veiculo.viagens_afetadas_por_aresta(aresta, self.grafo)
                
                if viagens_afetadas:
                    viagens_para_recalcular.append((
                        veiculo_id, 
                        veiculo, 
                        viagens_afetadas,
                        aresta
                    ))
        
        return viagens_para_recalcular
    
    def aplicar_nova_rota(self, viagem, nova_rota):
        """Aplica nova rota a uma viagem e retorna informações.
        
        Args:
            viagem: Viagem a atualizar
            nova_rota: Nova rota a aplicar
            
        Returns:
            Dict com {pedido_id, delta_tempo, distancia_anterior, distancia_nova} ou None
        """
        tempo_anterior = viagem.tempo_restante_horas()
        distancia_anterior = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
        
        if viagem.aplicar_nova_rota(nova_rota, self.grafo):
            tempo_novo = viagem.tempo_restante_horas()
            distancia_nova = sum(seg['distancia'] for seg in viagem.segmentos[viagem.indice_segmento_atual:])
            delta = (tempo_novo - tempo_anterior) * 60
            
            return {
                'pedido_id': viagem.pedido_id,
                'delta_tempo': delta,
                'distancia_anterior': distancia_anterior,
                'distancia_nova': distancia_nova
            }
        return None
    
    # -------------------- Gestão de Recarga --------------------
    
    def executar_recarga(self, veiculo) -> float:
        """Executa a recarga de um veículo e retorna autonomia recarregada.
        
        Args:
            veiculo: Veículo a reabastecer
            
        Returns:
            Autonomia recarregada em km
        """
        autonomia_anterior = veiculo.autonomia_atual
        veiculo.reabastecer()
        return veiculo.autonomia_atual - autonomia_anterior
    
    # -------------------- Processamento de Viagens --------------------
    
    def atualizar_viagens_ativas(self, viagens_ativas: dict, tempo_passo_horas: float):
        """Atualiza o progresso de todas as viagens em curso.
        
        Args:
            viagens_ativas: Dicionário de veículos com viagens ativas
            tempo_passo_horas: Tempo simulado decorrido neste passo, em horas
            
        Returns:
            Tupla (viagens_concluidas, veiculos_chegaram_posto)
        """
        if not viagens_ativas:
            return ([], [])
        
        viagens_concluidas = []
        veiculos_chegaram_posto = []
        
        for veiculo_id, veiculo in list(viagens_ativas.items()):
            # Processar viagem de recarga
            if veiculo.viagem_recarga and veiculo.viagem_recarga.viagem_ativa:
                distancia_antes = veiculo.viagem_recarga.distancia_percorrida
                concluida = veiculo.viagem_recarga.atualizar_progresso(tempo_passo_horas)
                distancia_depois = veiculo.viagem_recarga.distancia_percorrida
                distancia_avancada = max(0.0, distancia_depois - distancia_antes)
                veiculo.atualizar_autonomia(distancia_avancada)
                
                # Atualizar localização enquanto viaja
                if veiculo.viagem_recarga.localizacao_atual:
                    veiculo._localizacao_atual = veiculo.viagem_recarga.localizacao_atual
                
                if concluida:
                    veiculo.concluir_viagem_recarga()
                    veiculos_chegaram_posto.append((veiculo_id, veiculo))
                continue
            
            # Atualizar viagens normais
            concluidas = veiculo.atualizar_progresso_viagem(tempo_passo_horas)
            for v in concluidas:
                viagens_concluidas.append((veiculo_id, veiculo, v))
        
        return (viagens_concluidas, veiculos_chegaram_posto)
    
    # -------------------- Processamento de Pedidos --------------------
    
    def obter_nomes_nos_pedido(self, pedido):
        """Obtém os nomes dos nós de origem e destino de um pedido.
        
        Args:
            pedido: Pedido a processar
            
        Returns:
            Tupla (origem_nome, destino_nome)
        """
        origem_pedido_nome = self.grafo.getNodeName(pedido.origem)
        destino_nome = self.grafo.getNodeName(pedido.destino)
        return (origem_pedido_nome, destino_nome)
    
    def obter_rota_atual_veiculo(self, veiculo):
        """Obtém a rota total atual do veículo."""
        return veiculo.rota_total_viagens()
    
    
    def listar_postos_por_tipo(self, tipo_posto):
        """Lista todos os postos de um tipo específico.
        
        Args:
            tipo_posto: Tipo de posto (TipoNodo)
            
        Returns:
            Lista de nomes de postos
        """
        return self.grafo.get_nodes_by_tipo(tipo_posto)


