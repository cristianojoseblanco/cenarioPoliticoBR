"""Carrega a configuração única do projeto (config/sources.yaml)."""
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(ROOT / "config" / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(cfg: dict, key: str) -> Path:
    return ROOT / cfg["caminhos"][key]


def connect(cfg: dict, db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    tmp = path(cfg, "tmp") / "duckdb"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute(f"SET memory_limit = '{cfg['duckdb']['memory_limit']}'")
    con.execute(f"SET threads = {int(cfg['duckdb']['threads'])}")
    con.execute(f"SET temp_directory = '{tmp.as_posix()}'")
    return con


def por_legislatura(cfg: dict):
    """Gera (legislatura, cfg_da_legislatura) com período e pastas de saída próprios.

    As saídas de `redes`, `fatias` e `governabilidade` (e seus relatórios) ganham o
    sufixo `leg<N>`; o período de `redes` passa a ser o da legislatura.
    """
    import copy

    for leg, per in cfg.get("legislaturas", {}).items():
        c = copy.deepcopy(cfg)
        c["redes"]["periodo"] = {"inicio": per["inicio"], "fim": per["fim"]}
        for sec in ("redes", "fatias", "governabilidade"):
            if sec in c:
                c[sec]["saida"] = c[sec]["saida"].replace("data/marts/camara/", f"data/marts/camara/leg{leg}/")
                rel = c[sec]["relatorio"]
                c[sec]["relatorio"] = rel.replace("artifacts/reports/", f"artifacts/reports/leg{leg}/")
        c["legislatura_atual"] = leg
        yield leg, c


def legislatura_tem_dados(cfg: dict, minimo: int = 50) -> bool:
    """True se há pelo menos `minimo` votações nominais no Plenário no período da legislatura."""
    per = cfg["redes"]["periodo"]
    P = path(cfg, "processed") / "votacoes"
    if not any(P.rglob("*.parquet")):
        return False
    con = connect(cfg)
    q = con.execute(
        f"""SELECT count(*) FROM read_parquet('{P.as_posix()}/**/*.parquet', hive_partitioning = true)
            WHERE nominal AND sigla_orgao = 'PLEN' AND data BETWEEN DATE '{per["inicio"]}' AND DATE '{per["fim"]}'"""
    ).fetchone()[0]
    return q >= minimo
