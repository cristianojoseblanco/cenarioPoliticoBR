"""e-Agendas (CGU): compromissos de autoridades do Executivo federal que citam deputados ou senadores.

O arquivo completo (zip de ~200 MB com CSVs mensais) é lido em fluxo; só ficam as linhas em que o assunto ou os
participantes trazem "Deputado(a) [Federal] <nome parlamentar>" ou "Senador(a) <nome parlamentar>" de alguém
das legislaturas analisadas. Nada além do compromisso público é guardado.

Staging: data/staging/agendas/compromissos.parquet (uma linha por compromisso × parlamentar citado).
Uso: python -m src.ingestion.agendas
"""
from __future__ import annotations

import io
import re
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests

from src.config import ROOT, load_config, path, para_senado


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s)).strip()


def _col(cols, *chaves):
    for c in cols:
        nc = norm(c)
        if all(k in nc for k in chaves):
            return c
    return None


def parlamentares(cfg: dict) -> pd.DataFrame:
    """Nome parlamentar normalizado de deputados (legislaturas 56+) e senadores."""
    P = path(cfg, "processed")
    d = pd.read_parquet(P / "deputados", columns=["deputado_id", "nome", "idLegislaturaFinal"])
    d = d[pd.to_numeric(d["idLegislaturaFinal"], errors="coerce") >= 56]
    out = [pd.DataFrame({"casa": "camara", "parlamentar_id": d["deputado_id"], "nome": d["nome"]})]
    ps = path(para_senado(cfg), "processed") / "deputados"
    if ps.exists():
        s = pd.read_parquet(ps, columns=["deputado_id", "nome"])
        out.append(pd.DataFrame({"casa": "senado", "parlamentar_id": s["deputado_id"], "nome": s["nome"]}))
    p = pd.concat(out, ignore_index=True)
    p["chave"] = p["nome"].map(norm)
    # nomes de uma palavra só ou repetidos entre pessoas geram falsos positivos
    p = p[p["chave"].str.len() >= 6]
    dup = p.groupby(["casa", "chave"])["parlamentar_id"].transform("nunique") > 1
    return p[~dup].drop_duplicates(["casa", "chave"])


def main() -> int:
    cfg = load_config()
    a = cfg["agendas"]
    par = parlamentares(cfg)
    padroes = {}
    for casa, prefixo in (("camara", r"(?:DEPUTAD[OA]S?|DEP)(?: FEDERA(?:L|IS)| FED)?"), ("senado", r"SENADOR(?:A|ES|AS)?")):
        g = par[par["casa"] == casa]
        nomes = sorted(g["chave"], key=len, reverse=True)
        padroes[casa] = (re.compile(rf"\b{prefixo} ({'|'.join(map(re.escape, nomes))})\b"),
                         dict(zip(g["chave"], g["parlamentar_id"])))
    destino = ROOT / a["caminhos"]["staging"]
    destino.mkdir(parents=True, exist_ok=True)
    linhas, total = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "e.zip"
        with requests.get(a["url"], stream=True, timeout=cfg["http"]["timeout_s"],
                          headers={"User-Agent": cfg["http"]["user_agent"]}) as r:
            r.raise_for_status()
            with open(arq, "wb") as f:
                for b in r.iter_content(1 << 20):
                    f.write(b)
        z = zipfile.ZipFile(arq)
        membros = [m for m in z.namelist() if m.lower().endswith(".csv")]
        print(f"{len(membros)} arquivos no zip")
        for m in membros:
            bruto = z.read(m)
            df = pd.read_csv(io.BytesIO(bruto), sep=";", dtype=str, encoding="utf-8-sig", on_bad_lines="skip", encoding_errors="replace")
            if df.shape[1] == 1:
                df = pd.read_csv(io.BytesIO(bruto), sep=",", dtype=str, encoding="utf-8-sig", on_bad_lines="skip", encoding_errors="replace")
            if total == 0:
                print("colunas:", list(df.columns))
            total += len(df)
            cols = df.columns
            c_ass, c_part = _col(cols, "ASSUNTO"), _col(cols, "PARTICIPANTE")
            c_nome, c_cargo, c_org = _col(cols, "NOME"), _col(cols, "CARGO"), _col(cols, "ORGAO")
            c_tipo, c_data = _col(cols, "TIPO"), _col(cols, "DATA", "INICIO")
            texto = (df[c_ass].fillna("") if c_ass else "") + " | " + (df[c_part].fillna("") if c_part else "")
            tn = texto.map(norm)
            for casa, (rx, ids) in padroes.items():
                achados = tn.str.findall(rx)
                for i, nomes in achados[achados.str.len() > 0].items():
                    for nm in set(nomes):
                        linhas.append({"casa": casa, "parlamentar_id": ids[nm], "data": df.at[i, c_data] if c_data else None,
                                       "autoridade": df.at[i, c_nome] if c_nome else None,
                                       "cargo": df.at[i, c_cargo] if c_cargo else None,
                                       "orgao": df.at[i, c_org] if c_org else None,
                                       "tipo": df.at[i, c_tipo] if c_tipo else None,
                                       "assunto": (df.at[i, c_ass] or "")[:300] if c_ass else None,
                                       "arquivo": m})
    out = pd.DataFrame(linhas)
    if len(out):
        out["data"] = pd.to_datetime(out["data"], errors="coerce", dayfirst=True)
    out.to_parquet(destino / "compromissos.parquet", index=False)
    print(f"{total:,} compromissos lidos; {len(out):,} citações de parlamentares".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
