# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,2% | 0,944 | 0,295 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.204 (2,9%); 45,5% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7023
- dep_apoio_gov: 0,0739
- dep_disciplina: 0,0731
- plenario_sim: 0,0704
- or_governo: 0,0621
- dep_sim: 0,0110
- or_partido: 0,0100
- colegas_n: 0,0081

## Mais imprevisíveis (100+ votos)

- Kim Kataguiri (UNIÃO): 10,2% de 889 votos (mediana do partido: 3,7%)
- Weliton Prado (SOLIDARIEDADE): 10,2% de 832 votos (mediana do partido: 6,0%)
- Marco Bertaiolli (PSD): 9,3% de 107 votos (mediana do partido: 3,8%)
- Paulinho da Força (SOLIDARIEDADE): 8,8% de 408 votos (mediana do partido: 6,0%)
- Chiquinho Brazão (UNIÃO): 8,8% de 182 votos (mediana do partido: 3,7%)
- Dr. Daniel Soranz (PSD): 8,5% de 236 votos (mediana do partido: 3,8%)
- Pedro Paulo (PSD): 8,4% de 595 votos (mediana do partido: 3,8%)
- Rafael Fera (PODE): 8,0% de 274 votos (mediana do partido: 3,6%)
- Duda Ramos (MDB): 7,9% de 717 votos (mediana do partido: 3,5%)
- Socorro Neri (PP): 7,6% de 889 votos (mediana do partido: 3,1%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,2% de 24.652 votos
- Administração Pública: 3,0% de 131.505 votos
- Finanças Públicas e Orçamento: 3,0% de 176.146 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Economia: 2,9% de 64.833 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
