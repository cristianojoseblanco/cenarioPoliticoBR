"""Baixa zips (ou outros arquivos) e grava um resumo: tamanho, membros e primeiras linhas.

Uso (no GitHub Actions): python scripts/explorar_zip.py URL [URL ...]
Saída em amostras_zip/: indice.tsv e, para cada zip, membros.tsv e cabeçalhos dos arquivos de texto.
Filtra os membros mostrados por FILTRO (variável de ambiente, padrão "BRASIL|_BR|SP").
"""
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import requests

saida = Path("amostras_zip")
saida.mkdir(exist_ok=True)
args = [a for a in sys.argv[1:] if not a.startswith("--filtro=")]
filtro = re.compile(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--filtro=")),
                         os.environ.get("FILTRO", "BRASIL|_BR|SP")), re.I)
idx = []
for i, url in enumerate(args, 1):
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            with requests.get(url, stream=True, timeout=600) as r:
                status = r.status_code
                for ch in r.iter_content(1 << 20):
                    tmp.write(ch)
        tam = os.path.getsize(tmp.name)
        idx.append(f"{i}\t{status}\t{tam}\t{url}")
        if status != 200 or not zipfile.is_zipfile(tmp.name):
            continue
        z = zipfile.ZipFile(tmp.name)
        d = saida / str(i)
        d.mkdir(exist_ok=True)
        membros = z.infolist()
        (d / "membros.tsv").write_text("\n".join(f"{m.filename}\t{m.file_size}" for m in membros), encoding="utf-8")
        mostrados = [m for m in membros if filtro.search(m.filename)][:4] or membros[:2]
        for m in mostrados:
            with z.open(m) as f:
                linhas = [f.readline().decode("latin-1", "replace") for _ in range(6)]
            (d / (Path(m.filename).name + ".head.txt")).write_text("".join(linhas), encoding="utf-8")
        os.unlink(tmp.name)
    except Exception as e:  # noqa: BLE001
        idx.append(f"{i}\terro\t0\t{url}\t{e}")
(saida / "indice.tsv").write_text("\n".join(idx), encoding="utf-8")
print("\n".join(idx))
