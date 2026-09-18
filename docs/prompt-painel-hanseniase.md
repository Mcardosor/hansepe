# Prompt para abrir em outra conversa — Painel de Hanseníase de Pernambuco

Copie tudo abaixo da linha e cole como primeira mensagem de uma conversa nova,
com o diretório de trabalho em `C:\Users\Cenarios-Matheus\Desktop\Painéis_Cenários`.

---

Preciso de um painel de monitoramento da **hanseníase** de Pernambuco. Ele
nasce de duas bases, e o trabalho é comparar as duas, ficar com o melhor de
cada e entregar com a cara nova:

1. **Base de conteúdo: `paineis/tbpe`** — o painel de tuberculose de PE que já
   existe. É antigo (último commit em ago/2026, antes do RecifeTB), mas é ele
   que sabe de Pernambuco: 185 municípios, 12 regiões de saúde e 4
   macrorregiões, ETL de microdado com residência em PE, população IBGE por
   município e ano (SIDRA), precomputação da visão padrão, e as regras de
   negócio em `src/indicadores.py`. Também tem seções que o RecifeTB não tem
   (coorte de desfecho, oportunidade do tratamento, comorbidades, heatmap por
   macrorregião, Superset embutido).
2. **Base de forma: `paineis/RecifeTB`** — o painel de tuberculose de Recife,
   o mais recente da família. É a referência visual e de arquitetura: página
   única com `Navegacao` (cidade → distrito → bairro), mapa pydeck clicável
   com três classificações (natural, quartil, fixa), cartões de KPI, canal
   endêmico, tópicos de interesse, tema em `src/theme/`, disease pack em
   `src/doencas/`, entrega por imagem Docker e regra absoluta do dado
   nominal. O prompt que planejou o pack de hanseníase de Recife está em
   `paineis/RecifeTB/docs/prompt-painel-hanseniase.md` — leia, porque os
   indicadores, cortes de endemicidade e colunas da ficha **têm que ser os
   mesmos** nos dois painéis. Quem decidir primeiro, o outro copia.

Não é para fazer o tbpe "virar" hanseníase por busca-e-troca, nem para copiar
o RecifeTB e apontar para PE. É um painel novo, em `paineis/hansepe`, que herda o ETL e as regras de PE do tbpe e a
estrutura, o visual e as convenções do RecifeTB.

Leia primeiro, nesta ordem:

- `paineis/tbpe/README.md` — conteúdo, regras de negócio, limitações
  conhecidas (não há linkage com o SIM; ano parcial é detectado; anos sem
  estimativa IBGE são interpolados) e o gotcha da ordem de enrolamento dos
  GeoJSONs
- `paineis/tbpe/etl/preparar_dados.py`, `baixar_populacao.py`,
  `precomputar.py` — o pipeline; hoje lê
  `../dashboard-tb-v3/dados_dashboard/tuberculose_*_tratado.parquet` e os
  shapefiles da SES-PE
- `paineis/tbpe/src/indicadores.py` e `src/filtros.py` — o que cada número
  faz e como o filtro atravessa
- `paineis/RecifeTB/CLAUDE.md` — arquitetura, comandos, armadilhas
- `paineis/RecifeTB/docs/metodologia.md`, `docs/dados.md`,
  `docs/paridade-com-o-painel-r.md` — a hanseníase precisa dos três
- `paineis/RecifeTB/src/doencas/tuberculose.py`, `src/doencas/__init__.py`
  (`CONTRATO`), `src/data/kpis.py`, `src/mapa.py`, `src/theme/`
- `paineis/sinan/docs/como-fazer.md` — a receita da família; e
  `paineis/sinan/src/data/recortes.py`, que já lê macrorregião e GERES de PE

## Comparar antes de construir

O quadro comparativo tbpe × RecifeTB **já está decidido em `docs/plano.md`
§3** — este é o resumo; preencha o que lá ficou como "avaliar" e me mostre
antes de codar:

| Peça | tbpe | RecifeTB | Fica |
|---|---|---|---|
| Mapa | Plotly, sem clique; três níveis por botão | pydeck, clique navega; classificações natural/quartil/fixa | RecifeTB — os cortes de endemicidade da hanseníase pedem a escala fixa |
| Navegação | filtros de macro/região/município na lateral | `Navegacao` em cascata | RecifeTB, com PE → macrorregião → região de saúde → município |
| Dados | microdado parquet + precomputação | agregados + microdado sem identificador | decidir olhando o que a extração de hanseníase traz |
| População | IBGE/SIDRA por município e ano, pessoas-ano nas séries | do dataset agregado | tbpe — é o que existe para PE |
| Óbito | campo de encerramento do SINAN | SIM | tbpe, com a ressalva no texto (hanseníase quase não mata; talvez nem seja KPI) |
| Coorte / oportunidade / comorbidades / heatmap | tem | não tem | avaliar uma a uma para hanseníase |
| Superset embutido | tem | não | manter só se o cliente usar |
| Tema, cartões, tipografia, cores | próprio, antigo | `src/theme/`, cromo `#12346B` + cores de métrica da família | RecifeTB |
| Testes | 14 regressões | 170, com paridade contra R e Boletim | RecifeTB como padrão |

## O que é da hanseníase

| | Tuberculose | Hanseníase |
|---|---|---|
| KPIs | incidência, casos novos, mortalidade, interrupção, HIV+, cura | **taxa de detecção geral /100 mil**, **detecção em < 15 anos /100 mil**, **grau 2 de incapacidade no diagnóstico (%)**, **cura (%)** entre os que saíram de registro ativo, **contatos examinados (%)**, **abandono (%)** — confirmar com o Boletim de Hanseníase e com o chefe |
| Escala fixa | âncoras Brasil / PE / meta de cura | endemicidade oficial: detecção geral **< 2 baixa · 2–10 média · 10–20 alta · 20–40 muito alta · ≥ 40 hiperendêmica**; em < 15 anos **< 0,5 · 0,5–2,5 · 2,5–5 · 5–10 · ≥ 10**; grau 2 **< 5% baixo · 5–10 médio · ≥ 10% alto** — por município, então o mapa municipal é a tela principal |
| Ficha | colunas de TB | `CLASSOPERA`, `FORMACLINI`, `AVALIA_N`, `ESQ_INI_N`, `MODOENTR`, `NERVOSAFE`, `NU_LESOES`, `CONTREG`/`CONTEXAM`, `TPALTA_N`, `BACILOSCO` …; os identificadores continuam fora, pelo mesmo `preparar_microdado.py` |
| Tópicos | 10 variáveis da TB | classificação operacional (PB/MB), forma clínica, grau de incapacidade, modo de entrada, esquema terapêutico, nº de lesões, nervos afetados, raça/cor, sexo |
| Série / canal | mensal | mensal no estado (PE ~2.500–3.000 casos/ano); avaliar trimestral por município |
| Comorbidades | agravos, populações vulneráveis | não se aplica igual; ver o que a ficha de hanseníase tem (reações hansênicas, se vierem) |

**Dados:** já existem — a extração do `paineis/sinan` traz hanseníase para
os 185 municípios de PE, 2010–2025, com grau II, < 15 anos, `TPALTA_N` e
`CONTEXAM`/`CONTREG`. O inventário está em `docs/plano.md` §1; o que falta
(microdado, série mensal) também.

## Regras que não mudam

- **Dado nominal nunca entra no git nem na imagem.** `.gitignore`,
  `.dockerignore`, `preparar_microdado.py` e `test_imagem.py` do RecifeTB
  vêm inteiros.
- Números seguem o **Boletim Epidemiológico de Hanseníase** do MS e o boletim
  estadual; recorte por **residência**, como no tbpe. Toda divergência vai
  para `docs/paridade-hanseniase.md`.
- `ruff check --select F` para código morto; testes com o `.venv` do sinan;
  commit quando eu disser "pode commitar"; a rede bloqueia GitHub sem VPN.
- Entrega: decidir entre imagem para outra equipe (RecifeTB) ou compose na
  VM (tbpe roda em `/cenarios/tbpe/`) — depende de quem vai hospedar; me
  pergunte.

## Como quero trabalhar

**Leia `docs/plano.md` desta pasta antes de qualquer coisa** — inventário
dos dados, KPIs com fórmula e fonte, quadro comparativo decidido, decisões
pendentes (§4) e o roteiro do dia 1 (§5). Não refaça o inventário; confira o
que ele manda conferir e siga o roteiro, por partes, sempre me mostrando no
navegador. As decisões de §4 estão todas fechadas — não reabra. O microdado já foi
pedido (`docs/pedido-microdado.md`); enquanto não chega, é fase 1 com
agregados.
