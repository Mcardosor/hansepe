"""Testes da pirâmide etária.

O ponto sensível aqui é a origem dos dados. `piramides` traz casos, cura e
óbitos, mas cura e óbitos vêm zerados para tuberculose — falha do pipeline da
equipe parceira, não ausência de dado na fonte. Óbitos têm saída local pelo
SIM; cura não tem nenhuma. Ver docs/perguntas-equipe-r.md.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import graficos
from src.data import leitura
from src.data.escopo import Escopo

ESCOPOS = [
    Escopo("TB", 2024, "BR"),
    Escopo("TB", 2024, "UF", uf="PE"),
    Escopo("TB", 2024, "MUN", uf="PE", mun="261160"),
]


@pytest.mark.parametrize("esc", ESCOPOS, ids=lambda e: e.nivel)
@pytest.mark.parametrize("tipo", ["CASOS", "OBITOS"])
def test_tem_as_onze_faixas_para_cada_sexo(esc: Escopo, tipo: str) -> None:
    """Faixa sem registro entra zerada — a pirâmide não pode ter degrau vago."""
    dados = leitura.piramide_completa(esc, tipo)
    if dados.empty:
        pytest.skip(f"sem dado de {tipo} em {esc.nivel}")

    esperadas = {rotulo for _, rotulo in leitura.FAIXAS}
    for sexo, grupo in dados.groupby("sexo"):
        assert set(grupo["faixa_etaria"]) == esperadas, f"sexo {sexo}"
        assert len(grupo) == len(leitura.FAIXAS)
    assert dados["valor"].notna().all()


def test_obitos_do_sim_usam_o_mesmo_vocabulario_de_faixas() -> None:
    """A premissa que torna o SIM utilizável como fonte da pirâmide.

    `obitos_sim_faixa` traz um subconjunto das faixas de `piramides` — não
    tem as três faixas jovens — mas os `faixa_ord` das faixas comuns são
    idênticos. É isso que permite reindexar em vez de mapear rótulos na mão.
    """
    esc = Escopo("TB", 2024, "UF", uf="PE")
    sim = leitura.obitos_por_faixa(esc)
    sinan = leitura.piramide(esc, "CASOS")
    if sim.empty or sinan.empty:
        pytest.skip("dado indisponível")

    de_sim = dict(zip(sim["faixa_etaria"], sim["faixa_ord"], strict=True))
    de_sinan = dict(zip(sinan["faixa_etaria"], sinan["faixa_ord"], strict=True))

    assert set(de_sim) <= set(de_sinan), "SIM tem faixa que não existe no SINAN"
    for faixa, ordem in de_sim.items():
        assert de_sinan[faixa] == ordem, f"{faixa}: {ordem} vs {de_sinan[faixa]}"


def test_cura_e_vazia_e_nao_quebra() -> None:
    """Sem fonte local. Precisa devolver vazio limpo, não estourar."""
    dados = leitura.piramide_completa(Escopo("TB", 2024, "UF", uf="PE"), "CURA")
    assert dados.empty
    assert list(dados.columns) == ["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"]


def test_tipo_invalido_falha_claramente() -> None:
    with pytest.raises(ValueError, match="Tipo inválido"):
        leitura.piramide_completa(Escopo("TB", 2024, "BR"), "XPTO")


def test_tipo_aceita_minuscula() -> None:
    esc = Escopo("TB", 2024, "UF", uf="PE")
    assert leitura.piramide_completa(esc, "casos").equals(
        leitura.piramide_completa(esc, "CASOS")
    )


def test_grafico_poe_homens_a_esquerda() -> None:
    """A convenção da pirâmide: homens negativos, mulheres positivos."""
    dados = leitura.piramide_completa(Escopo("TB", 2024, "UF", uf="PE"), "CASOS")
    if dados.empty:
        pytest.skip("sem dado")

    figura = graficos.piramide(dados, rotulo="Casos")
    base = figura.data
    assert (base.loc[base["sexo"] == "M", "evento"] <= 0).all()
    assert (base.loc[base["sexo"] == "F", "evento"] >= 0).all()


def test_taxa_por_100mil_usa_a_populacao_da_faixa() -> None:
    dados = leitura.piramide_completa(Escopo("TB", 2024, "UF", uf="PE"), "CASOS")
    if dados.empty or not (pd.to_numeric(dados["pop"], errors="coerce") > 0).any():
        pytest.skip("sem população")

    figura = graficos.piramide(dados, rotulo="Casos", por_100mil=True)
    linha = dados[pd.to_numeric(dados["pop"], errors="coerce") > 0].iloc[0]
    esperado = linha["valor"] / linha["pop"] * 100_000
    obtido = figura.data.loc[
        (figura.data["sexo"] == linha["sexo"])
        & (figura.data["faixa_etaria"] == linha["faixa_etaria"]),
        "valor",
    ].iloc[0]
    assert obtido == pytest.approx(esperado)


def test_taxa_sem_populacao_avisa_em_vez_de_dividir_por_zero() -> None:
    """Óbitos vêm do SIM, sem população — pedir taxa não pode explodir."""
    dados = leitura.piramide_completa(Escopo("TB", 2024, "UF", uf="PE"), "OBITOS")
    if dados.empty:
        pytest.skip("sem dado")

    assert graficos.piramide(dados, rotulo="Óbitos", por_100mil=True) is not None


def test_grafico_vazio_nao_quebra() -> None:
    vazio = pd.DataFrame(columns=["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"])
    assert graficos.piramide(vazio, rotulo="Casos") is not None
