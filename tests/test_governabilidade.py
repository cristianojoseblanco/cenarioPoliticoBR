"""Testes da leitura de orientações (partido > federação > bloco) e do índice de Rice."""
import pandas as pd

from src.config import load_config
from src.governance.indicadores import membros_bloco, orientacoes_partidarias, rice

G = load_config()["governabilidade"]


def test_membros_bloco_para_no_corte():
    assert membros_bloco("Bl MdbPsdRepPode", G["blocos"]) == ["MDB", "PSD", "REPUBLICANOS", "PODE"]
    assert membros_bloco("Bl UniPpFdrPsdbCid...", G["blocos"]) == ["UNIÃO", "PP", "PSDB", "CIDADANIA"]
    assert membros_bloco("Bl XyzPp", G["blocos"]) == []  # abreviação desconhecida no início: nada


def test_prioridade_partido_federacao_bloco():
    o = pd.DataFrame([
        ("v1", "Bl MdbPsdRepPode", "Sim"),
        ("v1", "PSD", "Não"),                 # partido orientou: vence o bloco
        ("v1", "Fdr PT-PCdoB-PV", "Sim"),
        ("v1", "Governo", "Sim"),            # não é partido
        ("v1", "Novo", "Liberado"),          # apelido + liberado
    ], columns=["votacao_id", "bancada", "orientacao"])
    op = orientacoes_partidarias(o, G).set_index("partido")
    assert op.loc["PSD", "valor"] == -1 and op.loc["PSD", "nivel"] == "partido"
    assert op.loc["MDB", "valor"] == 1 and op.loc["MDB", "nivel"] == "bloco"
    assert op.loc["PCdoB", "nivel"] == "federacao"
    assert bool(op.loc["NOVO", "liberado"]) and pd.isna(op.loc["NOVO", "valor"])
    assert "Governo" not in op.index


def test_rice():
    b = pd.DataFrame({"votacao_id": ["v"] * 6, "partido": ["A"] * 6, "valor": [1, 1, 1, 1, -1, None]})
    r = rice(b, 5)
    assert r.loc[0, "rice"] == 3 / 5
