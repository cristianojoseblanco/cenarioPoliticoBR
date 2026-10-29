# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,4% | 0,934 | 0,266 |
| M2 · + perfil do senador e tema | 92,1% | 0,964 | 0,189 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 695 (2,7%); 21,9% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1850
- plenario_sim: 0,1587
- or_partido: 0,0869
- or_governo: 0,0273
- dep_disciplina: 0,0222
- dep_apoio_gov: 0,0211
- dep_sim: 0,0132
- colegas_n: 0,0087

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,9%)
- Luis Carlos Heinze (PP): 5,1% de 353 votos (mediana do partido: 3,0%)
- Carlos Portinho (PL): 4,9% de 203 votos (mediana do partido: 3,6%)
- Elmano Férrer (PP): 4,5% de 312 votos (mediana do partido: 3,0%)
- Renan Calheiros (MDB): 4,5% de 179 votos (mediana do partido: 2,9%)
- Major Olimpio (PSL): 4,4% de 160 votos (mediana do partido: 3,2%)
- Rodrigo Cunha (PSDB): 4,3% de 303 votos (mediana do partido: 3,9%)
- José Serra (PSDB): 4,3% de 280 votos (mediana do partido: 3,9%)
- Esperidião Amin (PP): 4,2% de 354 votos (mediana do partido: 3,0%)
- Marcio Bittar (MDB): 4,2% de 287 votos (mediana do partido: 2,9%)

## Temas com mais votos imprevisíveis

