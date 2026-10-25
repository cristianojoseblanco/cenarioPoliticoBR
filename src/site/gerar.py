"""Gera a página estática (site/index.html) a partir dos resultados em data/marts.

Junta os dados de cada legislatura e da comparação num único JSON embutido no HTML
(site/modelo.html). Não há servidor: a página funciona sozinha (GitHub Pages).

Uso: python -m src.site.gerar
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.config import ROOT, legislatura_tem_dados, load_config, por_legislatura

MODELO = ROOT / "src" / "site" / "modelo.html"
SAIDA = ROOT / "site" / "index.html"
TOP = 12


def _r(x, d=4):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), d)


def _ler(c, sec, arq):
    p = ROOT / c[sec]["saida"] / arq
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return pd.read_parquet(p)


def dados_legislatura(leg: str, c: dict) -> dict:
    m = _ler(c, "redes", "metricas.json")
    rede = _ler(c, "redes", "deputados_rede.parquet")
    arestas = _ler(c, "redes", "arestas.parquet")
    polos = _ler(c, "fatias", "polos.json")
    res = _ler(c, "fatias", "resumo.parquet")
    meta = _ler(c, "fatias", "fatias.parquet")
    pos = _ler(c, "fatias", "posicoes.parquet")
    desl = _ler(c, "fatias", "deslocamentos.parquet")
    gdep = _ler(c, "governabilidade", "deputados.parquet")
    gpart = _ler(c, "governabilidade", "partidos.parquet")
    gjan = _ler(c, "governabilidade", "janelas_comunidade.parquet")
    gvit = _ler(c, "governabilidade", "janelas_vitoria.parquet")
    gtem = _ler(c, "governabilidade", "temas.parquet")
    gres = _ler(c, "governabilidade", "resumo.json")

    # posição de cada deputado: média das janelas em que aparece
    pj = pos[pos["tipo"] == "janela"]
    pos_media = pj.groupby("deputado_id")["posicao"].mean()

    d = rede.rename(columns={"participacao": "ponte"}).merge(
        gdep[["deputado_id", "votos_gov", "apoio_gov", "votos_disc", "disciplina", "em_exercicio", "presentes",
              "participacao"]], on="deputado_id", how="left")
    d["posicao"] = d["deputado_id"].map(pos_media)
    d = d.sort_values("deputado_id").reset_index(drop=True)
    idx = {k: i for i, k in enumerate(d["deputado_id"])}
    deputados = [{
        "id": r.deputado_id, "n": r.nome, "p": r.partido, "uf": r.uf, "c": r.comunidade,
        "x": _r(r.x, 3), "y": _r(r.y, 3), "pos": _r(r.posicao, 3),
        "ag": _r(r.apoio_gov, 4), "vg": int(r.votos_gov) if r.votos_gov == r.votos_gov else 0,
        "di": _r(r.disciplina, 4), "vd": int(r.votos_disc) if r.votos_disc == r.votos_disc else 0,
        "pa": _r(r.participacao, 4), "pr": int(r.presentes) if r.presentes == r.presentes else 0,
        "ex": int(r.em_exercicio) if r.em_exercicio == r.em_exercicio else 0, "po": _r(r.ponte, 3),
    } for r in d.itertuples()]
    edges = [[idx[a], idx[b]] for a, b in zip(arestas["deputado_a"], arestas["deputado_b"]) if a in idx and b in idx]

    comunidades = []
    for cc, tam in m["comunidades"].items():
        sub = d[d["comunidade"] == cc]
        comunidades.append({"id": cc, "tam": tam,
                            "comp": [[p, int(q)] for p, q in sub["partido"].value_counts().head(5).items()]})

    jan = res[res["tipo"] == "janela"].copy()
    jan["fim"] = jan["fatia"].str[-10:]
    jan["ini"] = jan["fatia"].str[4:14]
    janelas = []
    mj = meta[meta["tipo"] == "janela"].set_index("fatia")
    for (fatia, ini, fim), g in jan.groupby(["fatia", "ini", "fim"], sort=False):
        v = gvit[gvit["janela"] == fatia]
        ap = gjan[gjan["janela"] == fatia].set_index("comunidade")["apoio"]
        janelas.append({
            "ini": ini, "fim": fim, "cp": _r(mj.loc[fatia, "conc_entre_polos"]),
            "pos": {r.comunidade_global: _r(r.posicao_media, 3) for r in g.itertuples()},
            "ap": {k: _r(v2) for k, v2 in ap.items()},
            "vit": _r(v["vitoria"].iloc[0]) if len(v) else None,
            "nv": int(v["votacoes_gov"].iloc[0]) if len(v) else 0,
        })
    janelas.sort(key=lambda j: j["fim"])

    tem = res[res["tipo"] == "tema"]
    mt = meta[meta["tipo"] == "tema"].set_index("fatia")
    gt = gtem.pivot(index="tema", columns="comunidade", values="apoio")
    temas = [{
        "t": t, "nv": int(mt.loc[t, "votacoes"]), "cp": _r(mt.loc[t, "conc_entre_polos"]),
        "pos": {r.comunidade_global: _r(r.posicao_media, 3) for r in tem[tem["fatia"] == t].itertuples()},
        "ap": {k: _r(gt.loc[t, k]) for k in gt.columns if k != "vitoria_governo" and t in gt.index},
        "vit": _r(gt.loc[t, "vitoria_governo"]) if t in gt.index else None,
    } for t in mt.sort_values("votacoes", ascending=False).index]

    part = gpart[gpart["deputados"] >= 5].copy()
    part["cob"] = part["votos_disc"] / part["votos_com_valor"]
    partidos = [{"p": r.partido, "dep": int(r.deputados), "ag": _r(r.apoio_gov), "di": _r(r.disciplina),
                 "cob": _r(r.cob), "ri": _r(r.rice)} for r in part.sort_values("apoio_gov", ascending=False).itertuples()]

    # rankings (deputados com base mínima de votos)
    base = d[(d["votos_gov"] >= 100)]
    dl = desl.join(d.set_index("deputado_id")[[]], how="inner")

    def lista(df, col, asc, extra=None):
        out = []
        for r in df.sort_values(col, ascending=asc).head(TOP).itertuples():
            out.append(idx[r.deputado_id] if hasattr(r, "deputado_id") else idx[r.Index])
        return out

    rankings = {
        "governistas": lista(base, "apoio_gov", False),
        "oposicao": lista(base, "apoio_gov", True),
        "divergentes": lista(d[d["votos_disc"] >= 100], "disciplina", True),
        "pontes": lista(d, "ponte", False),
        "participacao": lista(d[d["em_exercicio"] >= 100], "participacao", True),
    }
    mov = dl.reindex(dl["delta"].abs().sort_values(ascending=False).index).head(TOP)
    rankings["moveram"] = [{"i": idx[i], "de": _r(r.inicio, 3), "ate": _r(r.fim, 3)} for i, r in mov.iterrows()]

    return {
        "leg": leg, "ini": c["redes"]["periodo"]["inicio"], "fim": c["redes"]["periodo"]["fim"],
        "votacoes": m["votacoes"]["votacoes_total"], "analisadas": m["votacoes"]["incluidas"],
        "modularidade": _r(m["modularidade"]), "nmi": _r(m["nmi_com_partido"]),
        "polos": {"a": polos["polo_a"], "b": polos["polo_b"]},
        "gov": {"n": gres["votacoes_gov"], "v": gres["vitorias_gov"]},
        "comunidades": comunidades, "deputados": deputados, "arestas": edges,
        "janelas": janelas, "temas": temas, "partidos": partidos, "rankings": rankings,
    }


def dados_comparacao() -> dict | None:
    p = ROOT / "data" / "marts" / "camara" / "comparacao"
    if not (p / "legislaturas.parquet").exists():
        return None
    re = pd.read_parquet(p / "reeleitos.parquet")
    q = json.loads((p / "quadrantes.json").read_text(encoding="utf-8"))
    l0, l1 = q["legislaturas"]
    part = pd.read_parquet(p / "partidos.parquet")
    pv = part[part["deputados"] >= 5].pivot(index="partido", columns="legislatura", values="apoio_gov").dropna()
    return {
        "legs": [l0, l1], "quad": q,
        "reeleitos": [{"n": r.nome, "p0": getattr(r, f"partido_{l0}"), "p1": getattr(r, f"partido_{l1}"),
                       "a0": _r(getattr(r, f"apoio_{l0}"), 3), "a1": _r(getattr(r, f"apoio_{l1}"), 3)}
                      for r in re.itertuples()],
        "partidos": [{"p": i, "a0": _r(r[l0]), "a1": _r(r[l1])} for i, r in pv.sort_values(l1).iterrows()],
    }


def main() -> int:
    cfg = load_config()
    legs = [dados_legislatura(leg, c) for leg, c in por_legislatura(cfg) if legislatura_tem_dados(c)]
    try:
        meta = json.loads((ROOT / "data/metadata/camara/_ultima_execucao.json").read_text(encoding="utf-8"))
        atualizado = meta["executado_em"][:10]
    except Exception:
        atualizado = datetime.now(timezone.utc).date().isoformat()
    dados = {"atualizado": atualizado, "legislaturas": legs, "comparacao": dados_comparacao(),
             "marcadores": cfg.get("marcadores_periodo", []),
             "repo": f"https://github.com/{cfg['armazenamento']['repositorio']}"}
    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    corpo = MODELO.read_text(encoding="utf-8").replace("/*__DADOS__*/null", js.replace("</", "<\\/"))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    # fragmento (para publicar como artifact, que já envolve o documento)
    (SAIDA.parent / "fragmento.html").write_text(corpo, encoding="utf-8")
    # documento completo (GitHub Pages)
    # move o <style> e metadados para o head e o resto para o body
    i = corpo.index("</style>") + len("</style>")
    pagina = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
              '[hidden]{display:none!important}img{max-width:100%}</style>\n'
              + corpo[:i] + "\n</head>\n<body>\n" + corpo[i:] + "\n</body>\n</html>\n")
    SAIDA.write_text(pagina, encoding="utf-8")
    print(f"site/index.html: {len(pagina) / 1e3:.0f} KB, legislaturas {[l['leg'] for l in legs]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
