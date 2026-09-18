

def test_escopo_com_municipios_normaliza_e_so_vale_na_uf() -> None:
    """Região de saúde: lista de municípios sobre o nível UF, sempre em 6 dígitos."""
    import pytest

    from src.data.escopo import Escopo, particao_e_filtro_geo

    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE", municipios=("2611606", "260005"))
    assert esc.municipios == ("261160", "260005")
    particao, onde, params = particao_e_filtro_geo(esc)
    assert particao == "MUN" and onde == "geo_id IN (?, ?)" and params == ["261160", "260005"]

    with pytest.raises(ValueError):
        Escopo("HANSENIASE", 2025, "MUN", uf="PE", mun="261160", municipios=("261160",))
