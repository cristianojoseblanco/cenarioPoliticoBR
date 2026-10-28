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
    if falhas:
        print("Falhas:", ", ".join(falhas))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
