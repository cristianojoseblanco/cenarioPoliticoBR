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

from src.config import ROOT, legislatura_tem_dados, load_config, path, por_legislatura

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


def dados_legislatura(leg: str, c: dict, casa: str = "camara") -> dict:
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
    gt = gtem.pivot(index="tema", columns="comunidade", values="apoio") if len(gtem) else pd.DataFrame()
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

    # dimensões de voto
    base_dim = ROOT / c["redes"]["saida"].replace("/redes", "/dimensoes")
    dim = None
    if (base_dim / "resumo.json").exists():
        dres = json.loads((base_dim / "resumo.json").read_text(encoding="utf-8"))
        ddep = pd.read_parquet(base_dim / "deputados.parquet").set_index("deputado_id")
        dvt = pd.read_parquet(base_dim / "votacoes.parquet")
        dim = {
            "var": [_r(v) for v in dres["variancia"]], "temas": dres["temas_principais"],
            "corr": dres["correlacoes"],
            "pts": [[idx[i], _r(r.d1, 3), _r(r.d2, 3)] for i, r in ddep.iterrows() if i in idx],
            "votacoes": [{"dim": r.dim, "lado": r.lado, "data": (r.data or "")[:10], "prop": r.proposicao,
                          "ementa": (r.ementa or "").splitlines()[0][:160]} for r in dvt.itertuples()],
        }

    # dinâmica mensal e agenda
    base_din = ROOT / c["redes"]["saida"].replace("/redes", "/dinamica")
    din = None
    if (base_din / "mensal.parquet").exists():
        mm = pd.read_parquet(base_din / "mensal.parquet")
        ag = pd.read_parquet(base_din / "agenda.parquet")
        dr = json.loads((base_din / "resumo.json").read_text(encoding="utf-8"))
        din = {
            "resumo": dr,
            "mensal": [{"m": r.mes.strftime("%Y-%m"), "n": int(r.votacoes), "pol": int(r.polarizadas),
                        "ap": int(r.apertadas), "go": int(r.gov_orientou), "gv": int(r.gov_venceu),
                        "folga": _r(r.votos_para_virar, 1), "fora": _r(r.fora_no_lado_gov, 3)} for r in mm.itertuples()],
            "agenda": [{"t": r.tri.strftime("%Y-%m"), "tema": r.tema, "n": int(r.votacoes)} for r in ag.itertuples()],
        }

    # pontos de mudança e comunidades no tempo
    base_mud = ROOT / c["redes"]["saida"].replace("/redes", "/mudancas")
    mud = None
    if (base_mud / "resumo.json").exists():
        ss = pd.read_parquet(base_mud / "series.parquet")
        sg = pd.read_parquet(base_mud / "segmentos.parquet")
        pt = pd.read_parquet(base_mud / "pontos.parquet")
        js_ = pd.read_parquet(base_mud / "janelas.parquet")
        fl = pd.read_parquet(base_mud / "fluxos.parquet")
        cols = ["apoio_polo_a", "apoio_polo_b", "apoio_fora", "polarizacao", "vitoria_gov"]
        mud = {
            "resumo": json.loads((base_mud / "resumo.json").read_text(encoding="utf-8")),
            "series": [{"m": r["mes"].strftime("%Y-%m"), "n": int(r["votacoes"]), **{k: _r(r[k], 3) for k in cols}}
                       for _, r in ss.iterrows()],
            "segmentos": [{"ini": r["inicio"].strftime("%Y-%m"), "fim": r["fim"].strftime("%Y-%m"), "meses": int(r["meses"]),
                           "n": int(r["votacoes"]), **{k: _r(r[k], 3) for k in cols}} for _, r in sg.iterrows()],
            "pontos": [{"m": r["mes"].strftime("%Y-%m"), "rob": bool(r["robusto"]), "princ": list(r["principais"]),
                        "delta": {k: _r(r[f"delta_{k}"], 3) for k in cols},
                        "ev": r["evento"] if pd.notna(r["evento"]) else None,
                        "evd": r["evento_data"].strftime("%Y-%m-%d") if pd.notna(r["evento_data"]) else None}
                       for _, r in pt.iterrows()] if len(pt) else [],
            "janelas": [{"j": r.janela[:3], "fim": r.fim, "ari": _r(r.ari_anterior, 3), "tr": _r(r.trocaram, 3),
                         "k": int(r.comunidades)} for r in js_.itertuples()],
            "fluxos": [{"j": r.janela[:3], "de": r.de, "para": r.para, "n": int(r.deputados)}
                       for r in fl.itertuples() if r.de != r.para],
        }

    # rede em várias camadas
    base_mc = ROOT / c["redes"]["saida"].replace("/redes", "/multicamadas")
    multi = None
    if (base_mc / "resumo.json").exists():
        cr = pd.read_parquet(base_mc / "correlacoes.parquet")
        fr = pd.read_parquet(base_mc / "frentes.parquet")
        ft = pd.read_parquet(base_mc / "frentes_tematicas.parquet")
        multi = {
            "resumo": json.loads((base_mc / "resumo.json").read_text(encoding="utf-8")),
            "corr": [{"cam": r.camada, "pares": r.pares, "rho": _r(r.spearman, 3), "com": _r(r.conc_com_ligacao, 3),
                      "sem": _r(r.conc_sem_ligacao, 3), "nl": int(r.com_ligacao), "n": int(r.n_pares)} for r in cr.itertuples()],
            "frentes": [{"t": r.titulo, "m": int(r.membros_com_voto), "o": _r(r.coesao, 3), "e": _r(r.coesao_esperada, 3),
                         "x": _r(r.excesso, 4), "pc": _r(r.percentil, 3), "p": r.partidos, "b": bool(r.bloco)}
                        for r in fr.sort_values("excesso", ascending=False).head(15).itertuples()] if len(fr) else [],
            "frentes_analisadas": int(len(fr)), "frentes_bloco": int(fr["bloco"].sum()) if len(fr) else 0,
            "tematicas": [{"f": r.frente, "t": r.titulo, "m": int(r.membros), "temas": r.temas,
                           "dt": _r(r.dif_tema, 4), "dti": _r(r.ic_tema_inf, 4), "dts": _r(r.ic_tema_sup, 4),
                           "do": _r(r.dif_outros, 4), "doi": _r(r.ic_outros_inf, 4), "dos": _r(r.ic_outros_sup, 4),
                           "esp": _r(r.especifico, 4), "claro": bool(r.efeito_claro), "nv": int(r.votacoes_tema)}
                          for r in ft.sort_values("especifico", ascending=False).itertuples()] if len(ft) else [],
        }
        if len(fr):
            mem = pd.read_parquet(path(c, "processed") / "frente_membro")
            mem = mem[mem["legislatura"] == int(leg)]
            multi["frentes_total"] = int(mem["frente_id"].nunique())
            multi["frentes_por_dep"] = _r(mem.groupby("deputado_id")["frente_id"].nunique().median(), 1)
            multi["membros_mediana"] = _r(mem.groupby("frente_id")["deputado_id"].nunique().median(), 0)

    # modelo de voto individual
    base_mo = ROOT / c["redes"]["saida"].replace("/redes", "/modelo")
    modelo = None
    if (base_mo / "resumo.json").exists():
        md = pd.read_parquet(base_mo / "deputados.parquet")
        minimo = int(c.get("modelo", {}).get("min_votos_deputado", 100))
        md = md[md["votos"] >= minimo]
        im = pd.read_parquet(base_mo / "importancias.parquet")
        tm = pd.read_parquet(base_mo / "temas.parquet")
        mm = pd.read_parquet(base_mo / "mensal.parquet")
        vv = pd.read_parquet(base_mo / "votacoes.parquet")
        uf = d.set_index("deputado_id")["uf"]
        modelo = {
            "resumo": json.loads((base_mo / "resumo.json").read_text(encoding="utf-8")),
            "imp": [{"v": r.variavel, "i": _r(r.importancia, 4)} for r in im.head(8).itertuples()],
            "mais": [{"n": r.nome, "p": r.partido, "uf": uf.get(r.deputado_id, ""), "i": _r(r.imprevisibilidade, 4),
                      "ip": _r(r.imprev_partido, 4), "s": int(r.surpresas), "v": int(r.votos)}
                     for r in md.nlargest(15, "imprevisibilidade").itertuples()],
            "menos": [{"n": r.nome, "p": r.partido, "uf": uf.get(r.deputado_id, ""), "i": _r(r.imprevisibilidade, 4),
                       "ip": _r(r.imprev_partido, 4), "s": int(r.surpresas), "v": int(r.votos)}
                      for r in md.nsmallest(15, "imprevisibilidade").itertuples()],
            "partidos": [{"p": p_, "i": _r(g.median(), 4), "n": int(len(g))}
                         for p_, g in md.groupby("partido")["imprevisibilidade"] if len(g) >= 5],
            "temas": [{"t": r.tema, "i": _r(r.imprevisibilidade, 4), "v": int(r.votos)} for r in tm.itertuples()],
            "mensal": [{"m": r.mes.strftime("%Y-%m"), "i": _r(r.imprevisibilidade, 4), "v": int(r.votos)} for r in mm.itertuples()],
            "votacoes": [{"d": str(r.data)[:10], "prop": r.proposicao, "t": r.texto, "s": int(r.surpresas), "v": int(r.votos)}
                         for r in vv.head(8).itertuples()],
        }

    per = c["legislaturas"][leg] if "legislaturas" in c else {}
    return {
        "leg": leg, "casa": casa, "ini": c["redes"]["periodo"]["inicio"], "fim": c["redes"]["periodo"]["fim"],
        "nome": per.get("nome", f"{leg}ª legislatura"), "governo": per.get("governo", ""),
        "dim": dim, "din": din, "mud": mud, "multi": multi, "modelo": modelo,
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


def dados_acompanhamento(cfg) -> list | None:
    p = ROOT / cfg.get("acompanhamento", {}).get("saida", "data/marts/camara/acompanhamento")
    if not (p / "deputados.json").exists():
        return None
    fichas = json.loads((p / "deputados.json").read_text(encoding="utf-8"))
    mm = pd.read_parquet(p / "mensal.parquet") if (p / "mensal.parquet").stat().st_size > 0 else pd.DataFrame()
    rb = pd.read_parquet(p / "rebeldias.parquet") if (p / "rebeldias.parquet").stat().st_size > 0 else pd.DataFrame()
    minimo = int(cfg.get("acompanhamento", {}).get("min_colegas", 3))
    for f in fichas:
        i = f.get("deputado_id")
        f["mensal"] = [] if mm.empty or not i else [
            {"m": r.mes.strftime("%Y-%m"), "p": r.partido, "v": int(r.votos) if r.votos == r.votos else 0,
             "sp": _r(r.segue_partido, 3), "nsp": int(r.n_segue_partido) if r.n_segue_partido == r.n_segue_partido else 0,
             "cb": _r(r.com_bancada, 3), "ag": _r(r.apoio_gov, 3), "pr": _r(r.presenca, 3),
             "psp": _r(r.partido_segue_partido, 3), "pcb": _r(r.partido_com_bancada, 3), "pag": _r(r.partido_apoio_gov, 3),
             "peq": bool(r.colegas == r.colegas and r.colegas < minimo)}
            for r in mm[mm["deputado_id"] == i].sort_values("mes").itertuples()]
        f["rebs"] = [] if rb.empty or not i else [
            {"d": str(r.data)[:10], "p": r.partido, "prop": r.proposicao, "t": r.texto, "v": r.voto_dep,
             "op": r.orientacao_partido, "og": r.orientacao_governo}
            for r in rb[rb["deputado_id"] == i].head(cfg.get("acompanhamento", {}).get("rebeldias_na_pagina", 15)).itertuples()]
    return fichas


def main() -> int:
    cfg = load_config()
    legs = [dados_legislatura(leg, c) for leg, c in por_legislatura(cfg) if legislatura_tem_dados(c)]
    if "senado" in cfg:
        from src.config import para_senado
        for leg, c in por_legislatura(para_senado(cfg)):
            if legislatura_tem_dados(c) and (ROOT / c["governabilidade"]["saida"] / "resumo.json").exists():
                legs.append(dados_legislatura(leg, c, "senado"))
    try:
        meta = json.loads((ROOT / "data/metadata/camara/_ultima_execucao.json").read_text(encoding="utf-8"))
        atualizado = meta["executado_em"][:10]
    except Exception:
        atualizado = datetime.now(timezone.utc).date().isoformat()
    dados = {"atualizado": atualizado, "legislaturas": legs, "comparacao": dados_comparacao(),
             "acompanhamento": dados_acompanhamento(cfg),
             "marcadores": cfg.get("marcadores_periodo", []), "contexto": cfg.get("contexto", {}),
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
