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

    # campanha (TSE) × comportamento
    base_el = ROOT / c["redes"]["saida"].replace("/redes", "/eleicao")
    eleicao = None
    if (base_el / "resumo.json").exists():
        pa = pd.read_parquet(base_el / "parlamentares.parquet")
        co = pd.read_parquet(base_el / "correlacoes.parquet")
        alfa = float(load_config()["tse"].get("alfa", 0.01))
        pts = []
        for r in pa.itertuples():
            if r.deputado_id in idx:
                pts.append([idx[r.deputado_id], _r(r.maior_municipio, 3), _r(getattr(r, "frac_fundo_eleitoral", None), 3),
                            _r(r.custo_por_voto, 2), int(r.votos) if r.votos == r.votos else None,
                            _r(getattr(r, "receita_total", None), 0), r.municipio_principal, r.municipios_1pct if r.municipios_1pct == r.municipios_1pct else None,
                            _r(getattr(r, "imprevisibilidade", None), 4)])
        sig = co[(co["p"] < alfa) | (co["p_dentro"] < alfa)] if len(co) else co
        eleicao = {
            "resumo": json.loads((base_el / "resumo.json").read_text(encoding="utf-8")),
            "pts": pts,
            "corr": [{"x": r.campanha, "y": r.comportamento, "r": _r(r.spearman, 3), "rd": _r(r.spearman_dentro_partido, 3),
                      "s": bool(r.p < alfa), "sd": bool(r.p_dentro < alfa), "n": int(r.n)}
                     for r in sig.sort_values("spearman_dentro_partido", key=abs, ascending=False).itertuples()] if len(sig) else [],
        }

    # cota parlamentar e patrimônio
    base_co = ROOT / c["redes"]["saida"].replace("/redes", "/cota")
    cota = None
    if (base_co / "resumo.json").exists():
        cp_ = pd.read_parquet(base_co / "parlamentares.parquet")
        cp_ = cp_[cp_["meses"] >= 6]
        cota = {"resumo": json.loads((base_co / "resumo.json").read_text(encoding="utf-8")),
                "top": [{"i": idx[r.deputado_id], "m": _r(r.por_mes_real, 0), "d": _r(r.frac_divulgacao, 3)}
                        for r in cp_.nlargest(12, "por_mes_real").itertuples() if r.deputado_id in idx],
                "menos": [{"i": idx[r.deputado_id], "m": _r(r.por_mes_real, 0), "d": _r(r.frac_divulgacao, 3)}
                          for r in cp_.nsmallest(12, "por_mes_real").itertuples() if r.deputado_id in idx]}

    # comissões, relatorias, urgência e pivôs (só Câmara)
    base_cm = ROOT / c["redes"]["saida"].replace("/redes", "/comissoes")
    bast = None
    if (base_cm / "resumo.json").exists():
        rs = json.loads((base_cm / "resumo.json").read_text(encoding="utf-8"))
        pv = pd.read_parquet(base_cm / "pivos.parquet")
        pv = pv[(pv["apertadas"] >= 5) & pv["deputado_id"].isin(idx)]
        bast = {"resumo": rs,
                "pivos": [{"i": idx[r.deputado_id], "a": int(r.apertadas), "dv": int(r.dissid_venc), "dd": int(r.dissid_decisiva),
                           "ga": _r(r.apoio_gov_apertadas, 3), "gt": _r(r.apoio_gov_todas, 3)}
                          for r in pv.sort_values(["dissid_venc", "dissid_decisiva"], ascending=False).head(10).itertuples()]}
        if (base_cm / "relatores.parquet").exists():
            rl = pd.read_parquet(base_cm / "relatores.parquet")
            rl = rl[rl["deputado_id"].isin(idx)]
            bast["relatores"] = [{"i": idx[r.deputado_id], "n": int(r.relatorias), "u": _r(r.urgencia, 2)}
                                 for r in rl.nlargest(12, "relatorias").itertuples()]
            rp = pd.read_parquet(base_cm / "relatorias_partido.parquet").dropna(subset=["deputados"])
            bast["relatorias_partido"] = [{"p": r.partido, "r": _r(r.frac_relatorias, 3), "c": _r(r.frac_deputados, 3), "n": int(r.relatorias)}
                                          for r in rp.sort_values("relatorias", ascending=False).head(12).itertuples()]

    # influência e atenção (só Câmara)
    base_at = ROOT / c["redes"]["saida"].replace("/redes", "/atencao")
    aten = None
    if (base_at / "resumo.json").exists():
        ra = json.loads((base_at / "resumo.json").read_text(encoding="utf-8"))
        da = pd.read_parquet(base_at / "deputados.parquet")
        da = da[da["deputado_id"].isin(idx)]
        aten = {"resumo": {k: v for k, v in ra.items() if k != "wikipedia"}}
        if "wikipedia" in ra:
            aten["resumo"]["wikipedia"] = {k: v for k, v in ra["wikipedia"].items() if k != "picos"}
        for col, chave in (("encontros", "enc"), ("visitas_mes", "vis"), ("discursos", "dis")):
            if col in da.columns and da[col].notna().sum() >= 30:
                aten[chave] = [{"i": idx[r.deputado_id], "v": _r(getattr(r, col), 0)} for r in da.nlargest(10, col).itertuples()]
        if not any(k in aten for k in ("enc", "vis", "dis")):
            aten = None

    per = c["legislaturas"][leg] if "legislaturas" in c else {}
    return {
        "leg": leg, "casa": casa, "_ids": list(d["deputado_id"]), "ini": c["redes"]["periodo"]["inicio"], "fim": c["redes"]["periodo"]["fim"],
        "nome": per.get("nome", f"{leg}ª legislatura"), "governo": per.get("governo", ""),
        "dim": dim, "din": din, "mud": mud, "multi": multi, "modelo": modelo, "eleicao": eleicao, "cota": cota, "bastidores": bast, "atencao": aten,
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


def gerar_mapa(cfg: dict, legs: list[dict]) -> None:
    """Arquivos do mapa do Brasil, carregados pela página só quando a seção aparece (site/geo, site/dados)."""
    import shutil
    from src.config import para_senado
    from src.geo.municipios import tse_para_ibge

    destino = SAIDA.parent
    geo = ROOT / cfg["ibge"]["caminhos"]["geo"]
    ib_p = ROOT / cfg["ibge"]["caminhos"]["staging"] / "municipios.parquet"
    if not (geo / "municipios.topo.json").exists() or not ib_p.exists():
        print("mapa: malha ou indicadores do IBGE ausentes; seção do mapa sem dados")
        return
    (destino / "geo").mkdir(parents=True, exist_ok=True)
    for f in ("municipios.topo.json", "ufs.topo.json"):
        shutil.copy(geo / f, destino / "geo" / f)
    ib = pd.read_parquet(ib_p)
    # voto no PT no 2º turno presidencial, por município
    pt_anos, pt = [], {}
    for ano in cfg["tse"]["eleicoes"]:
        p = ROOT / cfg["tse"]["caminhos"]["staging"] / str(ano) / "votos_presidente.parquet"
        if not p.exists():
            continue
        vp = pd.read_parquet(p)
        vp = vp[vp["NR_TURNO"] == "2"]
        if vp.empty:
            continue
        vp = vp.merge(tse_para_ibge(cfg, vp), on="CD_MUNICIPIO", how="left").dropna(subset=["cod_ibge"])
        tot = vp.groupby("cod_ibge")["votos"].sum()
        pt[int(ano)] = (vp[vp["NR_CANDIDATO"] == "13"].groupby("cod_ibge")["votos"].sum() / tot).to_dict()
        pt_anos.append(int(ano))
    cols = ["nome", "uf", "pop", "pib_pc", "alf", "urb", "dens", "cap", *[f"pt_{a}" for a in pt_anos]]
    m = {}
    for r in ib.itertuples():
        m[r.cod_ibge] = [r.nome, r.uf, _r(r.pop_2022, 0), _r(r.pib_per_capita, 0), _r(r.alfabetizacao, 4), _r(r.urbanizacao, 4),
                         _r(r.densidade, 2), bool(r.capital), *[_r(pt[a].get(r.cod_ibge), 4) for a in pt_anos]]
    (destino / "dados").mkdir(parents=True, exist_ok=True)
    (destino / "dados" / "municipios.json").write_text(json.dumps({"c": cols, "m": m, "pt_anos": pt_anos}, ensure_ascii=False,
                                                                  separators=(",", ":")), encoding="utf-8")
    confs = {("camara", leg): c for leg, c in por_legislatura(cfg)}
    if "senado" in cfg:
        confs.update({("senado", leg): c for leg, c in por_legislatura(para_senado(cfg))})
    (destino / "dados" / "dep").mkdir(parents=True, exist_ok=True)
    n_dep = 0
    for L in legs:
        casa, leg = L.get("casa", "camara"), L["leg"]
        c = confs.get((casa, leg))
        resumo_dir = ROOT / c["redes"]["saida"].replace("/redes", "/emendas") if c else None
        base = ROOT / cfg["emendas"]["caminhos"]["mapa"] / f"{casa}_leg{leg}"
        if not resumo_dir or not (base / "municipios.parquet").exists():
            continue
        idx = {k: i for i, k in enumerate(L["_ids"])}
        mun = pd.read_parquet(base / "municipios.parquet")
        aut = pd.read_parquet(base / "municipios_autores.parquet")
        aut = aut[aut["deputado_id"].isin(idx)]
        top_aut = {k: [[idx[d], round(float(v))] for d, v in zip(g["deputado_id"], g["pago"])] for k, g in aut.groupby("cod_ibge")}
        e = {r.cod_ibge: [round(float(r.pago)), _r(r.pago_per_capita, 3), top_aut.get(r.cod_ibge, [])]
             for r in mun.itertuples() if r.pago > 0}
        v = {}
        be = base / "base_eleitoral.parquet"
        if be.exists():
            b = pd.read_parquet(be).dropna(subset=["cod_ibge"])
            b = b[b["deputado_id"].isin(idx)]
            for k, g in b.sort_values("votos", ascending=False).groupby("cod_ibge"):
                v[k] = [[idx[d], int(x)] for d, x in zip(g["deputado_id"].head(3), g["votos"].head(3))]
            dm = pd.read_parquet(base / "dep_municipio.parquet")
            for dep_id, g in b.groupby("deputado_id"):
                g = g[g["frac_votos"] >= float(cfg.get("geo", {}).get("frac_minima_mapa", 0.0005))]
                em_ = dm[dm["deputado_id"] == dep_id]
                arq = destino / "dados" / "dep" / f"{casa}_{leg}_{dep_id}.json"
                arq.write_text(json.dumps({"v": {k: round(float(x), 5) for k, x in zip(g["cod_ibge"], g["frac_votos"])},
                                           "e": {k: round(float(x)) for k, x in zip(em_["cod_ibge"], em_["pago"])}},
                                          separators=(",", ":")), encoding="utf-8")
                n_dep += 1
        r = json.loads((resumo_dir / "resumo.json").read_text(encoding="utf-8"))
        (destino / "dados" / f"mapa_{casa}_{leg}.json").write_text(json.dumps(
            {"anos": r["anos_orcamento"], "resumo": {k: r.get(k) for k in ("pago", "empenhado", "frac_base_mediana", "conexao_mediana",
                                                                        "necessidade_pib", "execucao_mediana",
                                                                        "execucao_apoio_dentro", "execucao_apoio_dentro_p")},
             "e": e, "v": v}, ensure_ascii=False, separators=(",", ":"), default=float), encoding="utf-8")
    print(f"mapa: {len(m)} municípios, {n_dep} parlamentares com arquivo próprio")


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
    tend = []
    for casa, base in (("camara", cfg), ("senado", None)):
        if casa == "senado":
            if "senado" not in cfg:
                continue
            from src.config import para_senado
            base = para_senado(cfg)
        for leg, c in por_legislatura(base):
            p = ROOT / c["redes"]["saida"].replace("/redes", "/eleicao") / "resumo.json"
            if p.exists():
                r = json.loads(p.read_text(encoding="utf-8"))
                tend.append({"casa": casa, "leg": leg, "eleicoes": r["eleicoes"], "votos": r["mediana_votos"],
                             "receita": r["mediana_receita"], "custo": r["mediana_custo_por_voto"],
                             "fundo": r["mediana_frac_fundo_eleitoral"]})
    sem = []
    for casa, base_ in (("camara", cfg), ("senado", None)):
        if casa == "senado":
            from src.config import para_senado
            base_ = para_senado(cfg)
        partes = []
        for leg, c in por_legislatura(base_):
            p_ = ROOT / c["redes"]["saida"].replace("/redes", "/cota") / "mensal.parquet"
            if p_.exists():
                partes.append(pd.read_parquet(p_))
        if partes:
            m_ = pd.concat(partes)
            m_["s"] = m_["data_mes"].dt.year.astype(str) + "-" + np.where(m_["data_mes"].dt.month <= 6, "1", "2")
            g_ = m_.groupby("s")[["divulgacao_real", "total_real"]].sum()
            sem.append({"casa": casa, "s": [{"s": k, "d": _r(r.divulgacao_real, 0), "t": _r(r.total_real, 0)} for k, r in g_.iterrows()]})
    dados = {"atualizado": atualizado, "campanha_tendencia": tend, "cota_semestres": sem, "legislaturas": legs, "comparacao": dados_comparacao(),
             "acompanhamento": dados_acompanhamento(cfg),
             "marcadores": cfg.get("marcadores_periodo", []), "contexto": cfg.get("contexto", {}),
             "repo": f"https://github.com/{cfg['armazenamento']['repositorio']}"}
    try:
        gerar_mapa(cfg, legs)
    except Exception as e:  # noqa: BLE001 — o mapa não derruba a página
        print(f"::warning title=mapa::{e}")
    for L in legs:
        L.pop("_ids", None)
    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    corpo = MODELO.read_text(encoding="utf-8").replace("/*__DADOS__*/null", js.replace("</", "<\\/"))
    partes = (ROOT / "src" / "site" / "mapa.html").read_text(encoding="utf-8")
    css, resto = partes.split("<!--CSS-->", 1)[1].split("<!--HTML-->", 1)
    html_, js_mapa = resto.split("<!--JS-->", 1)
    corpo = corpo.replace("/*__MAPA_CSS__*/", css).replace("<!--__MAPA_HTML__-->", html_).replace("/*__MAPA_JS__*/", js_mapa)
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
