#!/usr/bin/env bash
# Coleta do Bloco A (cota, bens do TSE, IPCA) para inspeção fora do Actions.
set -uo pipefail
python -m src.storage baixar staging_tse staging_ibge > /dev/null 2>&1 || true
for mod in src.ingestion.cota src.ingestion.tse src.ingestion.ibge; do
  if ! python -m "$mod" > "/tmp/$mod.out" 2> "/tmp/$mod.err"; then
    echo "::error title=$mod::$( (grep -m3 -i 'tentativa\|Error' "/tmp/$mod.err"; tail -c 300 "/tmp/$mod.err") | tr '\n' ' ' | tr -s ' ' | cut -c1-950)"
  fi
  tail -12 "/tmp/$mod.out"
done
mkdir -p coleta/tse
cp -r data/staging/cota coleta/ ; cp data/staging/ibge/ipca.parquet coleta/ 2>/dev/null || true
for a in 2018 2022 2026; do mkdir -p coleta/tse/$a; cp data/staging/tse/$a/bens.parquet coleta/tse/$a/ 2>/dev/null || true; done
du -sh coleta/*
