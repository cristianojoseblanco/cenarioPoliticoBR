"""Ingestão dos arquivos em lote da Câmara dos Deputados para Parquet.

- Baixa os CSVs listados em config/sources.yaml.
- Converte para Parquet com TODAS as colunas como texto (staging fiel à fonte:
  nenhum voto, ausência ou código é reinterpretado aqui).
- Idempotente: se o SHA-256 do arquivo baixado não mudou, nada é reescrito.
- Registra metadados de origem (URL, data de coleta, hash, linhas, bytes).

Uso:
    python -m src.ingestion.camara                # anos do config
    ANOS=2023,2024 python -m src.ingestion.camara # sobrescreve anos
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.config import connect, load_config, path

SCHEMA_VERSION = 1


def _download(url: str, dest: Path, http: dict) -> str | None:
    """Baixa url para dest. Retorna sha256, ou None se a fonte não tem o arquivo (404)."""
    headers = {"User-Agent": http["user_agent"]}
    for tentativa in range(1, http["retries"] + 1):
        try:
            with requests.get(url, stream=True, timeout=http["timeout_s"], headers=headers) as r:
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                h = hashlib.sha256()
                part = dest.with_name(dest.name + ".part")
                with open(part, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        h.update(chunk)
                part.replace(dest)
                return h.hexdigest()
        except requests.RequestException as e:
            espera = 2 ** tentativa
            print(f"  tentativa {tentativa} falhou ({e}); nova tentativa em {espera}s", file=sys.stderr)
            time.sleep(espera)
    raise RuntimeError(f"Falha ao baixar {url} após {http['retries']} tentativas")


def csv_to_parquet(con, csv_path: Path, parquet_path: Path, delim: str) -> int:
    """Converte CSV em Parquet sem inferir tipos. Retorna número de linhas."""
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = parquet_path.with_name(parquet_path.name + ".tmp")
    con.execute(
        f"""
        COPY (
            SELECT * FROM read_csv(
                '{csv_path.as_posix()}',
                delim = '{delim}', header = true, all_varchar = true,
                quote = '"', escape = '"', strict_mode = false
            )
        ) TO '{tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """
    )
    tmp.replace(parquet_path)
    return con.execute(f"SELECT count(*) FROM '{parquet_path.as_posix()}'").fetchone()[0]


def _ingest_one(con, cfg: dict, nome: str, ano: int | None) -> dict:
    c = cfg["camara"]
    fmt = c["formato"]
    arquivo = f"{nome}-{ano}" if ano else nome
    url = f"{c['base_url']}/{nome}/{fmt}/{arquivo}.{fmt}"

    tmp_dir = path(cfg, "tmp")
    meta_dir = path(cfg, "metadata")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    destino = path(cfg, "staging") / nome / (f"ano={ano}" if ano else "") / "part-0.parquet"
    meta_file = meta_dir / f"{arquivo}.json"
    anterior = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

    print(f"→ {arquivo}")
    csv_path = tmp_dir / f"{arquivo}.{fmt}"
    inicio = time.time()
    sha = _download(url, csv_path, cfg["http"])
    if sha is None:
        print("  não disponível na fonte (404)")
        return {"arquivo": arquivo, "status": "ausente_na_fonte"}

    if sha == anterior.get("sha256") and destino.exists():
        csv_path.unlink(missing_ok=True)
        print("  sem mudanças")
        return {"arquivo": arquivo, "status": "sem_mudanca"}

    bytes_csv = csv_path.stat().st_size
    linhas = csv_to_parquet(con, csv_path, destino, c["csv_delim"])
    csv_path.unlink(missing_ok=True)

    meta = {
        "fonte": "camara",
        "dataset": nome,
        "ano": ano,
        "url": url,
        "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": sha,
        "linhas": linhas,
        "bytes_csv": bytes_csv,
        "bytes_parquet": destino.stat().st_size,
        "segundos": round(time.time() - inicio, 1),
        "versao_esquema": SCHEMA_VERSION,
        "transformacao": "csv -> parquet, todas as colunas como texto, sem filtros",
    }
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {linhas:,} linhas".replace(",", "."))
    return {"arquivo": arquivo, "status": "atualizado", **meta}


def anos_apresentacao(con, cfg: dict, anos_votacao: list[int]) -> list[int]:
    """Anos de apresentação das proposições com votação nominal, mais os anos de votação."""
    staging = path(cfg, "staging")
    vp, vv = staging / "votacoesProposicoes", staging / "votacoesVotos"
    anos = set(anos_votacao)
    if any(vp.rglob("*.parquet")) and any(vv.rglob("*.parquet")):
        rows = con.execute(
            f"""
            SELECT DISTINCT TRY_CAST(vp.proposicao_ano AS INTEGER)
            FROM read_parquet('{vp.as_posix()}/**/*.parquet', hive_partitioning = true) vp
            JOIN (SELECT DISTINCT idVotacao
                  FROM read_parquet('{vv.as_posix()}/**/*.parquet', hive_partitioning = true)) v
              USING (idVotacao)
            """
        ).fetchall()
        anos |= {r[0] for r in rows if r[0] is not None}
    minimo = cfg["camara"].get("ano_minimo_apresentacao", 0)
    return sorted(a for a in anos if a >= minimo)


def main() -> int:
    cfg = load_config()
    c = cfg["camara"]
    anos_env = os.environ.get("ANOS", "").strip()
    anos = [int(a) for a in anos_env.split(",") if a.strip()] if anos_env else c["anos_padrao"]

    con = connect(cfg)
    resultados, erros = [], []

    def rodar(tarefas):
        for nome, ano in tarefas:
            try:
                resultados.append(_ingest_one(con, cfg, nome, ano))
            except Exception as e:  # registra e segue; falha no fim
                print(f"  ERRO: {e}", file=sys.stderr)
                erros.append({"arquivo": f"{nome}-{ano}" if ano else nome, "erro": str(e)})

    # 1) arquivos únicos e arquivos por ano de votação
    rodar([(n, None) for n in c["datasets_unicos"]] + [(n, a) for a in anos for n in c["datasets_anuais"]])

    # 2) arquivos por ano de apresentação, com anos derivados dos dados
    anos_apres = anos_apresentacao(con, cfg, anos)
    print(f"Anos de apresentação necessários: {anos_apres}")
    rodar([(n, a) for a in anos_apres for n in c.get("datasets_por_apresentacao", [])])

    log = path(cfg, "metadata") / "_ultima_execucao.json"
    log.write_text(
        json.dumps(
            {
                "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "anos": anos,
                "resultados": [{k: r[k] for k in ("arquivo", "status")} for r in resultados],
                "erros": erros,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
