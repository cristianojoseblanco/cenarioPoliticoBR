#!/usr/bin/env bash
# Coleta do Bloco C para inspeção fora do Actions. Uso: bash scripts/coletar_c.sh "agendas wiki" | "discursos"
set -uo pipefail
PARTES="${1:-agendas wiki}"
python -m src.storage baixar processed_camara processed_senado > /dev/null 2>&1 || true
rodar() {
  if ! timeout 2400 python -m "$@" > /tmp/out.txt 2> /tmp/err.txt; then
    echo "::error title=$1::$(tail -c 600 /tmp/err.txt | tr '\n' ' ')"
  fi
  grep "::" /tmp/out.txt || true
  echo "::notice title=$1::$(tail -c 900 /tmp/out.txt | tr '\n' ' ')"
}
case "$PARTES" in *agendas*) rodar src.ingestion.agendas ;; esac
ATT=$(echo "$PARTES" | tr ' ' '\n' | grep -E '^(wiki|discursos)$' | tr '\n' ' ')
[ -n "$ATT" ] && rodar src.ingestion.atencao $ATT
mkdir -p coleta data/staging/agendas data/staging/atencao && cp -r data/staging/agendas data/staging/atencao coleta/
du -sh coleta/*
