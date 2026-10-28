# Modelo de voto individual

11.576 votos (Sim × Não/Obstrução) em 177 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,5% | 0,919 | 0,268 |
| M1 · partido, governo e colegas | 86,0% | 0,916 | 0,340 |
| M2 · + perfil do deputado e tema | 92,3% | 0,964 | 0,221 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 468 (4,0%); 31,0% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- or_partido: 0,3763
- plenario_sim: 0,2809
- colegas_sim: 0,1256
- dep_disciplina: 0,0561
- or_governo: 0,0486
- dep_apoio_gov: 0,0351
- dep_sim: 0,0174
- colegas_n: 0,0141

## Mais imprevisíveis (100+ votos)

- Irajá (PSD): 12,9% de 93 votos (mediana do partido: 4,6%)
- Mara Gabrilli (PSD): 10,2% de 118 votos (mediana do partido: 4,6%)
- Sergio Moro (UNIÃO): 8,7% de 161 votos (mediana do partido: 3,2%)
- Lucas Barreto (PSD): 8,6% de 151 votos (mediana do partido: 4,6%)
- Weverton (PDT): 7,7% de 142 votos (mediana do partido: 3,8%)
- Alessandro Vieira (MDB): 7,6% de 144 votos (mediana do partido: 3,0%)
- Fernando Farias (MDB): 7,6% de 144 votos (mediana do partido: 3,0%)
- Margareth Buzetti (PSD): 7,3% de 96 votos (mediana do partido: 4,6%)
- Rodrigo Cunha (PODE): 7,0% de 86 votos (mediana do partido: 5,6%)
- Cleitinho (REPUBLICANOS): 7,0% de 172 votos (mediana do partido: 6,0%)

## Temas com mais votos imprevisíveis

