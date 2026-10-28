import plotly.express as px
import streamlit as st

from dados import json_, leg_atual, marts, parquet, rodape, seletor_legislatura

st.set_page_config(page_title="Emendas · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Emendas parlamentares × Plenário")
st.session_state["_pagina"] = "12_Emendas.py"
seletor_legislatura()
if not (marts() / f"leg{leg_atual()}" / "emendas" / "resumo.json").exists():
    st.info("Ainda não calculado para esta legislatura.")
    rodape()
    st.stop()
r = json_("emendas/resumo.json")
pa = parquet("emendas/parlamentares.parquet")
co = parquet("emendas/correlacoes.parquet")
st.caption(f"Emendas individuais dos orçamentos {r['anos_orcamento'][0]}–{r['anos_orcamento'][-1]}. Mapa interativo na página do projeto.")
c = st.columns(4)
c[0].metric("Pago", f"R$ {r['pago'] / 1e9:.1f} bi".replace(".", ","))
c[1].metric("Empenhado", f"R$ {r['empenhado'] / 1e9:.1f} bi".replace(".", ","))
c[2].metric("Execução (mediana)", f"{100 * r['execucao_mediana']:.0f}%")
if r.get("conexao_mediana"):
    c[3].metric("Base ÷ resto da UF (R$/hab.)", f"{r['conexao_mediana']:.2f}".replace(".", ","))
d = pa.dropna(subset=["execucao", "apoio_gov"])
st.plotly_chart(px.scatter(d, x="execucao", y="apoio_gov", color="partido", hover_name="nome", size="pago",
                           labels={"execucao": "Taxa de execução (pago ÷ empenhado)", "apoio_gov": "Apoio ao governo"}),
                use_container_width=True)
st.subheader("Emendas × comportamento (Spearman, em todos e dentro do partido)")
st.dataframe(co, hide_index=True)
st.subheader("Parlamentares")
st.dataframe(pa.sort_values("pago", ascending=False), hide_index=True)
rodape()
