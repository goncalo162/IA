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
    
    def carregar_grafo(self, caminho: str):
        """Carrega o grafo a partir de um ficheiro JSON."""
        self.grafo = Grafo.from_json_file(caminho)
    
    def carregar_veiculos(self, caminho: str):
        """Carrega a frota de veículos a partir de um ficheiro JSON."""
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
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
    
    def carregar_pedidos(self, caminho: str):
        """Carrega os pedidos de transporte a partir de um ficheiro JSON."""
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
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
                preferencia_ambiental=p_data.get('preferencia_ambiental', 0)
            )
            pedido._estado = estado
            self._pedidos[pedido.id] = pedido
    
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

    def remover_veiculo(self, id_veiculo: int) -> Optional[Veiculo]:
        """Remove um veículo da frota pelo ID."""
        return self._veiculos.pop(id_veiculo, None)

    # -------------------- Pedidos --------------------
    def adicionar_pedido(self, pedido: Pedido):
        """Adiciona um pedido."""
        self._pedidos[pedido.id] = pedido
    
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
        veiculo.estado = veiculo.estado.EM_ANDAMENTO #talvez aqui meter indisponivel e passar para em adamento em comecar_viagem

        return True	

    def concluir_pedido(self, pedido_id: int) -> bool:
        pedido = self.obter_pedido(pedido_id)
        if pedido is None:
            return False

        veiculo = self.obter_veiculo(pedido.atribuir_a)
        if veiculo:
            veiculo.concluir_viagem(pedido.destino)
        pedido.estado = pedido.estado.CONCLUIDO
        return True

    # -------------------- Cálculos Auxiliares --------------------

    #nota: ver se é necessário ou usamos diretamente do grafo    
    def _calcular_distancia_rota(self, rota) -> float:
        """Wrapper para cálculo de distância delegando no grafo.""" 
        
        if not self.grafo:
            return 0.0
        return self.grafo.calcular_distancia_rota(rota)
    
    #nota: ver se é necessário ou usamos diretamente do grafo
    def _calcular_tempo_rota(self, rota) -> float:
        """Wrapper para cálculo de tempo delegando no grafo."""
        
        if not self.grafo:
            return 0.0
        return self.grafo.calcular_tempo_rota(rota)
    
    def _calcular_emissoes(self, veiculo, distancia: float) -> float:
        """Calcula as emissões de CO₂ de uma viagem."""
        if isinstance(veiculo, VeiculoEletrico):
            return 0.0
        else:
            return distancia * 0.12