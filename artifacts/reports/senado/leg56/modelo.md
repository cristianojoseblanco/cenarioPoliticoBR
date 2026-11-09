# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 89,0% | 0,936 | 0,262 |
| M2 · + perfil do senador e tema | 92,2% | 0,964 | 0,190 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 706 (2,8%); 21,4% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1634
- plenario_sim: 0,1615
- or_partido: 0,0797
- or_governo: 0,0255
- dep_apoio_gov: 0,0212
- dep_disciplina: 0,0190
- dep_sim: 0,0107
- comunidade: 0,0081

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,5%)
- Esperidião Amin (PP): 5,4% de 354 votos (mediana do partido: 4,2%)
- Elmano Férrer (PP): 5,1% de 312 votos (mediana do partido: 4,2%)
- Major Olimpio (PSL): 5,0% de 160 votos (mediana do partido: 3,7%)
- Carlos Portinho (PL): 4,9% de 203 votos (mediana do partido: 3,8%)
- Eliane Nogueira (PP): 4,7% de 128 votos (mediana do partido: 4,2%)
- José Serra (PSDB): 4,6% de 280 votos (mediana do partido: 3,5%)
- Veneziano Vital do Rêgo (MDB): 4,6% de 306 votos (mediana do partido: 2,7%)
- Luis Carlos Heinze (PP): 4,5% de 353 votos (mediana do partido: 4,2%)
- Irajá (PSD): 4,5% de 244 votos (mediana do partido: 2,1%)

## Temas com mais votos imprevisíveis

