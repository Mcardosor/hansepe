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
| `canal.epicurva` (10 anos) | 93 | 125 | 101 |
| `canal.montar` | 61 | 86 | 67 |
| `serie_qualidade` (Gráficos 10–13) | 37 | 74 | 50 |
| `ranking` | 16 | 16 | 15 |
| `serie_classificacao_operacional` | 15 | 30 | 22 |
| `piramide_completa` | 13 | 16 | 14 |
| `valores_por_geografia` (o mapa) | 11 | 11 | 11 |
| `composicao` (um tópico) | 9 | 14 | 10 |
| `serie_0_14` | 8 | 17 | 9 |
| `casos_novos_ms` | 5 | 10 | 7 |
| **soma dos leitores** | **267** | **398** | **306** |
| `kpis.calcular` (os 7 cards) | 39 | 60 | 46 |

Somar a coluna superestima o que o usuário espera: os leitores são cacheados
separadamente, e um clique no mapa não invalida todos. Mas serve de teto — e
no recorte por macrorregião ele **passa dos 300 ms**.

## O que pesa, e por quê

**As duas vistas mensais custam metade do orçamento.** `canal.montar` e
`canal.epicurva` somam 154 ms em PE e 211 ms numa macrorregião — mais que
todos os outros leitores juntos. A razão é estrutural: as duas montam a série
ano a ano, uma consulta por ano, sobre o `_cache_ts`, que é o dataset mais
granular que temos.

A janela de 5, 10 ou 15 anos, que entrou em 28/set, é o que segura esse custo:
em 15 anos a epicurva custaria metade a mais que em 10.

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
