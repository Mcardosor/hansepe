# Performance — linha de base

Medido em 03/ago/2026, antes de qualquer otimização. Reproduzir com:

```bash
python -m scripts.medir_performance
```

Mediana de 5 execuções, em milissegundos, **sem** o cache do Streamlit.

| Operação | BR | UF (PE) | MUN (Recife) |
|---|---:|---:|---:|
| `incidencia` | 1,9 | 2,0 | 2,9 |
| `incidencia_0_14` | 1,4 | 1,5 | 1,9 |
| `obitos_sim` | 0,8 | 1,1 | 1,0 |
| `serie_mensal` | 1,7 | 1,9 | 2,6 |
| `casos_novos` | 1,0 | 1,1 | 1,1 |
| `piramide` | 1,8 | 2,2 | 3,5 |
| `obitos_por_faixa` | 3,6 | 3,6 | 3,6 |
| `variavel_sinan(HIV)` | 2,8 | 2,7 | 4,5 |
| `indicador_contatos` | 1,2 | 1,8 | 2,2 |
| **`kpis.calcular`** (11 KPIs) | **14,3** | **13,8** | **18,3** |

## Leitura

A poda de partição pelo caminho está funcionando: consultar um município custa
o mesmo que consultar o Brasil, na mesma ordem de grandeza, apesar de
`sinan_landing` ter 28,9 milhões de linhas.

O conjunto completo de KPIs sai em menos de 20 ms. Com `st.cache_data` por
cima, o custo por interação tende a zero em recortes já visitados.

## O que ainda não foi medido

- Renderização do mapa, que no original é o componente mais lento
- O painel de composição, que percorre 11 variáveis de `sinan_landing`
- Comportamento com vários usuários simultâneos

O alvo de tempo de resposta por interação está fixado abaixo.

## Geometria (semana 2.4)

Pré-processada uma vez por `scripts/preparar_geometria.py`, de GeoJSON gzipado
para GeoParquet simplificado. O dashboard em R simplificava **a cada
redesenho**; aqui é uma vez só, em disco.

| | Antes | Depois |
|---|---:|---:|
| Tamanho total | 133,7 MB | 3,7 MB |
| Carregar a malha de PE | 267 ms | 16 ms |
| Idem, já em cache | — | < 1 ms |

Dois ganhos independentes: **formato** (GeoParquet contra GeoJSON gzipado) e
**simplificação** (tolerância relativa à largura do bbox, como no original).

### Por que topológica

O `simplify` do shapely trata cada polígono isoladamente, então vizinhos
simplificam a divisa comum de formas diferentes e o mosaico se rompe. Medido
no ES com a tolerância do original: 1,97% da área do estado virava fresta e
163 pares de municípios passavam a se sobrepor — fiapos brancos e bordas
dobradas no coroplético. O dashboard em R tem esse defeito.

Com simplificação topológica, as arestas compartilhadas são simplificadas uma
única vez:

| | Por polígono | Topológica |
|---|---:|---:|
| Frestas (ES) | 1,97% | 0,41% |
| Erro de área (ES) | 0,470% | 0,088% |
| UFs sem nenhuma sobreposição | — | 15 de 27 |
| Pior sobreposição do país | — | 1,74 km² (MT) |

A pior sobreposição restante equivale a **0,06 pixel²** num mapa do Brasil de
800px de largura. Custa cerca de 1,5 s por UF na geração, uma vez só.

Limites monitorados em `tests/test_geo.py`.

---

## O payload do mapa — medido e corrigido em 07/ago/2026

O `GeoJsonLayer` do deck.gl recebe a geometria **embutida no JSON do
componente**. Cada renderização do mapa reenvia o mosaico inteiro ao
navegador:

| Recorte | Payload | A 10 Mbit/s |
|---|---:|---:|
| Brasil (27 UFs) | 0,85 MB | 0,7 s |
| PE (185 municípios) | 0,53 MB | 0,4 s |
| **MG (853 municípios)** | **2,76 MB** | **2,2 s** |

E não é só na primeira carga: o spec muda a cada navegação e a cada troca de
métrica — as cores fazem parte dele —, então o mosaico volta pela rede toda
vez que alguém clica.

**Por que isso importa mais do que parece.** Em `localhost` o custo é zero, e
foi em `localhost` que medimos os 754 ms que hoje sustentam a comparação com
o painel em R. Sobre uma rede real, MG sozinho gasta mais tempo transferindo
mapa do que o round-trip inteiro que medimos no painel deles. A meta de
performance pode evaporar exatamente no recorte mais pesado, e nenhum teste
local mostraria isso.

**Resolvido em 07/ago/2026 — era indentação.**

O `pydeck.serialize` chama `json.dumps(..., indent=2)`, e o
`st.pydeck_chart` envia ao navegador exatamente o que `to_json()` devolver.
Com a geometria aninhada em listas de coordenadas, cada número ganhava sua
linha e seu recuo. **Três quartos do que trafegava era espaço em branco.**

| Recorte | Antes | Depois | |
|---|---:|---:|---:|
| Brasil (27 UFs) | 0,85 MB | 0,19 MB | −78% |
| PE (185 municípios) | 0,53 MB | 0,14 MB | −73% |
| MG (853 municípios) | 2,76 MB | 0,71 MB | −74% |

Sem mudar um pixel: mesma malha, mesma precisão, mesmas cores. O ajuste está
em `mapa._compactar`, e `tests/test_mapa.py` prende o teto em 1 MB para MG.

Vale registrar como quase passou batido. Medi o payload achando que ia
justificar simplificar mais a malha; o GeoJSON cru de MG tinha 0,63 MB contra
2,76 MB do payload, e foi essa diferença de 4,4× que denunciou o problema.
Se eu tivesse ido direto simplificar geometria, teria degradado o mapa para
ganhar uma fração do que a formatação estava custando.

**Medido e descartado:** reduzir a precisão das coordenadas. Hoje são 7 casas
decimais, cerca de 1 cm. A 5 casas o payload de MG cai para 0,66 MB e a 4
casas para 0,62 MB — 7% e 13%. Não compensa o custo de processar a cada
renderização nem o de regerar a malha, e o teto de 1 MB já tem folga.

**Caminhos que restam, se o teto apertar:**

1. Simplificar mais a malha nos níveis com muitos polígonos — hoje a
   tolerância é a mesma para 27 UFs e para 853 municípios.
2. Servir a geometria uma vez e mandar só as cores nas renderizações
   seguintes. É o ganho grande e a mudança maior: exige separar geometria de
   dado no componente.

Nenhuma das duas é necessária hoje. O que continua valendo é medir pela rede
depois do deploy: 0,71 MB por navegação ainda é o maior item isolado do que
trafega, e localhost não cobra por isso.

---

## Perfil do servidor — medido em 08/ago/2026

Com o payload já resolvido, restava saber onde o tempo é gasto **antes** de a
resposta sair. Medido com cache quente, média de três execuções:

| Etapa | Brasil | MG (853 mun) |
|---|---:|---:|
| `kpis.calcular` | 13,2 ms | 13,6 ms |
| `composicao` | 6,5 ms | 6,5 ms |
| `piramide_completa` | 6,3 ms | 6,9 ms |
| `ranking` | 3,6 ms | 7,6 ms |
| `serie_mensal` | 3,0 ms | 3,1 ms |
| `indicadores_programa` | 2,3 ms | 3,7 ms |
| `valores_por_geografia` | 1,7 ms | 2,3 ms |
| **soma das leituras** | **~37 ms** | **~44 ms** |
| **`mapa.deck()`** | **50,7 ms** | **112,5 ms** |

**A camada de dados não é o gargalo.** Nenhuma leitura passa de 14 ms — o
DuckDB sobre parquet particionado entrega o que prometia. O item mais caro era
montar o mapa, e dentro dele **75,6 ms eram converter a malha para GeoJSON**,
trabalho idêntico repetido a cada renderização: a geometria não muda quando o
usuário troca de métrica ou de ano.

**Correção:** a geometria convertida passa a ser guardada por recorte, em
`mapa._geometrias`. Só a geometria — propriedade carrega cor e valor, que
mudam a cada interação, e cachear junto serviria mapa velho.

| | Antes | Depois |
|---|---:|---:|
| `mapa.deck()` em MG | 110,8 ms | **39,2 ms** |

De quebra o payload encolheu de novo: sem passar pelo `__geo_interface__`
completo, somem os campos `bbox` e `id` que ele acrescenta por feição e que o
deck.gl não usa.

### O que isso diz sobre a meta de performance

Somando, o servidor gasta hoje cerca de **80 ms** por navegação em MG — 44 ms
de leitura e 39 ms de mapa. A medição ponta a ponta em localhost deu 754 ms.

A diferença, aproximadamente **670 ms, é overhead do próprio Streamlit**:
reexecução do script, diferença de árvore de widgets, WebSocket e renderização
no navegador. Não é dado, não é DuckDB, não é geometria.

Isso delimita o alvo realista: dá para melhorar o que é nosso, e o que é nosso
já custa 10% do total. Perseguir os outros 90% significaria trocar de
framework, o que não está em discussão.

---

# Alvo de tempo de resposta

Fixado em 23/ago/2026, com mapa e gráficos prontos. Medido nesta máquina, com
os parquets em disco local.

| Orçamento | Alvo | Medido | Onde é preso |
|---|---:|---:|---|
| **Servidor**, por interação, pior recorte | ≤ 300 ms | **270 ms** (MG) | `tests/test_performance.py` |
| **Payload do mapa**, pior recorte | ≤ 1,0 MB | **0,71 MB** (MG) | `tests/test_mapa.py` |
| **Percebido**, rede local | ≤ 1,5 s | **1,0 s** | não testável — ver abaixo |

"Interação" é o trabalho completo de uma troca de recorte ou de métrica: os
KPIs do ano e do anterior, o mapa, o ranking, a série, a pirâmide, a
composição e os indicadores.

## Por que o alvo tem três linhas e não uma

Só as duas primeiras são nossas. A terceira depende da máquina do usuário e da
rede, e um teste que a medisse falharia por motivo alheio ao código — vira
ruído e acaba desligado.

Os dois orçamentos que controlamos são justamente os que **causam** a terceira,
e por isso são o que os testes prendem.

## O que a medição do percebido mostrou

Trocar a métrica no mapa do Brasil leva **1,00 s** de mediana, e em Minas
Gerais leva **1,00 s** também — apesar de MG transferir 0,71 MB contra 0,19 do
Brasil. Em `localhost` o payload é gratuito, e essa é exatamente a armadilha
que este documento já registrava: **medir localmente esconde o custo de rede**.
Num enlace de 10 Mbit/s, o meio megabyte a mais de MG acrescenta cerca de
0,6 s, e o pior caso vai a ~1,6 s.

Dos 1,00 s medidos, **cerca de 160 ms são nossos**. O resto é o ciclo de rerun
do Streamlit mais o redesenho de cinco painéis no navegador — deck.gl
reconstruindo a cena WebGL e o Vega remontando quatro gráficos.

Vale registrar como o alvo **não** foi medido. A primeira tentativa cronometrou
o indicador de execução do Streamlit e deu ~2 s; a mesma medição dava ~2 s
também para arrastar o slider do ranking, que só redesenha o ranking dentro de
um fragmento. Duas interações de custo muito diferente com o mesmo número é
sinal de que se está medindo o instrumento. O número acima vem de esperar a
**mudança de conteúdo** — o título do ranking passando a nomear a nova métrica.

## O que já foi ganho depois da linha de base

**Leitura duplicada nos KPIs, 23/ago.** A contagem de desfechos entrou lendo
`SITUA_ENCE` por conta própria, sem saber que a interrupção já lia. O conjunto
de KPIs pagava duas idas ao `sinan_landing` pelo mesmo dado. Corrigido lendo
uma vez e emprestando:

| Recorte | Antes | Depois | |
|---|---:|---:|---:|
| Brasil | 23,3 ms | 18,3 ms | −21% |
| PE | 24,3 ms | 19,4 ms | −20% |
| Recife | 31,4 ms | 23,5 ms | −25% |

Não quebrou nada e não apareceu em teste nenhum, porque duplicar leitura não
muda resultado — só custo. `test_calcular_nao_le_a_mesma_variavel_duas_vezes`
existe para a próxima não passar despercebida.
