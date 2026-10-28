"""Ficha mensal de deputados acompanhados (lista em `acompanhar` no config).

Responde, mês a mês e para todas as legislaturas com dados:
  - segue a orientação do partido?  voto igual à orientação do próprio partido (ou federação/bloco,
    mesma hierarquia da Etapa 5);
  - vota com a maioria da bancada?  voto igual ao lado da maioria dos COLEGAS de partido na votação
    (o próprio deputado não entra na conta; precisa de `min_colegas` colegas com voto);
  - apoia o governo?               voto igual à orientação do Governo;
  - presença:                       votos registrados ÷ votações nominais em que estava em exercício.
Cada taxa vem com a média dos colegas de partido no mesmo mês, para comparação.
Aviso de bancada pequena: com menos de `min_colegas` colegas votando (mediana do mês), "segue o
partido" perde sentido (a orientação pode ser do próprio deputado, como líder).

"Rebeldias": votações em que votou contra a orientação do próprio partido (lista com proposição).

Identificação: `id` da Câmara quando existe; senão o nome parlamentar (sem acento, sem caixa) entre
os deputados da legislatura `desde_legislatura` em diante, conferido pela UF dos votos. Sem
correspondência única, o deputado aparece como "aguardando dados" (ex.: eleito que ainda não tomou posse).

Saídas em data/marts/camara/acompanhamento/: deputados.json, mensal.parquet, rebeldias.parquet.
Uso: python -m src.governance.acompanhamento
"""
from __future__ import annotations

import json
import sys
import unicodedata

import numpy as np
import pandas as pd

from src.config import ROOT, legislatura_tem_dados, load_config, path, por_legislatura
from src.governance.indicadores import base_votos, carregar, em_exercicio_historico, taxa
from src.networks.votacao import dec, n, pct


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def identificar(cfg, alvo: dict, votos: pd.DataFrame) -> tuple[str | None, str]:
    """(deputado_id, situação)."""
    if alvo.get("id"):
        return str(alvo["id"]), "ok"
    deps = pd.read_parquet(path(cfg, "processed") / "deputados")
    leg_min = int(alvo.get("desde_legislatura", 0))
    deps = deps[pd.to_numeric(deps["idLegislaturaFinal"], errors="coerce").fillna(0) >= leg_min]
    nomes = {_norm(x) for x in [alvo["nome"], *alvo.get("nomes_alternativos", [])]}
    cand = deps[deps["nome"].map(_norm).isin(nomes)]
    if alvo.get("uf") and len(cand):
        ufs = votos[votos["deputado_id"].isin(cand["deputado_id"])].groupby("deputado_id")["uf"].agg(
            lambda s: s.mode().iat[0] if len(s.mode()) else None)
        com_voto = set(ufs.index)
        cand = cand[cand["deputado_id"].map(ufs).eq(alvo["uf"]) | ~cand["deputado_id"].isin(com_voto)]
    if len(cand) == 1:
        return str(cand["deputado_id"].iat[0]), "ok"
    if len(cand) > 1:
        return None, f"nome ambíguo ({len(cand)} deputados); informe o id no config"
    return None, "aguardando dados (ainda sem registro na Câmara)"


def base_completa(cfg):
    votacoes, votos, orient, tipos = carregar(cfg)
    b, gov, _ = base_votos(cfg, votacoes, votos, orient)
    b["mes"] = pd.to_datetime(b["data"]).dt.to_period("M").dt.to_timestamp()
    # maioria dos colegas de partido (sem o próprio deputado)
    x = b[b["valor"].isin([1, -1])]
    soma = x.groupby(["votacao_id", "partido"])["valor"].agg(["sum", "size"])
    b = b.join(soma, on=["votacao_id", "partido"])
    proprio = b["valor"].where(b["valor"].isin([1, -1]), 0).fillna(0)
    b["colegas_soma"] = b["sum"].fillna(0) - proprio
    b["colegas_n"] = b["size"].fillna(0) - (proprio != 0)
    minimo = int(cfg.get("acompanhamento", {}).get("min_colegas", 3))
    ok = b["valor"].isin([1, -1]) & (b["colegas_n"] >= minimo) & (b["colegas_soma"] != 0)
    b["com_bancada"] = np.where(ok, np.sign(b["colegas_soma"]) == b["valor"], np.nan)
    b = b.drop(columns=["sum", "size"])
    exerc = em_exercicio_historico(cfg, votacoes)
    return votacoes, b, exerc


def mensal_deputado(dep_id: str, b: pd.DataFrame, votacoes: pd.DataFrame, exerc: pd.DataFrame) -> pd.DataFrame:
    meu = b[b["deputado_id"] == dep_id]
    if meu.empty:
        return pd.DataFrame()
    ex = exerc[exerc["deputado_id"] == dep_id].merge(votacoes[["votacao_id", "data"]], on="votacao_id")
    ex["mes"] = pd.to_datetime(ex["data"]).dt.to_period("M").dt.to_timestamp()
    em_ex = ex.groupby("mes").size().rename("votacoes_exercicio")
    m = meu.groupby("mes").agg(
        partido=("partido", lambda s: s.mode().iat[0] if len(s.mode()) else None),
        votos=("votacao_id", "nunique"),
        segue_partido=("disciplinado", taxa), n_segue_partido=("disciplinado", lambda s: s.notna().sum()),
        com_bancada=("com_bancada", taxa), n_com_bancada=("com_bancada", lambda s: s.notna().sum()),
        apoio_gov=("alinhado_gov", taxa), n_apoio_gov=("alinhado_gov", lambda s: s.notna().sum()),
        colegas=("colegas_n", "median"),
    ).join(em_ex, how="outer")
    m["presenca"] = m["votos"] / m["votacoes_exercicio"]
    # colegas do mesmo partido no mesmo mês
    pares = meu[["mes", "partido"]].drop_duplicates()
    col = b[b["deputado_id"] != dep_id].merge(pares, on=["mes", "partido"])
    cm = col.groupby("mes").agg(partido_segue_partido=("disciplinado", taxa), partido_com_bancada=("com_bancada", taxa),
                                partido_apoio_gov=("alinhado_gov", taxa))
    return m.join(cm).reset_index().assign(deputado_id=dep_id)


def rebeldias(dep_id: str, b: pd.DataFrame, cfg) -> pd.DataFrame:
    r = b[(b["deputado_id"] == dep_id) & (b["disciplinado"] == 0)]
    if r.empty:
        return pd.DataFrame()
    P = path(cfg, "processed")
    from src.config import connect
    con = connect(cfg)
    src = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    info = con.execute(f"""SELECT v.votacao_id, v.descricao,
                                  any_value(p.sigla_tipo || ' ' || p.numero || '/' || p.ano_apresentacao) AS proposicao,
                                  any_value(p.ementa) AS ementa
                           FROM {src('votacoes')} v
                           LEFT JOIN {src('votacao_proposicao')} vp USING (votacao_id)
                           LEFT JOIN {src('proposicoes')} p USING (proposicao_id)
                           WHERE v.votacao_id IN (SELECT unnest(?))
                           GROUP BY 1, 2""", [list(r["votacao_id"])]).df()
    inv = {1: "Sim", -1: "Não"}
    out = r.merge(info, on="votacao_id", how="left").assign(
        voto_dep=lambda x: x["voto"],
        orientacao_partido=lambda x: x["partido_valor"].map(inv),
        orientacao_governo=lambda x: x["gov_valor"].map(inv),
        com_bancada=lambda x: x["com_bancada"],
    )
    out["texto"] = out["ementa"].fillna(out["descricao"]).fillna("").str.split("\n").str[0].str[:220]
    return out[["deputado_id", "votacao_id", "data", "partido", "proposicao", "texto", "voto_dep",
                "orientacao_partido", "orientacao_governo", "com_bancada", "nivel_orientacao"]].sort_values(
        "data", ascending=False)


def contexto_legislaturas(cfg, dep_id: str) -> list[dict]:
    """Posição no mapa de cada legislatura com dados: eixo entre polos, comunidade, ranking de apoio."""
    out = []
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            continue
        g = ROOT / c["governabilidade"]["saida"] / "deputados.parquet"
        if not g.exists():
            continue
        gd = pd.read_parquet(g)
        if dep_id not in set(gd["deputado_id"]):
            continue
        linha = gd[gd["deputado_id"] == dep_id].iloc[0]
        pos = pd.read_parquet(ROOT / c["fatias"]["saida"] / "posicoes.parquet")
        pj = pos[(pos["tipo"] == "janela") & (pos["deputado_id"] == dep_id)].dropna(subset=["posicao"])
        validos = gd[gd["votos_gov"] >= 50]
        mp = ROOT / c["redes"]["saida"].replace("/redes", "/modelo") / "deputados.parquet"
        imp = {}
        if mp.exists():
            md = pd.read_parquet(mp)
            minimo = int(cfg.get("modelo", {}).get("min_votos_deputado", 100))
            if dep_id in set(md["deputado_id"]):
                r_ = md[md["deputado_id"] == dep_id].iloc[0]
                base_ = md[md["votos"] >= minimo]
                imp = {"imprevisibilidade": _f(r_["imprevisibilidade"]), "imprev_partido": _f(r_["imprev_partido"]),
                       "imprev_surpresas": int(r_["surpresas"]), "imprev_votos": int(r_["votos"]),
                       "imprev_posicao": int((base_["imprevisibilidade"] > r_["imprevisibilidade"]).sum()) + 1,
                       "imprev_total": int(len(base_))}
        ep = ROOT / c["redes"]["saida"].replace("/redes", "/emendas") / "parlamentares.parquet"
        if ep.exists():
            e_ = pd.read_parquet(ep)
            if dep_id in set(e_["deputado_id"]):
                r_ = e_[e_["deputado_id"] == dep_id].iloc[0]
                imp.update({"emendas_pago": _f(r_["pago"]), "emendas_execucao": _f(r_["execucao"]),
                            "emendas_base": _f(r_.get("frac_base")), "emendas_qtd": int(r_["emendas"])})
        out.append({**imp,
            "leg": leg, "governo": c["legislaturas"][leg].get("governo", ""), "partido": linha["partido"],
            "comunidade": linha["comunidade"], "apoio_gov": _f(linha["apoio_gov"]), "disciplina": _f(linha["disciplina"]),
            "participacao": _f(linha["participacao"]),
            "apoio_percentil": _f((validos["apoio_gov"] < linha["apoio_gov"]).mean()) if len(validos) else None,
            "posicao_media": _f(pj["posicao"].mean()) if len(pj) else None,
            "posicoes": [{"fim": f.split(" a ")[-1], "posicao": _f(p)} for f, p in zip(pj["fatia"], pj["posicao"])],
        })
    return out


def campanhas(cfg, alvo: dict, dep_id: str | None) -> list[dict]:
    """Perfil de campanha (TSE) do deputado em cada eleição disponível: pelo deputado_id ou por nome + UF."""
    from src.governance.eleicoes import _nome, perfil_eleicao
    t = cfg.get("tse")
    if not t:
        return []
    cargo = str(t["cargos"]["deputado_federal"])
    nomes = {_nome(x) for x in [alvo["nome"], *alvo.get("nomes_alternativos", [])]}
    out = []
    for ano in t["eleicoes"]:
        p = perfil_eleicao(int(ano), cfg)
        if p.empty:
            continue
        p = p[p["CD_CARGO"] == cargo]
        sel = p[p["deputado_id"] == dep_id] if dep_id else p.iloc[0:0]
        if sel.empty:
            urna, civil = p["NM_URNA_CANDIDATO"].map(_nome), p["NM_CANDIDATO"].map(_nome)
            sel = p[(urna.isin(nomes) | civil.isin(nomes)) & (p["SG_UF"] == alvo.get("uf", p["SG_UF"]))]
        if len(sel) != 1:
            continue
        r = sel.iloc[0]
        uf = p[p["SG_UF"] == r["SG_UF"]]
        out.append({"ano": int(ano), "partido": r["SG_PARTIDO"], "situacao": r["DS_SIT_TOT_TURNO"],
                    "votos": int(r["votos"]) if r["votos"] == r["votos"] else None, "frac_uf": _f(r["frac_uf"]),
                    "posicao_uf": int((uf["votos"] > r["votos"]).sum()) + 1, "candidatos_uf": int(len(uf)),
                    "municipio_principal": r.get("municipio_principal"), "maior_municipio": _f(r["maior_municipio"]),
                    "municipios_1pct": int(r["municipios_1pct"]) if r["municipios_1pct"] == r["municipios_1pct"] else None,
                    "receita_total": _f(r.get("receita_total")), "custo_por_voto": _f(r.get("custo_por_voto")),
                    "frac_fundo_eleitoral": _f(r.get("frac_fundo_eleitoral")),
                    "frac_pessoas_fisicas": _f(r.get("frac_pessoas_fisicas")),
                    "frac_recursos_proprios": _f(r.get("frac_recursos_proprios"))})
    return out


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(x) else round(x, 4)


def main() -> int:
    cfg = load_config()
    alvos = cfg.get("acompanhar", [])
    a = cfg.get("acompanhamento", {})
    saida = ROOT / a.get("saida", "data/marts/camara/acompanhamento")
    saida.mkdir(parents=True, exist_ok=True)
    if not alvos:
        print("Ninguém em `acompanhar`.")
        return 0
    votacoes, b, exerc = base_completa(cfg)
    fichas, mens, rebs = [], [], []
    for alvo in alvos:
        dep_id, situacao = identificar(cfg, alvo, b)
        ficha = {k: alvo.get(k) for k in ("nome", "uf", "partido_eleito", "nota", "eleicao")}
        ficha.update(deputado_id=dep_id, situacao=situacao, campanhas=campanhas(cfg, alvo, dep_id))
        if dep_id:
            m = mensal_deputado(dep_id, b, votacoes, exerc)
            r = rebeldias(dep_id, b, cfg)
            if m.empty:
                ficha["situacao"] = "identificado; ainda sem votos no Plenário"
            else:
                mens.append(m)
                meu = b[b["deputado_id"] == dep_id]
                ficha.update(
                    primeiro_voto=str(meu["data"].min())[:10], ultimo_voto=str(meu["data"].max())[:10],
                    votos=int(meu["votacao_id"].nunique()),
                    segue_partido=_f(taxa(meu["disciplinado"])), n_segue_partido=int(meu["disciplinado"].notna().sum()),
                    com_bancada=_f(taxa(meu["com_bancada"])), n_com_bancada=int(meu["com_bancada"].notna().sum()),
                    apoio_gov=_f(taxa(meu["alinhado_gov"])), n_apoio_gov=int(meu["alinhado_gov"].notna().sum()),
                    rebeldias=int(len(r)), partido_atual=meu.sort_values("data")["partido"].iat[-1],
                    meses_bancada_pequena=int((m["colegas"] < int(a.get("min_colegas", 3))).sum()),
                    bancada_pequena_atual=bool(m.dropna(subset=["colegas"])["colegas"].iat[-1] < int(a.get("min_colegas", 3))),
                    legislaturas=contexto_legislaturas(cfg, dep_id),
                )
                # média dos colegas de partido no período inteiro (mesmo partido de cada voto)
                pares = meu[["votacao_id", "partido"]]
                col = b[b["deputado_id"] != dep_id].merge(pares, on=["votacao_id", "partido"])
                ficha.update(partido_segue_partido=_f(taxa(col["disciplinado"])),
                             partido_com_bancada=_f(taxa(col["com_bancada"])),
                             partido_apoio_gov=_f(taxa(col["alinhado_gov"])))
            if not r.empty:
                rebs.append(r)
        fichas.append(ficha)
        print(f"{alvo['nome']}: {ficha['situacao']}" + (f" (id {dep_id})" if dep_id else ""))

    mensal = pd.concat(mens, ignore_index=True) if mens else pd.DataFrame()
    reb = pd.concat(rebs, ignore_index=True) if rebs else pd.DataFrame()
    mensal.to_parquet(saida / "mensal.parquet", index=False)
    reb.to_parquet(saida / "rebeldias.parquet", index=False)
    (saida / "deputados.json").write_text(json.dumps(fichas, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# Deputados acompanhados", "",
         "Segue o partido = voto igual à orientação do próprio partido. Com a bancada = voto igual à maioria dos "
         "colegas de partido. Entre parênteses: média dos colegas de partido nas mesmas votações.", ""]
    for f in fichas:
        L.append(f"## {f['nome']} ({f.get('uf') or '—'})")
        L.append("")
        if not f.get("votos"):
            L += [f"- Situação: {f['situacao']}", ""]
            continue
        L += [f"- Votos no Plenário: {n(f['votos'])} ({f['primeiro_voto']} a {f['ultimo_voto']}); partido atual: {f['partido_atual']}",
              f"- Segue a orientação do partido: {pct(round(f['segue_partido'] * f['n_segue_partido']), f['n_segue_partido'])}"
              f" (colegas: {dec(100 * (f['partido_segue_partido'] or 0), 1)}%)",
              f"- Vota com a maioria da bancada: {pct(round(f['com_bancada'] * f['n_com_bancada']), f['n_com_bancada'])}"
              f" (colegas: {dec(100 * (f['partido_com_bancada'] or 0), 1)}%)",
              f"- Apoio ao governo: {pct(round(f['apoio_gov'] * f['n_apoio_gov']), f['n_apoio_gov'])}"
              f" (colegas: {dec(100 * (f['partido_apoio_gov'] or 0), 1)}%)",
              f"- Votos contra a orientação do partido: {n(f['rebeldias'])}", ""]
        if f.get("bancada_pequena_atual"):
            L += ["- Aviso: a bancada atual tem menos de "
                  f"{a.get('min_colegas', 3)} colegas votando; 'segue o partido' pode refletir a orientação do próprio deputado.", ""]
        r = reb[reb["deputado_id"] == f["deputado_id"]].head(5) if len(reb) else []
        for _, x in (r.iterrows() if len(r) else []):
            L.append(f"  - {str(x['data'])[:10]} · {x['proposicao'] or ''} · votou {x['voto_dep']}, "
                     f"partido orientou {x['orientacao_partido']} · {x['texto'][:110]}")
        L.append("")
    rel = ROOT / a.get("relatorio", "artifacts/reports/acompanhamento.md")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
