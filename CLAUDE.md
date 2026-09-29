# CLAUDE.md

Guidance for Claude Code when working in this repository.

Painel de monitoramento da **hanseníase de Pernambuco**, em Streamlit.
Reconstrução em Python do painel Shiny da equipe parceira
(`cenariostb.unb.br/PE_HANSE_06_01`, embutido em
`cenarios.unb.br/pernambuco-hans`), tela a tela — inventário em
`docs/inventario-painel-origem.md`. **A cara reproduz o painel de origem; os números também, exceto casos
novos e taxa de detecção, que seguem a definição do Ministério
(`MODOENTR = 1`) desde 20/set/2026.** Cada divergência está em
`docs/paridade-hanseniase.md` e no tooltip do card.

Herda o core do painel nacional (`../sinan`: leitores, `Escopo`,
navegação PE → macro → região de saúde → município, `recortes.py`) e a
composição de tela do RecifeTB (`mapa.py` com três classificações,
`graficos.py`, `canal.py`, `theme/`). Segue `../sinan/docs/como-fazer.md`.

Documentação, código, commits e comentários em português.

## Comandos

Ambiente: o `.venv` do painel nacional, `../sinan/.venv` (Python 3.13). Os
dados são **do painel**: `data/` tem só as partições `doenca=HANS` e
`doenca=HANSENIASE`, 44 MB, geradas do lago do painel nacional por
`python -m scripts.extrair_dados_hanseniase`. Era uma junção para
`../sinan/data` até 29/set/2026 — 241 MB com dengue, zika e tuberculose que
este painel nunca lê, e uma dependência de o sinan estar na mesma máquina.
É cópia: quando a extração do sinan mudar, rode o script de novo
(`data/PROCEDENCIA.json` guarda origem e data).

```bash
streamlit run app.py                       # aplicação (porta 8501)
pytest                                     # suíte (~380 testes, ~45 s)
pytest tests/paridade -q                   # contra a tela do painel de origem
pytest tests/test_aplicacao.py -q          # ponta a ponta com AppTest
ruff check --select F app.py src tests     # código morto

docker compose up -d --build               # porta 8510, /cenarios/hansepe/
```

Config de dev do navegador: `../.claude/launch.json` tem `hansepe` na 8515.

## Arquitetura

**Fluxo:** `app.py` (página única) → `src/estado.py` (`Navegacao`, topo em
PE) → `src/data/*` → `src/mapa.py` e `src/graficos.py`.

- **`src/data/escopo.py`** — `Escopo(doenca, ano, nivel, uf, mun,
  municipios)`. `municipios` é a lista de uma macrorregião ou região de
  saúde: com ela, `particao_e_filtro_geo` manda os leitores à partição
  `MUN` com `geo_id IN (...)`. É o que faz **tudo** na tela seguir o clique
  no mapa — a origem só muda dois cards.
- **`src/data/kpis.py`** — `calcular` (UF e município) e `calcular_regiao`
  (soma municipal). `proporcoes_hanseniase` dá MB e grau II com numerador e
  denominador, para a fração do card sair da mesma conta.
- **`src/data/leitura.py`** — os leitores do sinan mais os desta doença:
  `serie_mensal` **agrega por mês** (o `_cache_ts` da hanseníase vem
  estratificado por `avalia_n`, 5 linhas/mês) e aceita `grau`;
  `composicao` recebe rótulos do pack e ordem numérica;
  `componentes_de_regiao`, `serie_classificacao_operacional`, `serie_0_14`.
- **`src/doencas/hanseniase.py`** — o pack: 7 KPIs (5 na faixa, 2
  proporções), `CORTES_FIXOS` de endemicidade do MS, `ROTULOS_VALORES`
  (`FORMACLINI`, `EPIS_RACIO` vêm sem rótulo), `VARIAVEIS_NUMERICAS`,
  16 variáveis curadas.
- **`src/mapa.py`** — pydeck; `QUARTIL` são **quintis** (`QUANTIS = 5`),
  como a origem; `alvo_do_clique` lê `cod_mun6`, `regiao`, `uf`.
- **`tests/paridade/`** — `referencia_origem.json` foi lido da tela em
  18/set/2026 antes de existir código.

## Armadilhas

- **Módulos importados não recarregam** no Streamlit: editou `src/`,
  reinicie o servidor.
- **Mapa e gráficos são componentes próprios**, portados do tbpe em
  21/set/2026: `src/mapa_componente.py` + `src/componente_mapa/` (deck.gl
  vivo, voo da câmera e cor interpolada) e `src/grafico_componente.py` +
  `src/componente_grafico/` (ECharts vivo: ranking, tópicos, canal, série
  anual, epicurva, pirâmide e os dois empilhados do rodapé). `key` estável,
  clique com nonce em `session_state`. O `graficos.py` Altair saiu em
  21/set/2026. Detalhes e medição: `../tbpe/docs/mapa-clique.md`.
- **Animação não se mede no navegador embutido do app** (1 frame/s com a
  janela oculta): falso negativo.
- **A paridade externa é o boletim da SES-PE**, não o painel de origem:
  `tests/paridade/referencia_boletim*.json`, com os 185 municípios e as 12
  GERES da Tabela 2. Regerar com `python -m scripts.extrair_tabela_boletim
  <pdf>` (o PDF não entra no repositório; precisa de `pypdf`).
- **Os parâmetros das legendas são os do boletim estadual** e estão presos
  por teste (`tests/paridade/test_referencia_boletim.py`): cortes, nomes das
  classes e bordas. Mexer no `CORTES_FIXOS`/`NOMES_FIXOS` sem o boletim na
  mão quebra a suíte, e é essa a intenção.
- **Coorte aberta suprime cura, abandono e contatos** abaixo de 50% de
  saídas registradas (`kpis.COBERTURA_MINIMA_COORTE`): em 2025 a cura daria
  30,4%, que é ano incompleto, não programa ruim.
- **`casos_total` da hanseníase é toda entrada no registro**, não caso novo.
  Casos novos e detecção saem de `leitura.casos_novos_ms` /
  `casos_novos_por_municipio` (`MODOENTR = 1`); 0–14, grau II, curas e a
  série mensal continuam sobre todas as entradas (paridade §1) — e **não dá
  para aproximar** aplicando a proporção geral de casos novos: na faixa de
  0–14 ela é 5 a 15 pontos maior (paridade §1.1). O dataset `cases_new`, que
  o nome promete, é idêntico a `casos_total`: não serve (§1.3).
- **`/XD data` no robocopy engole `src/data`** — foi assim que a camada de
  dados quase não veio. Mesma armadilha do `/data/` no `.gitignore`.
- **O SIM para em 2024**: `componentes_municipais` tolera a partição ausente,
  senão o mapa por macro cai no último ano.
- **Ano parcial se detecta** (`meses_com_dado`), não se presume: 2025 tem
  12 meses; a origem o marca como parcial e está errada.
- As do sinan continuam valendo: glob na raiz de dataset, `sexo='TOTAL'`,
  6 dígitos de município, código da doença por dataset (`HANS` no
  `sinan_landing`), `valor` com espaço, `except Exception` nunca
  `BaseException`, não importar `app.py` em teste.

## Estado

Fase 1, com agregados. Os sete indicadores do boletim que dá para calcular
estão na tela; falta o % GIF na cura, que precisa da coorte. O microdado está pedido (`docs/pedido-microdado.md`);
com ele entram cura de coorte, contatos examinados, abandono e as taxas
0–14 e grau II sobre casos novos. Deploy: `docs/deploy.md`.
