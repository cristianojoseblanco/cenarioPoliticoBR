import plotly.graph_objects as go
import streamlit as st

from dados import CINZA, SERIES, cor_com, deputados_rede, n, ordem_com, parquet, rodape, rotulo, seletor_legislatura

st.set_page_config(page_title="Rede · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Rede de votação")
st.session_state["_pagina"] = "1_Rede.py"
seletor_legislatura()
st.markdown("Cada ponto é um deputado. Cada linha liga um deputado aos 15 colegas que **votam mais parecido** com ele. "
            "Quem fica perto no desenho vota parecido.")

d = deputados_rede()
ar = parquet("redes/arestas.parquet")

cor_por = st.radio("Colorir por", ["Comunidade", "Partido"], horizontal=True)
partidos = d["partido"].value_counts()
destaque = st.multiselect("Destacar partidos", list(partidos.index), placeholder="Todos")

pos = d.set_index("deputado_id")[["x", "y"]]
ex, ey = [], []
for a, b in zip(ar["deputado_a"], ar["deputado_b"]):
    if a in pos.index and b in pos.index:
        ex += [pos.at[a, "x"], pos.at[b, "x"], None]
        ey += [pos.at[a, "y"], pos.at[b, "y"], None]

fig = go.Figure()
fig.add_trace(go.Scattergl(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.12)", width=0.5),
                           hoverinfo="skip", showlegend=False))

if cor_por == "Comunidade":
    grupos = [(c, d[d["comunidade"] == c], cor_com(c), rotulo(c)) for c in ordem_com(d["comunidade"])]
else:
    top = list(partidos.index[:8])
    grupos = [(p, d[d["partido"] == p], SERIES[i], p) for i, p in enumerate(top)]
    grupos.append(("outros", d[~d["partido"].isin(top)], CINZA, "Outros partidos"))

for _, sub, cor, nome in grupos:
    em_destaque = sub["partido"].isin(destaque) if destaque else sub["partido"].notna()
    fig.add_trace(go.Scattergl(
        x=sub["x"], y=sub["y"], mode="markers", name=nome,
        marker=dict(color=cor, size=[10 if a else 6 for a in em_destaque] if destaque else 7,
                    opacity=[1.0 if a else 0.15 for a in em_destaque] if destaque else 0.95,
                    line=dict(color="#fcfcfb", width=1)),
        customdata=sub[["nome", "partido", "uf", "comunidade"]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<br>"
                      "Comunidade %{customdata[3]}<extra></extra>",
    ))

fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                  xaxis=dict(visible=False), yaxis=dict(visible=False),
                  legend=dict(orientation="h", yanchor="top", y=-0.02, x=0, font=dict(size=11)),
                  hoverlabel=dict(bgcolor="white"))
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

st.subheader("Composição das comunidades")
tab = (d.groupby("comunidade")
       .agg(deputados=("deputado_id", "size"),
            partidos=("partido", lambda s: ", ".join(f"{p} {q}" for p, q in s.value_counts().head(5).items())))
       .loc[ordem_com(d["comunidade"])])
tab["deputados"] = tab["deputados"].map(n)
st.dataframe(tab.rename(columns={"deputados": "Deputados", "partidos": "Principais partidos"}),
             use_container_width=True)

st.subheader("Pontes entre comunidades")
st.markdown("Deputados cujas ligações mais fortes se espalham por várias comunidades (coeficiente de participação).")
pontes = d.sort_values("participacao", ascending=False).head(15)
st.dataframe(pontes[["nome", "partido", "uf", "comunidade", "participacao"]].rename(columns={
    "nome": "Deputado", "partido": "Partido", "uf": "UF", "comunidade": "Comunidade", "participacao": "Participação"}),
    hide_index=True, use_container_width=True,
    column_config={"Participação": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})
rodape()
