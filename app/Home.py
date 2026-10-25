"""Painel do Laboratório de Inteligência Política do Brasil.

Rodar: streamlit run app/Home.py
"""
import streamlit as st

from dados import composicao, grande, json_, n, parquet, pct, rodape, rotulo, seletor_legislatura

st.set_page_config(page_title="Cenário Político BR", page_icon="🏛️", layout="wide")

st.title("Cenário Político BR")
st.session_state["_pagina"] = "Home.py"
seletor_legislatura()
st.markdown("Como os deputados federais votam: **quem vota com quem, sobre o quê e como isso muda no tempo.** "
            "Plenário da Câmara, legislaturas de 2019 em diante. Os números abaixo são da legislatura escolhida.")

m = json_("redes/metricas.json")
g = json_("governabilidade/resumo.json")
dep = parquet("governabilidade/deputados.parquet")
votos_total = int(dep["votos_gov"].sum())

c1, c2 = st.columns(2)
c1.metric("Votações nominais no Plenário", n(m["votacoes"]["votacoes_total"]))
c2.metric("Deputados analisados", n(m["deputados_no_grafo"]))
c3, c4 = st.columns(2)
c3.metric("Comunidades de votação", len(m["comunidades"]))
c4.metric("Votações vencidas pelo governo", pct(g["vitorias_gov"], g["votacoes_gov"]))

st.subheader("As comunidades")
st.markdown("Grupos de deputados que votam de forma parecida, encontrados pelo algoritmo a partir dos votos. "
            "O nome é só a composição: **não há rótulo de esquerda ou direita.**")
for c, tam in m["comunidades"].items():
    st.markdown(f"- **{rotulo(c)}** — {n(tam)} deputados")

st.subheader("Páginas")
st.markdown(
    "- **Rede**: o mapa de quem vota com quem.\n"
    "- **Tempo**: como as comunidades se movem e o apoio ao governo ao longo da legislatura.\n"
    "- **Temas**: em que assuntos o centro vota com cada lado.\n"
    "- **Partidos**: apoio ao governo, disciplina e coesão.\n"
    "- **Deputado**: ficha individual, com os colegas que votam mais parecido.\n"
    "- **Comparação**: as duas legislaturas lado a lado e os deputados reeleitos."
)
with st.expander("Como ler os números"):
    st.markdown(
        "- **Concordância**: proporção das votações em comum em que dois deputados votaram igual.\n"
        "- **Eixo entre polos**: −1 = vota sempre com o núcleo do polo A e nunca com o do B; +1 = o contrário. "
        "Os polos são as duas comunidades que mais discordam entre si.\n"
        "- **Apoio ao governo**: % dos votos iguais à orientação do líder do Governo.\n"
        "- **Disciplina**: % dos votos iguais à orientação do próprio partido (ou federação, ou bloco).\n"
        "- **Coesão (Rice)**: quanto o partido vota unido; 100% = todos iguais.\n"
        "- **Participação**: votos registrados ÷ votações em que o deputado estava em exercício."
    )
rodape()
