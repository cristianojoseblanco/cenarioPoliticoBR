# Modelo de voto individual

12.464 votos (Sim × Não/Obstrução) em 189 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,5% | 0,917 | 0,271 |
| M1 · partido, governo e colegas | 86,0% | 0,919 | 0,326 |
| M2 · + perfil do senador e tema | 93,0% | 0,969 | 0,201 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 442 (3,5%); 37,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- plenario_sim: 0,3133
- or_partido: 0,2421
- or_governo: 0,1139
- colegas_sim: 0,1051
- dep_apoio_gov: 0,1025
- dep_sim: 0,0315
- dep_disciplina: 0,0240
- colegas_n: 0,0129

## Mais imprevisíveis (100+ votos)

- Irajá (PSD): 10,8% de 102 votos (mediana do partido: 3,3%)
- Sergio Moro (UNIÃO): 9,3% de 172 votos (mediana do partido: 3,0%)
- Lucas Barreto (PSD): 8,6% de 163 votos (mediana do partido: 3,3%)
- Romário (PL): 7,1% de 140 votos (mediana do partido: 1,8%)
- Alessandro Vieira (MDB): 7,1% de 156 votos (mediana do partido: 3,2%)
- Oriovisto Guimarães (PODE): 6,5% de 154 votos (mediana do partido: 5,7%)
- Luis Carlos Heinze (PP): 6,2% de 145 votos (mediana do partido: 4,7%)
- Styvenson Valentim (PODE): 6,2% de 162 votos (mediana do partido: 5,7%)
- Cid Gomes (PSB): 6,1% de 98 votos (mediana do partido: 4,4%)
- Cleitinho (REPUBLICANOS): 6,0% de 184 votos (mediana do partido: 4,0%)

## Temas com mais votos imprevisíveis

