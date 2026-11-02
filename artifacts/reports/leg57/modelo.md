# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,0% | 0,943 | 0,297 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.202 (2,9%); 45,1% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,6939
- dep_disciplina: 0,0735
- dep_apoio_gov: 0,0709
- plenario_sim: 0,0681
- or_governo: 0,0649
- dep_sim: 0,0145
- or_partido: 0,0138
- colegas_n: 0,0075

## Mais imprevisíveis (100+ votos)

- Kim Kataguiri (UNIÃO): 9,6% de 889 votos (mediana do partido: 3,7%)
- Paulinho da Força (SOLIDARIEDADE): 9,6% de 408 votos (mediana do partido: 5,9%)
- Weliton Prado (SOLIDARIEDADE): 9,3% de 832 votos (mediana do partido: 5,9%)
- Chiquinho Brazão (UNIÃO): 8,8% de 182 votos (mediana do partido: 3,7%)
- Pedro Paulo (PSD): 8,6% de 595 votos (mediana do partido: 3,8%)
- Alexandre Leite (UNIÃO): 8,3% de 472 votos (mediana do partido: 3,7%)
- Socorro Neri (PP): 8,1% de 889 votos (mediana do partido: 3,1%)
- Rafael Fera (PODE): 8,0% de 274 votos (mediana do partido: 4,2%)
- Luiz Carlos Hauly (PODE): 8,0% de 798 votos (mediana do partido: 4,2%)
- Newton Cardoso Jr (MDB): 8,0% de 528 votos (mediana do partido: 3,6%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,1% de 24.652 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Administração Pública: 2,9% de 131.505 votos
- Economia: 2,9% de 64.833 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
