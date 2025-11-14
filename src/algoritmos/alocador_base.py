"""
Interface base para algoritmos de alocação de veículos.
Todos os algoritmos de escolha de veículo devem herdar desta classe.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from infra.entidades.veiculos import Veiculo
from infra.entidades.pedidos import Pedido
from infra.grafo.grafo import Grafo
from algoritmos.criterios import FuncaoCusto, Heuristica, CustoDefault, ZeroHeuristica


class AlocadorBase(ABC):
    """
    Classe abstrata que define a interface para algoritmos de alocação.
    
    Um alocador é responsável por escolher qual veículo deve atender
    um pedido específico, considerando critérios como disponibilidade,
    distância, capacidade, autonomia, custo, etc.
    """

    def __init__(self, funcao_custo: Optional[FuncaoCusto] = None, heuristica: Optional[Heuristica] = None):
        """Inicializa o alocador com funções opcionais de custo e heurística.

        Essas dependências são opcionais e destinam-se a permitir testar/alterar
        critérios sem modificar o algoritmo.
        """
        self.funcao_custo: FuncaoCusto = funcao_custo if funcao_custo is not None else CustoDefault()
        self.heuristica: Heuristica = heuristica if heuristica is not None else ZeroHeuristica()

    @abstractmethod
    def escolher_veiculo(self, pedido: Pedido, veiculos_disponiveis: List[Veiculo], grafo: Grafo) -> Optional[Veiculo]:
        """
        Escolhe o melhor veículo para atender um pedido.
        
        Args:
            pedido: O pedido a ser atendido
            veiculos_disponiveis: Lista de veículos disponíveis
            grafo: Grafo da cidade para cálculo de distâncias
        
        Returns:
            O veículo escolhido, ou None se nenhum veículo for adequado
        """
        pass
    
    def _verificar_capacidade(self, veiculo: Veiculo, pedido: Pedido) -> bool:
        """Verifica se o veículo tem capacidade para o número de passageiros."""
        return veiculo.capacidade_passageiros >= pedido.passageiros
    
    def _verificar_autonomia(self, veiculo: Veiculo, distancia: float) -> bool:
        """Verifica se o veículo tem autonomia suficiente."""
        return veiculo.autonomia_atual >= distancia
