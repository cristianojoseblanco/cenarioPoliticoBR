# Rede de votação — Plenário

Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/senado`.

## Dados

- Votações nominais no Plenário: 189
  - sem voto com valor (secretas): 0
  - minoria abaixo de 2,5%: 73
  - incluídas: 116 de 189 (61,4%)
- Senadores na matriz: 104; no grafo: 80 de 104 (76,9%)
- Arestas (kNN = 8): 472

## Comunidades (variante principal)

- Modularidade: 0,542
- Estabilidade entre 20 sementes (ARI médio): 0,835
- Correspondência com partido: ARI 0,228, NMI 0,419

| Comunidade | Senadores | Partidos principais | Concordância interna média |
| --- | --- | --- | --- |
| C1 | 23 | MDB 8, PSD 7, PSB 3, UNIÃO 3, PDT 1, PODE 1 | 83,7% |
| C2 | 22 | PL 12, REPUBLICANOS 3, PP 2, UNIÃO 2, PODE 2, NOVO 1 | 82,1% |
| C3 | 19 | PT 9, PSD 4, MDB 3, PDT 2, PSB 1 | 88,6% |
| C4 | 16 | PODE 4, PP 4, PSD 3, UNIÃO 2, PL 1, PSDB 1 | 77,1% |

## Partidos divididos entre comunidades

| Partido | Senadores no grafo | Na comunidade principal do partido | Distribuição |
| --- | --- | --- | --- |
| MDB | 11 | 8 de 11 (72,7%) | C1 8, C3 3 |
| PL | 13 | 12 de 13 (92,3%) | C2 12, C4 1 |
| PODE | 7 | 4 de 7 (57,1%) | C4 4, C2 2, C1 1 |
| PP | 6 | 4 de 6 (66,7%) | C4 4, C2 2 |
| PSD | 14 | 7 de 14 (50,0%) | C1 7, C3 4, C4 3 |
| UNIÃO | 7 | 3 de 7 (42,9%) | C1 3, C2 2, C4 2 |

## Pontes entre comunidades (maior coeficiente de participação)

Senadores cujas 15 ligações mais fortes se espalham por mais de uma comunidade.

| Senador | Partido | UF | Comunidade | Participação |
| --- | --- | --- | --- | --- |
| Styvenson Valentim | PODE | RN | C4 | 0,65 |
| Margareth Buzetti | PSD | MT | C4 | 0,60 |
| Lucas Barreto | PSD | AP | C4 | 0,56 |
| Romário | PL | RJ | C2 | 0,53 |
| Tereza Cristina | PP | MS | C4 | 0,50 |
| Jussara Lima | PSD | PI | C3 | 0,50 |
| Marcelo Castro | MDB | PI | C1 | 0,50 |
| Jader Barbalho | MDB | PA | C1 | 0,49 |
| Eduardo Gomes | PL | TO | C4 | 0,48 |
| Vanderlan Cardoso | PSD | GO | C4 | 0,48 |
| Renan Calheiros | MDB | AL | C3 | 0,48 |
| Otto Alencar | PSD | BA | C1 | 0,48 |
| Ana Paula Lobato | PDT | MA | C3 | 0,47 |
| Fernando Farias | MDB | AL | C3 | 0,47 |
| Rodrigo Cunha | PODE | AL | C4 | 0,47 |

## Sensibilidade

ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.

| Variante | Votações | Senadores | Comunidades | Modularidade | ARI vs principal |
| --- | --- | --- | --- | --- | --- |
| codificacao=B | 116 | 80 | 4 | 0,542 | 1,000 |
| codificacao=C | 116 | 80 | 4 | 0,532 | 1,000 |
| minoria=0.0 | 189 | 82 | 3 | 0,536 | 0,493 |
| minoria=0.1 | 94 | 80 | 3 | 0,543 | 0,653 |
| knn=10 | 116 | 80 | 4 | 0,528 | 0,840 |
| knn=25 | 116 | 80 | 3 | 0,430 | 0,485 |
