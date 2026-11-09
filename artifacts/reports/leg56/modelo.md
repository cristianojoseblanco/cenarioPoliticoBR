# Modelo de voto individual

786.779 votos (Sim × Não/Obstrução) em 1.970 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 93,0% | 0,939 | 0,244 |
| M1 · partido, governo e colegas | 93,0% | 0,972 | 0,204 |
| M2 · + perfil do deputado e tema | 94,4% | 0,984 | 0,155 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 20.098 (2,6%); 81,2% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7120
- plenario_sim: 0,0562
- dep_disciplina: 0,0491
- dep_apoio_gov: 0,0378
- or_partido: 0,0233
- or_governo: 0,0166
- colegas_n: 0,0055
- dep_sim: 0,0047

## Mais imprevisíveis (100+ votos)

- Ricardo Izar (PP): 7,9% de 1.275 votos (mediana do partido: 1,8%)
- Tabata Amaral (PDT): 7,6% de 1.754 votos (mediana do partido: 3,1%)
- Danrlei de Deus Hinterholz (PSD): 7,5% de 853 votos (mediana do partido: 3,0%)
- Nelho Bezerra (UNIÃO): 7,4% de 216 votos (mediana do partido: 4,1%)
- Gastão Vieira (PROS): 7,3% de 1.143 votos (mediana do partido: 3,3%)
- Mauro Nazif (PSB): 7,2% de 1.774 votos (mediana do partido: 2,3%)
- Rodrigo Maia (DEM): 7,1% de 491 votos (mediana do partido: 2,5%)
- Hélio Costa (REPUBLICANOS): 7,1% de 1.803 votos (mediana do partido: 1,3%)
- Daniel Coelho (CIDADANIA): 6,9% de 1.583 votos (mediana do partido: 4,1%)
- Angela Amin (PP): 6,8% de 1.799 votos (mediana do partido: 1,8%)

## Temas com mais votos imprevisíveis

- Política, Partidos e Eleições: 4,1% de 42.204 votos
- Educação: 2,7% de 52.101 votos
- Energia, Recursos Hídricos e Minerais: 2,7% de 69.707 votos
- Administração Pública: 2,7% de 226.423 votos
- Viação, Transporte e Mobilidade: 2,5% de 59.886 votos
- Saúde: 2,5% de 118.412 votos
