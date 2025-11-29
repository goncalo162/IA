from enum import Enum


class NivelTransito(Enum):
    VAZIO = 0.5
    NORMAL = 1
    ELEVADO = 1.5
    MUITO_ELEVADO = 2
    ACIDENTE = -1


class Aresta:
    def __init__(self, quilometro: int, velocidadeMaxima: float, nome: str, transito: NivelTransito = NivelTransito.NORMAL):  # construtor do nodo....."
        self.m_quilometro = quilometro
        self.m_velocidadeMaxima = velocidadeMaxima
        self.m_nivelTransito = transito
        self.m_nome = nome

    def __str__(self):
        return "node " + self.m_nome

    def __repr__(self):
        return "node " + self.m_nome

    def setNivelTransito(self, transito: NivelTransito):
        self.m_nivelTransito = transito

    def getQuilometro(self):
        return self.m_quilometro

    def getNome(self):
        return self.m_nome

    def getVelocidadeMaxima(self):
        return self.m_velocidadeMaxima

    def getTransito(self):
        return self.m_nivelTransito

    def getTempoPercorrer(self):
        if (self.m_nivelTransito == NivelTransito.ACIDENTE):
            return None
        else:
            return (self.m_quilometro / self.m_velocidadeMaxima) * self.m_nivelTransito.value

    def __eq__(self, other):
        # ver se é preciso tb testar o id....
        return self.m_nome == other.m_nome and self.m_nivelTransito == other.m_nivelTransito

    def __hash__(self):
        return hash(self.m_nome)