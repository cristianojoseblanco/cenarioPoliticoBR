# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 93,0% | 0,972 | 0,204 |
| M2 · + perfil do deputado e tema | 94,4% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 19.961 (2,5%); 81,5% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7633
- plenario_sim: 0,0574
- dep_disciplina: 0,0496
- dep_apoio_gov: 0,0383
- or_partido: 0,0207
- or_governo: 0,0153
- colegas_n: 0,0066
- dep_sim: 0,0051

## Mais imprevisíveis (100+ votos)

- Ricardo Izar (PP): 8,5% de 1.275 votos (mediana do partido: 2,0%)
- Nelho Bezerra (UNIÃO): 8,3% de 216 votos (mediana do partido: 4,1%)
- Rodrigo Maia (DEM): 7,7% de 491 votos (mediana do partido: 2,4%)
- Patrick Dorneles (PSD): 7,5% de 106 votos (mediana do partido: 3,0%)
- Gastão Vieira (PROS): 7,3% de 1.143 votos (mediana do partido: 3,4%)
- Daniel Coelho (CIDADANIA): 6,9% de 1.583 votos (mediana do partido: 4,5%)
- Mauro Nazif (PSB): 6,9% de 1.774 votos (mediana do partido: 2,3%)
- Danrlei de Deus Hinterholz (PSD): 6,9% de 853 votos (mediana do partido: 3,0%)
- Angela Amin (PP): 6,9% de 1.799 votos (mediana do partido: 2,0%)
- Hélio Costa (REPUBLICANOS): 6,8% de 1.803 votos (mediana do partido: 1,2%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,1% de 42.204 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Educação: 2,7% de 52.101 votos
- Administração Pública: 2,6% de 226.423 votos
- Viação, Transporte e Mobilidade: 2,5% de 59.886 votos
- Saúde: 2,4% de 118.412 votos
