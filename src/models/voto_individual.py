"""Modelo de voto individual e votos imprevisíveis (por legislatura).

Alvo: o deputado votou Sim (1) ou Não/Obstrução (0)? Só votos com valor da codificação principal.

Três modelos, do mais simples ao mais completo (cada um acrescenta informação ao anterior):
  M0 "segue o partido":   orientação do partido (se não houver, a maioria dos colegas de partido);
  M1 "partido e governo": orientação do partido, do governo, se o partido liberou, e como votaram os
                          colegas de partido e o restante do Plenário (sem o próprio deputado);
  M2 "perfil do deputado": M1 + histórico do deputado (apoio ao governo, disciplina, taxa de Sim,
                          medidos só nas votações de treino), grupo de votação e temas da votação.
M1 e M2: gradient boosting (HistGradientBoosting). Validação cruzada por votação (`folds` grupos):
toda votação é prevista por um modelo que nunca a viu, e o histórico do deputado vem só do treino.

Voto imprevisível: probabilidade prevista pelo M2 para o voto que de fato ocorreu abaixo de
`limiar_surpresa`. Índice de imprevisibilidade do deputado = fração dos seus votos imprevisíveis.

Saídas em data/marts/camara/leg<N>/modelo/.
Uso: python -m src.models.voto_individual
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from src.config import ROOT, connect, load_config, path
from src.governance.indicadores import base_votos, carregar
from src.networks.votacao import dec, n, nomes_deputados

M1_COLS = ["or_partido", "partido_orientou", "partido_liberou", "or_governo", "colegas_sim", "colegas_n", "plenario_sim"]
PERFIL = ["dep_apoio_gov", "dep_disciplina", "dep_sim", "dep_votos_treino"]


def _src(cfg, t):
    return f"read_parquet('{(path(cfg, 'processed') / t).as_posix()}/**/*.parquet', hive_partitioning = true)"


def montar_base(c: dict) -> tuple[pd.DataFrame, list[str]]:
    m = c.get("modelo", {})
    votacoes, votos, orient, tipos = carregar(c)
    b, gov, _ = base_votos(c, votacoes, votos, orient)
    b = b[b["valor"].isin([1, -1])].copy()
    b["y"] = (b["valor"] > 0).astype(int)
    b["or_partido"] = b["partido_valor"].fillna(0)
    b["partido_orientou"] = b["partido_valor"].notna().astype(int)
    b["partido_liberou"] = b["partido_liberou"].fillna(False).astype(int)
    b["or_governo"] = b["gov_valor"].fillna(0)
    # colegas de partido e restante do Plenário, sem o próprio deputado
    sp = b.groupby(["votacao_id", "partido"])["y"].agg(["sum", "size"])
    b = b.join(sp, on=["votacao_id", "partido"])
    b["colegas_n"] = b["size"] - 1
    b["colegas_sim"] = np.where(b["colegas_n"] > 0, (b["sum"] - b["y"]) / b["colegas_n"].clip(lower=1), np.nan)
    tot = b.groupby("votacao_id")["y"].agg(["sum", "size"]).rename(columns={"sum": "ts", "size": "tn"})
    b = b.join(tot, on="votacao_id")
    b["plenario_sim"] = (b["ts"] - b["sum"]) / (b["tn"] - b["size"]).clip(lower=1)
    b = b.drop(columns=["sum", "size", "ts", "tn"])
    # comunidade e temas
    com = pd.read_parquet(ROOT / c["redes"]["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]
    b["comunidade"] = b["deputado_id"].map(princ).fillna("fora").astype("category").cat.codes
    con = connect(c)
    vt = con.execute(f"""SELECT DISTINCT vp.votacao_id, t.tema FROM {_src(c, 'votacao_proposicao')} vp
                         JOIN {_src(c, 'proposicao_tema')} t USING (proposicao_id)""").df()
    vt = vt[vt["votacao_id"].isin(b["votacao_id"].unique())]
    top = vt["tema"].value_counts().head(int(m.get("temas", 12))).index
    dummies = pd.crosstab(vt["votacao_id"], vt["tema"])[list(top)].clip(upper=1)
    dummies.columns = [f"tema_{i}" for i in range(len(top))]
    b = b.join(dummies, on="votacao_id")
    tcols = list(dummies.columns)
    b[tcols] = b[tcols].fillna(0)
    b.attrs["temas"] = dict(zip(tcols, top))
    return b.reset_index(drop=True), tcols


def perfil(treino: pd.DataFrame) -> pd.DataFrame:
    g = treino.groupby("deputado_id")
    return pd.DataFrame({
        "dep_apoio_gov": g["alinhado_gov"].mean(),
        "dep_disciplina": g["disciplinado"].mean(),
        "dep_sim": g["y"].mean(),
        "dep_votos_treino": g.size(),
    })


def m0(b: pd.DataFrame) -> np.ndarray:
    """Probabilidade de Sim segundo a orientação do partido (suavizada) ou a maioria dos colegas."""
    eps = 0.05
    p = np.where(b["or_partido"] > 0, 1 - eps, np.where(b["or_partido"] < 0, eps, np.nan))
    p = np.where(np.isnan(p), b["colegas_sim"].fillna(0.5).clip(eps, 1 - eps), p)
    return p


def rodar(c: dict) -> int:
    m = c.get("modelo", {})
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/modelo")
    saida.mkdir(parents=True, exist_ok=True)
    b, tcols = montar_base(c)
    m2_cols = M1_COLS + PERFIL + ["comunidade"] + tcols
    params = dict(max_iter=int(m.get("iteracoes", 300)), learning_rate=float(m.get("taxa_aprendizado", 0.1)),
                  max_leaf_nodes=31, random_state=0)
    p1 = np.full(len(b), np.nan)
    p2 = np.full(len(b), np.nan)
    imp = []
    gkf = GroupKFold(n_splits=int(m.get("folds", 5)))
    for k, (tr, te) in enumerate(gkf.split(b, groups=b["votacao_id"])):
        treino, teste = b.iloc[tr], b.iloc[te]
        pf = perfil(treino)
        Xtr = treino.join(pf, on="deputado_id")
        Xte = teste.join(pf, on="deputado_id")
        mod1 = HistGradientBoostingClassifier(**params).fit(Xtr[M1_COLS], treino["y"])
        p1[te] = mod1.predict_proba(Xte[M1_COLS])[:, 1]
        mod2 = HistGradientBoostingClassifier(**params, categorical_features=[m2_cols.index("comunidade")]).fit(
            Xtr[m2_cols], treino["y"])
        p2[te] = mod2.predict_proba(Xte[m2_cols])[:, 1]
        if k == 0:
            amostra = Xte.sample(min(len(Xte), int(m.get("amostra_importancia", 20000))), random_state=0)
            pi = permutation_importance(mod2, amostra[m2_cols], amostra.loc[amostra.index, "y"], n_repeats=3,
                                        random_state=0, scoring="neg_log_loss")
            imp = pd.DataFrame({"variavel": m2_cols, "importancia": pi.importances_mean})
    p0 = m0(b)
    y = b["y"].to_numpy()

    def met(p):
        p = np.clip(p, 1e-4, 1 - 1e-4)
        return {"acerto": float(((p >= .5) == y).mean()), "auc": float(roc_auc_score(y, p)), "logloss": float(log_loss(y, p))}

    metr = {"M0": met(p0), "M1": met(p1), "M2": met(p2)}
    b["p_sim"] = p2
    b["p_obs"] = np.where(y == 1, p2, 1 - p2)
    lim = float(m.get("limiar_surpresa", 0.2))
    b["surpresa"] = b["p_obs"] < lim
    # contra o partido e imprevisível (o tipo mais interessante)
    b["contra_partido"] = (b["partido_valor"].notna()) & (b["valor"] != b["partido_valor"])

    nomes = nomes_deputados(c).set_index("deputado_id")["nome"]
    dep = b.groupby("deputado_id").agg(
        votos=("y", "size"), surpresas=("surpresa", "sum"), contra_partido=("contra_partido", "sum"),
        p_obs_media=("p_obs", "mean"),
        partido=("partido", lambda s: s.mode().iat[0] if len(s.mode()) else None)).reset_index()
    dep["imprevisibilidade"] = dep["surpresas"] / dep["votos"]
    dep["nome"] = dep["deputado_id"].map(nomes)
    # comparação com colegas de partido
    part = dep[dep["votos"] >= int(m.get("min_votos_deputado", 100))].groupby("partido")["imprevisibilidade"].median()
    dep["imprev_partido"] = dep["partido"].map(part)
    dep.to_parquet(saida / "deputados.parquet", index=False)

    # surpresas por tema e por mês
    temas = []
    for col, nome in b.attrs["temas"].items():
        s = b[b[col] > 0]
        temas.append({"tema": nome, "votos": int(len(s)), "imprevisibilidade": float(s["surpresa"].mean())})
    temas = pd.DataFrame(temas).sort_values("imprevisibilidade", ascending=False)
    temas.to_parquet(saida / "temas.parquet", index=False)
    b["mes"] = pd.to_datetime(b["data"]).dt.to_period("M").dt.to_timestamp()
    mensal = b.groupby("mes").agg(votos=("y", "size"), imprevisibilidade=("surpresa", "mean")).reset_index()
    mensal.to_parquet(saida / "mensal.parquet", index=False)

    # votações com mais votos imprevisíveis
    P = path(c, "processed")
    con = connect(c)
    info = con.execute(f"""SELECT v.votacao_id, v.data, v.descricao,
                                  any_value(p.sigla_tipo || ' ' || p.numero || '/' || p.ano_apresentacao) AS proposicao,
                                  any_value(p.ementa) AS ementa
                           FROM {_src(c, 'votacoes')} v
                           LEFT JOIN {_src(c, 'votacao_proposicao')} vp USING (votacao_id)
                           LEFT JOIN {_src(c, 'proposicoes')} p USING (proposicao_id)
                           GROUP BY 1, 2, 3""").df().set_index("votacao_id")
    vv = b.groupby("votacao_id").agg(votos=("y", "size"), surpresas=("surpresa", "sum")).query("votos >= 100")
    vv["frac"] = vv["surpresas"] / vv["votos"]
    vv = vv.sort_values("surpresas", ascending=False).head(int(m.get("top_votacoes", 15))).join(info, how="left")
    vv["texto"] = vv["ementa"].fillna(vv["descricao"]).fillna("").str.split("\n").str[0].str[:200]
    vv.reset_index()[["votacao_id", "data", "proposicao", "texto", "votos", "surpresas", "frac"]].to_parquet(
        saida / "votacoes.parquet", index=False)
    # votos imprevisíveis por deputado (para a ficha): os mais surpreendentes
    sv = b[b["surpresa"]].nsmallest(int(m.get("top_surpresas", 4000)), "p_obs")[
        ["deputado_id", "votacao_id", "data", "partido", "voto", "partido_valor", "gov_valor", "p_obs"]]
    sv.to_parquet(saida / "surpresas.parquet", index=False)

    nomes_imp = {**{k: k for k in M1_COLS + PERFIL + ["comunidade"]}, **{k: f"tema: {v}" for k, v in b.attrs["temas"].items()}}
    imp["variavel"] = imp["variavel"].map(nomes_imp)
    imp.sort_values("importancia", ascending=False).to_parquet(saida / "importancias.parquet", index=False)

    resumo = {"votos": int(len(b)), "votacoes": int(b["votacao_id"].nunique()), "deputados": int(b["deputado_id"].nunique()),
              "metricas": metr, "limiar_surpresa": lim, "surpresas": int(b["surpresa"].sum()),
              "imprevisibilidade": float(b["surpresa"].mean()),
              "surpresas_contra_partido": float(b.loc[b["surpresa"], "contra_partido"].mean())}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    rot = {"M0": "segue o partido", "M1": "partido, governo e colegas", "M2": "+ perfil do deputado e tema"}
    L = ["# Modelo de voto individual", "",
         f"{n(len(b))} votos (Sim × Não/Obstrução) em {n(resumo['votacoes'])} votações. Validação cruzada por votação "
         f"({m.get('folds', 5)} grupos).", "",
         "| Modelo | Acerto | AUC | Log-loss |", "| --- | --- | --- | --- |"]
    for k, v in metr.items():
        L.append(f"| {k} · {rot[k]} | {dec(100 * v['acerto'], 1)}% | {dec(v['auc'], 3)} | {dec(v['logloss'], 3)} |")
    L += ["", f"Votos imprevisíveis (probabilidade do voto observado abaixo de {dec(100 * lim, 0)}%): "
          f"{n(resumo['surpresas'])} ({dec(100 * resumo['imprevisibilidade'], 1)}%); "
          f"{dec(100 * resumo['surpresas_contra_partido'], 1)}% deles contra a orientação do partido.", "",
          "## O que mais pesa na previsão (M2)", ""]
    for _, r in imp.sort_values("importancia", ascending=False).head(8).iterrows():
        L.append(f"- {r['variavel']}: {dec(r['importancia'], 4)}")
    base_rank = dep[dep["votos"] >= int(m.get("min_votos_deputado", 100))]
    L += ["", "## Mais imprevisíveis (100+ votos)", ""]
    for _, r in base_rank.nlargest(10, "imprevisibilidade").iterrows():
        L.append(f"- {r['nome']} ({r['partido']}): {dec(100 * r['imprevisibilidade'], 1)}% de {n(r['votos'])} votos "
                 f"(mediana do partido: {dec(100 * (r['imprev_partido'] or 0), 1)}%)")
    L += ["", "## Temas com mais votos imprevisíveis", ""]
    for _, r in temas.head(6).iterrows():
        L.append(f"- {r['tema']}: {dec(100 * r['imprevisibilidade'], 1)}% de {n(r['votos'])} votos")
    L.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "modelo")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


def main() -> int:
    from src.config import legislatura_tem_dados, por_legislatura

    cfg = load_config()
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            continue
        print(f"===== legislatura {leg} =====")
        rodar(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
