# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 87,9% | 0,943 | 0,297 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.105 (2,9%); 45,5% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7216
- plenario_sim: 0,0800
- dep_apoio_gov: 0,0717
- dep_disciplina: 0,0661
- or_governo: 0,0636
- dep_sim: 0,0133
- colegas_n: 0,0086
- or_partido: 0,0075

## Mais imprevisíveis (100+ votos)

- Rafael Fera (PODE): 10,6% de 274 votos (mediana do partido: 3,8%)
- Paulinho da Força (SOLIDARIEDADE): 10,0% de 408 votos (mediana do partido: 6,5%)
- Kim Kataguiri (UNIÃO): 9,7% de 889 votos (mediana do partido: 3,7%)
- Weliton Prado (SOLIDARIEDADE): 9,6% de 832 votos (mediana do partido: 6,5%)
- Dr. Daniel Soranz (PSD): 9,3% de 236 votos (mediana do partido: 4,1%)
- Alexandre Leite (UNIÃO): 8,7% de 472 votos (mediana do partido: 3,7%)
- Pedro Paulo (PSD): 8,6% de 595 votos (mediana do partido: 4,1%)
- Chiquinho Brazão (UNIÃO): 8,2% de 182 votos (mediana do partido: 3,7%)
- Newton Cardoso Jr (MDB): 8,0% de 528 votos (mediana do partido: 3,6%)
- Luiz Carlos Hauly (PODE): 7,8% de 798 votos (mediana do partido: 3,8%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,1% de 24.652 votos
- Administração Pública: 2,9% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direito Penal e Processual Penal: 2,9% de 37.436 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Economia: 2,8% de 64.833 votos
