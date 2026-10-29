"""Atenção pública e fala: visitas mensais ao verbete na Wikipédia e discursos na Câmara (Bloco C).

1. Wikipédia: o verbete de cada parlamentar é achado no Wikidata (pessoa brasileira com a mesma data de
   nascimento e nome compatível, com artigo na Wikipédia em português); as visitas mensais vêm da API de
   pageviews da Wikimedia (só usuários, sem robôs).
2. Discursos (Câmara, API /deputados/{id}/discursos): data, tipo, fase, sumário, palavras-chave e tamanho da
   transcrição. A transcrição inteira não é guardada.

Staging: data/staging/atencao/{wikipedia_mapa.parquet, wikipedia_visitas.parquet, discursos.parquet}.
Uso: python -m src.ingestion.atencao
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests

from src.config import ROOT, load_config, path, para_senado
from src.ingestion.agendas import norm
from src.ingestion.camara_api import _get

SPARQL = "https://query.wikidata.org/sparql"


def _ua(cfg):
    return {"User-Agent": cfg["http"]["user_agent"].encode("ascii", "ignore").decode()}


def pessoas(cfg) -> pd.DataFrame:
    P = path(cfg, "processed")
    d = pd.read_parquet(P / "deputados", columns=["deputado_id", "nome", "nomeCivil", "dataNascimento", "idLegislaturaFinal"])
    d = d[pd.to_numeric(d["idLegislaturaFinal"], errors="coerce") >= 56]
    out = pd.DataFrame({"casa": "camara", "parlamentar_id": d["deputado_id"], "nome": d["nome"],
                        "nome_civil": d["nomeCivil"], "nascimento": d["dataNascimento"]})
    sp = ROOT / cfg["atencao"]["senadores_nascimento"]
    if sp.exists():
        s = pd.read_parquet(sp)
        out = pd.concat([out, s.assign(casa="senado")], ignore_index=True)
    return out.dropna(subset=["nascimento"])


def wikidata(cfg, gente: pd.DataFrame) -> pd.DataFrame:
    datas = sorted(set(gente["nascimento"].str[:10]))
    achados = []
    for i in range(0, len(datas), 150):
        vals = " ".join(f'"{d}T00:00:00Z"^^xsd:dateTime' for d in datas[i:i + 150])
        q = f"""SELECT ?p ?nasc ?rotulo ?artigo WHERE {{
  VALUES ?nasc {{ {vals} }}
  ?p wdt:P569 ?nasc; wdt:P31 wd:Q5; wdt:P27 wd:Q155.
  ?artigo schema:about ?p; schema:isPartOf <https://pt.wikipedia.org/>.
  OPTIONAL {{ ?p rdfs:label ?rotulo FILTER(LANG(?rotulo) = "pt") }}
}}"""
        r = requests.post(SPARQL, data={"query": q, "format": "json"}, headers=_ua(cfg), timeout=120)
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            achados.append({"qid": b["p"]["value"].rsplit("/", 1)[-1], "nascimento": b["nasc"]["value"][:10],
                            "rotulo": b.get("rotulo", {}).get("value", ""),
                            "artigo": b["artigo"]["value"].rsplit("/", 1)[-1]})
        time.sleep(1)
    w = pd.DataFrame(achados).drop_duplicates(["qid", "artigo"])
    print(f"wikidata: {len(w)} candidatos")
    m = gente.assign(nascimento=gente["nascimento"].str[:10]).merge(w, on="nascimento")

    def casa_nome(r):
        rot = set(norm(r.rotulo).split()) | set(norm(r.artigo.replace("_", " ")).split())
        for nome in (r.nome, r.nome_civil):
            t = [x for x in norm(nome).split() if len(x) > 2]
            if t and sum(x in rot for x in t) >= min(2, len(t)):
                return True
        return False

    m = m[m.apply(casa_nome, axis=1)]
    # um verbete por parlamentar; se houver mais de um candidato, nenhum (ambíguo)
    m = m[m.groupby(["casa", "parlamentar_id"])["qid"].transform("nunique") == 1]
    return m.drop_duplicates(["casa", "parlamentar_id"])[["casa", "parlamentar_id", "qid", "artigo"]]


def visitas(cfg, mapa: pd.DataFrame) -> pd.DataFrame:
    a = cfg["atencao"]
    fim = datetime.now().strftime("%Y%m01")
    linhas = []
    for r in mapa.itertuples():
        url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/pt.wikipedia/all-access/user/"
               f"{quote(r.artigo, safe='')}/monthly/{a['wiki_desde']}0100/{fim}00")
        try:
            x = requests.get(url, headers=_ua(cfg), timeout=60)
            if x.status_code == 404:
                continue
            x.raise_for_status()
        except requests.RequestException as e:
            print(f"  {r.artigo}: {e}", file=sys.stderr)
            continue
        for it in x.json().get("items", []):
            linhas.append({"casa": r.casa, "parlamentar_id": r.parlamentar_id, "mes": it["timestamp"][:6],
                           "visitas": int(it["views"])})
        time.sleep(0.05)
    return pd.DataFrame(linhas)


def discursos(cfg) -> pd.DataFrame:
    c, a = cfg["camara"], cfg["atencao"]
    destino = ROOT / a["caminhos"]["staging"] / "discursos.parquet"
    velho = pd.read_parquet(destino) if destino.exists() else pd.DataFrame()
    P = path(cfg, "processed")
    d = pd.read_parquet(P / "deputados", columns=["deputado_id", "idLegislaturaFinal"])
    ids = sorted(d.loc[pd.to_numeric(d["idLegislaturaFinal"], errors="coerce") >= 56, "deputado_id"], key=int)
    inicio = a["discursos_desde"]
    if len(velho):
        # só o período recente é baixado de novo
        inicio = (pd.Timestamp.now() - pd.Timedelta(days=int(a["recarregar_dias"]))).strftime("%Y-%m-%d")
        velho = velho[velho["data"] < inicio]
    linhas = []
    for k, dep in enumerate(ids, 1):
        pagina = 1
        while True:
            try:
                js = _get(f"{c['api_base']}/deputados/{dep}/discursos", cfg["http"],
                          {"dataInicio": inicio, "dataFim": datetime.now().strftime("%Y-%m-%d"),
                           "itens": 100, "pagina": pagina, "ordenarPor": "dataHoraInicio", "ordem": "ASC"})
            except RuntimeError:
                break
            dados = js.get("dados", [])
            for x in dados:
                linhas.append({"deputado_id": dep, "data": str(x.get("dataHoraInicio") or "")[:10],
                               "hora": str(x.get("dataHoraInicio") or "")[11:16],
                               "tipo": x.get("tipoDiscurso"), "fase": (x.get("faseEvento") or {}).get("titulo"),
                               "sumario": (x.get("sumario") or "")[:600], "keywords": (x.get("keywords") or "")[:300],
                               "palavras": len((x.get("transcricao") or "").split())})
            if len(dados) < 100:
                break
            pagina += 1
            time.sleep(c["api_pausa_s"])
        if k % 100 == 0:
            print(f"  discursos: {k}/{len(ids)} deputados, {len(linhas)} discursos")
        time.sleep(c["api_pausa_s"])
    return pd.concat([velho, pd.DataFrame(linhas)], ignore_index=True)


def main() -> int:
    cfg = load_config()
    base = ROOT / cfg["atencao"]["caminhos"]["staging"]
    base.mkdir(parents=True, exist_ok=True)
    try:
        g = pessoas(cfg)
        mp = wikidata(cfg, g)
        mp.to_parquet(base / "wikipedia_mapa.parquet", index=False)
        print(f"wikipédia: {len(mp)} de {len(g)} parlamentares com verbete identificado")
        v = visitas(cfg, mp)
        v.to_parquet(base / "wikipedia_visitas.parquet", index=False)
        print(f"wikipédia: {len(v)} meses × parlamentar")
    except Exception as e:  # noqa: BLE001
        print(f"::error title=atenção::wikipédia: {e}")
    try:
        d = discursos(cfg)
        d.to_parquet(base / "discursos.parquet", index=False)
        print(f"discursos: {len(d)}")
    except Exception as e:  # noqa: BLE001
        print(f"::error title=atenção::discursos: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
