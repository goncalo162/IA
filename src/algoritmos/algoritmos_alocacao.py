from typing import Optional, List
from algoritmos.alocador_base import AlocadorBase
from infra.grafo.grafo import Grafo
from infra.entidades.veiculos import Veiculo
from infra.entidades.pedidos import Pedido


#################
#   *Simples*   #
#################

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

            # Só considerar veículos em andamento que passarão pela origem
            if not self._veiculo_passa_pela_origem(v, pedido, grafo):
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
            distancia_ate_cliente = grafo.calcular_distancia_rota(
                rota_ate_cliente)

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

    def nome_algoritmo(self):
        return "Simples"


####################
#   *Heuristico*   #
####################

#NOTA: NAO DEVERIA RECEBER A FUNÇÃO HEURISTICA OU CUSTO E USAR EM VEZ DE FAZER AS CONTAS TODAS AQUI?

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

            # Centralizar lógica: só considerar veículos em andamento que passarão pela origem
            if not self._veiculo_passa_pela_origem(v, pedido, grafo):
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

            # 4 — verificar autonomia ou planear recarga se necessário
            rota_completa = rota_ate_cliente + rota_pedido[1:]  # Concatenar rotas
            if not self.verificar_ou_planear_recarga(v, distancia_total, rota_completa):
                continue

            # 5 — calcular score
            score = 0

            # distância (quanto menor, melhor)
            score += self.PESO_DISTANCIA * distancia_ate_cliente

            # custo operacional (quanto maior, pior)
            score += self.PESO_CUSTO * v.custo_operacional_km

            # autonomia (quanto maior, melhor → subtrai)
            score -= self.PESO_AUTONOMIA * v.autonomia_atual

            # preferência ambiental
            if pedido.preferencia_ambiental == "eco":
                if v.tipo == "combustao":
                    score += self.PENALIZACAO_COMBUSTAO
            
            # Adicionar penalização se há plano de recarga
            if v.plano_recarga_pendente:
                if self.gestor_recargas and self.gestor_recargas.recarga_policy:
                    penalizacao_recarga = self.gestor_recargas.recarga_policy.calcular_penalizacao_recarga(v.plano_recarga_pendente)
                    score += penalizacao_recarga

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

    def nome_algoritmo(self):
        return "Heurístico"

#TODO: REVER ESTES ALGORITMOS

class AlocadorPorCusto(AlocadorBase):
    """Alocador que escolhe veículo com menor custo operacional estimado.

    Usa a `funcao_custo` para estimar custo/tempo das rotas e multiplica pelo
    custo operacional do veículo para obter custo monetário aproximado.
    """

    def escolher_veiculo(self, pedido: Pedido, veiculos_disponiveis: List[Veiculo], grafo: Grafo, rota_pedido: List[str], distancia_pedido: float) -> Optional[Veiculo]:
        origem_pedido_nome = grafo.getNodeName(pedido.origem)
        melhor = None
        melhor_custo = float('inf')

        for v in veiculos_disponiveis:
            if not self._verificar_capacidade(v, pedido):
                continue

            if not self._veiculo_passa_pela_origem(v, pedido, grafo):
                continue

            origem_veiculo_nome = v.localizacao_atual if isinstance(v.localizacao_atual, str) else grafo.getNodeName(v.localizacao_atual)

            rota_ate_cliente = self.navegador.calcular_rota(grafo=grafo, origem=origem_veiculo_nome, destino=origem_pedido_nome)
            if rota_ate_cliente is None:
                continue

            distancia_ate_cliente = grafo.calcular_distancia_rota(rota_ate_cliente)
            if distancia_ate_cliente is None:
                continue

            distancia_total = distancia_ate_cliente + distancia_pedido
            
            # Verificar autonomia ou planear recarga se necessário
            rota_completa = rota_ate_cliente + rota_pedido[1:]
            if not self.verificar_ou_planear_recarga(v, distancia_total, rota_completa):
                continue

            # custo estimado = (distancia_total) * custo_operacional_km
            custo_estimado = distancia_total * v.custo_operacional_km
            
            # Adicionar custo da recarga se necessária
            if v.plano_recarga_pendente:
                custo_estimado += v.plano_recarga_pendente.custo_extra_estimado

            if custo_estimado < melhor_custo:
                melhor_custo = custo_estimado
                melhor = v
                melhor.rota_ate_cliente = rota_ate_cliente
                melhor.distancia_ate_cliente = distancia_ate_cliente

        return melhor

    def nome_algoritmo(self):
        return "PorCusto"

class AlocadorAEstrela(AlocadorBase):
    """Alocador que aplica uma heurística (A*-like) para escolher veículo.

    Para cada veículo estima g = custo_real (pela `funcao_custo`) e h = heuristica
    e escolhe o veículo com menor g + h.
    """

    def escolher_veiculo(self, pedido: Pedido, veiculos_disponiveis: List[Veiculo], grafo: Grafo, rota_pedido: List[str], distancia_pedido: float) -> Optional[Veiculo]:
        origem_pedido_nome = grafo.getNodeName(pedido.origem)
        candidatos = []

        for v in veiculos_disponiveis:
            if not self._verificar_capacidade(v, pedido):
                continue

            if not self._veiculo_passa_pela_origem(v, pedido, grafo):
                continue

            origem_veiculo_nome = v.localizacao_atual if isinstance(v.localizacao_atual, str) else grafo.getNodeName(v.localizacao_atual)

            rota_ate_cliente = self.navegador.calcular_rota(grafo=grafo, origem=origem_veiculo_nome, destino=origem_pedido_nome)
            if rota_ate_cliente is None:
                continue

            # g: custo real da rota (veiculo->cliente + pedido)
            custo_ate_cliente = self.funcao_custo.custo_rota(grafo, rota_ate_cliente, v)
            custo_pedido = self.funcao_custo.custo_rota(grafo, rota_pedido, v)
            g = custo_ate_cliente + custo_pedido

            distancia_total = grafo.calcular_distancia_rota(rota_ate_cliente) + distancia_pedido
            
            # Verificar autonomia ou planear recarga se necessário
            rota_completa = rota_ate_cliente + rota_pedido[1:]
            if not self.verificar_ou_planear_recarga(v, distancia_total, rota_completa):
                continue

            # h: heurística entre veículo e origem do pedido
            h = self.heuristica.estimativa(grafo, origem_veiculo_nome, origem_pedido_nome)

            score = g + h
            
            # Adicionar penalização se há plano de recarga
            if v.plano_recarga_pendente:
                if self.gestor_recargas and self.gestor_recargas.recarga_policy:
                    penalizacao_recarga = self.gestor_recargas.recarga_policy.calcular_penalizacao_recarga(v.plano_recarga_pendente)
                    score += penalizacao_recarga
            
            candidatos.append((score, v, rota_ate_cliente, grafo.calcular_distancia_rota(rota_ate_cliente)))

        if not candidatos:
            return None

        candidatos.sort(key=lambda x: x[0])
        _, melhor_veiculo, rota, dist_cli = candidatos[0]
        melhor_veiculo.rota_ate_cliente = rota
        melhor_veiculo.distancia_ate_cliente = dist_cli
        return melhor_veiculo

    def nome_algoritmo(self):
        return "A-Estrela"