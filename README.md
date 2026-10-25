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

## Armazenamento

| Onde | O quê | Histórico |
| --- | --- | --- |
| Git | código, config, `data/metadata`, `data/marts` (resultados pequenos), relatórios | sim |
| Release `dados` | `staging_camara.tar`, `processed_camara.tar` (camadas grandes) | não: substituído a cada execução |

Para ter as camadas grandes localmente (ou no Colab): `python -m src.storage baixar`.
O workflow baixa os pacotes no início, roda tudo e publica de novo no fim.

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

## Camada processada (`data/processed/camara`)

| Tabela | Grão | Observação |
| --- | --- | --- |
| `deputados` | deputado | sem CPF |
| `votacoes` | votação | `nominal` indica se há voto por deputado |
| `votos` | votação × deputado | voto em texto original; ausência = falta de linha |
| `orientacoes` | votação × bancada | orientação do partido/bloco/governo |
| `votacao_proposicao` | votação × proposição | uma votação pode tocar várias proposições |
| `proposicoes` | proposição | ementa, tipo, situação, `principal_id` |
| `proposicao_tema` | proposição × tema | `origem` = `proprio` ou `herdado_principal` |
| `proposicao_autor` | proposição × autor | `proponente` separa autor de coautor |
| `partido_observado` | deputado × período | partido visto nas votações; fusões aparecem como troca |
| `exercicio` | deputado × período | períodos oficiais em exercício (API, histórico de mandato) |

Relatório: `artifacts/reports/processed_camara.md`.

## Análises (`data/marts/camara`)

| Etapa | Módulo | Saída | Relatório |
| --- | --- | --- | --- |
| 3 — rede de votação | `src/networks/votacao.py` | `redes/` (pares, arestas, comunidades, métricas, grafo) | `artifacts/reports/rede_votacao.md` |
| 4 — tema e tempo | `src/networks/fatias.py` | `fatias/` (posições no eixo entre polos, deslocamentos) | `artifacts/reports/fatias.md` |
| 5 — governabilidade | `src/governance/indicadores.py` | `governabilidade/` (apoio ao governo, disciplina, coesão, participação, vitórias) | `artifacts/reports/governabilidade.md` |

Notas de método e resultados: repositório `cenarioPoliticoBR-notas` (vault do Obsidian).

## Painel (Etapa 6)

`app/Home.py` + `app/pages/`: Streamlit lendo só os arquivos de `data/marts` (nada pesado roda no painel).
Páginas: Rede, Tempo, Temas, Partidos e Deputado. Dependências leves em `app/requirements.txt`.

- Local: `streamlit run app/Home.py`
- Nuvem: Streamlit Community Cloud apontando para `app/Home.py` neste repositório; o painel se atualiza
  sozinho quando o workflow semanal commita dados novos.

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests
python -m src.storage baixar          # camadas grandes do Release (opcional)
python -m src.ingestion.camara        # ou: ANOS=2023 python -m src.ingestion.camara
python -m src.processing.validation
python -m src.ingestion.camara_api    # histórico de mandatos (API)
python -m src.processing.entities
python -m src.networks.votacao
python -m src.networks.fatias
python -m src.governance.indicadores
```

## Estrutura

```
config/sources.yaml        parâmetros de fontes, caminhos e DuckDB
src/ingestion/camara.py    download + CSV → Parquet + metadados
src/ingestion/camara_api.py   histórico de mandatos pela API
src/processing/validation.py  relatório de qualidade do staging
src/processing/entities.py    camada processada (tabelas limpas e ligadas por ID)
data/staging/camara/<dataset>/ano=<ano>/part-0.parquet
data/processed/camara/<tabela>/          votos e votacoes particionados por ano
data/metadata/camara/<arquivo>.json
.github/workflows/ingestao_camara.yml
```

Fonte: [Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/).
