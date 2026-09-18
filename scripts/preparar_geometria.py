"""Pré-processa a geometria uma vez, em disco.

O dashboard em R simplificava a geometria **a cada redesenho do mapa**, sobre
GeoJSON gzipado. Aqui isso é feito uma vez e o resultado vai para GeoParquet.

Dois ganhos independentes, medidos em PE (185 municípios):

- **formato**: GeoJSON.gz custa 267 ms para ler, GeoParquet custa 22 ms
- **simplificação**: 2,31 MB caem para 0,06 MB, com 0,049% de erro de área

A tolerância é **relativa** à largura do bounding box, como no original: assim
ela se ajusta sozinha de um município ao país, sem número mágico por camada.

Uso::

    python -m scripts.preparar_geometria
"""

from __future__ import annotations

import gzip
import io
import shutil
import time
from pathlib import Path

import geopandas as gpd
import topojson as tp

from src.data import config

SAIDA = config.data_dir() / "geo"

#: Divisor da largura do bbox. Valores do dashboard em R: 900 para municípios,
#: 1200 para as camadas de região.
DIV_MUNICIPIO = 900
DIV_REGIAO = 1200

#: CRS métrico para conferir o erro de área (Brasil Polyconic).
CRS_AREA = 5880


def _ler_gz(caminho: Path) -> gpd.GeoDataFrame:
    """GeoJSON gzipado. O geopandas não abre `.gz` direto."""
    with gzip.open(caminho, "rb") as arquivo:
        return gpd.read_file(io.BytesIO(arquivo.read()))


def simplificar(geo: gpd.GeoDataFrame, divisor: int) -> tuple[gpd.GeoDataFrame, float]:
    """Simplifica preservando as fronteiras compartilhadas.

    O ``simplify`` do shapely trata cada polígono isoladamente, então dois
    municípios vizinhos simplificam a divisa comum de formas diferentes e o
    mosaico se rompe. Medido no ES com a tolerância do R: 1,97% da área do
    estado virava fresta e 163 pares de polígonos passavam a se sobrepor — o
    coroplético ganha fiapos brancos e bordas dobradas. O dashboard em R tem
    esse defeito, porque usa ``st_simplify`` por feição.

    Aqui a simplificação é topológica: as arestas compartilhadas são
    simplificadas uma única vez. No mesmo ES, as sobreposições vão a zero e as
    frestas caem para 0,41%. Custa cerca de 1,5 s por UF, uma vez só.
    """
    xmin, _, xmax, _ = geo.total_bounds
    tolerancia = (xmax - xmin) / divisor
    if tolerancia <= 0:
        return geo, 0.0

    area_antes = geo.to_crs(CRS_AREA).area.sum()

    if len(geo) < 2:
        # Uma feição só (DF, contorno do país) não tem fronteira compartilhada
        # para romper — o simplify direto basta e evita o custo da topologia.
        saida = geo.copy()
        saida["geometry"] = saida.geometry.simplify(tolerancia, preserve_topology=True)
    else:
        topologia = tp.Topology(geo, prequantize=False, shared_coords=False)
        saida = topologia.toposimplify(tolerancia).to_gdf()
        saida = saida.set_crs(geo.crs, allow_override=True)
        # `to_gdf()` reordena as colunas; devolve na ordem de entrada.
        saida = saida[list(geo.columns)]

    # A simplificação topológica não garante validade; conserta o que quebrou.
    invalidas = ~saida.geometry.is_valid
    if invalidas.any():
        saida.loc[invalidas, "geometry"] = saida.loc[invalidas, "geometry"].buffer(0)

    area_depois = saida.to_crs(CRS_AREA).area.sum()
    erro = abs(area_depois - area_antes) / area_antes * 100 if area_antes else 0.0
    return saida, erro


def _padronizar_municipios(geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Normaliza para as colunas que a aplicação usa.

    A chave é o código de **6 dígitos**, igual ao resto do projeto — ver
    docs/contrato-dados.md, armadilha 6.

    Descarta as "áreas operacionais" do IBGE: a malha municipal traz a Lagoa
    dos Patos (4300002) e a Lagoa Mirim (4300001) como feições próprias. Não
    são municípios, não têm dado, e as duas truncam para o mesmo ``430000`` —
    manter faria um join por município duplicar linhas no RS.
    """
    saida = geo.copy()
    saida["cod_mun6"] = saida["CD_MUN"].astype(str).str[:6]
    saida["nome_mun"] = saida["NM_MUN"].astype(str)
    saida["uf"] = saida["SIGLA_UF"].astype(str)
    saida = saida[saida["cod_mun6"].str[2:6] != "0000"]
    return saida[["cod_mun6", "nome_mun", "uf", "geometry"]]


def _tamanho(caminho: Path) -> float:
    return caminho.stat().st_size / 1e6


def main() -> None:
    origem = config.dashboard_dir() / "_geo_cache"
    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    (SAIDA / "municipios").mkdir(parents=True)

    print(f"{'camada':<16}{'feições':>9}{'antes':>10}{'depois':>10}{'redução':>10}"
          f"{'erro área':>11}{'leitura':>10}")

    total_antes = total_depois = 0.0

    # --- Municípios, uma camada por UF -------------------------------------
    for pasta in sorted((origem / "municipios").glob("uf=*")):
        uf = pasta.name.removeprefix("uf=")
        entrada = pasta / "mun.geojson.gz"
        if not entrada.exists():
            print(f"{uf:<16}{'—':>9}  (mun.geojson.gz ausente)")
            continue

        geo = _padronizar_municipios(_ler_gz(entrada))
        geo, erro = simplificar(geo, DIV_MUNICIPIO)

        destino = SAIDA / "municipios" / f"{uf}.parquet"
        geo.to_parquet(destino)

        antes, depois = _tamanho(entrada), _tamanho(destino)
        total_antes += antes
        total_depois += depois

        inicio = time.perf_counter()
        gpd.read_parquet(destino)
        ms = (time.perf_counter() - inicio) * 1000

        print(f"{uf:<16}{len(geo):>9}{antes:>9.2f}M{depois:>9.2f}M"
              f"{antes / depois:>9.0f}x{erro:>10.3f}%{ms:>9.0f}ms")

    # --- Camadas nacionais --------------------------------------------------
    for nome, arquivo, divisor in (
        ("ufs", "br_ufs.geojson.gz", DIV_REGIAO),
        ("pais", "br_pais.geojson.gz", DIV_REGIAO),
    ):
        entrada = origem / arquivo
        if not entrada.exists():
            continue
        geo, erro = simplificar(_ler_gz(entrada), divisor)
        destino = SAIDA / f"{nome}.parquet"
        geo.to_parquet(destino)
        antes, depois = _tamanho(entrada), _tamanho(destino)
        total_antes += antes
        total_depois += depois
        print(f"{nome:<16}{len(geo):>9}{antes:>9.2f}M{depois:>9.2f}M"
              f"{antes / depois:>9.0f}x{erro:>10.3f}%")

    # --- Recortes de saúde de PE -------------------------------------------
    # Vêm dos shapefiles de apoio, não do cache do pipeline. São a única fonte
    # de macrorregião e região de saúde.
    for nome, arquivo, coluna in (
        ("pe_macro", "PEMacSAUD MODIF.geojson", "NomeMacro"),
        ("pe_micro", "PERGSAUDE MODIF.geojson", "NomeRegSau"),
    ):
        entrada = config.support_dir() / arquivo
        if not entrada.exists():
            print(f"{nome:<16}{'—':>9}  ({arquivo} ausente em data/support)")
            continue
        geo = gpd.read_file(entrada)
        if geo.crs is None:
            geo = geo.set_crs(4326)
        geo = geo.to_crs(4326)
        geo["regiao"] = geo[coluna].astype(str).str.strip()
        geo = geo[["regiao", "geometry"]]
        geo, erro = simplificar(geo, DIV_REGIAO)
        destino = SAIDA / f"{nome}.parquet"
        geo.to_parquet(destino)
        antes, depois = _tamanho(entrada), _tamanho(destino)
        total_antes += antes
        total_depois += depois
        print(f"{nome:<16}{len(geo):>9}{antes:>9.2f}M{depois:>9.2f}M"
              f"{antes / depois:>9.0f}x{erro:>10.3f}%")

    print(f"\ntotal: {total_antes:.1f} MB -> {total_depois:.1f} MB "
          f"({total_antes / total_depois:.0f}x menor)")
    print(f"saída: {SAIDA}")


if __name__ == "__main__":
    main()
