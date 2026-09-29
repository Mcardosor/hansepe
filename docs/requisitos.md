# Requisitos, dados e como os parquets chegam — Pernambuco

Três perguntas que sempre voltam: **o que é preciso para rodar**, **de onde
saem os números** e **como os parquets chegam aqui**. O contrato completo dos
datasets, com as armadilhas, está em `contrato-dados.md`; este arquivo é o
recorte de Pernambuco.

---

## 1. Requisitos para rodar

### Máquina

| | |
|---|---|
| Python | 3.13 (usamos o `.venv` do painel nacional: `../sinan/.venv`) |
| Dependências | `requirements.txt` — Streamlit ≥ 1.40, DuckDB ≥ 1.1, PyArrow ≥ 16, pandas ≥ 2.2; GeoPandas, Shapely e TopoJSON só para o pré-processo da malha |
| Dados | `data/`, 44 MB (§3) — **não versionado** |
| Banco de dados | nenhum. O painel lê parquet do disco; não há servidor, não há VPN |
| Rede | nenhuma em execução. Os componentes de mapa e gráfico trazem `deck.gl` e `ECharts` embutidos, sem CDN |

```bash
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8501
pytest                        # ~420 testes, ~25 s
```

### Variáveis de ambiente

| Variável | Para que serve | Padrão |
|---|---|---|
| `SINAN_DATA_DIR` | raiz dos dados | `./data` |
| `SINAN_DOENCA` | qual pacote de doença carregar | `hanseniase` |
| `DADOS` | o que o Docker monta em `/app/data` | `./data` |

### Container

```bash
docker compose up -d --build   # porta 8510, /cenarios/hansepe/
```

A imagem não carrega dados: eles entram como volume somente leitura. Ver
`deploy.md`.

---

## 2. Quais bases e quais colunas

**Fonte:** SINAN/Ministério da Saúde, na extração agregada da equipe parceira.
População do IBGE. Hierarquia geográfica (macrorregiões e regiões de saúde) da
SES-PE. **Nenhum dado nominal entra no projeto** — tudo já vem agregado.

O painel abre seis datasets. Em cada um, só as partições `doenca=HANS` ou
`doenca=HANSENIASE` (o código muda de dataset para dataset — armadilha 2 do
`contrato-dados.md`).

| Dataset | Partições | Colunas que usamos | Alimenta |
|---|---|---|---|
| `incidence` | `doenca/nivel/ano` | `cod_mun6`, `nome_mun`, `uf`, `casos_total`, `casos_cura`, `pop_total`, `incid_100k_total`, `casos_grau_0`, `casos_grau_I`, `casos_grau_II`, `casos_nao_avaliado` | cards, mapa, ranking, grau II, GIF avaliado |
| `incidence_0_14` | `doenca/nivel/ano` | `casos_0_14_total`, `pop_0_14_total`, `incid_0_14_100k_total` | cards e gráfico de menores de 15 |
| `sinan_landing` | `doenca/nivel/ano` | `variavel`, `valor`, `valor_lbl`, `n`, `sexo`, `geo_id`, `uf` | casos novos (`MODOENTR`), tópicos, contatos, cura e abandono |
| `_cache_ts` | `nivel/doenca/ano` | `mes`, `casos`, `casos_cura`, `pop_total`, `incid_100k`, `avalia_n` | canal endêmico e epicurva |
| `piramides` | `nivel/tipo/doenca/ano` | `faixa_etaria`, `sexo`, `valor`, `pop` | pirâmide etária |
| `sinan_dict` | `doenca` | código → rótulo | nomes das categorias nos tópicos |

Mais `geo/` (malha dos 185 municípios) e `support/` (lookup de municípios e a
hierarquia da SES-PE).

### As variáveis do SINAN que lemos

Do `sinan_landing`, em formato longo (`variavel`, `valor`, `n`):

| Variável | Para quê |
|---|---|
| `MODOENTR` | **casos novos** pela definição do MS (`= 1`) — a base de tudo |
| `CLASSOPERA` | multibacilar / paucibacilar |
| `FORMACLINI` | forma clínica |
| `AVALIA_N` | grau de incapacidade no diagnóstico |
| `MODODETECT` | modo de detecção |
| `TPALTA_N` | saída do tratamento → cura (`= 1`) e abandono (`= 7`) |
| `CONTREG`, `CONTEXAM` | contatos registrados e examinados (o valor **é** a quantidade, não um código) |
| `CS_RACA`, `CS_ESCOL_N`, `CS_GESTANT` | perfil |
| `BACILOSCOP`, `NERVOSAFET`, `EPIS_RACIO`, `ESQ_INI_N`, `DOSE_RECEB` | no seletor de tópicos |

Os **filtros de sempre**: `sexo = 'TOTAL'` (a linha TOTAL já soma M, F e I —
somar tudo dobra a contagem) e `trim(valor)`, porque o código vem com espaço à
esquerda. As duas armadilhas estão no `contrato-dados.md`.

### Como o número vira indicador

As fórmulas, com numerador e denominador, estão em `metodologia.md`; onde
divergimos do painel de origem ou do Ministério, em `paridade-hanseniase.md`.

---

## 3. Como os parquets chegam

**Não há download em tempo de execução.** O painel lê arquivos locais, e é por
isso que responde em milissegundos e funciona sem VPN.

O caminho é:

1. A **equipe parceira** publica a extração agregada do SINAN.
2. Ela é carregada no lago do painel nacional (`../sinan/data`, ou
   `~/dashboard-sinan-pe/data` na VM): todas as doenças, 200–240 MB.
3. `scripts/extrair_dados_hanseniase.py` copia de lá **só o que este painel
   abre** — as partições de hanseníase dos seis datasets acima, mais `geo/` e
   `support/` — para o `data/` do projeto. São 44 MB.

```bash
python -m scripts.extrair_dados_hanseniase                          # de ../sinan/data
python -m scripts.extrair_dados_hanseniase --origem ~/dashboard-sinan-pe/data
```

Até 29/set/2026 o `data/` era um atalho para o lago inteiro. Passou a ser
pasta própria para que o painel fosse **independente**: mexer nos dados daqui
não afeta o sinan, o tbpe nem o RecifeTB, e a entrega não depende de o painel
nacional estar na mesma máquina.

> **É cópia, e cópia envelhece.** Quando a extração do SINAN for atualizada, é
> preciso rodar o script de novo — aqui e na VM. `data/PROCEDENCIA.json` grava
> de onde veio, quando e o tamanho de cada dataset.

### Como a consulta lê

DuckDB em memória, lendo o parquet direto, sem carregar nada para um banco:

```sql
SELECT cod_mun6, casos_total
FROM read_parquet('…/incidence/doenca=HANSENIASE/nivel=MUN/ano=2025/*.parquet',
                  hive_partitioning=true)
WHERE uf = 'PE'
```

A partição entra **no caminho**, não no `WHERE`. Não é só performance: um glob
da raiz une arquivos de esquemas diferentes — os de `nivel=BR` não têm a
coluna `uf` —, e o DuckDB resolve a união pelo esquema do primeiro arquivo,
fazendo sumir colunas que existem nos demais. A ordem das partições muda de
dataset para dataset e está declarada em `src/data/conexao.py`.
