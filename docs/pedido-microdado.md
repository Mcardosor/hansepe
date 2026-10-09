# Solicitação de microdado — hanseníase, residentes em Pernambuco

**Painel de Monitoramento da Hanseníase — Pernambuco**
Documento para envio à equipe responsável pela extração.

| | |
|---|---|
| Destinatário | equipe parceira responsável pela extração do SINAN |
| Versão | 1.2 |
| Última revisão | outubro de 2026 |
| Responsável técnico | Matheus Cardoso |

---

Estamos desenvolvendo o painel de hanseníase de Pernambuco, que acompanha os
painéis de tuberculose do estado e de Recife. Os agregados que vocês já
produzem cobrem os indicadores principais, e é com eles que a versão atual
está no ar: detecção geral e em menores de 15 anos, grau II, cura, contatos
examinados e abandono.

Quatro necessidades, porém, não se resolvem com dados agregados. Esta
solicitação trata delas.

## O que não conseguimos calcular hoje

**Cruzamento entre modo de entrada e os demais indicadores.** Os
coeficientes de detecção já seguem a definição do Ministério, contando
apenas casos novos. Os indicadores de 0 a 14 anos, grau II, curas e a série
mensal continuam calculados sobre todas as entradas no registro, porque as
tabelas correspondentes não trazem o modo de entrada. O efeito é visível: a
soma dos meses de 2024 fica cerca de 40% acima do total de casos novos do
ano.

**População de menores de 15 anos** por município e ano. Sem ela, a taxa de
detecção nessa faixa é calculada com denominador aproximado.

**Proporção de casos curados com grau de incapacidade avaliado.** O campo de
avaliação na situação atual existe nos agregados, mas não é possível saber
quais dos casos avaliados estão entre os curados. Calculado sobre o total de
curas, o indicador chega a 163% em 2025, o que evidencia que o campo é
preenchido também para abandonos e transferências.

**Cruzamentos entre variáveis** em geral — desfecho por raça/cor, desfecho
por classificação operacional, pirâmide etária por município.

O microdado individual resolve as quatro de uma vez.

## O que solicitamos

**Recorte.** Notificações de hanseníase do SINAN com município de residência
em Pernambuco, de 2010 ao ano mais recente disponível, com todos os modos de
entrada. O filtro de caso novo é aplicado do nosso lado.

**Colunas.** Apenas as listadas abaixo. Nenhum identificador: sem nome, nome
da mãe, CNS, endereço, telefone, coordenadas ou unidade notificadora.

| Grupo | Colunas |
|---|---|
| Tempo | `NU_ANO`, `DT_NOTIFIC`, `DT_DIAG`, `DT_ALTA_N` ou a data de saída do registro ativo que existir |
| Lugar | `ID_MUNICIP` de residência, indicando se tem 6 ou 7 dígitos, e `CS_ZONA` |
| Pessoa | `CS_SEXO`, `NU_IDADE_N`, `CS_RACA`, `CS_ESCOL_N`, `CS_GESTANT` |
| Clínico | `CLASSOPERA`, `CLASSATUAL`, `FORMACLINI`, `NU_LESOES`, `NERVOSAFET`, `AVALIA_N`, `AVAL_ATU_N`, `BACILOSCOP`, `EPIS_RACIO` |
| Programa | `MODOENTR`, `MODODETECT`, `ESQ_INI_N`, `ESQ_ATU_N`, `DOSE_RECEB`, `CONTREG`, `CONTEXAM`, `TPALTA_N`, `UFRESAT`, `IN_VINCULA`, `NDUPLIC_N` |

**Formato.** Parquet, ou CSV com separador ponto e vírgula e codificação
declarada. Preferimos UTF-8; a extração de Recife veio em Latin-1. Arquivo
único.

**Separadamente**, a tabela de população de menores de 15 anos por município
e ano, que não depende do microdado e pode vir antes.

## Quatro dúvidas sobre os campos

1. **O ano das tabelas que recebemos é o de notificação ou o de
   diagnóstico?** É a dúvida mais importante desta lista. Ela não muda só o
   rótulo de um eixo: muda a leitura de todos os números anuais do painel,
   inclusive os que já conferimos contra o boletim. Procuramos na
   documentação recebida e não está declarado; consultamos a equipe de
   vigilância, que também não soube dizer. Enquanto não tivermos a resposta,
   o eixo do tempo fica sem nome — preferimos isso a escrever o nome errado.

2. O campo `TPALTA_N` e as datas de alta refletem o registro no momento da
   extração, ou já consideram o fechamento de coorte do Ministério, com
   paucibacilares do ano seguinte e multibacilares de dois anos depois?

3. `CONTREG` e `CONTEXAM` são contagens de contatos por caso? Nos agregados
   chegaram como valores 0, 1, 2 e assim por diante, sem rótulo.

4. `FORMACLINI` veio sem rótulo no dicionário. Os códigos correspondem a
   1 indeterminada, 2 tuberculoide, 3 dimorfa, 4 virchowiana e 5 não
   classificada?

## Tratamento dos dados do nosso lado

O microdado recebe o mesmo tratamento aplicado à extração de Recife. Fica
fora do controle de versão e da imagem de publicação, e um script descarta
qualquer coluna fora da lista acima antes de gerar o arquivo que o painel
efetivamente lê. O painel publicado continua operando apenas sobre dados
agregados.
