# Como fazer outro painel desta família

Escrito no fim do primeiro painel, para quem vai começar o segundo.

> **Este arquivo é a fonte.** Existe uma versão publicada em
> <https://claude.ai/code/artifact/b0c0592b-c523-47e4-9a95-b4f616d4ac77>, para
> quem precisa ler o guia sem ter acesso a este repositório, que é privado.
> Ela é **espelho**: quem editar este arquivo republica lá, na mesma URL — o
> link já circulou na equipe. Editar só o espelho é como o guia morre.

**Não é um resumo dos outros documentos.** O contrato de dados, o cronograma,
a performance e o deploy continuam sendo a fonte de cada assunto — aqui só
está o que atravessa todos eles: **o que reaproveitar, em que ordem trabalhar,
e onde este projeto sangrou.** Quem for construir o painel 2 lê este primeiro
e depois vai aos específicos pelos ponteiros da §7.

O painel 1 (Tuberculose) levou **8 semanas, 1 dev, 40h/semana**, incluindo
reconstruir um dashboard Shiny/R de outra equipe com paridade auditada. O
painel 2 não deve levar isso — a maior parte do que segue existe para explicar
por quê.

---

## 0. A decisão que define todo o resto

**O core é único e a doença é configuração.** Herdamos o padrão de *disease
pack* do projeto original e ele se pagou: cores, rótulos, ordem dos KPIs,
métricas do mapa e paletas saem de `src/doencas/tuberculose.py` — 301 linhas
de constantes, sem lógica. O mapa, os gráficos, o tema e a navegação nunca
souberam que doença estão desenhando.

**E o registro já existe.** Era a primeira tarefa do painel 2 e foi feita
antes dele: `src/doencas/__init__.py` resolve o pack por nome e o `app.py`
recebe o resultado.

```python
pack = doencas.carregar()   # SINAN_DOENCA, ou tuberculose
```

A ordem é: nome passado à função, variável de ambiente `SINAN_DOENCA`, padrão
`tuberculose`. **Env var e não parâmetro de URL** — o deploy é um container
por painel, então o processo serve uma doença só; pelo URL o pack mudaria
entre reruns do Streamlit, com o `st.cache_resource` da geometria já quente
para a doença anterior.

Duas coisas que o registro faz além de importar, e que valem no painel 2:

- **Confere o nome contra os packs presentes antes do import.** O valor vem
  do ambiente, e `importlib` com string de fora importaria qualquer módulo
  alcançável.
- **Confere o contrato** — os quinze atributos que o `app.py` consome, em
  `doencas.CONTRATO`. Um pack incompleto falha no carregamento dizendo o que
  falta, e não meia tela adiante, num `AttributeError` engolido por
  `resiliencia.painel`. É a rede que o pack novo vai usar enquanto nasce.

A razão de ter sido feito **antes** da segunda doença continua valendo para a
terceira: se duas nascem com import fixo, o painel seguinte vira refatoração
em três lugares em vez de configuração — que é exatamente o erro que o projeto
em R cometeu ao fixar `pe` no nome das funções, e que `recortes.py` existe
para não repetir.

---

## 1. O que se reaproveita, e o que se reescreve

| Módulo | Reaproveita? | O que muda no painel 2 |
|---|---|---|
| `src/data/escopo.py` | **Inteiro** | Nada. `Escopo` é a espinha do projeto |
| `src/data/conexao.py` | Quase todo | `PARTICOES` e `ARQUIVOS_HETEROGENEOS` descrevem o *disco*, não o código |
| `src/data/config.py` | Quase todo | Os mapas de código de doença por dataset |
| `src/data/geo.py` + `scripts/preparar_geometria.py` | **Inteiro** | Nada — a malha do IBGE é a mesma |
| `src/data/recortes.py` | **Inteiro** | Uma entrada em `CONFIGURACOES` por UF nova, sem tocar em código |
| `src/mapa.py` | **Inteiro** (1.032 linhas) | Nada. As métricas vêm do pack |
| `src/graficos.py` | Quase todo | Só os gráficos que existem por causa da doença |
| `src/theme/` | **Inteiro** | Nada. Cor é por *métrica*, não por doença |
| `src/estado.py` | **Inteiro** | Nada |
| `src/resiliencia.py` | **Inteiro** | Nada |
| `src/data/leitura.py` | Metade | As fórmulas são de domínio: cada doença tem as suas |
| `src/data/kpis.py` | Metade | Idem |
| `app.py` | **Reescreve** | É layout: 1.037 linhas de composição, não de lógica |

Lido de outro jeito: **cerca de 4.000 das 6.236 linhas de `src/` são
infraestrutura já paga.** O que sobra é fórmula de KPI, os gráficos próprios
da doença e o arranjo da tela.

---

## 2. A ordem que funcionou, e o ajuste que eu faria

O `docs/cronograma.md` tem as 8 semanas com o detalhe. O que a ordem ensinou:

| Semana | Fase | Veredito |
|---|---|---|
| 1 | Fundação: dados, paridade, tema | Certa. Nada depois disso ficou bloqueado por falta de base |
| 2 | Esqueleto + KPIs + geometria | Certa |
| 3 | **Mapa** | Marcada como "semana de risco" antes de começar, e foi mesmo |
| 4 | Gráficos | Certa |
| 5 | Específico da doença | Certa |
| 6 | Paridade + performance | **Tarde demais** — ver abaixo |
| 7 | Análise livre (Superset) | Adiada, e pode não entrar. É produto separado |
| 8 | Polimento + deploy | Certa |

**Dois ajustes para o painel 2:**

1. **O teste de ponta a ponta do `app.py` entra na semana 2, não no fim.**
   Durante quase todo o projeto o `app.py` teve **zero cobertura de
   execução**: os testes cobriam leitores, gráficos e mapa, e ninguém rodava a
   aplicação. Um defeito de navegação (o `segmented_control` de recorte com
   `key`, §4) ficou **dois dias** no ar quebrando o drill-down sem nenhum
   teste vermelho. O `streamlit.testing.v1.AppTest` resolve, e é barato: 30
   casos rodam em ~20 s.

2. **Meça performance na semana 1, não na 6.** A linha de base em
   `docs/performance.md` só existiu quando já havia o que otimizar — então
   metade das medições virou arqueologia. Rodar `scripts/medir_performance.py`
   contra a camada de leitura no primeiro dia dá o número de "antes" de graça.

**A semana do mapa continua sendo a de risco.** Não é o desenho — é que todo
limite do Streamlit e do deck.gl aparece ali de uma vez (§4).

---

## 3. Sete decisões estruturais que valem repetir

**1. `Escopo` é o único parâmetro.** Todo leitor e todo KPI recebe um
`Escopo(doenca, ano, nivel, uf, mun)` congelado, que se valida sozinho no
`__post_init__`. Nada de arrastar `uf=None, mun=None, nivel="BR"` por seis
assinaturas. Quando o painel ganhou macrorregiões, o `Escopo` não mudou.

**2. DuckDB lê o parquet direto, sem carregar nada.** Conexão em memória,
`read_parquet` com pushdown do filtro de partição, `st.cache_resource` por
processo. Nenhum dado entra no banco. É a razão de o painel responder mais
rápido que o original em R, que faz round-trip ao servidor a cada interação.

**3. Geometria simplificada uma vez, em disco.** `scripts/preparar_geometria.py`
roda em ~40 s para as 27 UFs e o resultado é tratado como dado, não como
código. O original simplificava a cada redesenho do mapa. Simplificação
**topológica** — o porquê está em `docs/performance.md`; a ingênua abre
buracos entre municípios vizinhos.

**4. Chave canônica dentro, tradução na fronteira.** O código do município tem
6 e 7 dígitos conforme o dataset, e o código da doença muda de nome entre
datasets (`HANSENIASE` num, `HANS` noutro). A aplicação **só** conhece a forma
canônica; a tradução acontece na montagem da query. Sem isso, cada leitor novo
redescobre a inconsistência por conta própria.

**5. Falha de painel custa um painel.** No Streamlit, exceção no corpo do
script troca a **página inteira** pelo traceback — aconteceu de verdade: o
ranking montou um escopo inválido e o dashboard sumiu inteiro.
`src/resiliencia.py` contém a falha onde ela nasceu. O detalhe não óbvio, que
está comentado lá: capture `Exception`, **nunca** `BaseException` —
`st.rerun()` funciona levantando `RerunException`, que herda de
`BaseException` de propósito. Ampliar a captura mata toda a navegação por
clique sem erro nenhum aparecer.

**6. Cor é por métrica, não por doença.** Incidência é ocre em qualquer painel
da família; óbito é vermelho. Quem abrir o painel 2 já sabe ler a legenda. Os
tokens ficam em `src/theme/`, com contraste verificado nos dois temas.

**7. Paridade com divergências escritas.** O harness (`pytest tests/paridade`)
compara contra referências congeladas do painel de origem. **Divergir é
permitido; divergir em silêncio não.** Cada diferença vira uma entrada em
`tests/paridade/excecoes.md` com a decisão e o motivo — e três delas acabaram
provando que o painel de origem é que estava errado. Sem esse documento, a
primeira reunião vira discussão de número em vez de discussão de decisão.

---

## 4. As armadilhas que vão reaparecer

### Dados

As 17 armadilhas específicas estão em `docs/contrato-dados.md` e não se
repetem aqui. O que se repete são as **classes**:

- **Total escondido no meio das categorias.** `sinan_landing` tem linha
  `TOTAL` além de M, F e I — somar tudo dobra o número. Confira sempre se a
  soma das categorias bate com o total declarado.
- **Categoria que some no meio da série.** `SITUA_ENCE` perdeu "não
  informado" a partir de 2018, e isso cria um degrau que parece tendência.
  Conte as categorias distintas **por ano** antes de desenhar qualquer série
  temporal.
- **Mesmo diretório, esquemas diferentes.** Ler a pasta inteira adota o
  esquema do primeiro arquivo e **descarta colunas dos demais em silêncio**.
- **Fontes com relógios diferentes.** O SIM fecha bem depois do SINAN, então o
  dado de óbito fica um ano atrás o tempo todo. Isso é ausência normal, não
  erro de configuração — e precisa ser tratado como tal, ou o painel mostra
  zero onde deveria mostrar "ainda não".
- **Código com zero à esquerda, com espaço à esquerda, e com erro de ponto
  flutuante.** Os três aconteceram. Normalize na entrada.

### Streamlit

- **Widget com `key` é dono do valor; sem `key`, é espelho.** Um controle com
  `key` **briga** com navegação programática: o usuário clica no mapa, o
  estado muda, e o widget restaura o valor antigo. Isso causou **dois loops
  infinitos** neste projeto. Regra prática: controle que só o usuário mexe
  leva `key`; controle que o código também move não leva, e recebe `default` a
  cada run.
- **Seleção de gráfico persiste entre runs.** `st.altair_chart(on_select="rerun")`
  devolve a mesma seleção em todo rerun seguinte. O handler de clique **tem
  que ser idempotente**, ou re-executa a navegação para sempre.
- **O healthcheck mente.** `/_stcore/health` responde assim que o servidor
  sobe e ignora se o script levantou exceção. O container fica `healthy` com a
  página exibindo `FileNotFoundError`. **Depois de todo deploy, abra a página
  e confira um número conhecido** — está no fim do `docs/deploy.md`.

### deck.gl / pydeck

- **O pydeck converte strings *e listas* em acessores `@@=`. Só tuplas
  sobrevivem.** Foi o que quebrou os caracteres acentuados: o conjunto de
  caracteres do atlas de fonte precisa ser `tuple`, não `list`.
- **Multi-view não passa pelo componente do Streamlit.** O inset de Fernando
  de Noronha teve que ser feito como camada, não como segunda vista.
- **Não existe transição de câmera.** O Streamlit **recria o contêiner e o
  canvas do deck a cada rerun**, mesmo com a `key` inalterada — medido no
  navegador. `transitionDuration` e `FlyToInterpolator` são emitidos e não
  fazem nada, porque não há instância anterior de onde partir. Não tente de
  novo; o motivo está comentado em `src/theme/componentes.py`.
- **Os controles do mapbox nascem *dentro* do wrapper do deck**, que escuta o
  ponteiro na fase de captura. Clicar no botão de zoom com um polígono embaixo
  dá zoom **e** navega. `stopPropagation` não resolve em nenhuma das duas
  fases; a saída foi realocar o controle para fora do wrapper.

---

## 5. O que custou caro

Cinco coisas que este projeto pagou e o próximo não precisa pagar:

1. **Classificação por quantil no mapa.** Herdada do original. Dentro de uma
   UF ela comprime a cauda, e as barras do ranking saíam quase monocromáticas
   — GVF de 0,463 em PE. Trocada por **quebras naturais** (k-means 1-D):
   GVF 0,964. Comece com quebras naturais.
2. **Dois números da mesma coisa na tela.** A proporção de cura aparecia como
   57,15% num lugar e 65,1% noutro, porque os denominadores eram diferentes e
   ambos defensáveis. Custou uma investigação até o banco cru. **Antes de
   exibir uma proporção, escreva o denominador no contrato de dados** — e
   mostre a fração no próprio card, que foi como resolvemos.
3. **`app.py` sem teste** (§2).
4. **Credenciais no `.env.exemplo`.** O arquivo de exemplo é versionado; o
   `.env` não. Hoje há três guardas em `tests/test_segredos.py` que quebram a
   suíte se alguma credencial voltar para lá. Copie esse teste para o painel 2
   **no primeiro dia**, antes de existir um `.env`.
5. **README prometendo verde.** A suíte sem dados tinha 24 falhas enquanto o
   README dizia que passava. Marcadores de teste (`PRECISAM_DE_DADOS`, marker
   `dado`) resolvem — quem clona sem os 209 MB precisa ver skip, não falha.

---

## 6. Checklist de arranque do painel 2

- [ ] Copiar `src/` inteiro e apagar `src/doencas/tuberculose.py`
- [x] ~~Criar o registro de packs~~ — feito no painel 1 (§0); vem junto no `src/`
- [ ] Copiar `tests/test_segredos.py` e `tests/conftest.py` antes de existir um `.env`
- [ ] Escrever o pack novo contra `doencas.CONTRATO` — só constantes, sem lógica
- [ ] Apontar `SINAN_DOENCA` para ele no `docker-compose.yml`
- [ ] Mapear os códigos da doença por dataset em `config.py` (§3, item 4)
- [ ] Conferir `PARTICOES`: **a ordem das partições não é uniforme entre datasets**
- [ ] Rodar `scripts/medir_performance.py` e guardar a linha de base **antes** de otimizar
- [ ] Escrever `tests/test_aplicacao.py` assim que houver uma tela
- [ ] Congelar as referências de paridade **antes** de mexer nas fórmulas
- [ ] Abrir `tests/paridade/excecoes.md` na primeira divergência, não na décima

---

## 7. Onde está o resto

| Assunto | Documento |
|---|---|
| Origem, datasets, fórmulas e as 17 armadilhas | `docs/contrato-dados.md` |
| As 8 semanas, com o que ficou aberto | `docs/cronograma.md` |
| Medições, geometria, alvo de tempo de resposta | `docs/performance.md` |
| Docker, nginx, deploy key, o susto do healthcheck | `docs/deploy.md` |
| O que o painel de origem tem, tela por tela | `docs/inventario-funcionalidades.md` |
| Divergências com o painel em R, decididas | `tests/paridade/excecoes.md` |
| Banco cru do SINAN, para conferência | `docs/banco-cenarios.md` |
| Superset, se um dia voltar | `docs/analise-livre.md` |
| Perguntas abertas com a equipe parceira | `docs/perguntas-equipe-r.md` |
