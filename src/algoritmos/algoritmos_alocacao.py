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

    def escolher_veiculo(self, pedido: Pedido, veiculos_disponiveis: List[Veiculo], grafo: Grafo, rota_pedido: List[str], distancia_pedido: float) -> Optional[Veiculo]:
        """Escolhe o *primeiro* veículo com capacidade e autonomia suficientes.

        Usa o `navegador` e o `grafo` para calcular a rota veículo->cliente,
        somando a distância dessa rota com `distancia_pedido` (rota do pedido).
        """

        origem_pedido_nome = grafo.getNodeName(pedido.origem)

        for v in veiculos_disponiveis:
            if not self._verificar_capacidade(v, pedido):
                continue

            # Determinar origem do veículo em nome de nó
            if isinstance(v.localizacao_atual, str):
                origem_veiculo_nome = v.localizacao_atual
            else:
                origem_veiculo_nome = grafo.getNodeName(v.localizacao_atual)

            # Rota veículo -> cliente usando o mesmo navegador
            rota_ate_cliente = self.navegador.calcular_rota(
                grafo=grafo,
                origem=origem_veiculo_nome,
                destino=origem_pedido_nome,
            )

            if rota_ate_cliente is None:
                continue

            # Distância veículo -> cliente baseada nos quilómetros das arestas
            distancia_ate_cliente = grafo.calcular_distancia_rota(rota_ate_cliente)
            
            if distancia_ate_cliente is None:
                continue

            distancia_total = distancia_ate_cliente + distancia_pedido

            if v.autonomia_atual < distancia_total:
                continue

            # Guardar rota e distância até cliente no veículo para uso posterior
            v.rota_ate_cliente = rota_ate_cliente
            v.distancia_ate_cliente = distancia_ate_cliente
            return v  # simples: primeiro veículo viável

        return None

