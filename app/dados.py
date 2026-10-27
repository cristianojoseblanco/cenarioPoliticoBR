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


def legislaturas() -> list[str]:
    return sorted(p.name[3:] for p in MARTS.glob("leg*") if p.is_dir())


@st.cache_data(ttl=3600)
def _legs_cfg() -> dict:
    import yaml
    try:
        return yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8")).get("legislaturas", {})
    except Exception:
        return {}


def nome_leg(leg: str) -> str:
    """Ex.: '57ª · Governo Lula (3º mandato) · 2023–2026'."""
    c = _legs_cfg().get(leg, {})
    anos = f"{c['inicio'][:4]}–{int(c['fim'][:4]) - 1}" if c.get("inicio") else ""
    partes = [f"{leg}ª", c.get("governo", ""), anos]
    return " · ".join(p for p in partes if p)


def leg_atual() -> str:
    legs = legislaturas()
    if st.session_state.get("leg") not in legs:
        st.session_state["leg"] = legs[-1]
    return st.session_state["leg"]


def seletor_legislatura():
    """Seletor no topo da página; a escolha vale para todas as páginas da sessão."""
    legs = legislaturas()
    atual = leg_atual()
    if len(legs) > 1:
        escolha = st.radio("Legislatura", legs, index=legs.index(atual), horizontal=True, format_func=nome_leg,
                           key=f"radio_leg_{st.session_state.get('_pagina', '')}")
        st.session_state["leg"] = escolha
    return st.session_state["leg"]


@st.cache_data(ttl=3600)
def _parquet(leg: str, rel: str) -> pd.DataFrame:
    return pd.read_parquet(MARTS / f"leg{leg}" / rel)


@st.cache_data(ttl=3600)
def _json(leg: str, rel: str) -> dict:
    return json.loads((MARTS / f"leg{leg}" / rel).read_text(encoding="utf-8"))


def parquet(rel: str) -> pd.DataFrame:
    return _parquet(leg_atual(), rel)


def json_(rel: str) -> dict:
    return _json(leg_atual(), rel)


@st.cache_data(ttl=3600)
def comparacao(rel: str):
    p = MARTS / "comparacao" / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")) if p.suffix == ".json" else pd.read_parquet(p)


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


def composicao() -> dict[str, str]:
    return _composicao(leg_atual())


@st.cache_data(ttl=3600)
def _composicao(leg: str) -> dict[str, str]:
    d = _parquet(leg, "redes/deputados_rede.parquet")
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


@st.cache_data(ttl=3600)
def marcadores_periodo() -> list[dict]:
    import yaml
    try:
        cfg = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
        return cfg.get("marcadores_periodo", [])
    except Exception:
        return []


def marcar_periodos(fig):
    """Sombreia períodos especiais (ex.: votação remota) num gráfico com eixo de datas."""
    for m in marcadores_periodo():
        fig.add_vrect(x0=m["inicio"], x1=m["fim"], fillcolor="#e4e3df", opacity=0.5, line_width=0, layer="below",
                      annotation_text=m["rotulo"], annotation_position="top left",
                      annotation_font=dict(size=10, color="#52514e"))
    return fig


def rodape():
    st.caption(
        f"Dados: Câmara dos Deputados (dados abertos), Plenário, legislatura {nome_leg(leg_atual())}. "
        f"Atualizado em {atualizado_em()}. "
        "Comunidades e polos são definidos pelos votos, sem rótulo ideológico. "
        "Código e método: github.com/cristianojoseblanco/cenarioPoliticoBR"
    )
