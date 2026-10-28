"""Emendas parlamentares × voto (Etapa 7d), por casa e legislatura.

Emendas individuais dos orçamentos que a legislatura votou (anos A+defasagem ... A+3+defasagem, A = ano de
início). Autor ligado ao parlamentar pelo nome (entre quem votou na legislatura). Pago = pago no ano + restos a
pagar pagos depois. Taxa de execução = pago ÷ empenhado (o governo decide o que paga).

Perguntas:
  1. Emendas e governo: pago e taxa de execução × apoio ao governo, disciplina, votos imprevisíveis
     (Spearman em todos e dentro do partido).
  2. Tempo: no mesmo parlamentar, meses com mais pagamento têm mais apoio ao governo? (cada série menos a média
     do próprio parlamentar; Spearman nos meses com votação orientada pelo governo).
  3. Conexão eleitoral: fração do valor pago que vai para municípios da base (1%+ dos votos do parlamentar) ×
     fração esperada se distribuísse pelos votos válidos da UF. Índice > 1 = privilegia a própria base.
  4. Necessidade: valor pago por habitante no município × PIB per capita, alfabetização, população.

Saídas em data/marts/<casa>/leg<N>/emendas/. Uso: python -m src.governance.emendas
"""
from __future__ import annotations

import difflib
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import ROOT, legislatura_tem_dados, load_config, para_senado, path, por_legislatura
from src.geo.municipios import ibge, norm, tse_para_ibge
from src.governance.indicadores import base_votos, carregar
from src.networks.votacao import dec, n


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                         errors="coerce").fillna(0)


def carregar_emendas(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    st = ROOT / cfg["emendas"]["caminhos"]["staging"]
    em = pd.read_parquet(st / "emendas.parquet")
    for c in ("valor_empenhado", "valor_liquidado", "valor_pago", "valor_restos_a_pagar_pagos",
              "valor_restos_a_pagar_inscritos", "valor_restos_a_pagar_cancelados"):
        if c in em:
            em[c] = _num(em[c])
    em["pago"] = em["valor_pago"] + em.get("valor_restos_a_pagar_pagos", 0)
    em["ano"] = pd.to_numeric(em["ano_da_emenda"], errors="coerce")
    em["cod_ibge"] = em["codigo_municipio_ibge"].where(em["codigo_municipio_ibge"].str.fullmatch(r"\d{7}", na=False))
    pag = pd.read_parquet(st / "pagamentos.parquet")
    return em, pag


def ligar_autores(em: pd.DataFrame, pool: pd.DataFrame, minimo: float) -> pd.Series:
    """nome do autor -> deputado_id, entre os parlamentares da legislatura (pool: deputado_id, nome)."""
    pool = pool.dropna(subset=["nome"]).copy()
    pool["n"] = pool["nome"].map(norm)
    exato = dict(zip(pool["n"], pool["deputado_id"]))
    out = {}
    for autor in em["nome_do_autor_da_emenda"].dropna().unique():
        a = norm(autor)
        if a in exato:
            out[autor] = exato[a]
            continue
        notas = pool["n"].map(lambda x: difflib.SequenceMatcher(None, x, a).ratio())
        if len(notas) and notas.max() >= minimo:
            out[autor] = pool.loc[notas.idxmax(), "deputado_id"]
    return pd.Series(out, dtype="object")


def base_eleitoral(cfg: dict, casa: str, leg: str) -> pd.DataFrame:
    """(deputado_id, cod_ibge, frac_votos, frac_uf_votos) dos eleitos da legislatura."""
    from src.governance.eleicoes import ligar_senado, perfil_eleicao
    t = cfg["tse"]
    anos = [int(a) for a, lg in t["legislatura_da_eleicao"].items() if lg == leg]
    if casa == "senado":
        anos += [int(a) for a, lg in t["legislatura_da_eleicao"].items() if str(int(lg) + 1) == leg]
    partes = []
    for ano in anos:
        d = ROOT / t["caminhos"]["staging"] / str(ano)
        if not (d / "votos_municipio.parquet").exists():
            continue
        vm = pd.read_parquet(d / "votos_municipio.parquet")
        perf = perfil_eleicao(ano, cfg)
        cargo = str(t["cargos"]["senador" if casa == "senado" else "deputado_federal"])
        perf = perf[(perf["CD_CARGO"] == cargo) & perf["eleito"]]
        if casa == "senado":
            c_ = para_senado(cfg)
            c_["legislatura_atual"] = leg
            perf = perf.assign(deputado_id=ligar_senado(perf, {**c_, "tse": t}, float(t.get("semelhanca_minima", 0.75))))
        vm = vm.merge(perf[["SQ_CANDIDATO", "deputado_id", "CD_CARGO"]].dropna(subset=["deputado_id"]), on="SQ_CANDIDATO")
        tot_mun = pd.read_parquet(d / "votos_municipio.parquet").merge(
            perfil_eleicao(ano, cfg)[["SQ_CANDIDATO", "CD_CARGO"]], on="SQ_CANDIDATO")
        tot_mun = tot_mun[tot_mun["CD_CARGO"] == cargo].groupby(["SG_UF", "CD_MUNICIPIO"])["votos"].sum().rename("votos_mun")
        cw = tse_para_ibge(cfg, vm)
        vm = vm.merge(cw, on="CD_MUNICIPIO", how="left").join(tot_mun, on=["SG_UF", "CD_MUNICIPIO"])
        vm["frac_votos"] = vm["votos"] / vm.groupby("deputado_id")["votos"].transform("sum")
        vm["frac_uf_votos"] = vm["votos_mun"] / vm.groupby("deputado_id")["votos_mun"].transform("sum")
        partes.append(vm[["deputado_id", "SG_UF", "cod_ibge", "NM_MUNICIPIO", "votos", "frac_votos", "frac_uf_votos"]])
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def apoio_mensal(c: dict) -> pd.DataFrame:
    votacoes, votos, orient, _ = carregar(c)
    b, _, _ = base_votos(c, votacoes, votos, orient)
    b["mes"] = pd.to_datetime(b["data"]).dt.to_period("M").astype(str).str.replace("-", "")
    return b.groupby(["deputado_id", "mes"]).agg(apoio=("alinhado_gov", "mean"), n=("alinhado_gov", lambda s: s.notna().sum())).reset_index()


def _sp(x, y):
    s = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(s) < 15 or s["x"].nunique() < 3:
        return np.nan, np.nan, len(s)
    r = spearmanr(s["x"], s["y"])
    return float(r.statistic), float(r.pvalue), len(s)


def rodar(c: dict, casa: str, cfg: dict) -> int:
    e = cfg["emendas"]
    leg = c["legislatura_atual"]
    if not legislatura_tem_dados(c):
        return 0
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/emendas")
    saida.mkdir(parents=True, exist_ok=True)
    em, pag = carregar_emendas(cfg)
    a0 = int(c["redes"]["periodo"]["inicio"][:4]) + int(e.get("defasagem_ano", 1))
    anos = list(range(a0, a0 + 4))
    em = em[em["ano"].isin(anos) & em["tipo_de_emenda"].isin(e["tipos_individuais"])].copy()

    g = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "deputados.parquet")
    mp = ROOT / c["redes"]["saida"].replace("/redes", "/modelo") / "deputados.parquet"
    if mp.exists():
        g = g.merge(pd.read_parquet(mp)[["deputado_id", "imprevisibilidade"]], on="deputado_id", how="left")
    autores = ligar_autores(em, g[["deputado_id", "nome"]], float(e.get("semelhanca_autor", 0.9)))
    em["deputado_id"] = em["nome_do_autor_da_emenda"].map(autores)
    lig = em.dropna(subset=["deputado_id"])

    # ---- por parlamentar
    dep = lig.groupby("deputado_id").agg(emendas=("codigo_da_emenda", "nunique"), empenhado=("valor_empenhado", "sum"),
                                         pago=("pago", "sum"),
                                         pago_municipio=("pago", lambda s: s[lig.loc[s.index, "cod_ibge"].notna()].sum()))
    dep["execucao"] = dep["pago"] / dep["empenhado"].replace(0, np.nan)
    base = base_eleitoral(cfg, casa, leg)
    if len(base):
        lim = float(e.get("base_minima", 0.01))
        b_ = base[base["frac_votos"] >= lim].dropna(subset=["cod_ibge"])
        chave = set(zip(b_["deputado_id"], b_["cod_ibge"]))
        lm = lig.dropna(subset=["cod_ibge"])
        lm = lm.assign(na_base=[(d, m) in chave for d, m in zip(lm["deputado_id"], lm["cod_ibge"])])
        dep["frac_base"] = lm.groupby("deputado_id").apply(lambda x: x.loc[x["na_base"], "pago"].sum() / max(x["pago"].sum(), 1))
        dep["frac_base_esperada"] = b_.groupby("deputado_id")["frac_uf_votos"].sum()
        dep["conexao"] = dep["frac_base"] / dep["frac_base_esperada"].replace(0, np.nan)
    dep = dep.reset_index().merge(g[["deputado_id", "nome", "partido", "comunidade", "apoio_gov", "disciplina", "votos_gov",
                                     *(["imprevisibilidade"] if "imprevisibilidade" in g else [])]], on="deputado_id", how="left")
    dep.to_parquet(saida / "parlamentares.parquet", index=False)

    # ---- 1. emendas × comportamento
    minimo = int(c.get("modelo", {}).get("min_votos_deputado", 100))
    d1 = dep[dep["votos_gov"].fillna(0) >= minimo].copy()
    linhas = []
    for x in ("pago", "execucao", "conexao", "frac_base"):
        if x not in d1:
            continue
        for y in ("apoio_gov", "disciplina", "imprevisibilidade"):
            if y not in d1:
                continue
            r, p, k = _sp(d1[x], d1[y])
            dd = d1[[x, y, "partido"]].dropna()
            dd = dd.groupby("partido").filter(lambda q: len(q) >= 3)
            rd, pd_, kd = _sp(dd[x] - dd.groupby("partido")[x].transform("median"), dd[y] - dd.groupby("partido")[y].transform("median"))
            linhas.append({"emendas": x, "comportamento": y, "spearman": r, "p": p, "n": k,
                           "spearman_dentro": rd, "p_dentro": pd_, "n_dentro": kd})
    corr = pd.DataFrame(linhas)
    corr.to_parquet(saida / "correlacoes.parquet", index=False)

    # ---- 2. tempo: pagamentos do mês × apoio do mês, no mesmo parlamentar
    pg = pag.merge(lig[["codigo_da_emenda", "deputado_id"]].drop_duplicates(), left_on="codigo_emenda", right_on="codigo_da_emenda")
    pg = pg.groupby(["deputado_id", "ano_mes"])["valor"].sum().rename("pago_mes").reset_index().rename(columns={"ano_mes": "mes"})
    am = apoio_mensal(c)
    am = am[am["n"] >= int(e.get("min_votos_mes", 3))]
    tm = am.merge(pg, on=["deputado_id", "mes"], how="left").fillna({"pago_mes": 0})
    tm["lp"] = np.log1p(tm["pago_mes"])
    tm = tm.groupby("deputado_id").filter(lambda q: len(q) >= 6 and q["lp"].nunique() > 1)
    xd = tm["lp"] - tm.groupby("deputado_id")["lp"].transform("mean")
    yd = tm["apoio"] - tm.groupby("deputado_id")["apoio"].transform("mean")
    rt, pt, kt = _sp(xd, yd)
    com = tm[tm["pago_mes"] > 0]["apoio"] - tm[tm["pago_mes"] > 0].groupby("deputado_id")["apoio"].transform("mean")
    mensal_total = pg.groupby("mes")["pago_mes"].sum().reset_index()
    mensal_total.to_parquet(saida / "pagamentos_mes.parquet", index=False)

    # ---- 3/4. municípios
    ib = ibge(cfg)
    mun = lig.dropna(subset=["cod_ibge"]).groupby("cod_ibge").agg(pago=("pago", "sum"), emendas=("codigo_da_emenda", "nunique"),
                                                                 autores=("deputado_id", "nunique")).reset_index()
    mun = ib.merge(mun, on="cod_ibge", how="left").fillna({"pago": 0, "emendas": 0, "autores": 0})
    mun["pago_per_capita"] = mun["pago"] / mun["pop_2022"]
    top = (lig.dropna(subset=["cod_ibge"]).groupby(["cod_ibge", "deputado_id"])["pago"].sum().reset_index()
           .sort_values("pago", ascending=False).groupby("cod_ibge").head(3))
    top.to_parquet(saida / "municipios_autores.parquet", index=False)
    lig.dropna(subset=["cod_ibge"]).groupby(["deputado_id", "cod_ibge"])["pago"].sum().reset_index().to_parquet(
        saida / "dep_municipio.parquet", index=False)
    mun.to_parquet(saida / "municipios.parquet", index=False)
    nec = []
    for x in ("pib_per_capita", "alfabetizacao", "pop_2022", "urbanizacao", "densidade"):
        if x in mun:
            r, p, k = _sp(mun[x], mun["pago_per_capita"])
            nec.append({"indicador": x, "spearman": r, "p": p, "n": k})
    nec = pd.DataFrame(nec)
    if len(base):
        base.to_parquet(saida / "base_eleitoral.parquet", index=False)

    resumo = {"casa": casa, "legislatura": leg, "anos_orcamento": anos, "emendas": int(lig["codigo_da_emenda"].nunique()),
              "autores_ligados": int(lig["deputado_id"].nunique()), "autores_total": int(em["nome_do_autor_da_emenda"].nunique()),
              "empenhado": float(lig["valor_empenhado"].sum()), "pago": float(lig["pago"].sum()),
              "execucao_mediana": float(dep["execucao"].median()), "conexao_mediana": float(dep["conexao"].median()) if "conexao" in dep else None,
              "frac_base_mediana": float(dep["frac_base"].median()) if "frac_base" in dep else None,
              "tempo": {"spearman": rt, "p": pt, "n": kt, "apoio_meses_com_pagamento": float(com.mean()) if len(com) else None},
              "necessidade": nec.to_dict("records"),
              "necessidade_pib": float(nec.set_index("indicador")["spearman"].get("pib_per_capita", np.nan)) if len(nec) else None}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    alfa = float(cfg["tse"].get("alfa", 0.01))
    nome_casa = "Senado" if casa == "senado" else "Câmara"
    L = [f"# Emendas parlamentares × Plenário — {nome_casa}, legislatura {leg}", "",
         f"Emendas individuais dos orçamentos {anos[0]}–{anos[-1]}: {n(resumo['emendas'])} emendas de "
         f"{n(resumo['autores_ligados'])} parlamentares ligados (de {n(resumo['autores_total'])} autores).", "",
         f"- Empenhado: R$ {n(resumo['empenhado'])}; pago: R$ {n(resumo['pago'])}",
         f"- Taxa de execução (mediana por parlamentar): {dec(100 * (resumo['execucao_mediana'] or 0), 1)}%"]
    if resumo["conexao_mediana"]:
        L.append(f"- Fração do pago para a base eleitoral (mediana): {dec(100 * resumo['frac_base_mediana'], 1)}%; "
                 f"conexão eleitoral (observado ÷ esperado, mediana): {dec(resumo['conexao_mediana'], 2)}")
    L += ["", "## Emendas × comportamento (Spearman)", "", "| Emendas | Comportamento | Todos | Dentro do partido | n |",
          "| --- | --- | --- | --- | --- |"]
    st_ = lambda v, p_: "—" if v != v else f"{dec(v, 2)}{'*' if p_ < alfa else ''}"  # noqa: E731
    for _, r in corr.iterrows():
        L.append(f"| {r['emendas']} | {r['comportamento']} | {st_(r['spearman'], r['p'])} | {st_(r['spearman_dentro'], r['p_dentro'])} | {n(r['n'])} |")
    L += ["", f"\\* p < {dec(alfa, 2)}.", "", "## Tempo: pagamento no mês × apoio ao governo no mês (mesmo parlamentar)", "",
          f"- Spearman (desvios da média do parlamentar): {st_(rt, pt)} em {n(kt)} parlamentar-meses",
          f"- Apoio nos meses com pagamento, em relação à média do próprio parlamentar: "
          f"{'—' if resumo['tempo']['apoio_meses_com_pagamento'] is None else dec(100 * resumo['tempo']['apoio_meses_com_pagamento'], 2) + ' p.p.'}",
          "", "## Para onde vai o dinheiro (por município, R$ pago por habitante)", ""]
    for _, r in nec.iterrows():
        L.append(f"- {r['indicador']}: {st_(r['spearman'], r['p'])}")
    L.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "emendas")
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
