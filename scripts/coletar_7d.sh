#!/usr/bin/env bash
# Coleta das fontes da Etapa 7d (emendas, IBGE, TSE com presidente) para inspeção fora do Actions.
set -euo pipefail
python -m src.ingestion.emendas
python -m src.ingestion.ibge
python -m src.ingestion.tse
mkdir -p coleta
cp -r data/staging/emendas data/staging/ibge data/staging/tse data/marts/geo coleta/ 2>/dev/null || true
du -sh coleta/*
