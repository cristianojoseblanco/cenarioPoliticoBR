import plotly.graph_objects as go
import streamlit as st

from dados import MARTS, SERIES, json_, leg_atual, n, parquet, rodape, seletor_legislatura

st.set_page_config(page_title="Imprevisíveis · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Quem vota fora do roteiro")
st.session_state["_pagina"] = "10_Imprevisiveis.py"
seletor_legislatura()
if not (MARTS / f"leg{leg_atual()}" / "modelo" / "resumo.json").exists():
    st.info("Ainda não calculado para esta legislatura.")
    rodape()
    st.stop()
r = json_("modelo/resumo.json")
dep = parquet("modelo/deputados.parquet")
st.caption("Modelo de voto individual (gradient boosting, validação cruzada por votação). Voto imprevisível = o modelo "
           "dava menos de 20% de chance ao voto que ocorreu.")
c = st.columns(3)
for col, k, rot in zip(c, ["M0", "M1", "M2"], ["Segue o partido", "Partido, governo e colegas", "+ perfil e tema"]):
    col.metric(rot, f"{100 * r['metricas'][k]['acerto']:.1f}% de acerto".replace(".", ","), f"AUC {r['metricas'][k]['auc']:.3f}", delta_color="off")
st.write(f"{n(r['surpresas'])} votos imprevisíveis em {n(r['votos'])} ({100 * r['imprevisibilidade']:.1f}%).".replace(".", ",", 1))

minimo = st.slider("Mínimo de votos do deputado", 50, 1000, 100, 50)
d = dep[dep["votos"] >= minimo].sort_values("imprevisibilidade", ascending=False)
st.dataframe(d[["nome", "partido", "votos", "surpresas", "imprevisibilidade", "imprev_partido", "contra_partido"]],
             hide_index=True, column_config={"imprevisibilidade": st.column_config.NumberColumn(format="percent"),
                                              "imprev_partido": st.column_config.NumberColumn("mediana do partido", format="percent")})
st.subheader("Temas")
t = parquet("modelo/temas.parquet")
fig = go.Figure(go.Bar(x=t["imprevisibilidade"], y=t["tema"], orientation="h", marker_color=SERIES[1]))
fig.update_layout(xaxis_tickformat=".1%", height=420, margin=dict(t=10), yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)
st.subheader("Mês a mês")
m = parquet("modelo/mensal.parquet")
fig2 = go.Figure(go.Scatter(x=m["mes"], y=m["imprevisibilidade"], mode="lines+markers", line=dict(color=SERIES[0])))
fig2.update_layout(yaxis_tickformat=".1%", height=300, margin=dict(t=10))
st.plotly_chart(fig2, use_container_width=True)
st.subheader("Votações com mais votos imprevisíveis")
st.dataframe(parquet("modelo/votacoes.parquet"), hide_index=True)
st.subheader("O que mais pesa na previsão")
st.dataframe(parquet("modelo/importancias.parquet"), hide_index=True)
rodape()
