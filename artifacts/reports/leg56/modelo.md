# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 93,0% | 0,972 | 0,205 |
| M2 · + perfil do deputado e tema | 94,3% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 20.165 (2,6%); 81,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,8378
- plenario_sim: 0,0473
- dep_disciplina: 0,0472
- dep_apoio_gov: 0,0320
- or_partido: 0,0156
- or_governo: 0,0128
- colegas_n: 0,0055
- dep_sim: 0,0040

## Mais imprevisíveis (100+ votos)

- Nelho Bezerra (UNIÃO): 9,7% de 216 votos (mediana do partido: 4,1%)
- Patrick Dorneles (PSD): 9,4% de 106 votos (mediana do partido: 2,9%)
- Rodrigo Maia (DEM): 8,6% de 491 votos (mediana do partido: 2,5%)
- Ricardo Izar (PP): 7,8% de 1.275 votos (mediana do partido: 1,9%)
- Danrlei de Deus Hinterholz (PSD): 7,6% de 853 votos (mediana do partido: 2,9%)
- Tabata Amaral (PDT): 7,5% de 1.754 votos (mediana do partido: 3,2%)
- Mauro Nazif (PSB): 7,3% de 1.774 votos (mediana do partido: 2,4%)
- Daniel Coelho (CIDADANIA): 7,2% de 1.583 votos (mediana do partido: 3,8%)
- Gastão Vieira (PROS): 7,1% de 1.143 votos (mediana do partido: 3,3%)
- Hélio Costa (REPUBLICANOS): 7,0% de 1.803 votos (mediana do partido: 1,3%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,1% de 42.204 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Educação: 2,7% de 52.101 votos
- Administração Pública: 2,6% de 226.423 votos
- Saúde: 2,5% de 118.412 votos
- Finanças Públicas e Orçamento: 2,4% de 231.937 votos
