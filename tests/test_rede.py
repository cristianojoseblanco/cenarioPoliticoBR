"""Testes da matriz de votação e da concordância."""
import numpy as np
import pandas as pd

from src.networks.votacao import concordancia, montar_matriz

MAPA_A = {"Sim": 1, "Não": -1, "Obstrução": -1}


def _votos(linhas):
    return pd.DataFrame(linhas, columns=["votacao_id", "deputado_id", "voto"])


def test_codificacao_e_filtro_de_minoria():
    v = _votos([
        # v1: 2 x 1 -> minoria 33% (entra)
        ("v1", "a", "Sim"), ("v1", "b", "Sim"), ("v1", "c", "Obstrução"),
        # v2: unânime -> minoria 0% (sai com limiar 2,5%)
        ("v2", "a", "Sim"), ("v2", "b", "Sim"), ("v2", "c", "Sim"),
        # v3: secreta -> nenhum voto com valor (sai)
        ("v3", "a", None), ("v3", "b", None),
        # abstenção e artigo 17 ficam sem valor
        ("v1", "d", "Abstenção"), ("v1", "e", "Artigo 17"),
    ])
    m = montar_matriz(v, MAPA_A, 0.025)
    assert m.votacoes == ["v1"]
    assert m.deputados == ["a", "b", "c"]
    assert m.X[:, 0].tolist() == [1, 1, -1]
    assert m.excluidas == {"votacoes_total": 3, "sem_voto_com_valor": 1, "abaixo_minoria": 1, "incluidas": 1}


def test_concordancia_so_conta_votacoes_em_comum():
    X = np.array([
        [1, 1, -1, np.nan],
        [1, -1, -1, 1],
        [np.nan, np.nan, np.nan, 1],
    ])
    conc, comuns = concordancia(X)
    assert comuns[0, 1] == 3 and conc[0, 1] == 2 / 3
    assert comuns[0, 2] == 0 and np.isnan(conc[0, 2])
    assert comuns[1, 2] == 1 and conc[1, 2] == 1.0
