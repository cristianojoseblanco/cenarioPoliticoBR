"""Pacotes de dados grandes no GitHub Release (fora do histórico do Git).

  python -m src.storage baixar      # baixa e extrai os pacotes (sem login; repositório público)
  python -m src.storage publicar    # empacota e substitui os pacotes no Release (precisa do gh + token)

Cada pacote é um .tar de uma pasta (os Parquet já são comprimidos com zstd).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import requests

from src.config import ROOT, load_config


def _cfg():
    return load_config()["armazenamento"]


def baixar(pacotes: list[str] | None = None) -> int:
    a = _cfg()
    alvo = pacotes or list(a["pacotes"])
    falhas = 0
    for nome in alvo:
        url = f"https://github.com/{a['repositorio']}/releases/download/{a['release_tag']}/{nome}.tar"
        destino = ROOT / a["pacotes"][nome]
        with tempfile.TemporaryDirectory() as tmp:
            arq = Path(tmp) / f"{nome}.tar"
            r = requests.get(url, stream=True, timeout=300)
            if r.status_code == 404:
                print(f"{nome}: ainda não existe no Release")
                falhas += 1
                continue
            r.raise_for_status()
            with open(arq, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
            if destino.exists():
                shutil.rmtree(destino)
            destino.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(arq) as t:
                t.extractall(destino.parent, filter="data")
            print(f"{nome}: {arq.stat().st_size / 1e6:.1f} MB -> {destino.relative_to(ROOT)}")
    return 1 if falhas == len(alvo) else 0


def _rodar(cmd: list[str]) -> None:
    """Executa e, se falhar, registra a mensagem como anotação de erro do GitHub Actions (legível pela API)."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().replace("\n", " | ")[:900]
        print(f"::error title=storage::{' '.join(cmd[:3])}: {msg}")
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)


def publicar() -> int:
    a = _cfg()
    tag = a["release_tag"]
    existe = subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0
    # A tag do Release fica sempre no commit atual: uma tag antiga prenderia versões velhas
    # do histórico (e os arquivos grandes de antes) no GitHub.
    _rodar(["git", "tag", "-f", tag])
    try:
        _rodar(["git", "push", "--force", "origin", f"refs/tags/{tag}"])
    except subprocess.CalledProcessError:
        # o token do Actions não pode mover a tag para um commit que altera workflows; os pacotes
        # independem da posição da tag, então segue (a tag anda na próxima execução sem essa mudança)
        print("::warning title=storage::tag do Release não foi movida; pacotes enviados mesmo assim")
    if not existe:
        subprocess.run(["gh", "release", "create", tag, "--title", "Dados (pacote corrente)",
                        "--notes", "Camadas staging e processed. Substituídas a cada execução do workflow; "
                                   "use `python -m src.storage baixar`.", "--latest=false"], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        arquivos = []
        for nome, pasta in a["pacotes"].items():
            origem = ROOT / pasta
            if not origem.exists():
                print(f"{nome}: pasta {pasta} não existe; pulando")
                continue
            arq = Path(tmp) / f"{nome}.tar"
            with tarfile.open(arq, "w") as t:
                t.add(origem, arcname=origem.name)
            print(f"{nome}: {arq.stat().st_size / 1e6:.1f} MB")
            arquivos.append(str(arq))
        if arquivos:
            _rodar(["gh", "release", "upload", tag, *arquivos, "--clobber"])
    return 0


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else ""
    if acao == "baixar":
        sys.exit(baixar(sys.argv[2:] or None))
    if acao == "publicar":
        sys.exit(publicar())
    print(__doc__)
    sys.exit(2)
