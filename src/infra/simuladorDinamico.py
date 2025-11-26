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

    def gerarPedido(self, ambiente: GestaoAmbiente, curTime):
        (inicio, fim) = ambiente.getRandomNodePair()
        inicio_id = inicio.getId()
        fim_id = fim.getId()

        return Pedido(
            pedido_id=ambiente.arranjaId_pedido(),
            origem=inicio_id,
            destino=fim_id,
            passageiros=1,
            horario_pretendido=curTime,
            prioridade=0
        )
    
    def simulacaoDinamica(self, ambiente, curTime):
        chuvaMudou = False
        novo_pedido = None
    
        if random.random() <= self.m_chanceTrocaTempo:
            chuvaMudou = True
            if not self.m_chover:
                self.m_chover = True
                self.m_chancePedidoAleatorio *= 2
            else:
                self.m_chover = False
                self.m_chancePedidoAleatorio /= 2
    
        if random.random() <= self.m_chancePedidoAleatorio:
            novo_pedido = self.gerarPedido(ambiente, curTime)
            ambiente.adicionar_pedido(novo_pedido)
    
        return chuvaMudou, novo_pedido