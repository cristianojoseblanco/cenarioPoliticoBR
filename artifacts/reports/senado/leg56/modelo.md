# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,6% | 0,934 | 0,265 |
| M2 · + perfil do senador e tema | 92,2% | 0,963 | 0,191 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 723 (2,8%); 20,7% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1683
- plenario_sim: 0,1670
- or_partido: 0,1156
- dep_apoio_gov: 0,0235
- or_governo: 0,0222
- dep_disciplina: 0,0213
- dep_sim: 0,0148
- comunidade: 0,0117

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 4,0%)
- Luis Carlos Heinze (PP): 5,4% de 353 votos (mediana do partido: 2,9%)
- Eduardo Girão (PODE): 4,7% de 358 votos (mediana do partido: 3,3%)
- Oriovisto Guimarães (PODE): 4,7% de 318 votos (mediana do partido: 3,3%)
- Zenaide Maia (PROS): 4,7% de 344 votos (mediana do partido: 3,6%)
- Veneziano Vital do Rêgo (MDB): 4,6% de 306 votos (mediana do partido: 2,7%)
- Esperidião Amin (PP): 4,5% de 354 votos (mediana do partido: 2,9%)
- Renan Calheiros (MDB): 4,5% de 179 votos (mediana do partido: 2,7%)
- Plínio Valério (PSDB): 4,5% de 336 votos (mediana do partido: 4,0%)
- Rodrigo Cunha (PSDB): 4,3% de 303 votos (mediana do partido: 4,0%)

## Temas com mais votos imprevisíveis

