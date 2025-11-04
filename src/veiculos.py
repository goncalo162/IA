from abc import ABC, abstractmethod
from enum import Enum

#NOTA: enum sus, depois vejam os estados melhor
class EstadoVeiculo(Enum):
    DISPONIVEL = 1
    EM_ANDAMENTO = 2
    INDISPONIVEL = 3 
    EM_REABASTECIMENTO = 4
    EM_MANUTENCAO = 5

class Veiculo(ABC):
    def __init__(self, id_veiculo: str, autonomia_maxima: int, autonomia_atual: int,
                 capacidade_passageiros: int, custo_operacional_km: float,
                 estado: EstadoVeiculo = EstadoVeiculo.DISPONIVEL):
        self.id_veiculo = id_veiculo
        self.autonomia_maxima = autonomia_maxima
        self.autonomia_atual = autonomia_atual
        self.capacidade_passageiros = capacidade_passageiros
        self.custo_operacional_km = custo_operacional_km
        self.estado = estado

    @abstractmethod
    def reabastecer(self):
        """Método abstrato — implementado de forma diferente nos veículos a combustão e elétricos"""
        return

    @abstractmethod
    def tempoReabastecimento(self):
        return

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

# -------------------- Veículo a Combustão ---------------- #

class VeiculoCombustao(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km): #meter custo litro por kilometro se for preciso
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         custo_operacional_km)

    def tempoReabastecimento(self):
        return 5  # tempo fixo de reabastecimento em minutos, NOTA: pode ser ajustado conforme necessário


# -------------------- Veículo Elétrico ---------------- #

class VeiculoEletrico(Veiculo):
    def __init__(self, id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                 custo_operacional_km, tempo_recarga_km: int):
        super().__init__(id_veiculo, autonomia_maxima, autonomia_atual, capacidade_passageiros,
                         custo_operacional_km)
        self.tempo_recarga_km = tempo_recarga_km  # tempo médio para carga de um km

    def tempoReabastecimento(self):
        tempo = self.tempo_recarga_km * (self.autonomia_maxima - self.autonomia_atual)
        return tempo







    

