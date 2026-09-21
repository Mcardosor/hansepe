"""O componente próprio do mapa: o que o Python promete ao JavaScript."""

from __future__ import annotations

import json

from src import mapa_componente


def test_arquivos_do_componente_existem() -> None:
    """O Streamlit serve a pasta como está: faltar um arquivo é mapa em branco."""
    for nome in ("index.html", "mapa.js", "deck.min.js", "deck-json.min.js"):
        assert (mapa_componente.DIRETORIO / nome).is_file(), nome


def test_bundle_do_deck_traz_o_que_o_js_usa() -> None:
    js = (mapa_componente.DIRETORIO / "deck.min.js").read_text(encoding="utf-8", errors="ignore")
    conv = (mapa_componente.DIRETORIO / "deck-json.min.js").read_text(encoding="utf-8", errors="ignore")
    assert "FlyToInterpolator" in js
    assert "JSONConverter" in conv and "JSONConfiguration" in conv


def test_clique_novo_devolve_chave_e_nonce() -> None:
    ev = {"nonce": "a-1", "properties": {"cod_mun6": "261160", "regiao": "Metropolitana"}}
    assert mapa_componente.alvo_do_clique(ev, None) == ("261160", "a-1")
    assert mapa_componente.alvo_do_clique({"nonce": "a-2", "properties": {"regiao": "Agreste"}}, "a-1") == ("Agreste", "a-2")


def test_clique_ja_tratado_nao_navega_de_novo() -> None:
    """O valor do componente persiste entre reruns; sem o nonce, todo rerun
    repetiria a última navegação."""
    ev = {"nonce": "a-1", "properties": {"cod_mun6": "261160"}}
    assert mapa_componente.alvo_do_clique(ev, "a-1") == (None, None)


def test_evento_estranho_nao_derruba() -> None:
    assert mapa_componente.alvo_do_clique(None, None) == (None, None)
    assert mapa_componente.alvo_do_clique({"nonce": "x"}, None) == (None, "x")
    assert mapa_componente.alvo_do_clique({"nonce": "x", "properties": {}}, None) == (None, "x")


def test_camada_de_geografia_tem_id_fixo_e_transicao() -> None:
    """Sem `id` estável o deck.gl não interpola a cor entre reruns."""
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import box

    from src import doencas, mapa

    pack = doencas.carregar()
    dados = gpd.GeoDataFrame(
        {"cod_mun6": ["1", "2"], "nome_mun": ["A", "B"]},
        geometry=[box(-36, -9, -35, -8), box(-35, -9, -34, -8)],
        crs="EPSG:4326",
    )
    desenho, _ = mapa.deck(
        dados, pd.Series([1.0, 2.0], index=["1", "2"]), chave="cod_mun6",
        rampa=pack.rampa_mapa("incid"), rotulo_metrica="x", coluna_nome="nome_mun",
    )
    spec = json.loads(desenho.to_json())
    geo = next(c for c in spec["layers"] if c["@@type"] == "GeoJsonLayer")
    assert geo["id"] == "geografia"
    assert geo["transitions"] == {"getFillColor": mapa.TRANSICAO_COR_MS}
