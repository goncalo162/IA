"""
Interface base para algoritmos de navegação/procura de caminhos.
Todos os algoritmos de navegação devem herdar desta classe.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from infra.grafo.grafo import Grafo
from algoritmos.criterios import FuncaoCusto, Heuristica, CustoDefault, ZeroHeuristica


class NavegadorBase(ABC):
    """
    Classe abstrata que define a interface para algoritmos de navegação.

    Um navegador é responsável por encontrar o melhor caminho entre
    dois pontos no grafo da cidade, usando diferentes estratégias de procura
    (BFS, DFS, Dijkstra, A*, etc.).
    """

    def __init__(
            self,
            funcao_custo: Optional[FuncaoCusto] = None,
            heuristica: Optional[Heuristica] = None):
        """Inicializa o navegador com funções de custo e heurística opcionais.

        Estas dependências podem ser usadas por implementações (ex.: A*) que
        queiram consultar estimativas e custos personalizados.
        """
        self.funcao_custo: FuncaoCusto = funcao_custo if funcao_custo is not None else CustoDefault()
        self.heuristica: Heuristica = heuristica if heuristica is not None else ZeroHeuristica()

    @abstractmethod
    def calcular_rota(self, grafo: Grafo, origem: str, destino: str) -> Optional[List[str]]:
        """
        Calcula a rota entre origem e destino no grafo.

        Args:
            grafo: O grafo da cidade
            origem: Nome do nó de origem
            destino: Nome do nó de destino

        Returns:
            Lista com os nomes dos nós que formam o caminho,
            ou None se não existir caminho
        """
        pass

    @abstractmethod
    def nome_algoritmo(self) -> str:
        """Retorna o nome do algoritmo para identificação."""
        pass
