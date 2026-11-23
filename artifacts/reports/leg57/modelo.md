# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 87,8% | 0,944 | 0,296 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,186 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.120 (2,9%); 45,6% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7635
- dep_apoio_gov: 0,0757
- dep_disciplina: 0,0676
- or_governo: 0,0665
- plenario_sim: 0,0650
- dep_sim: 0,0122
- or_partido: 0,0092
- colegas_n: 0,0077

## Mais imprevisíveis (100+ votos)

- Paulinho da Força (SOLIDARIEDADE): 11,0% de 408 votos (mediana do partido: 5,9%)
- Kim Kataguiri (UNIÃO): 9,6% de 889 votos (mediana do partido: 3,7%)
- Dr. Daniel Soranz (PSD): 9,3% de 236 votos (mediana do partido: 3,9%)
- Weliton Prado (SOLIDARIEDADE): 8,8% de 832 votos (mediana do partido: 5,9%)
- Rafael Fera (PODE): 8,8% de 274 votos (mediana do partido: 4,0%)
- Pedro Paulo (PSD): 8,7% de 595 votos (mediana do partido: 3,9%)
- Marco Bertaiolli (PSD): 8,4% de 107 votos (mediana do partido: 3,9%)
- Chiquinho Brazão (UNIÃO): 8,2% de 182 votos (mediana do partido: 3,7%)
- Newton Cardoso Jr (MDB): 8,1% de 528 votos (mediana do partido: 3,6%)
- Socorro Neri (PP): 7,9% de 889 votos (mediana do partido: 3,1%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,2% de 24.652 votos
- Administração Pública: 2,9% de 131.505 votos
- Finanças Públicas e Orçamento: 2,9% de 176.146 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Direito Penal e Processual Penal: 2,8% de 37.436 votos
- Economia: 2,8% de 64.833 votos
