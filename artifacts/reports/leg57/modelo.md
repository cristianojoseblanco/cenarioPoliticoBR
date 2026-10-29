# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 88,3% | 0,945 | 0,292 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.101 (2,9%); 45,7% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7064
- dep_apoio_gov: 0,0906
- plenario_sim: 0,0726
- or_governo: 0,0711
- dep_disciplina: 0,0635
- or_partido: 0,0113
- dep_sim: 0,0109
- colegas_n: 0,0077

## Mais imprevisíveis (100+ votos)

- Paulinho da Força (SOLIDARIEDADE): 10,3% de 408 votos (mediana do partido: 6,0%)
- Weliton Prado (SOLIDARIEDADE): 10,1% de 832 votos (mediana do partido: 6,0%)
- Rafael Fera (PODE): 9,5% de 274 votos (mediana do partido: 3,5%)
- Kim Kataguiri (UNIÃO): 9,0% de 889 votos (mediana do partido: 3,9%)
- Marco Bertaiolli (PSD): 8,4% de 107 votos (mediana do partido: 3,8%)
- Luiz Carlos Hauly (PODE): 8,3% de 798 votos (mediana do partido: 3,5%)
- Pedro Paulo (PSD): 8,1% de 595 votos (mediana do partido: 3,8%)
- Alexandre Leite (UNIÃO): 8,1% de 472 votos (mediana do partido: 3,9%)
- Dr. Daniel Soranz (PSD): 8,1% de 236 votos (mediana do partido: 3,8%)
- Newton Cardoso Jr (MDB): 8,0% de 528 votos (mediana do partido: 3,8%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,3% de 24.652 votos
- Administração Pública: 3,0% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
- Direitos Humanos e Minorias: 2,8% de 70.928 votos
- Economia: 2,8% de 64.833 votos
