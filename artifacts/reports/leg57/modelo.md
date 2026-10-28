# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,1% | 0,944 | 0,296 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.173 (2,9%); 45,6% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7331
- dep_apoio_gov: 0,0763
- plenario_sim: 0,0759
- dep_disciplina: 0,0677
- or_governo: 0,0628
- dep_sim: 0,0133
- or_partido: 0,0090
- colegas_n: 0,0088

## Mais imprevisíveis (100+ votos)

- Weliton Prado (SOLIDARIEDADE): 10,8% de 832 votos (mediana do partido: 5,8%)
- Paulinho da Força (SOLIDARIEDADE): 10,5% de 408 votos (mediana do partido: 5,8%)
- Kim Kataguiri (UNIÃO): 9,3% de 889 votos (mediana do partido: 3,7%)
- Dr. Daniel Soranz (PSD): 8,9% de 236 votos (mediana do partido: 3,9%)
- Chiquinho Brazão (UNIÃO): 8,8% de 182 votos (mediana do partido: 3,7%)
- Marco Bertaiolli (PSD): 8,4% de 107 votos (mediana do partido: 3,9%)
- Pedro Paulo (PSD): 8,4% de 595 votos (mediana do partido: 3,9%)
- Luiz Carlos Hauly (PODE): 8,1% de 798 votos (mediana do partido: 3,7%)
- Newton Cardoso Jr (MDB): 8,1% de 528 votos (mediana do partido: 3,7%)
- Duda Ramos (MDB): 8,1% de 717 votos (mediana do partido: 3,7%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,4% de 24.652 votos
- Administração Pública: 3,0% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Economia: 2,8% de 64.833 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
