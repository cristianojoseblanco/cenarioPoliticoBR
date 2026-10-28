import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import marts, SERIES, json_, leg_atual, marcar_periodos, n, parquet, rodape, rotulo, seletor_legislatura

st.set_page_config(page_title="Mudanças · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Quando o Plenário mudou de comportamento")
st.session_state["_pagina"] = "7_Mudancas.py"
seletor_legislatura()

if not (marts() / f"leg{leg_atual()}" / "mudancas" / "resumo.json").exists():
    st.info("Ainda não calculado para esta legislatura.")
    rodape()
    st.stop()

r = json_("mudancas/resumo.json")
s = parquet("mudancas/series.parquet")
seg = parquet("mudancas/segmentos.parquet")
pts = parquet("mudancas/pontos.parquet")
jan = parquet("mudancas/janelas.parquet")
st.caption("Pontos de mudança: PELT (custo L2) nas séries mensais padronizadas, penalidade do tipo BIC. "
           "Robusto = continua aparecendo com a penalidade × 0,5 e × 1,5. Proximidade com um evento não prova causa.")

nomes = {"apoio_polo_a": f"Apoio ao governo · polo A ({rotulo(r['polo_a'])})",
         "apoio_polo_b": f"Apoio ao governo · polo B ({rotulo(r['polo_b'])})",
         "apoio_fora": "Apoio ao governo · fora dos polos", "polarizacao": "Votações polarizadas",
         "vitoria_gov": "Vitórias do governo"}
esc = st.multiselect("Séries", list(nomes), default=["apoio_polo_a", "apoio_polo_b", "apoio_fora"], format_func=nomes.get)
fig = go.Figure()
for i, k in enumerate(esc):
    fig.add_scatter(x=s["mes"], y=s[k], name=nomes[k], mode="lines+markers", line=dict(color=SERIES[i], width=2))
    for _, g in seg.iterrows():
        fig.add_shape(type="line", x0=g["inicio"], x1=g["fim"], y0=g[k], y1=g[k], line=dict(color=SERIES[i], width=6), opacity=.25)
for _, p in pts.iterrows():
    fig.add_vline(x=p["mes"], line_dash="solid" if p["robusto"] else "dash", line_color="#147a54" if p["robusto"] else "#b4541c")
fig.update_layout(yaxis_tickformat=".0%", height=440, legend=dict(orientation="h"), margin=dict(t=20))
marcar_periodos(fig)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Pontos de mudança")
if pts.empty:
    st.write("Nenhum com a penalidade atual.")
for _, p in pts.iterrows():
    deltas = ", ".join(f"{nomes[k].lower()} {100 * p[f'delta_{k}']:+.1f} p.p.".replace(".", ",") for k in p["principais"])
    ev = f" — perto de: {p['evento']}" if pd.notna(p["evento"]) else ""
    st.markdown(f"- **{p['mes']:%m/%Y}** ({'robusto' if p['robusto'] else 'sinal moderado'}): {deltas}{ev}")

st.subheader("Trechos")
t = seg.copy()
t["período"] = t["inicio"].dt.strftime("%m/%Y") + " a " + t["fim"].dt.strftime("%m/%Y")
st.dataframe(t[["período", "meses", "votacoes", *nomes]].rename(columns={"votacoes": "votações", **nomes}),
             hide_index=True, column_config={v: st.column_config.NumberColumn(format="percent") for v in nomes.values()})

st.subheader("Deputados que trocaram de grupo entre janelas seguidas")
j = jan.dropna(subset=["trocaram"])
fig2 = go.Figure(go.Bar(x=pd.to_datetime(j["fim"]), y=j["trocaram"], marker_color=SERIES[0],
                        customdata=j[["janela", "ari_anterior"]], hovertemplate="%{customdata[0]}<br>%{y:.1%} trocaram<br>ARI %{customdata[1]:.2f}<extra></extra>"))
fig2.update_layout(yaxis_tickformat=".0%", height=300, margin=dict(t=10))
st.plotly_chart(fig2, use_container_width=True)
st.caption(f"Mediana: {100 * (r['trocaram_mediana'] or 0):.1f}% trocam de grupo; estabilidade (ARI) mediana {r['ari_mediana']:.2f}.".replace(".", ","))
rodape()
