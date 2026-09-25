# Divergências — painel de origem e Ministério da Saúde

Toda diferença numérica entre este painel, o Shiny de origem
(`PE_HANSE_06_01`) e as definições do Ministério da Saúde deve estar
registrada aqui, com a decisão e o motivo. **O que não estiver listado e
divergir é bug.**

`tests/paridade/test_referencia_origem.py` compara a cada execução contra os
valores lidos da tela deles, congelados em `referencia_origem.json` em
18/set/2026 — antes de qualquer fórmula ser escrita.

**Estado em 25/set/2026:** cinco dos sete cards de PE 2025 (0–14, casos
0–14, curas, MB, grau II), as variações deles, curas e população dos popups
municipais e o drill-down da macro batem no dígito. **Casos novos e taxa de
detecção divergem de propósito** desde 20/set/2026: seguem a definição do
Ministério (§1), e `tests/paridade` prende a distância. As demais
divergências estão decididas; nenhuma em aberto com a equipe parceira.

> Paridade mede concordância, não correção. Os dois painéis leem a mesma
> extração, então concordar entre si não prova nada contra a fonte oficial —
> é o caso da §1, em que os dois divergem juntos do MS.

---

## 0. Onde batemos — e onde não, de propósito

| Item | PE 2025 | Origem | |
|---|---:|---:|---|
| **Casos novos** | **1.590** | 2.356 | §1 — definição do MS |
| **Taxa de detecção** | **16,63** | 24,64 | §1 |
| Taxa de detecção 0–14 | 4,02 | 4,02 | |
| Casos 0–14 | 78 | 78 | |
| Curas | 135 | 135 | |
| Multibacilar | 82,9% | 82,9% | |
| Grau II | 10,0% | 10,0% | |
| Macro Vale S.Francisco/Araripe — casos · detecção · curas | 413 · 38,52 · 29 | 672 · 62,68 · 29 | §1 nos dois primeiros |
| Abreu e Lima — casos · taxa · curas · população | 8 · 7,7 · 2 · 104.248 | 18 · 17,3 · 2 · 104.248 | §1 nos dois primeiros |

---

## 1. Casos novos pela definição do MS — divergente da origem, decidido

`incidence.casos_total` para a hanseníase conta **todas as entradas** no
registro ativo do ano: caso novo, recidiva, transferências e outros
reingressos. Para a tuberculose a mesma coluna já vem filtrada por tipo de
entrada; para a hanseníase não — e o painel de origem exibe assim. O
Boletim Epidemiológico de Hanseníase define os indicadores de endemicidade
sobre **casos novos** (`MODOENTR = 1`). Em PE 2025:

| | Todas as entradas (origem) | `MODOENTR = 1` (**este painel**) | `leprosy` (painel da família) |
|---|---:|---:|---:|
| Casos | 2.356 | **1.590** | 2024: 1.704 |
| Detecção /100 mil | 24,64 → *muito alta* | **16,63 → alta** | 2024: 17,9 → *alta* |
| Municípios hiperendêmicos (≥ 40) | 11 | **7** | |

**Decisão (20/set/2026): aplicar a definição do MS.** Vale para os cards
de casos novos e detecção, o mapa, o ranking, o tooltip, a agregação por
macro e região de saúde e a série anual — todos leem `MODOENTR = 1` do
`sinan_landing` (numerador) e a população do `incidence` (denominador); a
soma dos 185 municípios continua fechando com o estado (teste em
`tests/paridade`).

**O que continua sobre todas as entradas, por falta de cruzamento na
extração:** casos e taxa em **0–14**, **grau II**, **curas** (o
`incidence_0_14` e os `casos_grau_*` não separam modo de entrada) e a
**série mensal** — canal endêmico e epicurva vêm do `_cache_ts`, que
também não tem modo de entrada; por isso a soma dos meses de 2024 (2.475)
fica ~40% acima dos casos novos do ano (1.761), e o gráfico avisa. Tudo
isso passa a caso novo com o microdado (`pedido-microdado.md`).

A distância para a origem é conhecida (2.356 − 1.590 = 766) e o teste
`test_a_divergencia_com_a_origem_continua_registrada` falha se ela sumir
sem esta seção mudar.

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

## 4. Classificação do mapa — abre em endemicidade; quintis disponíveis

A origem reparte os 185 municípios em cinco classes de 37 (quintis) e a
régua muda a cada ano; ao lado da legenda, uma tabela "regiões por classe"
repete as faixas com o N — sempre 37. Aqui o mapa abre na **escala de
endemicidade do MS** (baixa < 2 … hiperendêmica ≥ 40), comparável entre
anos, e o N entra na própria legenda, onde passa a informar ("7
hiperendêmicos" em 2025, pela definição do MS de caso novo). Quintis e quebras naturais continuam no controle
"Cores". Decisão de 18/set/2026, depois de o usuário estranhar os 37.

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

## 8. Indicadores de qualidade: aproximação de coorte

Cura, abandono, contatos examinados e GIF avaliado entraram em 25/set/2026,
pedidos na reunião do dia 22. O boletim os calcula por **coorte** (PB
diagnosticados no ano anterior, MB dois anos antes); com os agregados só dá
para fazer por **ano de diagnóstico**. Medido em PE 2024:

| Indicador | Nosso | Boletim |
|---|---:|---:|
| Proporção de cura | 67,1% | 65,0% |
| Proporção de abandono | 12,2% | 13,5% |
| Contatos examinados | 81,6% | 77,3% |
| GIF avaliado no diagnóstico | 82,7% | 83,6% |

No estado a aproximação segura de 1 a 4 pontos, e a classificação do
boletim não muda. **Por município ela se solta**: em Abreu e Lima 2024 dá
72,7% de cura contra 58,3% publicados, e 93,7% de contatos contra 72,4%.
Fecha com o microdado (`pedido-microdado.md`).

O quinto indicador da Tabela 2 — **% GIF na cura** — ficou de fora: o
denominador é a coorte de curados, que não existe nos agregados (dá 32,6%
contra 46,9% publicados, distância que não é aproximação, é outra conta).

**Coorte aberta.** Abaixo de 50% de saídas registradas os três indicadores
de acompanhamento são suprimidos — ver `kpis.COBERTURA_MINIMA_COORTE`. Em
2025 seriam 30,4% de cura com 19% de cobertura.

## 9. Paridade com o boletim — a fonte externa

`tests/paridade/test_referencia_boletim.py` compara contra o Boletim
Epidemiológico de Hanseníase 2025 (SES-PE), congelado em
`referencia_boletim.json`: os sete quadros de parâmetros, a série de PE
2015–2024 e os indicadores de qualidade de 2023 e 2024.

A tolerância é **assimétrica**: o boletim foi tabulado em 16/04/2025 e nossa
extração é posterior, então ficar acima é o comportamento correto — medido,
de +0,4% a +4,4% na detecção geral. Ficar abaixo não tem causa benigna.

Foi este harness que confirmou a §1: a detecção geral acompanha o boletim
dentro da defasagem, enquanto a detecção em < 15 anos fica 8% a 28% acima
porque conta todas as entradas.

### Município a município — a Tabela 2

`scripts/extrair_tabela_boletim.py` lê os 185 municípios e as 12 Regionais
de Saúde da Tabela 2 (nove indicadores de 2024) e grava
`referencia_boletim_municipios.json`. Medido em 25/set/2026:

| | |
|---|---|
| Municípios com caso em alguma das fontes | 136 (49 zerados nas duas) |
| Batem no número exato | **95** |
| Mediana da diferença | **0** caso |
| Desvio mediano da taxa | **0,13%** |
| Extremos | −2 (Condado, Custódia) a +8 (Jaboatão) |

Ficar abaixo em um ou dois casos acontece: entre uma extração e outra o
SINAN corrige o município de residência, e o caso **muda de lugar** em vez
de aparecer. No estado isso se cancela; por município, não. O teste tolera
até três para baixo e sinaliza qualquer coisa além.

A mesma tabela valida o `recortes.py`: as 12 GERES contra as nossas regiões
de saúde. Três batem exatamente (VI/Arcoverde 100, XI/Serra Talhada 71,
V/Garanhuns 51). A numeração oficial — I GERES é Recife, VIII é Petrolina —
está em `GERES_PARA_REGIAO`, no teste.

O boletim escreve **"Garanhus"** na Tabela 2; é erro de digitação dele, e o
extrator tem o apelido registrado.

## 10. O que a origem mostra e este painel não — de propósito

- Sete tópicos de interesse (`NDUPLIC_N`, `IN_VINCULA`, `UFATUAL`,
  `UFRESAT`, `DTMUDESQ`, `CLASSATUAL`, `ESQ_ATU_N`, `AVAL_ATU_N`): controle
  do sistema, 100% num valor, ou situação atual pior preenchida que a do
  diagnóstico. Ver `inventario-painel-origem.md` §5.
- "Óbitos" no popup do mapa: `casos_obitos` do SINAN, quase sempre zero.
- "Dados parciais" no último ano: aqui só quando faltar mês.
