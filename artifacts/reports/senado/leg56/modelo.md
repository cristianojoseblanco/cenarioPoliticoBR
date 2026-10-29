# Modelo de voto individual

25.616 votos (Sim × Não/Obstrução) em 367 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,915 | 0,261 |
| M1 · partido, governo e colegas | 89,1% | 0,937 | 0,258 |
| M2 · + perfil do senador e tema | 92,2% | 0,963 | 0,191 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 716 (2,8%); 20,4% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,1962
- plenario_sim: 0,1464
- or_partido: 0,0826
- or_governo: 0,0209
- dep_apoio_gov: 0,0199
- dep_disciplina: 0,0195
- dep_sim: 0,0136
- colegas_n: 0,0066

## Mais imprevisíveis (100+ votos)

- José Aníbal (PSDB): 6,0% de 50 votos (mediana do partido: 3,2%)
- Renan Calheiros (MDB): 5,6% de 179 votos (mediana do partido: 2,9%)
- Carlos Portinho (PL): 4,9% de 203 votos (mediana do partido: 4,2%)
- Irajá (PSD): 4,9% de 244 votos (mediana do partido: 2,3%)
- Luis Carlos Heinze (PP): 4,8% de 353 votos (mediana do partido: 3,1%)
- Eliane Nogueira (PP): 4,7% de 128 votos (mediana do partido: 3,1%)
- Veneziano Vital do Rêgo (MDB): 4,6% de 306 votos (mediana do partido: 2,9%)
- Marcio Bittar (MDB): 4,5% de 287 votos (mediana do partido: 2,9%)
- Oriovisto Guimarães (PODE): 4,4% de 318 votos (mediana do partido: 2,8%)
- Zequinha Marinho (PSC): 4,3% de 299 votos (mediana do partido: 4,3%)

## Temas com mais votos imprevisíveis

