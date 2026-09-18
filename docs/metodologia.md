# Metodologia — o que o painel mostra e como calcula

Referência para quem lê o painel. Cada número da tela vem de uma das regras
abaixo; onde há mais de uma definição possível, a escolhida e o motivo estão
escritos. As divergências com o painel Shiny de origem e com o Ministério da
Saúde estão em [`paridade-hanseniase.md`](paridade-hanseniase.md).

## Fonte e cobertura

- **SINAN** (notificações de hanseníase, residentes em Pernambuco), na
  extração agregada da equipe parceira — a mesma que serve o painel de
  origem e o painel nacional de tuberculose (`../sinan/data`). Anos
  2010–2025, todos com 12 meses; 2026 existe só na série mensal, com dois
  meses, e por isso não é oferecido no seletor.
- **População** por município e ano: a que vem no próprio agregado
  (`pop_total`, `pop_0_14_total`), estimativas do IBGE.
- **Geografia**: 185 municípios, 12 regiões de saúde e 4 macrorregiões de
  saúde, das malhas da SES-PE (`data/support/`).
- **Recorte por residência**, não por notificação — regra do boletim
  estadual. A série mensal (`_cache_ts`) segue o mesmo critério: os totais de
  2024 batem (2.468) entre ela e a tabela anual.

## Os sete indicadores

Todos são do **ano selecionado** e do **território selecionado** (PE, uma
macrorregião, uma região de saúde ou um município). A seta compara com o ano
anterior no mesmo território.

| Indicador | Fórmula | Fonte |
|---|---|---|
| Taxa de detecção /100 mil | casos novos ÷ população × 100.000 | `incidence` |
| Taxa de detecção 0–14 /100 mil | casos de 0 a 14 ÷ população de 0 a 14 × 100.000 | `incidence_0_14` |
| Casos novos | `casos_total` — entradas no registro ativo no ano | `incidence` |
| Casos 0–14 | `casos_0_14_total` | `incidence_0_14` |
| Curas | `casos_cura` — saídas por cura entre os casos do ano | `incidence` |
| Multibacilar (%) | MB ÷ (PB + MB) × 100 | `sinan_landing`, `CLASSOPERA` |
| Grau II (%) | grau 2 ÷ (grau 0 + grau 1 + grau 2 + não avaliado) × 100 | `incidence`, `casos_grau_*` |

Detalhes que mudam o número:

- **"Casos novos" são todas as entradas no registro ativo** — recidivas,
  transferências e outros reingressos inclusive. É assim que a extração
  define `casos_total` para a hanseníase e é assim que o painel de origem
  exibe. Pela definição do Ministério da Saúde (só modo de entrada "caso
  novo", `MODOENTR = 1`) PE teria 1.590 casos e 16,6/100 mil em 2025, em
  vez de 2.356 e 24,64 — uma faixa de endemicidade abaixo. Ver
  `paridade-hanseniase.md` §1.
- **Curas não são coorte.** O tratamento leva 6 (PB) ou 12 (MB) meses, então
  as saídas por cura dos casos diagnosticados no ano corrente são sempre
  poucas (135 em 2025 contra 1.088 em 2024) e sobem nas extrações seguintes.
  O indicador de cura do Ministério é de coorte — PB diagnosticados no ano
  anterior, MB dois anos antes — e precisa do microdado, já pedido
  (`pedido-microdado.md`).
- **Grau II** usa como denominador os casos com o campo de avaliação
  preenchido, incluindo "não avaliado" e excluindo os em branco — o
  denominador do painel de origem (218 de 2.171 = 10,0% em 2025). Sobre o
  total dá 9,3%; sobre os avaliados (grau 0, 1 e 2), que é a regra do MS,
  dá 12,0%.
- **Multibacilar** exclui os sem classificação (1 em 2.356).
- A fração sob os cards de proporção ("1.953 de 2.355") é exatamente a
  conta que produziu o percentual.

## Agregação por macrorregião e região de saúde

Somam-se os componentes municipais e recalcula-se a taxa — nunca a média
das taxas municipais, que pesaria Petrolina igual a um município de dois
mil habitantes. Vale para os cards, o mapa, o ranking, a série anual, o
canal endêmico, a pirâmide, os tópicos e os dois gráficos de rodapé. A soma
dos 185 municípios reproduz o estado exatamente (teste em
`tests/paridade`).

## Mapa

Três classificações de cor, escolhidas no controle "Cores":

- **Quintis** (padrão, a do painel de origem): um quinto dos municípios em
  cada cor — 37 por classe. A régua é recalculada a cada ano.
- **Quebras naturais**: agrupa municípios parecidos (k-means 1-D).
- **Endemicidade**: os parâmetros do Ministério da Saúde para a taxa de
  detecção geral — baixa < 2, média 2–10, alta 10–20, muito alta 20–40,
  hiperendêmica ≥ 40 por 100 mil — e para 0–14 (< 0,5 · 0,5–2,5 · 2,5–5 ·
  5–10 · ≥ 10). É a única régua que deixa dois anos comparáveis.

A tabela "por classe" ao lado da legenda diz quantas unidades caem em cada
cor. Clicar numa macrorregião mostra as regiões de saúde dela; numa região,
os municípios dela; num município, entra nele. "Ver Pernambuco inteiro"
volta ao topo.

## Evolução temporal

- **Canal endêmico**: taxa mensal por 100 mil do ano selecionado contra a
  faixa interquartil (Q1–Q3) dos **cinco anos anteriores** — o painel de
  origem usa três; cinco anos dão uma faixa menos sensível a um ano atípico
  (2020, por exemplo). As linhas finas são cada ano de referência. O filtro
  "Grau de incapacidade" restringe a série a um estrato de `AVALIA_N`, como
  na origem — a série mensal vem estratificada por grau.
- **Todos os anos**: taxa de detecção por ano, 2010–2025.
- **Epicurva**: casos por mês, 2010–2025, contínua.

## Pirâmide etária

Casos por faixa de 10 anos e sexo, em contagem ou por 100 mil habitantes da
faixa (toggle). A pirâmide de curas está zerada na extração (regra 9 do
`CLAUDE.md` do painel nacional) e por isso não é oferecida.

## Tópicos de interesse

Distribuição percentual de cada variável da ficha de hanseníase no recorte.
Dezesseis variáveis curadas em quatro grupos; seis abrem por padrão. Ficam
de fora, de propósito, as de controle do sistema (`NDUPLIC_N`, `IN_VINCULA`),
as de UF (quase 100% PE), a data de mudança de esquema (uma barra por data)
e as de situação atual, redundantes com as do diagnóstico e pior
preenchidas. `FORMACLINI` e `EPIS_RACIO` vêm sem rótulo na extração; os
rótulos estão em `src/doencas/hanseniase.py`. Variáveis numéricas (contatos,
nervos, doses) aparecem em ordem crescente do valor.

Abaixo de **5** registros o percentual não é calculado e só a contagem
aparece.

## Ano incompleto

Detectado pelos meses com notificação na série mensal, não presumido. O
painel de origem marca o último ano como "dados parciais" por ser o último;
2025 tem os 12 meses. Quando 2026 entrar na tabela anual, o aviso aparece
sozinho enquanto faltar mês.
