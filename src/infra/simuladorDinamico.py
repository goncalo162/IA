import os
import random
from infra.gestaoAmbiente import GestaoAmbiente
from infra.entidades.pedidos import Pedido

class SimuladorDinamico:

    def __init__(self, chanceTrocaTempo = 0.05, chancePedidoAleatorio = 0.05):
        """
        Condições dinâmicas para o simulador
        """
        self.m_chover = False
        self.m_chanceTrocaTempo = chanceTrocaTempo
        self.m_chancePedidoAleatorio = chancePedidoAleatorio

    def gerarPedido(self, ambiente:GestaoAmbiente):
        (inicio,fim) = ambiente.getRandomNodePair()
        return Pedido(ambiente.arranjaId_pedido, inicio, fim, )
    
    def simulacaoDinamica(self, ambiente:GestaoAmbiente):
        chuvaMudou = False
        gerouPedido = False

        if(random.randrange(0, 1000, 1) <= self.m_chanceTrocaTempo * 200):
            if(self.m_chover == False):
                self.m_chover = True
                self.m_chancePedidoAleatorio *= 2
            else:
                self.m_chover = False
                self.m_chancePedidoAleatorio /= 2

        if(random.randrange(0, 1000, 1) <= self.m_chancePedidoAleatorio * 200):
            ambiente.adicionar_pedido(self.gerarPedido(ambiente))

        return(chuvaMudou, gerouPedido)