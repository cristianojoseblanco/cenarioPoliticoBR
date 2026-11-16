# Modelo de voto individual

12.159 votos (Sim × Não/Obstrução) em 185 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,5% | 0,918 | 0,268 |
| M1 · partido, governo e colegas | 87,4% | 0,923 | 0,324 |
| M2 · + perfil do senador e tema | 92,4% | 0,966 | 0,212 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 476 (3,9%); 31,9% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- or_partido: 0,1979
- plenario_sim: 0,1812
- colegas_sim: 0,0970
- dep_apoio_gov: 0,0322
- or_governo: 0,0257
- dep_disciplina: 0,0176
- dep_sim: 0,0111
- colegas_n: 0,0075

## Mais imprevisíveis (100+ votos)

- Irajá (PSD): 11,2% de 98 votos (mediana do partido: 3,5%)
- Mara Gabrilli (PSD): 9,5% de 126 votos (mediana do partido: 3,5%)
- Sergio Moro (UNIÃO): 9,5% de 168 votos (mediana do partido: 3,7%)
- Alessandro Vieira (MDB): 9,2% de 152 votos (mediana do partido: 3,5%)
- Cleitinho (REPUBLICANOS): 8,3% de 180 votos (mediana do partido: 5,3%)
- Carlos Viana (PODE): 7,9% de 140 votos (mediana do partido: 5,3%)
- Styvenson Valentim (PODE): 7,6% de 158 votos (mediana do partido: 5,3%)
- Romário (PL): 7,4% de 136 votos (mediana do partido: 3,0%)
- Margareth Buzetti (PSD): 7,3% de 96 votos (mediana do partido: 3,5%)
- Plínio Valério (PSDB): 6,4% de 173 votos (mediana do partido: 6,4%)

## Temas com mais votos imprevisíveis

