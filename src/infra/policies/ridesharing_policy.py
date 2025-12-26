"""
Políticas de ride-sharing para ajustar rotas quando múltiplos passageiros compartilham um veículo.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List


class RideSharingPolicy(ABC):
    """Classe abstrata para políticas de ride-sharing."""

    @abstractmethod
    def nome_policy(self) -> str:
        """Retorna o nome da política de ride-sharing."""
        pass

    @abstractmethod
    def ajustar_rotas(self, veiculo, origem_nome: str, destino_nome: str,
                      navegador, grafo) -> Optional[Tuple[List[str], float]]:
        """
        Ajusta rotas para acomodar um novo pedido em um veículo.

        Args:
            veiculo: Veículo que pode estar com viagens ativas
            origem_nome: Origem do novo pedido
            destino_nome: Destino do novo pedido
            navegador: Navegador para cálculo de rotas
            grafo: Grafo da cidade

        Returns:
            Tupla (rota_viagem_ajustada, distancia_viagem_ajustada) ou None
        """
        pass

    @abstractmethod
    def permite_ridesharing(self) -> bool:
        """Retorna True se a política permite ride-sharing."""
        pass


class SimplesRideSharingPolicy(RideSharingPolicy):
    """
    Política simples de ride-sharing: permite compartilhamento sem desvios.

    Se o veículo já tem viagens ativas, a rota do pedido deve iniciar coincidente
    com o plano atual do veículo e depois estender até ao destino do pedido.
    """

    def nome_policy(self):
        return "SimplesRideSharingPolicy"

    def permite_ridesharing(self) -> bool:
        return True

    def ajustar_rotas(self, veiculo, origem_nome: str, destino_nome: str,
                      navegador, grafo) -> Optional[Tuple[List[str], float]]:
        """
        Ajusta rotas para ride-sharing sem permitir desvios.

        A rota do novo pedido deve ser compatível com a rota atual do veículo.
        Isto é, a origem do pedido deve estar na rota atual do veículo, e o destino
        do pedido deve ser alcançável seguindo a rota atual ou estendendo-a.
        """
        # Obter rota atual do veículo
        rota_atual = veiculo.rota_total_viagens() if hasattr(veiculo, 'rota_total_viagens') else None
        if not rota_atual or len(rota_atual) < 2:
            return None

        # Verificar se há viagens ativas
        viagens_ativas = [v for v in veiculo.viagens if v.viagem_ativa]
        if not viagens_ativas:
            return None

        # Verificar se a origem do pedido está na rota atual do veículo
        if origem_nome not in rota_atual:
            return None

        # Construir rota combinada
        idx_origem = rota_atual.index(origem_nome)
        # Veículo -> cliente: do início da rota até a origem do pedido
        nova_rota_ate_origem = rota_atual[:idx_origem + 1]

        # Cliente -> destino: seguir rota atual e se necessário estender até ao destino
        tail_rota = rota_atual[idx_origem:]

        if destino_nome in tail_rota:
            idx_destino = tail_rota.index(destino_nome)
            nova_rota_viagem = tail_rota[:idx_destino + 1]
        else:
            # Estender rota até ao destino
            extensao_rota = navegador.calcular_rota(grafo, tail_rota[-1], destino_nome)
            if extensao_rota is None or len(extensao_rota) < 2:
                return None
            nova_rota_viagem = tail_rota + extensao_rota[1:]  # Sem repetir o nó de junção

        # Atualizar informações do veículo sobre a rota até o cliente
        veiculo.rota_ate_cliente = nova_rota_ate_origem
        veiculo.distancia_ate_cliente = grafo.calcular_distancia_rota(nova_rota_ate_origem)

        distancia_viagem = grafo.calcular_distancia_rota(nova_rota_viagem)
        return (nova_rota_viagem, distancia_viagem)


class SemRideSharingPolicy(RideSharingPolicy):
    """
    Política que não permite ride-sharing.

    Cada veículo só pode ter uma viagem ativa por vez.
    """

    def nome_policy(self):
        return "SemRideSharingPolicy"

    def permite_ridesharing(self) -> bool:
        return False

    def ajustar_rotas(self, veiculo, origem_nome: str, destino_nome: str,
                      navegador, grafo) -> Optional[Tuple[List[str], float]]:
        """Não ajusta rotas pois não permite ride-sharing."""
        return None
