"""Rede em várias camadas: voto, frentes parlamentares e coautoria (por legislatura).

Camadas (pares de deputados):
  - voto:      concordância de voto (Etapa 3, pares.parquet);
  - frentes:   peso de co-participação em frentes = soma, nas frentes que os dois integram, de 1/(membros − 1)
               (frente com 300 membros pesa pouco; com 15, muito). Só frentes da legislatura;
  - coautoria: mesma regra sobre proposições de `multicamadas.tipos_coautoria` apresentadas na legislatura,
               autores deputados (proponentes), com no máximo `max_autores` autores.

Análises:
  1. Correlação entre camadas (Spearman) em todos os pares, nos pares do mesmo partido e nos de partidos
     diferentes: frentes e coautoria dizem algo sobre o voto além do partido?
  2. Coesão de cada frente: concordância média de voto entre os membros, comparada com grupos sorteados
     com a MESMA composição partidária (cada membro trocado por outro deputado do mesmo partido).
     Excesso = observado − média dos sorteios; "bloco" = acima do percentil `percentil_bloco` dos sorteios.
  3. Efeito temático de frentes-chave (`frentes_tematicas`): nas votações dos temas da frente, membros
     votam mais com a "linha da frente" do que colegas de partido não membros? Linha da frente, para
     o partido P, = lado da maioria dos membros de OUTROS partidos (evita o membro definir a própria régua).
     Para cada votação e partido com `min_por_lado`+ membros e não membros votando:
     diferença = % de membros na linha − % de não membros na linha. Comparada com a mesma conta nas
     votações dos outros temas (controle). Intervalo de 95% por reamostragem das votações. Efeito "claro" =
     intervalos sem sobreposição e diferença de pelo menos `efeito_minimo`.
  4. Comunidades multicamada: Leiden multiplex nos grafos kNN de cada camada (pesos em `pesos_camadas`),
     comparadas com as comunidades só de voto e com os partidos (ARI).

Saídas em data/marts/camara/leg<N>/multicamadas/.
Uso: python -m src.networks.multicamadas
"""
from __future__ import annotations

import json
import sys

import igraph as ig
import leidenalg
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

from src.config import ROOT, connect, load_config, path
from src.networks.votacao import dec, n, nomes_deputados, partido_modal, carregar_votos


def _src(cfg, t):
    return f"read_parquet('{(path(cfg, 'processed') / t).as_posix()}/**/*.parquet', hive_partitioning = true)"


def co_pesos(grupos: pd.DataFrame, chave: str, maximo: int | None = None) -> pd.DataFrame:
    """Pares (a, b, peso) com peso = Σ 1/(k − 1) sobre os grupos em comum (k = tamanho do grupo)."""
    g = grupos[["deputado_id", chave]].drop_duplicates()
    tam = g.groupby(chave)["deputado_id"].transform("size")
    g = g[(tam >= 2) & ((tam <= maximo) if maximo else True)].assign(w=1 / (tam - 1))
    pares = g.merge(g, on=chave)
    pares = pares[pares["deputado_id_x"] < pares["deputado_id_y"]]
    return (pares.groupby(["deputado_id_x", "deputado_id_y"])["w_x"].sum().rename("peso").reset_index()
            .rename(columns={"deputado_id_x": "deputado_a", "deputado_id_y": "deputado_b"}))


def camada_coautoria(c: dict) -> pd.DataFrame:
    m = c.get("multicamadas", {})
    con = connect(c)
    tipos = ", ".join(f"'{t}'" for t in m.get("tipos_coautoria", ["PL", "PLP", "PEC", "PDL"]))
    ini, fim = c["redes"]["periodo"]["inicio"], c["redes"]["periodo"]["fim"]
    a = con.execute(f"""SELECT a.proposicao_id, a.deputado_id FROM {_src(c, 'proposicao_autor')} a
                        JOIN {_src(c, 'proposicoes')} p USING (proposicao_id)
                        WHERE a.deputado_id IS NOT NULL AND a.proponente AND p.sigla_tipo IN ({tipos})
                          AND p.data_apresentacao >= TIMESTAMP '{ini}' AND p.data_apresentacao <= TIMESTAMP '{fim}'""").df()
    return co_pesos(a, "proposicao_id", int(m.get("max_autores", 30)))


def camada_frentes(c: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(pares, membros) — membros com frente_id, titulo, deputado_id."""
    P = path(c, "processed")
    if not (P / "frente_membro").exists():
        return pd.DataFrame(columns=["deputado_a", "deputado_b", "peso"]), pd.DataFrame()
    leg = int(c["legislatura_atual"])
    con = connect(c)
    mem = con.execute(f"""SELECT m.frente_id, f.titulo, m.deputado_id FROM {_src(c, 'frente_membro')} m
                          JOIN {_src(c, 'frentes')} f USING (frente_id) WHERE f.legislatura = {leg}""").df()
    return co_pesos(mem, "frente_id"), mem


def knn(pares: pd.DataFrame, col: str, ids: list[str], k: int) -> ig.Graph:
    idx = {d: i for i, d in enumerate(ids)}
    p = pares[pares["deputado_a"].isin(idx) & pares["deputado_b"].isin(idx) & (pares[col] > 0)]
    dup = pd.concat([p.rename(columns={"deputado_a": "u", "deputado_b": "v"}),
                     p.rename(columns={"deputado_b": "u", "deputado_a": "v"})])
    top = dup.sort_values(col, ascending=False).groupby("u").head(k)
    arestas = {}
    for u, v, w in zip(top["u"], top["v"], top[col]):
        e = tuple(sorted((idx[u], idx[v])))
        arestas[e] = float(w)
    g = ig.Graph(n=len(ids), edges=list(arestas))
    g.es["weight"] = list(arestas.values())
    return g


def coesao_frentes(c: dict, mem: pd.DataFrame, voto: pd.DataFrame, partido: pd.Series) -> pd.DataFrame:
    m = c.get("multicamadas", {})
    reps, minimo = int(m.get("sorteios", 300)), int(m.get("min_membros_frente", 10))
    rng = np.random.default_rng(int(m.get("semente", 0)))
    ids = sorted(set(voto["deputado_a"]) | set(voto["deputado_b"]))
    idx = {d: i for i, d in enumerate(ids)}
    C = np.full((len(ids), len(ids)), np.nan)
    a, b = voto["deputado_a"].map(idx).to_numpy(), voto["deputado_b"].map(idx).to_numpy()
    C[a, b] = C[b, a] = voto["concordancia"].to_numpy()
    part = partido.reindex(ids).fillna("?").to_numpy()
    por_partido = {p: np.where(part == p)[0] for p in np.unique(part)}

    def media(g):
        sub = C[np.ix_(g, g)]
        return np.nanmean(sub[np.triu_indices(len(g), 1)])

    linhas = []
    for (fid, tit), gm in mem.groupby(["frente_id", "titulo"]):
        g = np.array([idx[d] for d in gm["deputado_id"] if d in idx])
        if len(g) < minimo:
            continue
        obs = media(g)
        sim = np.array([media(np.array([rng.choice(por_partido[part[i]]) for i in g])) for _ in range(reps)])
        comp = pd.Series(part[g]).value_counts()
        linhas.append({"frente_id": fid, "titulo": tit, "membros": int(gm["deputado_id"].nunique()), "membros_com_voto": len(g),
                       "coesao": float(obs), "coesao_esperada": float(np.nanmean(sim)),
                       "excesso": float(obs - np.nanmean(sim)), "percentil": float((sim < obs).mean()),
                       "partidos": ", ".join(f"{p} {q}" for p, q in comp.head(3).items()),
                       "maior_partido_frac": float(comp.iloc[0] / len(g))})
    out = pd.DataFrame(linhas)
    if len(out):
        out["bloco"] = out["percentil"] >= float(m.get("percentil_bloco", 0.95))
    return out


def efeito_tematico(c: dict, votos: pd.DataFrame, membros_todas: pd.DataFrame) -> pd.DataFrame:
    m = c.get("multicamadas", {})
    alvo = m.get("frentes_tematicas", [])
    if not alvo or membros_todas.empty:
        return pd.DataFrame()
    minimo, reps = int(m.get("min_por_lado", 3)), int(m.get("reamostragens", 200))
    rng = np.random.default_rng(int(m.get("semente", 0)))
    con = connect(c)
    vt = con.execute(f"""SELECT DISTINCT vp.votacao_id, t.tema FROM {_src(c, 'votacao_proposicao')} vp
                         JOIN {_src(c, 'proposicao_tema')} t USING (proposicao_id)""").df()
    v = votos[votos["valor"].isin([1, -1])][["votacao_id", "deputado_id", "partido_na_votacao", "valor"]].rename(
        columns={"partido_na_votacao": "partido"})
    linhas = []
    for fdef in alvo:
        sel = membros_todas[membros_todas["titulo"].str.contains(fdef["padrao"], case=False, regex=True)]
        if sel.empty:
            continue
        titulo = sel["titulo"].mode().iat[0]
        membros = set(sel["deputado_id"])
        x = v.assign(membro=v["deputado_id"].isin(membros))
        # linha da frente sem o próprio partido: soma dos membros na votação − soma dos membros do partido
        sm = x[x["membro"]].groupby("votacao_id")["valor"].sum()
        smp = x[x["membro"]].groupby(["votacao_id", "partido"])["valor"].sum()
        g = x.groupby(["votacao_id", "partido", "membro"])["valor"].agg(["sum", "size"]).unstack("membro")
        g = g.dropna()
        if g.empty:
            continue
        g.columns = [f"{a}_{'m' if b else 'n'}" for a, b in g.columns]
        g = g[(g["size_m"] >= minimo) & (g["size_n"] >= minimo)].reset_index()
        g["linha"] = np.sign(g["votacao_id"].map(sm) - g.set_index(["votacao_id", "partido"]).index.map(smp).fillna(0).to_numpy())
        g = g[g["linha"] != 0]
        # fração na linha: (size + linha*sum)/2/size
        g["fm"] = (g["size_m"] + g["linha"] * g["sum_m"]) / (2 * g["size_m"])
        g["fn"] = (g["size_n"] + g["linha"] * g["sum_n"]) / (2 * g["size_n"])
        g["d"] = g["fm"] - g["fn"]
        temas_v = set(vt.loc[vt["tema"].isin(fdef["temas"]), "votacao_id"])
        g["no_tema"] = g["votacao_id"].isin(temas_v)
        por_vot = g.groupby(["no_tema", "votacao_id"])["d"].mean()
        res = {}
        for lado in (True, False):
            if lado not in por_vot.index.get_level_values(0):
                res[lado] = (np.nan, np.nan, np.nan, 0)
                continue
            arr = por_vot.loc[lado].to_numpy()
            boot = [rng.choice(arr, len(arr)).mean() for _ in range(reps)]
            res[lado] = (arr.mean(), np.percentile(boot, 2.5), np.percentile(boot, 97.5), len(arr))
        linhas.append({"frente": fdef["nome"], "titulo": titulo, "membros": len(membros),
                       "temas": "; ".join(fdef["temas"]),
                       "dif_tema": res[True][0], "ic_tema_inf": res[True][1], "ic_tema_sup": res[True][2], "votacoes_tema": res[True][3],
                       "dif_outros": res[False][0], "ic_outros_inf": res[False][1], "ic_outros_sup": res[False][2],
                       "votacoes_outros": res[False][3],
                       "partidos_misturados": int(g.loc[g["no_tema"], "partido"].nunique())})
    out = pd.DataFrame(linhas)
    if len(out):
        out["especifico"] = out["dif_tema"] - out["dif_outros"]
        separados = (out["ic_tema_inf"] > out["ic_outros_sup"]) | (out["ic_tema_sup"] < out["ic_outros_inf"])
        out["efeito_claro"] = separados & (out["especifico"].abs() >= float(m.get("efeito_minimo", 0.01)))
    return out


def correlacoes(voto, camadas: dict, partido) -> list[dict]:
    base = voto[["deputado_a", "deputado_b", "concordancia"]]
    mesmo = base["deputado_a"].map(partido).to_numpy() == base["deputado_b"].map(partido).to_numpy()
    out = []
    for nome, pares in camadas.items():
        x = base.merge(pares, on=["deputado_a", "deputado_b"], how="left")["peso"].fillna(0).to_numpy()
        for rot, mask in (("todos", np.ones(len(base), bool)), ("mesmo partido", mesmo), ("partidos diferentes", ~mesmo)):
            y = base["concordancia"].to_numpy()[mask]
            xx = x[mask]
            rho = spearmanr(xx, y).statistic if len(y) > 10 and xx.std() > 0 else np.nan
            out.append({"camada": nome, "pares": rot, "n_pares": int(mask.sum()), "com_ligacao": int((xx > 0).sum()),
                        "spearman": float(rho),
                        "conc_com_ligacao": float(y[xx > 0].mean()) if (xx > 0).any() else np.nan,
                        "conc_sem_ligacao": float(y[xx == 0].mean()) if (xx == 0).any() else np.nan})
    return out


def rodar(c: dict) -> int:
    m = c.get("multicamadas", {})
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/multicamadas")
    saida.mkdir(parents=True, exist_ok=True)
    voto = pd.read_parquet(ROOT / c["redes"]["saida"] / "pares.parquet")
    voto = voto[voto["votacoes_comuns"] >= c["redes"]["min_votos_comuns"]]
    votos = carregar_votos(c)
    partido = partido_modal(votos)
    nomes = nomes_deputados(c).set_index("deputado_id")["nome"]

    co = camada_coautoria(c)
    fr, mem = camada_frentes(c)
    camadas = {"coautoria": co}
    if len(fr):
        camadas["frentes"] = fr
    corr = pd.DataFrame(correlacoes(voto, camadas, partido))

    coes = coesao_frentes(c, mem, voto, partido) if len(mem) else pd.DataFrame()
    votos["valor"] = votos["voto"].map(c["redes"]["codificacoes"][c["redes"]["principal"]["codificacao"]])
    tem = efeito_tematico(c, votos, mem)

    # comunidades multicamada
    com = pd.read_parquet(ROOT / c["redes"]["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]
    ids = sorted(princ.index)
    k = int(c["redes"]["knn"])
    grafos = {"voto": knn(voto, "concordancia", ids, k)}
    for nome, pares in camadas.items():
        grafos[nome] = knn(pares, "peso", ids, k)
    pesos = m.get("pesos_camadas", {"voto": 1.0, "frentes": 0.5, "coautoria": 0.5})
    nomes_g = list(grafos)
    melhor = None
    for s in range(int(c["redes"]["leiden"]["sementes"])):
        parts = [leidenalg.RBConfigurationVertexPartition(grafos[g], weights="weight",
                                                         resolution_parameter=c["redes"]["leiden"]["resolucao"]) for g in nomes_g]
        opt = leidenalg.Optimiser()
        opt.set_rng_seed(s)
        q = opt.optimise_partition_multiplex(parts, layer_weights=[float(pesos.get(g, 0.5)) for g in nomes_g], n_iterations=-1)
        if melhor is None or q > melhor[0]:
            melhor = (q, np.array(parts[0].membership))
    multi = pd.Series(melhor[1], index=ids)
    ari_voto = adjusted_rand_score(princ.reindex(ids), multi)
    ari_part_multi = adjusted_rand_score(partido.reindex(ids).fillna("?"), multi)
    ari_part_voto = adjusted_rand_score(partido.reindex(ids).fillna("?"), princ.reindex(ids))
    dmulti = pd.DataFrame({"deputado_id": ids, "comunidade_voto": princ.reindex(ids).values,
                           "comunidade_multi": [f"M{x + 1}" for x in multi.values]})
    dmulti["nome"] = dmulti["deputado_id"].map(nomes)
    dmulti["partido"] = dmulti["deputado_id"].map(partido)

    corr.to_parquet(saida / "correlacoes.parquet", index=False)
    coes.to_parquet(saida / "frentes.parquet", index=False)
    tem.to_parquet(saida / "frentes_tematicas.parquet", index=False)
    dmulti.to_parquet(saida / "comunidades.parquet", index=False)
    co.to_parquet(saida / "pares_coautoria.parquet", index=False)
    if len(fr):
        fr.to_parquet(saida / "pares_frentes.parquet", index=False)
    resumo = {"camadas": nomes_g, "pesos": {g: float(pesos.get(g, 0.5)) for g in nomes_g},
              "comunidades_multi": int(multi.nunique()), "comunidades_voto": int(princ.nunique()),
              "ari_multi_voto": float(ari_voto), "ari_multi_partido": float(ari_part_multi), "ari_voto_partido": float(ari_part_voto),
              "pares_coautoria": int(len(co)), "pares_frentes": int(len(fr)),
              "frentes_analisadas": int(len(coes)),
              "frentes_tematicas_efeito_claro": [r["frente"] for _, r in tem.iterrows() if r["efeito_claro"] and r["especifico"] > 0] if len(tem) else [], "frentes_bloco": int(coes["bloco"].sum()) if len(coes) else 0}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# Rede em várias camadas: voto, frentes e coautoria", "",
         f"Camadas: {', '.join(nomes_g)}. Pares de coautoria: {n(len(co))}; de frentes: {n(len(fr))}.", "",
         "## As camadas dizem algo sobre o voto além do partido?", "",
         "| Camada | Pares | Spearman com a concordância | Concordância com ligação | Sem ligação | Pares ligados |",
         "| --- | --- | --- | --- | --- | --- |"]
    for _, r in corr.iterrows():
        L.append(f"| {r['camada']} | {r['pares']} | {dec(r['spearman'], 2)} | {dec(100 * r['conc_com_ligacao'], 1)}% | "
                 f"{dec(100 * r['conc_sem_ligacao'], 1)}% | {n(r['com_ligacao'])} de {n(r['n_pares'])} |")
    if len(coes):
        L += ["", f"## Frentes: votam como bloco além da composição partidária? ({n(len(coes))} frentes com "
              f"{m.get('min_membros_frente', 10)}+ membros com voto)", "",
              f"{n(int(coes['bloco'].sum()))} frentes acima do percentil {dec(100 * float(m.get('percentil_bloco', .95)), 0)} "
              "dos sorteios com a mesma composição partidária.", "",
              "| Frente | Membros | Coesão | Esperada pela composição | Excesso | Maiores partidos |",
              "| --- | --- | --- | --- | --- | --- |"]
        for _, r in coes.sort_values("excesso", ascending=False).head(15).iterrows():
            L.append(f"| {r['titulo'][:80]} | {n(r['membros_com_voto'])} | {dec(100 * r['coesao'], 1)}% | "
                     f"{dec(100 * r['coesao_esperada'], 1)}% | {'+' if r['excesso'] >= 0 else '−'}{dec(abs(100 * r['excesso']), 1)} p.p. | {r['partidos']} |")
    if len(tem):
        L += ["", "## Frentes-chave: membros votam diferente dos colegas de partido no tema da frente?", "",
              "Diferença, em pontos percentuais, entre a fração de membros e a de não membros do MESMO partido que votam "
              "com a linha da frente (maioria dos membros dos outros partidos). Entre colchetes, intervalo de 95%.", "",
              "| Frente | Membros | Temas | No tema | Nos outros temas (controle) | Efeito do tema | Votações no tema |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        f = lambda a, b, c_: f"{dec(100 * a, 1)} [{dec(100 * b, 1)} a {dec(100 * c_, 1)}]" if a == a else "—"  # noqa: E731
        for _, r in tem.iterrows():
            L.append(f"| {r['frente']} | {n(r['membros'])} | {r['temas']} | {f(r['dif_tema'], r['ic_tema_inf'], r['ic_tema_sup'])} | "
                     f"{f(r['dif_outros'], r['ic_outros_inf'], r['ic_outros_sup'])} | "
                     f"{'+' if r['especifico'] >= 0 else '−'}{dec(abs(100 * r['especifico']), 1)} p.p.{' (claro)' if r['efeito_claro'] else ''} | "
                     f"{n(r['votacoes_tema'])} |")
    L += ["", "## Comunidades multicamada", "",
          f"- {n(resumo['comunidades_multi'])} comunidades com as camadas juntas (só voto: {n(resumo['comunidades_voto'])}).",
          f"- Semelhança com as comunidades só de voto (ARI): {dec(ari_voto, 2)}.",
          f"- Semelhança com os partidos (ARI): {dec(ari_part_multi, 2)} (só voto: {dec(ari_part_voto, 2)}).", ""]
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "multicamadas")
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
