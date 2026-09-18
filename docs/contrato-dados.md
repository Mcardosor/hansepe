# Contrato de dados

Levantado a partir do projeto original em R, validado com queries DuckDB direto
nos parquets. Todos os números abaixo foram conferidos, não inferidos.

## Origem

`data/parquet/dashboard/` — 888 MB, 2.814 arquivos parquet, particionamento Hive.
Cobertura 2010–2025 (Zika a partir de 2016; 2025 parcial). Nacional: BR, 27 UFs,
5.570 municípios.

Os dados são **nacionais**. Os arquivos de apoio de Pernambuco
(`municipios.csv`, `PE MODIF.*`, `PEMacSAUD MODIF.*`, `PERGSAUDE MODIF.*`)
**não** ficam em `data/parquet/` no projeto original — vivem seis níveis acima
na árvore. São a única fonte de macrorregião e região de saúde, e por isso
esse recorte só existe para PE. Copie para `data/support/`.

## Datasets

| Dataset | Linhas | Partições | Conteúdo |
|---|---|---|---|
| `incidence` | 325 k | `doenca/nivel/ano` | KPIs anuais: casos, óbitos, cura, população, incidência — com corte M/F |
| `incidence_0_14` | 325 k | `doenca/nivel/ano` | Mesmas métricas para a faixa 0–14 anos |
| `_cache_ts` | 1,2 M | `nivel/doenca/ano` | Série mensal: `mes`, `casos`, `casos_obitos`, `casos_cura`, `incid_100k` |
| `piramides` | 13,2 M | `nivel/tipo/doenca/ano` | Pirâmide etária. `tipo` ∈ CASOS, CURA, OBITOS. Campos `valor`, `pop`, `ratio` |
| `sinan_landing` | 28,9 M | `doenca/nivel/ano` | Variáveis SINAN em formato longo: `variavel`, `valor`, `valor_lbl`, `n` |
| `sinan_dict` | 4,5 k | — | Dicionário de código → rótulo |
| `cache_ts_sim_obitos` | 65 k | `nivel/doenca/ano` | Óbitos do SIM, mensais |
| `obitos_sim_faixa` | 57 k | `doenca/nivel/ano` | Óbitos do SIM por sexo e faixa etária |
| `cases_new` | 205 k | `doenca/ano` | Casos novos por `cod_mun6` |
| `indicadores_tb_contatos` | 54 k | — | TB: contatos identificados vs examinados |
| `indicadores_tb_cultura_retratamento` | 27 k | — | TB: cultura em casos de retratamento |
| `_geo_cache/` | 652 MB | `municipios/uf=XX/` | GeoJSON por UF + `municipios_centroids.parquet` |

A ordem das partições **não é uniforme** e a diferença é sutil: `cache_ts_sim_obitos`
é `nivel/doenca/ano`, mas `obitos_sim_faixa`, que também vem do SIM, é
`doenca/nivel/ano`. A ordem de cada dataset está declarada em
`src/data/conexao.py::PARTICOES`.

Globar a raiz de um dataset e filtrar no `WHERE` **não** funciona: os arquivos de
`nivel=BR` não têm a coluna `uf`, e o DuckDB resolve a união pelo esquema do
primeiro arquivo, fazendo colunas sumirem. Por isso a poda é feita pelo caminho.

## Fórmulas dos KPIs

```
incid_100k    = casos / pop * 100000
mortalidade   = obitos / pop * 100000
letalidade    = obitos / casos * 100
taxa_det_0_14 = casos_0_14 / pop_0_14 * 100000
hiv_pos_pct   = positivo / (positivo + negativo) * 100
interrupcao   = SITUA_ENCE = 2 / total de encerramentos * 100
```

`hiv_pos_pct` exclui "não realizado" e "em andamento" do denominador.
Sobre `interrupcao`, ver a armadilha 4.

## Armadilhas

### 1. `casos_obitos` é zero para tuberculose

Em `incidence`, todos os anos de 2010 a 2025. Calcular mortalidade ou letalidade
a partir desse campo dá zero. Os óbitos reais estão em `cache_ts_sim_obitos`
(73.409 óbitos por TB entre 2010 e 2024). São fontes distintas — SINAN vs SIM — e
o merge é responsabilidade da aplicação.

### 2. O código da doença muda entre datasets

| Dataset | Hanseníase | Dengue |
|---|---|---|
| `incidence`, `_cache_ts`, `piramides`, `cases_new` | `HANSENIASE` | `DENG` |
| `sinan_landing` | **`HANS`** | `DENG` |
| `cache_ts_sim_obitos`, `obitos_sim_faixa` | `HANSENIASE` | **`DENGUE`** |

Os dois datasets do SIM ainda trazem `CHIKUNGUNYA`, ausente em todos os outros.
Qualquer join precisa passar pelo mapa canônico em `src/data/`.

### 3. `valor` vem com espaço à esquerda

Em `sinan_landing`, os códigos têm comprimento 2 com espaço à esquerda —
verificado em hexadecimal: `" 1"` = `0x2031`, `" 2"` = `0x2032`. A exceção é
`"10"`, que não tem espaço. Sem `trim()`, todo filtro por código retorna zero
silenciosamente. O `sinan_dict` agrava: registra `" 3"` e `"03"` como entradas
distintas.

### 4. O indicador de interrupção diverge do padrão do MS

O projeto em R conta apenas `SITUA_ENCE = 2` (abandono) e usa **todos** os
encerramentos no denominador, incluindo `5` (transferência), `7` e `8`.

O padrão do Ministério da Saúde soma `2` + `10` (abandono primário) e exclui os
não avaliados do denominador.

Para TB/PE/2024: **11,89% pela regra do R, 14,75% pelo padrão do MS.**

Não é bug de programação, é escolha metodológica — mas precisa ser decidida antes
de fixar as referências de paridade. Ver `tests/paridade/excecoes.md`.

**Atualização de 2026-08-20 — há duas regras do MS, não uma.** O Boletim
Epidemiológico de TB 2026 publica, na Tabela 9, a interrupção como **coluna
irmã** de cura e de "não avaliados", as três sobre a mesma base — o que só
fecha com o denominador completo. Isso não contradiz o parágrafo acima: o
indicador de monitoramento do Ministério exclui os não avaliados, e a tabela
apresenta distribuição de desfechos. São perguntas diferentes.

O código passou a ter as três:

| Regra | Numerador | Denominador | Brasil 2024 |
|---|---|---|---:|
| `paridade` | `{2}` | todos | 14,91% |
| `ms` | `{2,10}` | avaliados | 17,20% |
| `boletim` | `{2,10}` | todos | 15,52% |

A Tabela 9 publica **15,2%**, e é `boletim` que a reproduz. Os 0,32 pontos
restantes são a defasagem de extração: nosso denominador tem 75.404
encerramentos e as porcentagens do MS implicam 77.467, com a diferença
concentrada em "não avaliados" — 9,7% aqui contra 12,6% lá.

**Cuidado com a população.** A Tabela 9 traz três: todos os casos novos de TB
(86.204), só pulmonar (74.885) e pulmonar confirmada em laboratório (56.388),
com interrupção de 15,2%, 15,9% e 16,5%. A nossa é a primeira. Comparar o
nosso número com 16,5% é comparar populações diferentes — engano que já se
cometeu aqui e custou uma investigação.

### 5. `SITUA_ENCE` já vem reagrupado

Os rótulos foram achatados em Favorável / Desfavorável / Não avaliado. Os códigos
`2` (abandono), `3` e `4` (óbitos) e `9` (falência) aparecem todos como
"Desfavorável". Para separar óbito de abandono, use o **código**, nunca o
`valor_lbl`.

### 13. O código de `SITUA_ENCE` tem zero à esquerda em alguns anos

`03` e `04` convivem com `3` e `4` no mesmo dataset — só em 2018 e 2019, 177
registros no Brasil. O `trim` da armadilha 3 **não** resolve isso: ele tira o
espaço, não o zero.

Um filtro por `{"3", "4"}` perde esses óbitos em silêncio, e eles vão parar em
qualquer balde que sirva de resto. Normalize com `lstrip("0")` antes de
comparar, preservando o `"0"` sozinho — que existe e é outra coisa (ver
abaixo). `kpis.grupo_do_desfecho()` é o único lugar que faz isso; use-o.

### 14. Existe um `SITUA_ENCE = 0` (Ignorado), e ele some em 2018

De 2010 a 2017 há um código `0` com volume relevante — 2.711 registros em 2015,
13.359 no total. Em 2018 caem para 47 e depois zeram, o que parece melhora de
preenchimento, não mudança de código.

Ele **não é encerramento favorável**. Tratá-lo como cura inflaria justamente os
anos antigos, que são a base de qualquer comparação temporal. O indicador de
monitoramento do MS já o excluía do denominador (ver armadilha 4); o empilhado
de desfechos o conta em "não avaliados e outros".

### 15. `geo_id = '000000'` existe e tem dado

É o balde de município ignorado, e traz encerramentos de verdade. Um teste que
usa `000000` esperando recorte vazio passa por engano — use um código que não
exista, como `999999`.

### 16. `SITUA_ENCE` perdeu a categoria "não informado" a partir de 2018

**É defeito de extração da equipe parceira, medido contra o SINAN bruto.**

| Ano | Fonte (`silver.tuberculose`) | Nosso parquet (código `0`) |
|---|---:|---:|
| 2015 | 2.716 | 2.711 |
| 2017 | 2.177 | 2.155 |
| **2018** | 2.087 | **47** |
| 2019 a 2023 | 1.921 a 2.706 | **0** |
| **2024** | **4.264** | **0** |

Até 2017 o balde vinha fiel, com a diferença de dezenas que se espera entre
duas extrações. Em 2018 ele colapsa e a partir de 2019 some.

**Efeito:** o denominador de qualquer proporção de encerramento encolhe, então
cura, interrupção e óbito aparecem **maiores** do que são. Medido para a cura
no Brasil, contra a mesma conta feita na fonte:

| | até 2017 | de 2018 em diante |
|---|---|---|
| Nosso desvio | −0,2 a −1,0 ponto | **+0,6 a +1,3 ponto** |

O sinal inverte em 2018 — antes ficávamos abaixo por defasagem de extração,
depois acima por denominador faltando. Na série de cura isso vira um degrau
artificial de cerca de 1,7 ponto entre 2017 e 2018, e faz a queda do período
parecer **menor** do que é: 8,6 pontos no painel contra 9,5 na fonte.

O empilhado de desfechos avisa disso na tela. Não dá para corrigir do nosso
lado — o dado não chega. Ver `docs/perguntas-equipe-r.md`.

### 17. `sinan_landing` tem município de outra UF sob a UF errada

Filtrando `uf = 'PE'` em 2024 vêm **dez municípios de outros estados** — 13
registros de 4.350, com `geo_nome` nulo. Prefixos 22, 25, 27, 29 e 35.

O mapa nunca os mostrou, porque não há geometria para pintar; quem cruza com a
camada geográfica os perde em silêncio, que aqui é o comportamento certo. Quem
**não** cruza os exibe: o ranking mostrava o código cru no lugar do nome, e
como bastava um caso curado para dar 100%, eles ocupavam o topo da cura.

Cruze sempre com `geo.municipios(uf)` antes de listar.

### 6. O código do município tem dois comprimentos

`incidence` e `incidence_0_14` trazem `cod_mun7` (7 dígitos) e `cod_mun6`.
Todos os outros datasets — `sinan_landing`, `_cache_ts`, `piramides`,
`cache_ts_sim_obitos` — chaveiam por `geo_id`, que tem **6**.

Cruzar os dois não levanta erro: devolve vazio. O 7º dígito é verificador e não
é reconstruível por truncamento, então a aplicação usa o código de **6 dígitos**
como chave canônica em todo lugar (`src/data/escopo.py`), deixando o de 7
apenas para exibição.

### 7. A série mensal não fecha com o total anual, por UF

`incidence` (anual) e `_cache_ts` (mensal) atribuem o caso a UFs diferentes.
Nacionalmente as diferenças se cancelam — o pior ano desvia 0,0086% — mas por
UF o desvio é grande e sistemático:

| Recorte | Desvio |
|---|---|
| DF | 7,7% (2024) a **36,8%** (2011) — o pior em todos os 15 anos |
| Demais UFs | 4,5% a 13,9%, concentrado em PI, TO e AP |

**Confirmado na fonte** (05/ago), com o SINAN bruto do banco `cenarios_ai`:

| Datasets | Critério |
|---|---|
| `incidence`, `cases_new` | **UF de residência** |
| `_cache_ts`, `piramides` | **UF de notificação** |

Comparando a contagem por `estado_notificacao` contra `estado_residencia` nas
27 UFs (TB/2024, caso novo) com o desvio observado nos parquets: correlação de
**0,998**, 26 dos 27 sinais concordando.

Consequência prática: no nível UF, o card de KPI e o gráfico de série temporal
mostram totais diferentes para o mesmo recorte. O dashboard em R tem a mesma
inconsistência, porque lê das mesmas duas fontes do mesmo jeito.

Para vigilância, **residência** é o critério usual: é onde a pessoa vive e
onde a política age. Notificação reflete a rede assistencial — por isso o DF,
que atende o Entorno, aparece inflado.

Consequência: a série temporal de `_cache_ts` não pode ser exibida ao lado de
um KPI de `incidence` sem ressalva, porque medem coisas diferentes. Limites
monitorados em `tests/paridade/test_consistencia.py`.

### 8. Dois arquivos de esquemas diferentes no mesmo diretório

`indicadores_tb_contatos` e `indicadores_tb_cultura_retratamento` têm dois
arquivos lado a lado:

| Arquivo | Linhas | Colunas |
|---|---|---|
| `por_ano.parquet` | 17 | agregado nacional por ano |
| `por_ano_geo.parquet` | 53.779 / 27.351 | o mesmo, mais `CO_MUNI_RESIDENCIA` |

Ler o diretório inteiro adota o esquema do primeiro arquivo em ordem alfabética
e **descarta a coluna geográfica do segundo, sem erro**. É a mesma falha do glob
de níveis. Por isso `conexao.caminho()` exige nomear o arquivo nesses dois casos.

A coluna se chama `CO_MUNI_RESIDENCIA` — **residência**, não notificação. É a
melhor pista que temos sobre a armadilha 7. O código `0` marca município
ignorado.

### 9. A pirâmide de tuberculose só tem CASOS

O dataset `piramides` particiona por `tipo` ∈ CASOS, CURA, OBITOS. Para
tuberculose, **CURA e OBITOS somam zero** em todos os 16 anos e nos três
níveis.

E o padrão por doença diz de onde vem o defeito:

| Doença | CASOS | CURA | OBITOS |
|---|:--:|:--:|:--:|
| Dengue | ✓ | ✓ | ✓ |
| Zika | ✓ | ✓ | ✓ |
| **Tuberculose** | ✓ | **zero** | **zero** |
| **Hanseníase** | ✓ | **zero** | **zero** |

A divisão é exatamente entre arboviroses e as duas doenças crônicas — que são
justamente as que registram desfecho em `SITUA_ENCE`, e não em `EVOLUCAO`.
A hipótese é que o pipeline da pirâmide leia um único campo de desfecho, que
existe para dengue e zika e não para as outras duas.

Consequência: a alternância CASOS/CURA/ÓBITOS da pirâmide etária não funciona
na entrega de TB. A pirâmide de óbitos precisa sair de `obitos_sim_faixa`, que
tem o dado (6.354 óbitos no Brasil em 2024). Esse dataset, por sua vez, só
existe no nível MUN — a agregação para UF e BR é feita na query.

### 11. `sinan_landing` tem linha TOTAL além de M, F e I — somar tudo dobra

A coluna `sexo` assume `M`, `F`, `I`, `NA`, `1` **e `TOTAL`**. A linha TOTAL
não é uma categoria: é a soma das demais, já agregada. Conferido em **9,97
milhões** de combinações de nível, geografia, ano e variável — TOTAL bate com
a soma das partes em todas, sem uma exceção.

Somar o dataset inteiro, que é o caminho óbvio, devolve exatamente o dobro.

```sql
-- errado: conta em dobro
SELECT sum(n) FROM sinan_landing WHERE variavel = 'SITUA_ENCE'
-- certo
SELECT sum(n) FROM sinan_landing WHERE variavel = 'SITUA_ENCE' AND sexo = 'TOTAL'
```

**Por que passou despercebido tanto tempo.** Proporção não sente: numerador e
denominador dobram juntos. Nossos KPIs de HIV e de interrupção batiam com o
painel em R **porque os dois estavam dobrados da mesma forma** — em PE 2024,
os dois mostravam "1.034 de 8.700" quando o correto é 517 de 4.350.

O que sentia era a contagem exibida, e o limiar de supressão de base pequena,
que valia metade do que aparentava: um município com 3 registros reais
aparecia com 6 e escapava do corte em 5.

Ver `excecoes.md` — virou divergência intencional, em que estamos certos e o
original não.

### 12. Os indicadores de TB vêm de outra extração, com outro ano

`indicadores_tb_contatos` e `indicadores_tb_cultura_retratamento` não seguem a
cobertura de ano do resto. Comparando o Brasil:

| Ano | Contatos identificados | Casos novos (`incidence`) | Contatos por caso |
|---|---:|---:|---:|
| 2024 | 169.207 | 85.932 | 2,0 |
| 2025 | 161.739 | 1.773 | **91,2** |

Em 2024, com as duas fontes fechadas, a razão é plausível. Em 2025 o arquivo
de indicadores está praticamente completo enquanto `incidence` mal começou —
são extrações de datas diferentes.

Consequência: **não dá para ler estes indicadores ao lado dos KPIs num ano que
ainda não fechou.** A proporção em si continua válida, porque numerador e
denominador saem do mesmo arquivo; o que não vale é a comparação com o resto
da tela. O painel avisa quando o ano está incompleto.

Estes dois arquivos também têm esquema próprio — `por_ano.parquet` nacional e
`por_ano_geo.parquet` com município, e coluna geográfica
`CO_MUNI_RESIDENCIA`. Ver armadilha 8.

## Conciliação entre fontes

Quatro datasets respondem "quantos casos", em três camadas que não conciliam:

| Camada | Fontes | DF/2024 | Divergência |
|---|---|---|---|
| 1 | `incidence`, `cases_new` | 440 | entre si, ≤ 0,098% (3 das 27 UFs) |
| 2 | `_cache_ts` | 474 | +7,7% sobre a camada 1 — ver armadilha 7 |
| 3 | `piramides` | 474 | camada 2 menos registros sem sexo ou faixa (≤ 0,13%) |

Para óbitos, `cache_ts_sim_obitos` (6.376 no BR/2024) e `obitos_sim_faixa`
(6.354) divergem em 0,35%.

**Nenhuma fonte é exatamente igual a outra.** Os limites medidos estão fixados
em `tests/paridade/test_consistencia.py`.

### 10. O código de município no `municipios.csv` tem erro de ponto flutuante

O arquivo de apoio de PE grava o código IBGE como número decimal, e **oito dos
185 municípios** aparecem com erro de representação: São Vicente Férrer é
`2613799.9999999995`, Tabira é `2614599.9999999995`.

Truncar (`int`) dá `261379` em vez de `261380`. Em dois dos oito casos isso
cruza a fronteira dos 6 dígitos, o município deixa de casar com os dados e some
da agregação por região — sem erro nenhum, só um total 10 casos menor que o da
UF. É preciso **arredondar**, não truncar.

Municípios afetados: Afogados da Ingazeira, Flores, Gravatá, Ipojuca,
Itapissuma, Jataúba, São Vicente Férrer e Tabira.
