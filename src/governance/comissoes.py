"""Comissões, relatorias, urgência e pivôs (Bloco B), Câmara, por legislatura.

1. Pivôs: votações nominais apertadas no Plenário (|Sim − Não| ≤ `comissoes.margem_apertada` dos votos Sim+Não).
   Por deputado: em quantas votou, quantas vezes votou contra a orientação do próprio partido E ficou do lado
   vencedor ("dissidência vencedora"), e o apoio ao governo nas apertadas × em todas.
   "Decisiva" = votação em que as dissidências do lado vencedor são em número maior que a margem.
2. Urgência: requerimentos de urgência votados por ano; votações de mérito sobre proposições em urgência
   (regime na tramitação vigente na data da votação); tempo entre apresentação e 1ª votação nominal, por regime.
3. Relatorias: relator no Plenário de cada proposição votada (último relator registrado na tramitação até a
   votação). Relatorias por partido e por deputado; apoio ao governo dos relatores.
4. Comissões: composição por partido, presidências (por partido, comissões-chave) e apoio ao governo dos
   titulares de cada comissão × Plenário.

Saídas em data/marts/camara/leg<N>/comissoes/. Uso: python -m src.governance.comissoes
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, legislatura_tem_dados, load_config, path, por_legislatura
from src.governance.indicadores import base_votos, carregar
from src.networks.votacao import dec, n, nomes_deputados


def _f(x, d=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x) else round(float(x), d)


def _staging(cfg):
    return ROOT / cfg["comissoes"]["caminhos"]["staging"]


def pivos(c, votacoes_gov, votos, orient, nomes, quorum):
    k = c["comissoes"]
    b, _, _ = base_votos(c, None, votos, orient)
    r = votacoes_gov[["votacao_id", "placar_sim", "placar_nao", "aprovado", "gov_valor", "governo_venceu"]].merge(
        quorum, on="votacao_id", how="left")
    # margem em votos até o resultado virar: maioria simples (Sim × Não) ou quórum fixo (PEC, PLP, urgência)
    r["margem"] = np.where(r["quorum"].notna(), (r["placar_sim"] - r["quorum"]).abs(),
                           (r["placar_sim"] - r["placar_nao"]).abs())
    r["apertada"] = r["margem"] <= k["margem_votos"]
    b = b.merge(r, on="votacao_id")
    b = b[b["valor"].notna()]
    b["vencedor"] = (b["valor"] > 0) == b["aprovado"].astype(bool)
    b["dissid_venc"] = (b["disciplinado"] == 0) & b["vencedor"]
    ap = b[b["apertada"]]
    dec_ = ap.groupby("votacao_id").agg(dv=("dissid_venc", "sum"), margem=("margem", "first"))
    decisivas = set(dec_.index[dec_["dv"] > dec_["margem"]])
    ap = ap.assign(decisiva=ap["votacao_id"].isin(decisivas))
    por = ap.groupby("deputado_id").agg(
        apertadas=("votacao_id", "nunique"), dissid_venc=("dissid_venc", "sum"),
        dissid_decisiva=("dissid_venc", lambda s: int((s & ap.loc[s.index, "decisiva"]).sum())),
        apoio_gov_apertadas=("alinhado_gov", "mean"), partido=("partido", lambda s: s.mode().iat[0]))
    geral = b.groupby("deputado_id")["alinhado_gov"].mean().rename("apoio_gov_todas")
    por = por.join(geral).reset_index().merge(nomes, on="deputado_id", how="left")
    por["diferenca_apoio"] = por["apoio_gov_apertadas"] - por["apoio_gov_todas"]
    rr = r[r["gov_valor"].notna()]
    resumo = {"votacoes": int(len(r)), "apertadas": int(r["apertada"].sum()), "decisivas": len(decisivas),
              "gov_venceu_apertadas": _f(rr.loc[rr["apertada"], "governo_venceu"].mean()),
              "gov_venceu_todas": _f(rr["governo_venceu"].mean()),
              "margem_votos": k["margem_votos"]}
    return por, resumo, r


def _principal(c, votacoes):
    """Proposição de cada votação: a de tipo mais 'de mérito' entre as ligadas (exclui REQ quando há outra)."""
    P = path(c, "processed")
    vp = pd.read_parquet(P / "votacao_proposicao")
    vp = vp[vp["votacao_id"].isin(votacoes["votacao_id"])]
    vp["req"] = vp["sigla_tipo"].isin(["REQ", "REC"])
    vp = vp.sort_values(["votacao_id", "req"]).drop_duplicates("votacao_id")
    pr = pd.read_parquet(P / "proposicoes", columns=["proposicao_id", "data_apresentacao", "ano_apresentacao"])
    return vp.merge(pr, on="proposicao_id", how="left")


def urgencia_relatoria(c, cfg, votacoes, gov_dep, nomes):
    P = path(c, "processed")
    v = pd.read_parquet(P / "votacoes", columns=["votacao_id", "descricao"])
    vt = votacoes.merge(v, on="votacao_id", how="left")
    vt["ano"] = pd.to_datetime(vt["data"]).dt.year
    vt["req_urgencia"] = vt["descricao"].str.contains(r"Requerimento de Urg", case=False, na=False)
    out = {"req_urgencia_ano": [{"ano": int(a), "req": int(g["req_urgencia"].sum()), "votacoes": int(len(g))}
                                for a, g in vt.groupby("ano")]}
    trp = _staging(cfg) / "tramitacoes.parquet"
    if not trp.exists():
        return out, None, None
    tr = pd.read_parquet(trp)
    tr["dataHora"] = pd.to_datetime(tr["dataHora"], errors="coerce")
    tr = tr.dropna(subset=["dataHora"]).sort_values("dataHora")
    pp = _principal(c, votacoes).merge(vt[["votacao_id", "data", "req_urgencia", "ano"]], on="votacao_id")
    pp["data"] = pd.to_datetime(pp["data"])
    pp = pp.sort_values("data")
    tr["proposicao_id"] = tr["proposicao_id"].astype(str)
    pp["proposicao_id"] = pp["proposicao_id"].astype(str)
    # regime vigente e último relator até o fim do dia da votação
    pp["corte"] = pp["data"] + pd.Timedelta(days=1)
    reg = pd.merge_asof(pp.sort_values("corte"), tr[tr["regime"].notna() & (tr["regime"] != "None")][["proposicao_id", "dataHora", "regime"]],
                        left_on="corte", right_on="dataHora", by="proposicao_id", direction="backward")
    rel = pd.merge_asof(pp.sort_values("corte"), tr[tr["relator_id"].notna() & (tr["relator_id"] != "None")][["proposicao_id", "dataHora", "relator_id"]],
                        left_on="corte", right_on="dataHora", by="proposicao_id", direction="backward")
    pp = reg[["votacao_id", "proposicao_id", "sigla_tipo", "data", "ano", "req_urgencia", "data_apresentacao", "regime"]].merge(
        rel[["votacao_id", "relator_id"]], on="votacao_id", how="left")
    pp["urgencia"] = pp["regime"].str.contains("Urg", na=False)
    merito = pp[~pp["req_urgencia"] & ~pp["sigla_tipo"].isin(["REQ", "REC"])]
    out["merito_urgencia_ano"] = [{"ano": int(a), "urgencia": int(g["urgencia"].sum()), "merito": int(len(g))}
                                  for a, g in merito.groupby("ano")]
    prim = merito.sort_values("data").drop_duplicates("proposicao_id")
    prim = prim.assign(dias=(prim["data"] - pd.to_datetime(prim["data_apresentacao"], errors="coerce")).dt.days)
    prim = prim[prim["dias"] >= 0]
    out["tempo_ate_votar"] = [{"grupo": nome, "proposicoes": int(len(g)), "mediana_dias": _f(g["dias"].median(), 0)}
                              for nome, g in (("Urgência", prim[prim["urgencia"]]), ("Sem urgência", prim[~prim["urgencia"]]))
                              if len(g)]
    out["tempo_por_tipo"] = [{"tipo": t, "urgencia": _f(g["urgencia"].mean()), "proposicoes": int(len(g)),
                              "mediana_dias": _f(g["dias"].median(), 0)}
                             for t, g in prim.groupby("sigla_tipo") if len(g) >= 10]
    # relatorias: uma por proposição (o relator da votação de mérito mais recente)
    rl = merito.dropna(subset=["relator_id"]).sort_values("data").drop_duplicates("proposicao_id", keep="last")
    rl = rl.merge(gov_dep[["deputado_id", "partido", "apoio_gov", "comunidade"]], left_on="relator_id",
                  right_on="deputado_id", how="left")
    por_dep = rl.groupby("relator_id").agg(relatorias=("proposicao_id", "nunique"),
                                           urgencia=("urgencia", "mean")).reset_index().rename(columns={"relator_id": "deputado_id"})
    por_dep = por_dep.merge(gov_dep[["deputado_id", "partido", "apoio_gov"]], on="deputado_id", how="left").merge(
        nomes, on="deputado_id", how="left")
    por_part = rl.groupby("partido").agg(relatorias=("proposicao_id", "nunique")).reset_index()
    tam = gov_dep.groupby("partido").size().rename("deputados")
    por_part = por_part.merge(tam, on="partido", how="left")
    por_part["frac_relatorias"] = por_part["relatorias"] / por_part["relatorias"].sum()
    por_part["frac_deputados"] = por_part["deputados"] / tam.sum()
    out["relatorias"] = {"proposicoes_com_relator": int(len(rl)), "proposicoes_merito": int(merito["proposicao_id"].nunique()),
                         "apoio_gov_relatores": _f(rl["apoio_gov"].mean()), "apoio_gov_plenario": _f(gov_dep["apoio_gov"].mean()),
                         "relatores": int(rl["relator_id"].nunique())}
    return out, por_dep, por_part


def comissoes(c, cfg, leg, gov_dep, nomes):
    mp = _staging(cfg) / "membros" / f"leg={leg}.parquet"
    op = _staging(cfg) / "orgaos.parquet"
    if not mp.exists():
        return None, None
    m = pd.read_parquet(mp)
    org = pd.read_parquet(op) if op.exists() else pd.DataFrame()
    if len(org):
        org["orgao_id"] = org["uri"].map(lambda u: str(u).rstrip("/").rsplit("/", 1)[-1]) if "uri" in org.columns else org.get("id")
        tipo_col = next((x for x in ("tipoOrgao", "descricaoTipo", "tipo") if x in org.columns), None)
        if tipo_col:
            m = m.merge(org[["orgao_id", tipo_col]].rename(columns={tipo_col: "tipo_orgao"}), on="orgao_id", how="left")
    if "tipo_orgao" not in m.columns:
        m["tipo_orgao"] = None
    perm = m[m["tipo_orgao"].fillna("").str.contains("Permanente", case=False)]
    if perm.empty:
        perm = m[m["siglaOrgao"].str.match(r"^C[A-Z]+$", na=False)]
    perm = perm.copy()
    perm["cargo"] = perm["cargo"].fillna("")
    # siglas cortadas no arquivo (ex.: REPUBLIC) → sigla completa usada nas votações
    siglas = sorted(set(gov_dep["partido"].dropna()))
    perm["siglaPartido"] = perm["siglaPartido"].map(
        lambda s: s if s in siglas or not isinstance(s, str) else next((x for x in siglas if x.startswith(s.upper())), s))
    perm = perm.merge(gov_dep[["deputado_id", "apoio_gov"]], on="deputado_id", how="left")
    plen = gov_dep["apoio_gov"].mean()
    tit = perm[perm["cargo"].isin(["Titular", "Presidente", "1º Vice-Presidente", "2º Vice-Presidente", "3º Vice-Presidente"])]
    pres = perm[perm["cargo"] == "Presidente"].copy()
    pres["inicio"] = pd.to_datetime(pres["dataInicio"], errors="coerce")
    pres = pres.dropna(subset=["inicio"]).sort_values("inicio")
    # o arquivo traz o partido ATUAL do deputado; vale o partido em que votava na data da posse
    po = pd.read_parquet(path(c, "processed") / "partido_observado").sort_values("primeiro_voto")
    pres = pd.merge_asof(pres, po[["deputado_id", "primeiro_voto", "partido"]].rename(columns={"partido": "partido_data"}),
                         left_on="inicio", right_on="primeiro_voto", by="deputado_id", direction="backward")
    falta = pres["partido_data"].isna()
    pres.loc[falta, "partido_data"] = pd.merge_asof(
        pres.loc[falta, ["inicio", "deputado_id"]], po[["deputado_id", "primeiro_voto", "partido"]],
        left_on="inicio", right_on="primeiro_voto", by="deputado_id", direction="forward")["partido"].values
    pres["siglaPartido"] = pres["partido_data"].fillna(pres["siglaPartido"])
    pres_part = pres.groupby("siglaPartido").size().rename("presidencias").reset_index()
    tam = gov_dep.groupby("partido").size().rename("deputados").reset_index().rename(columns={"partido": "siglaPartido"})
    pres_part = pres_part.merge(tam, on="siglaPartido", how="left").sort_values("presidencias", ascending=False)
    por_com = tit.groupby(["siglaOrgao"]).agg(nome=("nomeOrgao", "first"), titulares=("deputado_id", "nunique"),
                                              apoio_gov=("apoio_gov", "mean")).reset_index()
    por_com["diferenca"] = por_com["apoio_gov"] - plen
    chave = []
    for s in c["comissoes"]["chave"]:
        p_ = pres[pres["siglaOrgao"] == s]
        chave.append({"sigla": s, "presidentes": [{"nome": r.nomeDeputado, "partido": r.siglaPartido,
                                                   "inicio": str(r.dataInicio)[:10]} for r in p_.itertuples()]})
    resumo = {"comissoes_permanentes": int(perm["siglaOrgao"].nunique()),
              "presidencias": [{"partido": r.siglaPartido, "n": int(r.presidencias), "deputados": _f(r.deputados, 0)}
                               for r in pres_part.itertuples()],
              "chave": chave, "apoio_gov_plenario": _f(plen),
              "comissoes": [{"sigla": r.siglaOrgao, "nome": r.nome, "titulares": int(r.titulares),
                             "apoio_gov": _f(r.apoio_gov), "diferenca": _f(r.diferenca)}
                            for r in por_com.sort_values("diferenca").itertuples()]}
    return resumo, perm


def rodar(c: dict, cfg: dict) -> int:
    leg = c["legislatura_atual"]
    if not legislatura_tem_dados(c):
        return 0
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/comissoes")
    saida.mkdir(parents=True, exist_ok=True)
    gdir = ROOT / c["redes"]["saida"].replace("/redes", "/governabilidade")
    votacoes, votos, orient, _ = carregar(c)
    vg = pd.read_parquet(gdir / "votacoes.parquet")
    gov_dep = pd.read_parquet(gdir / "deputados.parquet")
    gov_dep = gov_dep[gov_dep["votos_gov"] >= 30]
    nomes = nomes_deputados(c)
    votos = votos.rename(columns={"partido": "partido"})
    v_ = pd.read_parquet(path(c, "processed") / "votacoes", columns=["votacao_id", "descricao"])
    tp = _principal(c, votacoes)[["votacao_id"]].merge(
        pd.read_parquet(path(c, "processed") / "votacao_proposicao", columns=["votacao_id", "sigla_tipo"]), on="votacao_id")
    q = c["comissoes"]["quorum"]
    quorum = tp.groupby("votacao_id")["sigla_tipo"].agg(lambda t: max([q.get(x, 0) for x in t] or [0])).rename("quorum").reset_index()
    quorum = quorum.merge(v_, on="votacao_id", how="left")
    urg = quorum["descricao"].str.contains(r"Requerimento de Urg[eê]ncia \(Art\. 155", case=False, na=False)
    quorum.loc[urg, "quorum"] = q["urgencia"]
    # votações de PEC/PLP que não são a deliberação final (destaques, requerimentos) seguem maioria simples
    simples = quorum["descricao"].str.contains(r"Destaque|Requerimento|Emenda|Parecer", case=False, na=False) & ~urg
    quorum.loc[simples, "quorum"] = 0
    quorum["quorum"] = quorum["quorum"].replace(0, np.nan)
    por, rp, _ = pivos(c, vg, votos, orient, nomes, quorum[["votacao_id", "quorum"]])
    por.to_parquet(saida / "pivos.parquet", index=False)
    resumo = {"legislatura": leg, "pivos": rp}
    u, rel_dep, rel_part = urgencia_relatoria(c, cfg, votacoes, gov_dep, nomes)
    resumo["urgencia"] = u
    if rel_dep is not None:
        rel_dep.to_parquet(saida / "relatores.parquet", index=False)
        rel_part.to_parquet(saida / "relatorias_partido.parquet", index=False)
    com, perm = comissoes(c, cfg, leg, gov_dep, nomes)
    resumo["comissoes"] = com
    if perm is not None:
        perm.drop(columns=[x for x in ("apoio_gov",) if x in perm.columns]).to_parquet(saida / "membros.parquet", index=False)
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    relatorio(c, resumo, por, rel_dep, rel_part)
    return 0


def _pc(x, d=0):
    return "—" if x is None else f"{x * 100:.{d}f}%".replace(".", ",")


def relatorio(c, r, por, rel_dep, rel_part):
    leg = r["legislatura"]
    p = r["pivos"]
    L = [f"# Comissões, relatorias, urgência e pivôs — legislatura {leg}", "",
         "## Votações apertadas", "",
         f"- {n(p['apertadas'])} de {n(p['votacoes'])} votações nominais no Plenário tiveram diferença de até "
         f"{p['margem_votos']} votos do resultado virar (Sim × Não, ou Sim × quórum em PEC, PLP e urgência); em {n(p['decisivas'])} as dissidências do lado vencedor superaram a margem.",
         f"- Governo venceu {_pc(p['gov_venceu_apertadas'])} das apertadas ({_pc(p['gov_venceu_todas'])} de todas).", "",
         "### Quem mais votou contra o partido e ficou do lado vencedor nas apertadas", "",
         "| Deputado | Partido | Apertadas | Dissidências vencedoras | Em decisivas | Apoio ao governo (apertadas / todas) |",
         "| --- | --- | --- | --- | --- | --- |"]
    for x in por[por["apertadas"] >= 5].nlargest(15, "dissid_venc").itertuples():
        L.append(f"| {x.nome} | {x.partido} | {x.apertadas} | {x.dissid_venc} | {x.dissid_decisiva} | "
                 f"{_pc(x.apoio_gov_apertadas)} / {_pc(x.apoio_gov_todas)} |")
    u = r["urgencia"]
    L += ["", "## Urgência", "", "| Ano | Requerimentos de urgência votados | Votações nominais |", "| --- | --- | --- |"]
    L += [f"| {x['ano']} | {x['req']} | {x['votacoes']} |" for x in u["req_urgencia_ano"]]
    if "merito_urgencia_ano" in u:
        L += ["", "Votações de mérito sobre proposição em regime de urgência:", "",
              "| Ano | Em urgência | Votações de mérito |", "| --- | --- | --- |"]
        L += [f"| {x['ano']} | {x['urgencia']} ({_pc(x['urgencia'] / x['merito'] if x['merito'] else None)}) | {x['merito']} |"
              for x in u["merito_urgencia_ano"]]
        L += ["", "Tempo da apresentação à 1ª votação nominal no Plenário (mediana):", ""]
        L += [f"- {x['grupo']}: {n(x['mediana_dias'])} dias ({n(x['proposicoes'])} proposições)" for x in u["tempo_ate_votar"]]
        rl = u["relatorias"]
        L += ["", "## Relatorias de Plenário", "",
              f"- {n(rl['proposicoes_com_relator'])} de {n(rl['proposicoes_merito'])} proposições votadas têm relator "
              f"registrado; {n(rl['relatores'])} relatores diferentes.",
              f"- Apoio médio ao governo dos relatores: {_pc(rl['apoio_gov_relatores'])} (Plenário: {_pc(rl['apoio_gov_plenario'])}).",
              "", "| Partido | Relatorias | Fatia das relatorias | Fatia das cadeiras |", "| --- | --- | --- | --- |"]
        for x in rel_part.sort_values("relatorias", ascending=False).head(15).itertuples():
            L.append(f"| {x.partido} | {x.relatorias} | {_pc(x.frac_relatorias)} | {_pc(x.frac_deputados)} |")
        L += ["", "| Deputado | Partido | Relatorias |", "| --- | --- | --- |"]
        L += [f"| {x.nome} | {x.partido} | {x.relatorias} |" for x in rel_dep.nlargest(12, "relatorias").itertuples()]
    cm = r["comissoes"]
    if cm:
        L += ["", "## Comissões permanentes", "", f"- {cm['comissoes_permanentes']} comissões permanentes.", "",
              "| Partido | Presidências | Deputados |", "| --- | --- | --- |"]
        L += [f"| {x['partido']} | {x['n']} | {int(x['deputados']) if x['deputados'] else '—'} |" for x in cm["presidencias"][:15]]
        L += ["", "Comissões-chave:", ""]
        for x in cm["chave"]:
            L.append(f"- **{x['sigla']}**: " + ("; ".join(f"{p['nome']} ({p['partido']}, desde {p['inicio']})" for p in x["presidentes"]) or "—"))
        L += ["", "Apoio ao governo dos titulares × Plenário (comissões mais distantes):", "",
              "| Comissão | Titulares | Apoio | Diferença |", "| --- | --- | --- | --- |"]
        cs = cm["comissoes"]
        for x in cs[:6] + cs[-6:]:
            L.append(f"| {x['sigla']} | {x['titulares']} | {_pc(x['apoio_gov'])} | {'+' if x['diferenca'] > 0 else ''}{x['diferenca'] * 100:.1f} pp |".replace(".", ","))
    dest = ROOT / c["governabilidade"]["relatorio"].replace("governabilidade.md", "comissoes.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
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
