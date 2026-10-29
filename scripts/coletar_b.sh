#!/usr/bin/env bash
# Coleta do Bloco B (comissões e tramitação) para inspeção fora do Actions.
set -uo pipefail
python -m src.storage baixar processed_camara > /dev/null 2>&1 || true
mod=src.ingestion.comissoes
if ! python -m "$mod" > "/tmp/$mod.out" 2> "/tmp/$mod.err"; then
  echo "::error title=$mod::$(tail -c 600 "/tmp/$mod.err" | tr '\n' ' ')"
fi
grep "::" "/tmp/$mod.out" || true
tail -8 "/tmp/$mod.out"
mkdir -p coleta && cp -r data/staging/comissoes coleta/
du -sh coleta/*
