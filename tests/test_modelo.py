import numpy as np
import pandas as pd

from src.models.voto_individual import m0


def test_m0_segue_partido_e_cai_nos_colegas():
    b = pd.DataFrame({"or_partido": [1, -1, 0], "colegas_sim": [0.1, 0.9, 0.8]})
    p = m0(b)
    assert p[0] > 0.9 and p[1] < 0.1 and abs(p[2] - 0.8) < 1e-9
