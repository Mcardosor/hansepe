"""Testes da geometria pré-processada.

O que importa aqui não é o tamanho do arquivo, é o mosaico continuar íntegro:
municípios vizinhos não podem se sobrepor nem deixar fresta visível. Foi
justamente isso que a simplificação por polígono quebrava.
"""

from __future__ import annotations

import geopandas as gpd
import pytest

from src.data import config, geo

#: Amostra com perfis diferentes: muitos municípios pequenos (ES), muitos e
#: grandes (MG), poucos e enormes (AM), um só (DF), e o alvo do projeto (PE).
UFS_AMOSTRA = ["PE", "ES", "MG", "AM", "DF"]

#: CRS métrico para medir área (Brasil Polyconic).
CRS_AREA = 5880


def _existe(caminho) -> bool:
    return caminho.exists()


pytestmark = pytest.mark.skipif(
    not _existe(geo.geo_dir() / "municipios"),
    reason="geometria não gerada; rode: python -m scripts.preparar_geometria",
)


@pytest.mark.parametrize("uf", UFS_AMOSTRA)
def test_camada_de_municipios_carrega(uf: str) -> None:
    camada = geo.municipios(uf)
    assert not camada.empty
    assert set(camada.columns) == {"cod_mun6", "nome_mun", "uf", "geometry"}
    assert camada.crs is not None
    assert (camada["uf"] == uf).all()


@pytest.mark.parametrize("uf", UFS_AMOSTRA)
def test_codigo_de_municipio_tem_seis_digitos(uf: str) -> None:
    """A chave canônica do projeto — ver contrato-dados, armadilha 6."""
    codigos = geo.municipios(uf)["cod_mun6"]
    assert codigos.str.len().eq(6).all()
    assert codigos.is_unique


@pytest.mark.parametrize("uf", UFS_AMOSTRA)
def test_geometria_valida(uf: str) -> None:
    assert geo.municipios(uf).geometry.is_valid.all()


#: Sobreposição máxima tolerada entre dois municípios vizinhos, em m².
#:
#: Depois da simplificação topológica sobram só resíduos de precisão em
#: vértices compartilhados. Medido no país inteiro: 15 das 27 UFs não têm
#: nenhuma, e a pior é MT com 1,74 km² — que num mapa do Brasil de 800px de
#: largura equivale a 0,06 pixel². Invisível.
#:
#: Para comparar, o `shapely.simplify` por feição produzia 163 pares só no ES.
LIMITE_SOBREPOSICAO_M2 = 2_000_000


@pytest.mark.parametrize("uf", ["PE", "ES", "MG", "MT"])
def test_municipios_vizinhos_quase_nao_se_sobrepoem(uf: str) -> None:
    """Regressão do defeito da simplificação por polígono.

    Com ``shapely.simplify`` por feição, ES tinha 163 pares se sobrepondo e o
    coroplético ganhava bordas dobradas. Com simplificação topológica sobram
    só resíduos de precisão, de área desprezível.
    """
    camada = geo.municipios(uf).to_crs(CRS_AREA)[["geometry"]]
    pares = gpd.sjoin(camada, camada, predicate="overlaps")
    if pares.empty:
        return

    pior = max(
        camada.geometry.iloc[i].intersection(camada.geometry.iloc[j]).area
        for i, j in zip(pares.index, pares["index_right"], strict=True)
    )
    assert pior < LIMITE_SOBREPOSICAO_M2, (
        f"{uf}: sobreposição de {pior:.0f} m² entre vizinhos"
    )


#: Fresta máxima entre a malha simplificada e a original, como fração da área
#: do estado. Medido com simplificação topológica: 0,41% (ES).
LIMITE_FRESTA = 0.006


@pytest.mark.parametrize("uf", ["PE", "ES"])
def test_frestas_contra_a_malha_original_sao_pequenas(uf: str) -> None:
    """Compara a malha simplificada com a de origem, não consigo mesma.

    Com simplificação por polígono, ES perdia 1,97% da área em frestas. Com
    topológica, 0,41%.
    """
    import gzip
    import io

    caminho = (
        config.dashboard_dir() / "_geo_cache" / "municipios" / f"uf={uf}" / "mun.geojson.gz"
    )
    if not caminho.exists():
        pytest.skip("malha de origem indisponível")

    with gzip.open(caminho, "rb") as arquivo:
        original = gpd.read_file(io.BytesIO(arquivo.read())).to_crs(CRS_AREA)

    simplificada = geo.municipios(uf).to_crs(CRS_AREA)
    antes = original.union_all()
    depois = simplificada.union_all()

    fresta = antes.difference(depois).area / antes.area
    assert fresta < LIMITE_FRESTA, f"{uf}: {fresta:.2%} da área virou fresta"


def test_uf_e_pais_carregam() -> None:
    assert len(geo.ufs()) == 27
    assert len(geo.pais()) >= 1


@pytest.mark.parametrize("nivel,esperado", [("macro", 4), ("micro", 12)])
def test_recortes_de_pe(nivel: str, esperado: int) -> None:
    camada = geo.regioes('PE', nivel)
    assert len(camada) == esperado
    assert "regiao" in camada.columns
    assert camada["regiao"].notna().all()


def test_nao_ha_leitura_de_centroides() -> None:
    """`geo.centroides()` saiu, e não deve voltar por hábito.

    Ela lia `_geo_cache/municipios_centroids.parquet` e nunca foi chamada em
    produção — só por este arquivo. O teste passou meses verde apenas porque a
    função existia, o que é o oposto de cobertura.

    Quem precisar de um ponto por polígono usa `representative_point()`, como
    `mapa._camada_rotulos`: dispensa o arquivo, funciona em qualquer nível e
    garante um ponto dentro do polígono — o centroide de forma côncava cai
    fora, e o rótulo vai parar no vizinho.
    """
    assert not hasattr(geo, "centroides")


def test_uf_desconhecida_falha_claramente() -> None:
    with pytest.raises(ValueError, match="UF desconhecida"):
        geo.municipios("XX")


def test_total_de_municipios() -> None:
    """5.570 municípios do IBGE, mais Boa Esperança do Norte (MT).

    Esse último existe na malha de 2024 mas ainda não em `dim_geo` — aparece
    no mapa sem dado, que é o comportamento correto. As duas "áreas
    operacionais" do RS (Lagoa dos Patos e Lagoa Mirim) são descartadas na
    geração; ver `_padronizar_municipios`.
    """
    total = sum(len(geo.municipios(uf)) for uf in config.CODIGO_POR_UF)
    assert total == 5571


def test_codigo_de_municipio_e_unico_no_pais() -> None:
    """As áreas operacionais do RS colidiam em 430000 e duplicariam o join."""
    import pandas as pd

    codigos = pd.concat(
        [geo.municipios(uf)["cod_mun6"] for uf in config.CODIGO_POR_UF]
    )
    assert codigos.is_unique


def test_toda_uf_tem_nome_por_extenso() -> None:
    """`NOME_POR_UF` e `CODIGO_POR_UF` precisam cobrir as mesmas 27 UFs.

    São duas listas escritas à mão sobre o mesmo domínio. Faltando uma
    entrada, a faixa de identificação cai no `.get(uf, uf)` e mostra a sigla
    para aquele estado só — um "AM" no meio de "Pernambuco" e "São Paulo",
    que ninguém nota até alguém navegar justo para lá.
    """
    from src.data import config

    faltando = set(config.CODIGO_POR_UF) - set(config.NOME_POR_UF)
    sobrando = set(config.NOME_POR_UF) - set(config.CODIGO_POR_UF)
    assert not faltando, f"UF sem nome por extenso: {sorted(faltando)}"
    assert not sobrando, f"nome por extenso de UF inexistente: {sorted(sobrando)}"
