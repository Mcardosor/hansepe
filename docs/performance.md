# Performance

Medido em 29/set/2026, com hanseníase, no `data/` deste painel. Reproduzir com:

```bash
python -m scripts.medir_performance
```

Antes deste dia o arquivo trazia medições do painel nacional — dengue e
tuberculose, em outra máquina. Estas são nossas.

## O alvo

**300 ms por interação.** É o tempo entre o clique e a tela nova: abaixo disso
a resposta é percebida como imediata, e acima começa a parecer que travou.

O alvo vale para a **primeira** vez. O `st.cache_data` guarda cada leitura por
24 horas, então repetir o mesmo recorte custa quase nada — o número que
interessa é o do usuário que clica num município pela primeira vez.

## Quanto custa cada leitura

Mediana de cinco execuções, em milissegundos, sem o cache do Streamlit. Três
recortes: o estado, uma macrorregião e um município.

| Operação | PE | macrorregião | Recife |
|---|---:|---:|---:|
| `canal.montar` | 61 | 86 | 67 |
| `canal.epicurva` (10 anos) | **29** | **38** | **30** |
| `serie_qualidade` (Gráficos 10–13) | 37 | 74 | 50 |
| `ranking` | 16 | 16 | 15 |
| `serie_classificacao_operacional` | 15 | 30 | 22 |
| `piramide_completa` | 13 | 16 | 14 |
| `valores_por_geografia` (o mapa) | 11 | 11 | 11 |
| `composicao` (um tópico) | 9 | 14 | 10 |
| `serie_0_14` | 8 | 17 | 9 |
| `casos_novos_ms` | 5 | 10 | 7 |
| **soma dos leitores** | **203** | **311** | **235** |
| `kpis.calcular` (os 7 cards) | 39 | 60 | 46 |

A linha da epicurva já é a de depois da otimização de 30/set (abaixo); as
demais são de 29/set. Somar a coluna superestima o que o usuário espera — os
leitores são cacheados separadamente, e um clique no mapa não invalida todos —,
mas serve de teto, e agora ele cabe nos 300 ms em PE e no município.

## A epicurva numa consulta só — 30/set/2026

Ela montava a série **ano a ano**, e cada ano custava duas leituras do
`_cache_ts` (uma para casos, outra para incidência) mais duas do `incidence`
quando o recorte é uma região. Dez anos numa macrorregião eram quarenta
consultas para desenhar uma linha de contagem.

Agora é uma consulta: a partição `ano` fica fora do caminho, o glob pega todos
os anos e o `WHERE` recorta o intervalo. E só `casos` — a epicurva desenha
contagem, e trazer população para calcular uma incidência que ninguém usa era
metade do custo.

Medido alternando as duas implementações **no mesmo processo**, que é o que
torna a comparação honesta: a máquina varia de carga ao longo do dia, e medir
uma de manhã e a outra à tarde compara o computador, não o código.

| recorte | antes | depois | ganho |
|---|---:|---:|---:|
| PE | 201 ms | **29 ms** | 85% |
| macrorregião | 275 ms | **38 ms** | 86% |
| município | 217 ms | **30 ms** | 86% |

`tests/test_performance.py` compara mês a mês as duas contas: trocar um laço
por consulta agregada é o tipo de mudança que acerta o total e erra a
distribuição sem ninguém ver.

É a exceção à regra de podar pela partição (`contrato-dados.md`): vale porque
o que se lê é justamente a série inteira, e os arquivos de um mesmo nível têm
o mesmo esquema.

## O que pesa, e por quê

**O canal endêmico é agora o item mais caro**, com 61 ms em PE e 86 numa
macrorregião. Ele monta a série dos cinco anos de referência mais o corrente,
um ano por consulta, e precisa da **incidência** — não só da contagem —, então
a mesma otimização da epicurva não se aplica de graça: exigiria trazer a
população de todos os anos junto e recalcular a taxa, o que mexe em número na
tela e pede conferência.

A janela de 5, 10 ou 15 anos, que entrou em 28/set, continua segurando o custo
da epicurva: ela é linear no número de anos mesmo depois da otimização.

Vale registrar a ironia: esses dois gráficos são os que menos dizem sobre
hanseníase — o mês de notificação é a agenda do serviço, não a doença, porque
a incubação leva de dois a sete anos. São o que há de mais caro pelo que menos
informa. Está em `revisao-graficos.md`, à espera de decisão.

**A macrorregião é o pior recorte, não o município.** Ela lê a partição `MUN`
com uma lista de municípios no `IN (...)`, então paga por vários onde o estado
paga por um agregado pronto. É o preço de o escopo atravessar a tela inteira,
que é justamente o que o painel de origem não faz.

## O mapa

| | |
|---|---|
| Payload de PE, 185 municípios | **0,12 MB** |
| Montar o `deck` (geometria + cores + tooltip) | 201 ms |
| Carregar a malha do disco | 40 ms na primeira vez, 14 depois |

O teto de payload está preso em 1 MB por `tests/test_mapa.py`. Com 0,12 MB há
folga de oito vezes — a malha já vem simplificada e as coordenadas
arredondadas, e é isso que mantém o número baixo.

Os 201 ms de montagem acontecem **uma vez por recorte** e ficam em cache. O
clique que só muda a cor — trocar de métrica, clicar numa faixa da legenda —
não paga isso: o componente interpola a cor no navegador, sem refazer o deck.

## O que a suíte prende

`tests/test_performance.py` guarda duas regras que já foram quebradas uma vez:

- **Nenhuma variável do SINAN é lida duas vezes no mesmo `kpis.calcular`.** Já
  aconteceu de dois indicadores lerem o mesmo dado sem saber um do outro, e o
  conjunto pagar duas vezes.
- **O teto de payload do mapa continua existindo**, com valor abaixo de 1 MB.

Nenhuma das duas mede tempo: tempo varia com a máquina e o teste falharia por
motivo errado. Elas prendem a *estrutura* que mantém o tempo baixo.

## O que não foi medido

- Vários usuários simultâneos.
- O tempo de renderização no navegador, separado do tempo de servidor.
