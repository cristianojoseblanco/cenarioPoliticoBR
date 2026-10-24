# Relatório de qualidade — Câmara (staging)

Problemas encontrados: 1

## deputados

- Linhas: 7.889
- Colunas (13): `uri`, `nome`, `idLegislaturaInicial`, `idLegislaturaFinal`, `nomeCivil`, `cpf`, `siglaSexo`, `urlRedeSocial`, `urlWebsite`, `dataNascimento`, `dataFalecimento`, `ufNascimento`, `municipioNascimento`
- Chave (uri) única

## votacoes

- Linhas: 10.851
  - 2023: 10.851
- Colunas (20): `id`, `uri`, `data`, `dataHoraRegistro`, `idOrgao`, `uriOrgao`, `siglaOrgao`, `idEvento`, `uriEvento`, `aprovacao`, `votosSim`, `votosNao`, `votosOutros`, `descricao`, `ultimaAberturaVotacao_dataHoraRegistro`, `ultimaAberturaVotacao_descricao`, `ultimaApresentacaoProposicao_dataHoraRegistro`, `ultimaApresentacaoProposicao_descricao`, `ultimaApresentacaoProposicao_idProposicao`, `ultimaApresentacaoProposicao_uriProposicao`
- Chave (id) única

## votacoesVotos

- Linhas: 128.679
  - 2023: 128.679
- Colunas (12): `idVotacao`, `uriVotacao`, `dataHoraVoto`, `voto`, `deputado_id`, `deputado_uri`, `deputado_nome`, `deputado_siglaPartido`, `deputado_uriPartido`, `deputado_siglaUf`, `deputado_idLegislatura`, `deputado_urlFoto`
- Chave (idVotacao, deputado_id) única
- Valores de `voto`:
  - `Sim`: 74.884 de 128.679 (58,2%)
  - `Não`: 49.937 de 128.679 (38,8%)
  - `Obstrução`: 3.222 de 128.679 (2,5%)
  - `Abstenção`: 359 de 128.679 (0,3%)
  - `Artigo 17`: 277 de 128.679 (0,2%)

## votacoesOrientacoes

- Linhas: 4.359
  - 2023: 4.359
- Colunas (7): `idVotacao`, `uriVotacao`, `siglaOrgao`, `descricao`, `siglaBancada`, `uriBancada`, `orientacao`
- ⚠️ Colunas-chave ausentes: `siglaPartidoBloco` — ajustar `chaves` no config

## votacoesProposicoes

- Linhas: 8.811
  - 2023: 8.811
- Colunas (12): `idVotacao`, `uriVotacao`, `data`, `descricao`, `proposicao_id`, `proposicao_uri`, `proposicao_titulo`, `proposicao_ementa`, `proposicao_codTipo`, `proposicao_siglaTipo`, `proposicao_numero`, `proposicao_ano`
- Chave (idVotacao, proposicao_id) única
