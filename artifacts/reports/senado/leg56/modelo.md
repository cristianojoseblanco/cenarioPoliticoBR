# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,2% | 0,936 | 0,262 |
| M2 · + perfil do deputado e tema | 92,2% | 0,964 | 0,191 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 752 (2,9%); 20,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1811
- plenario_sim: 0,1531
- or_partido: 0,1163
- dep_disciplina: 0,0232
- or_governo: 0,0224
- dep_apoio_gov: 0,0204
- dep_sim: 0,0158
- comunidade: 0,0085

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 4,2%)
- Veneziano Vital do Rêgo (MDB): 5,9% de 306 votos (mediana do partido: 3,0%)
- Eliane Nogueira (PP): 5,5% de 128 votos (mediana do partido: 4,2%)
- Luis Carlos Heinze (PP): 5,4% de 353 votos (mediana do partido: 4,2%)
- Elmano Férrer (PP): 5,1% de 312 votos (mediana do partido: 4,2%)
- Esperidião Amin (PP): 5,1% de 354 votos (mediana do partido: 4,2%)
- Oriovisto Guimarães (PODE): 5,0% de 318 votos (mediana do partido: 2,9%)
- José Serra (PSDB): 5,0% de 280 votos (mediana do partido: 4,2%)
- Marcio Bittar (MDB): 4,9% de 287 votos (mediana do partido: 3,0%)
- Zenaide Maia (PROS): 4,7% de 344 votos (mediana do partido: 3,7%)

## Temas com mais votos imprevisíveis

