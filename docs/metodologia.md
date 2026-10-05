# Metodologia

**Painel de Monitoramento da Hanseníase — Pernambuco**
Documento de referência para leitura dos indicadores.

| | |
|---|---|
| Destinatário | Secretaria Estadual de Saúde de Pernambuco |
| Versão | 1.0 |
| Última revisão | outubro de 2026 |
| Responsável técnico | *(preencher)* |

---

Este documento descreve a origem dos dados e a regra de cálculo de cada
indicador exibido no painel. Onde existe mais de uma definição aceita, a
escolhida está justificada. As diferenças em relação ao painel Shiny da
equipe parceira e às definições do Ministério da Saúde estão reunidas em
[`paridade-hanseniase.md`](paridade-hanseniase.md).

## 1. Fonte dos dados

O painel utiliza a extração agregada do SINAN mantida pela equipe parceira,
restrita às notificações de hanseníase de residentes em Pernambuco. É a mesma
base que alimenta o painel Shiny de origem, o que permite comparação direta
entre os dois.

A série cobre de 2010 a 2025, com os doze meses em todos os anos. O ano de
2026 ainda está incompleto e por isso não é oferecido no seletor, embora
apareça na série mensal.

As estimativas populacionais por município e ano vêm do IBGE e já acompanham
o agregado. A malha territorial é a da SES-PE: 185 municípios, 12 regiões de
saúde e 4 macrorregiões de saúde.

Todo recorte geográfico segue o **município de residência**, conforme a regra
adotada no boletim estadual. A série mensal obedece ao mesmo critério, e os
totais conferem com a tabela anual (2.468 casos em 2024 pelas duas vias).

Nenhum dado nominal ou identificável entra no painel.

## 2. Os sete indicadores principais

Os sete cartões do topo se referem sempre ao ano e ao território
selecionados, seja Pernambuco, uma macrorregião, uma região de saúde ou um
município. A seta ao lado de cada valor compara com o ano anterior no mesmo
território.

| Indicador | Cálculo |
|---|---|
| Taxa de detecção geral | casos novos ÷ população × 100.000 |
| Taxa de detecção em menores de 15 anos | casos novos de 0 a 14 ÷ população de 0 a 14 × 100.000 |
| Casos novos | notificações com modo de entrada "caso novo" |
| Casos novos de 0 a 14 anos | notificações na faixa etária |
| Curas | saídas por cura registradas no ano |
| Proporção de multibacilares | MB ÷ (PB + MB) × 100 |
| Proporção de grau II no diagnóstico | grau 2 ÷ casos com avaliação registrada × 100 |

### Casos novos seguem a definição do Ministério

Contam apenas as notificações cujo modo de entrada é "caso novo". Recidivas,
transferências e demais reingressos ficam de fora.

O painel de origem adota outro critério: utiliza o total de entradas no
registro ativo. A diferença é relevante. Em Pernambuco, em 2025, são 2.356
entradas contra 1.590 casos novos, o que leva a taxa de detecção de 24,64
para 16,63 por 100 mil habitantes — uma faixa inteira de endemicidade abaixo.

A definição do Ministério vale para os cartões, o mapa, o ranking, a
agregação regional e a série anual. Ela ainda **não** se aplica aos
indicadores de 0 a 14 anos, grau II, curas e à série mensal, porque a
extração atual não cruza essas tabelas com o modo de entrada. Esse é o
principal item do pedido de microdado em andamento.

### Curas não constituem coorte

O tratamento dura seis meses nos casos paucibacilares e doze nos
multibacilares. Em consequência, os casos diagnosticados no ano corrente
registram poucas saídas por cura, número que cresce nas extrações seguintes:
em 2025 foram 135 curas, contra 1.088 em 2024.

O indicador de cura do Ministério é construído por coorte, acompanhando os
paucibacilares diagnosticados no ano anterior e os multibacilares de dois
anos antes. Fechar a coorte exige o microdado individual.

### Observações sobre os demais

A **proporção de grau II** usa como denominador os casos com o campo de
avaliação preenchido, incluindo os registrados como "não avaliado" e
excluindo os em branco. É o mesmo denominador do painel de origem, e resulta
em 10,0% para Pernambuco em 2025 (218 de 2.171). Calculada sobre o total de
casos daria 9,3%; sobre os efetivamente avaliados, que é a regra do
Ministério, 12,0%.

A **proporção de multibacilares** exclui as notificações sem classificação
operacional, uma em 2.356 no último ano.

A fração exibida abaixo de cada cartão de proporção reproduz exatamente a
conta que gerou o percentual.

## 3. Indicadores de qualidade do programa

São os quatro indicadores de acompanhamento do tratamento que constam da
Tabela 2 do boletim estadual. Cada um aparece com os parâmetros de
classificação do Ministério ao lado.

| Indicador | Cálculo | Parâmetros |
|---|---|---|
| Proporção de cura | altas por cura ÷ saídas registradas | Bom ≥ 90% · Regular 75 a 89,9% · Precário < 75% |
| Proporção de abandono | abandonos ÷ saídas registradas | Bom < 10% · Regular 10 a 25% · Precário > 25% |
| Contatos examinados | contatos examinados ÷ contatos registrados | Bom ≥ 90% · Regular 75 a 89,9% · Precário < 75% |
| GIF avaliado no diagnóstico | casos com grau avaliado ÷ casos | Bom ≥ 90% · Regular 75 a 89,9% · Precário < 75% |

Os quatro são calculados por ano de diagnóstico, e não por coorte fechada,
pela mesma limitação descrita acima. A aproximação se mostrou próxima do
publicado. Comparação para Pernambuco em 2024:

| | painel | boletim |
|---|---:|---:|
| Proporção de cura | 67,1% | 65,0% |
| Proporção de abandono | 12,2% | 13,5% |
| Contatos examinados | 81,6% | 77,3% |
| GIF avaliado | 82,7% | 83,6% |

**Anos de coorte aberta ficam suprimidos.** Cura, abandono e contatos se
preenchem ao longo do acompanhamento. Em 2025, apenas 19% dos casos já
tinham saída de tratamento registrada, e a proporção de cura calculada sobre
esse conjunto resultaria em 30% — número que descreveria o calendário, não o
desempenho do programa. Quando a cobertura de saídas fica abaixo de 50%, os
três indicadores deixam de ser exibidos e o painel informa o motivo. O GIF
avaliado permanece, por ser campo preenchido no diagnóstico.

## 4. Agregação por região

Ao selecionar uma macrorregião ou região de saúde, o painel soma os
componentes municipais e recalcula a taxa. Não é feita média das taxas
municipais, procedimento que daria a Petrolina o mesmo peso de um município
de dois mil habitantes.

O critério vale para todos os elementos da tela: cartões, mapa, ranking,
série anual, canal endêmico, pirâmide etária, tópicos de interesse e os
gráficos de rodapé. A soma dos 185 municípios reproduz exatamente o total
estadual.

## 5. Mapa

O controle "Cores" oferece três formas de repartir os municípios:

**Endemicidade**, que é o padrão, aplica os parâmetros do Ministério da Saúde
para a taxa de detecção geral: baixa abaixo de 2, média de 2 a 10, alta de 10
a 20, muito alta de 20 a 40 e hiperendêmica a partir de 40 por 100 mil
habitantes. Para a faixa de 0 a 14 anos os cortes são 0,5, 2,5, 5 e 10. É a
única das três que mantém a régua fixa e permite comparar dois anos. A
legenda informa quantos municípios caem em cada faixa; em 2025, sete estavam
na categoria hiperendêmica.

**Quintis** reproduz a classificação do painel de origem, distribuindo um
quinto dos municípios em cada cor — 37 por classe, por construção. A régua é
recalculada a cada ano, o que impede comparação entre anos.

**Quebras naturais** agrupa municípios com valores semelhantes.

O mapa é navegável: um clique em macrorregião abre as regiões de saúde que a
compõem; um clique em região de saúde abre seus municípios; um clique em
município entra no recorte municipal. O botão "Ver Pernambuco inteiro"
retorna ao estado.

## 6. Evolução temporal

**Canal endêmico.** Compara a taxa mensal por 100 mil habitantes do ano
selecionado com a faixa interquartil dos cinco anos anteriores. O painel de
origem utiliza três anos; adotamos cinco porque a faixa fica menos sensível a
um ano atípico, como foi 2020. O filtro "Grau de incapacidade" restringe a
série a um estrato de avaliação, como na origem.

**Série anual.** Taxa de detecção por ano, de 2010 a 2025.

**Epicurva.** Casos por mês ao longo de toda a série, com janela selecionável
de 5, 10 ou 15 anos.

Canal endêmico e epicurva contam todas as entradas no registro, porque a
tabela mensal não traz o modo de entrada. A soma dos meses fica, portanto,
acima do total de casos novos do ano, e o gráfico traz essa ressalva.

## 7. Pirâmide etária

Casos por faixa etária de dez anos e sexo, em contagem absoluta ou por 100
mil habitantes da faixa. A pirâmide de curas não é oferecida: o campo vem
zerado na extração recebida.

## 8. Tópicos de interesse

Distribuição percentual das variáveis da ficha de notificação no recorte
selecionado. São dezesseis variáveis organizadas em quatro grupos, das quais
seis abrem por padrão.

Ficaram de fora as variáveis de controle do sistema, as de unidade federativa
(que são quase integralmente Pernambuco), a data de mudança de esquema
terapêutico e as de situação atual, redundantes em relação às do diagnóstico
e com preenchimento inferior.

Quando o recorte tem menos de cinco registros, o painel exibe apenas a
contagem, sem calcular percentual.

## 9. Tratamento de ano incompleto

O painel verifica quantos meses do ano têm notificação registrada, em vez de
presumir que o último ano da série está parcial. O aviso de ano incompleto
aparece somente quando faltam meses.

---

*Painel desenvolvido pela equipe Cenários+ a partir do painel Shiny da equipe
parceira. Dúvidas sobre o conteúdo deste documento devem ser encaminhadas ao
responsável técnico indicado no cabeçalho.*
