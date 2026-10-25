"""Etapa 4 — a rede de votação fatiada por tema e por janelas móveis de tempo.

Para cada fatia (um tema, ou uma janela de N votações seguidas):
  1. concordância entre deputados só nas votações da fatia;
  2. posição de cada deputado no eixo entre os dois polos
     (posição = concordância com o núcleo do polo B − concordância com o núcleo do polo A);
  3. comunidades da fatia (kNN + Leiden), comparadas às comunidades globais da Etapa 3.

Os polos são as duas comunidades globais com menor concordância entre si. Não recebem
rótulo ideológico: são identificados pela composição.

Parâmetros: `fatias` e `redes` em config/sources.yaml.
Pré-requisito: python -m src.networks.votacao (comunidades globais).

Uso: python -m src.networks.fatias
"""
from __future__ import annotations

import json
import math
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

from src.config import ROOT, connect, load_config, path
from src.networks.votacao import (
    carregar_votos, concordancia, dec, grafo_knn, leiden, montar_matriz, n, nomes_deputados, partido_modal, pct,
)

# Paleta categórica de referência (slots 1–8, modo claro), na ordem fixa.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


# ---------------------------------------------------------------- referência global

def referencia_global(cfg, votos):
    """Comunidades globais, polos e núcleos."""
    r = cfg["redes"]
    com = pd.read_parquet(ROOT / r["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]

    # núcleo: mesma comunidade (mapeada para os rótulos principais) em todas as variantes
    estavel = pd.Series(True, index=princ.index)
    for var, sub in com[com["variante"] != "principal"].groupby("variante"):
        s = sub.set_index("deputado_id")["comunidade"]
        comuns = princ.index.intersection(s.index)
        tab = pd.crosstab(s[comuns], princ[comuns])
        mapa = tab.idxmax(axis=1)
        mapeado = s.reindex(princ.index).map(mapa)
        estavel &= mapeado.eq(princ)

    # concordância média entre comunidades globais → polos
    m = montar_matriz(votos, r["codificacoes"][r["principal"]["codificacao"]], r["minoria_minima"])
    conc, comuns_n = concordancia(m.X)
    conc = np.where(comuns_n >= r["min_votos_comuns"], conc, np.nan)
    idx = {d: i for i, d in enumerate(m.deputados)}
    grupos = {c: [idx[d] for d in princ.index[princ == c] if d in idx] for c in sorted(princ.unique())}
    nucleos = {c: [d for d in princ.index[(princ == c) & estavel]] for c in grupos}
    candidatas = [c for c in grupos if len(nucleos[c]) >= cfg["fatias"]["nucleo_minimo"]]
    pares = []
    for a in candidatas:
        for b in candidatas:
            if a < b:
                pares.append((np.nanmean(conc[np.ix_(grupos[a], grupos[b])]), a, b))
    _, ca, cb = min(pares)
    polo_a, polo_b = sorted([ca, cb], key=lambda c: -len(grupos[c]))
    nucleo = {"A": nucleos[polo_a], "B": nucleos[polo_b]}
    tamanhos_nucleo = {c: len(v) for c, v in nucleos.items()}
    return princ, polo_a, polo_b, nucleo, set(m.votacoes), tamanhos_nucleo


# ---------------------------------------------------------------- fatias

def definir_fatias(cfg, votos, incluidas):
    f = cfg["fatias"]
    P = path(cfg, "processed")
    con = connect(cfg)
    src = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    vt = con.execute(
        f"""SELECT DISTINCT vp.votacao_id, t.tema
            FROM {src('votacao_proposicao')} vp JOIN {src('proposicao_tema')} t USING (proposicao_id)"""
    ).df()
    vt = vt[vt["votacao_id"].isin(incluidas)]
    cont = vt.groupby("tema")["votacao_id"].nunique().sort_values(ascending=False)
    fatias = []
    for tema, q in cont.items():
        if q >= f["tema_min_votacoes"]:
            fatias.append(("tema", tema, set(vt.loc[vt["tema"] == tema, "votacao_id"])))

    ordem = (
        votos[votos["votacao_id"].isin(incluidas)]
        .groupby("votacao_id")
        .agg(t=("data_hora_registro", "min"), d=("data", "min"))
        .assign(t=lambda x: x["t"].fillna(pd.to_datetime(x["d"])))
        .sort_values("t")
    )
    ids = list(ordem.index)
    N, W, S = len(ids), f["janela_votacoes"], f["janela_passo"]
    inicios = list(range(0, max(N - W, 0) + 1, S))
    if inicios and inicios[-1] + W < N:
        inicios.append(N - W)  # última janela termina na votação mais recente
    for i, ini in enumerate(inicios):
        bloco = ids[ini:ini + W]
        d0, d1 = ordem.loc[bloco[0], "d"], ordem.loc[bloco[-1], "d"]
        fatias.append(("janela", f"J{i + 1:02d} {d0:%Y-%m-%d} a {d1:%Y-%m-%d}", set(bloco)))
    return fatias, cont


def analisar_fatia(cfg, votos, ids, princ, nucleo):
    r, f = cfg["redes"], cfg["fatias"]
    sub = votos[votos["votacao_id"].isin(ids)]
    m = montar_matriz(sub, r["codificacoes"][r["principal"]["codificacao"]], r["minoria_minima"])
    conc, comuns = concordancia(m.X)
    min_c = max(f["min_comuns_piso"], math.ceil(f["min_comuns_fracao"] * len(m.votacoes)))
    validos = np.where(comuns >= min_c, conc, np.nan)
    np.fill_diagonal(validos, np.nan)
    idx = {d: i for i, d in enumerate(m.deputados)}

    def media_com(nuc):
        cols = [idx[d] for d in nuc if d in idx]
        if not cols:
            return np.full(len(idx), np.nan)
        bloco = validos[:, cols]
        ok = (~np.isnan(bloco)).sum(axis=1)
        with warnings.catch_warnings():  # deputado sem comparação válida -> NaN, esperado
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmean(bloco, axis=1)
        return np.where(ok >= 5, med, np.nan)

    ca, cb = media_com(nucleo["A"]), media_com(nucleo["B"])
    pos = pd.DataFrame({"deputado_id": m.deputados, "conc_a": ca, "conc_b": cb})
    pos["posicao"] = pos["conc_b"] - pos["conc_a"]

    # concordância entre os núcleos dentro da fatia
    ia = [idx[d] for d in nucleo["A"] if d in idx]
    ib = [idx[d] for d in nucleo["B"] if d in idx]
    entre = float(np.nanmean(validos[np.ix_(ia, ib)])) if ia and ib else np.nan

    # comunidades da fatia, mapeadas para os rótulos globais
    g, ativos = grafo_knn(conc, comuns, min_c, r["knn"])
    meta = {"votacoes": len(m.votacoes), "min_comuns": min_c, "conc_entre_polos": entre,
            "deputados_grafo": len(ativos)}
    pos["comunidade_fatia"] = None
    if g.vcount() > r["knn"] * 2 and g.ecount() > 0:
        membros, mod, _ = leiden(g, r["leiden"]["resolucao"], r["leiden"]["sementes"])
        deps = [m.deputados[i] for i in ativos]
        s = pd.Series([f"C{c}" for c in membros], index=deps)
        comuns_d = s.index.intersection(princ.index)
        tab = pd.crosstab(s[comuns_d], princ[comuns_d])
        mapa = tab.idxmax(axis=1)
        pos = pos.merge(s.map(mapa).rename("comunidade_fatia_mapeada").rename_axis("deputado_id").reset_index(),
                        on="deputado_id", how="left")
        meta.update({
            "comunidades": int(membros.max()), "modularidade": mod,
            "ari_vs_global": adjusted_rand_score(princ[comuns_d], s[comuns_d]),
        })
    pos = pos.drop(columns="comunidade_fatia")
    if "comunidade_fatia_mapeada" not in pos:
        pos["comunidade_fatia_mapeada"] = None
    return pos, meta


def deslocamentos(pos, k):
    jan = pos[(pos["tipo"] == "janela")].pivot_table(index="deputado_id", columns="ordem", values="posicao")
    cols = sorted(jan.columns)
    ini, fim = jan[cols[:k]].mean(axis=1), jan[cols[-k:]].mean(axis=1)
    ok = jan[cols[:k]].notna().any(axis=1) & jan[cols[-k:]].notna().any(axis=1)
    return pd.DataFrame({"inicio": ini, "fim": fim, "delta": fim - ini})[ok]


# ---------------------------------------------------------------- gráficos

def _estilo(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TXT2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def grafico_janelas(res, comps, polo_a, polo_b, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    jan = res[res["tipo"] == "janela"].copy()
    jan["fim"] = pd.to_datetime(jan["fatia"].str[-10:])
    fig, ax = plt.subplots(figsize=(11, 6), dpi=130, facecolor=SURFACE)
    _estilo(ax)
    ax.axhline(0, color=TXT2, lw=0.8, zorder=1)
    rotulos = []
    for i, c in enumerate(sorted(jan["comunidade_global"].unique(), key=lambda x: int(x[1:]))):
        s = jan[jan["comunidade_global"] == c].sort_values("fim")
        cor = SERIES[i % len(SERIES)]
        ax.plot(s["fim"], s["posicao_media"], color=cor, lw=2, zorder=3)
        ax.scatter(s["fim"], s["posicao_media"], color=cor, s=22, edgecolors=SURFACE, linewidths=1.5, zorder=4)
        ult = s.iloc[-1]
        rotulos.append([ult["posicao_media"], ult["fim"], f"{c} · {comps[c]}"])
        ax.plot([], [], color=cor, lw=2, label=f"{c} · {comps[c]}")
    # rótulos diretos no fim das linhas, afastados para não se sobreporem
    rotulos.sort(key=lambda r: r[0])
    for j in range(1, len(rotulos)):
        rotulos[j][0] = max(rotulos[j][0], rotulos[j - 1][0] + 0.07)
    for y, x, txt in rotulos:
        ax.annotate(txt, (x, y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8.5,
                    color=TXT, annotation_clip=False)
    ax.set_ylim(-1, 1)
    ax.set_ylabel(f"← mais perto do polo A ({polo_a})      mais perto do polo B ({polo_b}) →",
                  color=TXT2, fontsize=9)
    ax.set_title("Posição média de cada comunidade entre os dois polos, em janelas de 150 votações",
                 loc="left", color=TXT, fontsize=12)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=3, frameon=False, fontsize=8.5, labelcolor=TXT)
    fig.text(0.01, 0.005, "Cada ponto = uma janela, posicionada na data da última votação. "
             "Posição = concordância com o núcleo do polo B − concordância com o núcleo do polo A.",
             fontsize=7.5, color=TXT2)
    fig.tight_layout(rect=(0, 0.03, 0.88, 1))
    fig.savefig(destino, facecolor=SURFACE)
    plt.close(fig)


def grafico_temas(res, comps, ordem_temas, polo_a, polo_b, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tem = res[res["tipo"] == "tema"]
    cs = sorted(tem["comunidade_global"].unique(), key=lambda x: int(x[1:]))
    fig, axs = plt.subplots(1, len(cs), figsize=(2.3 * len(cs) + 2.5, 0.42 * len(ordem_temas) + 1.8),
                            dpi=130, sharey=True, facecolor=SURFACE)
    y = np.arange(len(ordem_temas))[::-1]
    for ax, c in zip(np.atleast_1d(axs), cs):
        _estilo(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.axvline(0, color=TXT2, lw=0.8)
        s = tem[tem["comunidade_global"] == c].set_index("fatia").reindex(ordem_temas)
        ax.hlines(y, 0, s["posicao_media"], color=GRID, lw=2)
        ax.scatter(s["posicao_media"], y, color=SERIES[0], s=40, edgecolors=SURFACE, linewidths=1.5, zorder=3)
        ax.set_xlim(-1, 1)
        ax.set_xticks([-1, 0, 1], ["A", "0", "B"])
        ax.set_title(f"{c}\n{comps[c]}", fontsize=8.5, color=TXT)
    np.atleast_1d(axs)[0].set_yticks(y, ordem_temas, fontsize=8.5, color=TXT)
    fig.suptitle(f"Posição média por tema (−1 = polo A, {polo_a}; +1 = polo B, {polo_b})",
                 x=0.01, ha="left", color=TXT, fontsize=11)
    fig.tight_layout()
    fig.savefig(destino, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- principal

def main() -> int:
    cfg = load_config()
    f = cfg["fatias"]
    saida = ROOT / f["saida"]
    saida.mkdir(parents=True, exist_ok=True)

    votos = carregar_votos(cfg)
    princ, polo_a, polo_b, nucleo, incluidas, tam_nucleo = referencia_global(cfg, votos)
    partido = partido_modal(votos)
    nomes = nomes_deputados(cfg).set_index("deputado_id")["nome"]

    def composicao(c, k=2):
        vc = partido.reindex(princ.index[princ == c]).value_counts()
        return ", ".join(f"{p} {q}" for p, q in vc.head(k).items())

    comps = {c: composicao(c) for c in sorted(princ.unique(), key=lambda x: int(x[1:]))}
    fatias, cont_temas = definir_fatias(cfg, votos, incluidas)

    posicoes, metas = [], []
    for ordem, (tipo, nome, ids) in enumerate(fatias):
        pos, meta = analisar_fatia(cfg, votos, ids, princ, nucleo)
        pos.insert(0, "fatia", nome)
        pos.insert(0, "tipo", tipo)
        pos.insert(2, "ordem", ordem)
        posicoes.append(pos)
        metas.append({"tipo": tipo, "fatia": nome, "ordem": ordem, **meta})
        print(f"{tipo:6s} {nome}: {meta['votacoes']} votações")
    pos = pd.concat(posicoes, ignore_index=True)
    pos["comunidade_global"] = pos["deputado_id"].map(princ)
    pos["mudou"] = pos["comunidade_fatia_mapeada"].notna() & pos["comunidade_global"].notna() & (
        pos["comunidade_fatia_mapeada"] != pos["comunidade_global"])
    meta = pd.DataFrame(metas)

    res = (pos.dropna(subset=["comunidade_global"])
           .groupby(["tipo", "fatia", "ordem", "comunidade_global"])
           .agg(posicao_media=("posicao", "mean"), deputados=("posicao", "count"), mudaram=("mudou", "sum"))
           .reset_index())

    pos.to_parquet(saida / "posicoes.parquet", index=False)
    meta.to_parquet(saida / "fatias.parquet", index=False)
    res.to_parquet(saida / "resumo.parquet", index=False)
    (saida / "polos.json").write_text(json.dumps({
        "polo_a": polo_a, "polo_b": polo_b, "composicao": comps,
        "nucleo_a": len(nucleo["A"]), "nucleo_b": len(nucleo["B"]), "tamanho_nucleos": tam_nucleo,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    ordem_temas = [t for t in cont_temas.index if t in set(meta.loc[meta["tipo"] == "tema", "fatia"])]
    grafico_janelas(res, comps, polo_a, polo_b, saida / "posicao_janelas.png")
    grafico_temas(res, comps, ordem_temas, polo_a, polo_b, saida / "posicao_temas.png")

    # ---------------- relatório
    cs = list(comps)
    def tabela(tipo):
        sub = res[res["tipo"] == tipo].pivot(index=["ordem", "fatia"], columns="comunidade_global",
                                              values="posicao_media").sort_index()
        m = meta[meta["tipo"] == tipo].set_index("fatia")
        L = ["| Fatia | Votações | Concordância A×B | Semelhança com a estrutura global (ARI) | " + " | ".join(cs) + " |",
             "| --- | --- | --- | --- | " + " | ".join("---" for _ in cs) + " |"]
        for (_, nome), row in sub.iterrows():
            ari = m.loc[nome].get("ari_vs_global", np.nan)
            L.append(f"| {nome} | {n(m.loc[nome, 'votacoes'])} | {dec(100 * m.loc[nome, 'conc_entre_polos'], 1)}% | "
                     f"{dec(ari, 2) if pd.notna(ari) else '—'} | "
                     + " | ".join(dec(row[c], 2) if pd.notna(row.get(c)) else "—" for c in cs) + " |")
        return L

    L = [
        "# Fatias por tema e por tempo — Plenário",
        "",
        "Parâmetros em `config/sources.yaml` → `fatias`.",
        "",
        "## Eixo de referência",
        "",
        f"- Polo A = {polo_a} ({comps[polo_a]}); núcleo estável com {n(len(nucleo['A']))} deputados.",
        f"- Polo B = {polo_b} ({comps[polo_b]}); núcleo estável com {n(len(nucleo['B']))} deputados.",
        f"- Os polos são as duas comunidades globais com menor concordância entre si, entre as que têm núcleo estável "
        f"de pelo menos {f['nucleo_minimo']} deputados. Sem rótulo ideológico.",
        "- Núcleo estável por comunidade: " + ", ".join(f"{c} {q}" for c, q in tam_nucleo.items()) + ".",
        "- Posição de um deputado = concordância com o núcleo B − concordância com o núcleo A (−1 a +1).",
        "",
        "Composição das comunidades globais: " + "; ".join(f"{c} = {v}" for c, v in comps.items()),
        "",
        "## Por tema (posição média de cada comunidade global)",
        "",
        *tabela("tema"),
        "",
        "## Por janela de tempo (posição média de cada comunidade global)",
        "",
        *tabela("janela"),
        "",
        "## Quem mais se moveu no eixo",
        "",
        f"Posição média nas {f['janelas_comparacao']} últimas janelas menos a posição média nas "
        f"{f['janelas_comparacao']} primeiras (só deputados presentes nas duas pontas). "
        "Positivo = aproximou-se do polo B; negativo = do polo A.",
        "",
        "| Deputado | Partido | Comunidade global | Posição no início | Posição no fim | Deslocamento |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    mov = deslocamentos(pos, f["janelas_comparacao"])
    mov.to_parquet(saida / "deslocamentos.parquet")
    for d, row in mov.reindex(mov["delta"].abs().sort_values(ascending=False).index).head(20).iterrows():
        L.append(f"| {nomes.get(d, d)} | {partido.get(d, '')} | {princ.get(d, '')} | {dec(row['inicio'], 2)} | "
                 f"{dec(row['fim'], 2)} | {'+' if row['delta'] > 0 else ''}{dec(row['delta'], 2)} |")
    L += ["", "### Deslocamento médio por comunidade global", "",
          "| Comunidade | Deputados comparáveis | Início | Fim | Deslocamento |", "| --- | --- | --- | --- | --- |"]
    mv = mov.assign(c=mov.index.map(princ)).dropna(subset=["c"]).groupby("c").agg(
        q=("delta", "size"), ini=("inicio", "mean"), fim=("fim", "mean"), d=("delta", "mean"))
    for c, row in mv.sort_index(key=lambda x: x.str[1:].astype(int)).iterrows():
        L.append(f"| {c} ({comps[c]}) | {n(row['q'])} | {dec(row['ini'], 2)} | {dec(row['fim'], 2)} | "
                 f"{'+' if row['d'] > 0 else ''}{dec(row['d'], 2)} |")
    L.append("")
    rel = ROOT / f["relatorio"]
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
