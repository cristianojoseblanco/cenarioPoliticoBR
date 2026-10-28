"""Roda no Senado as mesmas análises da Câmara, com `para_senado(cfg)`.

Saídas em data/marts/senado/leg<N>/ e relatórios em artifacts/reports/senado/leg<N>/.
Uso: python -m src.senado
"""
from __future__ import annotations

import sys
import traceback

from src.config import legislatura_tem_dados, load_config, para_senado, por_legislatura
from src.governance import dinamica, indicadores
from src.models import voto_individual
from src.networks import dimensoes, fatias, mudancas, votacao

ETAPAS = [("rede", votacao.rodar), ("fatias", fatias.rodar), ("governabilidade", indicadores.rodar),
          ("dimensoes", dimensoes.rodar), ("dinamica", dinamica.rodar), ("mudancas", mudancas.rodar),
          ("modelo", voto_individual.rodar)]


TROCAS = [("Deputadas", "Senadoras"), ("deputadas", "senadoras"), ("Deputados", "Senadores"), ("deputados", "senadores"),
          ("Deputada", "Senadora"), ("deputada", "senadora"), ("Deputado", "Senador"), ("deputado", "senador"),
          ("da Câmara", "do Senado")]


def ajustar_relatorios(cfg: dict) -> int:
    """Os módulos são da Câmara e escrevem "deputados"; nos relatórios do Senado, troca por "senadores"."""
    import re
    from src.config import ROOT
    n_ = 0
    for p in (ROOT / "artifacts" / "reports" / "senado").rglob("*.md"):
        t = p.read_text(encoding="utf-8")
        u = t
        for a, b in TROCAS:
            u = re.sub(rf"\b{a}\b", b, u)
        u = u.replace("data/metadata/camara", "data/metadata/senado")
        if u != t:
            p.write_text(u, encoding="utf-8")
            n_ += 1
    return n_


def main() -> int:
    cfg = para_senado(load_config())
    falhas = []
    for leg, c in por_legislatura(cfg):
        if not legislatura_tem_dados(c):
            print(f"Senado, legislatura {leg}: sem dados suficientes")
            continue
        for nome, fn in ETAPAS:
            print(f"===== Senado · legislatura {leg} · {nome} =====")
            try:
                fn(c)
            except Exception:
                traceback.print_exc()
                falhas.append(f"{leg}/{nome}")
    print(f"relatórios ajustados: {ajustar_relatorios(cfg)}")
    if falhas:
        print("Falhas:", ", ".join(falhas))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
