# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 93,0% | 0,972 | 0,204 |
| M2 · + perfil do deputado e tema | 94,4% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 20.132 (2,6%); 81,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7849
- plenario_sim: 0,0629
- dep_disciplina: 0,0505
- dep_apoio_gov: 0,0363
- or_partido: 0,0209
- or_governo: 0,0164
- colegas_n: 0,0075
- dep_sim: 0,0045

## Mais imprevisíveis (100+ votos)

- Patrick Dorneles (PSD): 8,5% de 106 votos (mediana do partido: 3,0%)
- Nelho Bezerra (UNIÃO): 8,3% de 216 votos (mediana do partido: 3,2%)
- Ricardo Izar (PP): 7,9% de 1.275 votos (mediana do partido: 2,0%)
- Rodrigo Maia (DEM): 7,7% de 491 votos (mediana do partido: 2,4%)
- Daniel Coelho (CIDADANIA): 7,6% de 1.583 votos (mediana do partido: 4,3%)
- Gastão Vieira (PROS): 7,5% de 1.143 votos (mediana do partido: 3,2%)
- Angela Amin (PP): 7,2% de 1.799 votos (mediana do partido: 2,0%)
- Mauro Nazif (PSB): 7,0% de 1.774 votos (mediana do partido: 2,2%)
- Danrlei de Deus Hinterholz (PSD): 7,0% de 853 votos (mediana do partido: 3,0%)
- Tabata Amaral (PDT): 7,0% de 1.754 votos (mediana do partido: 3,3%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,0% de 42.204 votos
- Educação: 2,8% de 52.101 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Administração Pública: 2,7% de 226.423 votos
- Viação, Transporte e Mobilidade: 2,5% de 59.886 votos
- Saúde: 2,5% de 118.412 votos
