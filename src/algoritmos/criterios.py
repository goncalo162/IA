"""Compatibilidade: re-exporta as classes de custos e heurísticas.
Facilita a importação a partir do módulo 'criterios'.
"""

from .funcoes_custo import FuncaoCusto, CustoDefault, CustoTempoPercurso, CustoAmbientalTempo
from .heuristicas import Heuristica, ZeroHeuristica, HeuristicaEuclidiana

__all__ = [
    'FuncaoCusto', 'CustoDefault', 'CustoTempoPercurso', 'CustoAmbientalTempo'
    'Heuristica', 'ZeroHeuristica', 'HeuristicaEuclidiana'
]
