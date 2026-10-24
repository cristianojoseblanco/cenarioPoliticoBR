"""Relatório de qualidade do staging da Câmara.

Confere, para cada dataset: linhas por ano, colunas presentes, colunas-chave
esperadas (config), nulos nas chaves, duplicidade das chaves e, nos votos,
a distribuição dos valores de voto (para decidir a codificação na Fase 2).
"""
from __future__ import annotations

import sys

from src.config import connect, load_config, path


def n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def pct(parte: int, total: int) -> str:
    p = 100 * parte / total if total else 0.0
    p_txt = f"{p:.1f}".replace(".", ",")
    return f"{n(parte)} de {n(total)} ({p_txt}%)"


def cobertura(con, staging) -> list[str]:
    """Cobertura de tema e de cadastro das proposições com votação nominal, por ano de votação."""
    req = ["votacoesVotos", "votacoesProposicoes", "proposicoes", "proposicoesTemas"]
    if not all(any((staging / d).rglob("*.parquet")) for d in req):
        return []
    r = lambda d: f"read_parquet('{(staging / d).as_posix()}/**/*.parquet', hive_partitioning = true)"
    rows = con.execute(
        f"""
        WITH votadas AS (
            SELECT DISTINCT vp.ano, vp.proposicao_id AS pid
            FROM {r('votacoesProposicoes')} vp
            JOIN (SELECT DISTINCT idVotacao FROM {r('votacoesVotos')}) v USING (idVotacao)
        ),
        com_tema AS (SELECT DISTINCT regexp_extract(uriProposicao, '(\\d+)$', 1) AS pid FROM {r('proposicoesTemas')}),
        cadastradas AS (SELECT DISTINCT id AS pid FROM {r('proposicoes')})
        SELECT v.ano, count(*) AS total,
               count(t.pid) AS com_tema,
               count(c.pid) AS cadastradas
        FROM votadas v
        LEFT JOIN com_tema t USING (pid)
        LEFT JOIN cadastradas c USING (pid)
        GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    out = ["## Cobertura das proposições com votação nominal", ""]
    for ano, total, tema, cad in rows:
        out.append(f"- {ano}: com tema {pct(tema, total)}; com cadastro {pct(cad, total)}")
    tot = [sum(x) for x in zip(*[r[1:] for r in rows])] if rows else [0, 0, 0]
    out += [f"- Total: com tema {pct(tot[1], tot[0])}; com cadastro {pct(tot[2], tot[0])}", ""]
    return out


def main() -> int:
    cfg = load_config()
    con = connect(cfg)
    staging = path(cfg, "staging")
    chaves = cfg["camara"]["chaves"]
    datasets = (
        cfg["camara"]["datasets_unicos"]
        + cfg["camara"]["datasets_anuais"]
        + cfg["camara"].get("datasets_por_apresentacao", [])
    )

    linhas = ["# Relatório de qualidade — Câmara (staging)", ""]
    problemas = 0

    for ds in datasets:
        pasta = staging / ds
        arquivos = sorted(pasta.rglob("*.parquet"))
        linhas += [f"## {ds}", ""]
        if not arquivos:
            linhas += ["Nenhum arquivo encontrado.", ""]
            continue

        fonte = f"read_parquet('{pasta.as_posix()}/**/*.parquet', hive_partitioning = true)"
        cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {fonte}").fetchall()]
        total = con.execute(f"SELECT count(*) FROM {fonte}").fetchone()[0]
        linhas.append(f"- Linhas: {n(total)}")

        if "ano" in cols:
            for ano, qtd in con.execute(f"SELECT ano, count(*) FROM {fonte} GROUP BY 1 ORDER BY 1").fetchall():
                linhas.append(f"  - {ano}: {n(qtd)}")

        cols_fonte = [c for c in cols if c != "ano"]
        linhas.append(f"- Colunas ({len(cols_fonte)}): `{'`, `'.join(cols_fonte)}`")

        esperadas = chaves.get(ds, [])
        faltando = [c for c in esperadas if c not in cols]
        if faltando:
            problemas += 1
            linhas.append(f"- ⚠️ Colunas-chave ausentes: `{'`, `'.join(faltando)}` — ajustar `chaves` no config")
        presentes = [c for c in esperadas if c in cols]
        for c in presentes:
            nulos = con.execute(f"SELECT count(*) FROM {fonte} WHERE \"{c}\" IS NULL OR trim(\"{c}\") = ''").fetchone()[0]
            if nulos:
                problemas += 1
                linhas.append(f"- ⚠️ `{c}` vazio em {pct(nulos, total)} linhas")
        if presentes and len(presentes) == len(esperadas):
            k = ", ".join(f'"{c}"' for c in presentes)
            distintos = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT {k} FROM {fonte})").fetchone()[0]
            dup = total - distintos
            if dup:
                problemas += 1
                linhas.append(f"- ⚠️ Chave ({', '.join(presentes)}) duplicada em {pct(dup, total)} linhas")
            else:
                linhas.append(f"- Chave ({', '.join(presentes)}) única")

        if ds == "votacoesVotos" and "voto" in cols:
            linhas += ["- Valores de `voto`:"]
            for v, qtd in con.execute(f"SELECT voto, count(*) FROM {fonte} GROUP BY 1 ORDER BY 2 DESC").fetchall():
                linhas.append(f"  - `{v}`: {pct(qtd, total)}")
        linhas.append("")

    linhas += cobertura(con, staging)
    linhas.insert(2, f"Problemas encontrados: {problemas}\n")
    destino = path(cfg, "relatorio_qualidade")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
