# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,1% | 0,944 | 0,295 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,187 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.123 (2,9%); 45,4% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,6984
- dep_disciplina: 0,0741
- plenario_sim: 0,0708
- dep_apoio_gov: 0,0703
- or_governo: 0,0624
- or_partido: 0,0137
- dep_sim: 0,0128
- colegas_n: 0,0079

## Mais imprevisíveis (100+ votos)

- Weliton Prado (SOLIDARIEDADE): 10,3% de 832 votos (mediana do partido: 6,3%)
- Paulinho da Força (SOLIDARIEDADE): 9,6% de 408 votos (mediana do partido: 6,3%)
- Kim Kataguiri (UNIÃO): 9,2% de 889 votos (mediana do partido: 3,8%)
- Pedro Paulo (PSD): 8,6% de 595 votos (mediana do partido: 3,7%)
- Rafael Fera (PODE): 8,4% de 274 votos (mediana do partido: 3,8%)
- Luiz Carlos Hauly (PODE): 8,3% de 798 votos (mediana do partido: 3,8%)
- Chiquinho Brazão (UNIÃO): 8,2% de 182 votos (mediana do partido: 3,8%)
- Newton Cardoso Jr (MDB): 8,1% de 528 votos (mediana do partido: 3,7%)
- Dr. Daniel Soranz (PSD): 8,1% de 236 votos (mediana do partido: 3,7%)
- Alexandre Leite (UNIÃO): 7,8% de 472 votos (mediana do partido: 3,8%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,3% de 24.652 votos
- Administração Pública: 2,9% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direito Penal e Processual Penal: 2,9% de 37.436 votos
- Economia: 2,9% de 64.833 votos
- Direitos Humanos e Minorias: 2,8% de 70.928 votos
