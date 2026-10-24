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

- Linhas: 62.437
  - 2023: 62.437
- Colunas (30): `id`, `uri`, `siglaTipo`, `numero`, `codTipo`, `descricaoTipo`, `ementa`, `ementaDetalhada`, `keywords`, `dataApresentacao`, `uriOrgaoNumerador`, `uriPropAnterior`, `uriPropPrincipal`, `uriPropPosterior`, `urlInteiroTeor`, `urnFinal`, `ultimoStatus_dataHora`, `ultimoStatus_sequencia`, `ultimoStatus_uriRelator`, `ultimoStatus_idOrgao`, `ultimoStatus_siglaOrgao`, `ultimoStatus_uriOrgao`, `ultimoStatus_regime`, `ultimoStatus_descricaoTramitacao`, `ultimoStatus_idTipoTramitacao`, `ultimoStatus_descricaoSituacao`, `ultimoStatus_idSituacao`, `ultimoStatus_despacho`, `ultimoStatus_apreciacao`, `ultimoStatus_url`

## proposicoesTemas

- Linhas: 22.917
  - 2023: 22.917
- Colunas (6): `uriProposicao`, `siglaTipo`, `numero`, `codTema`, `tema`, `relevancia`

## proposicoesAutores

- Linhas: 164.953
  - 2023: 164.953
- Colunas (12): `idProposicao`, `uriProposicao`, `idDeputadoAutor`, `uriAutor`, `codTipoAutor`, `tipoAutor`, `nomeAutor`, `siglaPartidoAutor`, `uriPartidoAutor`, `siglaUFAutor`, `ordemAssinatura`, `proponente`
