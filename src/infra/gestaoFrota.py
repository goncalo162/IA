"""Gestão de frota

Classe responsável por manter veículos e pedidos e por operações simples
de atribuição.
"""

from typing import Dict, Optional

from entidades.pedidos import Pedido
from entidades.veiculos import Veiculo


class GestaoFrota:
    """Gestor simples de frota e pedidos."""

    def __init__(self):
        self._veiculos: Dict[int, Veiculo] = {}
        self._pedidos: Dict[int, Pedido] = {}

    # -------------------- Veículos --------------------
    def adicionar_veiculo(self, vehicle: Veiculo):
        self.veiculos[vehicle.id_veiculo] = vehicle

    def remover_veiculo(self, vehicle_id: int) -> Optional[Veiculo]:
        return self.veiculos.pop(vehicle_id, None)

    def get_veiculo(self, vehicle_id: int) -> Optional[Veiculo]:
        return self.veiculos.get(vehicle_id)

    def lista_veiculos(self):
        return list(self._veiculos.values())

    # -------------------- Pedidos --------------------
    def adicionar_pedido(self, pedido: Pedido):
        self.pedidos[pedido.id] = pedido

    def remover_pedido(self, pedido_id: int) -> Optional[Pedido]:
        return self.pedidos.pop(pedido_id, None)

    def get_pedido(self, pedido_id: int) -> Optional[Pedido]:
        return self.pedidos.get(pedido_id)

    def lista_pedidos(self):
        return list(self.pedidos.values())

    # -------------------- Atribuição de Pedidos a Veículos --------------------
    def atribuir_pedido_a_veiculo(self, pedido_id: int, veiculo_id: int) -> bool:
        """Atribui um pedido a um veículo já escolhido e atualiza os estados."""
        pedido = self.get_pedido(pedido_id)
        if pedido is None:
            return False

        veiculo = self.get_veiculo(veiculo_id)
        if veiculo is None:
            return False

        pedido.atribuir_a = veiculo.id_veiculo
        pedido.estado = pedido.estado.EM_CURSO
        veiculo.estado = veiculo.estado.EM_ANDAMENTO
        return True	

    def concluir_pedido(self, pedido_id: int) -> bool:
        pedido = self.get_pedido(pedido_id)
        if pedido is None:
            return False
        if pedido.atribuir_a is None:
            pedido.estado = pedido.estado.CONCLUIDO
            return True

        veiculo = self.get_veiculo(pedido.atribuir_a)
        if veiculo:
            veiculo.estado = veiculo.estado.DISPONIVEL
        pedido.estado = pedido.estado.CONCLUIDO
        return True
    