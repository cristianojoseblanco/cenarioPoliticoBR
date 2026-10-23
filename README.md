# Laboratório de Inteligência Política do Brasil

Análise quantitativa da estrutura política brasileira: comunidades de votação,
coesão, fragmentação e governabilidade. Começa pela Câmara dos Deputados.

## Como roda (nuvem, custo zero)

| Camada | Onde | O quê |
| --- | --- | --- |
| Ingestão | GitHub Actions | Baixa os arquivos em lote da Câmara, converte para Parquet e commita no repositório |
| Armazenamento | Este repositório | `data/staging` (Parquet fiel à fonte) e `data/metadata` (origem, hash, linhas) |
| Análise | Clone do repositório + DuckDB | Matriz de votação, grafos, comunidades, indicadores |
| Painel | Streamlit Community Cloud | `app/Home.py`, lendo os Parquet do repositório (Fase 4) |

## Ingestão

- Automática toda segunda-feira.
- Manual: aba **Actions → Ingestão Câmara → Run workflow**. O campo *anos* aceita
  `2019,2020` etc.; vazio usa `anos_padrao` de `config/sources.yaml`.
- Idempotente: arquivo com o mesmo SHA-256 não é reescrito, e não há commit sem dado novo.
- O relatório de qualidade sai em `artifacts/reports/qualidade_camara.md` e no resumo da execução.

## Regras do projeto

- Todo parâmetro fica em `config/sources.yaml`. Nada de constante no código.
- O staging guarda tudo como texto, exatamente como veio. Ausência, abstenção,
  obstrução e voto vazio são estados distintos, e a codificação deles é decidida
  na camada de processamento, com análise de sensibilidade.
- Identificadores oficiais são chave. Nome nunca é chave.

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests
python -m src.ingestion.camara        # ou: ANOS=2023 python -m src.ingestion.camara
python -m src.processing.validation
```

## Estrutura

```
config/sources.yaml        parâmetros de fontes, caminhos e DuckDB
src/ingestion/camara.py    download + CSV → Parquet + metadados
src/processing/validation.py  relatório de qualidade
data/staging/camara/<dataset>/ano=<ano>/part-0.parquet
data/metadata/camara/<arquivo>.json
.github/workflows/ingestao_camara.yml
```

Fonte: [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/).
