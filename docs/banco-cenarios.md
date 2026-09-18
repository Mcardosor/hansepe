# Banco `cenarios_ai`

PostgreSQL 14 em `10.20.10.107:5432`, acessível por VPN. Contém o SINAN bruto,
além de SIM, SIH e SINASC.

**Serve para investigação, não para a aplicação.** O dashboard lê dos parquets,
que são rápidos e não dependem de rede. Este banco existe no projeto para
responder perguntas que os agregados não respondem.

## Acesso

Credenciais em `.env`, ignorado pelo git. Copie de `.env.exemplo`.

A conexão em `src/data/banco.py` abre em **somente leitura**, com barreira
dupla: `readonly=True` na sessão e `default_transaction_read_only=on` no
servidor. Qualquer escrita falha na origem, não por disciplina de quem escreve
a query.

## Onde está a tuberculose

| Tabela | Linhas | O quê |
|---|---:|---|
| `public.sinan_tube` | 2.300.791 | SINAN bruto, nomes originais (`sg_uf`, `sg_uf_not`, `situa_ence`) |
| `silver.tuberculose` | 2.300.872 | mesma base com nomes traduzidos e códigos resolvidos |

Prefira a `silver`: ela separa `estado_notificacao` de `estado_residencia` e
traduz `tipo_entrada` e `situacao_encerramento` para texto legível, o que
elimina uma classe inteira de erro de código.

As 81 linhas a mais na `silver` não foram investigadas.

## O que já foi respondido aqui

Ver `docs/perguntas-equipe-r.md` para o detalhe. Em resumo:

- **`incidence` e `cases_new` usam residência; `_cache_ts` e `piramides` usam
  notificação.** Correlação de 0,998 entre o desvio no bruto e o desvio nos
  parquets, nas 27 UFs.
- **A regra do abandono** subestima em cerca de um terço: 10,87% contra 14,70%
  na mesma população.
- **A pirâmide vazia é falha de pipeline**, não ausência de dado: a fonte tem
  54.323 curas e 6.668 óbitos em 2024, com sexo e idade em mais de 99,9%.

## O que não foi resolvido

O filtro exato do pipeline. "Caso novo" em 2024 dá **84.860** casos, contra
**85.932** em `incidence` — faltam 1.072, ou 1,2%. Testado com o ano vindo de
`nu_ano`, de `dt_notific` e de `dt_diag`, e com outras combinações de
`tipo_entrada`; nenhuma fecha.

Isso não afeta as conclusões acima, que dependem da **distribuição** entre UFs
e não do total. Mas impede reproduzir `incidence` do zero, e por isso continua
valendo perguntar à equipe de R qual é o filtro.
