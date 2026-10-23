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
