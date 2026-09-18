"""Conexão DuckDB e resolução de caminhos dos datasets.

A conexão é única por processo. No Streamlit, envolver em ``st.cache_resource``.
Fora dele (testes, scripts), o ``lru_cache`` já garante instância única.

Nenhum dado é copiado para dentro do DuckDB: tudo é lido direto dos parquets
via ``read_parquet``, com pushdown do filtro de partição.
"""

from __future__ import annotations

from functools import lru_cache

import duckdb

from . import config


@lru_cache(maxsize=1)
def conectar() -> duckdb.DuckDBPyConnection:
    """Conexão DuckDB em memória, única por processo."""
    con = duckdb.connect(database=":memory:")
    con.execute("SET enable_progress_bar = false")
    return con


#: Ordem das partições em disco, por dataset. Não é uniforme: ``incidence`` é
#: ``doenca/nivel/ano`` e ``cache_ts_sim_obitos`` é ``nivel/doenca/ano``.
#: ``obitos_sim_faixa``, apesar de também vir do SIM, segue a ordem do primeiro.
PARTICOES: dict[str, tuple[str, ...]] = {
    "incidence": ("doenca", "nivel", "ano"),
    "incidence_0_14": ("doenca", "nivel", "ano"),
    "sinan_landing": ("doenca", "nivel", "ano"),
    "obitos_sim_faixa": ("doenca", "nivel", "ano"),
    "_cache_ts": ("nivel", "doenca", "ano"),
    "cache_ts_sim_obitos": ("nivel", "doenca", "ano"),
    "piramides": ("nivel", "tipo", "doenca", "ano"),
    "cases_new": ("doenca", "ano"),
    "sinan_dict": ("doenca",),
    "indicadores_tb_contatos": (),
    "indicadores_tb_cultura_retratamento": (),
}


#: Datasets cujo diretório contém arquivos de **esquemas diferentes**. Ler o
#: diretório inteiro adota o esquema do primeiro arquivo e descarta colunas dos
#: demais, em silêncio. Aqui é preciso nomear o arquivo em :func:`caminho`.
ARQUIVOS_HETEROGENEOS = {
    "indicadores_tb_contatos": ("por_ano.parquet", "por_ano_geo.parquet"),
    "indicadores_tb_cultura_retratamento": ("por_ano.parquet", "por_ano_geo.parquet"),
}


class ParticaoAusente(FileNotFoundError):
    """A partição pedida não existe, mas o dataset sim.

    Quase sempre é ano ainda não consolidado, não erro de configuração: o SIM
    fecha bem depois do SINAN, então `cache_ts_sim_obitos` e `obitos_sim_faixa`
    ficam um ano atrás de `incidence` o tempo todo. Quem consulta uma fonte
    sujeita a essa defasagem trata isto como ausência de dado; os demais deixam
    subir, porque aí é mesmo defeito.

    Distinta de `FileNotFoundError` de dataset inexistente — aquele é
    configuração errada e precisa gritar.
    """


def caminho(dataset: str, arquivo: str | None = None, **particoes) -> str:
    """Glob dos parquets de um dataset, podando partições pelo caminho.

    Podar pelo caminho em vez de filtrar no ``WHERE`` não é só performance: um
    glob da raiz une arquivos de esquemas diferentes — os de ``nivel=BR`` não
    têm a coluna ``uf`` — e o DuckDB resolve a união pelo esquema do primeiro
    arquivo, fazendo sumir colunas que existem nos demais.

    As partições são consumidas na ordem declarada em :data:`PARTICOES` e
    param na primeira ausente, já que não dá para pular um nível de caminho.
    """
    base = config.dashboard_dir() / dataset
    if not base.is_dir():
        raise FileNotFoundError(
            f"Dataset '{dataset}' não encontrado em {base}.\n"
            f"Confira SINAN_DATA_DIR ou veja docs/contrato-dados.md."
        )

    if dataset not in PARTICOES:
        raise KeyError(f"Dataset '{dataset}' sem ordem de partição declarada.")

    desconhecidas = set(particoes) - set(PARTICOES[dataset])
    if desconhecidas:
        raise KeyError(
            f"Partições inexistentes em '{dataset}': {sorted(desconhecidas)}. "
            f"Disponíveis: {list(PARTICOES[dataset])}."
        )

    for chave in PARTICOES[dataset]:
        valor = particoes.get(chave)
        if valor is None:
            break
        base = base / f"{chave}={valor}"

    # Sem isto o DuckDB devolve `IOException: No files found that match the
    # pattern`, que não distingue ano não consolidado de caminho errado — e
    # derrubava a página inteira ao mover o slider para 2025.
    if particoes and not base.is_dir():
        raise ParticaoAusente(
            f"Dataset '{dataset}' não tem a partição {particoes}: {base} não existe."
        )

    esperados = ARQUIVOS_HETEROGENEOS.get(dataset)
    if esperados:
        if arquivo is None:
            raise ValueError(
                f"'{dataset}' tem arquivos de esquemas diferentes no mesmo diretório; "
                f"nomeie um deles: {list(esperados)}. Ler o diretório inteiro faz "
                f"colunas sumirem sem erro."
            )
        if arquivo not in esperados:
            raise ValueError(f"'{arquivo}' não existe em '{dataset}'. Esperado: {list(esperados)}.")
        return (base / arquivo).as_posix()

    if arquivo is not None:
        return (base / arquivo).as_posix()

    return (base / "**" / "*.parquet").as_posix()


# Havia aqui `ler()` e `escalar()`, helpers genéricos de consulta. Saíram em
# 2026-08-20 sem nunca terem sido chamados: todo leitor em `leitura.py` monta o
# próprio SQL, porque cada dataset precisa de poda de partição e de tratamento
# próprio — um `SELECT *` genérico não servia a nenhum deles.
#
# `caminho()` e `conectar()` são a interface real deste módulo.
