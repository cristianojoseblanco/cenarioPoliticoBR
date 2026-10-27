import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import MARTS, SERIES, n, pct, rodape

st.set_page_config(page_title="Acompanhados · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Vota com o partido ou sozinho?")
st.session_state["_pagina"] = "8_Acompanhados.py"
base = MARTS / "acompanhamento"
if not (base / "deputados.json").exists():
    st.info("Ainda não calculado.")
    rodape()
    st.stop()
fichas = json.loads((base / "deputados.json").read_text(encoding="utf-8"))
mm = pd.read_parquet(base / "mensal.parquet")
rb = pd.read_parquet(base / "rebeldias.parquet")
st.caption("Cada taxa vem ao lado da média dos colegas do mesmo partido nas mesmas votações. "
           "Lista de deputados em `acompanhar` no config/sources.yaml.")

f = st.selectbox("Deputado", fichas, format_func=lambda x: f"{x['nome']} ({x.get('uf') or ''})")
st.markdown(f"### {f['nome']}")
if f.get("eleicao"):
    st.caption(f["eleicao"])
if not f.get("votos"):
    st.info(f"{f['situacao']}. A ficha se preenche a partir das primeiras votações nominais no Plenário.")
    rodape()
    st.stop()

c = st.columns(4)
for col, (rot, v, k, ref) in zip(c, [("Segue o partido", "segue_partido", "n_segue_partido", "partido_segue_partido"),
                                     ("Com a bancada", "com_bancada", "n_com_bancada", "partido_com_bancada"),
                                     ("Apoio ao governo", "apoio_gov", "n_apoio_gov", "partido_apoio_gov"),
                                     ("Votos contra o partido", None, None, None)]):
    if v:
        col.metric(rot, pct(round(f[v] * f[k]), f[k]), help=f"colegas de partido: {100 * (f[ref] or 0):.1f}%".replace(".", ","))
        col.caption(f"colegas de partido: {100 * (f[ref] or 0):.1f}%".replace(".", ","))
    else:
        col.metric(rot, n(f["rebeldias"]))
if f.get("bancada_pequena_atual"):
    st.warning("A bancada atual tem menos de 3 colegas votando: 'segue o partido' pode refletir a orientação do próprio deputado.")

m = mm[mm["deputado_id"] == f["deputado_id"]].sort_values("mes")
med = st.radio("Medida", ["segue_partido", "com_bancada", "apoio_gov"], horizontal=True,
               format_func={"segue_partido": "Segue o partido", "com_bancada": "Com a bancada", "apoio_gov": "Apoio ao governo"}.get)
fig = go.Figure()
fig.add_scatter(x=m["mes"], y=m[med], name=f["nome"], mode="lines+markers", line=dict(color=SERIES[2], width=2),
                marker=dict(size=(m["votos"] ** .5).clip(3, 14)), customdata=m[["partido", "votos"]],
                hovertemplate="%{x|%m/%Y} · %{customdata[0]}<br>%{y:.0%} em %{customdata[1]} votos<extra></extra>")
fig.add_scatter(x=m["mes"], y=m[f"partido_{med}"], name="colegas de partido", mode="lines", line=dict(color="#7a8780", dash="dash"))
fig.update_layout(yaxis_tickformat=".0%", height=380, legend=dict(orientation="h"), margin=dict(t=10))
st.plotly_chart(fig, use_container_width=True)

if f.get("legislaturas"):
    st.subheader("Por legislatura")
    st.dataframe(pd.DataFrame(f["legislaturas"]).drop(columns=["posicoes"]), hide_index=True)
r = rb[rb["deputado_id"] == f["deputado_id"]]
if len(r):
    st.subheader("Votos contra a orientação do partido")
    st.dataframe(r[["data", "partido", "proposicao", "voto_dep", "orientacao_partido", "orientacao_governo", "texto"]],
                 hide_index=True)
rodape()
