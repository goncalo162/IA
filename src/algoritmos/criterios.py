"""Compatibilidade: re-exporta as classes de custos e heurísticas.
Facilita a importação a partir do módulo 'criterios'.
"""

from .funcoes_custo import FuncaoCusto, CustoDefault, CustoTempoPercurso
from .heuristicas import Heuristica, ZeroHeuristica, HeuristicaEuclidiana

__all__ = [
    'FuncaoCusto', 'CustoDefault', 'CustoTempoPercurso',
    'Heuristica', 'ZeroHeuristica', 'HeuristicaEuclidiana'
]
