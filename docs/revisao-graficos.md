# Revisão crítica dos gráficos — o que herdamos da tuberculose

**25/set/2026.** Este painel foi construído com a composição visual do
RecifeTB, um painel de **tuberculose**, sobre o núcleo de dados do `sinan`.
A herança acelerou a entrega e foi a decisão certa. Mas o que veio junto não
foi só o código: veio o *raciocínio*. Vários gráficos respondem perguntas que
fazem sentido para uma doença aguda e não fazem para hanseníase.

O rastro está nos próprios arquivos. `canal.py` argumenta sobre "a
tuberculose em Recife está em alta sustentada"; `serie_dupla` se descreve
como "o gráfico duplo da tuberculose"; a epicurva diz "só Recife inteiro".
São docstrings que nunca foram reescritas para esta doença — e a docstring
não reescrita é o sintoma, não a causa.

Este documento lista o que está errado, com evidência, e o que propomos
fazer. **Nada aqui foi alterado ainda**: as mudanças de 2 a 5 mexem no que o
painel *afirma*, e essa decisão é da equipe, não do código.

---

## Resumo

| # | Problema | Gravidade | Proposta | Decisão de quem |
|---|---|---|---|---|
| 1 | Epicurva e canal endêmico mensais | **Alta** — a vista não tem referente | Remover as duas; o tempo da hanseníase é anual | Equipe (SES/Caio) |
| 2 | Mapa em contagem absoluta (`Casos novos`, `Casos 0–14`) | **Alta** — induz leitura falsa | Tirar do seletor do mapa, manter no ranking | Nossa, com aviso |
| 3 | Mapa em `Curas` | **Alta** — mistura coortes | Tirar do mapa; ou rotular como desfecho de coorte | Equipe |
| 4 | Definição do MS só em `casos`/`incid` | **Alta** — inconsistência interna | ~~Estender `MODOENTR=1`~~ **impossível na extração**; tela avisa, conserto depende do microdado | Feito em 28/set (aviso) |
| 5 | Ano corrente contra régua anual | Média | Abrir no último ano fechado; marcar o parcial | Equipe |
| 6 | Cortes de `casos` vestidos de "Endemicidade" | Média | Renomear a opção; a régua do MS é só de taxa | Nossa |

O que **não** está em revisão, e defendemos como está: o mapa em coeficiente
de detecção com a régua fixa do MS, a série anual, a proporção MB, o ranking
municipal, a pirâmide etária e os indicadores de qualidade com supressão de
coorte aberta.

---

## 1. A epicurva e o canal endêmico não têm referente em hanseníase

**O que existe hoje.** Na aba "Evolução temporal", duas vistas mensais: o
canal endêmico (`src/data/canal.py`, `montar`) e a epicurva contínua
(`epicurva`, de 2010 até o ano selecionado, `canal.py:226`).

**Por que não faz sentido.** O período de incubação da hanseníase é de dois
a sete anos. O mês em que um caso entra no SINAN não é o mês da infecção nem
o do adoecimento: é o mês em que **alguém encontrou** aquela pessoa. A curva
mensal desenha, portanto, a agenda do serviço — campanha, mutirão, exame de
contatos de um caso índice, férias da equipe, atraso de digitação. Em dengue
essa curva é epidemiologia; aqui é logística.

O canal endêmico agrava. Ele pergunta "março de 2025 está fora do padrão
histórico de março?". Para esta doença a pergunta não tem referente: não
existe padrão de março. A docstring de `canal.py` já admite que o canal
pressupõe série estacionária e que sob tendência ele mente — mas argumenta
isso para a TB. Aqui a premissa falha antes: não é que a tendência atrapalhe
o canal, é que não há sazonalidade a canalizar.

**O tamanho do número piora tudo.** PE tem ~1.590 casos novos por ano, ~130
por mês. Um município médio tem 5 a 10 casos **no ano**. Filtrado por
município, a série mensal é `0, 0, 1, 0, 2, 0…`, e os quartis de cinco anos
dessa sequência são 0 e 1. O canal vira ruído desenhado com rigor.

**Nota de fato:** o dado mensal existe de 2010 a 2026 em `_cache_ts` para
HANSENIASE — se a tela mostra a epicurva terminando por volta de 2015, é
rótulo de eixo ou janela de zoom do ECharts, não dado ausente. Vale conferir,
mas é o menor dos problemas desta seção.

**Proposta.** Remover as duas vistas mensais. O tempo da hanseníase é anual,
e a série anual 2010–2025 que o painel já tem é a vista correta. Se a equipe
quiser manter algum recorte intra-anual, o que tem sentido operacional é o
**acumulado do ano até o mês** contra o mesmo período dos anos anteriores —
mede ritmo de detecção do programa, não sazonalidade da doença.

**Custo:** remoção. `canal.py` sai do caminho do painel; os testes que
prendem o método do canal podem ficar, porque o módulo continua correto para
quem o use com doença aguda (é o mesmo núcleo do `tbpe` e do RecifeTB).

---

## 2. Contagem absoluta em mapa coroplético

**O que existe hoje.** `METRICAS_MAPA` inclui `casos` e `casos_0_14`
(`src/doencas/hanseniase.py:163`).

**Por que está errado.** Pintar contagem por área mapeia população. Recife,
Jaboatão e Caruaru ficam escuros em todo ano e em todo indicador, e a leitura
que o olho faz — "é ali que está o problema" — é falsa: Recife tem muitos
casos porque tem muita gente. O mapa em taxa existe exatamente para desfazer
isso, e a opção ao lado o refaz com um clique. É erro cartográfico clássico,
não questão de gosto.

**Proposta.** Tirar `casos` e `casos_0_14` do seletor **do mapa**. A
contagem continua onde ela responde bem: no KPI, no ranking de municípios e
no popup do município. Quem precisa do número absoluto por município o tem em
tabela, que é onde contagem se lê sem ilusão de área.

---

## 3. "Curas" no mapa mistura coortes

**O que existe hoje.** `cura` é opção do mapa, colorida pelo ano selecionado.

**Por que está errado.** Cura é desfecho de **coorte**: quem se cura em 2025
foi diagnosticado em 2023 ou 2024 (PB dura 6 meses, MB dura 12). Pôr "Casos
novos 2025" e "Curas 2025" no mesmo seletor, no mesmo mapa, sob o mesmo
título de ano, convida a dividir um pelo outro — e essa razão não significa
nada.

É o mesmo problema que já reconhecemos nos indicadores de qualidade, onde
suprimimos a cura quando a coorte está aberta (`kpis.COBERTURA_MINIMA_COORTE`).
**No mapa essa supressão não existe.** Em setembro de 2025 o mapa de curas é
mecanicamente claro no estado inteiro, e nada na tela diz que é artefato do
calendário.

**Proposta.** Tirar do mapa. Se a equipe quiser manter, então tem de vir com
o mesmo tratamento dos indicadores de qualidade: rótulo dizendo "coorte de
diagnóstico" e supressão quando a coorte do ano ainda está aberta.

---

## 4. A definição do MS entrou só pela metade

**O que existe hoje.** `MODOENTR = 1` — a definição de caso novo do
Ministério, adotada em 20/set/2026 — é aplicada apenas a `casos` e `incid`
(`src/data/leitura.py:479` e `:669`). Todo o resto continua em `casos_total`,
que na extração é **toda entrada no registro**: recidiva, transferência,
reingresso após abandono.

**Duas consequências, ambas visíveis na tela:**

1. Na mesma página, o KPI "Casos novos" conta uma coisa e a epicurva logo
   abaixo conta outra. Ninguém que compare os dois vai conseguir fechar.
2. `casos_0_14` e `taxa_det_0_14` são calculados sobre entradas totais,
   enquanto a régua exibida ao lado — "Hiperendêmico ≥ 10,00 por 100 mil" —
   é o parâmetro do MS para **detecção de casos novos** em menores de 15
   anos. A régua está certa; o número que ela mede não é o que ela mede.

Isso provavelmente explica parte do desvio de +8 a +28% contra o boletim que
registramos em `paridade-hanseniase.md` e atribuímos à falta de microdado.
**Vale medir antes de creditar ao microdado.**

**Proposta original — e por que ela não sobreviveu à medição.** A proposta
era estender o filtro `MODOENTR = 1` a `casos_0_14`, `taxa_det_0_14` e às
séries. Medido em 28/set/2026, **não dá**: `sinan_landing` é marginal por
variável, sem cruzamento e sem idade; `_cache_ts` cruza só por grau. Não
existe consulta que devolva 0–14 com modo de entrada.

E o atalho de aplicar a proporção geral de casos novos ao 0–14 **erra**: a
proporção nessa faixa é de 5 a 15 pontos maior que a geral (criança
raramente teve tratamento anterior, então quase não há recidiva nem
reingresso). Em 2023 o atalho levaria 97 para 67, contra 77 do boletim —
trocaria um erro de +26% por um de −13%. A tabela ano a ano está em
`paridade-hanseniase.md` §1.1.

**O que foi feito em 28/set/2026.** Só o que era honesto fazer sem o
microdado: a tela passou a dizer o que mede. O tooltip de `casos_0_14`
afirmava que "a diferença é pequena nessa faixa" — era falso, e agora traz a
faixa medida (78% a 92%); o de `taxa_det_0_14` e a ajuda do gráfico de 0–14
passaram a avisar que o número conta todas as entradas enquanto a régua ao
lado é definida sobre casos novos. A série mensal já avisava.

**O que continua pendente.** O conserto numérico depende do microdado
(`pedido-microdado.md`). O teste
`test_0_14_fica_acima_do_boletim_por_falta_de_modo_de_entrada` já prende a
divergência e falha quando ela sumir.

**De quebra, um achado para o núcleo `sinan`:** o dataset `cases_new`, cuja
coluna se chama `casos_novos`, é idêntico a `incidence.casos_total` em todos
os anos de PE. O nome promete um filtro que o conteúdo não tem. Este painel
não o usa. Registrado em `paridade-hanseniase.md` §1.3.

---

## 5. O ano corrente contra a régua anual

O mapa abre em 2025 com cerca de nove meses de notificação e classifica cada
município numa escala de coeficiente **anual**. O estado inteiro aparece
menos endêmico do que é, e o mapa de 2025 não é comparável ao de 2024. O
boletim da SES usa 2024 fechado exatamente por isso.

**Proposta.** Abrir no último ano fechado e marcar o ano corrente como
parcial no seletor ("2025 — parcial"), mantendo-o disponível. É decisão da
equipe porque troca "dado mais recente" por "dado comparável", e as duas
leituras têm defensores.

---

## 6. Cortes inventados vestidos de parâmetro oficial

Os cortes usados para `casos` no mapa — `(0, 5, 10, 25, 50, 100)`,
`hanseniase.py:246` — não são parâmetro do Ministério de coisa alguma.
São números escolhidos por nós. Eles aparecem sob o mesmo botão
"Endemicidade" que, nas outras métricas, cita literalmente o boletim: a
legenda fica com autoridade emprestada.

**Proposta.** Se 2 for aceito, o problema some com a métrica. Se `casos`
ficar no mapa, a opção precisa de outro nome ("faixas de contagem") e a
legenda, de uma linha dizendo que o corte é nosso.

---

## O que fica de lição

A herança do RecifeTB nos deu em dias um painel que levaria semanas, e as
partes estruturais — mapa, componentes, cache, escopo — estavam certas para
as duas doenças. O que não transferiu foi a **epidemiologia**: gráfico é
afirmação sobre uma doença, e uma afirmação verdadeira sobre tuberculose
pode ser vazia sobre hanseníase. Onde o núcleo é compartilhado entre painéis
(`canal.py` serve `tbpe`, RecifeTB e este), a regra deve ser que o *pacote da
doença* decida quais vistas existem — hoje ele decide cores, rótulos e
cortes, mas não isso.
