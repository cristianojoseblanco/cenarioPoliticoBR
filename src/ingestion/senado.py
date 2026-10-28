"""Ingestão do Senado Federal (dados abertos): votações nominais do Plenário, votos e orientações.

Por ano:
  {api_base}/votacao?ano=AAAA                                      votações com voto de cada senador
  {api_base}/plenario/votacao/orientacaoBancada/AAAA0101/AAAA1231.json   orientação das lideranças

Staging (texto, como veio) em data/staging/senado/{votacoes,votos,orientacoes}/ano=AAAA/part-0.parquet.
Idempotente: resposta com o mesmo SHA-256 não é reescrita; anos antigos já baixados são pulados.

Uso: python -m src.ingestion.senado            (ANOS=2023,2024 sobrescreve)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from src.config import ROOT, load_config


def _get(url: str, http: dict) -> bytes | None:
    headers = {"User-Agent": http["user_agent"], "Accept": "application/json"}
    for tentativa in range(1, http["retries"] + 1):
        try:
            r = requests.get(url, headers=headers, timeout=http["timeout_s"])
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            espera = 2 ** tentativa
            print(f"  {url}: tentativa {tentativa} falhou ({e}); nova em {espera}s", file=sys.stderr)
            time.sleep(espera)
    raise RuntimeError(f"Falha em {url}")


def _txt(x):
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False)
    return str(x)


def converter_votacoes(dados: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    vt, vo = [], []
    for v in dados:
        linha = {k: _txt(val) for k, val in v.items() if k != "votos"}
        vt.append(linha)
        for x in v.get("votos") or []:
            vo.append({"codigoSessaoVotacao": _txt(v.get("codigoSessaoVotacao")), **{k: _txt(val) for k, val in x.items()}})
    return pd.DataFrame(vt), pd.DataFrame(vo)


def converter_orientacoes(js: dict) -> pd.DataFrame:
    linhas = []
    for v in js.get("votacoes") or []:
        base = {k: _txt(v.get(k)) for k in ("codigoVotacaoSve", "sequencialVotacao", "dataInicioVotacao", "dataTerminoVotacao",
                                            "siglaTipoMateria", "numeroMateria", "anoMateria", "qtdVotosSim", "qtdVotosNao",
                                            "qtdVotosAbstencao", "qtdObstrucoes")}
        for o in v.get("orientacoesLideranca") or []:
            linhas.append({**base, "partido": _txt(o.get("partido")), "voto": _txt(o.get("voto")),
                           "dataHora": _txt(o.get("dataHora"))})
    return pd.DataFrame(linhas)


def main() -> int:
    cfg = load_config()
    s = cfg["senado"]
    base, http = s["api_base"], cfg["http"]
    staging = ROOT / s["caminhos"]["staging"]
    meta_dir = ROOT / s["caminhos"]["metadata"]
    meta_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.get("ANOS", "").strip()
    a = s["anos_padrao"]
    anos = [int(x) for x in env.split(",") if x.strip()] if env else (
        list(range(int(a["desde"]), datetime.now().year + 1)) if isinstance(a, dict) else list(a))
    # anos do período padrão que ainda não existem no staging entram sempre (mesmo com ANOS definido)
    padrao = list(range(int(a["desde"]), datetime.now().year + 1)) if isinstance(a, dict) else list(a)
    faltando = [y for y in padrao if not (staging / "votacoes" / f"ano={y}" / "part-0.parquet").exists()]
    anos = sorted(set(anos) | set(faltando))
    recentes = s.get("recarregar_anos_recentes", 2)
    registro = []
    for ano in anos:
        destino = staging / "votacoes" / f"ano={ano}" / "part-0.parquet"
        meta_p = meta_dir / f"{ano}.json"
        if destino.exists() and meta_p.exists() and ano < datetime.now().year - recentes:
            print(f"{ano}: já consolidado, pulado")
            continue
        print(f"{ano}: baixando")
        bruto_v = _get(f"{base}/votacao?ano={ano}", http)
        bruto_o = _get(f"{base}/plenario/votacao/orientacaoBancada/{ano}0101/{ano}1231.json", http)
        sha = hashlib.sha256((bruto_v or b"") + (bruto_o or b"")).hexdigest()
        antes = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        if antes.get("sha256") == sha and destino.exists():
            print(f"{ano}: sem mudança")
            continue
        vt, vo = converter_votacoes(json.loads(bruto_v) if bruto_v else [])
        ori = converter_orientacoes(json.loads(bruto_o) if bruto_o else {})
        for nome, df in (("votacoes", vt), ("votos", vo), ("orientacoes", ori)):
            d = staging / nome / f"ano={ano}"
            d.mkdir(parents=True, exist_ok=True)
            df.astype("string").to_parquet(d / "part-0.parquet", index=False)
        info = {"ano": ano, "sha256": sha, "votacoes": len(vt), "votos": len(vo), "orientacoes": len(ori),
                "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        meta_p.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        registro.append(info)
        print(f"  {len(vt)} votações, {len(vo)} votos, {len(ori)} orientações")
        time.sleep(s.get("pausa_s", 0.5))
    (meta_dir / "_ultima_execucao.json").write_text(json.dumps(
        {"executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "anos": registro}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
