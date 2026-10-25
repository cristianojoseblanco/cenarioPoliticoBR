# Rede de votação — Plenário

Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/camara`.

## Dados

- Votações nominais no Plenário: 1.128
  - sem voto com valor (secretas): 2
  - minoria abaixo de 2,5%: 87
  - incluídas: 1.039 de 1.128 (92,1%)
- Deputados na matriz: 644; no grafo: 618 de 644 (96,0%)
- Arestas (kNN = 15): 7.554

## Comunidades (variante principal)

- Modularidade: 0,601
- Estabilidade entre 20 sementes (ARI médio): 0,883
- Correspondência com partido: ARI 0,385, NMI 0,502

| Comunidade | Deputados | Partidos principais | Concordância interna média |
| --- | --- | --- | --- |
| C1 | 165 | PL 100, UNIÃO 21, PP 15, MDB 6, NOVO 4, REPUBLICANOS 4 | 80,3% |
| C2 | 142 | UNIÃO 46, PP 42, PODE 14, PSDB 9, REPUBLICANOS 6, PL 5 | 85,2% |
| C3 | 121 | PSD 49, MDB 36, PDT 18, UNIÃO 3, PRD 3, REPUBLICANOS 2 | 82,1% |
| C4 | 114 | PT 75, PSB 14, PCdoB 9, PV 4, UNIÃO 2, AVANTE 2 | 93,9% |
| C5 | 58 | REPUBLICANOS 45, MDB 4, PODE 4, PP 2, PSD 1, AVANTE 1 | 87,7% |
| C6 | 18 | PSOL 14, REDE 3, PDT 1 | 95,9% |

## Partidos divididos entre comunidades

| Partido | Deputados no grafo | Na comunidade principal do partido | Distribuição |
| --- | --- | --- | --- |
| AVANTE | 7 | 3 de 7 (42,9%) | C2 3, C4 2, C1 1, C5 1 |
| CIDADANIA | 5 | 2 de 5 (40,0%) | C3 2, C1 2, C2 1 |
| MDB | 52 | 36 de 52 (69,2%) | C3 36, C1 6, C2 5, C5 4, C4 1 |
| PDT | 20 | 18 de 20 (90,0%) | C3 18, C6 1, C4 1 |
| PL | 108 | 100 de 108 (92,6%) | C1 100, C2 5, C3 2, C5 1 |
| PODE | 23 | 14 de 23 (60,9%) | C2 14, C5 4, C1 3, C4 1, C3 1 |
| PP | 61 | 42 de 61 (68,9%) | C2 42, C1 15, C5 2, C3 1, C4 1 |
| PRD | 7 | 3 de 7 (42,9%) | C3 3, C1 2, C2 2 |
| PSB | 17 | 14 de 17 (82,4%) | C4 14, C3 2, C2 1 |
| PSD | 57 | 49 de 57 (86,0%) | C3 49, C2 4, C1 3, C5 1 |
| PSDB | 13 | 9 de 13 (69,2%) | C2 9, C1 3, C4 1 |
| PSOL | 15 | 14 de 15 (93,3%) | C6 14, C4 1 |
| PV | 5 | 4 de 5 (80,0%) | C4 4, C2 1 |
| REPUBLICANOS | 57 | 45 de 57 (78,9%) | C5 45, C2 6, C1 4, C3 2 |
| SOLIDARIEDADE | 6 | 3 de 6 (50,0%) | C2 3, C3 2, C4 1 |
| UNIÃO | 72 | 46 de 72 (63,9%) | C2 46, C1 21, C3 3, C4 2 |

## Pontes entre comunidades (maior coeficiente de participação)

Deputados cujas 15 ligações mais fortes se espalham por mais de uma comunidade.

| Deputado | Partido | UF | Comunidade | Participação |
| --- | --- | --- | --- | --- |
| Carlos Sampaio | PSD | SP | C3 | 0,75 |
| Amom Mandel | CIDADANIA | AM | C3 | 0,75 |
| Alceu Moreira | MDB | RS | C5 | 0,75 |
| Rafael Fera | PODE | RO | C5 | 0,75 |
| Gilson Daniel | PODE | ES | C5 | 0,74 |
| Leandre | PSD | PR | C3 | 0,74 |
| Otoni de Paula | MDB | RJ | C5 | 0,73 |
| Marussa Boldrin | MDB | GO | C5 | 0,72 |
| Marreca Filho | PRD | MA | C3 | 0,72 |
| Mariana Carvalho | REPUBLICANOS | MA | C1 | 0,72 |
| Dr. Gonçalo | PODE | MA | C5 | 0,71 |
| Icaro de Valmir | PL | SE | C2 | 0,71 |
| Meire Serafim | UNIÃO | AC | C3 | 0,70 |
| Delegado da Cunha | PP | SP | C2 | 0,70 |
| Guilherme Uchoa | PSB | PE | C3 | 0,70 |

## Sensibilidade

ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.

| Variante | Votações | Deputados | Comunidades | Modularidade | ARI vs principal |
| --- | --- | --- | --- | --- | --- |
| codificacao=B | 1.030 | 617 | 7 | 0,602 | 0,908 |
| codificacao=C | 1.039 | 619 | 7 | 0,601 | 0,864 |
| minoria=0.0 | 1.126 | 623 | 6 | 0,593 | 0,819 |
| minoria=0.1 | 894 | 602 | 7 | 0,625 | 0,883 |
| knn=10 | 1.039 | 618 | 7 | 0,614 | 0,888 |
| knn=25 | 1.039 | 617 | 4 | 0,581 | 0,718 |
