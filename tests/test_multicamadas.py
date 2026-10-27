import pandas as pd

from src.networks.multicamadas import co_pesos


def test_co_pesos_inverso_do_tamanho():
    g = pd.DataFrame({"deputado_id": ["1", "2", "1", "2", "3"], "grupo": ["a", "a", "b", "b", "b"]})
    p = co_pesos(g, "grupo").set_index(["deputado_a", "deputado_b"])["peso"]
    # par 1-2: grupo a (k=2 -> 1) + grupo b (k=3 -> 0,5)
    assert abs(p[("1", "2")] - 1.5) < 1e-9
    assert abs(p[("1", "3")] - 0.5) < 1e-9


def test_co_pesos_maximo():
    g = pd.DataFrame({"deputado_id": list("1234"), "grupo": ["a"] * 4})
    assert co_pesos(g, "grupo", maximo=3).empty
