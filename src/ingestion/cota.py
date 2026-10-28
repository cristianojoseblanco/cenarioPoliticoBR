"""Ingestão da cota parlamentar: Câmara (CEAP, arquivo por ano) e Senado (CEAPS, API por ano).

Uma linha por despesa: parlamentar, ano, mês, categoria, fornecedor, CNPJ, valor líquido.
Privacidade: fornecedor pessoa física (documento com 11 dígitos) vira "PESSOA FÍSICA", sem nome nem CPF;
nome de passageiro e CPF do parlamentar não são lidos.

Staging: data/staging/cota/<casa>/ano=AAAA/part-0.parquet. Anos anteriores a (ano atual − recarregar) que já
existem não são baixados de novo.
Uso: python -m src.ingestion.cota
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.config import ROOT, load_config


def _doc(x) -> str:
    return re.sub(r"\D", "", str(x or ""))


def _privacidade(df: pd.DataFrame) -> pd.DataFrame:
    d = df["documento"].map(_doc)
    pf = d.str.len() == 11
    df["cnpj"] = d.where(d.str.len() == 14)
    df.loc[pf, "fornecedor"] = "PESSOA FÍSICA"
    df["pessoa_fisica"] = pf
    return df.drop(columns=["documento"])


def _get(url: str, http: dict) -> bytes | None:
    r = requests.get(url, timeout=http["timeout_s"], headers={"User-Agent": http["user_agent"].encode("ascii", "ignore").decode()})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.content


def camara(ano: int, cfg: dict) -> pd.DataFrame | None:
    bruto = _get(cfg["cota"]["camara_url"].format(ano=ano), cfg["http"])
    if bruto is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(bruto))
    membro = z.namelist()[0]
    cols = {"ideCadastro": "parlamentar_id", "txNomeParlamentar": "nome", "sgUF": "uf", "sgPartido": "partido",
            "numAno": "ano", "numMes": "mes", "txtDescricao": "categoria", "txtFornecedor": "fornecedor",
            "txtCNPJCPF": "documento", "vlrLiquido": "valor", "datEmissao": "data"}
    with z.open(membro) as f:
        df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8-sig"), sep=";", dtype=str, usecols=list(cols))
    df = df.rename(columns=cols)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df = df[df["parlamentar_id"].notna() & (df["parlamentar_id"] != "")]  # lideranças não têm parlamentar
    return _privacidade(df)


def senado(ano: int, cfg: dict) -> pd.DataFrame | None:
    bruto = _get(cfg["cota"]["senado_url"].format(ano=ano), cfg["http"])
    if bruto is None:
        return None
    d = pd.DataFrame(json.loads(bruto))
    if d.empty:
        return None
    df = pd.DataFrame({"parlamentar_id": d["codSenador"].astype(str), "nome": d["nomeSenador"], "uf": None, "partido": None,
                       "ano": d["ano"].astype(str), "mes": d["mes"].astype(str), "categoria": d["tipoDespesa"],
                       "fornecedor": d["fornecedor"], "documento": d["cpfCnpj"],
                       "valor": pd.to_numeric(d["valorReembolsado"], errors="coerce").fillna(0), "data": d["data"]})
    return _privacidade(df)


def main() -> int:
    cfg = load_config()
    c = cfg["cota"]
    base = ROOT / c["caminhos"]["staging"]
    agora = datetime.now().year
    registro = []
    for casa, fn in (("camara", camara), ("senado", senado)):
        for ano in range(int(c["desde"]), agora + 1):
            destino = base / casa / f"ano={ano}" / "part-0.parquet"
            if destino.exists() and ano < agora - int(c.get("recarregar_anos_recentes", 1)):
                continue
            try:
                df = fn(ano, cfg)
            except Exception as e:  # noqa: BLE001 — um ano com problema não derruba os outros
                print(f"::warning title=cota::{casa} {ano}: {e}")
                continue
            if df is None:
                print(f"{casa} {ano}: sem arquivo")
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            df.drop(columns=["ano"]).to_parquet(destino, index=False)
            registro.append({"casa": casa, "ano": ano, "linhas": len(df), "valor": float(df["valor"].sum())})
            print(f"{casa} {ano}: {len(df):,} despesas, R$ {df['valor'].sum():,.0f}".replace(",", "."))
    meta = ROOT / c["caminhos"]["metadata"]
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "_ultima_execucao.json").write_text(json.dumps(
        {"executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "anos": registro}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
