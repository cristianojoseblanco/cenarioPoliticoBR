import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import cor_com, dec, json_, ordem_com, parquet, rodape, rotulo

st.set_page_config(page_title="Tempo · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Ao longo do tempo")
st.markdown("Cada ponto é uma **janela de 150 votações seguidas**, na data da última votação.")

polos = json_("fatias/polos.json")
res = parquet("fatias/resumo.parquet")
jan = res[res["tipo"] == "janela"].copy()
jan["fim"] = pd.to_datetime(jan["fatia"].str[-10:])
gov = parquet("governabilidade/janelas_comunidade.parquet")
vit = parquet("governabilidade/janelas_vitoria.parquet")

coms = ordem_com(jan["comunidade_global"])
escolha = st.multiselect("Comunidades", coms, default=coms, format_func=rotulo)
metrica = st.radio("Mostrar", ["Posição entre os polos", "Apoio ao governo"], horizontal=True)

fig = go.Figure()
for c in escolha:
    if metrica == "Posição entre os polos":
        s = jan[jan["comunidade_global"] == c].sort_values("fim")
        y, txt = s["posicao_media"], [dec(v, 2) for v in s["posicao_media"]]
    else:
        s = gov[gov["comunidade"] == c].sort_values("fim")
        y, txt = 100 * s["apoio"], [f"{dec(100 * v)}%" for v in s["apoio"]]
    fig.add_trace(go.Scatter(x=s["fim"], y=y, mode="lines+markers", name=rotulo(c), text=txt,
                             line=dict(color=cor_com(c), width=2), marker=dict(size=7, line=dict(color="#fcfcfb", width=1.5)),
                             hovertemplate="%{x|%d/%m/%Y}: %{text}<extra>" + c + "</extra>"))
if metrica == "Posição entre os polos":
    fig.add_hline(y=0, line=dict(color="#52514e", width=1))
    fig.update_yaxes(range=[-1, 1], title=f"← A ({polos['polo_a']}) · B ({polos['polo_b']}) →")
    st.caption(f"Polo A = {polos['polo_a']} ({polos['composicao'][polos['polo_a']]}); "
               f"polo B = {polos['polo_b']} ({polos['composicao'][polos['polo_b']]}). "
               "São as duas comunidades que mais discordam entre si; não representam esquerda ou direita.")
else:
    fig.update_yaxes(range=[0, 100], title="% dos votos iguais à orientação do Governo")
fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                  legend=dict(orientation="h", y=-0.15, x=0), hovermode="x unified")
fig.update_xaxes(gridcolor="#e4e3df")
fig.update_yaxes(gridcolor="#e4e3df")
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

st.subheader("Votações vencidas pelo governo")
v = vit.sort_values("fim")
fig2 = go.Figure(go.Scatter(
    x=v["fim"], y=100 * v["vitoria"], mode="lines+markers", line=dict(color="#52514e", width=2),
    text=[f"{dec(100 * a)}% ({int(round(a * b))} de {b})" for a, b in zip(v["vitoria"], v["votacoes_gov"])],
    hovertemplate="%{x|%d/%m/%Y}: %{text}<extra></extra>"))
fig2.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb")
fig2.update_yaxes(range=[50, 100], title="% de vitórias", gridcolor="#e4e3df")
fig2.update_xaxes(gridcolor="#e4e3df")
st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False})

st.subheader("Quem mais se moveu no eixo")
st.markdown("Posição média nas 3 últimas janelas menos a posição nas 3 primeiras. Negativo = foi para o polo A.")
desl = parquet("fatias/deslocamentos.parquet")
from dados import deputados_rede  # noqa: E402
d = deputados_rede().set_index("deputado_id")
desl = desl.join(d[["nome", "partido", "comunidade"]], how="inner")
desl = desl.reindex(desl["delta"].abs().sort_values(ascending=False).index).head(20)
st.dataframe(desl[["nome", "partido", "comunidade", "inicio", "fim", "delta"]].rename(columns={
    "nome": "Deputado", "partido": "Partido", "comunidade": "Comunidade", "inicio": "Início", "fim": "Fim",
    "delta": "Deslocamento"}).round(2), hide_index=True, use_container_width=True)
rodape()
