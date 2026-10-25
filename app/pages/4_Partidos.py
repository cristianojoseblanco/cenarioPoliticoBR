import plotly.graph_objects as go
import streamlit as st

from dados import CINZA, SERIES, dec, n, parquet, rodape, seletor_legislatura

st.set_page_config(page_title="Partidos · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Partidos")
st.session_state["_pagina"] = "4_Partidos.py"
seletor_legislatura()

p = parquet("governabilidade/partidos.parquet")
minimo = st.slider("Partidos com pelo menos N deputados no período", 1, 40, 5)
p = p[p["deputados"] >= minimo].copy()
p["cobertura"] = p["votos_disc"] / p["votos_com_valor"]
COB = 0.30

metrica = st.radio("Ordenar e desenhar por", ["Apoio ao governo", "Disciplina", "Coesão (Rice)"], horizontal=True)
col = {"Apoio ao governo": "apoio_gov", "Disciplina": "disciplina", "Coesão (Rice)": "rice"}[metrica]
s = p.sort_values(col)
cores = [CINZA if (col == "disciplina" and c < COB) else SERIES[0] for c in s["cobertura"]]
fig = go.Figure(go.Bar(
    x=100 * s[col], y=[f"{a} ({b})" for a, b in zip(s["partido"], s["deputados"])], orientation="h",
    marker=dict(color=cores), text=[f"{dec(100 * v, 0)}%" if v == v else "—" for v in s[col]], textposition="outside",
    hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
fig.update_layout(height=28 * len(s) + 80, margin=dict(l=0, r=30, t=10, b=0), plot_bgcolor="#fcfcfb",
                  paper_bgcolor="#fcfcfb")
fig.update_xaxes(range=[0, 110], gridcolor="#e4e3df", ticksuffix="%")
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
if col == "disciplina":
    st.caption(f"Barras cinza: disciplina medida em menos de {dec(100 * COB, 0)}% dos votos do partido "
               "(orienta pouco sozinho ou fica na parte cortada do nome do bloco). Ler com cautela.")

st.subheader("Tabela")
t = p.sort_values("apoio_gov", ascending=False)
st.dataframe(t.assign(
    **{"Partido": t["partido"], "Deputados no período": t["deputados"].map(n),
       "Apoio ao governo": t["apoio_gov"].map(lambda v: f"{dec(100 * v)}%"),
       "Disciplina": [f"{dec(100 * v)}%{'*' if c < COB else ''}" if v == v else "—" for v, c in zip(t["disciplina"], t["cobertura"])],
       "Votos com disciplina medida": [f"{dec(100 * c)}% ({n(a)} de {n(b)})" for c, a, b in
                                       zip(t["cobertura"], t["votos_disc"], t["votos_com_valor"])],
       "Coesão (Rice)": t["rice"].map(lambda v: f"{dec(100 * v)}%" if v == v else "—")}
)[["Partido", "Deputados no período", "Apoio ao governo", "Disciplina", "Votos com disciplina medida", "Coesão (Rice)"]],
    hide_index=True, use_container_width=True)
st.caption("Deputados no período: todos que passaram pelo partido em algum momento, inclusive suplentes.")
rodape()
