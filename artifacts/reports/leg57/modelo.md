# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,1% | 0,944 | 0,295 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.133 (2,9%); 45,8% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7306
- dep_apoio_gov: 0,0787
- plenario_sim: 0,0750
- dep_disciplina: 0,0668
- or_governo: 0,0614
- dep_sim: 0,0112
- or_partido: 0,0088
- colegas_n: 0,0082

## Mais imprevisíveis (100+ votos)

- Weliton Prado (SOLIDARIEDADE): 10,9% de 832 votos (mediana do partido: 6,0%)
- Paulinho da Força (SOLIDARIEDADE): 10,0% de 408 votos (mediana do partido: 6,0%)
- Rafael Fera (PODE): 9,9% de 274 votos (mediana do partido: 4,0%)
- Kim Kataguiri (UNIÃO): 9,0% de 889 votos (mediana do partido: 3,6%)
- Luiz Carlos Hauly (PODE): 8,6% de 798 votos (mediana do partido: 4,0%)
- Newton Cardoso Jr (MDB): 8,5% de 528 votos (mediana do partido: 3,7%)
- Pedro Paulo (PSD): 8,4% de 595 votos (mediana do partido: 3,6%)
- Alexandre Leite (UNIÃO): 8,3% de 472 votos (mediana do partido: 3,6%)
- Socorro Neri (PP): 8,0% de 889 votos (mediana do partido: 3,2%)
- Chiquinho Brazão (UNIÃO): 7,7% de 182 votos (mediana do partido: 3,6%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,3% de 24.652 votos
- Administração Pública: 3,0% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
- Economia: 2,8% de 64.833 votos
