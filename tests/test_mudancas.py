import numpy as np

from src.governance.acompanhamento import _norm
from src.networks.mudancas import pelt


def test_pelt_acha_degrau_claro():
    rng = np.random.default_rng(0)
    x = np.r_[rng.normal(0, 0.3, 20), rng.normal(3, 0.3, 20)][:, None]
    assert pelt(x, 1.0, 3) == [20]


def test_pelt_sem_mudanca_em_ruido():
    rng = np.random.default_rng(1)
    assert pelt(rng.normal(0, 1, (40, 2)), 1.0, 3) == []


def test_norm_nome():
    assert _norm("  Lucas  PAVANATO ") == "lucas pavanato"
    assert _norm("Jônes Manoel") == "jones manoel"
