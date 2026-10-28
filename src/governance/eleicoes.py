"""Campanha × comportamento no Plenário (Etapa 7c), por casa e legislatura.

Para cada parlamentar eleito (TSE, `tse.legislatura_da_eleicao`):
  - votos: total, fração dos votos válidos nominais do cargo na UF, peso do maior município, número de
    municípios com 1%+ dos votos dele, concentração (índice de Herfindahl entre municípios);
  - eleito pelo quociente partidário (votação própria) ou pela média (sobras);
  - receitas: total, custo por voto e fração por origem (fundo eleitoral, fundo partidário, pessoas físicas,
    recursos próprios, partido, outros candidatos, financiamento coletivo).
Cruza com o comportamento na legislatura: apoio ao governo, disciplina, participação, votos imprevisíveis,
posição no eixo entre polos.

Ligação: Câmara pelo deputado_id gravado na ingestão (nome civil + nascimento); Senado pelo nome de urna e
UF entre os eleitos (semelhança de texto, no mínimo `tse.semelhanca_minima`).

Comparações (Spearman): em todos e DENTRO do partido (cada variável menos a mediana do partido), para não
confundir efeito de partido com efeito de campanha.

Saídas em data/marts/<casa>/leg<N>/eleicao/. Uso: python -m src.governance.eleicoes
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import ROOT, legislatura_tem_dados, load_config, para_senado, path, por_legislatura
from src.networks.votacao import dec, n

ORIGENS = {
    "fundo_eleitoral": ("fonte", r"FUNDO ESPECIAL"),
    "fundo_partidario": ("fonte", r"FUNDO PARTID"),
    "pessoas_fisicas": ("origem", r"pessoas f[ií]sicas"),
    "recursos_proprios": ("origem", r"pr[oó]prios"),
    "financiamento_coletivo": ("origem", r"coletivo"),
    "outros_candidatos": ("origem", r"outros candidatos"),
}
COMPORTAMENTO = ["apoio_gov", "disciplina", "participacao", "imprevisibilidade", "posicao"]
CAMPANHA = ["votos", "frac_uf", "maior_municipio", "concentracao", "municipios_1pct", "eleito_qp",
            "receita_total", "custo_por_voto", "frac_fundo_eleitoral", "frac_pessoas_fisicas", "frac_recursos_proprios"]
ROTULO = {"votos": "votos", "frac_uf": "% dos votos da UF", "maior_municipio": "peso do maior município",
          "concentracao": "concentração geográfica", "municipios_1pct": "municípios com 1%+ dos votos",
          "eleito_qp": "eleito pela votação própria (QP)", "receita_total": "receita total",
          "custo_por_voto": "custo por voto", "frac_fundo_eleitoral": "% do fundo eleitoral",
          "frac_pessoas_fisicas": "% de pessoas físicas", "frac_recursos_proprios": "% de recursos próprios",
          "apoio_gov": "apoio ao governo", "disciplina": "disciplina", "participacao": "participação",
          "imprevisibilidade": "votos imprevisíveis", "posicao": "posição no eixo (A → B)"}


def _nome(x) -> str:
    s = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z ]", " ", s).split())


def perfil_eleicao(ano: int, cfg: dict) -> pd.DataFrame:
    d = ROOT / cfg["tse"]["caminhos"]["staging"] / str(ano)
    if not (d / "candidatos.parquet").exists():
        return pd.DataFrame()
    cand = pd.read_parquet(d / "candidatos.parquet")
    vm = pd.read_parquet(d / "votos_municipio.parquet")
    rec = pd.read_parquet(d / "receitas.parquet")
    cand["eleito"] = cand["DS_SIT_TOT_TURNO"].str.startswith("ELEITO", na=False)
    cand["eleito_qp"] = cand["DS_SIT_TOT_TURNO"].eq("ELEITO POR QP").astype(float)
    cand.loc[cand["DS_SIT_TOT_TURNO"].eq("ELEITO") | ~cand["eleito"], "eleito_qp"] = np.nan  # senador: não se aplica

    vm = vm.merge(cand[["SQ_CANDIDATO", "CD_CARGO"]], on="SQ_CANDIDATO").rename(columns={"votos": "vm"})
    tot = vm.groupby("SQ_CANDIDATO")["vm"].sum().rename("votos")
    uf = vm.groupby(["SG_UF", "CD_CARGO"])["vm"].sum().rename("uf_total")
    vm = vm.join(tot.rename("tot"), on="SQ_CANDIDATO")
    vm["share"] = vm["vm"] / vm["tot"].replace(0, np.nan)
    geo = vm.groupby("SQ_CANDIDATO").agg(maior_municipio=("share", "max"), concentracao=("share", lambda s: float((s ** 2).sum())),
                                         municipios_1pct=("share", lambda s: int((s >= 0.01).sum())))
    top = vm.sort_values("vm", ascending=False).drop_duplicates("SQ_CANDIDATO").set_index("SQ_CANDIDATO")["NM_MUNICIPIO"]
    p = cand.set_index("SQ_CANDIDATO").join(tot).join(geo)
    p["municipio_principal"] = top
    p = p.join(uf, on=["SG_UF", "CD_CARGO"])
    p["frac_uf"] = p["votos"] / p["uf_total"]

    if len(rec):
        rec = rec.copy()
        r = rec.groupby("SQ_CANDIDATO")["valor"].sum().rename("receita_total").to_frame()
        for nome, (campo, padrao) in ORIGENS.items():
            col = "DS_FONTE_RECEITA" if campo == "fonte" else "DS_ORIGEM_RECEITA"
            m = rec[col].fillna("").str.contains(padrao, case=False, regex=True)
            r[f"rec_{nome}"] = rec[m].groupby("SQ_CANDIDATO")["valor"].sum()
        r = r.fillna(0)
        for nome in ORIGENS:
            r[f"frac_{nome}"] = r[f"rec_{nome}"] / r["receita_total"].replace(0, np.nan)
        p = p.join(r)
    p["custo_por_voto"] = p.get("receita_total") / p["votos"].replace(0, np.nan)
    p["ano_eleicao"] = ano
    return p.reset_index()


def ligar_senado(perfil: pd.DataFrame, c: dict, minimo: float) -> pd.Series:
    """deputado_id (código do senador) por nome de urna + UF, entre os senadores eleitos."""
    sen = pd.read_parquet(path(c, "processed") / "deputados")
    sen["n"] = sen["nome"].map(_nome)
    out = {}
    for i, r in perfil[perfil["CD_CARGO"] == str(c["tse"]["cargos"]["senador"])].iterrows():
        cands = sen[sen["uf"] == r["SG_UF"]]
        if cands.empty:
            continue
        alvo = [_nome(r["NM_URNA_CANDIDATO"]), _nome(r["NM_CANDIDATO"])]
        notas = cands["n"].map(lambda x: max(difflib.SequenceMatcher(None, x, a).ratio() for a in alvo))
        if notas.max() >= minimo:
            out[i] = cands.loc[notas.idxmax(), "deputado_id"]
    return pd.Series(out, dtype="object")


def rodar(c: dict, casa: str, cfg_base: dict) -> int:
    t = cfg_base["tse"]
    leg = c["legislatura_atual"]
    cargo = str(t["cargos"]["senador" if casa == "senado" else "deputado_federal"])
    anos = [int(a) for a, lg in t["legislatura_da_eleicao"].items() if lg == leg]
    if casa == "senado":  # senador eleito serve duas legislaturas
        anos += [int(a) for a, lg in t["legislatura_da_eleicao"].items() if str(int(lg) + 1) == leg]
    perf = pd.concat([perfil_eleicao(a, cfg_base) for a in sorted(set(anos))], ignore_index=True)
    if perf.empty:
        print(f"{casa} {leg}: sem dados do TSE")
        return 0
    perf = perf[(perf["CD_CARGO"] == cargo) & perf["eleito"]].copy()
    if casa == "senado":
        perf["deputado_id"] = ligar_senado(perf, {**c, "tse": t}, float(t.get("semelhanca_minima", 0.75)))
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/eleicao")
    saida.mkdir(parents=True, exist_ok=True)

    tem_comportamento = legislatura_tem_dados(c) and (ROOT / c["governabilidade"]["saida"] / "deputados.parquet").exists()
    base = perf.copy()
    if tem_comportamento:
        g = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "deputados.parquet")
        mp = ROOT / c["redes"]["saida"].replace("/redes", "/modelo") / "deputados.parquet"
        if mp.exists():
            g = g.merge(pd.read_parquet(mp)[["deputado_id", "imprevisibilidade", "votos"]].rename(
                columns={"votos": "votos_plenario"}), on="deputado_id", how="left")
        pos = pd.read_parquet(ROOT / c["fatias"]["saida"] / "posicoes.parquet")
        g["posicao"] = g["deputado_id"].map(pos[pos["tipo"] == "janela"].groupby("deputado_id")["posicao"].mean())
        base = perf.merge(g.drop(columns=["nome"], errors="ignore"), on="deputado_id", how="left",
                          suffixes=("", "_plen"))
    base.drop(columns=[c_ for c_ in ("SQ_CANDIDATO", "NM_CANDIDATO") if c_ in base], errors="ignore").to_parquet(
        saida / "parlamentares.parquet", index=False)

    ligados = int(base["deputado_id"].notna().sum())
    linhas = []
    if tem_comportamento:
        minimo = int(c.get("modelo", {}).get("min_votos_deputado", 100))
        b = base[base["votos_gov"].fillna(0) >= minimo].copy()
        partido = b["partido"].fillna(b["SG_PARTIDO"])
        for x in CAMPANHA:
            if x not in b:
                continue
            for y in COMPORTAMENTO:
                if y not in b:
                    continue
                s = b[[x, y]].assign(p=partido).dropna()
                if len(s) < 15 or s[x].nunique() < 3:
                    continue
                rr = spearmanr(s[x], s[y])
                rho, pv = rr.statistic, rr.pvalue
                dentro = s.groupby("p").filter(lambda g_: len(g_) >= 3)
                xd = dentro[x] - dentro.groupby("p")[x].transform("median")
                yd = dentro[y] - dentro.groupby("p")[y].transform("median")
                rd = spearmanr(xd, yd) if len(dentro) >= 15 and xd.nunique() > 2 else None
                rho_d, pv_d = (rd.statistic, rd.pvalue) if rd is not None else (np.nan, np.nan)
                linhas.append({"campanha": x, "comportamento": y, "n": len(s), "spearman": float(rho), "p": float(pv),
                               "spearman_dentro_partido": float(rho_d), "p_dentro": float(pv_d), "n_dentro": len(dentro)})
    corr = pd.DataFrame(linhas)
    corr.to_parquet(saida / "correlacoes.parquet", index=False)

    qp = None
    if tem_comportamento and casa == "camara":
        bb = base[base["votos_gov"].fillna(0) >= int(c.get("modelo", {}).get("min_votos_deputado", 100))]
        qp = bb.groupby("eleito_qp")[["apoio_gov", "disciplina", "imprevisibilidade", "participacao"]].median().to_dict("index")
    resumo = {"casa": casa, "legislatura": leg, "eleicoes": sorted(set(anos)), "eleitos": int(len(perf)),
              "ligados": ligados, "com_comportamento": bool(tem_comportamento),
              "mediana_votos": float(perf["votos"].median()), "mediana_receita": float(perf["receita_total"].median()) if "receita_total" in perf else None,
              "mediana_custo_por_voto": float(perf["custo_por_voto"].median()),
              "mediana_frac_fundo_eleitoral": float(perf["frac_fundo_eleitoral"].median()) if "frac_fundo_eleitoral" in perf else None,
              "eleitos_qp": int((perf["eleito_qp"] == 1).sum()), "eleitos_media": int((perf["eleito_qp"] == 0).sum()),
              "qp_vs_media": {str(k): v for k, v in qp.items()} if qp else None}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    nome_casa = "Senado" if casa == "senado" else "Câmara"
    L = [f"# Campanha × Plenário — {nome_casa}, legislatura {leg}", "",
         f"Eleições: {', '.join(map(str, resumo['eleicoes']))}. {n(len(perf))} eleitos; {n(ligados)} ligados aos dados do Plenário.", "",
         f"- Votos (mediana): {n(resumo['mediana_votos'])}",
         f"- Receita de campanha (mediana): R$ {n(resumo['mediana_receita'] or 0)}",
         f"- Custo por voto (mediana): R$ {dec(resumo['mediana_custo_por_voto'], 2)}",
         f"- Fração do fundo eleitoral na receita (mediana): {dec(100 * (resumo['mediana_frac_fundo_eleitoral'] or 0), 1)}%"]
    if casa == "camara":
        L.append(f"- Eleitos pela votação própria (QP): {n(resumo['eleitos_qp'])}; pela média: {n(resumo['eleitos_media'])}")
    if len(corr):
        alfa = float(t.get("alfa", 0.01))
        L += ["", f"## Campanha e comportamento (Spearman; só relações com p < {dec(alfa, 2)} em todos ou dentro do partido)", "",
              f"São {n(len(corr))} comparações: com p < {dec(alfa, 2)}, cerca de {dec(alfa * len(corr), 1)} apareceriam por acaso.", "",
              "| Campanha | Comportamento | Todos | Dentro do partido | n |", "| --- | --- | --- | --- | --- |"]
        forte = corr[(corr["p"] < alfa) | (corr["p_dentro"] < alfa)]
        for _, r in forte.sort_values("spearman_dentro_partido", key=abs, ascending=False).iterrows():
            st_ = lambda v, p_: f"{dec(v, 2)}{'*' if p_ < alfa else ''}"  # noqa: E731
            L.append(f"| {ROTULO[r['campanha']]} | {ROTULO[r['comportamento']]} | {st_(r['spearman'], r['p'])} | "
                     f"{st_(r['spearman_dentro_partido'], r['p_dentro'])} | {n(r['n'])} |")
        L.append("")
        L.append(f"\\* p < {dec(alfa, 2)}.")
    if qp:
        L += ["", "## Eleitos pela votação própria (QP) × pela média (medianas)", "",
              "| | Apoio ao governo | Disciplina | Votos imprevisíveis | Participação |", "| --- | --- | --- | --- | --- |"]
        for k, v in qp.items():
            rot = "Votação própria (QP)" if k == 1 else "Média (sobras)"
            L.append(f"| {rot} | {dec(100 * v['apoio_gov'], 1)}% | {dec(100 * v['disciplina'], 1)}% | "
                     f"{dec(100 * v['imprevisibilidade'], 1)}% | {dec(100 * v['participacao'], 1)}% |")
    L.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "eleicao")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


def main() -> int:
    cfg = load_config()
    for casa, base in (("camara", cfg), ("senado", para_senado(cfg))):
        for leg, c in por_legislatura(base):
            print(f"===== {casa} · legislatura {leg} =====")
            rodar(c, casa, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
