"""Camada processada da Câmara: tabelas limpas, tipadas e ligadas por IDs oficiais.

Regras:
- Voto mantém o texto original (Sim, Não, Obstrução, Abstenção, Artigo 17).
  A codificação numérica é decisão de método e fica para a etapa de análise.
- Ausência não é linha: é a falta de linha em `votos` para um deputado em exercício.
- Tema herdado da proposição principal é marcado com origem = 'herdado_principal'.
- O partido de cada deputado é o observado na votação (`partido_na_votacao`),
  e o histórico partidário é derivado dessa observação.

Uso: python -m src.processing.entities
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone

from src.config import connect, load_config, path

ID_DA_URI = r"regexp_extract({col}, '(\d+)$', 1)"


def _src(staging, ds: str) -> str:
    return f"read_parquet('{(staging / ds).as_posix()}/**/*.parquet', hive_partitioning = true, union_by_name = true)"


def build(cfg: dict) -> dict[str, int]:
    con = connect(cfg)
    st = path(cfg, "staging")
    out = path(cfg, "processed")
    proc = cfg.get("processamento", {})
    excl = proc.get("colunas_excluidas", {})

    S = lambda ds: _src(st, ds)  # noqa: E731
    uid = lambda c: ID_DA_URI.format(col=c)  # noqa: E731

    excl_dep = ", ".join(f'"{c}"' for c in excl.get("deputados", []))
    exclude_clause = f"EXCLUDE ({excl_dep})" if excl_dep else ""

    tabelas: dict[str, str] = {
        "deputados": f"""
            SELECT {uid('uri')} AS deputado_id, * {exclude_clause}
            FROM {S('deputados')}
        """,
        "votacoes": f"""
            WITH n AS (SELECT idVotacao, count(*) AS n_votos FROM {S('votacoesVotos')} GROUP BY 1)
            SELECT v.id AS votacao_id,
                   TRY_CAST(v.data AS DATE) AS data,
                   CAST(v.ano AS INTEGER) AS ano,
                   TRY_CAST(v.dataHoraRegistro AS TIMESTAMP) AS data_hora_registro,
                   v.idOrgao AS orgao_id, v.siglaOrgao AS sigla_orgao,
                   v.idEvento AS evento_id,
                   v.descricao,
                   TRY_CAST(v.aprovacao AS INTEGER) AS aprovacao,
                   TRY_CAST(v.votosSim AS INTEGER) AS placar_sim,
                   TRY_CAST(v.votosNao AS INTEGER) AS placar_nao,
                   TRY_CAST(v.votosOutros AS INTEGER) AS placar_outros,
                   coalesce(n.n_votos, 0) AS n_votos_registrados,
                   n.n_votos IS NOT NULL AS nominal
            FROM {S('votacoes')} v LEFT JOIN n ON n.idVotacao = v.id
        """,
        "votos": f"""
            SELECT idVotacao AS votacao_id,
                   deputado_id,
                   voto,
                   TRY_CAST(dataHoraVoto AS TIMESTAMP) AS data_hora_voto,
                   deputado_siglaPartido AS partido_na_votacao,
                   deputado_siglaUf AS uf,
                   TRY_CAST(deputado_idLegislatura AS INTEGER) AS legislatura,
                   CAST(ano AS INTEGER) AS ano
            FROM {S('votacoesVotos')}
        """,
        "orientacoes": f"""
            SELECT idVotacao AS votacao_id, siglaOrgao AS sigla_orgao,
                   siglaBancada AS bancada, orientacao, CAST(ano AS INTEGER) AS ano
            FROM {S('votacoesOrientacoes')}
        """,
        "votacao_proposicao": f"""
            SELECT DISTINCT idVotacao AS votacao_id, proposicao_id,
                   proposicao_siglaTipo AS sigla_tipo,
                   TRY_CAST(proposicao_numero AS INTEGER) AS numero,
                   TRY_CAST(proposicao_ano AS INTEGER) AS ano_apresentacao
            FROM {S('votacoesProposicoes')}
        """,
        "proposicoes": f"""
            SELECT id AS proposicao_id, siglaTipo AS sigla_tipo, descricaoTipo AS descricao_tipo,
                   TRY_CAST(numero AS INTEGER) AS numero,
                   CAST(ano AS INTEGER) AS ano_apresentacao,
                   TRY_CAST(dataApresentacao AS TIMESTAMP) AS data_apresentacao,
                   ementa, ementaDetalhada AS ementa_detalhada, keywords,
                   nullif({uid('uriPropPrincipal')}, '') AS principal_id,
                   ultimoStatus_descricaoSituacao AS situacao,
                   ultimoStatus_regime AS regime,
                   ultimoStatus_apreciacao AS apreciacao,
                   urlInteiroTeor AS url_inteiro_teor
            FROM {S('proposicoes')}
            QUALIFY row_number() OVER (PARTITION BY id ORDER BY ano DESC) = 1
        """,
        "proposicao_autor": f"""
            SELECT DISTINCT idProposicao AS proposicao_id,
                   nullif(idDeputadoAutor, '') AS deputado_id,
                   tipoAutor AS tipo_autor, nomeAutor AS nome_autor,
                   siglaPartidoAutor AS partido_autor, siglaUFAutor AS uf_autor,
                   TRY_CAST(ordemAssinatura AS INTEGER) AS ordem_assinatura,
                   proponente = '1' AS proponente
            FROM {S('proposicoesAutores')}
        """,
    }

    tema_proprio = f"""
        SELECT DISTINCT {uid('uriProposicao')} AS proposicao_id,
               TRY_CAST(codTema AS INTEGER) AS cod_tema, tema,
               TRY_CAST(relevancia AS INTEGER) AS relevancia
        FROM {S('proposicoesTemas')}
    """
    if proc.get("herdar_tema_da_principal", False):
        tabelas["proposicao_tema"] = f"""
            WITH proprio AS ({tema_proprio}),
            p AS (SELECT DISTINCT id AS proposicao_id, nullif({uid('uriPropPrincipal')}, '') AS principal_id
                  FROM {S('proposicoes')})
            SELECT *, 'proprio' AS origem FROM proprio
            UNION ALL
            SELECT p.proposicao_id, t.cod_tema, t.tema, t.relevancia, 'herdado_principal'
            FROM p JOIN proprio t ON t.proposicao_id = p.principal_id
            WHERE p.proposicao_id NOT IN (SELECT proposicao_id FROM proprio)
        """
    else:
        tabelas["proposicao_tema"] = f"SELECT *, 'proprio' AS origem FROM ({tema_proprio})"

    # Histórico partidário observado: sequência de partidos por deputado ao longo das votações
    tabelas["partido_observado"] = f"""
        WITH v AS (
            SELECT deputado_id, deputado_siglaPartido AS partido,
                   TRY_CAST(dataHoraVoto AS TIMESTAMP) AS t
            FROM {S('votacoesVotos')} WHERE dataHoraVoto IS NOT NULL
        ),
        m AS (
            SELECT *, CASE WHEN partido IS DISTINCT FROM lag(partido) OVER w THEN 1 ELSE 0 END AS mudou
            FROM v WINDOW w AS (PARTITION BY deputado_id ORDER BY t)
        ),
        g AS (SELECT *, sum(mudou) OVER (PARTITION BY deputado_id ORDER BY t) AS seq FROM m)
        SELECT deputado_id, seq, partido,
               min(t) AS primeiro_voto, max(t) AS ultimo_voto, count(*) AS n_votos
        FROM g GROUP BY deputado_id, seq, partido
    """

    particionadas = {"votos", "votacoes"}
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    contagens = {}
    for nome, sql in tabelas.items():
        destino = out / nome
        if nome in particionadas:
            con.execute(f"COPY ({sql}) TO '{destino.as_posix()}' (FORMAT parquet, COMPRESSION zstd, PARTITION_BY (ano))")
            leitura = f"read_parquet('{destino.as_posix()}/**/*.parquet', hive_partitioning = true)"
        else:
            destino.mkdir()
            arq = destino / "part-0.parquet"
            con.execute(f"COPY ({sql}) TO '{arq.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
            leitura = f"'{arq.as_posix()}'"
        contagens[nome] = con.execute(f"SELECT count(*) FROM {leitura}").fetchone()[0]
        print(f"{nome}: {contagens[nome]:,}".replace(",", "."))
    return contagens


def relatorio(cfg: dict, contagens: dict[str, int]) -> None:
    con = connect(cfg)
    P = path(cfg, "processed")
    r = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    n = lambda x: f"{x:,}".replace(",", ".")  # noqa: E731

    def pct(a, b):
        return f"{n(a)} de {n(b)} ({f'{100 * a / b:.1f}'.replace('.', ',') if b else '0,0'}%)"

    linhas = [
        "# Camada processada — Câmara",
        "",
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Tabelas",
        "",
    ]
    linhas += [f"- `{t}`: {n(q)} linhas" for t, q in contagens.items()]

    tot, com_tema, herdado = con.execute(
        f"""
        WITH vot AS (SELECT DISTINCT vp.proposicao_id FROM {r('votacao_proposicao')} vp
                     JOIN {r('votacoes')} v USING (votacao_id) WHERE v.nominal),
        t AS (SELECT proposicao_id, bool_and(origem = 'herdado_principal') AS so_herdado
              FROM {r('proposicao_tema')} GROUP BY 1)
        SELECT count(*), count(t.proposicao_id), count(*) FILTER (WHERE t.so_herdado)
        FROM vot LEFT JOIN t USING (proposicao_id)
        """
    ).fetchone()
    linhas += [
        "",
        "## Cobertura de tema (proposições com votação nominal)",
        "",
        f"- Com tema: {pct(com_tema, tot)}",
        f"  - dos quais herdado da proposição principal: {pct(herdado, com_tema)}",
        f"- Sem tema: {pct(tot - com_tema, tot)}",
        "",
        "## Votações nominais por ano",
        "",
    ]
    for ano, nom, total in con.execute(
        f"SELECT ano, count(*) FILTER (WHERE nominal), count(*) FROM {r('votacoes')} GROUP BY 1 ORDER BY 1"
    ).fetchall():
        linhas.append(f"- {ano}: {pct(nom, total)} votações")

    trocas = con.execute(
        f"SELECT count(*) FROM (SELECT deputado_id FROM {r('partido_observado')} GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    deps = con.execute(f"SELECT count(DISTINCT deputado_id) FROM {r('partido_observado')}").fetchone()[0]
    linhas += ["", "## Partido observado", "", f"- Deputados com mais de um partido no período: {pct(trocas, deps)}", ""]

    destino = path(cfg, "relatorio_processed")
    destino.write_text("\n".join(linhas), encoding="utf-8")
    print("\n".join(linhas))


def main() -> int:
    cfg = load_config()
    contagens = build(cfg)
    relatorio(cfg, contagens)
    return 0


if __name__ == "__main__":
    sys.exit(main())
