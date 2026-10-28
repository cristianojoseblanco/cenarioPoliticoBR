import pandas as pd
import plotly.express as px
import streamlit as st

from dados import json_, leg_atual, marts, parquet, rodape, seletor_legislatura

st.set_page_config(page_title="Campanha · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Campanha (TSE) × Plenário")
st.session_state["_pagina"] = "11_Campanha.py"
seletor_legislatura()
if not (marts() / f"leg{leg_atual()}" / "eleicao" / "resumo.json").exists():
    st.info("Ainda não calculado para esta legislatura.")
    rodape()
    st.stop()
r = json_("eleicao/resumo.json")
pa = parquet("eleicao/parlamentares.parquet")
co = parquet("eleicao/correlacoes.parquet")
st.caption(f"Eleições {', '.join(map(str, r['eleicoes']))}: {r['ligados']} de {r['eleitos']} eleitos ligados ao Plenário.")
c = st.columns(4)
c[0].metric("Votos (mediana)", f"{r['mediana_votos']:,.0f}".replace(",", "."))
c[1].metric("Receita (mediana)", f"R$ {r['mediana_receita']:,.0f}".replace(",", "."))
c[2].metric("Custo por voto (mediana)", f"R$ {r['mediana_custo_por_voto']:.2f}".replace(".", ","))
c[3].metric("Fundo eleitoral (mediana)", f"{100 * r['mediana_frac_fundo_eleitoral']:.0f}%")
xs = {"maior_municipio": "Peso do maior município", "frac_fundo_eleitoral": "% do fundo eleitoral", "custo_por_voto": "Custo por voto",
      "municipios_1pct": "Municípios com 1%+ dos votos", "receita_total": "Receita total"}
ys = {"disciplina": "Disciplina", "imprevisibilidade": "Votos imprevisíveis", "apoio_gov": "Apoio ao governo", "participacao": "Participação"}
a, b = st.columns(2)
x = a.selectbox("Campanha", list(xs), format_func=xs.get)
ys = {k: v for k, v in ys.items() if k in pa}
if not ys:
    st.info("Ainda sem votos no Plenário para cruzar.")
    rodape()
    st.stop()
y = b.selectbox("Plenário", list(ys), format_func=ys.get)
d = pa.dropna(subset=[x, y])
st.plotly_chart(px.scatter(d, x=x, y=y, color="comunidade", hover_name="NM_URNA_CANDIDATO", hover_data=["SG_PARTIDO", "SG_UF", "votos"],
                           labels={x: xs[x], y: ys[y]}), use_container_width=True)
st.subheader("Relações (Spearman, em todos e dentro do partido)")
st.dataframe(co.sort_values("p_dentro"), hide_index=True)
st.subheader("Eleitos")
st.dataframe(pa[[c_ for c_ in ["NM_URNA_CANDIDATO", "SG_PARTIDO", "SG_UF", "DS_SIT_TOT_TURNO", "votos", "frac_uf", "municipio_principal",
                               "maior_municipio", "receita_total", "custo_por_voto", "frac_fundo_eleitoral", "apoio_gov", "disciplina",
                               "imprevisibilidade"] if c_ in pa]], hide_index=True)
rodape()
