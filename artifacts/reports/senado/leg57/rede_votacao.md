# Rede de votação — Plenário

Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/senado`.

## Dados

- Votações nominais no Plenário: 177
  - sem voto com valor (secretas): 0
  - minoria abaixo de 2,5%: 68
  - incluídas: 109 de 177 (61,6%)
- Senadores na matriz: 102; no grafo: 80 de 102 (78,4%)
- Arestas (kNN = 8): 466

## Comunidades (variante principal)

- Modularidade: 0,550
- Estabilidade entre 20 sementes (ARI médio): 0,925
- Correspondência com partido: ARI 0,186, NMI 0,383

| Comunidade | Senadores | Partidos principais | Concordância interna média |
| --- | --- | --- | --- |
| C1 | 30 | PL 13, PP 5, REPUBLICANOS 4, UNIÃO 3, PODE 2, PSDB 1 | 79,8% |
| C2 | 28 | PSD 8, MDB 6, PODE 5, UNIÃO 4, PSB 3, PP 1 | 79,3% |
| C3 | 22 | PT 9, MDB 5, PSD 5, PDT 2, PSB 1 | 88,0% |

## Partidos divididos entre comunidades

| Partido | Senadores no grafo | Na comunidade principal do partido | Distribuição |
| --- | --- | --- | --- |
| MDB | 11 | 6 de 11 (54,5%) | C2 6, C3 5 |
| PODE | 7 | 5 de 7 (71,4%) | C2 5, C1 2 |
| PP | 6 | 5 de 6 (83,3%) | C1 5, C2 1 |
| PSD | 14 | 8 de 14 (57,1%) | C2 8, C3 5, C1 1 |
| UNIÃO | 7 | 4 de 7 (57,1%) | C2 4, C1 3 |

## Pontes entre comunidades (maior coeficiente de participação)

Senadores cujas 15 ligações mais fortes se espalham por mais de uma comunidade.

| Senador | Partido | UF | Comunidade | Participação |
| --- | --- | --- | --- | --- |
| Jader Barbalho | MDB | PA | C3 | 0,50 |
| Otto Alencar | PSD | BA | C3 | 0,50 |
| Veneziano Vital do Rêgo | MDB | PB | C2 | 0,49 |
| Eduardo Braga | MDB | AM | C2 | 0,49 |
| Marcelo Castro | MDB | PI | C3 | 0,48 |
| Margareth Buzetti | PSD | MT | C2 | 0,47 |
| Ana Paula Lobato | PDT | MA | C3 | 0,47 |
| Sérgio Petecão | PSD | AC | C2 | 0,43 |
| Jussara Lima | PSD | PI | C3 | 0,39 |
| Omar Aziz | PSD | AM | C2 | 0,39 |
| Alan Rick | UNIÃO | AC | C1 | 0,39 |
| Flávio Arns | PSB | PR | C2 | 0,38 |
| Angelo Coronel | PSD | BA | C2 | 0,38 |
| Rodrigo Cunha | PODE | AL | C2 | 0,37 |
| Irajá | PSD | TO | C2 | 0,37 |

## Sensibilidade

ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.

| Variante | Votações | Senadores | Comunidades | Modularidade | ARI vs principal |
| --- | --- | --- | --- | --- | --- |
| codificacao=B | 109 | 80 | 3 | 0,550 | 1,000 |
| codificacao=C | 109 | 80 | 3 | 0,543 | 0,965 |
| minoria=0.0 | 177 | 82 | 3 | 0,540 | 0,931 |
| minoria=0.1 | 88 | 80 | 3 | 0,552 | 0,861 |
| knn=10 | 109 | 80 | 3 | 0,541 | 1,000 |
| knn=25 | 109 | 80 | 3 | 0,438 | 0,761 |
