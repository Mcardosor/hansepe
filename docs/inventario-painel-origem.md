# Inventário do painel de origem — Hanseníase de PE (Shiny)

Levantado em 18/set/2026 em <https://cenarios.unb.br/pernambuco-hans/>, que embute
`https://cenariostb.unb.br/PE_HANSE_06_01/` (Shiny, Leaflet + ECharts). É o
painel que o `hansepe` reconstrói em Python, tela a tela — o equivalente do
`inventario-funcionalidades.md` do sinan. Os números foram conferidos contra
`../sinan/data/parquet/dashboard`: **o painel lê a mesma extração**.

## 1. Faixa de KPIs (5 cards clicáveis — o clicado vira a métrica do mapa)

| Card | PE 2025 | Fórmula observada | Dataset |
|---|---:|---|---|
| Taxa de detecção | 24,64 | `casos_total / pop_total × 1e5` | `incidence` |
| Taxa de detecção (0 a 14 anos) | 4,02 | `casos_0_14_total / pop_0_14_total × 1e5` | `incidence_0_14` |
| Casos novos | 2.356 | **`casos_total`** — todas as entradas (`MODOENTR=1` daria 1.590) | `incidence` |
| Casos novos (0 a 14 anos) | 78 | `casos_0_14_total` | `incidence_0_14` |
| Curas entre casos novos | 135 (↓ −953) | `casos_cura` = `TPALTA_N=1` do mesmo ano de diagnóstico, sem coorte | `incidence` |

Cada card traz a variação absoluta contra o ano anterior (seta verde/vermelha;
"≈ sem variação" quando zero).

Dois cards de proporção, não clicáveis:

| Card | PE 2025 | Fórmula observada |
|---|---:|---|
| Proporção multibacilar (MB) | 82,9% | `CLASSOPERA=2 / (1+2)` = 1.953/2.355 |
| Proporção grau II (diagnóstico) | 10,0% | `casos_grau_II / (grau_0 + grau_I + grau_II + nao_avaliado)` = 218/2.171 — **exclui os 185 sem `AVALIA_N`, inclui "não avaliado"**. Nem sobre o total (9,3%) nem sobre avaliados (12,0%) |

## 2. Controles

- **Ano**: select 2010–2025. O último ano recebe a pill "dados parciais" por
  presunção ("ano mais recente pode estar incompleto") — o `_cache_ts` tem 12
  meses em 2025.
- **Nível do mapa**: rádio Municípios / Microrregião / Macrorregião.
- **Buscar município**: select com autocomplete; centraliza e foca.
- **Métrica** (pill "Métrica: Incidência"): definida pelo card clicado.
- Botão "<" volta um nível.

## 3. Mapa (Leaflet)

- Coroplético do nível escolhido; clique desce macro → micro → município e
  troca o escopo dos cards **de detecção e casos** (ver §7).
- Classificação única: **quintis** (185/5 = 37 por classe), legenda de 5
  degraus + tabela "Regiões por classe" (classe, N).
- Popup: título "Município (PE)", subtítulo "Taxa de detecção (100k): 17,3",
  depois lista com bolinha na cor da métrica: Casos novos · Taxa de
  detecção/100k · Óbitos · Curas · População.

## 4. Painel direito — 3 abas

**Evolução temporal**
- *Meses do ano*: canal endêmico — taxa mensal /100 mil do ano selecionado,
  linhas dos 3 anos anteriores, faixa Q1–Q3 dos 3 anos anteriores. Filtro
  "Grau de incapacidade" (todos / grau zero / I / II / não avaliado / não
  informado) — é a estratificação `avalia_n` do `_cache_ts`.
  Tooltip por mês: as 7 séries com 3 decimais.
- *Todos os anos*: taxa anual 2010–2025 + média móvel dos 3 anos anteriores.
  Tooltip: "Média 3 anos anteriores · Total anual" (o "total" é a taxa).
- Abaixo, **Epicurva por mês**: casos absolutos 2010-01 → 2025-12, com zoom.

**Ranking de municípios**: barras horizontais da métrica ativa, top-N com
barra de rolagem (Petrolina, Itapissuma, Lagoa Grande, Cabo de Santo Agostinho…).
Tooltip: nome e taxa com 3 decimais.

**Pirâmide etária**: casos por faixa de 10 anos e sexo, contagem absoluta.

## 5. Tópicos de interesse (22 gráficos de barras horizontais, %)

Todas as variáveis do `sinan_landing` (`HANS`), uma a uma, sem curadoria e
sem o *n* no tooltip ("Grau zero · Percentual 44,219"):

Grau de incapacidade no diagnóstico · Baciloscopia · Classificação operacional
atual · Classificação operacional no diagnóstico · Nº de contatos examinados ·
Nº de contatos registrados · Escolaridade · Gestante · Raça/Cor · Nº de doses
supervisionadas · **Data de mudança de esquema** (uma barra por data) · Tipo
de reação hansênica (valor `4` sem rótulo, 90%) · Esquema em uso · Esquema
inicial · **Forma clínica inicial (códigos 1–5 sem rótulo)** · Notificação
vinculada (100%) · Modo de detecção · Modo de entrada · Identificador de
duplicidade (100%) · Nº de nervos afetados · Tipo de saída · UF de atendimento
atual. Rodapé: "Não se aplica: 2.892".

Dois gráficos temporais no fim: casos MB × PB por ano com proporção MB (%) em
linha (tooltip quebrado), e casos 0–14 por ano com taxa em linha (rotulada
"(%)", é /100 mil).

## 6. Textos de ajuda (ⓘ)

Genéricos, sobre uso ("clique em uma KPI para mudar a métrica…", "use o nível
para alternar…"). Nenhum diz fórmula ou denominador.

## 7. O que não funciona lá e o hansepe corrige

1. **Escopo pela metade.** Entrando na macro Vale do S. Francisco/Araripe os
   cards de detecção e casos mudam (62,68; 672; 29 curas), mas 0–14, MB,
   grau II, a evolução temporal e os tópicos continuam mostrando PE.
2. **"Casos novos" são todas as entradas** (recidiva, transferência,
   reingresso). Ver `paridade-hanseniase.md`.
3. Sem escala de endemicidade do MS; só quintil, que muda a régua a cada ano.
4. Sem cura de coorte, contatos examinados nem abandono como indicador.
5. Tópicos sem curadoria e sem rótulo; tooltips sem *n*; "Óbitos" no popup
   do mapa (quase sempre 0); 3 decimais em taxa; rótulos errados ("Total
   anual", "(%)").
6. Ano parcial presumido.

## 8. O que vale herdar

Canal endêmico com filtro por grau (o `_cache_ts` já vem estratificado); os
dois temporais do rodapé (MB/PB e 0–14 com taxa); a tabela "regiões por
classe" ao lado da legenda; o popup do mapa com título, taxa em destaque e
componentes na cor da métrica; a variação contra o ano anterior no card.
