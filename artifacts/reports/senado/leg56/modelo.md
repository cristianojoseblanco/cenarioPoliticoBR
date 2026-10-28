# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,6% | 0,935 | 0,264 |
| M2 · + perfil do deputado e tema | 92,1% | 0,964 | 0,192 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 761 (3,0%); 20,2% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- plenario_sim: 0,1866
- colegas_sim: 0,1800
- or_partido: 0,1068
- dep_apoio_gov: 0,0251
- or_governo: 0,0248
- dep_disciplina: 0,0241
- dep_sim: 0,0147
- comunidade: 0,0085

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 3,7%)
- José Serra (PSDB): 5,4% de 280 votos (mediana do partido: 3,7%)
- Jarbas Vasconcelos (MDB): 5,2% de 310 votos (mediana do partido: 3,3%)
- Marcio Bittar (MDB): 4,9% de 287 votos (mediana do partido: 3,3%)
- Fernando Bezerra Coelho (MDB): 4,7% de 340 votos (mediana do partido: 3,3%)
- Romário (PL): 4,7% de 322 votos (mediana do partido: 3,8%)
- Veneziano Vital do Rêgo (MDB): 4,6% de 306 votos (mediana do partido: 3,3%)
- Luis Carlos Heinze (PP): 4,5% de 353 votos (mediana do partido: 3,5%)
- Esperidião Amin (PP): 4,5% de 354 votos (mediana do partido: 3,5%)
- Renan Calheiros (MDB): 4,5% de 179 votos (mediana do partido: 3,3%)

## Temas com mais votos imprevisíveis

