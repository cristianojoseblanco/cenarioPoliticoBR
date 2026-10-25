"""Leitura dos resultados (data/marts) e formatação para o painel.

O painel só lê arquivos prontos; nenhum cálculo pesado roda aqui.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts" / "camara"
META = ROOT / "data" / "metadata" / "camara"

# Paleta categórica de referência (ordem fixa) — a mesma dos gráficos estáticos.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CINZA = "#b7b5ae"


@st.cache_data(ttl=3600)
def parquet(rel: str) -> pd.DataFrame:
    return pd.read_parquet(MARTS / rel)


@st.cache_data(ttl=3600)
def json_(rel: str) -> dict:
    return json.loads((MARTS / rel).read_text(encoding="utf-8"))


@st.cache_data(ttl=3600)
def atualizado_em() -> str:
    try:
        d = json.loads((META / "_ultima_execucao.json").read_text(encoding="utf-8"))
        return pd.Timestamp(d["executado_em"]).tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y")
    except Exception:
        return "—"


def deputados_rede() -> pd.DataFrame:
    return parquet("redes/deputados_rede.parquet")


def ordem_com(cs) -> list[str]:
    return sorted(set(cs), key=lambda c: int(str(c)[1:]))


@st.cache_data(ttl=3600)
def composicao() -> dict[str, str]:
    d = deputados_rede()
    return {c: ", ".join(f"{p} {q}" for p, q in d[d["comunidade"] == c]["partido"].value_counts().head(2).items())
            for c in ordem_com(d["comunidade"])}


def rotulo(c: str) -> str:
    return f"{c} · {composicao().get(c, '')}"


def cor_com(c: str) -> str:
    return SERIES[(int(str(c)[1:]) - 1) % len(SERIES)]


# ---------------------------------------------------------------- formatação

def n(x) -> str:
    """Número inteiro com ponto de milhar."""
    return f"{int(round(x)):,}".replace(",", ".")


def grande(x) -> str:
    """Número grande por extenso: 473 mil, 1,2 milhão."""
    x = float(x)
    if x >= 1e9:
        v, u = x / 1e9, ("bilhão", "bilhões")
    elif x >= 1e6:
        v, u = x / 1e6, ("milhão", "milhões")
    elif x >= 1e4:
        return f"{x / 1e3:.0f} mil"
    else:
        return n(x)
    txt = f"{v:.1f}".replace(".", ",").replace(",0", "")
    return f"{txt} {u[0] if v < 2 else u[1]}"


def dec(x, d=1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def pct(a, b, d=1) -> str:
    """Porcentagem sempre com o número que ela representa: 85,4% (750 de 878)."""
    if not b:
        return "—"
    return f"{dec(100 * a / b, d)}% ({n(a)} de {n(b)})"


def rodape():
    st.caption(
        f"Dados: Câmara dos Deputados (dados abertos), Plenário, 2023 em diante. Atualizado em {atualizado_em()}. "
        "Comunidades e polos são definidos pelos votos, sem rótulo ideológico. "
        "Código e método: github.com/cristianojoseblanco/cenarioPoliticoBR"
    )
