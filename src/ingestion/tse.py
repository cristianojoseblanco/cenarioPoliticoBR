"""Ingestão do TSE: candidatos, votação por município e receitas de campanha (deputado federal e senador).

Por eleição (config `tse.eleicoes`), baixa três zips do CDN do TSE, lê só os cargos de interesse e grava
RESUMOS por candidato (os arquivos brutos, de centenas de MB, não são guardados):

  data/staging/tse/<ano>/candidatos.parquet   candidato, partido, UF, situação final, deputado_id (Câmara)
  data/staging/tse/<ano>/votos_municipio.parquet   votos nominais válidos por candidato e município
  data/staging/tse/<ano>/votos_presidente.parquet  votos para presidente por município, nos dois turnos
  data/staging/tse/<ano>/receitas.parquet     receitas por candidato, fonte e origem

Eleições já baixadas não são reprocessadas, exceto as listadas em `tse.recarregar` (contas ainda abertas).
Ligação com a Câmara: nome civil completo + data de nascimento (os dois cadastros têm). CPF não é lido.

Uso: python -m src.ingestion.tse
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.config import ROOT, load_config


def _nome(x) -> str:
    s = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z ]", " ", s).split())


def mapa_camara(cfg: dict) -> dict[tuple, str]:
    """(nome civil, nascimento) -> deputado_id, e (nome civil,) -> deputado_id quando o nome é único."""
    p = ROOT / cfg["caminhos"]["staging"] / "deputados"
    if not any(p.rglob("*.parquet")):
        from src.storage import baixar as baixar_pacote
        baixar_pacote(["staging_camara"])
    d = pd.concat([pd.read_parquet(a) for a in p.rglob("*.parquet")])
    d["id"] = d["uri"].str.rsplit("/", n=1).str[-1]
    d["n"] = d["nomeCivil"].map(_nome)
    d["nasc"] = pd.to_datetime(d["dataNascimento"], errors="coerce").dt.strftime("%Y-%m-%d")
    m = {(n, a): i for n, a, i in zip(d["n"], d["nasc"], d["id"]) if n}
    unicos = d.drop_duplicates("n", keep=False)
    m.update({(n,): i for n, i in zip(unicos["n"], unicos["id"]) if n})
    return m


def baixar(url: str, http: dict) -> Path:
    tmp = Path(tempfile.mkstemp(suffix=".zip")[1])
    with requests.get(url, stream=True, timeout=http["timeout_s"], headers={"User-Agent": http["user_agent"]}) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
    print(f"  {url.rsplit('/', 1)[-1]}: {tmp.stat().st_size / 1e6:.0f} MB")
    return tmp


def _ler(z: zipfile.ZipFile, membro: str, usecols, filtro, chunks=400_000):
    """Lê um CSV do zip em pedaços, só as colunas pedidas (as que existirem), aplicando o filtro."""
    with z.open(membro) as f:
        cab = f.readline().decode("latin-1").strip().replace('"', "").split(";")
    cols = [c for c in usecols if c in cab]
    partes = []
    with z.open(membro) as f:
        for ch in pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str, usecols=cols,
                              chunksize=chunks, low_memory=False):
            partes.append(filtro(ch))
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=cols)


def _ufs(z, prefixo):
    return [m for m in z.namelist() if re.match(rf"{prefixo}_[A-Z]{{2}}\.csv$", Path(m).name)
            and not Path(m).name.endswith(("_BR.csv",))]


def processar(ano: int, t: dict, http: dict, destino: Path, mapa: dict) -> dict:
    cargos = {str(c) for c in t["cargos"].values()}
    base = t["cdn"]
    so_cargos = lambda df: df[df["CD_CARGO"].isin(cargos)]  # noqa: E731
    destino.mkdir(parents=True, exist_ok=True)

    # candidatos
    zc = baixar(f"{base}/consulta_cand/consulta_cand_{ano}.zip", http)
    z = zipfile.ZipFile(zc)
    membro = next(m for m in z.namelist() if m.endswith(f"_{ano}_BRASIL.csv"))
    cand = _ler(z, membro, ["SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO", "DT_NASCIMENTO",
                            "SG_UF", "CD_CARGO", "DS_CARGO", "SG_PARTIDO", "NR_TURNO", "CD_TIPO_ELEICAO",
                            "DS_SITUACAO_CANDIDATURA", "DS_SIT_TOT_TURNO", "SG_FEDERACAO", "NM_COLIGACAO"], so_cargos)
    zc.unlink()
    if "CD_TIPO_ELEICAO" in cand:
        cand = cand[cand["CD_TIPO_ELEICAO"] == "2"]  # eleição ordinária (sem suplementares)
    nasc = pd.to_datetime(cand["DT_NASCIMENTO"], format="%d/%m/%Y", errors="coerce").dt.strftime("%Y-%m-%d")
    nome = cand["NM_CANDIDATO"].map(_nome)
    cand["deputado_id"] = [mapa.get((n, a)) or mapa.get((n,)) for n, a in zip(nome, nasc)]
    cand = cand.drop(columns=["DT_NASCIMENTO"]).drop_duplicates("SQ_CANDIDATO", keep="last")
    cand.to_parquet(destino / "candidatos.parquet", index=False)

    # votos por município (arquivos por UF; o BRASIL tem 4 GB e é ignorado)
    zv = baixar(f"{base}/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip", http)
    z = zipfile.ZipFile(zv)
    col_votos = ["QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_NOMINAIS"]
    partes, pres = [], []
    pres_cod = str(t.get("cargo_presidente", 1))
    com_pres = lambda df: df[df["CD_CARGO"].isin(cargos | {pres_cod})]  # noqa: E731
    for m in _ufs(z, f"votacao_candidato_munzona_{ano}"):
        df = _ler(z, m, ["SQ_CANDIDATO", "CD_CARGO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_TURNO",
                         "CD_TIPO_ELEICAO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", *col_votos], com_pres)
        if "CD_TIPO_ELEICAO" in df:
            df = df[df["CD_TIPO_ELEICAO"] == "2"]
        vc = next(c for c in col_votos if c in df.columns)
        df["votos"] = pd.to_numeric(df[vc], errors="coerce").fillna(0)
        p_ = df[df["CD_CARGO"] == pres_cod]
        pres.append(p_.groupby(["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_CANDIDATO", "NM_URNA_CANDIDATO",
                                "SG_PARTIDO"], as_index=False)["votos"].sum())
        df = df[(df["NR_TURNO"] == "1") & (df["CD_CARGO"] != pres_cod)]
        partes.append(df.groupby(["SQ_CANDIDATO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO"], as_index=False)["votos"].sum())
    # presidente: o TSE põe a votação de abrangência nacional no arquivo _BR
    br = [m for m in z.namelist() if Path(m).name == f"votacao_candidato_munzona_{ano}_BR.csv"]
    for m in br:
        df = _ler(z, m, ["CD_CARGO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_TURNO", "CD_TIPO_ELEICAO", "NR_CANDIDATO",
                         "NM_URNA_CANDIDATO", "SG_PARTIDO", *col_votos], lambda d: d[d["CD_CARGO"] == pres_cod])
        if "CD_TIPO_ELEICAO" in df:
            df = df[df["CD_TIPO_ELEICAO"] == "2"]
        vc = next(c for c in col_votos if c in df.columns)
        df["votos"] = pd.to_numeric(df[vc], errors="coerce").fillna(0)
        pres.append(df.groupby(["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_CANDIDATO", "NM_URNA_CANDIDATO",
                                "SG_PARTIDO"], as_index=False)["votos"].sum())
    zv.unlink()
    votos = pd.concat(partes, ignore_index=True)
    votos.to_parquet(destino / "votos_municipio.parquet", index=False)
    pd.concat(pres, ignore_index=True).to_parquet(destino / "votos_presidente.parquet", index=False)

    # receitas
    zr = baixar(f"{base}/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{ano}.zip", http)
    z = zipfile.ZipFile(zr)
    partes = []
    for m in _ufs(z, f"receitas_candidatos_{ano}"):
        df = _ler(z, m, ["SQ_CANDIDATO", "CD_CARGO", "DS_FONTE_RECEITA", "DS_ORIGEM_RECEITA", "DS_NATUREZA_RECEITA",
                         "VR_RECEITA", "TP_PRESTACAO_CONTAS"], so_cargos)
        df["valor"] = pd.to_numeric(df["VR_RECEITA"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                                    errors="coerce").fillna(0)
        partes.append(df.groupby(["SQ_CANDIDATO", "DS_FONTE_RECEITA", "DS_ORIGEM_RECEITA",
                                  "DS_NATUREZA_RECEITA"], as_index=False, dropna=False)["valor"].sum())
    zr.unlink()
    rec = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    rec.to_parquet(destino / "receitas.parquet", index=False)
    return {"ano": ano, "candidatos": len(cand), "linhas_votos": len(votos), "linhas_receitas": len(rec),
            "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def main() -> int:
    cfg = load_config()
    t = cfg["tse"]
    out = ROOT / t["caminhos"]["staging"]
    meta = ROOT / t["caminhos"]["metadata"]
    meta.mkdir(parents=True, exist_ok=True)
    mapa = None
    for ano in t["eleicoes"]:
        d = out / str(ano)
        vp = d / "votos_presidente.parquet"
        if vp.exists() and len(pd.read_parquet(vp)) == 0:
            vp.unlink()  # versão anterior gravou vazio (presidente fica no arquivo _BR)
        pronto = all((d / f).exists() for f in ("candidatos.parquet", "votos_municipio.parquet", "votos_presidente.parquet",
                                                  "receitas.parquet"))
        if pronto and ano not in t.get("recarregar", []):
            print(f"{ano}: já processado, pulado")
            continue
        print(f"{ano}: processando")
        try:
            mapa = mapa if mapa is not None else mapa_camara(cfg)
            info = processar(ano, t, cfg["http"], d, mapa)
        except Exception as e:  # noqa: BLE001 — uma eleição com problema não derruba as outras
            print(f"::error title=tse::{ano}: {e}")
            continue
        (meta / f"{ano}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {info}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
