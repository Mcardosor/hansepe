# CLAUDE.md

Guidance for Claude Code when working in this repository.

Painel de monitoramento da **hanseníase de Pernambuco**, em Streamlit.
Reconstrução em Python do painel Shiny da equipe parceira
(`cenariostb.unb.br/PE_HANSE_06_01`, embutido em
`cenarios.unb.br/pernambuco-hans`), tela a tela — inventário em
`docs/inventario-painel-origem.md`. **Os números reproduzem o painel de
origem; a cara também.** Onde a origem diverge do Ministério da Saúde, a
divergência está em `docs/paridade-hanseniase.md` e no tooltip do card.

Herda o core do painel nacional (`../sinan`: leitores, `Escopo`,
navegação PE → macro → região de saúde → município, `recortes.py`) e a
composição de tela do RecifeTB (`mapa.py` com três classificações,
`graficos.py`, `canal.py`, `theme/`). Segue `../sinan/docs/como-fazer.md`.

Documentação, código, commits e comentários em português.

## Comandos

Ambiente: o `.venv` do painel nacional, `../sinan/.venv` (Python 3.13). Os
dados são a extração do sinan: em dev, `data/` é uma **junção** para
`../sinan/data` (`New-Item -ItemType Junction`); em produção, volume.

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
- **`casos_total` da hanseníase é toda entrada no registro**, não caso novo
  (paridade §1). Para TB a mesma coluna já vem filtrada.
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

Fase 1, com agregados. O microdado está pedido (`docs/pedido-microdado.md`);
com ele entram cura de coorte, contatos examinados, abandono e as taxas
0–14 e grau II sobre casos novos. Deploy: `docs/deploy.md`.
