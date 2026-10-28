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
    import re

    for leg, per in cfg.get("legislaturas", {}).items():
        c = copy.deepcopy(cfg)
        c["redes"]["periodo"] = {"inicio": per["inicio"], "fim": per["fim"]}
        for sec in ("redes", "fatias", "governabilidade"):
            if sec in c:
                c[sec]["saida"] = re.sub(r"data/marts/(\w+)/", rf"data/marts/\1/leg{leg}/", c[sec]["saida"], count=1)
                c[sec]["relatorio"] = re.sub(r"artifacts/reports/((?:senado/)?)", rf"artifacts/reports/\1leg{leg}/",
                                             c[sec]["relatorio"], count=1)
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


def _mesclar(base: dict, extra: dict) -> dict:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def para_senado(cfg: dict) -> dict:
    """Configuração para rodar as análises no Senado: caminhos próprios e parâmetros de `senado.analise`."""
    import copy

    c = copy.deepcopy(cfg)
    s = c["senado"]
    c["caminhos"]["processed"] = s["caminhos"]["processed"]
    c["caminhos"]["staging"] = s["caminhos"]["staging"]
    for sec, val in c.items():
        if isinstance(val, dict):
            for k in ("saida", "relatorio"):
                if isinstance(val.get(k), str):
                    val[k] = val[k].replace("data/marts/camara", "data/marts/senado").replace(
                        "artifacts/reports/", "artifacts/reports/senado/")
    _mesclar(c, s.get("analise", {}))
    c["casa"] = "senado"
    return c
