from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from infra.entidades.viagem import Viagem

#NOTA: enum sus, depois vejam os estados melhor
class EstadoVeiculo(Enum):
    DISPONIVEL = 1
    EM_ANDAMENTO = 2
    INDISPONIVEL = 3 
    EM_REABASTECIMENTO = 4
    EM_MANUTENCAO = 5

class Veiculo(ABC):
    def __init__(self, id_veiculo: int, autonomia_maxima: int, autonomia_atual: int,
                 capacidade_passageiros: int, numero_passageiros: int, custo_operacional_km: float,
                 estado: EstadoVeiculo = EstadoVeiculo.DISPONIVEL, localizacao_atual = 0):
        # atributos protegidos (encapsulados) — aceder via propriedades
        self._id_veiculo = id_veiculo
        self._autonomia_maxima = autonomia_maxima
        self._autonomia_atual = autonomia_atual
        self._capacidade_passageiros = capacidade_passageiros
        self._numero_passageiros = numero_passageiros
        self._custo_operacional_km = custo_operacional_km
        self._estado = estado
        self._localizacao_atual = localizacao_atual  # ID ou nome do nó onde o veículo está
        
        # Estado de viagem agora é encapsulado na classe Viagem
        self.viagem: Optional[Viagem] = None

        
        # Dados auxiliares da próxima viagem (rota veículo->cliente)
        self._rota_ate_cliente: list = []
        self._distancia_ate_cliente: float = 0.0

    @abstractmethod
    def reabastecer(self):
        """Método abstrato — implementado de forma diferente nos veículos a combustão e elétricos"""
        return

    @abstractmethod
    def tempoReabastecimento(self):
        return

    def adicionar_passageiros(self, numero: int):
        """Adiciona passageiros ao veículo, se houver capacidade."""
        if self._numero_passageiros + numero <= self._capacidade_passageiros:
            self._numero_passageiros += numero
            return True
        return False

    def reabastecer(self):
        self.autonomia_atual = self.autonomia_maxima
        self.estado = EstadoVeiculo.DISPONIVEL

    def atualizar_autonomia(self, km_percorridos: int):
        """Reduz a autonomia atual de acordo com a distância percorrida"""
        self.autonomia_atual = max(0, self.autonomia_atual - km_percorridos) # Evita autonomia negativa

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
        """Retorna a localização atual (nome do nó ou ID)."""
        return self.viagem.viagem_ativa if self.viagem else False

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
        self._distancia_ate_cliente = float(value) if value is not None else 0.0
    
    def iniciar_viagem(self, pedido_id: int,
                       rota_ate_cliente: list,
                       rota_pedido: list,
                       distancia_ate_cliente: float,
                       distancia_pedido: float,
                       tempo_inicio,
                       grafo,
                       velocidade_media: float = 50.0):
        """Inicia uma viagem separando rota até cliente e rota do pedido."""
        self.viagem = Viagem(
            pedido_id=pedido_id,
            rota_ate_cliente=rota_ate_cliente,
            rota_pedido=rota_pedido,
            distancia_ate_cliente=distancia_ate_cliente,
            distancia_pedido=distancia_pedido,
            tempo_inicio=tempo_inicio,
            grafo=grafo,
            velocidade_media=velocidade_media,
        )

        # Atualizar autonomia com base na distância total prevista da viagem
        self.atualizar_autonomia(self.viagem.distancia_total)


    def atualizar_progresso_viagem(self, tempo_decorrido_horas: float) -> bool:
        """Delega atualização de progresso para Viagem. Retorna True se viagem for concluída."""
        if not self.viagem:
            return False
        return self.viagem.atualizar_progresso(tempo_decorrido_horas)
   
    
    def concluir_viagem(self, destino):
        """Finaliza a viagem (delegado para Viagem e limpa a referência)."""
        if self.viagem:
            try:
                self.viagem.concluir()
                self.localizacao_atual = destino
                self.estado = EstadoVeiculo.DISPONIVEL
            finally:
                self.viagem = None
    
    @property
    def progresso_percentual(self) -> float:
        """Retorna o progresso da viagem em percentual (0-100)."""
        if not self.viagem:
            return 0.0
        return self.viagem.progresso_percentual
    
    @property
    def destino(self) -> str:
        """Retorna o destino final da rota."""
        return self.viagem.destino if self.viagem else None

    @property
    def pedido_id(self):
        return self.viagem.pedido_id if self.viagem else None

# -------------------- Veículo a Combustão ---------------- #

class VeiculoCombustao(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km, numero_passageiros=0, localizacao_atual=0): #meter custo litro por kilometro se for preciso
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
        # tempo médio para carga de um km (armazenado em campo protegido)
        self._tempo_recarga_km = tempo_recarga_km


    def tempoReabastecimento(self):
        tempo = self.tempo_recarga_km * (self.autonomia_maxima - self.autonomia_atual)
        return tempo

    @property
    def tempo_recarga_km(self) -> int:
        return self._tempo_recarga_km


# -------------------- Propriedades (getters/setters) --------------------


    






