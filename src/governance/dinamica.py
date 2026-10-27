"""Dinâmica do Plenário mês a mês: agenda, polarização, votações apertadas e peso de quem está fora dos polos.

Definições (por votação nominal do Plenário):
  - polarizada: a maioria do polo A e a maioria do polo B votaram em lados opostos (Sim × Não/Obstrução);
  - apertada: diferença entre os lados menor que `dinamica.margem_apertada` dos votos com valor;
  - votos de fora dos polos: deputados das comunidades que não são nenhum dos dois polos;
  - folga do governo: numa vitória do governo, quantos votos precisariam mudar de lado para o
    resultado se inverter (maioria simples; ignora quórum qualificado) e quanto isso representa
    dos votos de fora dos polos que estavam com o governo.

Agenda: votações nominais por trimestre e por tema oficial (os temas da Etapa 4 + "Outros").

Saídas por legislatura em data/marts/camara/leg<N>/dinamica/.
Uso: python -m src.governance.dinamica
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from src.config import ROOT, connect, load_config, path
from src.networks.votacao import carregar_votos, dec, n, pct


def rodar(c: dict) -> int:
    d = c.get("dinamica", {})
    margem = float(d.get("margem_apertada", 0.10))
    saida = ROOT / c["redes"]["saida"].replace("/redes", "/dinamica")
    saida.mkdir(parents=True, exist_ok=True)
    mapa = c["redes"]["codificacoes"][c["redes"]["principal"]["codificacao"]]

    votos = carregar_votos(c)
    votos["valor"] = votos["voto"].map(mapa)
    com = pd.read_parquet(ROOT / c["redes"]["saida"] / "comunidades.parquet")
    princ = com[com["variante"] == "principal"].set_index("deputado_id")["comunidade"]
    polos = json.loads((ROOT / c["fatias"]["saida"] / "polos.json").read_text(encoding="utf-8"))
    pa, pb = polos["polo_a"], polos["polo_b"]
    gdep = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "deputados.parquet").set_index("deputado_id")
    apoio_com = gdep.join(princ.rename("com"), how="inner").groupby("com")["apoio_gov"].mean()
    polo_gov = pa if apoio_com.get(pa, 0) >= apoio_com.get(pb, 0) else pb
    gv = pd.read_parquet(ROOT / c["governabilidade"]["saida"] / "votacoes.parquet")

    v = votos.dropna(subset=["valor"]).copy()
    v = v[v["valor"] != 0]
    v["com"] = v["deputado_id"].map(princ)
    v["grupo"] = np.where(v["com"] == pa, "A", np.where(v["com"] == pb, "B", np.where(v["com"].notna(), "F", "?")))

    # por votação
    lado = v.groupby(["votacao_id", "grupo"])["valor"].agg(pos=lambda s: (s > 0).sum(), neg=lambda s: (s < 0).sum()).unstack(fill_value=0)
    tot = v.groupby("votacao_id")["valor"].agg(pos=lambda s: (s > 0).sum(), neg=lambda s: (s < 0).sum())
    pv = pd.DataFrame(index=tot.index)
    for g in ("A", "B"):
        p_, n_ = lado.get(("pos", g), 0), lado.get(("neg", g), 0)
        pv[f"maioria_{g}"] = np.sign(p_ - n_)
    pv["polarizada"] = (pv["maioria_A"] * pv["maioria_B"]) < 0
    pv["apertada"] = (tot["pos"] - tot["neg"]).abs() / (tot["pos"] + tot["neg"]) < margem
    pv = pv.join(gv.set_index("votacao_id")[["data", "gov_valor", "governo_venceu"]], how="left")

    fpos, fneg = lado.get(("pos", "F"), 0), lado.get(("neg", "F"), 0)
    gov_lado = np.where(pv["gov_valor"] > 0, tot["pos"], tot["neg"])
    opo_lado = np.where(pv["gov_valor"] > 0, tot["neg"], tot["pos"])
    f_gov = np.where(pv["gov_valor"] > 0, fpos.reindex(pv.index, fill_value=0), fneg.reindex(pv.index, fill_value=0))
    pv["fora_no_lado_gov"] = np.where(pv["gov_valor"].notna(), f_gov / np.maximum(gov_lado, 1), np.nan)
    vence = pv["governo_venceu"] == 1
    virar = np.floor((gov_lado - opo_lado) / 2) + 1
    pv["votos_para_virar"] = np.where(vence, virar, np.nan)
    pv["fracao_fora_para_virar"] = np.where(vence & (f_gov > 0), np.minimum(virar / np.maximum(f_gov, 1), 1), np.nan)
    pv["mes"] = pd.to_datetime(pv["data"]).dt.to_period("M").dt.to_timestamp()
    pv.reset_index().to_parquet(saida / "votacoes.parquet", index=False)

    mensal = pv.groupby("mes").agg(
        votacoes=("polarizada", "size"), polarizadas=("polarizada", "sum"), apertadas=("apertada", "sum"),
        gov_orientou=("gov_valor", lambda s: s.notna().sum()), gov_venceu=("governo_venceu", lambda s: (s == 1).sum()),
        votos_para_virar=("votos_para_virar", "median"), fracao_fora_para_virar=("fracao_fora_para_virar", "median"),
        fora_no_lado_gov=("fora_no_lado_gov", "mean"),
    ).reset_index()
    mensal.to_parquet(saida / "mensal.parquet", index=False)

    # agenda por trimestre e tema
    P = path(c, "processed")
    con = connect(c)
    src = lambda t: f"read_parquet('{(P / t).as_posix()}/**/*.parquet', hive_partitioning = true)"  # noqa: E731
    vt = con.execute(f"""SELECT DISTINCT vp.votacao_id, t.tema FROM {src('votacao_proposicao')} vp
                         JOIN {src('proposicao_tema')} t USING (proposicao_id)""").df()
    temas_ok = set(pd.read_parquet(ROOT / c["fatias"]["saida"] / "fatias.parquet").query("tipo == 'tema'")["fatia"])
    ids = pv.index
    vt = vt[vt["votacao_id"].isin(ids)]
    vt["tema"] = np.where(vt["tema"].isin(temas_ok), vt["tema"], "Outros")
    vt = vt.drop_duplicates()
    vt["tri"] = vt["votacao_id"].map(pd.to_datetime(pv["data"]).dt.to_period("Q").dt.start_time)
    agenda = vt.groupby(["tri", "tema"])["votacao_id"].nunique().rename("votacoes").reset_index()
    agenda.to_parquet(saida / "agenda.parquet", index=False)

    gvv = pv[pv["governo_venceu"] == 1]
    resumo = {
        "polo_a": pa, "polo_b": pb, "polo_governo": polo_gov, "margem_apertada": margem,
        "votacoes": int(len(pv)), "polarizadas": int(pv["polarizada"].sum()), "apertadas": int(pv["apertada"].sum()),
        "vitorias_gov": int(len(gvv)), "votos_para_virar_mediana": float(gvv["votos_para_virar"].median()),
        "fracao_fora_para_virar_mediana": float(gvv["fracao_fora_para_virar"].median()),
        "fora_no_lado_gov_medio": float(gvv["fora_no_lado_gov"].mean()),
    }
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# Dinâmica do Plenário", "",
         f"Polo A = {pa}; polo B = {pb}; polo mais governista = {polo_gov}. Fora dos polos = demais comunidades.", "",
         f"- Votações polarizadas (maiorias dos polos em lados opostos): {pct(resumo['polarizadas'], resumo['votacoes'])}",
         f"- Votações apertadas (margem abaixo de {dec(100 * margem, 0)}%): {pct(resumo['apertadas'], resumo['votacoes'])}",
         f"- Folga do governo nas vitórias (mediana): {n(resumo['votos_para_virar_mediana'])} votos precisariam mudar de lado, "
         f"ou {dec(100 * resumo['fracao_fora_para_virar_mediana'], 1)}% dos votos de fora dos polos que estavam com o governo",
         f"- Parcela média dos votos do lado do governo vinda de fora dos polos: {dec(100 * resumo['fora_no_lado_gov_medio'], 1)}%",
         "", "## Por semestre", "",
         "| Semestre | Votações | Polarizadas | Apertadas | Vitórias do governo | Folga mediana (votos para virar) |",
         "| --- | --- | --- | --- | --- | --- |"]
    mensal["sem"] = mensal["mes"].dt.year.astype(str) + "-" + np.where(mensal["mes"].dt.month <= 6, "1", "2")
    for s_, g in mensal.groupby("sem"):
        L.append(f"| {s_} | {n(g['votacoes'].sum())} | {pct(g['polarizadas'].sum(), g['votacoes'].sum())} | "
                 f"{pct(g['apertadas'].sum(), g['votacoes'].sum())} | {pct(g['gov_venceu'].sum(), g['gov_orientou'].sum())} | "
                 f"{n(pv[(pv['mes'].isin(g['mes'])) & (pv['governo_venceu'] == 1)]['votos_para_virar'].median())} |")
    L.append("")
    rel = ROOT / c["governabilidade"]["relatorio"].replace("governabilidade", "dinamica")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


def main() -> int:
    from src.config import legislatura_tem_dados, por_legislatura

    cfg = load_config()
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            continue
        print(f"===== legislatura {leg} =====")
        rodar(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
