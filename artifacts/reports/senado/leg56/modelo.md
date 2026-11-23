# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 88,6% | 0,935 | 0,264 |
| M2 · + perfil do senador e tema | 92,1% | 0,964 | 0,189 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 706 (2,8%); 21,2% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- plenario_sim: 0,2022
- colegas_sim: 0,1622
- or_partido: 0,1462
- or_governo: 0,0282
- dep_disciplina: 0,0244
- dep_apoio_gov: 0,0238
- dep_sim: 0,0143
- comunidade: 0,0072

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,5%)
- Major Olimpio (PSL): 5,0% de 160 votos (mediana do partido: 4,0%)
- Veneziano Vital do Rêgo (MDB): 4,9% de 306 votos (mediana do partido: 2,6%)
- Esperidião Amin (PP): 4,8% de 354 votos (mediana do partido: 3,6%)
- Dário Berger (MDB): 4,7% de 338 votos (mediana do partido: 2,6%)
- Irajá (PSD): 4,5% de 244 votos (mediana do partido: 2,3%)
- Elmano Férrer (PP): 4,5% de 312 votos (mediana do partido: 3,6%)
- Otto Alencar (PSD): 4,5% de 314 votos (mediana do partido: 2,3%)
- Alessandro Vieira (CIDADANIA): 4,3% de 347 votos (mediana do partido: 3,4%)
- José Serra (PSDB): 4,3% de 280 votos (mediana do partido: 3,5%)

## Temas com mais votos imprevisíveis

