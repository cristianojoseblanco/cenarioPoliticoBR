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
from urllib.parse import quote, unquote

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
                            "artigo": unquote(b["artigo"]["value"].rsplit("/", 1)[-1])})
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


def visitas(cfg, mapa: pd.DataFrame, velho: pd.DataFrame) -> pd.DataFrame:
    """Incremental e devagar: a API da Wikimedia limita pedidos vindos de servidores de nuvem.

    Cada execução pede no máximo `wiki_max_por_execucao` verbetes, primeiro os nunca baixados e depois os mais
    desatualizados, só a partir do último mês já guardado. Num 429 espera e tenta uma vez; no segundo, para.
    """
    a = cfg["atencao"]
    hoje = pd.Timestamp.now()
    fim = hoje.strftime("%Y%m01")
    mes_fechado = (hoje.replace(day=1) - pd.Timedelta(days=1)).strftime("%Y%m")
    ult = velho.groupby(["casa", "parlamentar_id"])["mes"].max() if len(velho) else pd.Series(dtype=str)
    feitos = set(velho[["casa", "parlamentar_id"]].itertuples(index=False, name=None)) if len(velho) else set()
    fila = []
    for r in mapa.itertuples():
        k = (r.casa, r.parlamentar_id)
        u = ult.get(k) if k in ult.index else None
        if u is not None and u >= mes_fechado:
            continue
        fila.append((0 if k not in feitos else 1, u or "", r))
    fila.sort(key=lambda x: (x[0], x[1]))
    fila = fila[: int(a["wiki_max_por_execucao"])]
    linhas, status, bloqueios = [], {}, 0
    for _, u, r in fila:
        desde = (u or a["wiki_desde"])
        url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/pt.wikipedia/all-access/user/"
               f"{quote(r.artigo, safe='')}/monthly/{desde}0100/{fim}00")
        try:
            x = requests.get(url, headers=_ua(cfg), timeout=60)
        except requests.RequestException as e:
            status[type(e).__name__] = status.get(type(e).__name__, 0) + 1
            continue
        if x.status_code == 429:
            bloqueios += 1
            if bloqueios >= 2:
                print("wikipédia: limite da API atingido; o resto fica para a próxima execução")
                break
            time.sleep(60)
            x = requests.get(url, headers=_ua(cfg), timeout=60)
        status[x.status_code] = status.get(x.status_code, 0) + 1
        if x.status_code == 200:
            for it in x.json().get("items", []):
                linhas.append({"casa": r.casa, "parlamentar_id": r.parlamentar_id, "mes": it["timestamp"][:6],
                               "visitas": int(it["views"])})
        time.sleep(float(a["wiki_pausa_s"]))
    print(f"wikipédia: {len(fila)} verbetes na fila; respostas {status}")
    novo = pd.DataFrame(linhas, columns=["casa", "parlamentar_id", "mes", "visitas"])
    tudo = pd.concat([velho, novo], ignore_index=True)
    return tudo.drop_duplicates(["casa", "parlamentar_id", "mes"], keep="last")


def discursos(cfg) -> pd.DataFrame:
    """Por deputado e legislatura (a API não aceita intervalos de mais de 4 anos; `idLegislatura` resolve).

    Na primeira vez baixa as legislaturas de `atencao.discursos_legislaturas`; depois, só a mais recente.
    """
    c, a = cfg["camara"], cfg["atencao"]
    destino = ROOT / a["caminhos"]["staging"] / "discursos.parquet"
    velho = pd.read_parquet(destino) if destino.exists() else pd.DataFrame()
    P = path(cfg, "processed")
    d = pd.read_parquet(P / "deputados", columns=["deputado_id", "idLegislaturaInicial", "idLegislaturaFinal"])
    d["ini"] = pd.to_numeric(d["idLegislaturaInicial"], errors="coerce")
    d["fim"] = pd.to_numeric(d["idLegislaturaFinal"], errors="coerce")
    legs = [int(x) for x in a["discursos_legislaturas"]]
    if len(velho) and "legislatura" in velho.columns:
        feitas = set(velho["legislatura"].unique())
        legs = [x for x in legs if x not in feitas] + [max(legs)]
        velho = velho[~velho["legislatura"].isin(legs)]
    tarefas = [(r.deputado_id, leg) for r in d.itertuples() for leg in sorted(set(legs))
               if r.ini <= leg <= r.fim]
    print(f"discursos: {len(tarefas)} pares deputado × legislatura ({sorted(set(legs))})")
    headers = {"User-Agent": cfg["http"]["user_agent"], "Accept": "application/json"}

    def um(tarefa):
        dep, leg = tarefa
        linhas, pagina = [], 1
        while True:
            js = None
            for tentativa in range(3):
                try:
                    r = requests.get(f"{c['api_base']}/deputados/{dep}/discursos", headers=headers, timeout=90,
                                     params={"idLegislatura": leg, "itens": 100, "pagina": pagina})
                except requests.RequestException:
                    time.sleep(2 ** tentativa)
                    continue
                if r.status_code == 429 or r.status_code >= 500:
                    time.sleep(2 ** tentativa)
                    continue
                if r.status_code == 200:
                    js = r.json()
                break
            if js is None:
                return linhas, 1
            dados = js.get("dados", [])
            for x in dados:
                linhas.append({"deputado_id": dep, "legislatura": leg, "data": str(x.get("dataHoraInicio") or "")[:10],
                               "hora": str(x.get("dataHoraInicio") or "")[11:16],
                               "tipo": x.get("tipoDiscurso"), "fase": (x.get("faseEvento") or {}).get("titulo"),
                               "sumario": (x.get("sumario") or "")[:600], "keywords": (x.get("keywords") or "")[:300],
                               "palavras": len((x.get("transcricao") or "").split())})
            if len(dados) < 100:
                return linhas, 0
            pagina += 1

    from concurrent.futures import ThreadPoolExecutor
    linhas, falhas = [], 0
    with ThreadPoolExecutor(int(a.get("paralelo", 6))) as ex:
        for k, (ls, f) in enumerate(ex.map(um, tarefas), 1):
            linhas += ls
            falhas += f
            if k % 200 == 0:
                print(f"  discursos: {k}/{len(tarefas)}, {len(linhas)} discursos, {falhas} falhas", flush=True)
    if falhas:
        print(f"::warning title=discursos::{falhas} pares sem resposta")
    return pd.concat([velho, pd.DataFrame(linhas)], ignore_index=True)


def _wiki(cfg, base) -> None:
    g = pessoas(cfg)
    mp = wikidata(cfg, g)
    mp.to_parquet(base / "wikipedia_mapa.parquet", index=False)
    print(f"wikipédia: {len(mp)} de {len(g)} parlamentares com verbete identificado")
    vp = base / "wikipedia_visitas.parquet"
    v = visitas(cfg, mp, pd.read_parquet(vp) if vp.exists() else pd.DataFrame())
    v.to_parquet(base / "wikipedia_visitas.parquet", index=False)
    print(f"wikipédia: {len(v)} meses × parlamentar")


def _discursos(cfg, base) -> None:
    d = discursos(cfg)
    d.to_parquet(base / "discursos.parquet", index=False)
    print(f"discursos: {len(d)}")


def main() -> int:
    cfg = load_config()
    base = ROOT / cfg["atencao"]["caminhos"]["staging"]
    base.mkdir(parents=True, exist_ok=True)
    partes = sys.argv[1:] or ["wiki", "discursos"]
    for nome, fn in (("wiki", _wiki), ("discursos", _discursos)):
        if nome in partes:
            try:
                fn(cfg, base)
            except Exception as e:  # noqa: BLE001 — uma fonte fora do ar não derruba a outra
                print(f"::error title=atenção::{nome}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
