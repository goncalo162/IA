"""
Políticas de reposicionamento proativo de veículos.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from infra.entidades.pedidos import EstadoPedido


class ReposicionamentoPolicy(ABC):
    """Classe abstrata para políticas de reposicionamento proativo."""

    @abstractmethod
    def nome_politica(self) -> str:
        """Retorna o nome da política de reposicionamento."""
        pass


    @abstractmethod
    def decidir_reposicionamentos(
        self,
        veiculos_disponiveis: List,
        grafo,
        ambiente=None,
        tempo_simulacao: datetime = None
    ) -> List[Tuple[object, str]]:
        """
        Decide quais veículos devem ser reposicionados e para onde.

        Args:
            veiculos_disponiveis: Lista de veículos disponíveis para reposicionamento
            grafo: Grafo da rede de transporte
            ambiente: GestaoAmbiente com acesso ao histórico de pedidos
            tempo_simulacao: Tempo atual da simulação

        Returns:
            Lista de tuplas (veiculo, nodo_destino_id) indicando reposicionamentos
        """
        pass

    #### cálculos auxiliares comuns para politicas ####

    def _ordenar_veiculos_por_distancia(self, veiculos: List, zonas_destino: List[str], grafo) -> List:
        """
        Ordena veículos por distância às zonas de destino (mais longe primeiro).

        Args:
            veiculos: Lista de veículos
            zonas_destino: IDs das zonas destino
            grafo: Grafo da rede

        Returns:
            Lista ordenada de veículos
        """
        veiculos_com_dist = []
        for veiculo in veiculos:
            # Calcular distância mínima a qualquer zona destino
            dist_min = float("inf")
            for zona_id in zonas_destino:
                dist = self._calcular_distancia_aproximada(veiculo, zona_id, grafo)
                dist_min = min(dist_min, dist)
            veiculos_com_dist.append((veiculo, dist_min))

        # Ordenar por distância (mais longe primeiro = mais necessidade de reposicionar)
        veiculos_com_dist.sort(key=lambda x: x[1], reverse=True)
        return [v for v, _ in veiculos_com_dist]

    def _calcular_distancia_aproximada(self, veiculo, zona_destino: str, grafo) -> float:
        """
        Calcula distância aproximada (heurística) do veículo a uma zona.

        Args:
            veiculo: Veículo
            zona_destino: ID do nodo destino
            grafo: Grafo da rede

        Returns:
            Distância aproximada em km
        """
        try:
            origem = str(veiculo.localizacao_atual)
            destino = str(zona_destino)

            # Se origem = destino, distância zero
            if origem == destino:
                return 0.0
            
            # Tentar usar distância euclidiana se coordenadas disponíveis (Heurística simples baseada em coordenadas)
            node_origem = grafo.get_node_by_name(origem)
            node_destino = grafo.get_node_by_name(destino)

            if node_origem and node_destino:
                x1 = node_origem.getX()
                y1 = node_origem.getY()
                x2 = node_destino.getX()
                y2 = node_destino.getY()

                if x1 is not None and x2 is not None and y1 is not None and y2 is not None:
                    dx = x2 - x1
                    dy = y2 - y1
                    return (dx ** 2 + dy ** 2) ** 0.5

            return 100.0 # Retornar distância alta se não conseguir calcular
        except Exception:
            return 100.0
        
class ReposicionamentoNulo(ReposicionamentoPolicy):
    """Política que não faz reposicionamento."""

    def nome_politica(self) -> str:
        return "ReposicionamentoNulo"

    def decidir_reposicionamentos(
        self,
        veiculos_disponiveis: List,
        grafo,
        ambiente=None,
        tempo_simulacao: datetime = None
    ) -> List[Tuple[object, str]]:
        """Não realiza reposicionamentos."""
        return []



class ReposicionamentoAtratividade(ReposicionamentoPolicy):
    """
    Política de reposicionamento baseada na atratividade dos nós do grafo.

    Seleciona as zonas com maior atratividade (atributo do Node) e reposiciona
    um percentual dos veículos disponíveis para essas zonas, priorizando
    veículos mais distantes das zonas quentes.
    """
    #TODO: PASSAR ESTES VALORES PARA O .ENV, EVITAR "MAGIC NUMBERS"
    def __init__(
        self,
        top_k_zonas: int = 3,
        percentual_veiculos_reposicionar: float = 0.3,
        distancia_maxima_reposicionamento: float = 100.0,
        intervalo_reposicionamento_minutos: int = 15,
    ):
        self.top_k_zonas = top_k_zonas
        self.percentual_veiculos_reposicionar = percentual_veiculos_reposicionar
        self.distancia_maxima_reposicionamento = distancia_maxima_reposicionamento
        self.intervalo_reposicionamento_minutos = intervalo_reposicionamento_minutos

        self.ultimo_reposicionamento: Optional[datetime] = None

    def nome_politica(self) -> str:
        return f'ReposicionamentoAtratividade(top_k={self.top_k_zonas}, pct={self.percentual_veiculos_reposicionar})'

    def decidir_reposicionamentos(
        self,
        veiculos_disponiveis: List,
        grafo,
        ambiente=None,
        tempo_simulacao: datetime = None,
    ) -> List[Tuple[object, str]]:
        # Evitar reposicionamentos muito frequentes
        if self.ultimo_reposicionamento is not None and tempo_simulacao is not None:
            delta = (tempo_simulacao - self.ultimo_reposicionamento).total_seconds() / 60
            if delta < self.intervalo_reposicionamento_minutos:
                return []

        if not veiculos_disponiveis:
            return []

        # Construir mapa de atratividade a partir dos nodes do grafo
        zonas = grafo.getNodes()
        zonas_atratividade = {n.getName(): n.getAtratividade() for n in zonas}

        # Filtrar zonas sem atratividade
        zonas_atratividade = {k: v for k, v in zonas_atratividade.items() if v and v > 0}
        if not zonas_atratividade:
            return []

        top_zonas = sorted(zonas_atratividade.items(), key=lambda x: x[1], reverse=True)[: self.top_k_zonas]
        top_zonas_ids = [zona_id for zona_id, _ in top_zonas]

        num_veiculos_reposicionar = max(1, int(len(veiculos_disponiveis) * self.percentual_veiculos_reposicionar))

        veiculos_ordenados = self._ordenar_veiculos_por_distancia(veiculos_disponiveis, top_zonas_ids, grafo)

        reposicionamentos = []
        for veiculo in veiculos_ordenados:
            if len(reposicionamentos) >= num_veiculos_reposicionar:
                break

            idx_zona = len(reposicionamentos) % len(top_zonas_ids)
            zona_destino = top_zonas_ids[idx_zona]

            distancia = self._calcular_distancia_aproximada(veiculo, zona_destino, grafo)
            if distancia <= self.distancia_maxima_reposicionamento:
                reposicionamentos.append((veiculo, zona_destino))

        if reposicionamentos and tempo_simulacao is not None:
            self.ultimo_reposicionamento = tempo_simulacao

        return reposicionamentos




#NOTA: REVER ESTA POLITICA, FOI GERADA PELO COPILOT, SO DEI UMA VISTA DE OLHOS POR ALTO
class ReposicionamentoEstatistico(ReposicionamentoPolicy):
    """
    Política de reposicionamento baseada em análise estatística de demanda histórica.

    Usa histograma de origens de pedidos por janela temporal para identificar
    zonas de alta atratividade e reposicionar veículos proativamente.
    """

    def __init__(
        self,
        janela_historico_minutos: int = 60,
        intervalo_reposicionamento_minutos: int = 15,
        top_k_zonas: int = 3,
        percentual_veiculos_reposicionar: float = 0.3,
        distancia_maxima_reposicionamento: float = 10.0
    ):
        """
        Inicializa a política de reposicionamento estatístico.

        Args:
            janela_historico_minutos: Tamanho da janela de histórico a considerar
            intervalo_reposicionamento_minutos: Intervalo mínimo entre reposicionamentos
            top_k_zonas: Número de zonas de maior demanda a considerar
            percentual_veiculos_reposicionar: Percentual máximo de veículos disponíveis a reposicionar
            distancia_maxima_reposicionamento: Distância máxima (km) para reposicionar um veículo
        """
        self.janela_historico_minutos = janela_historico_minutos
        self.intervalo_reposicionamento_minutos = intervalo_reposicionamento_minutos
        self.top_k_zonas = top_k_zonas
        self.percentual_veiculos_reposicionar = percentual_veiculos_reposicionar
        self.distancia_maxima_reposicionamento = distancia_maxima_reposicionamento

        # Última vez que ocorreu reposicionamento
        self.ultimo_reposicionamento: Optional[datetime] = None
        # Histórico interno (compatibilidade retroativa para testes e chamadas)
        # lista de (timestamp, nodo_origem)
        self.historico_demanda: List[Tuple[datetime, str]] = []

    def nome_politica(self) -> str:
        """Retorna o nome da política de reposicionamento."""
        return f'ReposicionamentoEstatistico(janela={self.janela_historico_minutos}min, top_k={self.top_k_zonas})'

    #NOTA: SE TIVESSEMOS UM MODULO DE HISTORICO ISTO PODIA USÁ-LO
    def _obter_historico_recente(self, ambiente, tempo_simulacao: datetime) -> List[Tuple[datetime, str]]:
        """
        Obtém o histórico de pedidos recente (dentro da janela) do ambiente.

        Args:
            ambiente: GestaoAmbiente com acesso aos pedidos
            tempo_simulacao: Tempo atual da simulação

        Returns:
            Lista de tuplas (timestamp, nodo_origem) dos pedidos na janela temporal
        """
        
        janela_inicio = tempo_simulacao - timedelta(minutes=self.janela_historico_minutos)
        historico = []
        
        # pedidos que foram atendidos ou estão em curso dentro da janela
        for pedido in ambiente.listar_pedidos():
            if pedido.estado in (EstadoPedido.EM_CURSO, EstadoPedido.CONCLUIDO):
                if janela_inicio <= pedido.horario_pretendido <= tempo_simulacao:
                    historico.append((pedido.horario_pretendido, str(pedido.origem)))
        
        return historico


    def _calcular_zonas_atratividade(
        self,
        tempo_simulacao: datetime,
        historico_pedidos: Optional[List[Dict]] = None
    ) -> Dict[str, int]:
        """
        Calcula histograma baseado no histórico interno
        se presente, caso contrário usa um histórico externo (lista de dicts).
        """
        zonas_contagem = defaultdict(int)
        janela_inicio = tempo_simulacao - timedelta(minutes=self.janela_historico_minutos)

        # Usar histórico externo se fornecido
        if historico_pedidos:
            for timestamp, origem in historico_pedidos:
                if timestamp and origem and timestamp >= janela_inicio:
                    zonas_contagem[str(origem)] += 1

        # Caso contrário, usar histórico interno se disponível
        elif self.historico_demanda:
            for timestamp, origem in self.historico_demanda:
                if timestamp >= janela_inicio:
                    zonas_contagem[origem] += 1


        return dict(zonas_contagem)

    def decidir_reposicionamentos(
        self,
        veiculos_disponiveis: List,
        grafo,
        ambiente=None,
        tempo_simulacao: datetime = None
    ) -> List[Tuple[object, str]]:
        """
        Decide reposicionamentos usando histograma de demanda.

        Args:
            veiculos_disponiveis: Veículos disponíveis
            grafo: Grafo da rede
            ambiente: GestaoAmbiente com histórico de pedidos
            tempo_simulacao: Tempo atual

        Returns:
            Lista de (veiculo, nodo_destino)
        """
        # Verificar se já está no tempo de reposicionar
        if self.ultimo_reposicionamento is not None:
            delta = (tempo_simulacao - self.ultimo_reposicionamento).total_seconds() / 60
            if delta < self.intervalo_reposicionamento_minutos:
                return []

        # Se não há veículos disponíveis, não faz nada
        if not veiculos_disponiveis:
            return []

        # Obter mapa de atratividade: priorizar histórico interno
        if ambiente is not None:
            historico_recente = self._obter_historico_recente(ambiente, tempo_simulacao)
            zonas_atratividade = self._calcular_zonas_atratividade(tempo_simulacao, historico_recente)

        if not zonas_atratividade:
            return []

        # Selecionar top-k zonas
        top_zonas = sorted(zonas_atratividade.items(), key=lambda x: x[1], reverse=True)[:self.top_k_zonas]
        top_zonas_ids = [zona_id for zona_id, _ in top_zonas]

        # Calcular quantos veículos reposicionar
        num_veiculos_reposicionar = max(1, int(len(veiculos_disponiveis) * self.percentual_veiculos_reposicionar))

        # Selecionar veículos para reposicionar (priorizar mais distantes das zonas quentes)
        veiculos_ordenados = self._ordenar_veiculos_por_distancia(
            veiculos_disponiveis,
            top_zonas_ids,
            grafo
        )

        reposicionamentos = []
        # Tentar escolher até `num_veiculos_reposicionar` veículos, testando os
        # veículos ordenados por distância (mais longe primeiro) e 
        # que respeitam o limite de distância.
        for veiculo in veiculos_ordenados:
            if len(reposicionamentos) >= num_veiculos_reposicionar:
                break

            # Escolher zona destino (distribuir veículos entre top-k)
            idx_zona = len(reposicionamentos) % len(top_zonas_ids)
            zona_destino = top_zonas_ids[idx_zona]

            # Verificar distância máxima
            distancia = self._calcular_distancia_aproximada(veiculo, zona_destino, grafo)
            if distancia <= self.distancia_maxima_reposicionamento:
                reposicionamentos.append((veiculo, zona_destino))

        # Atualizar timestamp do último reposicionamento
        if reposicionamentos:
            self.ultimo_reposicionamento = tempo_simulacao

        return reposicionamentos

