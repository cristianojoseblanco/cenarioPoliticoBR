# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,5% | 0,935 | 0,263 |
| M2 · + perfil do senador e tema | 92,1% | 0,963 | 0,192 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 753 (2,9%); 22,0% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1782
- plenario_sim: 0,1669
- or_partido: 0,0948
- or_governo: 0,0214
- dep_apoio_gov: 0,0205
- dep_disciplina: 0,0196
- dep_sim: 0,0129
- comunidade: 0,0086

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,5%)
- Renan Calheiros (MDB): 5,6% de 179 votos (mediana do partido: 3,8%)
- Veneziano Vital do Rêgo (MDB): 5,6% de 306 votos (mediana do partido: 3,8%)
- Jarbas Vasconcelos (MDB): 5,2% de 310 votos (mediana do partido: 3,8%)
- José Serra (PSDB): 5,0% de 280 votos (mediana do partido: 3,5%)
- Carlos Portinho (PL): 4,9% de 203 votos (mediana do partido: 3,8%)
- Marcio Bittar (MDB): 4,9% de 287 votos (mediana do partido: 3,8%)
- Elmano Férrer (PP): 4,8% de 312 votos (mediana do partido: 3,5%)
- Rodrigo Cunha (PSDB): 4,6% de 303 votos (mediana do partido: 3,5%)
- Luis Carlos Heinze (PP): 4,5% de 353 votos (mediana do partido: 3,5%)

## Temas com mais votos imprevisíveis

