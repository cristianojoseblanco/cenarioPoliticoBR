import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import cor_com, dec, json_, n, ordem_com, parquet, rodape, rotulo

st.set_page_config(page_title="Temas · Cenário Político BR", page_icon="🏛️", layout="wide")
st.title("Por tema")
st.markdown("Temas oficiais da Câmara com pelo menos 75 votações. Uma votação pode ter mais de um tema.")

polos = json_("fatias/polos.json")
res = parquet("fatias/resumo.parquet")
meta = parquet("fatias/fatias.parquet")
tem = res[res["tipo"] == "tema"]
gov = parquet("governabilidade/temas.parquet")

coms = ordem_com(tem["comunidade_global"])
temas = list(meta[meta["tipo"] == "tema"].sort_values("votacoes", ascending=False)["fatia"])


def quebra(t, w=22):
    """Quebra nomes longos de tema em linhas, para caber no celular."""
    linhas, atual = [], ""
    for p in t.split():
        if atual and len(atual) + len(p) + 1 > w:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    return "<br>".join(linhas + [atual])
metrica = st.radio("Mostrar", ["Posição entre os polos", "Apoio ao governo"], horizontal=True)
escolha = st.multiselect("Comunidades", coms, default=coms, format_func=rotulo)

fig = go.Figure()
for c in escolha:
    if metrica == "Posição entre os polos":
        s = tem[tem["comunidade_global"] == c].set_index("fatia").reindex(temas)["posicao_media"]
        txt = [dec(v, 2) for v in s]
    else:
        s = gov[gov["comunidade"] == c].set_index("tema").reindex(temas)["apoio"] * 100
        txt = [f"{dec(v)}%" for v in s]
    fig.add_trace(go.Scatter(x=s.values, y=temas, mode="markers", name=rotulo(c), text=txt,
                             marker=dict(color=cor_com(c), size=11, line=dict(color="#fcfcfb", width=1.5)),
                             hovertemplate="%{y}: %{text}<extra>" + c + "</extra>"))
if metrica == "Posição entre os polos":
    fig.add_vline(x=0, line=dict(color="#52514e", width=1))
    fig.update_xaxes(range=[-1, 1], title=f"← A ({polos['polo_a']}) · B ({polos['polo_b']}) →")
else:
    fig.update_xaxes(range=[0, 100], title="% dos votos iguais à orientação do Governo")
fig.update_yaxes(autorange="reversed", tickvals=temas, ticktext=[quebra(t) for t in temas])
fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb",
                  legend=dict(orientation="h", y=-0.2, x=0))
fig.update_xaxes(gridcolor="#e4e3df")
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

st.subheader("Tabela")
m = meta[meta["tipo"] == "tema"].set_index("fatia")
vit = gov[gov["comunidade"] == "vitoria_governo"].set_index("tema")["apoio"]
linhas = []
for t in temas:
    linhas.append({
        "Tema": t, "Votações": n(m.loc[t, "votacoes"]),
        "Concordância entre os polos": f"{dec(100 * m.loc[t, 'conc_entre_polos'])}%",
        "Vitória do governo": f"{dec(100 * vit.get(t, float('nan')))}%",
        **{c: dec(tem[(tem['fatia'] == t) & (tem['comunidade_global'] == c)]['posicao_media'].iloc[0], 2)
           for c in coms if not tem[(tem['fatia'] == t) & (tem['comunidade_global'] == c)].empty},
    })
st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
st.caption("Colunas C1…C6: posição média da comunidade no eixo entre os polos (−1 a +1).")
rodape()
