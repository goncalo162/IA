from abc import ABC, abstractmethod
from enum import Enum


class NiveisTransito(Enum):
    VAZIO = 0.5
    NORMAL = 1
    ELEVADO = 1.5
    MUITO_ELEVADO = 2
    ACIDENTE = None


class Veiculo(ABC):

    @abstractmethod
    def tempoReabastecimento(self):
        return
    
    def tempoPercorrer(self, velocidade, quilometros, nivelTransito):
        if(nivelTransito != ACIDENTE):
            return velocidade * quilometros * nivelTransito
        else:
            return None
