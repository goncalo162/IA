from collections import deque
from typing import Optional, List

from algoritmos.alocador_base import AlocadorBase
from infra.grafo.grafo import Grafo
from infra.entidades.veiculos import Veiculo
from infra.entidades.pedidos import Pedido


# Implementação dos algoritmos de alocação


class AlocadorSimples(AlocadorBase):
    """Alocador muito simples: retorna o primeiro veículo que tem capacidade.

    Apenas para testar se a main esta a funcionar.

    Não tenta optimizar por distância, autonomia ou custo — apenas garante que
    a capacidade de passageiros do veículo é suficiente.
    """

    def escolher_veiculo(self, pedido: Pedido, veiculos_disponiveis: List[Veiculo],
                        grafo: Grafo) -> Optional[Veiculo]:
        for v in veiculos_disponiveis:
            if self._verificar_capacidade(v, pedido):
                return v
        return None
