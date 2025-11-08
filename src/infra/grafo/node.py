from enum import Enum

class TipoNodo(Enum):
    LOCAL = 0
    BOMBA_GASOLINA = 1
    POSTO_CARREGAMENTO = 2

class Node:
    def __init__(self, name, id=-1, tipo: TipoNodo = TipoNodo.LOCAL):
        self.m_id = id
        self.m_name = str(name)
        self.m_tipo = tipo

    def __str__(self):
        return "node " + self.m_name

    def __repr__(self):
        return "node " + self.m_name

    def setId(self, id):
        self.m_id = id

    def getId(self):
        return self.m_id

    def getName(self):
        return self.m_name

    def getTipoNodo(self):
        return self.m_tipo

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.m_name == other.m_name and self.m_tipo == other.m_tipo

    def __hash__(self):
        return hash((self.m_name, self.m_tipo))