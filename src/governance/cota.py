"""Cota parlamentar e patrimônio declarado (Bloco A), por casa e legislatura.

Cota (Câmara: CEAP; Senado: CEAPS), despesas dentro do período da legislatura:
  1. Gasto por parlamentar: total, por mês com despesa, por categoria.
  2. Ano eleitoral: divulgação no 1º semestre do ano da eleição ÷ 1º semestre do ano anterior, no mesmo
     parlamentar (a lei proíbe divulgação com a cota nos 120 dias antes da eleição, por isso o 1º semestre).
  3. Reeleição: entre quem se candidatou de novo, taxa de reeleição por quartil de gasto mensal com divulgação.
  4. Rede de fornecedores: pares de parlamentares que usam as mesmas empresas (CNPJ), sem os fornecedores que
     atendem mais de `cota.fornecedor_max_frac` dos parlamentares; comparada com a concordância de voto.
Patrimônio (TSE, bens declarados na candidatura), corrigido pelo IPCA para o último mês disponível:
  5. Bens declarados em cada eleição e a variação entre eleições do mesmo parlamentar.

Saídas em data/marts/<casa>/leg<N>/cota/. Uso: python -m src.governance.cota
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.config import ROOT, legislatura_tem_dados, load_config, para_senado, por_legislatura
from src.networks.votacao import dec, n, partido_modal, carregar_votos


def ipca(cfg: dict) -> pd.Series | None:
    p = ROOT / cfg["ibge"]["caminhos"]["staging"] / "ipca.parquet"
    if not p.exists():
        return None
    s = pd.read_parquet(p).set_index("mes")["indice"]
    return s


def fator_real(cfg: dict, ano: int, mes: int = 10) -> float:
    """Multiplica um valor nominal de (ano, mês) para trazê-lo a reais do último mês do IPCA."""
    s = ipca(cfg)
    if s is None:
        return 1.0
    k = f"{ano}{mes:02d}"
    if k not in s.index:
        return 1.0
    return float(s.iloc[-1] / s.loc[k])


def carregar_cota(cfg: dict, casa: str) -> pd.DataFrame:
    p = ROOT / cfg["cota"]["caminhos"]["staging"] / casa
    arqs = sorted(p.rglob("*.parquet"))
    if not arqs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a).assign(ano=int(a.parent.name.split("=")[1])) for a in arqs], ignore_index=True)
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df = df.dropna(subset=["mes"])
    df["mes"] = df["mes"].astype(int)
    df["data_mes"] = pd.to_datetime(df["ano"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2) + "-01")
    return df


def patrimonio(cfg: dict, casa: str, ids: set) -> pd.DataFrame:
    """Bens declarados por parlamentar e eleição (nominal e real)."""
    from src.governance.eleicoes import ligar_senado, perfil_eleicao
    t = cfg["tse"]
    cargo = str(t["cargos"]["senador" if casa == "senado" else "deputado_federal"])
    linhas = []
    for ano in t["eleicoes"]:
        d = ROOT / t["caminhos"]["staging"] / str(ano)
        if not (d / "bens.parquet").exists():
            continue
        cand = pd.read_parquet(d / "candidatos.parquet")
        cand = cand[cand["CD_CARGO"].isin([str(v) for v in t["cargos"].values()])]
        if casa == "senado":
            c_ = para_senado(cfg)
            perf = perfil_eleicao(int(ano), cfg)
            perf = perf[(perf["CD_CARGO"] == cargo) & perf["eleito"]]
            cand = perf.assign(deputado_id=ligar_senado(perf, {**c_, "tse": t}, float(t.get("semelhanca_minima", 0.75))))
        cand = cand.dropna(subset=["deputado_id"])
        cand = cand[cand["deputado_id"].isin(ids)]
        bens = pd.read_parquet(d / "bens.parquet").groupby("SQ_CANDIDATO")["valor"].sum()
        f = fator_real(cfg, int(ano), 8)
        for r in cand.itertuples():
            v = float(bens.get(r.SQ_CANDIDATO, 0.0))
            linhas.append({"deputado_id": r.deputado_id, "ano": int(ano), "bens": v, "bens_real": v * f,
                           "eleito": str(getattr(r, "DS_SIT_TOT_TURNO", "")).startswith("ELEITO")})
    return pd.DataFrame(linhas)


def rodar(c: dict, casa: str, cfg: dict) -> int:
    k = cfg["cota"]
    leg = c["legislatura_atual"]
    if not legislatura_tem_dados(c):
        return 0
    cota = carregar_cota(cfg, casa)
    if cota.empty:
        print(f"{casa} {leg}: sem dados da cota")
        return 0
    ini, fim = pd.Timestamp(c["redes"]["periodo"]["inicio"]), pd.Timestamp(c["redes"]["periodo"]["fim"])
    cota = cota[(cota["data_mes"] >= ini.replace(day=1)) & (cota["data_mes"] <= fim)]
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/cota")
    saida.mkdir(parents=True, exist_ok=True)
    g = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "deputados.parquet")
    ids = set(g["deputado_id"])
    cota = cota[cota["parlamentar_id"].isin(ids)]
    # reais de hoje
    s = ipca(cfg)
    if s is not None:
        fatores = (s.iloc[-1] / s).rename("f")
        cota["f"] = cota["data_mes"].dt.strftime("%Y%m").map(fatores).fillna(1.0)
    else:
        cota["f"] = 1.0
    cota["valor_real"] = cota["valor"] * cota["f"]
    div = cota["categoria"].str.upper().str.contains(k["divulgacao"], na=False)

    # 1. por parlamentar
    meses = cota.groupby("parlamentar_id")["data_mes"].nunique().rename("meses")
    dep = cota.groupby("parlamentar_id").agg(total=("valor", "sum"), total_real=("valor_real", "sum")).join(meses)
    dep["por_mes_real"] = dep["total_real"] / dep["meses"]
    dep["divulgacao_real"] = cota[div].groupby("parlamentar_id")["valor_real"].sum()
    dep["divulgacao_real"] = dep["divulgacao_real"].fillna(0)
    dep["frac_divulgacao"] = dep["divulgacao_real"] / dep["total_real"].replace(0, np.nan)
    cat = cota.groupby("categoria")["valor_real"].sum().sort_values(ascending=False)
    dep = dep.reset_index().rename(columns={"parlamentar_id": "deputado_id"}).merge(
        g[["deputado_id", "nome", "partido", "comunidade", "apoio_gov", "disciplina", "votos_gov"]], on="deputado_id", how="left")

    # 2. ano eleitoral (1º semestre do ano da eleição × 1º semestre do ano anterior)
    ano_el = int(fim.year) - 1 if fim.month == 1 else int(fim.year)
    sem = cota[div & (cota["mes"] <= 6)]
    a = sem[sem["ano"] == ano_el].groupby("parlamentar_id")["valor_real"].sum()
    b = sem[sem["ano"] == ano_el - 1].groupby("parlamentar_id")["valor_real"].sum()
    par = pd.concat([a.rename("eleicao"), b.rename("antes")], axis=1).fillna(0)
    par = par[(par["eleicao"] > 0) | (par["antes"] > 0)]
    eleitoral = {"ano_eleicao": ano_el, "parlamentares": int(len(par)),
                 "total_antes": float(par["antes"].sum()), "total_eleicao": float(par["eleicao"].sum()),
                 "aumentaram": int((par["eleicao"] > par["antes"]).sum()),
                 "mediana_razao": float((par["eleicao"] / par["antes"].replace(0, np.nan)).median())}
    mensal = cota.groupby(["data_mes"]).agg(total_real=("valor_real", "sum")).join(
        cota[div].groupby("data_mes")["valor_real"].sum().rename("divulgacao_real")).fillna(0).reset_index()
    mensal.to_parquet(saida / "mensal.parquet", index=False)

    # 3. reeleição (TSE da eleição que fecha a legislatura)
    reel = None
    pc = ROOT / cfg["tse"]["caminhos"]["staging"] / str(ano_el) / "candidatos.parquet"
    if pc.exists() and casa == "camara":
        cand = pd.read_parquet(pc)
        cand = cand[cand["CD_CARGO"] == str(cfg["tse"]["cargos"]["deputado_federal"])].dropna(subset=["deputado_id"])
        cand["reeleito"] = cand["DS_SIT_TOT_TURNO"].str.startswith("ELEITO", na=False)
        r_ = dep.merge(cand[["deputado_id", "reeleito"]].drop_duplicates("deputado_id"), on="deputado_id")
        if len(r_) >= 40:
            r_["div_mes"] = r_["divulgacao_real"] / r_["meses"]
            r_["quartil"] = pd.qcut(r_["div_mes"].rank(method="first"), 4, labels=["1º (menos)", "2º", "3º", "4º (mais)"])
            reel = r_.groupby("quartil", observed=True).agg(candidatos=("reeleito", "size"), reeleitos=("reeleito", "sum"),
                                                            gasto_mes=("div_mes", "median")).reset_index()
            reel["taxa"] = reel["reeleitos"] / reel["candidatos"]
            dep = dep.merge(r_[["deputado_id", "reeleito"]], on="deputado_id", how="left")

    # 4. rede de fornecedores
    f_ = cota.dropna(subset=["cnpj"])
    alcance = f_.groupby("cnpj")["parlamentar_id"].nunique()
    limite = max(int(k.get("min_parlamentares_fornecedor", 2)), int(len(dep) * float(k["fornecedor_max_frac"])))
    compart = alcance[(alcance >= int(k.get("min_parlamentares_fornecedor", 2))) & (alcance <= limite)].index
    ff = f_[f_["cnpj"].isin(compart)][["parlamentar_id", "cnpj"]].drop_duplicates()
    tam = ff.groupby("cnpj")["parlamentar_id"].transform("size")
    ff = ff.assign(w=1 / (tam - 1))
    pares = ff.merge(ff, on="cnpj")
    pares = pares[pares["parlamentar_id_x"] < pares["parlamentar_id_y"]]
    pares = pares.groupby(["parlamentar_id_x", "parlamentar_id_y"])["w_x"].sum().rename("peso").reset_index().rename(
        columns={"parlamentar_id_x": "deputado_a", "parlamentar_id_y": "deputado_b"})
    rede = {}
    pv = ROOT / c["redes"]["saida"] / "pares.parquet"
    if pv.exists() and len(pares):
        voto = pd.read_parquet(pv)
        voto = voto[voto["votacoes_comuns"] >= c["redes"]["min_votos_comuns"]]
        partido = partido_modal(carregar_votos(c))
        bse = voto.merge(pares, on=["deputado_a", "deputado_b"], how="left").fillna({"peso": 0})
        mesmo = bse["deputado_a"].map(partido).to_numpy() == bse["deputado_b"].map(partido).to_numpy()
        for rot, m in (("todos", np.ones(len(bse), bool)), ("mesmo partido", mesmo), ("partidos diferentes", ~mesmo)):
            sub = bse[m]
            com = sub[sub["peso"] > 0]["concordancia"]
            sem_ = sub[sub["peso"] == 0]["concordancia"]
            rho = spearmanr(sub["peso"], sub["concordancia"]).statistic if sub["peso"].nunique() > 2 else np.nan
            rede[rot] = {"pares": int(len(sub)), "ligados": int(len(com)), "conc_com": float(com.mean()) if len(com) else None,
                         "conc_sem": float(sem_.mean()) if len(sem_) else None, "spearman": float(rho)}
    top_forn = (f_[f_["cnpj"].isin(compart)].groupby(["cnpj"]).agg(
        fornecedor=("fornecedor", lambda x: x.mode().iat[0]), parlamentares=("parlamentar_id", "nunique"),
        valor_real=("valor_real", "sum")).sort_values("parlamentares", ascending=False).head(30).reset_index())
    partidos_f = f_[f_["cnpj"].isin(top_forn["cnpj"])][["cnpj", "parlamentar_id"]].drop_duplicates().merge(
        dep[["deputado_id", "partido"]].rename(columns={"partido": "partido_dep"}), left_on="parlamentar_id", right_on="deputado_id")
    top_forn["partidos"] = top_forn["cnpj"].map(partidos_f.groupby("cnpj")["partido_dep"].agg(
        lambda x: ", ".join(f"{p} {q}" for p, q in x.value_counts().head(3).items())))
    top_forn.to_parquet(saida / "fornecedores.parquet", index=False)
    pares.to_parquet(saida / "pares_fornecedores.parquet", index=False)

    # 5. patrimônio
    pat = patrimonio(cfg, casa, ids)
    pat.to_parquet(saida / "patrimonio.parquet", index=False)
    pat_res = {}
    if len(pat):
        w = pat.pivot_table(index="deputado_id", columns="ano", values="bens_real", aggfunc="max")
        for a1, a2 in zip(sorted(w.columns)[:-1], sorted(w.columns)[1:]):
            both = w[[a1, a2]].dropna()
            both = both[(both[a1] > 0) & (both[a2] > 0)]
            if len(both) >= 10:
                pat_res[f"{a1}-{a2}"] = {"n": int(len(both)), "mediana_razao_real": float((both[a2] / both[a1]).median()),
                                         "aumentaram": int((both[a2] > both[a1]).sum())}
        ult = pat.sort_values("ano").groupby("deputado_id").tail(1).set_index("deputado_id")
        dep["bens_real"] = dep["deputado_id"].map(ult["bens_real"])
        dep["bens_ano"] = dep["deputado_id"].map(ult["ano"])
    dep.to_parquet(saida / "parlamentares.parquet", index=False)

    resumo = {"casa": casa, "legislatura": leg, "parlamentares": int(len(dep)), "total_real": float(cota["valor_real"].sum()),
              "mediana_por_mes_real": float(dep["por_mes_real"].median()),
              "categorias": [{"categoria": i, "valor_real": float(v)} for i, v in cat.head(8).items()],
              "eleitoral": eleitoral, "reeleicao": reel.to_dict("records") if reel is not None else None,
              "rede": rede, "patrimonio": pat_res,
              "ipca_ate": str(s.index[-1]) if s is not None else None}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    nome_casa = "Senado" if casa == "senado" else "Câmara"
    L = [f"# Cota parlamentar e patrimônio — {nome_casa}, legislatura {leg}", "",
         f"Valores em reais de {resumo['ipca_ate']} (IPCA).", "",
         f"- Gasto total da cota: R$ {n(resumo['total_real'])}; mediana por parlamentar e mês: R$ {n(resumo['mediana_por_mes_real'])}",
         "", "## Maiores categorias", ""]
    for x in resumo["categorias"]:
        L.append(f"- {x['categoria']}: R$ {n(x['valor_real'])}")
    e = eleitoral
    L += ["", f"## Divulgação no 1º semestre de {e['ano_eleicao']} (ano eleitoral) × 1º semestre de {e['ano_eleicao'] - 1}", "",
          f"- Total: R$ {n(e['total_antes'])} → R$ {n(e['total_eleicao'])}",
          f"- {n(e['aumentaram'])} de {n(e['parlamentares'])} parlamentares gastaram mais; razão mediana: {dec(e['mediana_razao'] or 0, 2)}"]
    if reel is not None:
        L += ["", f"## Reeleição em {e['ano_eleicao']} por quartil de gasto mensal com divulgação (só quem se candidatou)", "",
              "| Quartil | Gasto mensal (mediana) | Reeleitos |", "| --- | --- | --- |"]
        for _, r in reel.iterrows():
            L.append(f"| {r['quartil']} | R$ {n(r['gasto_mes'])} | {n(r['reeleitos'])} de {n(r['candidatos'])} ({dec(100 * r['taxa'], 1)}%) |")
    if rede:
        L += ["", "## Fornecedores em comum × voto", "", "| Pares | Concordância com fornecedor em comum | Sem | Pares ligados |",
              "| --- | --- | --- | --- |"]
        for rot, v in rede.items():
            L.append(f"| {rot} | {dec(100 * (v['conc_com'] or 0), 1)}% | {dec(100 * (v['conc_sem'] or 0), 1)}% | {n(v['ligados'])} de {n(v['pares'])} |")
    if pat_res:
        L += ["", "## Patrimônio declarado (real, IPCA)", ""]
        for k_, v in pat_res.items():
            L.append(f"- {k_}: razão mediana {dec(v['mediana_razao_real'], 2)}; {n(v['aumentaram'])} de {n(v['n'])} aumentaram")
    L.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "cota")
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
