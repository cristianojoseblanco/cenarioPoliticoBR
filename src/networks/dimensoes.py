"""Dimensões de voto: um mapa 2D dos deputados a partir da matriz de votação.

Método (análise de componentes principais da matriz deputado × votação):
  1. matriz com a codificação principal (Sim +1; Não/Obstrução −1; resto vazio);
  2. cada votação é centrada na própria média; célula vazia vira 0 (= média da votação);
  3. só entram deputados com valor em pelo menos `dimensoes.cobertura_minima` das votações;
  4. decomposição em valores singulares; as 3 primeiras dimensões são guardadas.

A dimensão 1 é orientada para crescer na direção do polo B (mesmo sentido do eixo entre polos).
Cada dimensão é descrita pelas votações e temas que mais pesam nela — o nome dela vem disso,
não de rótulo ideológico.

Saídas (por legislatura, em <redes.saida>/../dimensoes/):
  deputados.parquet  d1, d2, d3 por deputado
  resumo.json        variância explicada, correlações com indicadores
  temas.parquet      peso de cada tema em cada dimensão
  votacoes.parquet   votações que mais definem cada lado de cada dimensão

Uso: python -m src.networks.dimensoes
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, connect, load_config, path
from src.networks.votacao import carregar_votos, dec, montar_matriz, n


def _saida(c):
    return ROOT / c["redes"]["saida"].replace("/redes", "/dimensoes")


def rodar(c: dict) -> int:
    r, cfgd = c["redes"], c.get("dimensoes", {})
    k = int(cfgd.get("componentes", 3))
    cob = float(cfgd.get("cobertura_minima", 0.3))
    saida = _saida(c)
    saida.mkdir(parents=True, exist_ok=True)

    votos = carregar_votos(c)
    m = montar_matriz(votos, r["codificacoes"][r["principal"]["codificacao"]], r["minoria_minima"])
    X = m.X
    ok = (~np.isnan(X)).mean(axis=1) >= cob
    X = X[ok]
    deps = [d for d, o in zip(m.deputados, ok) if o]
    media = np.nanmean(X, axis=0)
    falta = np.isnan(X)
    Z = np.where(falta, 0.0, X - media)
    # imputação iterativa de baixo posto: as células vazias recebem a reconstrução
    # das k dimensões, em vez da média — evita puxar quem falta muito para o centro do mapa
    for _ in range(int(cfgd.get("iteracoes_imputacao", 30))):
        U, S, Vt = np.linalg.svd(Z, full_matrices=False)
        rec = (U[:, :k] * S[:k]) @ Vt[:k]
        novo = np.where(falta, rec, Z)
        mudanca = np.abs(novo - Z)[falta].mean() if falta.any() else 0
        Z = novo
        if mudanca < 1e-4:
            break
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    var = (S ** 2) / (S ** 2).sum()
    sc = U[:, :k] * S[:k]
    load = Vt[:k].T  # votações × k

    # orientação: dim1 cresce para o polo B (posição média nas janelas)
    pos = pd.read_parquet(ROOT / c["fatias"]["saida"] / "posicoes.parquet")
    pmed = pos[pos["tipo"] == "janela"].groupby("deputado_id")["posicao"].mean()
    gdep = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "deputados.parquet").set_index("deputado_id")
    df = pd.DataFrame(sc, columns=[f"d{i + 1}" for i in range(k)])
    df.insert(0, "deputado_id", deps)
    pv = df["deputado_id"].map(pmed)
    if np.corrcoef(df["d1"][pv.notna()], pv.dropna())[0, 1] < 0:
        df["d1"] *= -1
        load[:, 0] *= -1
    # demais dimensões: orientadas para o apoio ao governo crescer no sentido positivo
    ap = df["deputado_id"].map(gdep["apoio_gov"])
    for i in range(1, k):
        col = f"d{i + 1}"
        if ap.notna().sum() > 10 and np.corrcoef(df[col][ap.notna()], ap.dropna())[0, 1] < 0:
            df[col] *= -1
            load[:, i] *= -1
    # escala: dimensões em desvios-padrão da dim1, para o mapa não distorcer
    escala = df["d1"].std()
    for i in range(k):
        df[f"d{i + 1}"] = df[f"d{i + 1}"] / escala
    df.to_parquet(saida / "deputados.parquet", index=False)

    # correlações com indicadores conhecidos
    ind = {"posicao_eixo": pv, "apoio_gov": ap,
           "disciplina": df["deputado_id"].map(gdep["disciplina"]),
           "participacao": df["deputado_id"].map(gdep["participacao"])}
    corr = {}
    for i in range(k):
        col = f"d{i + 1}"
        corr[col] = {nome: (float(np.corrcoef(df[col][s.notna()], s.dropna())[0, 1]) if s.notna().sum() > 10 else None)
                     for nome, s in ind.items()}

    # temas e votações que definem cada dimensão
    P = path(c, "processed")
    con = connect(c)
    src = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    vt = con.execute(f"""SELECT DISTINCT vp.votacao_id, t.tema FROM {src('votacao_proposicao')} vp
                         JOIN {src('proposicao_tema')} t USING (proposicao_id)""").df()
    info = con.execute(f"""SELECT v.votacao_id, v.data, v.descricao,
                                  any_value(p.sigla_tipo || ' ' || p.numero || '/' || p.ano_apresentacao) AS proposicao,
                                  any_value(p.ementa) AS ementa
                           FROM {src('votacoes')} v
                           LEFT JOIN {src('votacao_proposicao')} vp USING (votacao_id)
                           LEFT JOIN {src('proposicoes')} p USING (proposicao_id)
                           GROUP BY 1, 2, 3""").df().set_index("votacao_id")
    L = pd.DataFrame(load, columns=[f"d{i + 1}" for i in range(k)])
    L.insert(0, "votacao_id", m.votacoes)
    tem = vt.merge(L, on="votacao_id")
    geral = (L[[f"d{i + 1}" for i in range(k)]] ** 2).mean()
    temas = (tem.groupby("tema")[[f"d{i + 1}" for i in range(k)]]
             .agg(lambda s: float((s ** 2).mean())).div(geral).reset_index())
    temas["votacoes"] = tem.groupby("tema")["votacao_id"].nunique().reindex(temas["tema"]).values
    temas.to_parquet(saida / "temas.parquet", index=False)

    linhas = []
    for i in range(min(k, 2)):
        col = f"d{i + 1}"
        for lado, asc in (("positivo", False), ("negativo", True)):
            ordem = L.sort_values(col, ascending=asc)
            ordem = ordem.assign(prop=ordem["votacao_id"].map(lambda v: info["proposicao"].get(v) if v in info.index else v))
            ordem = ordem.drop_duplicates("prop")
            for _, row in ordem.head(8).iterrows():
                inf = info.loc[row["votacao_id"]] if row["votacao_id"] in info.index else None
                linhas.append({"dim": col, "lado": lado, "votacao_id": row["votacao_id"], "carga": row[col],
                               "data": None if inf is None else str(inf["data"]),
                               "proposicao": None if inf is None else inf["proposicao"],
                               "ementa": None if inf is None else (inf["ementa"] or inf["descricao"])})
    vtop = pd.DataFrame(linhas)
    vtop.to_parquet(saida / "votacoes.parquet", index=False)

    desc = {}
    for i in range(k):
        col = f"d{i + 1}"
        top = temas[temas["votacoes"] >= 40].sort_values(col, ascending=False).head(3)["tema"].tolist()
        desc[col] = top
    resumo = {"deputados": len(deps), "votacoes": len(m.votacoes), "cobertura_minima": cob,
              "variancia": [float(v) for v in var[:k]], "correlacoes": corr, "temas_principais": desc}
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    # relatório
    Lr = ["# Dimensões de voto", "",
          f"{n(len(deps))} deputados (com valor em {dec(100 * cob, 0)}%+ das votações) × {n(len(m.votacoes))} votações.", "",
          "| Dimensão | Variância explicada | Corr. com eixo entre polos | Corr. com apoio ao governo | Corr. com participação |",
          "| --- | --- | --- | --- | --- |"]
    for i in range(k):
        col = f"d{i + 1}"
        cc = corr[col]
        f = lambda v: dec(v, 2) if v is not None else "—"  # noqa: E731
        Lr.append(f"| {i + 1} | {dec(100 * var[i], 1)}% | {f(cc['posicao_eixo'])} | {f(cc['apoio_gov'])} | {f(cc['participacao'])} |")
    for i in range(min(k, 2)):
        col = f"d{i + 1}"
        Lr += ["", f"## Dimensão {i + 1}: temas com mais peso", ""]
        Lr.append("Peso relativo (1 = média das votações; acima de 1 = o tema define mais esta dimensão).")
        Lr.append("")
        for _, t in temas[temas["votacoes"] >= 40].sort_values(col, ascending=False).head(6).iterrows():
            Lr.append(f"- {t['tema']}: {dec(t[col], 2)} ({n(t['votacoes'])} votações)")
        for lado in ("positivo", "negativo"):
            Lr += ["", f"Votações em que votar Sim mais aproxima do lado {lado}:", ""]
            for _, v in vtop[(vtop["dim"] == col) & (vtop["lado"] == lado)].head(5).iterrows():
                Lr.append(f"- {str(v['data'])[:10]} · {v['proposicao']} · {(v['ementa'] or '').splitlines()[0][:140]}")
    Lr.append("")
    rel = ROOT / c["redes"]["relatorio"].replace("rede_votacao", "dimensoes")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(Lr), encoding="utf-8")
    print("\n".join(Lr[:12]))
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
