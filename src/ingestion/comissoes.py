"""Ingestão de comissões e tramitação (Câmara).

1. Composição dos órgãos por legislatura (arquivo em lote orgaosDeputados-L{leg}.csv) e cadastro de órgãos
   (orgaos.csv): quem é titular, suplente, presidente ou vice de cada comissão, e quando.
2. Tramitação (API /proposicoes/{id}/tramitacoes) de cada proposição com votação nominal no Plenário:
   regime (urgência ou não), relatores, órgãos por onde passou.

Staging: data/staging/comissoes/{orgaos.parquet, membros/leg=N.parquet, tramitacoes.parquet}.
A tramitação é baixada só para proposições novas ou com movimento nos últimos `recarregar_dias`.
Uso: python -m src.ingestion.comissoes
"""
from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from src.config import ROOT, load_config, path
from src.ingestion.camara_api import _get


def _csv(url: str, http: dict) -> pd.DataFrame | None:
    r = requests.get(url, timeout=http["timeout_s"], headers={"User-Agent": http["user_agent"]})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), sep=";", dtype=str, encoding="utf-8-sig")


def _id(uri) -> str | None:
    s = str(uri or "").rstrip("/")
    return s.rsplit("/", 1)[-1] if s else None


def composicao(cfg: dict, base) -> None:
    c, k = cfg["camara"], cfg["comissoes"]
    o = _csv(f"{c['base_url']}/orgaos/csv/orgaos.csv", cfg["http"])
    if o is not None:
        o.to_parquet(base / "orgaos.parquet", index=False)
        print(f"órgãos: {len(o)}")
    for leg in k["legislaturas"]:
        d = _csv(f"{c['base_url']}/orgaosDeputados/csv/orgaosDeputados-L{leg}.csv", cfg["http"])
        if d is None or d.empty:
            print(f"legislatura {leg}: sem arquivo")
            continue
        d["orgao_id"] = d["uriOrgao"].map(_id)
        d["deputado_id"] = d["uriDeputado"].map(_id)
        d = d.drop(columns=[x for x in ("uriOrgao", "uriDeputado") if x in d.columns])
        (base / "membros").mkdir(parents=True, exist_ok=True)
        d.to_parquet(base / "membros" / f"leg={leg}.parquet", index=False)
        print(f"legislatura {leg}: {len(d)} vínculos em {d['orgao_id'].nunique()} órgãos")


def proposicoes_plenario(cfg: dict) -> list[str]:
    P = path(cfg, "processed")
    v = pd.read_parquet(P / "votacoes", columns=["votacao_id", "sigla_orgao", "nominal"])
    vp = pd.read_parquet(P / "votacao_proposicao", columns=["votacao_id", "proposicao_id"])
    v = v[v["nominal"] & (v["sigla_orgao"] == "PLEN")]
    return sorted(set(vp.loc[vp["votacao_id"].isin(v["votacao_id"]), "proposicao_id"].astype(str)), key=int)


def tramitacoes(cfg: dict, base) -> None:
    c, k = cfg["camara"], cfg["comissoes"]
    destino = base / "tramitacoes.parquet"
    velho = pd.read_parquet(destino) if destino.exists() else pd.DataFrame(columns=["proposicao_id", "dataHora"])
    ids = proposicoes_plenario(cfg)
    limite = (datetime.now() - timedelta(days=int(k["recarregar_dias"]))).strftime("%Y-%m-%d")
    ult = velho.groupby("proposicao_id")["dataHora"].max() if len(velho) else pd.Series(dtype=str)
    fazer = [i for i in ids if i not in ult.index or str(ult[i]) >= limite]
    print(f"tramitação: {len(ids)} proposições, {len(fazer)} a consultar")
    cols = ["dataHora", "sequencia", "siglaOrgao", "regime", "idTipoTramitacao", "descricaoTramitacao",
            "descricaoSituacao", "despacho", "uriUltimoRelator", "apreciacao"]
    novos, erros = [], 0
    for n, pid in enumerate(fazer, 1):
        try:
            js = _get(f"{c['api_base']}/proposicoes/{pid}/tramitacoes", cfg["http"])
        except RuntimeError:
            erros += 1
            continue
        for t in js.get("dados", []):
            linha = {x: t.get(x) for x in cols}
            linha["despacho"] = (linha["despacho"] or "")[:300]
            linha["relator_id"] = _id(linha.pop("uriUltimoRelator"))
            linha["proposicao_id"] = pid
            novos.append(linha)
        if n % 100 == 0:
            print(f"  {n}/{len(fazer)}")
        time.sleep(c["api_pausa_s"])
    if erros:
        print(f"::warning title=tramitação::{erros} proposições sem resposta")
    novo = pd.DataFrame(novos)
    if len(novo):
        novo = novo.astype({x: str for x in novo.columns if x not in ("sequencia",)})
    feitos = set(novo["proposicao_id"]) if len(novo) else set()
    tudo = pd.concat([velho[~velho["proposicao_id"].isin(feitos)], novo], ignore_index=True)
    tudo.to_parquet(destino, index=False)
    print(f"tramitação: {len(tudo)} registros de {tudo['proposicao_id'].nunique()} proposições")


def main() -> int:
    cfg = load_config()
    base = ROOT / cfg["comissoes"]["caminhos"]["staging"]
    base.mkdir(parents=True, exist_ok=True)
    try:
        composicao(cfg, base)
    except Exception as e:  # noqa: BLE001
        print(f"::error title=comissões::composição: {e}")
    try:
        tramitacoes(cfg, base)
    except Exception as e:  # noqa: BLE001
        print(f"::error title=comissões::tramitação: {e}")
    (base / "_ultima_execucao.json").write_text(json.dumps(
        {"executado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
