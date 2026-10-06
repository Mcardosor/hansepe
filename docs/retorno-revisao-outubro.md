# Retorno à revisão de outubro

Resposta ponto a ponto ao documento enviado pela equipe parceira.
Os ajustes já publicados estão em <https://painel.cenarios.unb.br/cenarios/hansepe/>.

---

Rafaela, obrigado pela revisão — foi detalhada e rendeu bastante. Sete dos
dez pontos já estão no ar. Três dependem de uma decisão sua, e dois de uma
informação que só a equipe que gera a extração pode dar. Respondo na ordem
do seu documento.

## O que já está no painel

**1. "Taxa de detecção" nos cards.** Os dois cards passaram a se chamar
"Taxa de detecção" e "Taxa de detecção 0–14". Você tem razão: ao lado de
"Casos novos", o nome "Detecção" era ambíguo, porque os dois falam de
detecção e só um é taxa. Os botões de seleção continuam com o nome curto,
senão os cinco não cabem numa linha.

**3. Número absoluto na legenda do mapa.** A legenda agora diz "Número de
casos novos", "Número de curas" e "Número de casos de 0 a 14 anos". E
"Municípios por faixa" ficou entre parênteses, como você sugeriu, para
amarrar com as faixas logo abaixo.

**5. A palavra "proporção".** Contatos examinados e GIF avaliado passaram a
ser "Proporção de contatos examinados" e "Proporção de GIF avaliado no
diagnóstico". Cura e abandono já tinham.

**8. Pirâmide etária.** O seletor agora se chama "Taxa de detecção por 100
mil habitantes", e o ícone de interrogação traz a fórmula: casos da faixa
etária dividido pela população da mesma faixa, vezes 100.000.

**9. Período analisado.** Cada gráfico de tópicos passou a trazer o recorte
e o ano no título, assim: "Proporção de casos segundo forma clínica — PE,
2024". É sempre um ano por vez, nunca a série inteira. Acrescentei também o
território, porque o gráfico muda quando se seleciona um município e a mesma
dúvida apareceria.

## O ponto 4 era um defeito, e maior do que apareceu

Você apontou que a opção "Endemicidade" altera números e cores quando a
métrica é "Curas", e que ela deveria valer só para detecção. Está correto, e
ao investigar encontramos três situações diferentes:

Com **Curas** e **Casos 0–14** não existe régua de endemicidade nenhuma. O
mapa classificava por quebras naturais enquanto o botão continuava marcado
como "Endemicidade". Quem olhasse acreditaria estar vendo a régua oficial.

Com **Casos novos** existiam faixas, mas de contagem: menos de 5, de 5 a 10,
de 10 a 25. Endemicidade é conceito de taxa e não se aplica a contagem
bruta, então o nome estava errado.

Com as **duas taxas de detecção** a régua oficial sempre funcionou, incluindo
a de menores de 15 anos que você sugeriu incluir. Ela já existia — o defeito
é que o botão parecia funcionar em tudo, e isso escondia que nas duas certas
ele estava certo.

A opção agora só aparece nas duas taxas de detecção. Nas demais métricas o
mapa usa quebras naturais, e o botão não promete o que não entrega.

## Três pontos que dependem de decisão sua

**1. A cor do card de Curas.** Nos painéis da família, verde marca desfecho
favorável e ocre marca dano — é por isso que Curas destoa dos outros. Como a
convenção não se leu sozinha, vale decidir: explicamos no ícone de ajuda,
tiramos o verde e deixamos a cor só na seta de variação, ou mantemos como
está? Vale notar que a mudança afetaria também os painéis de tuberculose,
que seguem a mesma convenção.

**2. A seta do multibacilar.** Você diz que a redução de MB é um dado
positivo e deveria aparecer em verde. Concordamos, e há um argumento a favor
no próprio painel: o grau II já está configurado como "melhora quando cai", e
o multibacilar não. Os dois medem gravidade no diagnóstico, então a
inconsistência é nossa. Confirma que podemos inverter?

**4. As faixas de contagem de casos novos.** Elas foram retiradas do botão
"Endemicidade", mas continuam disponíveis no código. São úteis para repartir
o mapa quando a métrica é contagem. Interessa mantê-las sob outro nome, algo
como "Faixas de casos", ou preferem que o mapa use só quebras naturais e
quintis nessas métricas?

## Dois pontos que precisam da equipe de extração

**7. Os eixos da epicurva.** O eixo vertical passa a ser "Número de casos",
sem dúvida. O horizontal depende de uma informação que não temos: **o ano da
nossa extração é o de notificação ou o de diagnóstico?** Procuramos na
documentação que recebemos e não está declarado.

Isso vai além do rótulo do eixo. A escolha muda a interpretação de todos os
números anuais do painel, inclusive os que já conferimos contra o boletim.
Preferimos deixar o eixo sem nome a escrever o nome errado.

**10. A totalidade dos casos na base do cálculo.** Faz sentido mostrar o
total ao lado dos casos com o campo preenchido — fica visível o quanto o
campo está incompleto. Só precisamos saber qual total você tem em mente:
todos os casos do ano, ou apenas os casos novos? Em 2024 são números
diferentes, 2.466 contra 1.761.

---

Assim que tivermos as três decisões e as duas respostas, fechamos os pontos
restantes. Os sete já publicados podem ser conferidos no endereço acima.
