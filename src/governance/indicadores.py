"""Etapa 5 — indicadores de governabilidade no Plenário.

Indicadores (definições em config `governabilidade` e no vault):
  - apoio ao governo: voto com valor igual à orientação do Governo (Sim/Não/Obstrução; Obstrução = Não);
  - disciplina: voto igual à orientação do próprio partido (ou da federação, se o partido não orientou);
  - coesão (índice de Rice): |%Sim − %Não| dentro do partido em cada votação;
  - participação: votos registrados ÷ votações em que o deputado estava em exercício;
  - vitória do governo: resultado igual à orientação do Governo.

Uso: python -m src.governance.indicadores
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

from src.config import ROOT, connect, load_config, path
from src.networks.fatias import GRID, SERIES, SURFACE, TXT, TXT2, _estilo, definir_fatias
from src.networks.votacao import dec, montar_matriz, n, nomes_deputados, partido_modal, pct


# ---------------------------------------------------------------- dados

def _src(cfg, t):
    P = path(cfg, "processed")
    return f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"


def carregar(cfg):
    g = cfg["governabilidade"]
    con = connect(cfg)
    orgaos = ", ".join(f"'{o}'" for o in g["orgaos"])
    per = cfg["redes"].get("periodo", {})
    filtro = "".join([f" AND data >= DATE '{per['inicio']}'" if per.get("inicio") else "",
                      f" AND data <= DATE '{per['fim']}'" if per.get("fim") else ""])
    votacoes = con.execute(
        f"""SELECT votacao_id, data, data_hora_registro, aprovacao, placar_sim, placar_nao
            FROM {_src(cfg, 'votacoes')} WHERE nominal AND sigla_orgao IN ({orgaos}){filtro}"""
    ).df()
    votos = con.execute(
        f"""SELECT v.votacao_id, v.deputado_id, v.voto, v.partido_na_votacao AS partido, v.uf,
                   vt.data, vt.data_hora_registro
            FROM {_src(cfg, 'votos')} v JOIN {_src(cfg, 'votacoes')} vt USING (votacao_id)
            WHERE vt.nominal AND vt.sigla_orgao IN ({orgaos}){filtro.replace("data", "vt.data")}"""
    ).df()
    orient = con.execute(f"SELECT votacao_id, bancada, orientacao FROM {_src(cfg, 'orientacoes')}").df()
    orient = orient[orient["votacao_id"].isin(votacoes["votacao_id"])]
    tipos = con.execute(
        f"SELECT votacao_id, list(DISTINCT sigla_tipo) AS tipos FROM {_src(cfg, 'votacao_proposicao')} GROUP BY 1"
    ).df()
    return votacoes, votos, orient, tipos


def orientacoes_partidarias(orient: pd.DataFrame, g: dict) -> pd.DataFrame:
    """(votacao_id, partido, valor, liberado, nivel) a partir das bancadas de partido e de federação."""
    apel = g["apelidos_bancada"]
    pref = g["prefixo_federacao"]
    bl = g.get("blocos", {})
    ignorar = set(g.get("bancadas_nao_partidarias", []))
    linhas = []
    for row in orient.itertuples(index=False):
        b = (row.bancada or "").strip()
        if not b or b in ignorar:
            continue
        if b.startswith(bl.get("prefixo", "Bl ")):
            if not bl.get("usar", False):
                continue
            membros, nivel = membros_bloco(b, bl), "bloco"
        elif b.startswith(pref):
            membros, nivel = [apel.get(m.strip(), m.strip()) for m in b[len(pref):].split("-")], "federacao"
        else:
            membros, nivel = [apel.get(b, b)], "partido"
        for m in membros:
            linhas.append((row.votacao_id, m, row.orientacao, nivel))
    df = pd.DataFrame(linhas, columns=["votacao_id", "partido", "orientacao", "nivel"])
    df["valor"] = df["orientacao"].map(g["valores_orientacao"])
    df["liberado"] = df["orientacao"].eq("Liberado")
    # prioridade: orientação do partido > da federação > do bloco
    df["prio"] = df["nivel"].map({"partido": 0, "federacao": 1, "bloco": 2})
    return df.sort_values("prio").drop_duplicates(["votacao_id", "partido"]).drop(columns="prio")


def membros_bloco(nome: str, bl: dict) -> list[str]:
    """Decifra o nome abreviado do bloco ("Bl MdbPsdRepPode", "Bl UniPpFdrPsdbCid...").

    Lê as abreviações da esquerda para a direita (casamento mais longo primeiro).
    Para no "..." ou na primeira abreviação desconhecida: só membros visíveis entram.
    """
    s = nome[len(bl.get("prefixo", "Bl ")):].split("...")[0].strip()
    tokens = sorted(bl["abreviacoes"].items(), key=lambda kv: -len(kv[0]))
    membros, i = [], 0
    while i < len(s):
        for tok, sig in tokens:
            if s.startswith(tok, i):
                membros += sig if isinstance(sig, list) else [sig]
                i += len(tok)
                break
        else:
            break
    return membros


def em_exercicio_aproximacao(votos: pd.DataFrame, votacoes: pd.DataFrame) -> pd.DataFrame:
    """Par (votação, deputado) para quem votou no Plenário no mesmo mês da votação."""
    v = votos.assign(mes=pd.to_datetime(votos["data"]).dt.to_period("M"))
    ativos = v[["deputado_id", "mes"]].drop_duplicates()
    vt = votacoes.assign(mes=pd.to_datetime(votacoes["data"]).dt.to_period("M"))[["votacao_id", "mes"]]
    return vt.merge(ativos, on="mes")[["votacao_id", "deputado_id"]]


def em_exercicio_historico(cfg, votacoes: pd.DataFrame) -> pd.DataFrame:
    """Par (votação, deputado) a partir dos períodos oficiais de exercício."""
    per = pd.read_parquet(path(cfg, "processed") / "exercicio" / "part-0.parquet")
    vt = votacoes.assign(t=pd.to_datetime(votacoes["data_hora_registro"]).fillna(pd.to_datetime(votacoes["data"])))
    con = connect(cfg)
    con.register("per", per)
    con.register("vt", vt[["votacao_id", "t"]])
    return con.execute(
        "SELECT vt.votacao_id, per.deputado_id FROM vt JOIN per ON vt.t >= per.inicio AND vt.t < per.fim"
    ).df()


# ---------------------------------------------------------------- cálculo

def base_votos(cfg, votacoes, votos, orient):
    g = cfg["governabilidade"]
    val = g["valores_orientacao"]
    nomes_gov = g["bancada_governo"] if isinstance(g["bancada_governo"], list) else [g["bancada_governo"]]
    gov = orient[orient["bancada"].isin(nomes_gov)].drop_duplicates("votacao_id")[["votacao_id", "orientacao"]].rename(
        columns={"orientacao": "orient_gov"})
    gov["gov_valor"] = gov["orient_gov"].map(val)
    op = orientacoes_partidarias(orient, g)
    b = votos.assign(valor=votos["voto"].map(val))
    b = b.merge(gov, on="votacao_id", how="left")
    b = b.merge(op[["votacao_id", "partido", "valor", "liberado", "nivel"]].rename(
        columns={"valor": "partido_valor", "liberado": "partido_liberou", "nivel": "nivel_orientacao"}),
        on=["votacao_id", "partido"], how="left")
    b["alinhado_gov"] = np.where(b["valor"].notna() & b["gov_valor"].notna(), b["valor"] == b["gov_valor"], np.nan)
    b["disciplinado"] = np.where(b["valor"].notna() & b["partido_valor"].notna(),
                                 b["valor"] == b["partido_valor"], np.nan)
    return b, gov, op


def resultados(cfg, votacoes, gov, tipos):
    g = cfg["governabilidade"]
    r = votacoes.merge(gov, on="votacao_id", how="left").merge(tipos, on="votacao_id", how="left")
    placar = r["placar_sim"] > r["placar_nao"]
    r["aprovado"] = r["aprovacao"].map({1: True, 0: False})
    r["fonte_resultado"] = np.where(r["aprovado"].notna(), "aprovacao", "placar")
    r["aprovado"] = r["aprovado"].fillna(placar)
    qq = set(g["tipos_quorum_qualificado"])
    r["quorum_qualificado"] = r["tipos"].apply(lambda t: bool(qq & set(t)) if isinstance(t, (list, np.ndarray)) else False)
    r["governo_venceu"] = np.where(r["gov_valor"].notna(), (r["gov_valor"] > 0) == r["aprovado"], np.nan)
    return r


def rice(b: pd.DataFrame, minimo: int) -> pd.DataFrame:
    x = b.dropna(subset=["valor"])
    x = x[x["valor"] != 0]
    agg = x.groupby(["votacao_id", "partido"])["valor"].agg(pos=lambda s: (s > 0).sum(), neg=lambda s: (s < 0).sum())
    agg = agg[(agg["pos"] + agg["neg"]) >= minimo]
    agg["rice"] = (agg["pos"] - agg["neg"]).abs() / (agg["pos"] + agg["neg"])
    return agg.reset_index()


def taxa(serie) -> float:
    s = pd.Series(serie).dropna().astype(float)
    return float(s.mean()) if len(s) else np.nan


# ---------------------------------------------------------------- gráficos

def grafico_tempo(jan_com, jan_vit, comps, destino):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 8.2), dpi=130, facecolor=SURFACE, sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.2]})
    _estilo(ax)
    _estilo(ax2)
    rot = []
    for i, c in enumerate(sorted(jan_com["comunidade"].unique(), key=lambda x: int(x[1:]))):
        s = jan_com[jan_com["comunidade"] == c].sort_values("fim")
        cor = SERIES[i % len(SERIES)]
        ax.plot(s["fim"], 100 * s["apoio"], color=cor, lw=2, zorder=3)
        ax.scatter(s["fim"], 100 * s["apoio"], color=cor, s=22, edgecolors=SURFACE, linewidths=1.5, zorder=4)
        ax.plot([], [], color=cor, lw=2, label=f"{c} · {comps[c]}")
        rot.append([100 * s["apoio"].iloc[-1], s["fim"].iloc[-1], f"{c} · {comps[c]}"])
    rot.sort(key=lambda r: r[0])
    for j in range(1, len(rot)):
        rot[j][0] = max(rot[j][0], rot[j - 1][0] + 3.5)
    for y, x, t in rot:
        ax.annotate(t, (x, y), xytext=(8, 0), textcoords="offset points", va="center", fontsize=8.5, color=TXT,
                    annotation_clip=False)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% dos votos iguais à orientação do Governo", color=TXT2, fontsize=9)
    ax.set_title("Apoio ao governo por comunidade, em janelas de tempo", loc="left", color=TXT, fontsize=12)
    ax.legend(loc="lower left", ncol=3, frameon=False, fontsize=8, labelcolor=TXT)

    s = jan_vit.sort_values("fim")
    ax2.plot(s["fim"], 100 * s["vitoria"], color=TXT2, lw=2)
    ax2.scatter(s["fim"], 100 * s["vitoria"], color=TXT2, s=18, edgecolors=SURFACE, linewidths=1.5, zorder=4)
    ax2.set_ylim(50, 100)
    ax2.set_ylabel("% de vitórias", color=TXT2, fontsize=9)
    ax2.set_title("Votações em que o resultado seguiu a orientação do Governo", loc="left", color=TXT, fontsize=10)
    fig.text(0.01, 0.005, "Cada ponto = uma janela da Etapa 4 (todas as votações nominais do Plenário no mesmo "
             "intervalo de datas), na data da última votação.", fontsize=7.5, color=TXT2)
    fig.tight_layout(rect=(0, 0.02, 0.86, 1))
    fig.savefig(destino, facecolor=SURFACE)
    plt.close(fig)


def grafico_partidos(part, destino, cob_min, minimo=8):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    p = part[part["deputados"] >= minimo].sort_values("apoio_gov")
    fig, axs = plt.subplots(1, 3, figsize=(13, 0.36 * len(p) + 1.6), dpi=130, sharey=True, facecolor=SURFACE)
    y = np.arange(len(p))
    for ax, col, tit in zip(axs, ["apoio_gov", "disciplina", "rice"],
                            ["Apoio ao governo", "Disciplina partidária", "Coesão (Rice)"]):
        _estilo(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, lw=0.8)
        v = 100 * p[col].to_numpy()
        fraca = (col == "disciplina") & (p["votos_disc"] / p["votos_com_valor"] < cob_min).to_numpy()
        ax.barh(y, v, color=np.where(fraca, GRID, SERIES[0]), height=0.6)
        for yi, vi, fr in zip(y, v, fraca):
            if not np.isnan(vi):
                ax.text(vi + 1, yi, f"{vi:.0f}{'*' if fr else ''}", va="center", fontsize=7.5, color=TXT2)
        ax.set_xlim(0, 110)
        ax.set_xticks([0, 50, 100], ["0%", "50%", "100%"])
        ax.set_title(tit, fontsize=10, color=TXT, loc="left")
    axs[0].set_yticks(y, [f"{a} ({b})" for a, b in zip(p["partido"], p["deputados"])], fontsize=8.5, color=TXT)
    fig.suptitle(f"Partidos com {minimo}+ deputados — Plenário 2023–2026", x=0.01, ha="left", color=TXT, fontsize=11)
    fig.text(0.01, 0.005, f"* Barra cinza: disciplina medida em menos de {cob_min:.0%} dos votos do partido "
             "(o partido orientou pouco por conta própria ou ficou na parte cortada do nome do bloco).",
             fontsize=7.5, color=TXT2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(destino, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- principal

def rodar(cfg: dict) -> int:
    g = cfg["governabilidade"]
    saida = ROOT / g["saida"]
    saida.mkdir(parents=True, exist_ok=True)

    votacoes, votos, orient, tipos = carregar(cfg)
    b, gov, op = base_votos(cfg, votacoes, votos, orient)
    res = resultados(cfg, votacoes, gov, tipos)
    nomes = nomes_deputados(cfg).set_index("deputado_id")["nome"]
    partido = partido_modal(votos.rename(columns={"partido": "partido_na_votacao"}))

    com = pd.read_parquet(ROOT / cfg["redes"]["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]
    comps = {c: ", ".join(f"{p} {q}" for p, q in partido.reindex(princ.index[princ == c]).value_counts().head(2).items())
             for c in sorted(princ.unique(), key=lambda x: int(x[1:]))}

    # ---- participação
    fonte = g["participacao_fonte"]
    exerc = em_exercicio_historico(cfg, votacoes) if fonte == "historico" else em_exercicio_aproximacao(votos, votacoes)
    presentes = votos[["votacao_id", "deputado_id"]].drop_duplicates()
    part_dep = exerc.groupby("deputado_id").size().rename("em_exercicio").to_frame().join(
        presentes.merge(exerc, on=["votacao_id", "deputado_id"]).groupby("deputado_id").size().rename("presentes"))
    part_dep["presentes"] = part_dep["presentes"].fillna(0)
    part_dep["participacao"] = part_dep["presentes"] / part_dep["em_exercicio"]
    fora = presentes.merge(exerc, on=["votacao_id", "deputado_id"], how="left", indicator=True)
    votos_fora_exercicio = int((fora["_merge"] == "left_only").sum())

    # ---- por deputado
    dep = b.groupby("deputado_id").agg(
        votos_gov=("alinhado_gov", lambda s: s.notna().sum()), apoio_gov=("alinhado_gov", taxa),
        votos_disc=("disciplinado", lambda s: s.notna().sum()), disciplina=("disciplinado", taxa),
    )
    dep = dep.join(part_dep, how="outer")
    dep["nome"] = dep.index.map(nomes)
    dep["partido"] = dep.index.map(partido)
    dep["comunidade"] = dep.index.map(princ)
    dep.reset_index().to_parquet(saida / "deputados.parquet", index=False)

    # ---- por partido
    rc = rice(b, g["rice_min_votos"])
    part = b.groupby("partido").agg(
        deputados=("deputado_id", "nunique"), apoio_gov=("alinhado_gov", taxa), disciplina=("disciplinado", taxa),
        votos_disc=("disciplinado", lambda s: s.notna().sum()), votos_com_valor=("valor", lambda s: s.notna().sum()),
    ).join(rc.groupby("partido").agg(rice=("rice", "mean"), votacoes_rice=("rice", "size")))
    liberou = op.groupby("partido").agg(orientou=("valor", lambda s: s.notna().sum()), liberou=("liberado", "sum"))
    part = part.join(liberou).reset_index()
    part.to_parquet(saida / "partidos.parquet", index=False)

    # ---- por comunidade
    bc = b.assign(comunidade=b["deputado_id"].map(princ)).dropna(subset=["comunidade"])
    comu = bc.groupby("comunidade").agg(apoio_gov=("alinhado_gov", taxa), disciplina=("disciplinado", taxa))

    # ---- janelas (mesmos intervalos da Etapa 4) e temas
    rd = cfg["redes"]
    votos_net = votos.rename(columns={"partido": "partido_na_votacao"})
    m = montar_matriz(votos_net, rd["codificacoes"][rd["principal"]["codificacao"]], rd["minoria_minima"])
    fatias, _ = definir_fatias(cfg, votos_net, set(m.votacoes))
    t_vot = res.assign(t=pd.to_datetime(res["data_hora_registro"]).fillna(pd.to_datetime(res["data"])))
    linhas_j, linhas_v, linhas_t = [], [], []
    for tipo, nome, ids in fatias:
        if tipo == "janela":
            ts = t_vot[t_vot["votacao_id"].isin(ids)]["t"]
            ids_all = set(t_vot[(t_vot["t"] >= ts.min()) & (t_vot["t"] <= ts.max())]["votacao_id"])
            fim = pd.to_datetime(nome[-10:])
            sub = bc[bc["votacao_id"].isin(ids_all)]
            for c, s in sub.groupby("comunidade"):
                linhas_j.append({"janela": nome, "fim": fim, "comunidade": c, "apoio": taxa(s["alinhado_gov"]),
                                 "disciplina": taxa(s["disciplinado"])})
            rv = res[res["votacao_id"].isin(ids_all)]
            linhas_v.append({"janela": nome, "fim": fim, "votacoes": len(rv),
                             "votacoes_gov": int(rv["governo_venceu"].notna().sum()),
                             "vitoria": taxa(rv["governo_venceu"])})
        else:
            sub = bc[bc["votacao_id"].isin(ids)]
            for c, s in sub.groupby("comunidade"):
                linhas_t.append({"tema": nome, "comunidade": c, "apoio": taxa(s["alinhado_gov"])})
            rv = res[res["votacao_id"].isin(ids)]
            linhas_t.append({"tema": nome, "comunidade": "vitoria_governo", "apoio": taxa(rv["governo_venceu"])})
    jan_com, jan_vit, tem = pd.DataFrame(linhas_j), pd.DataFrame(linhas_v), pd.DataFrame(linhas_t)
    jan_com.to_parquet(saida / "janelas_comunidade.parquet", index=False)
    jan_vit.to_parquet(saida / "janelas_vitoria.parquet", index=False)
    tem.to_parquet(saida / "temas.parquet", index=False)
    res.drop(columns=["tipos"]).to_parquet(saida / "votacoes.parquet", index=False)

    grafico_tempo(jan_com, jan_vit, comps, saida / "apoio_janelas.png")
    grafico_partidos(part, saida / "partidos.png", g["disciplina_cobertura_minima"])

    # ---------------- relatório
    gv = res[res["governo_venceu"].notna()]
    qq = gv[gv["quorum_qualificado"]]
    perd = res[(res["governo_venceu"] == 0)]
    L = [
        "# Governabilidade — Plenário",
        "",
        "Parâmetros em `config/sources.yaml` → `governabilidade`.",
        "",
        "## Orientação e resultado",
        "",
        f"- Votações nominais: {n(len(res))}; com orientação do Governo Sim/Não/Obstrução: {pct(len(gv), len(res))}",
        f"- Governo venceu: {pct(int(gv['governo_venceu'].sum()), len(gv))}",
        f"  - em votações de quórum qualificado ({', '.join(g['tipos_quorum_qualificado'])}): "
        f"{pct(int(qq['governo_venceu'].sum()), len(qq))}",
        f"- Resultado pelo campo `aprovacao`: {pct(int((res['fonte_resultado'] == 'aprovacao').sum()), len(res))}; "
        f"pelo placar nas demais.",
        "",
        "## Por comunidade",
        "",
        "| Comunidade | Apoio ao governo | Disciplina partidária |",
        "| --- | --- | --- |",
    ]
    for c, row in comu.sort_index(key=lambda x: x.str[1:].astype(int)).iterrows():
        L.append(f"| {c} ({comps[c]}) | {dec(100 * row['apoio_gov'], 1)}% | {dec(100 * row['disciplina'], 1)}% |")

    L += ["", "## Por partido (5+ deputados)", "",
          "| Partido | Deputados no período | Apoio ao governo | Disciplina | Votos com disciplina medida | Coesão (Rice) |",
          "| --- | --- | --- | --- | --- | --- |"]
    for _, row in part[part["deputados"] >= 5].sort_values("apoio_gov", ascending=False).iterrows():
        f = lambda v: f"{dec(100 * v, 1)}%" if pd.notna(v) else "—"  # noqa: E731
        aviso = "*" if row["votos_disc"] < g["disciplina_cobertura_minima"] * row["votos_com_valor"] else ""
        L.append(f"| {row['partido']} | {n(row['deputados'])} | {f(row['apoio_gov'])} | {f(row['disciplina'])}{aviso} | "
                 f"{pct(row['votos_disc'], row['votos_com_valor'])} | {f(row['rice'])} |")

    L += ["", f"\\* Disciplina medida em menos de {dec(100 * g['disciplina_cobertura_minima'], 0)}% dos votos do partido: "
          "ler com cautela."]
    cobertura = b["valor"].notna()
    L += ["", "## Cobertura da disciplina", "",
          f"- Votos com valor com orientação de referência (partido, federação ou bloco): "
          f"{pct(int(b.loc[cobertura, 'disciplinado'].notna().sum()), int(cobertura.sum()))}",
          "  - referência usada (votos com valor): " + "; ".join(
              f"{nv}: {n(((b['nivel_orientacao'] == nv) & cobertura & b['disciplinado'].notna()).sum())}"
              for nv in ("partido", "federacao", "bloco")),
          "- Votos sem medida: o partido liberou a bancada, ninguém orientou por ele, ou ele estava "
          "na parte cortada do nome de um bloco (\"...\").", ""]

    L += ["## Participação", "",
          f"- Fonte: **{fonte}**" + (" (em exercício = votou no Plenário no mesmo mês; superestima a presença)"
                                     if fonte == "aproximacao" else " (períodos oficiais de exercício, API da Câmara)"),
          f"- Participação média dos deputados: {dec(100 * part_dep['participacao'].mean(), 1)}%",
          f"- Votos registrados fora de um período de exercício: {n(votos_fora_exercicio)}",
          "", "| Comunidade | Participação média |", "| --- | --- |"]
    pc = dep.dropna(subset=["comunidade"]).groupby("comunidade")["participacao"].mean()
    for c, v in pc.sort_index(key=lambda x: x.str[1:].astype(int)).items():
        L.append(f"| {c} ({comps[c]}) | {dec(100 * v, 1)}% |")

    L += ["", "## No tempo", "",
          "| Janela | Votações | Vitória do governo | " + " | ".join(comps) + " |",
          "| --- | --- | --- | " + " | ".join("---" for _ in comps) + " |"]
    pj = jan_com.pivot(index="janela", columns="comunidade", values="apoio")
    for _, row in jan_vit.sort_values("fim").iterrows():
        L.append(f"| {row['janela']} | {n(row['votacoes'])} | {dec(100 * row['vitoria'], 1)}% | "
                 + " | ".join(f"{dec(100 * pj.loc[row['janela'], c], 0)}%" for c in comps) + " |")

    L += ["", "## Por tema (apoio ao governo)", "",
          "| Tema | Vitória do governo | " + " | ".join(comps) + " |", "| --- | --- | " + " | ".join("---" for _ in comps) + " |"]
    pt = tem.pivot(index="tema", columns="comunidade", values="apoio")
    for t in pt.sort_values("vitoria_governo").index:
        L.append(f"| {t} | {dec(100 * pt.loc[t, 'vitoria_governo'], 1)}% | "
                 + " | ".join(f"{dec(100 * pt.loc[t, c], 0)}%" for c in comps) + " |")

    L += ["", "## Deputados que mais divergem do próprio partido (100+ votos medidos)", "",
          "| Deputado | Partido | Comunidade | Disciplina | Apoio ao governo |", "| --- | --- | --- | --- | --- |"]
    for d, row in dep[dep["votos_disc"] >= 100].sort_values("disciplina").head(15).iterrows():
        L.append(f"| {row['nome']} | {row['partido']} | {row['comunidade']} | {dec(100 * row['disciplina'], 1)}% | "
                 f"{dec(100 * row['apoio_gov'], 1)}% |")

    L += ["", "## Derrotas do governo (10 mais recentes)", "", "| Data | Votação | Orientação do Governo | Placar |",
          "| --- | --- | --- | --- |"]
    for _, row in perd.sort_values("data", ascending=False).head(10).iterrows():
        L.append(f"| {row['data']:%Y-%m-%d} | {row['votacao_id']} | {row['orient_gov']} | "
                 f"{n(row['placar_sim'])} Sim × {n(row['placar_nao'])} Não |")
    L.append("")
    (ROOT / g["relatorio"]).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / g["relatorio"]).write_text("\n".join(L), encoding="utf-8")
    (saida / "resumo.json").write_text(json.dumps({
        "votacoes": len(res), "votacoes_gov": len(gv), "vitorias_gov": int(gv["governo_venceu"].sum()),
        "participacao_fonte": fonte,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
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
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sys.exit(main())
