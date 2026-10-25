import plotly.graph_objects as go
import streamlit as st

from dados import SERIES, comparacao, dec, n, nome_leg, pct, rodape

st.set_page_config(page_title="Comparação · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Comparação entre legislaturas")

leg = comparacao("legislaturas.parquet")
if leg is None or len(leg) < 2:
    st.info("A comparação aparece quando houver duas legislaturas processadas.")
    rodape()
    st.stop()

st.markdown("Os mesmos parâmetros nas duas legislaturas. Comunidades e polos são calculados **separadamente** em cada uma, "
            "então C1 de uma não é o mesmo grupo que C1 da outra.")
L = list(leg["legislatura"])
cols = st.columns(len(L))
for c, (_, r) in zip(cols, leg.iterrows()):
    c.markdown(f"#### {nome_leg(r['legislatura'])}")
    c.metric("Votações vencidas pelo governo", pct(r["vitorias_gov"], r["votacoes_gov"]))
    c.metric("Comunidades", r["comunidades"])
    c.metric("Concordância entre os polos", f"{dec(100 * r['conc_polos_min'])}% a {dec(100 * r['conc_polos_max'])}%")
    c.metric("Coesão média dos partidos", f"{dec(100 * r['rice_ponderado'])}%")
    c.metric("Participação média", f"{dec(100 * r['participacao_media'])}%")
    c.caption(f"Polo A: {r['polo_a']}  \nPolo B: {r['polo_b']}")

st.subheader("Partidos: apoio ao governo de cada legislatura")
part = comparacao("partidos.parquet")
pv = part[part["deputados"] >= 5].pivot(index="partido", columns="legislatura", values="apoio_gov").dropna()
pv = pv.sort_values(L[-1])
fig = go.Figure()
for i, l in enumerate(L):
    fig.add_trace(go.Scatter(x=100 * pv[l], y=pv.index, mode="markers", name=nome_leg(l),
                             marker=dict(size=11, color=SERIES[i], line=dict(color="#fcfcfb", width=1.5)),
                             hovertemplate="%{y}: %{x:.1f}%<extra>" + nome_leg(l) + "</extra>"))
for p in pv.index:
    fig.add_shape(type="line", x0=100 * pv.loc[p, L[0]], x1=100 * pv.loc[p, L[-1]], y0=p, y1=p,
                  line=dict(color="#e4e3df", width=2), layer="below")
fig.update_layout(height=26 * len(pv) + 90, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb",
                  paper_bgcolor="#fcfcfb", legend=dict(orientation="h", y=-0.08, x=0))
fig.update_xaxes(range=[0, 100], ticksuffix="%", gridcolor="#e4e3df", title="% dos votos iguais à orientação do Governo")
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
st.caption("Cada legislatura teve um governo diferente: apoio alto nas duas indica quem acompanha o governo da vez.")

st.subheader("Deputados reeleitos")
re = comparacao("reeleitos.parquet")
q = comparacao("quadrantes.json")
l0, l1 = q["legislaturas"]
st.markdown(f"{n(q['total'])} deputados com 100+ votos medidos nas duas. Governista = apoio de "
            f"{dec(100 * q['limiar'], 0)}% ou mais.")
c1, c2 = st.columns(2)
for c, k in zip([c1, c2, c1, c2], [k for k in q if k not in ("total", "limiar", "legislaturas")]):
    c.metric(k.capitalize(), pct(q[k], q["total"]))
fig2 = go.Figure(go.Scatter(
    x=100 * re[f"apoio_{l0}"], y=100 * re[f"apoio_{l1}"], mode="markers",
    marker=dict(size=8, color=SERIES[0], opacity=0.75, line=dict(color="#fcfcfb", width=1)),
    customdata=re[["nome", f"partido_{l0}", f"partido_{l1}"]].to_numpy(),
    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} → %{customdata[2]}<br>"
                  f"{l0}: " + "%{x:.0f}%<br>" + f"{l1}: " + "%{y:.0f}%<extra></extra>"))
for v in (100 * q["limiar"],):
    fig2.add_hline(y=v, line=dict(color="#b7b5ae", dash="dot"))
    fig2.add_vline(x=v, line=dict(color="#b7b5ae", dash="dot"))
fig2.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb")
fig2.update_xaxes(range=[0, 100], ticksuffix="%", title=f"Apoio ao governo na {nome_leg(l0)}", gridcolor="#e4e3df")
fig2.update_yaxes(range=[0, 100], ticksuffix="%", title=f"Apoio ao governo na {nome_leg(l1)}", gridcolor="#e4e3df")
st.plotly_chart(fig2, use_container_width=True, config={"displaylogo": False})

busca = st.text_input("Procurar deputado reeleito")
t = re if not busca else re[re["nome"].str.contains(busca, case=False, na=False)]
st.dataframe(t.assign(**{
    "Deputado": t["nome"], "Partido": t[f"partido_{l0}"] + " → " + t[f"partido_{l1}"],
    f"Apoio {l0}": (100 * t[f"apoio_{l0}"]).round(1), f"Apoio {l1}": (100 * t[f"apoio_{l1}"]).round(1),
})[["Deputado", "Partido", f"Apoio {l0}", f"Apoio {l1}"]].sort_values(f"Apoio {l1}", ascending=False),
    hide_index=True, use_container_width=True)
rodape()
