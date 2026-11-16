# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,6% | 0,936 | 0,264 |
| M2 · + perfil do senador e tema | 92,2% | 0,964 | 0,188 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 724 (2,8%); 21,3% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- plenario_sim: 0,1736
- colegas_sim: 0,1731
- or_partido: 0,0998
- or_governo: 0,0226
- dep_disciplina: 0,0216
- dep_sim: 0,0161
- dep_apoio_gov: 0,0147
- comunidade: 0,0090

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 4,0%)
- Luis Carlos Heinze (PP): 5,7% de 353 votos (mediana do partido: 3,7%)
- Esperidião Amin (PP): 5,6% de 354 votos (mediana do partido: 3,7%)
- Veneziano Vital do Rêgo (MDB): 4,6% de 306 votos (mediana do partido: 3,0%)
- Elmano Férrer (PP): 4,5% de 312 votos (mediana do partido: 3,7%)
- Otto Alencar (PSD): 4,5% de 314 votos (mediana do partido: 2,7%)
- Jorginho Mello (PL): 4,4% de 338 votos (mediana do partido: 4,0%)
- Arolde de Oliveira (PSD): 4,3% de 138 votos (mediana do partido: 2,7%)
- Rodrigo Cunha (PSDB): 4,3% de 303 votos (mediana do partido: 4,0%)
- Marcio Bittar (MDB): 4,2% de 287 votos (mediana do partido: 3,0%)

## Temas com mais votos imprevisíveis

