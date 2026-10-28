#!/usr/bin/env bash
# Coleta das fontes da Etapa 7d (emendas, IBGE, TSE com presidente) para inspeção fora do Actions.
# Cada etapa que falhar deixa a mensagem de erro como anotação (legível pela API do GitHub).
set -uo pipefail
MODS="${*:-src.ingestion.emendas src.ingestion.ibge src.ingestion.tse}"
for mod in $MODS; do
  if ! python -m "$mod" > "/tmp/$mod.out" 2> "/tmp/$mod.err"; then
    echo "::error title=$mod::$( (grep -m3 -i 'tentativa\|Error:' "/tmp/$mod.err"; tail -c 300 "/tmp/$mod.err") | tr '\n' ' ' | tr -s ' ' | cut -c1-950)"
  fi
  tail -5 "/tmp/$mod.out"
done
mkdir -p coleta
cp -r data/staging/emendas data/staging/ibge data/staging/tse data/marts/geo coleta/ 2>/dev/null || true
du -sh coleta/* || true
