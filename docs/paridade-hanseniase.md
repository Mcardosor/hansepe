# Divergências — painel de origem e Ministério da Saúde

Toda diferença numérica entre este painel, o Shiny de origem
(`PE_HANSE_06_01`) e as definições do Ministério da Saúde deve estar
registrada aqui, com a decisão e o motivo. **O que não estiver listado e
divergir é bug.**

`tests/paridade/test_referencia_origem.py` compara a cada execução contra os
valores lidos da tela deles, congelados em `referencia_origem.json` em
18/set/2026 — antes de qualquer fórmula ser escrita.

**Estado em 18/set/2026:** os sete cards de PE 2025, as cinco variações
contra 2024, quatro popups municipais e o drill-down da macro Vale do
S. Francisco/Araripe batem no dígito. As divergências abaixo são todas
**decididas**, nenhuma em aberto com a equipe parceira; a §1 é decisão a
confirmar com o chefe.

> Paridade mede concordância, não correção. Os dois painéis leem a mesma
> extração, então concordar entre si não prova nada contra a fonte oficial —
> é o caso da §1, em que os dois divergem juntos do MS.

---

## 0. Onde batemos

| Item | PE 2025 | Origem |
|---|---:|---:|
| Taxa de detecção | 24,64 | 24,64 |
| Taxa de detecção 0–14 | 4,02 | 4,02 |
| Casos novos | 2.356 | 2.356 |
| Casos 0–14 | 78 | 78 |
| Curas | 135 | 135 |
| Multibacilar | 82,9% | 82,9% |
| Grau II | 10,0% | 10,0% |
| Macro Vale S.Francisco/Araripe — detecção · casos · curas | 62,68 · 672 · 29 | 62,68 · 672 · 29 |
| Abreu e Lima — casos · taxa · curas · população | 18 · 17,3 · 2 · 104.248 | idem |

---

## 1. "Casos novos" são todas as entradas no registro — reproduzido, e divergente do MS

`incidence.casos_total` para a hanseníase conta **todas as entradas** no
registro ativo do ano: caso novo, recidiva, transferências e outros
reingressos. Para a tuberculose a mesma coluna já vem filtrada por tipo de
entrada; para a hanseníase não. Em PE 2025:

| | Todas as entradas | `MODOENTR = 1` (caso novo) | `leprosy` (painel da família, casos novos) |
|---|---:|---:|---:|
| Casos | 2.356 | 1.590 | — (2024: 1.704) |
| Detecção /100 mil | 24,64 → *muito alta* | 16,6 → *alta* | 2024: 17,9 → *alta* |

O Boletim Epidemiológico de Hanseníase define os três indicadores de
endemicidade (detecção geral, em < 15 anos e grau II) sobre **casos novos**.

**Decisão (18/set/2026):** reproduzir o painel de origem — `casos_total` —
para a paridade fechar e o painel substituir o deles sem trocar os números
que a equipe já circula. A definição do MS fica documentada aqui e no
tooltip do card. Trocar é uma linha em `kpis.calcular` (numerador
`MODOENTR = 1`, de `sinan_landing`), **mas só para a detecção geral**: as
taxas 0–14 e o grau II entre casos novos exigem cruzar variáveis, o que os
agregados não permitem — dependem do microdado (`pedido-microdado.md`).

**A confirmar com o chefe.** Se a decisão mudar, a §0 deixa de bater nos
três primeiros cards, de propósito.

## 2. Denominador do grau II — reproduzido

Três denominadores possíveis para 218 casos com grau 2 em PE 2025:

| Denominador | Valor |
|---|---:|
| Todos os casos (2.356) | 9,3% |
| Avaliação preenchida, incluindo "não avaliado" (2.171) — **origem** | **10,0%** |
| Só avaliados: grau 0, 1 e 2 (1.810) — **MS** | 12,0% |

Reproduzimos a origem. O denominador do MS está no tooltip do card.

## 3. Cura sem coorte — reproduzido, com aviso

O card "Curas" da origem é `casos_cura` do mesmo ano de diagnóstico
(`TPALTA_N = 1`), sem coorte. Em 2025 dá 135 (↓ 953): não é queda, é
tratamento em curso. Reproduzimos e o tooltip explica. O indicador de cura
do MS (coorte PB do ano anterior, MB de dois anos antes) entra com o
microdado.

## 4. Classificação do mapa — quintis reproduzidos, mais duas

A origem reparte os 185 municípios em cinco classes de 37 (quintis) e a
régua muda a cada ano. É o padrão aqui também, e o controle "Cores" oferece
quebras naturais e a escala fixa de endemicidade do MS, que a origem não
tem.

## 5. Canal endêmico — cinco anos em vez de três

A origem usa os três anos anteriores como referência (Q1/Q3 de 2022–2024
para 2025). Aqui são **cinco** (2020–2024), a decisão §6 do RecifeTB: com
três, um único ano atípico — 2020 — domina a faixa. As linhas de cada ano
de referência continuam no gráfico, então quem quiser ver os três de lá vê.

## 6. Escopo atravessa tudo — corrigido

Na origem, entrar numa macrorregião muda os cards de detecção e casos e
deixa 0–14, MB, grau II, a evolução temporal e os tópicos em PE. Aqui os
sete cards e todos os gráficos seguem o recorte, somando os municípios da
região e recalculando as taxas. Não há número da origem para comparar
nesses painéis; o teste de invariante (soma dos 185 = PE) é a garantia.

## 7. Séries mensais: UF × soma dos municípios — 7 casos

`_cache_ts` no nível UF soma 2.475 casos em PE 2024; no nível município,
2.468 — igual à tabela anual. A diferença (7 casos) é a mesma classe de
divergência do painel nacional (residência × notificação na UF). Como o
painel só lê o nível UF quando não há recorte, e o nível MUN nos demais, a
epicurva de PE inteiro pode diferir em poucos casos da soma das macros.
Registrado; irrelevante para os cards, que saem de `incidence`.

## 8. O que a origem mostra e este painel não — de propósito

- Sete tópicos de interesse (`NDUPLIC_N`, `IN_VINCULA`, `UFATUAL`,
  `UFRESAT`, `DTMUDESQ`, `CLASSATUAL`, `ESQ_ATU_N`, `AVAL_ATU_N`): controle
  do sistema, 100% num valor, ou situação atual pior preenchida que a do
  diagnóstico. Ver `inventario-painel-origem.md` §5.
- "Óbitos" no popup do mapa: `casos_obitos` do SINAN, quase sempre zero.
- "Dados parciais" no último ano: aqui só quando faltar mês.
