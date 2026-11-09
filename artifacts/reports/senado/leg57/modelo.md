# Modelo de voto individual

11.865 votos (Sim × Não/Obstrução) em 181 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 90,6% | 0,920 | 0,265 |
| M1 · partido, governo e colegas | 87,5% | 0,926 | 0,317 |
| M2 · + perfil do senador e tema | 92,7% | 0,966 | 0,211 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 456 (3,8%); 32,5% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- or_partido: 0,2674
- plenario_sim: 0,1890
- colegas_sim: 0,0770
- dep_disciplina: 0,0424
- or_governo: 0,0407
- dep_apoio_gov: 0,0404
- dep_sim: 0,0189
- colegas_n: 0,0115

## Mais imprevisíveis (100+ votos)

- Irajá (PSD): 12,6% de 95 votos (mediana do partido: 4,2%)
- Sergio Moro (UNIÃO): 10,3% de 165 votos (mediana do partido: 2,8%)
- Alessandro Vieira (MDB): 8,8% de 148 votos (mediana do partido: 2,7%)
- Flávio Arns (PSB): 8,2% de 146 votos (mediana do partido: 5,4%)
- Cid Gomes (PSB): 7,7% de 91 votos (mediana do partido: 5,4%)
- Cleitinho (REPUBLICANOS): 6,8% de 176 votos (mediana do partido: 5,2%)
- Rodrigo Pacheco (PSD): 6,7% de 60 votos (mediana do partido: 4,2%)
- Soraya Thronicke (PODE): 6,6% de 151 votos (mediana do partido: 6,2%)
- Carlos Viana (PODE): 6,6% de 137 votos (mediana do partido: 6,2%)
- Mara Gabrilli (PSD): 6,6% de 122 votos (mediana do partido: 4,2%)

## Temas com mais votos imprevisíveis

