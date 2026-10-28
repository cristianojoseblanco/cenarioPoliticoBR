"""Etapa 3 — rede de votação: matriz, concordância, grafo kNN e comunidades (Leiden).

Todos os parâmetros vêm de `redes` em config/sources.yaml.

Saídas (redes.saida):
  pares.parquet         concordância e votações em comum de cada par (variante principal)
  arestas.parquet       arestas do grafo kNN principal
  comunidades.parquet   comunidade de cada deputado em cada variante
  metricas.json         métricas da variante principal e da sensibilidade
  rede_plen.png         desenho do grafo principal

Uso: python -m src.networks.votacao
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

import igraph as ig
import leidenalg
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from src.config import ROOT, connect, load_config, path


# ---------------------------------------------------------------- dados

def carregar_votos(cfg: dict) -> pd.DataFrame:
    r = cfg["redes"]
    P = path(cfg, "processed")
    src = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    orgaos = ", ".join(f"'{o}'" for o in r["orgaos"])
    filtros = [f"vt.sigla_orgao IN ({orgaos})", "vt.nominal"]
    if r["periodo"].get("inicio"):
        filtros.append(f"vt.data >= DATE '{r['periodo']['inicio']}'")
    if r["periodo"].get("fim"):
        filtros.append(f"vt.data <= DATE '{r['periodo']['fim']}'")
    con = connect(cfg)
    return con.execute(
        f"""
        SELECT v.votacao_id, v.deputado_id, v.voto, v.partido_na_votacao, v.uf, vt.data,
               vt.data_hora_registro
        FROM {src('votos')} v JOIN {src('votacoes')} vt USING (votacao_id)
        WHERE {' AND '.join(filtros)}
        """
    ).df()


def nomes_deputados(cfg: dict) -> pd.DataFrame:
    P = path(cfg, "processed")
    con = connect(cfg)
    return con.execute(
        f"SELECT deputado_id, nome FROM read_parquet('{(P / 'deputados').as_posix()}/**/*.parquet')"
    ).df()


# ---------------------------------------------------------------- matriz e concordância

@dataclass
class Matriz:
    deputados: list[str]
    votacoes: list[str]
    X: np.ndarray                     # deputados × votações, NaN = sem valor
    excluidas: dict = field(default_factory=dict)


def montar_matriz(votos: pd.DataFrame, mapa: dict, minoria_minima: float) -> Matriz:
    v = votos.assign(valor=votos["voto"].map(mapa)).dropna(subset=["valor"])
    total = votos["votacao_id"].nunique()

    # minoria calculada só entre +1 e −1 (abstenção = 0 não conta para lado nenhum)
    lados = v[v["valor"] != 0].groupby("votacao_id")["valor"].agg(
        pos=lambda s: (s > 0).sum(), neg=lambda s: (s < 0).sum()
    )
    lados["minoria"] = lados[["pos", "neg"]].min(axis=1) / (lados["pos"] + lados["neg"])
    ok = lados.index[lados["minoria"] >= minoria_minima]

    v = v[v["votacao_id"].isin(ok)]
    piv = v.pivot_table(index="deputado_id", columns="votacao_id", values="valor", aggfunc="first")
    return Matriz(
        deputados=list(piv.index),
        votacoes=list(piv.columns),
        X=piv.to_numpy(dtype=float),
        excluidas={
            "votacoes_total": int(total),
            "sem_voto_com_valor": int(total - len(lados)),
            "abaixo_minoria": int(len(lados) - len(ok)),
            "incluidas": int(len(ok)),
        },
    )


def concordancia(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna (proporção de concordância, nº de votações em comum) para cada par."""
    M = (~np.isnan(X)).astype(np.float32)
    comuns = M @ M.T
    iguais = np.zeros_like(comuns)
    for val in np.unique(X[~np.isnan(X)]):
        B = (X == val).astype(np.float32)
        iguais += B @ B.T
    with np.errstate(invalid="ignore", divide="ignore"):
        conc = np.where(comuns > 0, iguais / comuns, np.nan)
    return conc, comuns


# ---------------------------------------------------------------- grafo e comunidades

def grafo_knn(conc: np.ndarray, comuns: np.ndarray, min_comuns: int, k: int) -> tuple[ig.Graph, np.ndarray]:
    n = conc.shape[0]
    valido = (comuns >= min_comuns) & ~np.eye(n, dtype=bool)
    # deputado entra no grafo se tem ao menos k vizinhos comparáveis
    ativos = np.where(valido.sum(axis=1) >= k)[0]
    idx = {d: i for i, d in enumerate(ativos)}
    pesos: dict[tuple[int, int], float] = {}
    for d in ativos:
        cand = np.where(valido[d])[0]
        cand = cand[np.isin(cand, ativos)]
        viz = cand[np.argsort(-conc[d, cand], kind="stable")[:k]]
        for u in viz:
            a, b = sorted((idx[d], idx[u]))
            pesos[(a, b)] = float(conc[d, u])
    g = ig.Graph(n=len(ativos), edges=list(pesos.keys()))
    g.es["weight"] = list(pesos.values())
    return g, ativos


def leiden(g: ig.Graph, resolucao: float, sementes: int) -> tuple[np.ndarray, float, float]:
    """Melhor partição entre várias sementes. Retorna (membros, modularidade, estabilidade média entre sementes)."""
    runs = []
    for s in range(sementes):
        p = leidenalg.find_partition(
            g, leidenalg.RBConfigurationVertexPartition, weights="weight",
            resolution_parameter=resolucao, seed=s, n_iterations=-1,
        )
        runs.append((p.quality(), np.array(p.membership)))
    runs.sort(key=lambda t: -t[0])
    melhor = runs[0][1]
    estab = float(np.mean([adjusted_rand_score(melhor, m) for _, m in runs[1:]])) if len(runs) > 1 else 1.0
    mod = g.modularity(melhor.tolist(), weights="weight")
    # rótulos C1, C2... por tamanho
    ordem = pd.Series(melhor).value_counts().index
    remap = {c: i + 1 for i, c in enumerate(ordem)}
    return np.array([remap[c] for c in melhor]), float(mod), estab


def coef_participacao(g: ig.Graph, membros: np.ndarray) -> np.ndarray:
    """Quanto as ligações de cada deputado se espalham por comunidades diferentes (0 = todas na própria)."""
    s = np.zeros(g.vcount())
    porcom = np.zeros((g.vcount(), membros.max() + 1))
    for e in g.es:
        a, b, w = e.source, e.target, e["weight"]
        porcom[a, membros[b]] += w
        porcom[b, membros[a]] += w
        s[a] += w
        s[b] += w
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.nan_to_num(1 - ((porcom / s[:, None]) ** 2).sum(axis=1))


# ---------------------------------------------------------------- variante

def rodar_variante(votos, cfg, codificacao, minoria, k):
    r = cfg["redes"]
    m = montar_matriz(votos, r["codificacoes"][codificacao], minoria)
    conc, comuns = concordancia(m.X)
    g, ativos = grafo_knn(conc, comuns, r["min_votos_comuns"], k)
    membros, mod, estab = leiden(g, r["leiden"]["resolucao"], r["leiden"]["sementes"])
    deps = [m.deputados[i] for i in ativos]
    return {
        "matriz": m, "conc": conc, "comuns": comuns, "grafo": g, "ativos": ativos,
        "deputados": deps, "membros": membros, "modularidade": mod, "estabilidade_sementes": estab,
    }


def partido_modal(votos: pd.DataFrame) -> pd.Series:
    return votos.groupby("deputado_id")["partido_na_votacao"].agg(lambda s: s.value_counts().index[0])


# ---------------------------------------------------------------- relatório

def n(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def dec(x, d=3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def pct(a, b) -> str:
    p = 100 * a / b if b else 0
    return f"{n(a)} de {n(b)} ({f'{p:.1f}'.replace('.', ',')}%)"


def layout(g) -> np.ndarray:
    """Posições dos deputados no desenho do grafo (determinístico)."""
    import random
    random.seed(42)
    ig.set_random_number_generator(random)
    return np.array(g.layout_fruchterman_reingold(weights="weight", niter=2000).coords)


def desenhar(g, membros, partidos, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lay = layout(g)
    cores = plt.get_cmap("tab10")
    fig, axs = plt.subplots(1, 2, figsize=(16, 8), dpi=110)
    top = pd.Series(partidos).value_counts().index[:9]
    cor_p = {p: cores(i) for i, p in enumerate(top)}
    for ax, titulo, cor in [
        (axs[0], "Comunidades (Leiden)", [cores((c - 1) % 10) for c in membros]),
        (axs[1], "Partido (9 maiores; demais em cinza)", [cor_p.get(p, (0.75, 0.75, 0.75, 1)) for p in partidos]),
    ]:
        for e in g.es:
            a, b = e.tuple
            ax.plot(*lay[[a, b]].T, color="#999", lw=0.15, alpha=0.4, zorder=1)
        ax.scatter(lay[:, 0], lay[:, 1], c=cor, s=18, edgecolors="white", linewidths=0.3, zorder=2)
        ax.set_title(titulo)
        ax.axis("off")
    for c in sorted(set(membros))[:10]:
        axs[0].scatter([], [], color=cores((c - 1) % 10), label=f"C{c}")
    axs[0].legend(loc="lower left", fontsize=8, frameon=False)
    for p in top:
        axs[1].scatter([], [], color=cor_p[p], label=p)
    axs[1].legend(loc="lower left", fontsize=8, frameon=False)
    fig.suptitle("Rede de votação — Plenário da Câmara (cada ponto é um deputado; ligações = 15 mais parecidos)")
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)


def rodar(cfg: dict) -> int:
    r = cfg["redes"]
    saida = ROOT / r["saida"]
    saida.mkdir(parents=True, exist_ok=True)

    votos = carregar_votos(cfg)
    nomes = nomes_deputados(cfg).set_index("deputado_id")["nome"]
    partido = partido_modal(votos)
    uf = votos.groupby("deputado_id")["uf"].agg(lambda s: s.value_counts().index[0])

    base = dict(codificacao=r["principal"]["codificacao"], minoria=r["minoria_minima"], k=r["knn"])
    variantes = {"principal": base}
    for cod in r["sensibilidade"]["codificacao"]:
        variantes[f"codificacao={cod}"] = {**base, "codificacao": cod}
    for mm in r["sensibilidade"]["minoria_minima"]:
        variantes[f"minoria={mm}"] = {**base, "minoria": mm}
    for k in r["sensibilidade"]["knn"]:
        variantes[f"knn={k}"] = {**base, "k": k}

    res = {nome: rodar_variante(votos, cfg, **p) for nome, p in variantes.items()}
    P = res["principal"]

    # ---- comunidades de todas as variantes
    linhas = []
    for nome, R in res.items():
        for d, c in zip(R["deputados"], R["membros"]):
            linhas.append({"variante": nome, "deputado_id": d, "comunidade": f"C{c}"})
    com = pd.DataFrame(linhas)
    part = coef_participacao(P["grafo"], P["membros"])
    princ = pd.DataFrame({
        "deputado_id": P["deputados"],
        "comunidade": [f"C{c}" for c in P["membros"]],
        "participacao": part,
        "grau": P["grafo"].degree(),
    })
    princ["nome"] = princ["deputado_id"].map(nomes)
    princ["partido"] = princ["deputado_id"].map(partido)
    princ["uf"] = princ["deputado_id"].map(uf)
    nvot = (~np.isnan(P["matriz"].X)).sum(axis=1)
    princ["votos_com_valor"] = [int(nvot[i]) for i in P["ativos"]]
    com = com.merge(princ[["deputado_id", "nome", "partido", "uf"]], on="deputado_id", how="left")
    com.to_parquet(saida / "comunidades.parquet", index=False)

    # ---- pares e arestas da principal
    deps_m = P["matriz"].deputados
    iu = np.triu_indices(len(deps_m), 1)
    pares = pd.DataFrame({
        "deputado_a": np.array(deps_m)[iu[0]], "deputado_b": np.array(deps_m)[iu[1]],
        "concordancia": P["conc"][iu], "votacoes_comuns": P["comuns"][iu].astype(int),
    })
    pares = pares[pares["votacoes_comuns"] >= r["min_votos_comuns"]]
    pares.to_parquet(saida / "pares.parquet", index=False)
    g = P["grafo"]
    pd.DataFrame({
        "deputado_a": [P["deputados"][e.source] for e in g.es],
        "deputado_b": [P["deputados"][e.target] for e in g.es],
        "concordancia": g.es["weight"],
    }).to_parquet(saida / "arestas.parquet", index=False)

    # ---- métricas
    ari_part = adjusted_rand_score(princ["partido"], princ["comunidade"])
    nmi_part = normalized_mutual_info_score(princ["partido"], princ["comunidade"])
    sens = {}
    base_map = dict(zip(P["deputados"], P["membros"]))
    for nome, R in res.items():
        if nome == "principal":
            continue
        comuns_d = [d for d in R["deputados"] if d in base_map]
        outro = dict(zip(R["deputados"], R["membros"]))
        sens[nome] = {
            "ari_vs_principal": adjusted_rand_score([base_map[d] for d in comuns_d], [outro[d] for d in comuns_d]),
            "comunidades": int(R["membros"].max()),
            "modularidade": R["modularidade"],
            "deputados": len(R["deputados"]),
            "votacoes": R["matriz"].excluidas["incluidas"],
        }
    tamanhos = princ["comunidade"].value_counts().sort_index(key=lambda s: s.str[1:].astype(int))
    metricas = {
        "parametros": {**base, "min_votos_comuns": r["min_votos_comuns"], "orgaos": r["orgaos"],
                       "periodo": r["periodo"], "leiden": r["leiden"]},
        "votacoes": P["matriz"].excluidas,
        "deputados_na_matriz": len(P["matriz"].deputados),
        "deputados_no_grafo": len(P["deputados"]),
        "arestas": g.ecount(),
        "comunidades": {k: int(v) for k, v in tamanhos.items()},
        "modularidade": P["modularidade"],
        "estabilidade_sementes_ari": P["estabilidade_sementes"],
        "ari_com_partido": ari_part,
        "nmi_com_partido": nmi_part,
        "sensibilidade": sens,
    }
    (saida / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

    desenhar(g, P["membros"], princ["partido"].tolist(), saida / "rede_plen.png")
    lay = layout(g)
    princ.assign(x=lay[:, 0], y=lay[:, 1]).to_parquet(saida / "deputados_rede.parquet", index=False)

    # ---- relatório
    ex = P["matriz"].excluidas
    L = [
        "# Rede de votação — Plenário",
        "",
        f"Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/{cfg.get('casa', 'camara')}`.",
        "",
        "## Dados",
        "",
        f"- Votações nominais no Plenário: {n(ex['votacoes_total'])}",
        f"  - sem voto com valor (secretas): {n(ex['sem_voto_com_valor'])}",
        f"  - minoria abaixo de {dec(r['minoria_minima'] * 100, 1)}%: {n(ex['abaixo_minoria'])}",
        f"  - incluídas: {pct(ex['incluidas'], ex['votacoes_total'])}",
        f"- Deputados na matriz: {n(len(P['matriz'].deputados))}; no grafo: {pct(len(P['deputados']), len(P['matriz'].deputados))}",
        f"- Arestas (kNN = {r['knn']}): {n(g.ecount())}",
        "",
        "## Comunidades (variante principal)",
        "",
        f"- Modularidade: {dec(P['modularidade'])}",
        f"- Estabilidade entre {r['leiden']['sementes']} sementes (ARI médio): {dec(P['estabilidade_sementes'])}",
        f"- Correspondência com partido: ARI {dec(ari_part)}, NMI {dec(nmi_part)}",
        "",
        "| Comunidade | Deputados | Partidos principais | Concordância interna média |",
        "| --- | --- | --- | --- |",
    ]
    idx_of = {d: i for i, d in enumerate(P["matriz"].deputados)}
    for c, tam in tamanhos.items():
        sub = princ[princ["comunidade"] == c]
        comp = sub["partido"].value_counts()
        comp_txt = ", ".join(f"{p} {q}" for p, q in comp.head(6).items())
        ids = [idx_of[d] for d in sub["deputado_id"]]
        bloco = P["conc"][np.ix_(ids, ids)]
        interna = np.nanmean(bloco[~np.eye(len(ids), dtype=bool)]) if len(ids) > 1 else np.nan
        L.append(f"| {c} | {n(tam)} | {comp_txt} | {dec(100 * interna, 1)}% |")

    L += ["", "## Partidos divididos entre comunidades", "",
          "| Partido | Deputados no grafo | Na comunidade principal do partido | Distribuição |", "| --- | --- | --- | --- |"]
    for p, sub in princ.groupby("partido"):
        if len(sub) < 5:
            continue
        dist = sub["comunidade"].value_counts()
        if len(dist) == 1:
            continue
        L.append(f"| {p} | {n(len(sub))} | {pct(dist.iloc[0], len(sub))} | "
                 + ", ".join(f"{c} {q}" for c, q in dist.items()) + " |")

    L += ["", "## Pontes entre comunidades (maior coeficiente de participação)", "",
          "Deputados cujas 15 ligações mais fortes se espalham por mais de uma comunidade.", "",
          "| Deputado | Partido | UF | Comunidade | Participação |", "| --- | --- | --- | --- | --- |"]
    for _, row in princ.sort_values("participacao", ascending=False).head(15).iterrows():
        L.append(f"| {row['nome']} | {row['partido']} | {row['uf']} | {row['comunidade']} | "
                 f"{dec(row['participacao'], 2)} |")

    L += ["", "## Sensibilidade", "",
          "ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.", "",
          "| Variante | Votações | Deputados | Comunidades | Modularidade | ARI vs principal |",
          "| --- | --- | --- | --- | --- | --- |"]
    for nome, s in sens.items():
        L.append(f"| {nome} | {n(s['votacoes'])} | {n(s['deputados'])} | {s['comunidades']} | "
                 f"{dec(s['modularidade'])} | {dec(s['ari_vs_principal'])} |")
    L.append("")

    rel = ROOT / r["relatorio"]
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


def main() -> int:
    from src.config import legislatura_tem_dados, por_legislatura

    cfg = load_config()
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            print(f"===== legislatura {leg}: sem dados suficientes, pulada =====")
            continue
        print(f"===== legislatura {leg} =====")
        rodar(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
