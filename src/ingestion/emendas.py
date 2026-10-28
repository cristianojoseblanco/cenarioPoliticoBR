"""Ingestão das emendas parlamentares (Portal da Transparência, arquivo único com todos os anos).

  {url} -> zip com EmendasParlamentares.csv (uma linha por emenda × localidade, com valores empenhado/pago e
  código IBGE do município) e EmendasParlamentares_PorFavorecido.csv (pagamentos por mês e favorecido).

Staging:
  data/staging/emendas/emendas.parquet     tabela principal, colunas como texto (nomes padronizados)
  data/staging/emendas/pagamentos.parquet  pagamentos somados por emenda e mês (do arquivo por favorecido)

Idempotente: zip com o mesmo SHA-256 não é reprocessado.
Uso: python -m src.ingestion.emendas
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.config import ROOT, load_config


def _col(c: str) -> str:
    s = unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode().lower()
    return "_".join("".join(ch if ch.isalnum() else " " for ch in s).split())


def _csv(z, nome, **kw):
    membro = next(m for m in z.namelist() if Path(m).name == nome)
    with z.open(membro) as f:
        return pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str, **kw)


def main() -> int:
    cfg = load_config()
    e = cfg["emendas"]
    out = ROOT / e["caminhos"]["staging"]
    meta = ROOT / e["caminhos"]["metadata"]
    out.mkdir(parents=True, exist_ok=True)
    meta.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkstemp(suffix=".zip")[1])
    with requests.get(e["url"], stream=True, timeout=cfg["http"]["timeout_s"],
                      headers={"User-Agent": cfg["http"]["user_agent"]}) as r:
        r.raise_for_status()
        h = hashlib.sha256()
        with open(tmp, "wb") as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
                h.update(ch)
    sha = h.hexdigest()
    mp = meta / "_ultima_execucao.json"
    antes = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    if antes.get("sha256") == sha and (out / "emendas.parquet").exists():
        print("Emendas: sem mudança")
        tmp.unlink()
        return 0
    z = zipfile.ZipFile(tmp)
    em = _csv(z, "EmendasParlamentares.csv")
    em.columns = [_col(c) for c in em.columns]
    em.to_parquet(out / "emendas.parquet", index=False)
    partes = []
    for ch in _csv(z, "EmendasParlamentares_PorFavorecido.csv", chunksize=500_000,
                   usecols=["Código da Emenda", "Ano/Mês", "Valor Recebido"]):
        ch.columns = ["codigo_emenda", "ano_mes", "valor"]
        ch["valor"] = pd.to_numeric(ch["valor"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                                    errors="coerce").fillna(0)
        partes.append(ch.groupby(["codigo_emenda", "ano_mes"], as_index=False)["valor"].sum())
    pag = pd.concat(partes).groupby(["codigo_emenda", "ano_mes"], as_index=False)["valor"].sum()
    pag.to_parquet(out / "pagamentos.parquet", index=False)
    tmp.unlink()
    info = {"sha256": sha, "linhas_emendas": len(em), "linhas_pagamentos": len(pag),
            "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    mp.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
