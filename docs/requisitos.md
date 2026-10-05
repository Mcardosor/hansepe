# Requisitos técnicos e origem dos dados

**Painel de Monitoramento da Hanseníase — Pernambuco**

| | |
|---|---|
| Destinatário | Secretaria Estadual de Saúde de Pernambuco |
| Versão | 1.0 |
| Última revisão | outubro de 2026 |
| Responsável técnico | *(preencher)* |

---

## Requisitos de máquina

O painel é leve. Ele não usa banco de dados, não consulta nada pela internet
enquanto roda e lê arquivos que ficam no próprio disco.

### Para quem só vai usar

Basta um navegador. O painel abre em <https://cenarios.unb.br/cenarios/hansepe/>
e funciona em qualquer computador dos últimos dez anos.

| | |
|---|---|
| Navegador | Chrome, Edge, Firefox ou Safari, versão dos últimos dois anos |
| Tela | a partir de 1366 × 768; abaixo disso os gráficos ficam apertados |
| Internet | 5 Mbps são suficientes |
| Placa de vídeo | qualquer uma. O mapa usa aceleração gráfica quando existe, e cai para desenho comum quando não existe |

### Para rodar o painel no servidor

Medido no container em produção, com o painel no ar.

| | Mínimo | Confortável |
|---|---|---|
| Processador | 1 núcleo | 2 núcleos |
| Memória | 512 MB | 1,5 GB |
| Disco | 350 MB | 1 GB |
| Sistema | Linux com Docker | Linux com Docker |

Na prática o container ocupa **46 MB de memória** e fica em 0,4% de CPU
atendendo. O limite de 1,5 GB existe como folga para picos, não porque ele
precise. Do disco, 260 MB são a imagem Docker e 47 MB são os dados.

O painel responde em milissegundos porque tudo está em disco local: não há
espera de rede nem de banco.

### Para desenvolver

| | |
|---|---|
| Python | 3.13 |
| Bibliotecas | Streamlit, DuckDB, PyArrow, pandas (lista em `requirements.txt`) |
| Memória | 4 GB |
| Disco | 500 MB, com os dados |

```bash
pip install -r requirements.txt
streamlit run app.py     # abre em http://localhost:8501
pytest                   # 438 testes, cerca de 45 segundos
```

GeoPandas, Shapely e TopoJSON aparecem na lista de bibliotecas, mas só são
usados para preparar a malha dos municípios uma vez. O painel no ar não
precisa deles.

---

## De onde vêm os números

**Fonte:** SINAN, do Ministério da Saúde, na extração agregada que a equipe
parceira prepara. População do IBGE. A divisão do estado em macrorregiões e
regiões de saúde vem da SES-PE.

Não há dado de paciente no projeto. Tudo chega já somado por município, ano e
categoria.

O painel abre seis conjuntos de arquivos:

| Arquivo | O que tem | O que alimenta na tela |
|---|---|---|
| `incidence` | casos, curas, população e graus de incapacidade por município e ano | os cards do topo, o mapa e o ranking |
| `incidence_0_14` | o mesmo para menores de 15 anos | o card e o gráfico de 0 a 14 |
| `sinan_landing` | as respostas da ficha de notificação, já contadas | casos novos, contatos, cura, abandono e os tópicos |
| `_cache_ts` | casos mês a mês | o canal endêmico e a epicurva |
| `piramides` | casos por sexo e faixa etária | a pirâmide |
| `sinan_dict` | o nome de cada código | os rótulos das categorias |

Mais a malha dos 185 municípios e a tabela que liga município a região de
saúde.

### Os campos da ficha que usamos

| Campo | Para quê |
|---|---|
| `MODOENTR` | separar **caso novo** de recidiva e transferência — é a base de todos os coeficientes |
| `TPALTA_N` | cura e abandono de tratamento |
| `CONTREG` e `CONTEXAM` | contatos registrados e examinados |
| `CLASSOPERA` | multibacilar ou paucibacilar |
| `FORMACLINI` | forma clínica |
| `AVALIA_N` | grau de incapacidade no diagnóstico |
| `MODODETECT` | como o caso foi encontrado |
| `CS_RACA`, `CS_ESCOL_N`, `CS_GESTANT` | perfil dos casos |
| `BACILOSCOP`, `NERVOSAFET`, `EPIS_RACIO`, `ESQ_INI_N`, `DOSE_RECEB` | disponíveis no seletor de tópicos |

Como cada indicador é calculado está em `metodologia.md`. Onde o nosso número
difere do painel da equipe parceira ou do boletim da SES-PE, e por quê, está
em `paridade-hanseniase.md`.

---

## Como os dados chegam até aqui

Nada é baixado enquanto o painel roda. Os arquivos são copiados uma vez e
ficam no disco.

O caminho é este:

1. A equipe parceira publica a extração agregada do SINAN.
2. Ela entra no acervo do painel nacional, que tem todas as doenças e pesa
   cerca de 240 MB.
3. Um script copia de lá só a parte de hanseníase, cerca de 47 MB, para a pasta
   `data/` deste projeto.

```bash
python -m scripts.extrair_dados_hanseniase
```

Até setembro de 2026 o painel apontava direto para o acervo compartilhado.
Passou a ter cópia própria para ficar **independente**: mexer nos dados daqui
não afeta os outros painéis, e a entrega não depende de o painel nacional
estar na mesma máquina.

**Atenção:** como é cópia, ela não se atualiza sozinha. Quando a equipe
parceira publicar uma extração nova, é preciso rodar o script de novo — aqui e
no servidor. O arquivo `data/PROCEDENCIA.json` registra de onde veio e quando.

### Como o painel lê

Os arquivos são lidos direto do disco pelo DuckDB, sem carregar nada para um
banco. Cada pasta guarda um recorte — doença, nível geográfico, ano — e a
consulta abre só as pastas de que precisa. É isso que faz o painel responder
instantaneamente mesmo com milhões de linhas disponíveis.

O detalhe técnico de como as pastas são organizadas, e os cuidados na leitura,
estão em `contrato-dados.md`.
