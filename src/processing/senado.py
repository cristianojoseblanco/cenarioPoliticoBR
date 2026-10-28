"""Camada processada do Senado no MESMO formato da Câmara (data/processed/senado/).

Assim os módulos de análise (rede, fatias, governabilidade, dimensões, dinâmica, mudanças, modelo)
rodam no Senado sem mudança, só com outra configuração (`senado.analise`).

Tabelas: votacoes, votos, orientacoes, votacao_proposicao, proposicoes, proposicao_tema (vazia: o Senado
não publica tema no mesmo padrão), deputados (= senadores; o nome da coluna é mantido de propósito).

Regras:
  - votação nominal = aberta (votacaoSecreta = "N"); nas secretas o voto vem só como "Votou";
  - voto e orientação padronizados pelos mapas `senado.mapa_votos` e `senado.mapa_orientacoes`;
  - orientação ligada à votação pelo número sequencial da votação e pela data;
  - placar calculado dos votos (a fonte traz os totais vazios).

Uso: python -m src.processing.senado
"""
from __future__ import annotations

import shutil
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, load_config


def _ler(staging, nome):
    p = staging / nome
    arqs = sorted(p.rglob("*.parquet"))
    if not arqs:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(a) for a in arqs], ignore_index=True)


def legislatura_da_data(datas: pd.Series, legs: dict) -> pd.Series:
    out = pd.Series(np.nan, index=datas.index)
    for leg, per in legs.items():
        m = (datas >= pd.Timestamp(per["inicio"])) & (datas <= pd.Timestamp(per["fim"]))
        out[m] = int(leg)
    return out.astype("Int64")


def construir(cfg: dict) -> dict[str, pd.DataFrame]:
    s = cfg["senado"]
    st = ROOT / s["caminhos"]["staging"]
    vt, vo, ori = _ler(st, "votacoes"), _ler(st, "votos"), _ler(st, "orientacoes")
    mv, mo = s["mapa_votos"], s["mapa_orientacoes"]
    apel = s.get("apelidos_bancada", {})

    vt = vt.drop_duplicates("codigoSessaoVotacao")
    vt["data"] = pd.to_datetime(vt["dataSessao"]).dt.date
    vt["nominal"] = vt["votacaoSecreta"].eq("N")
    # horário da votação vem do serviço de orientações (mesmo sequencial e mesma data)
    if len(ori):
        o1 = ori.drop_duplicates(["sequencialVotacao", "dataInicioVotacao"]).copy()
        o1["data"] = pd.to_datetime(o1["dataInicioVotacao"]).dt.date
        hora = o1.set_index(["sequencialVotacao", "data"])["dataInicioVotacao"]
        hora = hora[~hora.index.duplicated()]
        vt["data_hora_registro"] = pd.to_datetime(
            pd.Series(list(zip(vt["sequencialVotacao"], vt["data"]))).map(hora).to_numpy())
    else:
        vt["data_hora_registro"] = pd.NaT

    vo = vo.merge(vt[["codigoSessaoVotacao", "data", "nominal"]], on="codigoSessaoVotacao")
    vo = vo[vo["nominal"]]
    vo["voto"] = vo["siglaVotoParlamentar"].map(lambda x: mv.get(x, x))
    contagem = vo.groupby("codigoSessaoVotacao")["voto"].agg(
        placar_sim=lambda x: int((x == "Sim").sum()), placar_nao=lambda x: int((x == "Não").sum()),
        n_votos_registrados="size")
    vt = vt.join(contagem, on="codigoSessaoVotacao")

    votacoes = pd.DataFrame({
        "votacao_id": vt["codigoSessaoVotacao"], "data": pd.to_datetime(vt["data"]),
        "data_hora_registro": vt["data_hora_registro"], "orgao_id": "SF-PLEN", "sigla_orgao": "PLEN",
        "evento_id": vt["codigoSessao"], "descricao": vt["descricaoVotacao"],
        "aprovacao": vt["resultadoVotacao"].map({"A": 1, "R": 0}).astype("Int64"),
        "placar_sim": vt["placar_sim"].fillna(0).astype(int), "placar_nao": vt["placar_nao"].fillna(0).astype(int),
        "placar_outros": (vt["n_votos_registrados"].fillna(0) - vt["placar_sim"].fillna(0) - vt["placar_nao"].fillna(0)).astype(int),
        "n_votos_registrados": vt["n_votos_registrados"].fillna(0).astype(int), "nominal": vt["nominal"],
    })
    votacoes["ano"] = votacoes["data"].dt.year
    votacoes["data"] = votacoes["data"].dt.date

    votos = pd.DataFrame({
        "votacao_id": vo["codigoSessaoVotacao"], "deputado_id": vo["codigoParlamentar"], "voto": vo["voto"],
        "data_hora_voto": pd.NaT, "partido_na_votacao": vo["siglaPartidoParlamentar"].map(lambda x: apel.get(x, x)),
        "uf": vo["siglaUFParlamentar"],
        "legislatura": legislatura_da_data(pd.to_datetime(vo["data"]), cfg["legislaturas"]),
    })
    votos["ano"] = pd.to_datetime(vo["data"]).dt.year.to_numpy()

    if len(ori):
        ori = ori.copy()
        ori["data"] = pd.to_datetime(ori["dataInicioVotacao"]).dt.date
        chave = vt.set_index(["sequencialVotacao", "data"])["codigoSessaoVotacao"]
        chave = chave[~chave.index.duplicated()]
        ori["votacao_id"] = pd.Series(list(zip(ori["sequencialVotacao"], ori["data"]))).map(chave).to_numpy()
        ori = ori.dropna(subset=["votacao_id"])
        orientacoes = pd.DataFrame({
            "votacao_id": ori["votacao_id"], "sigla_orgao": "PLEN",
            "bancada": ori["partido"].map(lambda x: apel.get(x, x)),
            "orientacao": ori["voto"].map(lambda x: mo.get(x, x)),
            "ano": pd.to_datetime(ori["data"]).dt.year.astype(int).to_numpy(),
        }).drop_duplicates(["votacao_id", "bancada"])
    else:
        orientacoes = pd.DataFrame(columns=["votacao_id", "sigla_orgao", "bancada", "orientacao", "ano"])

    vp = pd.DataFrame({
        "votacao_id": vt["codigoSessaoVotacao"], "proposicao_id": vt["codigoMateria"], "sigla_tipo": vt["sigla"],
        "numero": pd.to_numeric(vt["numero"], errors="coerce").astype("Int64"),
        "ano_apresentacao": pd.to_numeric(vt["ano"], errors="coerce").astype("Int64"),
    }).dropna(subset=["proposicao_id"])
    proposicoes = vt.drop_duplicates("codigoMateria").dropna(subset=["codigoMateria"])
    proposicoes = pd.DataFrame({
        "proposicao_id": proposicoes["codigoMateria"], "sigla_tipo": proposicoes["sigla"],
        "descricao_tipo": None, "numero": pd.to_numeric(proposicoes["numero"], errors="coerce").astype("Int64"),
        "ano_apresentacao": pd.to_numeric(proposicoes["ano"], errors="coerce").astype("Int64"),
        "data_apresentacao": pd.to_datetime(proposicoes["dataApresentacao"], errors="coerce"),
        "ementa": proposicoes["ementa"], "ementa_detalhada": None, "keywords": None, "principal_id": None,
        "situacao": None, "regime": None, "apreciacao": None, "url_inteiro_teor": None,
    })
    tema = pd.DataFrame({"proposicao_id": pd.Series(dtype="string"), "cod_tema": pd.Series(dtype="Int64"),
                         "tema": pd.Series(dtype="string"), "relevancia": pd.Series(dtype="Int64"),
                         "origem": pd.Series(dtype="string")})
    ult = vo.sort_values("data").groupby("codigoParlamentar").last()
    senadores = pd.DataFrame({"deputado_id": ult.index, "nome": ult["nomeParlamentar"].to_numpy(),
                              "uf": ult["siglaUFParlamentar"].to_numpy(), "sexo": ult.get("sexoParlamentar")})
    return {"votacoes": votacoes, "votos": votos, "orientacoes": orientacoes, "votacao_proposicao": vp,
            "proposicoes": proposicoes, "proposicao_tema": tema, "deputados": senadores}


def main() -> int:
    cfg = load_config()
    out = ROOT / cfg["senado"]["caminhos"]["processed"]
    tabelas = construir(cfg)
    if out.exists():
        shutil.rmtree(out)
    for nome, df in tabelas.items():
        if nome in ("votos", "votacoes"):
            for ano, g in df.groupby("ano"):
                d = out / nome / f"ano={ano}"
                d.mkdir(parents=True, exist_ok=True)
                g.drop(columns="ano").to_parquet(d / "part-0.parquet", index=False)
        else:
            (out / nome).mkdir(parents=True, exist_ok=True)
            df.to_parquet(out / nome / "part-0.parquet", index=False)
        print(f"{nome}: {len(df):,}".replace(",", "."))
    v = tabelas["votacoes"]
    o = tabelas["orientacoes"]
    nom = v[v["nominal"]]
    gov = o[o["bancada"].isin(cfg["senado"]["analise"]["governabilidade"]["bancada_governo"])]["votacao_id"].nunique()
    print(f"nominais abertas: {len(nom)}; com orientação do Governo: {gov} ({100 * gov / max(len(nom), 1):.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
