import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import SERIES, cor_com, dec, deputados_rede, json_, n, parquet, pct, rodape, rotulo

st.set_page_config(page_title="Deputado · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Ficha do deputado")

gov = parquet("governabilidade/deputados.parquet")
rede = deputados_rede().set_index("deputado_id")
base = gov.dropna(subset=["nome"]).sort_values("nome")
nomes = dict(zip(base["deputado_id"], base["nome"] + " (" + base["partido"].fillna("") + ")"))
dep_id = st.selectbox("Buscar deputado", list(nomes), format_func=nomes.get, index=None,
                      placeholder="Digite um nome")
if dep_id is None:
    st.info("Escolha um deputado para ver a ficha.")
    rodape()
    st.stop()

r = base.set_index("deputado_id").loc[dep_id]
com = rede["comunidade"].get(dep_id)
st.markdown(f"### {r['nome']}")
st.markdown(f"**{r['partido']}** · {rede['uf'].get(dep_id, '')}" +
            (f" · comunidade **{rotulo(com)}**" if isinstance(com, str) else " · fora do grafo (poucos votos)"))

c1, c2, c3 = st.columns(3)
c1.metric("Apoio ao governo", pct(round(r["apoio_gov"] * r["votos_gov"]), r["votos_gov"]) if r["votos_gov"] else "—")
c2.metric("Disciplina partidária", pct(round(r["disciplina"] * r["votos_disc"]), r["votos_disc"]) if r["votos_disc"] else "—")
c3.metric("Participação", pct(r["presentes"], r["em_exercicio"]) if r["em_exercicio"] == r["em_exercicio"] and r["em_exercicio"] else "—")

pos = parquet("fatias/posicoes.parquet")
pj = pos[(pos["tipo"] == "janela") & (pos["deputado_id"] == dep_id)].copy()
if not pj.empty and pj["posicao"].notna().any():
    st.subheader("Posição entre os polos ao longo do tempo")
    polos = json_("fatias/polos.json")
    pj["fim"] = pd.to_datetime(pj["fatia"].str[-10:])
    res = parquet("fatias/resumo.parquet")
    fig = go.Figure()
    if isinstance(com, str):
        cm = res[(res["tipo"] == "janela") & (res["comunidade_global"] == com)].copy()
        cm["fim"] = pd.to_datetime(cm["fatia"].str[-10:])
        fig.add_trace(go.Scatter(x=cm["fim"], y=cm["posicao_media"], name=f"Média de {com}", mode="lines",
                                 line=dict(color=cor_com(com), width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=pj["fim"], y=pj["posicao"], name=r["nome"], mode="lines+markers",
                             line=dict(color="#0b0b0b", width=2), marker=dict(size=7)))
    fig.add_hline(y=0, line=dict(color="#52514e", width=1))
    fig.update_yaxes(range=[-1, 1], gridcolor="#e4e3df", title=f"← A ({polos['polo_a']}) · B ({polos['polo_b']}) →")
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                      legend=dict(orientation="h", y=-0.2, x=0))
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

pares = parquet("redes/pares.parquet")
mine = pares[(pares["deputado_a"] == dep_id) | (pares["deputado_b"] == dep_id)].copy()
if not mine.empty:
    mine["outro"] = mine["deputado_a"].where(mine["deputado_b"] == dep_id, mine["deputado_b"])
    info = gov.set_index("deputado_id")[["nome", "partido"]]
    mine = mine.join(info, on="outro")
    fmt = lambda df: df.assign(  # noqa: E731
        Concordância=[pct(round(c * v), v) for c, v in zip(df["concordancia"], df["votacoes_comuns"])]
    )[["nome", "partido", "Concordância"]].rename(columns={"nome": "Deputado", "partido": "Partido"})
    c1, c2 = st.columns(2)
    c1.subheader("Vota mais parecido com")
    c1.dataframe(fmt(mine.sort_values("concordancia", ascending=False).head(10)), hide_index=True, use_container_width=True)
    c2.subheader("Vota mais diferente de")
    c2.dataframe(fmt(mine.sort_values("concordancia").head(10)), hide_index=True, use_container_width=True)
    st.caption("Concordância nas votações em que os dois votaram (mínimo de 50 em comum).")
rodape()
