import os
import pytest

from config import Config
from algoritmos.criterios import CustoDefault, CustoTempoPercurso, ZeroHeuristica, HeuristicaEuclidiana
from algoritmos.navegador_base import NavegadorBase
from algoritmos.alocador_base import AlocadorBase


def test_funcao_custo_default_and_tempo_and_invalid():
    # default
    orig = Config.FUNCAO_CUSTO
    Config.FUNCAO_CUSTO = 'default'
    f = Config.get_funcao_custo()
    assert isinstance(f, CustoDefault)

    # tempo
    Config.FUNCAO_CUSTO = 'tempo'
    f2 = Config.get_funcao_custo()
    assert isinstance(f2, CustoTempoPercurso)

    # invalid
    Config.FUNCAO_CUSTO = 'invalida'
    with pytest.raises(SystemExit):
        Config.get_funcao_custo()

    Config.FUNCAO_CUSTO = orig


def test_heuristica_default_and_euclidiana_and_invalid():
    orig = Config.HEURISTICA
    Config.HEURISTICA = 'zero'
    h = Config.get_heuristica()
    assert isinstance(h, ZeroHeuristica)

    Config.HEURISTICA = 'euclidiana'
    h2 = Config.get_heuristica()
    assert isinstance(h2, HeuristicaEuclidiana)

    Config.HEURISTICA = 'naoexiste'
    with pytest.raises(SystemExit):
        Config.get_heuristica()

    Config.HEURISTICA = orig


def test_get_navegador_sets_funcao_e_heuristica():
    # create explicit function and heuristic and pass to get_navegador
    func = Config.get_funcao_custo('default')
    heur = Config.get_heuristica('zero')
    nav = Config.get_navegador('bfs', func, heur)
    assert isinstance(nav, NavegadorBase)
    assert nav.funcao_custo is func
    assert nav.heuristica is heur


def test_get_alocador_receives_funcao_e_heuristica():
    func = Config.get_funcao_custo('default')
    heur = Config.get_heuristica('zero')
    nav = Config.get_navegador('bfs', func, heur)
    al = Config.get_alocador(nav, 'simples', func, heur)
    assert isinstance(al, AlocadorBase)
    assert al.funcao_custo is func
    assert al.heuristica is heur
