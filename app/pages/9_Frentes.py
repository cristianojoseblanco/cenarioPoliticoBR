import plotly.graph_objects as go
import streamlit as st

from dados import marts, SERIES, json_, leg_atual, n, parquet, rodape, seletor_legislatura

st.set_page_config(page_title="Frentes · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Frentes parlamentares e coautoria")
st.session_state["_pagina"] = "9_Frentes.py"
seletor_legislatura()
if not (marts() / f"leg{leg_atual()}" / "multicamadas" / "resumo.json").exists():
    st.info("Ainda não calculado para esta legislatura.")
    rodape()
    st.stop()
r = json_("multicamadas/resumo.json")
tem = parquet("multicamadas/frentes_tematicas.parquet")
fr = parquet("multicamadas/frentes.parquet")
cr = parquet("multicamadas/correlacoes.parquet")
st.caption("Frente parlamentar exige a assinatura de um terço do Congresso: quase toda frente tem cerca de 200 membros. "
           "A pergunta é se assinar muda o voto em relação aos colegas do mesmo partido.")

st.subheader("Frentes-chave: efeito no tema da frente")
if len(tem):
    t = tem.sort_values("especifico")
    fig = go.Figure()
    fig.add_scatter(y=t["frente"], x=100 * t["dif_outros"], mode="markers", name="demais temas (controle)",
                    marker=dict(symbol="circle-open", size=11, color="#47554e"),
                    error_x=dict(type="data", symmetric=False, array=100 * (t["ic_outros_sup"] - t["dif_outros"]),
                                 arrayminus=100 * (t["dif_outros"] - t["ic_outros_inf"])))
    fig.add_scatter(y=t["frente"], x=100 * t["dif_tema"], mode="markers", name="tema da frente",
                    marker=dict(size=12, color=["#147a54" if c and e > 0 else "#b4541c" if c else "#7a8780" for c, e in zip(t["efeito_claro"], t["especifico"])]),
                    error_x=dict(type="data", symmetric=False, array=100 * (t["ic_tema_sup"] - t["dif_tema"]),
                                 arrayminus=100 * (t["dif_tema"] - t["ic_tema_inf"])))
    fig.add_vline(x=0, line_color="#121c17")
    fig.update_layout(height=60 + 48 * len(t), xaxis_title="membros − colegas de partido não membros (p.p.)",
                      legend=dict(orientation="h"), margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(tem[["frente", "titulo", "membros", "temas", "votacoes_tema", "especifico", "efeito_claro"]], hide_index=True)

st.subheader("Coautoria e voto")
st.dataframe(cr, hide_index=True)
st.subheader("Coesão das frentes além da composição partidária")
st.caption(f"{n(r['frentes_bloco'])} de {n(r['frentes_analisadas'])} frentes acima do percentil 95. Pode ser seleção de quem assina.")
st.dataframe(fr.sort_values("excesso", ascending=False), hide_index=True)
st.caption(f"Grupos com voto + frentes + coautoria × só voto (ARI): {r['ari_multi_voto']:.2f}".replace(".", ","))
rodape()
