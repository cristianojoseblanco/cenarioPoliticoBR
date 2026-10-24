# Relatório de qualidade — Câmara (staging)

Problemas encontrados: 0

## deputados

- Linhas: 7.889
- Colunas (13): `uri`, `nome`, `idLegislaturaInicial`, `idLegislaturaFinal`, `nomeCivil`, `cpf`, `siglaSexo`, `urlRedeSocial`, `urlWebsite`, `dataNascimento`, `dataFalecimento`, `ufNascimento`, `municipioNascimento`
- Chave (uri) única

## votacoes

- Linhas: 42.490
  - 2023: 10.851
  - 2024: 10.373
  - 2025: 13.827
  - 2026: 7.439
- Colunas (20): `id`, `uri`, `data`, `dataHoraRegistro`, `idOrgao`, `uriOrgao`, `siglaOrgao`, `idEvento`, `uriEvento`, `aprovacao`, `votosSim`, `votosNao`, `votosOutros`, `descricao`, `ultimaAberturaVotacao_dataHoraRegistro`, `ultimaAberturaVotacao_descricao`, `ultimaApresentacaoProposicao_dataHoraRegistro`, `ultimaApresentacaoProposicao_descricao`, `ultimaApresentacaoProposicao_idProposicao`, `ultimaApresentacaoProposicao_uriProposicao`
- Chave (id) única

## votacoesVotos

- Linhas: 473.272
  - 2023: 128.679
  - 2024: 116.400
  - 2025: 175.067
  - 2026: 53.126
- Colunas (12): `idVotacao`, `uriVotacao`, `dataHoraVoto`, `voto`, `deputado_id`, `deputado_uri`, `deputado_nome`, `deputado_siglaPartido`, `deputado_uriPartido`, `deputado_siglaUf`, `deputado_idLegislatura`, `deputado_urlFoto`
- Chave (idVotacao, deputado_id) única
- Valores de `voto`:
  - `Sim`: 277.280 de 473.272 (58,6%)
  - `Não`: 187.657 de 473.272 (39,7%)
  - `Obstrução`: 5.272 de 473.272 (1,1%)
  - `Abstenção`: 1.131 de 473.272 (0,2%)
  - `Artigo 17`: 1.045 de 473.272 (0,2%)
  - `None`: 887 de 473.272 (0,2%)

## votacoesOrientacoes

- Linhas: 15.571
  - 2023: 4.359
  - 2024: 4.361
  - 2025: 4.947
  - 2026: 1.904
- Colunas (7): `idVotacao`, `uriVotacao`, `siglaOrgao`, `descricao`, `siglaBancada`, `uriBancada`, `orientacao`
- Chave (idVotacao, siglaBancada) única

## votacoesProposicoes

- Linhas: 32.338
  - 2023: 8.811
  - 2024: 7.459
  - 2025: 10.331
  - 2026: 5.737
- Colunas (12): `idVotacao`, `uriVotacao`, `data`, `descricao`, `proposicao_id`, `proposicao_uri`, `proposicao_titulo`, `proposicao_ementa`, `proposicao_codTipo`, `proposicao_siglaTipo`, `proposicao_numero`, `proposicao_ano`
- Chave (idVotacao, proposicao_id) única

## proposicoes

- Linhas: 796.570
  - 2003: 31.994
  - 2004: 23.739
  - 2005: 26.150
  - 2007: 32.520
  - 2008: 30.315
  - 2010: 18.854
  - 2011: 33.580
  - 2012: 23.510
  - 2013: 29.153
  - 2014: 17.401
  - 2015: 39.648
  - 2016: 24.998
  - 2017: 32.565
  - 2018: 18.710
  - 2019: 38.494
  - 2020: 29.766
  - 2021: 39.872
  - 2022: 26.918
  - 2023: 62.437
  - 2024: 61.536
  - 2025: 107.587
  - 2026: 46.823
- Colunas (30): `id`, `uri`, `siglaTipo`, `numero`, `codTipo`, `descricaoTipo`, `ementa`, `ementaDetalhada`, `keywords`, `dataApresentacao`, `uriOrgaoNumerador`, `uriPropAnterior`, `uriPropPrincipal`, `uriPropPosterior`, `urlInteiroTeor`, `urnFinal`, `ultimoStatus_dataHora`, `ultimoStatus_sequencia`, `ultimoStatus_uriRelator`, `ultimoStatus_idOrgao`, `ultimoStatus_siglaOrgao`, `ultimoStatus_uriOrgao`, `ultimoStatus_regime`, `ultimoStatus_descricaoTramitacao`, `ultimoStatus_idTipoTramitacao`, `ultimoStatus_descricaoSituacao`, `ultimoStatus_idSituacao`, `ultimoStatus_despacho`, `ultimoStatus_apreciacao`, `ultimoStatus_url`

## proposicoesTemas

- Linhas: 278.819
  - 2003: 8.492
  - 2004: 5.115
  - 2005: 7.250
  - 2007: 11.377
  - 2008: 9.161
  - 2010: 5.235
  - 2011: 9.735
  - 2012: 5.496
  - 2013: 7.770
  - 2014: 4.093
  - 2015: 10.841
  - 2016: 7.055
  - 2017: 8.604
  - 2018: 5.126
  - 2019: 15.534
  - 2020: 19.186
  - 2021: 15.456
  - 2022: 10.109
  - 2023: 22.917
  - 2024: 23.732
  - 2025: 40.909
  - 2026: 25.626
- Colunas (6): `uriProposicao`, `siglaTipo`, `numero`, `codTema`, `tema`, `relevancia`

## proposicoesAutores

- Linhas: 1.660.453
  - 2003: 220.184
  - 2004: 75.914
  - 2005: 74.784
  - 2007: 53.586
  - 2008: 128.555
  - 2010: 21.888
  - 2011: 39.834
  - 2012: 27.941
  - 2013: 42.873
  - 2014: 21.269
  - 2015: 55.888
  - 2016: 34.089
  - 2017: 62.539
  - 2018: 21.779
  - 2019: 127.940
  - 2020: 55.763
  - 2021: 76.396
  - 2022: 43.786
  - 2023: 164.953
  - 2024: 97.124
  - 2025: 154.579
  - 2026: 58.789
- Colunas (12): `idProposicao`, `uriProposicao`, `idDeputadoAutor`, `uriAutor`, `codTipoAutor`, `tipoAutor`, `nomeAutor`, `siglaPartidoAutor`, `uriPartidoAutor`, `siglaUFAutor`, `ordemAssinatura`, `proponente`

## Cobertura das proposições com votação nominal

- 2023: com tema 182 de 229 (79,5%); com cadastro 229 de 229 (100,0%)
- 2024: com tema 186 de 235 (79,1%); com cadastro 235 de 235 (100,0%)
- 2025: com tema 216 de 241 (89,6%); com cadastro 241 de 241 (100,0%)
- 2026: com tema 99 de 112 (88,4%); com cadastro 112 de 112 (100,0%)
- Total: com tema 683 de 817 (83,6%); com cadastro 817 de 817 (100,0%)
