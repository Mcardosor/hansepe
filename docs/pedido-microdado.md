# Pedido à equipe parceira — microdado de hanseníase, residência em PE

Redigido em 17/set/2026. Pronto para mandar; falta só decidir o canal (o
mesmo por onde veio o `SINAN_RECIFE_TB.csv`).

---

Estamos montando o painel de hanseníase de Pernambuco, irmão do de
tuberculose (`painel.cenarios.unb.br/cenarios/sinan/`) e do de Recife. Os
agregados que vocês já geram (`incidence`, `incidence_0_14`, `sinan_landing`
com `HANS`) cobrem os indicadores principais — detecção geral e em menores de
15, grau 2, cura, contatos e abandono — e é com eles que a primeira versão
vai ao ar.

O que não conseguimos fazer com agregados são os **cruzamentos** (desfecho ×
raça/cor, desfecho × classificação operacional, pirâmide por município) e a
**série mensal** de detecção, que é a base do canal endêmico. Para isso
precisamos do microdado, no mesmo molde do que vocês mandaram para o Recife:

**Recorte:** notificações de hanseníase do SINAN com **município de
residência em Pernambuco**, 2010 até o mais recente disponível — todos os
modos de entrada (o painel filtra caso novo pelo `MODOENTR`).

**Colunas** (só estas; **nenhum identificador** — sem nome, nome da mãe, CNS,
endereço, telefone, coordenadas, unidade notificadora):

| Grupo | Colunas |
|---|---|
| Tempo | `NU_ANO`, `DT_NOTIFIC`, `DT_DIAG`, `DT_ALTA_N` (ou a data de saída do registro ativo que existir) |
| Lugar (residência) | `ID_MUNICIP` de residência (6 ou 7 dígitos, dizer qual), `CS_ZONA` |
| Pessoa | `CS_SEXO`, `NU_IDADE_N`, `CS_RACA`, `CS_ESCOL_N`, `CS_GESTANT` |
| Clínico | `CLASSOPERA`, `CLASSATUAL`, `FORMACLINI`, `NU_LESOES`, `NERVOSAFET`, `AVALIA_N`, `AVAL_ATU_N`, `BACILOSCOP`, `EPIS_RACIO` |
| Programa | `MODOENTR`, `MODODETECT`, `ESQ_INI_N`, `ESQ_ATU_N`, `DOSE_RECEB`, `CONTREG`, `CONTEXAM`, `TPALTA_N`, `UFRESAT`, `IN_VINCULA`, `NDUPLIC_N` |

**Formato:** parquet ou CSV com separador `;` e codificação declarada (o de
Recife veio em Latin-1; UTF-8 é melhor). Um arquivo só.

**Três perguntas** que ajudam a não errar no nosso lado:

1. O `TPALTA_N` e as datas de alta são os do registro na extração ou já
   fecham a coorte do MS (PB no ano seguinte, MB dois anos depois)?
2. `CONTREG` e `CONTEXAM` são contagens de contatos por caso, certo? No
   `sinan_landing` vieram como valores `0`, `1`, `2`… sem rótulo.
3. `FORMACLINI` veio sem rótulo no `sinan_dict` — os códigos são
   1 Indeterminada, 2 Tuberculóide, 3 Dimorfa, 4 Virchowiana, 5 Não
   classificada?

Do nosso lado, o microdado passa pelo mesmo tratamento do de Recife: fica
fora do git e da imagem, e um script descarta qualquer coluna fora da lista
antes de gravar o parquet que o painel lê.
