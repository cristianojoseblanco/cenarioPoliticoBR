# Rede de votação — Plenário

Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/camara`.

## Dados

- Votações nominais no Plenário: 1.971
  - sem voto com valor (secretas): 1
  - minoria abaixo de 2,5%: 247
  - incluídas: 1.723 de 1.971 (87,4%)
- Deputados na matriz: 597; no grafo: 592 de 597 (99,2%)
- Arestas (kNN = 15): 7.374

## Comunidades (variante principal)

- Modularidade: 0,527
- Estabilidade entre 20 sementes (ARI médio): 0,901
- Correspondência com partido: ARI 0,303, NMI 0,542

| Comunidade | Deputados | Partidos principais | Concordância interna média |
| --- | --- | --- | --- |
| C1 | 172 | PL 40, PP 40, PSD 34, PSC 9, SOLIDARIEDADE 9, PROS 8 | 88,7% |
| C2 | 119 | PT 58, PSB 30, PSOL 11, PCdoB 9, PDT 2, PV 2 | 85,6% |
| C3 | 113 | PSL 49, PSD 9, PP 8, CIDADANIA 6, PL 6, PODE 5 | 85,4% |
| C4 | 68 | PSDB 33, NOVO 8, PODE 7, PSL 5, MDB 3, CIDADANIA 3 | 76,3% |
| C5 | 41 | REPUBLICANOS 34, SOLIDARIEDADE 3, PTB 2, MDB 1, PSC 1 | 92,4% |
| C6 | 33 | MDB 32, REPUBLICANOS 1 | 89,8% |
| C7 | 24 | DEM 23, PTB 1 | 92,0% |
| C8 | 22 | PDT 21, CIDADANIA 1 | 88,4% |

## Partidos divididos entre comunidades

| Partido | Deputados no grafo | Na comunidade principal do partido | Distribuição |
| --- | --- | --- | --- |
| AVANTE | 8 | 5 de 8 (62,5%) | C1 5, C2 2, C3 1 |
| CIDADANIA | 10 | 6 de 10 (60,0%) | C3 6, C4 3, C8 1 |
| DEM | 31 | 23 de 31 (74,2%) | C7 23, C1 5, C3 2, C4 1 |
| MDB | 39 | 32 de 39 (82,1%) | C6 32, C4 3, C3 2, C1 1, C5 1 |
| PATRIOTA | 6 | 4 de 6 (66,7%) | C1 4, C3 2 |
| PDT | 28 | 21 de 28 (75,0%) | C8 21, C1 3, C2 2, C3 2 |
| PL | 48 | 40 de 48 (83,3%) | C1 40, C3 6, C2 1, C4 1 |
| PODE | 14 | 7 de 14 (50,0%) | C4 7, C3 5, C2 2 |
| PP | 48 | 40 de 48 (83,3%) | C1 40, C3 8 |
| PROS | 12 | 8 de 12 (66,7%) | C1 8, C3 3, C4 1 |
| PSB | 36 | 30 de 36 (83,3%) | C2 30, C3 5, C4 1 |
| PSC | 13 | 9 de 13 (69,2%) | C1 9, C3 2, C4 1, C5 1 |
| PSD | 45 | 34 de 45 (75,6%) | C1 34, C3 9, C4 2 |
| PSDB | 39 | 33 de 39 (84,6%) | C4 33, C3 3, C1 2, C2 1 |
| PSL | 55 | 49 de 55 (89,1%) | C3 49, C4 5, C1 1 |
| PTB | 12 | 7 de 12 (58,3%) | C1 7, C5 2, C4 2, C7 1 |
| REPUBLICANOS | 40 | 34 de 40 (85,0%) | C5 34, C3 3, C1 2, C6 1 |
| SOLIDARIEDADE | 14 | 9 de 14 (64,3%) | C1 9, C5 3, C3 2 |

## Pontes entre comunidades (maior coeficiente de participação)

Deputados cujas 15 ligações mais fortes se espalham por mais de uma comunidade.

| Deputado | Partido | UF | Comunidade | Participação |
| --- | --- | --- | --- | --- |
| Victor Mendes | MDB | MA | C4 | 0,80 |
| Ronaldo Martins | REPUBLICANOS | CE | C5 | 0,79 |
| Paes Landim | PTB | PI | C7 | 0,79 |
| Fábio Faria | PSD | RN | C4 | 0,78 |
| Lucio Mosquini | MDB | RO | C5 | 0,77 |
| Norma Pereira | PSDB | SC | C3 | 0,76 |
| Tiririca | PL | SP | C2 | 0,76 |
| Paulinho da Força | SOLIDARIEDADE | SP | C5 | 0,76 |
| Felipe Rigoni | PSB | ES | C4 | 0,76 |
| Fabio Reis | MDB | SE | C6 | 0,74 |
| Gilberto Nascimento | PSC | SP | C5 | 0,74 |
| Emanuel Pinheiro Neto | PTB | MT | C4 | 0,74 |
| Elcione Barbalho | MDB | PA | C6 | 0,74 |
| Maurício Dziedricki | PTB | RS | C4 | 0,74 |
| Luis Miranda | DEM | DF | C7 | 0,74 |

## Sensibilidade

ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.

| Variante | Votações | Deputados | Comunidades | Modularidade | ARI vs principal |
| --- | --- | --- | --- | --- | --- |
| codificacao=B | 1.724 | 592 | 8 | 0,529 | 0,982 |
| codificacao=C | 1.723 | 592 | 8 | 0,526 | 0,925 |
| minoria=0.0 | 1.970 | 593 | 8 | 0,522 | 0,874 |
| minoria=0.1 | 1.396 | 591 | 8 | 0,543 | 0,800 |
| knn=10 | 1.723 | 592 | 10 | 0,539 | 0,765 |
| knn=25 | 1.723 | 592 | 6 | 0,511 | 0,721 |
