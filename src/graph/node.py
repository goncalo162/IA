from enum import Enum

class TipoNodo(Enum):
    LOCAL = 0
    BOMBA_GASOLINA = 1
    POSTO_CARREGAMENTO = 2

# Classe nodo para definiçao dos nodos
# cada nodo tem um nome e um id, poderia ter também um apontador para outro elemento a guardar....
class Node:
    def __init__(self, name, id=-1, tipo:TipoNodo = TipoNodo.LOCAL):     #  construtor do nodo....."
        self.m_id = id
        self.m_name = str(name)
        self.m_tipo = tipo
        # posteriormente podera ser colocodo um objeto que armazena informação em cada nodo.....

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
        return self.m_name == other.m_name and self.m_tipo == other.m_tipo # ver se é preciso tb testar o id....

    def __hash__(self):
        return hash(self.m_name)