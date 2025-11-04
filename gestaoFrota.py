"""Gestão de frota

Contém a classe GestaoFrota que mantém dois mapas:
- `veiculos`: mapa id_veiculo -> objeto Veiculo
- `pedidos`: mapa pedido_id -> objeto Pedido

Esta classe fornece operações básicas de CRUD e um ponto de extensão
para estratégias de atribuição de pedido a veículo.

"""

from typing import Dict, Optional,

	from src.entidades.pedidos import Pedido  # type: ignore
	from src.entidades.veiculos import Veiculo  # type: ignore

class GestaoFrota:
	"""Gestor simples de frota e pedidos.

	Mantém dicionários públicos `veiculos` e `pedidos`.
	"""

	def __init__(self):
		self._veiculos: Dict[int, "Veiculo"] = {}
		self._pedidos: Dict[int, "Pedido"] = {}

	# -------------------- Veículos --------------------
	def adicionar_veiculo(self, vehicle: "Veiculo"):
		self.veiculos[vehicle.id_veiculo] = vehicle

	def remover_veiculo(self, vehicle_id: int) -> Optional["Veiculo"]:
		return self.veiculos.pop(vehicle_id, None)

	def get_veiculo(self, vehicle_id: int) -> Optional["Veiculo"]:
		return self.veiculos.get(vehicle_id)

	def lista_veiculos(self):
		return list(self.veiculos.values())

	# -------------------- Pedidos --------------------
	def adicionar_pedido(self, request: "Pedido"):
		self.pedidos[request.id] = request

	def remover_pedido(self, request_id: int) -> Optional["Pedido"]:
		return self.pedidos.pop(request_id, None)

	def get_pedido(self, request_id: int) -> Optional["Pedido"]:
		return self.pedidos.get(request_id)

	def lista_pedidos(self):
		return list(self.pedidos.values())

	
    # -------------------- Atribuição de Pedidos a Veículos -------------------- 
    # NOTA: ver se é aqui ou noutro lado

