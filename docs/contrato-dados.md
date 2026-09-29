# Contrato de dados

> **Escopo:** este arquivo veio do painel nacional, que serve cinco doenças.
> Em 29/set/2026 foi podado para o que **este** painel lê — saíram os datasets
> de tuberculose e as armadilhas de `SITUA_ENCE`, campo que a ficha de
> hanseníase não tem e que o código deixou de consultar. A numeração das
> armadilhas **não** foi refeita: o código cita algumas pelo número, e
> renumerar quebraria essas referências em silêncio. Os buracos na sequência
> são o registro do que saiu.

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

### 15. `geo_id = '000000'` existe e tem dado

É o balde de município ignorado, e traz encerramentos de verdade. Um teste que
usa `000000` esperando recorte vazio passa por engano — use um código que não
exista, como `999999`.

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
