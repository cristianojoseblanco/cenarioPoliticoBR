"""Etapa 7a — comparação entre legislaturas.

Lê os resultados já calculados de cada legislatura (data/marts/camara/leg<N>/) e monta:
  legislaturas.parquet   estrutura e governabilidade lado a lado
  partidos.parquet       apoio ao governo e coesão por partido em cada legislatura
  reeleitos.parquet      deputados presentes nas duas: apoio ao governo em cada uma
Relatório: artifacts/reports/comparacao.md

Uso: python -m src.networks.comparacao
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, legislatura_tem_dados, load_config, por_legislatura
from src.networks.votacao import dec, n, pct

SAIDA = "data/marts/camara/comparacao"
RELATORIO = "artifacts/reports/comparacao.md"
MIN_VOTOS = 100  # votos com orientação do governo para entrar na comparação de reeleitos


def _ler(c, sec, arq):
    p = ROOT / c[sec]["saida"] / arq
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return pd.read_parquet(p)


def main() -> int:
    cfg = load_config()
    legs = [(leg, c) for leg, c in por_legislatura(cfg) if legislatura_tem_dados(c)]
    if len(legs) < 2:
        print("Menos de duas legislaturas com dados; nada a comparar.")
        return 0
    saida = ROOT / SAIDA
    saida.mkdir(parents=True, exist_ok=True)

    linhas, partidos, deps = [], [], {}
    for leg, c in legs:
        m = _ler(c, "redes", "metricas.json")
        polos = _ler(c, "fatias", "polos.json")
        fat = _ler(c, "fatias", "fatias.parquet")
        g = _ler(c, "governabilidade", "resumo.json")
        part = _ler(c, "governabilidade", "partidos.parquet")
        dep = _ler(c, "governabilidade", "deputados.parquet")
        rede = _ler(c, "redes", "deputados_rede.parquet")
        jan = fat[fat["tipo"] == "janela"]
        rice_pond = np.average(part["rice"].fillna(0), weights=part["votacoes_rice"].fillna(0)) \
            if part["votacoes_rice"].fillna(0).sum() else np.nan
        linhas.append({
            "legislatura": leg, "inicio": c["redes"]["periodo"]["inicio"], "fim": c["redes"]["periodo"]["fim"],
            "votacoes_nominais": m["votacoes"]["votacoes_total"], "votacoes_analisadas": m["votacoes"]["incluidas"],
            "deputados_grafo": m["deputados_no_grafo"], "comunidades": len(m["comunidades"]),
            "modularidade": m["modularidade"], "nmi_partido": m["nmi_com_partido"],
            "polo_a": f"{polos['polo_a']} ({polos['composicao'][polos['polo_a']]})",
            "polo_b": f"{polos['polo_b']} ({polos['composicao'][polos['polo_b']]})",
            "conc_polos_min": jan["conc_entre_polos"].min(), "conc_polos_max": jan["conc_entre_polos"].max(),
            "conc_polos_media": jan["conc_entre_polos"].mean(),
            "votacoes_gov": g["votacoes_gov"], "vitorias_gov": g["vitorias_gov"],
            "participacao_media": dep["participacao"].mean(), "rice_ponderado": rice_pond,
        })
        partidos.append(part.assign(legislatura=leg))
        d = dep[dep["votos_gov"] >= MIN_VOTOS].set_index("deputado_id")
        d = d.join(rede.set_index("deputado_id")[["comunidade"]], rsuffix="_rede")
        deps[leg] = d

    leg_df = pd.DataFrame(linhas)
    leg_df.to_parquet(saida / "legislaturas.parquet", index=False)
    part_df = pd.concat(partidos, ignore_index=True)
    part_df.to_parquet(saida / "partidos.parquet", index=False)

    (l0, _), (l1, _) = legs[-2], legs[-1]
    a, b = deps[l0], deps[l1]
    comuns = a.index.intersection(b.index)
    re = pd.DataFrame({
        "deputado_id": comuns, "nome": b.loc[comuns, "nome"].values,
        f"partido_{l0}": a.loc[comuns, "partido"].values, f"partido_{l1}": b.loc[comuns, "partido"].values,
        f"comunidade_{l0}": a.loc[comuns, "comunidade"].values, f"comunidade_{l1}": b.loc[comuns, "comunidade"].values,
        f"apoio_{l0}": a.loc[comuns, "apoio_gov"].values, f"apoio_{l1}": b.loc[comuns, "apoio_gov"].values,
    })
    re["diferenca"] = re[f"apoio_{l1}"] - re[f"apoio_{l0}"]
    re.to_parquet(saida / "reeleitos.parquet", index=False)

    # ---------------- relatório
    L = ["# Comparação entre legislaturas — Plenário", "",
         "Mesmos parâmetros nas duas. Polos e comunidades são calculados separadamente em cada legislatura.", "",
         "| Indicador | " + " | ".join(f"Legislatura {r['legislatura']}" for r in linhas) + " |",
         "| --- | " + " | ".join("---" for _ in linhas) + " |"]
    def lin(rot, f):
        L.append(f"| {rot} | " + " | ".join(f(r) for r in linhas) + " |")
    lin("Período", lambda r: f"{r['inicio'][:4]}–{int(r['fim'][:4]) - 1}")
    lin("Votações nominais (analisadas)", lambda r: f"{n(r['votacoes_nominais'])} ({n(r['votacoes_analisadas'])})")
    lin("Deputados no grafo", lambda r: n(r["deputados_grafo"]))
    lin("Comunidades", lambda r: str(r["comunidades"]))
    lin("Modularidade", lambda r: dec(r["modularidade"]))
    lin("Correspondência comunidade × partido (NMI)", lambda r: dec(r["nmi_partido"]))
    lin("Polo A", lambda r: r["polo_a"])
    lin("Polo B", lambda r: r["polo_b"])
    lin("Concordância entre polos (janelas: mín.–máx.)",
        lambda r: f"{dec(100 * r['conc_polos_min'], 1)}% a {dec(100 * r['conc_polos_max'], 1)}%")
    lin("Vitórias do governo", lambda r: pct(r["vitorias_gov"], r["votacoes_gov"]))
    lin("Participação média", lambda r: f"{dec(100 * r['participacao_media'], 1)}%")
    lin("Coesão média dos partidos (Rice, ponderada)", lambda r: f"{dec(100 * r['rice_ponderado'], 1)}%")

    L += ["", f"## Partidos: apoio ao governo em cada legislatura (5+ deputados nas duas)", "",
          f"| Partido | {l0} | {l1} | Diferença |", "| --- | --- | --- | --- |"]
    pv = part_df[part_df["deputados"] >= 5].pivot(index="partido", columns="legislatura", values="apoio_gov").dropna()
    pv["dif"] = pv[l1] - pv[l0]
    for p, r in pv.sort_values("dif").iterrows():
        L.append(f"| {p} | {dec(100 * r[l0], 1)}% | {dec(100 * r[l1], 1)}% | "
                 f"{'+' if r['dif'] > 0 else ''}{dec(100 * r['dif'], 1)} p.p. |")

    L += ["", f"## Reeleitos ({n(len(re))} deputados com {MIN_VOTOS}+ votos medidos nas duas)", "",
          f"Apoio ao governo da legislatura {l0} × apoio ao governo da legislatura {l1}.", ""]
    alto = 0.7
    quad = {
        "governistas nos dois": ((re[f"apoio_{l0}"] >= alto) & (re[f"apoio_{l1}"] >= alto)).sum(),
        f"governistas só na {l0}": ((re[f"apoio_{l0}"] >= alto) & (re[f"apoio_{l1}"] < alto)).sum(),
        f"governistas só na {l1}": ((re[f"apoio_{l0}"] < alto) & (re[f"apoio_{l1}"] >= alto)).sum(),
        "governistas em nenhum": ((re[f"apoio_{l0}"] < alto) & (re[f"apoio_{l1}"] < alto)).sum(),
    }
    L.append(f"Governista = apoio de {dec(100 * alto, 0)}% ou mais.")
    L.append("")
    for k, v in quad.items():
        L.append(f"- {k}: {pct(v, len(re))}")
    L += ["", "| Deputado | Partido | Apoio " + l0 + " | Apoio " + l1 + " |", "| --- | --- | --- | --- |"]
    for _, r in re.reindex(re["diferenca"].abs().sort_values(ascending=False).index).head(15).iterrows():
        L.append(f"| {r['nome']} | {r[f'partido_{l0}']} → {r[f'partido_{l1}']} | {dec(100 * r[f'apoio_{l0}'], 1)}% | "
                 f"{dec(100 * r[f'apoio_{l1}'], 1)}% |")
    L.append("")
    (saida / "quadrantes.json").write_text(json.dumps({k: int(v) for k, v in quad.items()} | {
        "total": int(len(re)), "limiar": alto, "legislaturas": [l0, l1]}, ensure_ascii=False, indent=2), encoding="utf-8")
    rel = ROOT / RELATORIO
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
