"""Testa o SIDRA com cabeçalhos diferentes (diagnóstico de 403). Saída em amostras_sidra/resultado.txt."""
from pathlib import Path

import requests

u = "https://apisidra.ibge.gov.br/values/t/4714/n6/in%20n3%2011/v/all/p/2022"
saida = Path("amostras_sidra")
saida.mkdir(exist_ok=True)
linhas = []
for nome, h in [("navegador", {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}), ("curl", {"User-Agent": "curl/8.5.0", "Accept": "*/*"}),
                ("projeto", {"User-Agent": "cenarioPoliticoBR/0.1 (pesquisa)"}), ("padrao", {})]:
    try:
        r = requests.get(u, headers=h, timeout=60)
        linhas.append(f"{nome}\t{r.status_code}\t{len(r.content)}")
    except Exception as e:  # noqa: BLE001
        linhas.append(f"{nome}\terro\t{e}")
(saida / "resultado.txt").write_text("\n".join(linhas))
print("\n".join(linhas))
