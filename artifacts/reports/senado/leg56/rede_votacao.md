# Rede de votação — Plenário

Parâmetros em `config/sources.yaml` → `redes`. Data dos dados: ver `data/metadata/senado`.

## Dados

- Votações nominais no Plenário: 367
  - sem voto com valor (secretas): 0
  - minoria abaixo de 2,5%: 167
  - incluídas: 200 de 367 (54,5%)
- Deputados na matriz: 108; no grafo: 85 de 108 (78,7%)
- Arestas (kNN = 8): 512

## Comunidades (variante principal)

- Modularidade: 0,467
- Estabilidade entre 20 sementes (ARI médio): 0,784
- Correspondência com partido: ARI 0,161, NMI 0,399

| Comunidade | Deputados | Partidos principais | Concordância interna média |
| --- | --- | --- | --- |
| C1 | 29 | MDB 10, PSD 10, DEM 3, PP 2, PL 1, PROS 1 | 82,0% |
| C2 | 25 | PP 6, MDB 4, DEM 3, PODE 3, PL 2, PSD 2 | 81,0% |
| C3 | 16 | PT 6, MDB 3, REDE 2, PDT 2, CIDADANIA 1, PROS 1 | 83,0% |
| C4 | 15 | PSDB 6, PODE 6, CIDADANIA 2, PSL 1 | 69,5% |

## Partidos divididos entre comunidades

| Partido | Deputados no grafo | Na comunidade principal do partido | Distribuição |
| --- | --- | --- | --- |
| DEM | 6 | 3 de 6 (50,0%) | C2 3, C1 3 |
| MDB | 17 | 10 de 17 (58,8%) | C1 10, C2 4, C3 3 |
| PODE | 9 | 6 de 9 (66,7%) | C4 6, C2 3 |
| PP | 8 | 6 de 8 (75,0%) | C2 6, C1 2 |
| PSD | 12 | 10 de 12 (83,3%) | C1 10, C2 2 |
| PSDB | 7 | 6 de 7 (85,7%) | C4 6, C2 1 |

## Pontes entre comunidades (maior coeficiente de participação)

Deputados cujas 15 ligações mais fortes se espalham por mais de uma comunidade.

| Deputado | Partido | UF | Comunidade | Participação |
| --- | --- | --- | --- | --- |
| Alessandro Vieira | CIDADANIA | SE | C4 | 0,64 |
| Izalci Lucas | PSDB | DF | C4 | 0,64 |
| Tasso Jereissati | PSDB | CE | C4 | 0,63 |
| José Serra | PSDB | SP | C4 | 0,63 |
| Arolde de Oliveira | PSD | RJ | C2 | 0,59 |
| Romário | PODE | RJ | C2 | 0,58 |
| Simone Tebet | MDB | MS | C1 | 0,57 |
| Plínio Valério | PSDB | AM | C4 | 0,56 |
| José Maranhão | MDB | PB | C1 | 0,55 |
| Maria do Carmo Alves | DEM | SE | C2 | 0,54 |
| Antonio Anastasia | PSD | MG | C1 | 0,54 |
| Rodrigo Pacheco | DEM | MG | C1 | 0,53 |
| Telmário Mota | PROS | RR | C2 | 0,50 |
| Reguffe | PODE | DF | C4 | 0,50 |
| Jarbas Vasconcelos | MDB | PE | C1 | 0,50 |

## Sensibilidade

ARI = 1 significa partição idêntica à principal; perto de 0, sem relação.

| Variante | Votações | Deputados | Comunidades | Modularidade | ARI vs principal |
| --- | --- | --- | --- | --- | --- |
| codificacao=B | 199 | 85 | 4 | 0,472 | 0,922 |
| codificacao=C | 200 | 85 | 4 | 0,475 | 0,901 |
| minoria=0.0 | 367 | 88 | 5 | 0,460 | 0,654 |
| minoria=0.1 | 159 | 85 | 4 | 0,483 | 0,978 |
| knn=10 | 200 | 85 | 4 | 0,445 | 0,931 |
| knn=25 | 200 | 85 | 3 | 0,299 | 0,550 |
