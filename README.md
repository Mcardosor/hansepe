# Painel de Monitoramento da Hanseníase — Pernambuco

Painel de vigilância da hanseníase do estado de Pernambuco, em Streamlit,
com recorte por **município**, **região de saúde** e **macrorregião de
saúde**. Reconstrução em Python do painel Shiny da equipe parceira, sobre o
core da família Cenários+ (`../sinan`, `../RecifeTB`).

## Conteúdo

- **Sete indicadores** do ano e território selecionados, com variação
  contra o ano anterior: taxa de detecção geral e em menores de 15 anos,
  casos novos (geral e 0–14), curas, proporção de multibacilares e de grau
  II de incapacidade no diagnóstico.
- **Mapa** clicável (município → região de saúde → macrorregião), com três
  classificações de cor: quintis (como o painel de origem), quebras naturais
  e a **escala de endemicidade do Ministério da Saúde**.
- **Evolução temporal**: canal endêmico com filtro por grau de
  incapacidade, série anual e epicurva mensal desde 2010.
- **Ranking**, **pirâmide etária**, **tópicos de interesse** (16 variáveis
  da ficha) e os gráficos anuais de classificação operacional e de casos
  0–14.

Tudo responde ao recorte: entrar numa macrorregião muda os sete cards e
todos os gráficos, somando os municípios e recalculando as taxas.

Como cada número é calculado: [`docs/metodologia.md`](docs/metodologia.md).
Onde difere do painel de origem e do MS:
[`docs/paridade-hanseniase.md`](docs/paridade-hanseniase.md).

## Dados

A extração agregada do SINAN da equipe parceira, **só a parte de
hanseníase**: `incidence`, `incidence_0_14`, `sinan_landing`, `_cache_ts`,
`piramides` e os do SIM, com as partições `doenca=HANS` e
`doenca=HANSENIASE`, mais as malhas da SES-PE em `data/support/`. São 44 MB,
e o painel não lê nada fora de `data/` — apagar aqui não afeta outro projeto.
Nenhum dado nominal entra.

Os parquets não são versionados. Para montar a pasta a partir do lago do
painel nacional:

```bash
python -m scripts.extrair_dados_hanseniase          # de ../sinan/data
python -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data
```

É uma cópia: quando a extração do sinan for atualizada, rode de novo.
`data/PROCEDENCIA.json` diz de onde veio e quando.

## Como rodar

```bash
../sinan/.venv/Scripts/python -m streamlit run app.py
pytest
```

Deploy na VM: [`docs/deploy.md`](docs/deploy.md) — porta 8510,
`/cenarios/hansepe/`.

## Estrutura

```
hansepe/
├── app.py                  # composição da tela
├── src/
│   ├── estado.py           # navegação PE → macro → região → município
│   ├── mapa.py, graficos.py, resiliencia.py
│   ├── data/               # escopo, leitura, kpis, canal, recortes, geo
│   ├── doencas/hanseniase.py
│   └── theme/
├── tests/                  # ~380 testes; tests/paridade contra a tela de origem
├── docs/                   # metodologia, paridade, inventário, plano, deploy
└── assets/                 # bandeira de PE e marca
```

Fonte: SINAN/Ministério da Saúde; população IBGE. Hierarquia geográfica:
Secretaria Estadual de Saúde de Pernambuco.
