"""Ingestão via API REST da Câmara: histórico de mandato de cada deputado.

O histórico traz cada mudança de situação (Exercício, Afastado, Fim de Mandato...),
com data e hora. É a base para saber quem estava em exercício em cada votação.

Deputados consultados: os de `camara.legislaturas_historico` + todos que aparecem
nos votos já ingeridos. Saída em staging, tudo como texto, com metadados.

Uso: python -m src.ingestion.camara_api
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from src.config import connect, load_config, path

DATASET = "deputadosHistorico"


def _get(url: str, http: dict, params: dict | None = None) -> dict:
    headers = {"User-Agent": http["user_agent"], "Accept": "application/json"}
    for tentativa in range(1, http["retries"] + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            espera = 2 ** tentativa
            print(f"  {url}: tentativa {tentativa} falhou ({e}); nova tentativa em {espera}s", file=sys.stderr)
            time.sleep(espera)
    raise RuntimeError(f"Falha em {url}")


def ids_deputados(cfg: dict) -> list[str]:
    c = cfg["camara"]
    ids = set()
    for leg in c.get("legislaturas_historico", []):
        pagina = 1
        while True:
            try:
                js = _get(f"{c['api_base']}/deputados", cfg["http"],
                          {"idLegislatura": leg, "itens": 100, "pagina": pagina, "ordem": "ASC", "ordenarPor": "id"})
            except RuntimeError as e:  # legislatura futura ou API fora do ar: segue com o que tem
                print(f"  legislatura {leg}: {e}", file=sys.stderr)
                break
            dados = js.get("dados", [])
            ids |= {str(d["id"]) for d in dados}
            if len(dados) < 100:
                break
            pagina += 1
            time.sleep(c["api_pausa_s"])
    vv = path(cfg, "staging") / "votacoesVotos"
    if any(vv.rglob("*.parquet")):
        con = connect(cfg)
        rows = con.execute(
            f"SELECT DISTINCT deputado_id FROM read_parquet('{vv.as_posix()}/**/*.parquet', hive_partitioning = true)"
        ).fetchall()
        ids |= {r[0] for r in rows if r[0]}
    return sorted(ids, key=int)


def main() -> int:
    cfg = load_config()
    c = cfg["camara"]
    ids = ids_deputados(cfg)
    print(f"Deputados a consultar: {len(ids)}")
    linhas, erros = [], []
    for i, dep in enumerate(ids, 1):
        try:
            js = _get(f"{c['api_base']}/deputados/{dep}/historico", cfg["http"])
            for d in js.get("dados", []):
                linhas.append({"deputado_id": dep, **{k: (None if v is None else str(v)) for k, v in d.items()}})
        except Exception as e:
            erros.append({"deputado_id": dep, "erro": str(e)})
        if i % 100 == 0:
            print(f"  {i} de {len(ids)}")
        time.sleep(c["api_pausa_s"])

    df = pd.DataFrame(linhas).sort_values(["deputado_id", "dataHora"], kind="stable")
    destino = path(cfg, "staging") / DATASET / "part-0.parquet"
    destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = df.to_csv(index=False).encode("utf-8")
    sha = hashlib.sha256(conteudo).hexdigest()
    meta_file = path(cfg, "metadata") / f"{DATASET}.json"
    anterior = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    if sha != anterior.get("sha256") or not destino.exists():
        df.to_parquet(destino, index=False)
        meta_file.write_text(json.dumps({
            "fonte": "camara_api", "dataset": DATASET, "url": f"{c['api_base']}/deputados/{{id}}/historico",
            "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": sha, "linhas": len(df), "deputados": len(ids), "erros": len(erros),
            "transformacao": "JSON -> parquet, todas as colunas como texto",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Atualizado: {len(df)} linhas")
    else:
        print("Sem mudanças")
    if erros:
        print(f"Erros: {erros[:5]}", file=sys.stderr)
    # tolera falhas pontuais; falha só se mais de 5% dos deputados deram erro
    return 1 if len(erros) > 0.05 * max(len(ids), 1) else 0


if __name__ == "__main__":
    sys.exit(main())
