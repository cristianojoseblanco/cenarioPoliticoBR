# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 93,0% | 0,972 | 0,205 |
| M2 · + perfil do deputado e tema | 94,4% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 20.023 (2,5%); 81,4% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7950
- plenario_sim: 0,0508
- dep_disciplina: 0,0490
- dep_apoio_gov: 0,0354
- or_partido: 0,0195
- or_governo: 0,0151
- colegas_n: 0,0064
- dep_sim: 0,0047

## Mais imprevisíveis (100+ votos)

- Rodrigo Maia (DEM): 8,4% de 491 votos (mediana do partido: 2,5%)
- Ricardo Izar (PP): 8,3% de 1.275 votos (mediana do partido: 1,9%)
- Danrlei de Deus Hinterholz (PSD): 7,6% de 853 votos (mediana do partido: 2,9%)
- Patrick Dorneles (PSD): 7,5% de 106 votos (mediana do partido: 2,9%)
- Gastão Vieira (PROS): 7,4% de 1.143 votos (mediana do partido: 3,4%)
- Nelho Bezerra (UNIÃO): 7,4% de 216 votos (mediana do partido: 3,8%)
- Tabata Amaral (PDT): 7,1% de 1.754 votos (mediana do partido: 3,3%)
- Angela Amin (PP): 7,1% de 1.799 votos (mediana do partido: 1,9%)
- Hélio Costa (REPUBLICANOS): 6,9% de 1.803 votos (mediana do partido: 1,2%)
- Daniel Coelho (CIDADANIA): 6,8% de 1.583 votos (mediana do partido: 4,2%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,1% de 42.204 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Educação: 2,7% de 52.101 votos
- Administração Pública: 2,6% de 226.423 votos
- Saúde: 2,5% de 118.412 votos
- Viação, Transporte e Mobilidade: 2,4% de 59.886 votos
