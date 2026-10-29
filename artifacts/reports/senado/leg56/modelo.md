# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,8% | 0,936 | 0,260 |
| M2 · + perfil do senador e tema | 92,2% | 0,964 | 0,191 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 738 (2,9%); 20,9% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- plenario_sim: 0,2209
- colegas_sim: 0,1599
- or_partido: 0,1183
- or_governo: 0,0300
- dep_apoio_gov: 0,0269
- dep_disciplina: 0,0234
- dep_sim: 0,0128
- comunidade: 0,0093

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 8,0% de 50 votos (mediana do partido: 3,7%)
- Luis Carlos Heinze (PP): 5,7% de 353 votos (mediana do partido: 4,0%)
- Esperidião Amin (PP): 5,6% de 354 votos (mediana do partido: 4,0%)
- Eliane Nogueira (PP): 5,5% de 128 votos (mediana do partido: 4,0%)
- Veneziano Vital do Rêgo (MDB): 5,2% de 306 votos (mediana do partido: 3,0%)
- José Serra (PSDB): 5,0% de 280 votos (mediana do partido: 3,7%)
- Romário (PL): 5,0% de 322 votos (mediana do partido: 4,3%)
- Renan Calheiros (MDB): 4,5% de 179 votos (mediana do partido: 3,0%)
- Carlos Portinho (PL): 4,4% de 203 votos (mediana do partido: 4,3%)
- Fernando Bezerra Coelho (MDB): 4,4% de 340 votos (mediana do partido: 3,0%)

## Temas com mais votos imprevisíveis

