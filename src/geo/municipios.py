"""Correspondência de municípios TSE ↔ IBGE (nome + UF), com tratamento de grafias.

O TSE usa código próprio de município; as emendas e o IBGE usam o código IBGE. A ligação é feita pelo nome
normalizado (sem acento, sem pontuação, maiúsculas) dentro da UF; o que não casar exato vai para a melhor
semelhança de texto na UF (mínimo `geo.semelhanca_minima`).
"""
from __future__ import annotations

import difflib
import re
import unicodedata

import pandas as pd

from src.config import ROOT


def norm(x) -> str:
    s = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z ]", " ", s.replace("D'", "D").replace("'", ""))
    return " ".join(s.split())


def ibge(cfg: dict) -> pd.DataFrame:
    return pd.read_parquet(ROOT / cfg["ibge"]["caminhos"]["staging"] / "municipios.parquet")


def tse_para_ibge(cfg: dict, tse: pd.DataFrame) -> pd.DataFrame:
    """tse: colunas CD_MUNICIPIO, NM_MUNICIPIO, SG_UF. Devolve CD_MUNICIPIO -> cod_ibge."""
    ib = ibge(cfg)[["cod_ibge", "nome", "uf"]].copy()
    ib["n"] = ib["nome"].map(norm)
    t = tse[["CD_MUNICIPIO", "NM_MUNICIPIO", "SG_UF"]].drop_duplicates("CD_MUNICIPIO").copy()
    t["n"] = t["NM_MUNICIPIO"].map(norm)
    m = t.merge(ib, left_on=["n", "SG_UF"], right_on=["n", "uf"], how="left")
    minimo = float(cfg.get("geo", {}).get("semelhanca_minima", 0.85))
    falta = m["cod_ibge"].isna() & (m["SG_UF"] != "ZZ")
    for i in m.index[falta]:
        cands = ib[ib["uf"] == m.at[i, "SG_UF"]]
        if cands.empty:
            continue
        notas = cands["n"].map(lambda x: difflib.SequenceMatcher(None, x, m.at[i, "n"]).ratio())
        if notas.max() >= minimo:
            m.at[i, "cod_ibge"] = cands.loc[notas.idxmax(), "cod_ibge"]
    return m[["CD_MUNICIPIO", "cod_ibge"]]
