from typing import Optional, List
from algoritmos.alocador_base import AlocadorBase
from infra.grafo.grafo import Grafo
from infra.entidades.veiculos import Veiculo
from infra.entidades.pedidos import Pedido


class AlocadorHeuristico(AlocadorBase):
    """
    Alocador eficiente: escolhe o veículo com melhor score baseado em:
    - distância até ao cliente
    - autonomia
    - custo operacional
    - preferência ambiental
    - capacidade
    """

    # pesos ajustáveis
    PESO_DISTANCIA = 1.0
    PESO_CUSTO = 0.5
    PESO_AUTONOMIA = 1.2
    PENALIZACAO_COMBUSTAO = 5.0  # se o cliente preferir veículo "eco"

    def escolher_veiculo(
        self,
        pedido: Pedido,
        veiculos_disponiveis: List[Veiculo],
        grafo: Grafo,
        rota_pedido: List[str],
        distancia_pedido: float
    ) -> Optional[Veiculo]:

        origem_pedido_nome = grafo.getNodeName(pedido.origem)
        candidatos = []

        for v in veiculos_disponiveis:

            # 1 — verificar capacidade
            if not self._verificar_capacidade(v, pedido):
                continue

            # 2 — converter nome/localização
            origem_v = v.localizacao_atual if isinstance(v.localizacao_atual, str) else grafo.getNodeName(v.localizacao_atual)

            # 3 — rota veículo -> cliente
            rota_ate_cliente = self.navegador.calcular_rota(
                grafo=grafo,
                origem=origem_v,
                destino=origem_pedido_nome
            )

            if rota_ate_cliente is None:
                continue

            distancia_ate_cliente = grafo.calcular_distancia_rota(rota_ate_cliente)
            if distancia_ate_cliente is None:
                continue

            distancia_total = distancia_ate_cliente + distancia_pedido

            # 4 — verificar autonomia
            if v.autonomia_atual < distancia_total:
                continue

            # 5 — calcular score
            score = 0

            # distância (quanto menor, melhor)
            score += self.PESO_DISTANCIA * distancia_ate_cliente

            # custo operacional (quanto maior, pior)
            score += self.PESO_CUSTO * v.custo_operacional

            # autonomia (quanto maior, melhor → subtrai)
            score -= self.PESO_AUTONOMIA * v.autonomia_atual

            # preferência ambiental
            if pedido.preferencia_ambiental == "eco":
                if v.tipo == "combustao":
                    score += self.PENALIZACAO_COMBUSTAO

            candidatos.append((score, v, rota_ate_cliente, distancia_ate_cliente))

        # nenhum candidato viável
        if not candidatos:
            return None

        # escolher o veículo com menor score
        candidatos.sort(key=lambda x: x[0])
        melhor_score, melhor_veiculo, rota, dist_cli = candidatos[0]

        # guardar dados no veículo
        melhor_veiculo.rota_ate_cliente = rota
        melhor_veiculo.distancia_ate_cliente = dist_cli

        return melhor_veiculo
