# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,9% | 0,936 | 0,261 |
| M2 · + perfil do deputado e tema | 92,1% | 0,963 | 0,192 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 728 (2,8%); 22,3% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1779
- plenario_sim: 0,1571
- or_partido: 0,1123
- or_governo: 0,0268
- dep_apoio_gov: 0,0228
- dep_disciplina: 0,0213
- dep_sim: 0,0156
- comunidade: 0,0092

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 3,7%)
- Esperidião Amin (PP): 5,6% de 354 votos (mediana do partido: 3,8%)
- Veneziano Vital do Rêgo (MDB): 5,2% de 306 votos (mediana do partido: 2,9%)
- Reguffe (PODE): 5,0% de 362 votos (mediana do partido: 3,1%)
- Elmano Férrer (PP): 4,8% de 312 votos (mediana do partido: 3,8%)
- Dário Berger (MDB): 4,7% de 338 votos (mediana do partido: 2,9%)
- Oriovisto Guimarães (PODE): 4,7% de 318 votos (mediana do partido: 3,1%)
- Eliane Nogueira (PP): 4,7% de 128 votos (mediana do partido: 3,8%)
- Romário (PL): 4,7% de 322 votos (mediana do partido: 4,0%)
- Luis Carlos Heinze (PP): 4,5% de 353 votos (mediana do partido: 3,8%)

## Temas com mais votos imprevisíveis

