from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from infra.entidades.viagem import Viagem

class EstadoVeiculo(Enum):
    DISPONIVEL = 1
    EM_ANDAMENTO = 2
    INDISPONIVEL = 3
    EM_REABASTECIMENTO = 4


class Veiculo(ABC):
    def __init__(self, id_veiculo: int, autonomia_maxima: int, autonomia_atual: int,
                 capacidade_passageiros: int, numero_passageiros: int, custo_operacional_km: float,
                 estado: EstadoVeiculo = EstadoVeiculo.DISPONIVEL, localizacao_atual=0):

        self._id_veiculo = id_veiculo
        self._autonomia_maxima = autonomia_maxima
        self._autonomia_atual = autonomia_atual
        self._capacidade_passageiros = capacidade_passageiros
        self._numero_passageiros = numero_passageiros
        self._custo_operacional_km = custo_operacional_km
        self._estado = estado
        self._localizacao_atual = localizacao_atual  # ID ou nome do nó onde o veículo está
        self.viagens: List[Viagem] = [] # Um veículo pode ter múltiplas viagens simultâneas (ride-sharing)

        # Dados auxiliares da possível próxima viagem (rota veículo->cliente)
        #TODO: ver onde faz sentido voltar a meter isto a zeros para nao ficar com dados obsoletos (se estiver em andamento por exemplo, e mudar a localiação antes de começar a viagem)
        self._rota_ate_cliente: list = []
        self._distancia_ate_cliente: float = 0.0


    def reabastecer(self):
        """Reabastece o veículo, restaurando sua autonomia ao máximo."""
        self.autonomia_atual = self.autonomia_maxima

    @abstractmethod
    def tempoReabastecimento(self):
        return

    def adicionar_passageiros(self, numero: int):
        """Adiciona passageiros ao veículo, se houver capacidade."""
        if self._numero_passageiros + numero <= self._capacidade_passageiros:
            self._numero_passageiros += numero
            return True
        return False
    
    def remover_passageiros(self, numero: int):
        """Remove passageiros do veículo, garantindo que não fique negativo."""
        self._numero_passageiros = max(0, self._numero_passageiros - numero)

    def atualizar_autonomia(self, km_percorridos: int):
        """Reduz a autonomia atual de acordo com a distância percorrida"""
        self.autonomia_atual = max(0, self.autonomia_atual - km_percorridos)  # Evita autonomia negativa

    def __str__(self):
        return (f"{self.__class__.__name__} [{self.id_veiculo}] | "
                f"Autonomia: {self.autonomia_atual}/{self.autonomia_maxima} km | "
                f"Capacidade: {self.capacidade_passageiros} passageiros | "
                f"Custo/km: €{self.custo_operacional_km:.2f} | "
                f"Estado: {self.estado.value}")

    # -------------------- Propriedades (getters/setters) --------------------
    @property
    def id_veiculo(self) -> int:
        return self._id_veiculo

    @property
    def autonomia_maxima(self) -> int:
        return self._autonomia_maxima

    @property
    def autonomia_atual(self) -> int:
        return self._autonomia_atual

    @autonomia_atual.setter
    def autonomia_atual(self, value: int):
        self._autonomia_atual = max(0, value)

    @property
    def capacidade_passageiros(self) -> int:
        return self._capacidade_passageiros

    @property
    def custo_operacional_km(self) -> float:
        return self._custo_operacional_km

    @property
    def estado(self) -> EstadoVeiculo:
        return self._estado

    @estado.setter
    def estado(self, value: EstadoVeiculo):
        if not isinstance(value, EstadoVeiculo):
            raise ValueError("estado deve ser um EstadoVeiculo")
        self._estado = value

    @property
    def numero_passageiros(self) -> int:
        return self._numero_passageiros

    @property
    def localizacao_atual(self):
        """Retorna a localização atual (nome do nó ou ID)."""
        return self._localizacao_atual

    @localizacao_atual.setter
    def localizacao_atual(self, value):
        """Define a localização atual (pode ser nome do nó ou ID)."""
        self._localizacao_atual = value

    @property
    def viagem_ativa(self):
        """Indica se há alguma viagem ativa neste veículo."""
        return any(v.viagem_ativa for v in self.viagens)

    # -------------------- Rota veículo -> cliente (auxiliar de alocação) --------------------

    @property
    def rota_ate_cliente(self) -> list:
        return self._rota_ate_cliente

    @rota_ate_cliente.setter
    def rota_ate_cliente(self, value: list):
        self._rota_ate_cliente = value or []

    @property
    def distancia_ate_cliente(self) -> float:
        return self._distancia_ate_cliente

    @distancia_ate_cliente.setter
    def distancia_ate_cliente(self, value: float):
        self._distancia_ate_cliente = float(
            value) if value is not None else 0.0
        
    # -------------------- métodos auxiliares para as suas viagens --------------------

    def iniciar_viagem(self, pedido,
                       rota_ate_cliente: list,
                       rota_pedido: list,
                       distancia_ate_cliente: float,
                       distancia_pedido: float,
                       tempo_inicio,
                       grafo,
                       velocidade_media: float = 50.0) -> bool:
        """Inicia uma viagem e adiciona ao conjunto de viagens ativas.

        Valida capacidade: soma de passageiros em viagens ativas + novos
        não pode exceder a capacidade do veículo, a menos que a lógica
        externa permita divisão de embarques.
        """
        
        passageiros_novos = pedido.numero_passageiros

        if (not self.adicionar_passageiros(passageiros_novos)):
            return False

        nova_viagem = Viagem(
            pedido=pedido,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_pedido,
            distancia_ate_cliente=distancia_ate_cliente,
            distancia_pedido=distancia_pedido,
            tempo_inicio=tempo_inicio,
            grafo=grafo,
            velocidade_media=velocidade_media,
        )

        self.viagens.append(nova_viagem)
        self.estado = EstadoVeiculo.EM_ANDAMENTO
        return True

    def atualizar_progresso_viagem(self, tempo_decorrido_horas: float) -> List[Viagem]:
        """Atualiza o progresso de todas as viagens ativas e autonomia proporcional.

        Retorna lista de viagens concluídas neste passo.
        """
        viagens_concluidas: List[Viagem] = []
        distancia_total_avancada = 0.0

        for v in list(self.viagens):
            if not v.viagem_ativa:
                continue
            distancia_antes = v.distancia_percorrida
            concluida = v.atualizar_progresso(tempo_decorrido_horas)
            distancia_depois = v.distancia_percorrida
            distancia_avancada = max(0.0, distancia_depois - distancia_antes)
            distancia_total_avancada += distancia_avancada
            if concluida:
                viagens_concluidas.append(v)

        if distancia_total_avancada > 0:
            self.atualizar_autonomia(distancia_total_avancada)

        return viagens_concluidas

    def concluir_viagem(self, viagem: Viagem):
        """Finaliza apenas a viagem fornecida.

        Atualiza a localização se `destino` for informado; remove apenas
        os passageiros associados a esta viagem e mantém as demais.
        """
        if viagem and viagem in self.viagens:
            passageiros_remover = viagem.numero_passageiros()
            viagem.concluir()
            if viagem.destino is not None:
                self.localizacao_atual = viagem.destino

            self.remover_passageiros(passageiros_remover)
            self.viagens.remove(viagem)

            if not self.viagem_ativa: # Atualizar estado do veículo conforme viagens remanescentes
                self.estado = EstadoVeiculo.DISPONIVEL

    @property
    def progresso_percentual_medio(self) -> float:
        """Retorna o progresso médio das viagens ativas (0-100)."""
        ativos = [v.progresso_percentual for v in self.viagens if v.viagem_ativa]
        if not ativos:
            return 0.0
        return sum(ativos) / len(ativos)
    
    @property
    def progresso_percentual(self) -> List[float]:
        """Retorna o progresso de todas as viagens ativas (0-100)."""
        return [v.progresso_percentual for v in self.viagens if v.viagem_ativa]

    @property
    def primeiro_destino(self) -> str:
        """Retorna um destino representativo (primeira viagem ativa)."""
        for v in self.viagens:
            if v.viagem_ativa:
                return v.destino
        return None

    @property
    def primeiro_pedido_id(self):
        """Retorna o primeiro pedido ativo (se existir)."""
        for v in self.viagens:
            if v.viagem_ativa:
                return v.pedido.id
        return None

    def passa_por(self, local: str) -> bool:
        """Retorna True se alguma viagem ativa passar por `local`.
        """
        if not isinstance(local, str) or not local:
            return False
        for v in self.viagens:
            if v.viagem_ativa and v.passa_por(local):
                return True
        return False

# -------------------- Veículo a Combustão ---------------- #


class VeiculoCombustao(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 # meter custo litro por kilometro se for preciso
                 custo_operacional_km, numero_passageiros=0, localizacao_atual=0):
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         numero_passageiros, custo_operacional_km, localizacao_atual=localizacao_atual)

    def tempoReabastecimento(self):
        return 5  # tempo fixo de reabastecimento em minutos, NOTA: pode ser ajustado conforme necessário


# -------------------- Veículo Elétrico ---------------- #

class VeiculoEletrico(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km, tempo_recarga_km: int, numero_passageiros=0, localizacao_atual=0):
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         numero_passageiros, custo_operacional_km, localizacao_atual=localizacao_atual)
        
        self._tempo_recarga_km = tempo_recarga_km # tempo médio para carga de um km 

    def tempoReabastecimento(self):
        tempo = self.tempo_recarga_km * \
            (self.autonomia_maxima - self.autonomia_atual)
        return tempo

    @property
    def tempo_recarga_km(self) -> int:
        return self._tempo_recarga_km


