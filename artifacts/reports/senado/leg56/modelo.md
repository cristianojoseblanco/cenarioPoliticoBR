# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,5% | 0,937 | 0,259 |
| M2 · + perfil do senador e tema | 92,1% | 0,963 | 0,192 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 726 (2,8%); 21,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1849
- plenario_sim: 0,1464
- or_partido: 0,0873
- or_governo: 0,0217
- dep_disciplina: 0,0217
- dep_apoio_gov: 0,0212
- dep_sim: 0,0138
- colegas_n: 0,0071

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,6%)
- Veneziano Vital do Rêgo (MDB): 5,6% de 306 votos (mediana do partido: 3,0%)
- Eliane Nogueira (PP): 5,5% de 128 votos (mediana do partido: 3,9%)
- Luis Carlos Heinze (PP): 5,1% de 353 votos (mediana do partido: 3,9%)
- Marcio Bittar (MDB): 4,9% de 287 votos (mediana do partido: 3,0%)
- Esperidião Amin (PP): 4,5% de 354 votos (mediana do partido: 3,9%)
- Irajá (PSD): 4,5% de 244 votos (mediana do partido: 2,4%)
- Elmano Férrer (PP): 4,5% de 312 votos (mediana do partido: 3,9%)
- Carlos Portinho (PL): 4,4% de 203 votos (mediana do partido: 3,9%)
- Major Olimpio (PSL): 4,4% de 160 votos (mediana do partido: 3,5%)

## Temas com mais votos imprevisíveis

