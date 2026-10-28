"""Ingestão do IBGE: indicadores municipais (SIDRA) e malha municipal (geoftp), para emendas e mapa.

O servidor `servicodados.ibge.gov.br` não responde ao GitHub Actions; por isso usamos dois serviços oficiais
que respondem: apisidra.ibge.gov.br (tabelas) e geoftp.ibge.gov.br (malhas).

Saídas:
  data/staging/ibge/municipios.parquet   código IBGE, nome, UF, população (2022 e estimada), área, densidade,
                                         alfabetização (15+), % urbana, PIB e PIB per capita
  data/marts/geo/municipios.topo.json    malha municipal simplificada (TopoJSON), para a página
  data/marts/geo/ufs.topo.json           malha das UFs

Indicadores: refeitos se o arquivo tiver mais de `ibge.dias_validade` dias. Malha: só se não existir.
Uso: python -m src.ingestion.ibge
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.config import ROOT, load_config


def sidra(caminho: str, http: dict) -> pd.DataFrame:
    url = f"https://apisidra.ibge.gov.br/values{caminho}"
    for tentativa in range(1, 5):
        try:
            r = requests.get(url, timeout=300, headers={"User-Agent": http["user_agent"]})
            r.raise_for_status()
            d = r.json()
            return pd.DataFrame(d[1:])
        except (requests.RequestException, ValueError) as e:
            print(f"  SIDRA {caminho}: tentativa {tentativa} falhou ({e})", file=sys.stderr)
            time.sleep(5 * tentativa)
    raise RuntimeError(f"SIDRA falhou: {caminho}")


def _num(s):
    return pd.to_numeric(s.replace({"-": None, "...": None, "X": None, "..": None}), errors="coerce")


def indicadores(cfg: dict) -> pd.DataFrame:
    g, http = cfg["ibge"], cfg["http"]
    t = g["tabelas"]
    base = sidra(t["censo_area_densidade"], http)
    base["var"] = base["D2N"]
    m = base.pivot_table(index=["D1C", "D1N"], columns="var", values="V", aggfunc="first").reset_index()
    m = m.rename(columns={"D1C": "cod_ibge", "D1N": "nome_uf", "População residente": "pop_2022",
                          "Área da unidade territorial": "area_km2", "Densidade demográfica": "densidade"})
    for c in ("pop_2022", "area_km2", "densidade"):
        m[c] = _num(m[c])
    m["nome"] = m["nome_uf"].str.replace(r"\s*\([A-Z]{2}\)$", "", regex=True)
    m["uf"] = m["nome_uf"].str.extract(r"\(([A-Z]{2})\)$")[0]

    est = sidra(t["populacao_estimada"], http)
    m = m.merge(est[["D1C", "V", "D3N"]].rename(columns={"D1C": "cod_ibge", "V": "pop_estimada", "D3N": "ano_pop_estimada"}),
                on="cod_ibge", how="left")
    m["pop_estimada"] = _num(m["pop_estimada"])

    alf = sidra(t["alfabetizacao"], http)
    m = m.merge(alf[["D1C", "V"]].rename(columns={"D1C": "cod_ibge", "V": "alfabetizacao"}), on="cod_ibge", how="left")
    m["alfabetizacao"] = _num(m["alfabetizacao"]) / 100

    try:
        urb = sidra(t["situacao_domicilio"], http)
        u = urb.pivot_table(index="D1C", columns="D4N", values="V", aggfunc="first")
        m["urbanizacao"] = m["cod_ibge"].map(_num(u["Urbana"]) / _num(u["Total"]))
    except Exception as e:  # noqa: BLE001 — indicador opcional
        print(f"::warning title=ibge::urbanização indisponível ({e})")
        m["urbanizacao"] = None

    pib = sidra(t["pib"], http)
    m = m.merge(pib[["D1C", "V", "D3N"]].rename(columns={"D1C": "cod_ibge", "V": "pib_mil", "D3N": "ano_pib"}),
                on="cod_ibge", how="left")
    m["pib_mil"] = _num(m["pib_mil"])
    m["pib_per_capita"] = m["pib_mil"] * 1000 / m["pop_2022"]
    m["regiao"] = m["cod_ibge"].str[0].map({"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"})
    m["capital"] = m["cod_ibge"].isin([str(x) for x in g["capitais"]])
    return m.drop(columns=["nome_uf"])


def malhas(cfg: dict, destino: Path) -> None:
    g = cfg["ibge"]
    destino.mkdir(parents=True, exist_ok=True)
    for nome, arq, simpl in (("municipios", g["malha_municipios"], g["simplificacao_municipios"]),
                              ("ufs", g["malha_ufs"], g["simplificacao_ufs"])):
        alvo = destino / f"{nome}.topo.json"
        if alvo.exists():
            print(f"{alvo.name}: já existe")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            z = Path(tmp) / "malha.zip"
            with requests.get(f"{g['geoftp']}/{arq}", stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(z, "wb") as f:
                    for ch in r.iter_content(1 << 20):
                        f.write(ch)
            zipfile.ZipFile(z).extractall(tmp)
            shp = next(Path(tmp).rglob("*.shp"))
            # mapshaper: simplifica mantendo todos os polígonos, só o código e o nome, coordenadas quantizadas
            campos = "CD_MUN,NM_MUN,SIGLA_UF" if nome == "municipios" else "CD_UF,SIGLA_UF,NM_UF"
            cmd = ["npx", "-y", f"mapshaper@{g['mapshaper']}", str(shp), "-proj", "wgs84",
                   "-simplify", simpl, "keep-shapes", "-filter-fields", campos,
                   "-o", "format=topojson", "quantization=1e5", f"id-field={campos.split(',')[0]}", str(alvo)]
            subprocess.run(cmd, check=True)
        print(f"{alvo.name}: {alvo.stat().st_size / 1e6:.2f} MB")


def main() -> int:
    cfg = load_config()
    g = cfg["ibge"]
    out = ROOT / g["caminhos"]["staging"]
    out.mkdir(parents=True, exist_ok=True)
    arq = out / "municipios.parquet"
    velho = (not arq.exists()) or (time.time() - arq.stat().st_mtime > 86400 * int(g.get("dias_validade", 30)))
    meta = ROOT / g["caminhos"]["metadata"]
    meta.mkdir(parents=True, exist_ok=True)
    if velho:
        m = indicadores(cfg)
        m.to_parquet(arq, index=False)
        info = {"municipios": len(m), "ano_pib": m["ano_pib"].dropna().max(), "ano_pop_estimada": m["ano_pop_estimada"].dropna().max(),
                "executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        (meta / "_ultima_execucao.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(info)
    else:
        print("Indicadores do IBGE recentes; mantidos")
    try:
        malhas(cfg, ROOT / g["caminhos"]["geo"])
    except Exception as e:  # noqa: BLE001 — sem malha, o resto segue
        print(f"::error title=ibge::malha: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
