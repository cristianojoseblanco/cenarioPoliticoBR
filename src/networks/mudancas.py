"""Pontos de mudança e comunidades ao longo do tempo (por legislatura).

1. Séries mensais (meses com pelo menos `mudancas.min_votacoes_mes` votações nominais):
   - apoio ao governo do polo A, do polo B e de quem está fora dos polos (média, por votação, da fração
     de votos Sim/Não do grupo iguais à orientação do Governo);
   - fração de votações polarizadas; fração de vitórias do governo.
2. Pontos de mudança: PELT (biblioteca ruptures, custo L2) sobre as séries padronizadas, em conjunto.
   Penalidade = fator × nº de séries × ln(nº de meses). Um ponto é
   "robusto" quando aparece também com o fator × cada valor de `variantes` (tolerância `tolerancia_meses`). Cada ponto recebe o evento de
   contexto mais próximo (governo, presidência da Câmara, eleições, marcadores) até `janela_contexto_dias`.
   Também roda série a série (fator × 1) para dizer QUAL série mudou.
3. Comunidades ao longo do tempo: em cada janela móvel da Etapa 4 os deputados já têm comunidade
   (mapeada para a comunidade global). Aqui: estabilidade entre janelas seguidas (ARI), fração de
   deputados que trocaram de grupo e fluxos entre grupos.

Saídas em data/marts/camara/leg<N>/mudancas/.
Uso: python -m src.networks.mudancas
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

from src.config import ROOT, load_config
from src.networks.votacao import carregar_votos, dec, n

ROTULOS = {
    "apoio_polo_a": "apoio ao governo — polo A",
    "apoio_polo_b": "apoio ao governo — polo B",
    "apoio_fora": "apoio ao governo — fora dos polos",
    "polarizacao": "votações polarizadas",
    "vitoria_gov": "vitórias do governo",
}


def series_mensais(c: dict) -> tuple[pd.DataFrame, dict]:
    m = c.get("mudancas", {})
    mapa = c["redes"]["codificacoes"][c["redes"]["principal"]["codificacao"]]
    votos = carregar_votos(c)
    votos["valor"] = votos["voto"].map(mapa)
    votos = votos[votos["valor"].isin([1, -1])]
    com = pd.read_parquet(ROOT / c["redes"]["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]
    polos = json.loads((ROOT / c["fatias"]["saida"] / "polos.json").read_text(encoding="utf-8"))
    pa, pb = polos["polo_a"], polos["polo_b"]
    gv = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "votacoes.parquet")[
        ["votacao_id", "data", "gov_valor", "governo_venceu"]]
    dv = pd.read_parquet(ROOT / c["governabilidade"]["saida"].replace("/governabilidade", "/dinamica") / "votacoes.parquet")[
        ["votacao_id", "polarizada"]]

    v = votos.merge(gv[["votacao_id", "gov_valor"]], on="votacao_id").dropna(subset=["gov_valor"])
    com_ = v["deputado_id"].map(princ)
    v["grupo"] = np.where(com_ == pa, "apoio_polo_a", np.where(com_ == pb, "apoio_polo_b",
                          np.where(com_.notna(), "apoio_fora", None)))
    v = v.dropna(subset=["grupo"])
    v["ok"] = (v["valor"] == v["gov_valor"]).astype(float)
    por_vot = v.groupby(["votacao_id", "grupo"])["ok"].mean().unstack()

    base = gv.merge(dv, on="votacao_id", how="left").set_index("votacao_id").join(por_vot)
    base["mes"] = pd.to_datetime(base["data"]).dt.to_period("M").dt.to_timestamp()
    s = base.groupby("mes").agg(
        votacoes=("data", "size"),
        apoio_polo_a=("apoio_polo_a", "mean"), apoio_polo_b=("apoio_polo_b", "mean"), apoio_fora=("apoio_fora", "mean"),
        polarizacao=("polarizada", "mean"), vitoria_gov=("governo_venceu", "mean"),
    )
    s = s[s["votacoes"] >= int(m.get("min_votacoes_mes", 5))].dropna()
    return s.reset_index(), polos


def pelt(X: np.ndarray, fator: float, min_size: int) -> list[int]:
    import ruptures as rpt
    if len(X) < 2 * min_size:
        return []
    pen = fator * X.shape[1] * np.log(len(X))
    return [b for b in rpt.Pelt(model="l2", min_size=min_size, jump=1).fit(X).predict(pen=pen) if b < len(X)]


def eventos_contexto(cfg: dict) -> list[tuple[pd.Timestamp, str]]:
    ctx = cfg.get("contexto", {})
    ev = [(pd.Timestamp(g["inicio"]), f"início do {g['nome']}") for g in ctx.get("governos", [])]
    ev += [(pd.Timestamp(p["inicio"]), f"{p['nome']} assume a presidência da Câmara") for p in ctx.get("presidentes_camara", [])]
    ev += [(pd.Timestamp(e["data"]), e["rotulo"]) for e in ctx.get("eventos", [])]
    for mk in cfg.get("marcadores_periodo", []):
        ev += [(pd.Timestamp(mk["inicio"]), f"início: {mk['rotulo']}"), (pd.Timestamp(mk["fim"]), f"fim: {mk['rotulo']}")]
    return ev


def rodar(c: dict) -> int:
    m = c.get("mudancas", {})
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/mudancas")
    saida.mkdir(parents=True, exist_ok=True)
    s, polos = series_mensais(c)
    cols = list(m.get("series", list(ROTULOS)))
    Z = s[cols].to_numpy(float)
    Z = (Z - Z.mean(0)) / np.where(Z.std(0) > 0, Z.std(0), 1)
    fator, min_size, tol = float(m.get("penalidade_fator", 2.0)), int(m.get("min_meses", 3)), int(m.get("tolerancia_meses", 1))

    mult = [float(x) for x in m.get("variantes", [0.5, 1.5])]
    variantes = {f: pelt(Z, fator * f, min_size) for f in (1.0, *mult)}
    pontos = variantes[1.0]
    eventos = eventos_contexto(c)
    jan_ctx = pd.Timedelta(days=int(m.get("janela_contexto_dias", 90)))
    limites = [0, *pontos, len(s)]
    seg = []
    for i in range(len(limites) - 1):
        bloco = s.iloc[limites[i]:limites[i + 1]]
        seg.append({"segmento": i + 1, "inicio": bloco["mes"].iat[0], "fim": bloco["mes"].iat[-1],
                    "meses": len(bloco), "votacoes": int(bloco["votacoes"].sum()),
                    **{k: float(np.average(bloco[k], weights=bloco["votacoes"])) for k in cols}})
    seg = pd.DataFrame(seg)

    linhas = []
    for j, p in enumerate(pontos):
        data = s["mes"].iat[p]
        rob = all(any(abs(q - p) <= tol for q in variantes[f]) for f in mult)
        antes, depois = seg.iloc[j], seg.iloc[j + 1]
        delta = {k: float(depois[k] - antes[k]) for k in cols}
        principais = sorted(delta, key=lambda k: -abs(delta[k] / (s[k].std() or 1)))[:2]
        prox = [(abs((t - data).days), t, r) for t, r in eventos if abs(t - data) <= jan_ctx]
        prox = min(prox) if prox else None
        linhas.append({"mes": data, "robusto": rob, "principais": principais,
                       **{f"delta_{k}": v for k, v in delta.items()},
                       "evento": prox[2] if prox else None, "evento_data": prox[1] if prox else None})
    pts = pd.DataFrame(linhas)

    # série a série
    ps = []
    for k in cols:
        z = Z[:, [cols.index(k)]]
        for p in pelt(z, fator, min_size):
            ps.append({"serie": k, "mes": s["mes"].iat[p],
                       "antes": float(s[k].iloc[max(0, p - min_size):p].mean()),
                       "depois": float(s[k].iloc[p:p + min_size].mean())})
    ps = pd.DataFrame(ps, columns=["serie", "mes", "antes", "depois"])

    # comunidades ao longo das janelas
    pos = pd.read_parquet(ROOT / c["fatias"]["saida"] / "posicoes.parquet")
    meta = pd.read_parquet(ROOT / c["fatias"]["saida"] / "fatias.parquet")
    pj = pos[(pos["tipo"] == "janela")].dropna(subset=["comunidade_fatia_mapeada"])
    ordem = meta[meta["tipo"] == "janela"].sort_values("ordem")["fatia"].tolist()
    jan, fluxos = [], []
    anterior = None
    for f in ordem:
        atual = pj[pj["fatia"] == f].set_index("deputado_id")["comunidade_fatia_mapeada"]
        mt = meta.set_index("fatia").loc[f]
        lin = {"janela": f, "fim": f.split(" a ")[-1], "comunidades": int(mt["comunidades"]),
               "modularidade": float(mt["modularidade"]), "conc_entre_polos": float(mt["conc_entre_polos"]),
               "ari_anterior": None, "trocaram": None}
        if anterior is not None:
            comuns = atual.index.intersection(anterior.index)
            if len(comuns) > 10:
                a0, a1 = anterior.loc[comuns], atual.loc[comuns]
                lin["ari_anterior"] = float(adjusted_rand_score(a0, a1))
                lin["trocaram"] = float((a0 != a1).mean())
                fl = pd.DataFrame({"de": a0.values, "para": a1.values}).value_counts().rename("deputados").reset_index()
                fluxos.append(fl[fl["deputados"] > 0].assign(janela=f))
        anterior = atual
        jan.append(lin)
    jan = pd.DataFrame(jan)
    fluxos = pd.concat(fluxos, ignore_index=True) if fluxos else pd.DataFrame(columns=["de", "para", "deputados", "janela"])

    s.to_parquet(saida / "series.parquet", index=False)
    seg.to_parquet(saida / "segmentos.parquet", index=False)
    pts.to_parquet(saida / "pontos.parquet", index=False)
    ps.to_parquet(saida / "pontos_series.parquet", index=False)
    jan.to_parquet(saida / "janelas.parquet", index=False)
    fluxos.to_parquet(saida / "fluxos.parquet", index=False)
    resumo = {"polo_a": polos["polo_a"], "polo_b": polos["polo_b"], "composicao": polos.get("composicao", {}),
              "meses": int(len(s)), "pontos": int(len(pts)), "robustos": int(pts["robusto"].sum()) if len(pts) else 0,
              "penalidade_fator": fator, "min_meses": min_size,
              "ari_mediana": float(jan["ari_anterior"].median()) if jan["ari_anterior"].notna().any() else None,
              "trocaram_mediana": float(jan["trocaram"].median()) if jan["trocaram"].notna().any() else None}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    comp = polos.get("composicao", {})
    L = ["# Pontos de mudança e comunidades ao longo do tempo", "",
         f"Polo A = {polos['polo_a']} ({comp.get(polos['polo_a'], '')}); polo B = {polos['polo_b']} ({comp.get(polos['polo_b'], '')}).",
         f"{n(len(s))} meses com pelo menos {m.get('min_votacoes_mes', 5)} votações. PELT (L2), penalidade "
         f"{dec(fator, 1)} × séries × ln(meses), segmentos de pelo menos {min_size} meses.", "",
         "## Segmentos", "",
         "| Período | Meses | Votações | " + " | ".join(ROTULOS[k] for k in cols) + " |",
         "| --- | --- | --- | " + " | ".join("---" for _ in cols) + " |"]
    for _, r in seg.iterrows():
        L.append(f"| {r['inicio']:%Y-%m} a {r['fim']:%Y-%m} | {r['meses']} | {n(r['votacoes'])} | "
                 + " | ".join(f"{dec(100 * r[k], 1)}%" for k in cols) + " |")
    L += ["", "## Pontos de mudança", ""]
    for _, r in pts.iterrows():
        mud = "; ".join(f"{ROTULOS[k]} {'+' if r[f'delta_{k}'] >= 0 else '−'}{dec(abs(100 * r[f'delta_{k}']), 1)} p.p."
                        for k in r["principais"])
        ev = f" — perto de: {r['evento']} ({r['evento_data']:%Y-%m-%d})" if pd.notna(r["evento"]) else ""
        L.append(f"- {r['mes']:%Y-%m}{' (robusto)' if r['robusto'] else ''}: {mud}{ev}")
    if pts.empty:
        L.append("- Nenhum ponto de mudança com esta penalidade.")
    L += ["", "## Comunidades entre janelas seguidas", "",
          f"- Estabilidade mediana (ARI entre janelas seguidas): {dec(resumo['ari_mediana'] or 0, 2)}",
          f"- Fração mediana de deputados que trocaram de grupo: {dec(100 * (resumo['trocaram_mediana'] or 0), 1)}%", ""]
    menos = jan.dropna(subset=["ari_anterior"]).nsmallest(3, "ari_anterior")
    if len(menos):
        L.append("Janelas com maior reorganização:")
        L.append("")
        for _, r in menos.iterrows():
            L.append(f"- {r['janela']}: ARI {dec(r['ari_anterior'], 2)}, {dec(100 * r['trocaram'], 1)}% trocaram de grupo")
    L.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "mudancas")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


def main() -> int:
    from src.config import legislatura_tem_dados, por_legislatura

    cfg = load_config()
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            continue
        print(f"===== legislatura {leg} =====")
        rodar(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
