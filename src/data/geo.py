"""Leitura da geometria pré-processada.

As camadas vêm de ``data/geo/``, geradas por ``scripts.preparar_geometria``.
Nunca leia o ``_geo_cache`` do pipeline direto na aplicação: ele é GeoJSON
gzipado e custa mais de dez vezes o tempo de um GeoParquet.

Regenerar após qualquer mudança nos dados de origem::

    python -m scripts.preparar_geometria
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import geopandas as gpd

from . import config


def geo_dir() -> Path:
    return config.data_dir() / "geo"


def _ler(caminho: Path) -> gpd.GeoDataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Camada não encontrada: {caminho}\n"
            f"Gere com: python -m scripts.preparar_geometria"
        )
    return gpd.read_parquet(caminho)


@lru_cache(maxsize=32)
def municipios(uf: str) -> gpd.GeoDataFrame:
    """Municípios de uma UF. Colunas: ``cod_mun6``, ``nome_mun``, ``uf``."""
    sigla = str(uf or "").strip().upper()
    if sigla not in config.CODIGO_POR_UF:
        raise ValueError(f"UF desconhecida: {uf!r}")
    return _ler(geo_dir() / "municipios" / f"{sigla}.parquet")


@lru_cache(maxsize=1)
def ufs() -> gpd.GeoDataFrame:
    """As 27 unidades da federação."""
    return _ler(geo_dir() / "ufs.parquet")


@lru_cache(maxsize=1)
def pais() -> gpd.GeoDataFrame:
    """Contorno do Brasil."""
    return _ler(geo_dir() / "pais.parquet")


@lru_cache(maxsize=8)
def regioes(uf: str = "PE", nivel: str = "macro") -> gpd.GeoDataFrame:
    """Recortes de saúde de uma UF. Coluna ``regiao``.

    ``macro`` são as macrorregiões; ``micro`` as regiões de saúde. Hoje só PE
    tem a malha — ver `src/data/recortes.py` para acrescentar outra UF.
    """
    sigla = str(uf or "PE").strip().upper()
    chave = str(nivel or "macro").strip().lower()
    if chave not in ("macro", "micro"):
        raise ValueError(f"Nível inválido: {nivel!r}. Esperado 'macro' ou 'micro'.")
    return _ler(geo_dir() / f"{sigla.lower()}_{chave}.parquet")


# Houve aqui um `centroides()`, que lia
# `_geo_cache/municipios_centroids.parquet` e nunca foi chamado por nenhum
# caminho de produção — só pelo próprio teste. Saiu em 14/ago/2026, junto com o
# arquivo no pacote de publicação, pelo mesmo motivo que o dataset `obitos`
# saiu de `preparar_publicacao.DATASETS`: dado morto que ia para o servidor.
#
# Quem precisar de um ponto por polígono use `representative_point()` da própria
# geometria, como faz `mapa._camada_rotulos`. Além de dispensar o arquivo, ele
# funciona em qualquer nível — UF, macro, região de saúde — e garante um ponto
# **dentro** do polígono, coisa que o centroide não garante: em forma côncava
# ele cai fora, e o rótulo vai parar no vizinho.


# Havia aqui `limpar_cache()`, para descartar a geometria em memória depois de
# regerar as camadas. Nunca foi chamado — nem pela aplicação, nem pelos
# scripts. Regerar geometria exige reiniciar o serviço de qualquer forma, e o
# reinício limpa o cache sozinho.
