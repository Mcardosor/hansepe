# Painel de Hanseníase de Pernambuco — plano de partida

Escrito em 17/set/2026, na véspera de começar. Complementa
`prompt-painel-hanseniase.md` (o *porquê*) com o que já se sabe de fato
(o *com quê*). Tudo que está aqui foi conferido nos arquivos, não suposto.

## 1. A descoberta que muda o plano: os dados já existem

A extração do `paineis/sinan` (`data/parquet/dashboard`, a mesma que serve o
painel de TB em produção) **já traz hanseníase para os 185 municípios de PE,
2010–2025**. Não há extração a esperar. Inventário feito com DuckDB em
17/set/2026:

| Dataset | Código | Cobertura | O que tem para hanseníase |
|---|---|---|---|
| `incidence` | `HANSENIASE` | BR/UF/MUN, 2010–2025, 185 municípios de PE | `casos_total`, `casos_M/F`, `casos_cura`, `casos_grau_0/I/II`, `casos_nao_avaliado`, `casos_ignorado`, `pop_total`, `incid_100k_total`, **`incid_grauII_100k`**, **`prop_grauII`** |
| `incidence_0_14` | `HANSENIASE` | idem | `casos_0_14_total`, `pop_0_14_total`, **`incid_0_14_100k_total`** |
| `sinan_landing` | **`HANS`** | UF e MUN, 2010–2025 (152 municípios de PE com linha em 2024) | 23 variáveis da ficha, com `sexo='TOTAL'`: `AVALIA_N`, `AVAL_ATU_N`, `BACILOSCOP`, `CLASSOPERA`, `CLASSATUAL`, `CONTEXAM`, `CONTREG`, `CS_ESCOL_N`, `CS_GESTANT`, `CS_RACA`, `DOSE_RECEB`, `EPIS_RACIO`, `ESQ_INI_N`, `ESQ_ATU_N`, `FORMACLINI`, `MODODETECT`, `MODOENTR`, `NERVOSAFET`, `TPALTA_N`, `UFATUAL`, `UFRESAT`, `IN_VINCULA`, `NDUPLIC_N` |
| `sinan_dict` | `HANS` | — | rótulos das mesmas variáveis; **`FORMACLINI`, `CONTEXAM` e `CONTREG` vêm sem `valor_lbl`** — rotular no pack |
| `cases_new` | `HANSENIASE` | 16 arquivos | conferir amanhã o que é |
| `piramides` | `HANSENIASE` | — | pirâmide de cura **zerada** (regra 9 do sinan) |

Conferência de sanidade, PE 2024: 2.468 casos, detecção 25,9/100 mil
(**muito alta** na escala do MS), 302 com grau II (12,2%, **alto**), 125 em
< 15 anos (6,3/100 mil, **muito alta**). Os 185 municípios somam os mesmos
2.468 da UF.

O que **não** existe nesta extração:

- **Microdado.** Não há `sinan_hanseniase` nominal como o `SINAN_RECIFE_TB.csv`
  do Recife nem o `pe_tb_sinan.parquet` do tbpe. Consequência: tudo que no
  tbpe é filtro cruzado (desfecho × raça, pirâmide por município, série
  mensal) não dá para reproduzir — `sinan_landing` é contagem por variável,
  uma de cada vez, anual. Se o cliente quiser cruzamentos, a extração nominal
  é o pedido à equipe parceira.
- **Série mensal.** Só `_cache_ts` tem tempo dentro do ano; conferir amanhã
  se cobre `HANSENIASE`. Sem isso não há canal endêmico.
- **Óbito pelo SIM** para hanseníase (`cache_ts_sim_obitos` — conferir).
  Provavelmente irrelevante: em 2024 PE teve 34 óbitos em `TPALTA_N`.

Há ainda `paineis/leprosy`: risco relativo bayesiano por município,
2010–2024, com os três indicadores (geral, < 15, grau II). Não é fonte, mas é
a **referência de classificação de endemicidade** que a família já publicou —
os cortes têm que bater.

## 2. Os KPIs, com fórmula e fonte

Todos por residência, ano de diagnóstico, para o recorte ativo
(PE → macrorregião → região de saúde → município). Confirmar a lista com o
chefe e com o Boletim antes de codar.

| # | KPI | Fórmula | Fonte | Escala fixa |
|---|---|---|---|---|
| 1 | Taxa de detecção geral /100 mil | `casos_total / pop_total × 1e5` | `incidence` | < 2 baixa · 2–10 média · 10–20 alta · 20–40 muito alta · ≥ 40 hiperendêmica |
| 2 | Detecção em < 15 anos /100 mil | `casos_0_14_total / pop_0_14_total × 1e5` | `incidence_0_14` | < 0,5 · 0,5–2,5 · 2,5–5 · 5–10 · ≥ 10 |
| 3 | Grau 2 no diagnóstico (%) | `casos_grau_II / (grau_0 + grau_I + grau_II)` — **avaliados** no denominador, como o MS | `incidence` (ou `AVALIA_N`) | < 5 baixo · 5–10 médio · ≥ 10 alto |
| 4 | Cura (%) | `TPALTA_N=1 / (TPALTA_N ∈ {1, 6, 7})` — cura entre os que saíram por cura, óbito ou abandono; transferências e erro diagnóstico fora | `sinan_landing` | meta MS ≥ 90 bom · 75–89 regular · < 75 precário |
| 5 | Contatos examinados (%) | `Σ(CONTEXAM × n) / Σ(CONTREG × n)` — os valores são **números de contatos por caso**, não códigos | `sinan_landing` | ≥ 90 bom · 75–89 regular · < 75 precário |
| 6 | Abandono (%) | `TPALTA_N=7 / (TPALTA_N ∈ {1, 6, 7})` | `sinan_landing` | sem corte oficial; usar quartis |

Nota sobre a coorte: o MS avalia cura e contatos na **coorte** (PB
diagnosticados no ano anterior, MB dois anos antes). Com dado anual por ano de
diagnóstico dá para aproximar; documentar em `metodologia.md` que é
aproximação e por quê. `tests/paridade` contra o Boletim vai dizer quanto
distancia.

## 3. Quadro comparativo tbpe × RecifeTB — decidido

| Peça | tbpe | RecifeTB | Fica | Por quê |
|---|---|---|---|---|
| Mapa | Plotly, sem clique, 3 níveis por botão | pydeck clicável, natural/quartil/fixa | **RecifeTB** | endemicidade é escala fixa por município; clique navega |
| Navegação | filtros laterais | `Navegacao` em cascata | **RecifeTB**, PE → macro → região → município | `sinan/src/data/recortes.py` já resolve a hierarquia |
| Dados | microdado + precomputação | agregados + microdado anonimizado | **agregados do sinan**, sem microdado | é o que existe (§1); simplifica: zero dado nominal no projeto |
| População | IBGE/SIDRA, pessoas-ano | do agregado | **do agregado** (`pop_total`, `pop_0_14_total`) | vem pronta e é a mesma do Boletim; `baixar_populacao.py` não é mais necessário |
| Recorte | residência | — | **residência** | regra do boletim estadual; confirmar em `sinan/docs/contrato-dados.md` que `incidence` é por residência |
| Óbito | encerramento do SINAN | SIM | **nenhum KPI de óbito** | 34 óbitos/ano; grau II é o indicador de dano na hanseníase |
| Coorte de desfecho (100%) | tem | tem (`contagem_desfechos`) | **RecifeTB** com `TPALTA_N` | mesmo gráfico, outra variável |
| Oportunidade do tratamento | tem | não | **não** | precisa de datas do microdado |
| Comorbidades / heatmap de agravos | tem | não | **não** | ficha de hanseníase não tem agravos; `EPIS_RACIO` (reação hansênica) entra em tópicos |
| Heatmap por macrorregião | tem | não | **entra** (macro × ano de detecção) | macro × ano de detecção é barato com `incidence` e útil |
| Superset embutido | tem | não | **não** | só se o cliente pedir |
| Pirâmide etária | tem (microdado) | tem (agregado `piramides`) | **RecifeTB**, casos; cura está zerada | |
| Série mensal / canal | mensal (microdado) | mensal (`_cache_ts`) | **depende** do `_cache_ts` ter HANS (§1) | |
| Tópicos de interesse | perfil & clínico | `COMPOSICAO` | **RecifeTB**: `CLASSOPERA`, `FORMACLINI`, `AVALIA_N`, `MODOENTR`, `MODODETECT`, `ESQ_INI_N`, `NERVOSAFET`, `EPIS_RACIO`, `CS_RACA`, `CS_ESCOL_N`, sexo | tudo em `sinan_landing` |
| Tema, cartões, tipografia | próprio | `src/theme/` | **RecifeTB** | |
| Testes | 14 | 170 + paridade | **RecifeTB**: paridade contra Boletim de Hanseníase | |
| Deploy | compose na VM, `/cenarios/tbpe/` | imagem para outra equipe | **compose na VM**, `/cenarios/hansepe/` | é PE, hospedagem é nossa; dados montados como volume, como o sinan |

Conclusão: o projeto é **RecifeTB como esqueleto, lendo os parquets do sinan
com os leitores do sinan** (`conexao.caminho`, `config.cod_*`, `recortes`).
Do tbpe ficam as regras de negócio de PE, o texto de limitações e os GeoJSONs
já corrigidos (ordem de enrolamento) — e a lição de detectar ano parcial em
vez de presumir.

## 4. Decisões

Fechadas em 17/set/2026:

1. **Nome:** `hansepe` — pasta `paineis/hansepe`, repositório
   `github.com/Mcardosor/hansepe`, slug `/cenarios/hansepe/`.
2. **KPIs:** os 6 de §2, como estão.
3. **Coorte aproximada** (cura e contatos por ano de diagnóstico) está
   aceita; `metodologia.md` explica a diferença para a coorte do MS.

4. **Microdado:** pedir já. O texto do pedido está em
   `pedido-microdado.md`; enviar pelo mesmo canal do de Recife. Enquanto não
   chega, o painel vai com agregados (fase 1); cruzamentos e canal endêmico
   são fase 2.
5. **Heatmap macrorregião × ano entra; Superset não.**

## 5. Roteiro do dia 1

1. Criar `paineis/hansepe` a partir do RecifeTB: copiar estrutura,
   `.gitignore`, `.dockerignore`, `tests/test_segredos.py`, `src/theme/`,
   `src/mapa.py`, `src/estado.py`, `src/graficos.py`; **não** copiar dados
   nem `scripts/preparar_microdado.py`.
2. Trazer de `sinan`: `src/data/conexao.py`, `config.py`, `escopo.py`,
   `recortes.py`, `geo.py` — e apontar `SINAN_DATA_DIR` para
   `../sinan/data` em dev (volume na VM).
3. Conferir `_cache_ts`, `cases_new` e `cache_ts_sim_obitos` para HANS.
4. `src/doencas/hanseniase.py`: `CORES`, `ROTULOS_CURTOS`, `CORTES_FIXOS`
   (§2), `VARIAVEIS_DESTAQUE`, rótulos de `FORMACLINI` e `CONTEXAM`.
5. `src/data/kpis.py` **da hanseníase** — os 6 de §2 — com teste que
   reproduz PE 2024: 2.468 / 25,9 / 12,2% / 6,3.
6. Mapa municipal de PE com escala fixa de detecção, clicável até
   município, no navegador.
7. `docs/metodologia.md` iniciado junto com o código, não depois.

Ordem das entregas depois disso: cartões → coorte de desfecho → tópicos →
pirâmide → heatmap macro × ano → aparência → compose e nginx → paridade com o
Boletim.
