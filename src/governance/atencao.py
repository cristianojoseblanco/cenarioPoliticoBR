"""Influência e atenção (Bloco C), Câmara, por legislatura.

Por deputado, dentro do período da legislatura:
  - encontros: compromissos de autoridades do Executivo federal (e-Agendas) que citam o deputado;
  - visitas: média mensal de visitas ao verbete na Wikipédia em português;
  - discursos e palavras: discursos registrados pela Câmara e tamanho total das transcrições.
Comparados (Spearman, em todos e dentro do partido, p < `tse.alfa`) com apoio ao governo, disciplina,
posição na 1ª dimensão de voto (extremidade = |d1|) e emendas pagas.
Também: encontros por órgão do Executivo e por ano; série mensal de visitas.

Saídas em data/marts/camara/leg<N>/atencao/. Uso: python -m src.governance.atencao
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import ROOT, legislatura_tem_dados, load_config, por_legislatura
from src.networks.votacao import n, nomes_deputados


def _f(x, d=4):
    return None if x is None or pd.isna(x) or not np.isfinite(x) else round(float(x), d)


def _corr(df, a, b, alfa):
    x = df[[a, b, "partido"]].dropna()
    if len(x) < 30:
        return None
    s, p = spearmanr(x[a], x[b])
    xd = x.copy()
    for v in (a, b):
        xd[v] = xd[v] - xd.groupby("partido")[v].transform("median")
    sd, pd_ = spearmanr(xd[a], xd[b])
    return {"atencao": a, "comportamento": b, "spearman": _f(s, 3), "p": _f(p, 6), "n": len(x),
            "spearman_dentro": _f(sd, 3), "p_dentro": _f(pd_, 6),
            "relevante": bool(p < alfa), "relevante_dentro": bool(pd_ < alfa)}


def rodar(c: dict, cfg: dict) -> int:
    leg = c["legislatura_atual"]
    if not legislatura_tem_dados(c):
        return 0
    st = ROOT / cfg["atencao"]["caminhos"]["staging"]
    sa = ROOT / cfg["agendas"]["caminhos"]["staging"]
    ini, fim = pd.Timestamp(c["redes"]["periodo"]["inicio"]), pd.Timestamp(c["redes"]["periodo"]["fim"])
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/atencao")
    saida.mkdir(parents=True, exist_ok=True)
    g = pd.read_parquet(ROOT / c["redes"]["saida"].replace("/redes", "/governabilidade") / "deputados.parquet")
    g = g[g["votos_gov"] >= 30][["deputado_id", "nome", "partido", "apoio_gov", "disciplina", "em_exercicio"]]
    base = g.copy()
    resumo = {"legislatura": leg}
    dp = ROOT / c["redes"]["saida"].replace("/redes", "/dimensoes") / "deputados.parquet"
    if dp.exists():
        base = base.merge(pd.read_parquet(dp)[["deputado_id", "d1"]], on="deputado_id", how="left")
        base["extremidade"] = base["d1"].abs()
    ep = ROOT / c["redes"]["saida"].replace("/redes", "/emendas") / "parlamentares.parquet"
    if ep.exists():
        base = base.merge(pd.read_parquet(ep)[["deputado_id", "pago"]], on="deputado_id", how="left")
    meses_leg = max(1, (min(fim, pd.Timestamp.now()) - ini).days / 30.44)

    ag = sa / "compromissos.parquet"
    a = pd.read_parquet(ag) if ag.exists() else pd.DataFrame(columns=["casa", "data"])
    a = a[(a["casa"] == "camara") & (a["data"] >= ini) & (a["data"] <= fim)]
    if len(a) and a["data"].min() > ini + pd.Timedelta(days=365):
        a = a.iloc[0:0]  # o e-Agendas começa em out/2022: cobertura parcial demais nesta legislatura
    if len(a):
        a = a.drop_duplicates(["parlamentar_id", "data", "autoridade", "assunto"])
        cnt = a.groupby("parlamentar_id").size().rename("encontros")
        base = base.merge(cnt, left_on="deputado_id", right_index=True, how="left")
        base["encontros"] = base["encontros"].fillna(0)
        org = a.groupby("orgao").agg(encontros=("parlamentar_id", "size"), deputados=("parlamentar_id", "nunique"))
        resumo["agendas"] = {
            "encontros": int(len(a)), "deputados": int(a["parlamentar_id"].nunique()),
            "por_ano": [{"ano": int(k), "n": int(v)} for k, v in a.groupby(a["data"].dt.year).size().items()],
            "orgaos": [{"orgao": k, "encontros": int(r.encontros), "deputados": int(r.deputados)}
                       for k, r in org.nlargest(12, "encontros").iterrows()],
            "por_partido": [{"partido": k, "media": _f(v, 2)} for k, v in
                            base.groupby("partido")["encontros"].mean().sort_values(ascending=False).items()
                            if (base["partido"] == k).sum() >= 8]}

    wv = st / "wikipedia_visitas.parquet"
    if wv.exists():
        w = pd.read_parquet(wv)
        w = w[w["casa"] == "camara"]
        w["data"] = pd.to_datetime(w["mes"], format="%Y%m")
        w = w[(w["data"] >= ini) & (w["data"] <= fim)]
        vis = w.groupby("parlamentar_id")["visitas"].sum() / meses_leg
        base = base.merge(vis.rename("visitas_mes"), left_on="deputado_id", right_index=True, how="left")
        serie = w.groupby("data")["visitas"].sum()
        pico = w.loc[w.groupby("parlamentar_id")["visitas"].idxmax()] if len(w) else w
        resumo["wikipedia"] = {
            "com_verbete": int(base["visitas_mes"].notna().sum()), "deputados": int(len(base)),
            "serie": [{"mes": k.strftime("%Y-%m"), "v": int(v)} for k, v in serie.items()],
            "picos": [{"deputado_id": r.parlamentar_id, "mes": r.data.strftime("%Y-%m"), "v": int(r.visitas)}
                      for r in pico.nlargest(10, "visitas").itertuples()]}

    di = st / "discursos.parquet"
    if di.exists():
        d = pd.read_parquet(di)
        d["data"] = pd.to_datetime(d["data"], errors="coerce")
        d = d[(d["data"] >= ini) & (d["data"] <= fim)]
        dd = d.groupby("deputado_id").agg(discursos=("data", "size"), palavras=("palavras", "sum"))
        base = base.merge(dd, left_on="deputado_id", right_index=True, how="left")
        base[["discursos", "palavras"]] = base[["discursos", "palavras"]].fillna(0)
        base["discursos_mes"] = base["discursos"] / meses_leg
        resumo["discursos"] = {"discursos": int(len(d)), "palavras": int(d["palavras"].sum()),
                               "por_tipo": [{"tipo": k, "n": int(v)} for k, v in d["tipo"].value_counts().head(8).items()],
                               "mediana_deputado": _f(base["discursos"].median(), 0)}

    alfa = cfg["tse"]["alfa"]
    att = [x for x in ("encontros", "visitas_mes", "discursos", "palavras") if x in base.columns]
    comp = [x for x in ("apoio_gov", "disciplina", "extremidade", "pago") if x in base.columns]
    cor = [r for a_ in att for b_ in comp if (r := _corr(base, a_, b_, alfa))]
    cor += [r for i, a_ in enumerate(att) for b_ in att[i + 1:]
            if {a_, b_} != {"discursos", "palavras"} and (r := _corr(base, a_, b_, alfa))]
    resumo["correlacoes"] = cor
    base.to_parquet(saida / "deputados.parquet", index=False)
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    relatorio(c, resumo, base)
    return 0


def relatorio(c, r, base):
    leg = r["legislatura"]
    L = [f"# Influência e atenção — legislatura {leg}", ""]
    if "agendas" in r:
        a = r["agendas"]
        L += ["## Encontros com o Executivo (e-Agendas)", "",
              f"- {n(a['encontros'])} compromissos de autoridades do Executivo citam {n(a['deputados'])} deputados.", "",
              "| Órgão | Encontros | Deputados |", "| --- | --- | --- |"]
        L += [f"| {x['orgao']} | {n(x['encontros'])} | {n(x['deputados'])} |" for x in a["orgaos"]]
        L += ["", "| Deputado | Partido | Encontros |", "| --- | --- | --- |"]
        L += [f"| {x.nome} | {x.partido} | {int(x.encontros)} |" for x in base.nlargest(15, "encontros").itertuples()]
        L += ["", "Média de encontros por deputado, por partido (8+ deputados):", ""]
        L += [f"- {x['partido']}: {x['media']:.1f}".replace(".", ",") for x in a["por_partido"]]
    if "wikipedia" in r:
        w = r["wikipedia"]
        L += ["", "## Wikipédia", "", f"- {n(w['com_verbete'])} de {n(w['deputados'])} deputados com verbete identificado.", "",
              "| Deputado | Partido | Visitas por mês |", "| --- | --- | --- |"]
        L += [f"| {x.nome} | {x.partido} | {n(round(x.visitas_mes))} |" for x in base.nlargest(15, "visitas_mes").itertuples()]
    if "discursos" in r:
        d = r["discursos"]
        L += ["", "## Discursos", "", f"- {n(d['discursos'])} discursos; mediana de {n(d['mediana_deputado'])} por deputado.", "",
              "| Deputado | Partido | Discursos | Palavras |", "| --- | --- | --- | --- |"]
        L += [f"| {x.nome} | {x.partido} | {int(x.discursos)} | {n(int(x.palavras))} |" for x in base.nlargest(15, "discursos").itertuples()]
    L += ["", "## Correlações (Spearman; dentro = descontada a mediana do partido)", "",
          "| Atenção | Com | Todos | Dentro do partido | n |", "| --- | --- | --- | --- | --- |"]
    for x in r["correlacoes"]:
        L.append((f"| {x['atencao']} | {x['comportamento']} | {x['spearman']:.2f}{'*' if x['relevante'] else ''} | "
                  f"{x['spearman_dentro']:.2f}{'*' if x['relevante_dentro'] else ''} | {x['n']} |").replace(".", ","))
    L += ["", "\\* p < 0,01."]
    dest = ROOT / c["governabilidade"]["relatorio"].replace("governabilidade.md", "atencao.md")
    dest.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"relatório: {dest.relative_to(ROOT)}")


def main() -> int:
    cfg = load_config()
    for leg, c in por_legislatura(cfg):
        print(f"===== legislatura {leg} =====")
        rodar(c, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
