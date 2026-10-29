#!/usr/bin/env bash
# Coleta do Bloco C (e-Agendas, Wikipédia, discursos) para inspeção fora do Actions.
set -uo pipefail
python -m src.storage baixar processed_camara processed_senado > /dev/null 2>&1 || true
for mod in src.ingestion.agendas src.ingestion.atencao; do
  if ! python -m "$mod" > "/tmp/$mod.out" 2> "/tmp/$mod.err"; then
    echo "::error title=$mod::$(tail -c 600 "/tmp/$mod.err" | tr '\n' ' ')"
  fi
  grep "::" "/tmp/$mod.out" || true
  echo "::notice title=$mod::$(tail -c 900 "/tmp/$mod.out" | tr '\n' ' ')"
done
mkdir -p coleta && cp -r data/staging/agendas data/staging/atencao coleta/
du -sh coleta/*
