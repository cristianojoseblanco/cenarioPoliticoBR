# Modelo de voto individual

453.810 votos (Sim × Não/Obstrução) em 1.126 votações. Validação cruzada por votação (5 grupos).

| Modelo | Acerto | AUC | Log-loss |
| --- | --- | --- | --- |
| M0 · segue o partido | 89,2% | 0,915 | 0,323 |
| M1 · partido, governo e colegas | 87,9% | 0,944 | 0,294 |
| M2 · + perfil do deputado e tema | 92,9% | 0,977 | 0,187 |

Votos imprevisíveis (probabilidade do voto observado abaixo de 20%): 13.230 (2,9%); 46,0% deles contra a orientação do partido.

## O que mais pesa na previsão (M2)

- colegas_sim: 0,7397
- plenario_sim: 0,0810
- dep_apoio_gov: 0,0809
- or_governo: 0,0719
- dep_disciplina: 0,0704
- dep_sim: 0,0113
- or_partido: 0,0100
- colegas_n: 0,0089

## Mais imprevisíveis (100+ votos)

- Paulinho da Força (SOLIDARIEDADE): 10,3% de 408 votos (mediana do partido: 6,0%)
- Weliton Prado (SOLIDARIEDADE): 10,0% de 832 votos (mediana do partido: 6,0%)
- Kim Kataguiri (UNIÃO): 9,2% de 889 votos (mediana do partido: 3,7%)
- Chiquinho Brazão (UNIÃO): 8,8% de 182 votos (mediana do partido: 3,7%)
- Rafael Fera (PODE): 8,8% de 274 votos (mediana do partido: 3,9%)
- Pedro Paulo (PSD): 8,7% de 595 votos (mediana do partido: 4,0%)
- Luiz Carlos Hauly (PODE): 8,4% de 798 votos (mediana do partido: 3,9%)
- Newton Cardoso Jr (MDB): 8,3% de 528 votos (mediana do partido: 3,7%)
- Alexandre Leite (UNIÃO): 8,1% de 472 votos (mediana do partido: 3,7%)
- Glaustin da Fokus (PODE): 7,8% de 658 votos (mediana do partido: 3,9%)

## Temas com mais votos imprevisíveis

- Energia, Recursos Hídricos e Minerais: 3,2% de 24.652 votos
- Administração Pública: 3,0% de 131.505 votos
- Finanças Públicas e Orçamento: 3,0% de 176.146 votos
- Direitos Humanos e Minorias: 2,9% de 70.928 votos
- Direito Penal e Processual Penal: 2,9% de 37.436 votos
- Economia: 2,9% de 64.833 votos
