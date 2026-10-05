# Painel de Monitoramento da Hanseníase — Pernambuco

Painel de vigilância epidemiológica da hanseníase em Pernambuco, com recorte
por município, região de saúde e macrorregião de saúde. Desenvolvido em
Python com Streamlit, a partir do painel Shiny mantido pela equipe parceira.

Disponível em <https://painel.cenarios.unb.br/cenarios/hansepe/>.

## O que o painel apresenta

**Sete indicadores** do ano e do território selecionados, com a variação em
relação ao ano anterior: taxa de detecção geral e em menores de 15 anos,
casos novos (geral e na faixa de 0 a 14), curas, proporção de multibacilares
e proporção de grau II de incapacidade no diagnóstico.

**Mapa navegável** por clique, do estado até o município, com três formas de
classificar as cores: a escala de endemicidade do Ministério da Saúde, que é
o padrão, quintis e quebras naturais.

**Evolução temporal** em três vistas: canal endêmico com filtro por grau de
incapacidade, série anual e epicurva mensal desde 2010.

**Ranking de municípios, pirâmide etária e tópicos de interesse**, com
dezesseis variáveis da ficha de notificação, além dos gráficos anuais de
classificação operacional e de casos em menores de 15 anos.

Todos os elementos respondem ao recorte selecionado. Ao entrar em uma
macrorregião, os cartões e os gráficos são recalculados a partir da soma dos
municípios que a compõem.

A regra de cálculo de cada indicador está em
[`docs/metodologia.md`](docs/metodologia.md). As diferenças em relação ao
painel de origem e às definições do Ministério estão registradas em
[`docs/paridade-hanseniase.md`](docs/paridade-hanseniase.md).

## Dados

O painel lê a extração agregada do SINAN mantida pela equipe parceira,
restrita às partições de hanseníase, somada às malhas territoriais da
SES-PE. São cerca de 47 MB em disco, e o painel não acessa nada fora da pasta
`data/`. Nenhum dado nominal ou identificável entra.

Os arquivos não são versionados. Para montar a pasta a partir do lago do
painel nacional:

```bash
python -m scripts.extrair_dados_hanseniase
python -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data
```

O resultado é uma cópia independente: quando a extração de origem for
atualizada, é preciso rodar o script novamente. O arquivo
`data/PROCEDENCIA.json` registra a origem e a data da cópia em uso.

## Como executar

```bash
../sinan/.venv/Scripts/python -m streamlit run app.py
pytest
```

As instruções de publicação na VM estão em
[`docs/deploy.md`](docs/deploy.md).

## Organização do código

```
hansepe/
├── app.py                  composição da tela
├── src/
│   ├── estado.py           navegação estado → macro → região → município
│   ├── mapa.py             mapa em deck.gl
│   ├── grafico_componente.py   gráficos em ECharts
│   ├── data/               leitura, indicadores, agregação, geografia
│   ├── doencas/            definições específicas da hanseníase
│   └── theme/              identidade visual e componentes
├── data/                   extração de hanseníase (não versionada)
├── tests/                  suíte automatizada, incluindo paridade
├── docs/                   metodologia, paridade, operação
└── assets/                 bandeira de Pernambuco e marca
```

---

Fonte dos dados: SINAN, Ministério da Saúde. Estimativas populacionais:
IBGE. Hierarquia de regiões e macrorregiões de saúde: Secretaria Estadual de
Saúde de Pernambuco.
