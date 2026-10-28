# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 92,9% | 0,972 | 0,205 |
| M2 · + perfil do deputado e tema | 94,4% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 20.061 (2,5%); 81,5% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7688
- plenario_sim: 0,0533
- dep_disciplina: 0,0511
- dep_apoio_gov: 0,0353
- or_partido: 0,0209
- or_governo: 0,0157
- colegas_n: 0,0059
- dep_sim: 0,0045

## Mais imprevisíveis (100+ votos)

- Ricardo Izar (PP): 8,2% de 1.275 votos (mediana do partido: 1,8%)
- Rodrigo Maia (DEM): 8,1% de 491 votos (mediana do partido: 2,5%)
- Nelho Bezerra (UNIÃO): 7,9% de 216 votos (mediana do partido: 4,1%)
- Tabata Amaral (PDT): 7,4% de 1.754 votos (mediana do partido: 3,2%)
- Mauro Nazif (PSB): 7,3% de 1.774 votos (mediana do partido: 2,5%)
- Danrlei de Deus Hinterholz (PSD): 7,2% de 853 votos (mediana do partido: 3,0%)
- Angela Amin (PP): 7,1% de 1.799 votos (mediana do partido: 1,8%)
- Gastão Vieira (PROS): 7,0% de 1.143 votos (mediana do partido: 3,1%)
- Hélio Costa (REPUBLICANOS): 6,9% de 1.803 votos (mediana do partido: 1,2%)
- Rodrigo Agostinho (PSB): 6,7% de 1.845 votos (mediana do partido: 2,5%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,1% de 42.204 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Educação: 2,7% de 52.101 votos
- Administração Pública: 2,6% de 226.423 votos
- Saúde: 2,4% de 118.412 votos
- Viação, Transporte e Mobilidade: 2,4% de 59.886 votos
