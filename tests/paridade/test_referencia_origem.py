"""Paridade com o painel Shiny de origem (``PE_HANSE_06_01``).

Os valores em ``referencia_origem.json`` foram lidos da tela em 18/set/2026 —
cards, popup do mapa e tooltips — antes de existir uma linha de código aqui.
O painel de origem lê a **mesma extração** que nós, então a tolerância é só
o arredondamento de exibição: divergir é defeito, não defasagem.

Divergir de propósito é permitido; divergir em silêncio, não. Cada diferença
decidida vai para ``docs/paridade-hanseniase.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data import kpis as calc
from src.data.escopo import Escopo

REFERENCIA = json.loads(
    (Path(__file__).parent / "referencia_origem.json").read_text(encoding="utf-8")
)

PE_2025 = REFERENCIA["PE"]["2025"]

#: Código IBGE (6 dígitos) dos municípios cujo popup foi lido.
MUNICIPIOS = {
    "Abreu e Lima": "260005",
    "Afogados da Ingazeira": "260010",
    "Afranio": "260020",
    "Agrestina": "260030",
}


@pytest.fixture(scope="module")
def pe_2025():
    return calc.calcular(Escopo("HANSENIASE", 2025, "UF", uf="PE"))


@pytest.mark.parametrize(
    "campo, referencia, casas",
    [
        ("incid", "taxa_deteccao", 2),
        ("taxa_det_0_14", "taxa_deteccao_0_14", 2),
        ("casos", "casos_novos", 0),
        ("casos_0_14", "casos_novos_0_14", 0),
        ("cura", "curas", 0),
        ("prop_mb_pct", "prop_mb_pct", 1),
        ("prop_grau2_pct", "prop_grau2_pct", 1),
    ],
)
def test_cards_pe_2025(pe_2025, campo, referencia, casas):
    assert round(getattr(pe_2025, campo), casas) == PE_2025[referencia]


@pytest.mark.parametrize(
    "campo, referencia",
    [
        ("incid", "var_taxa_deteccao"),
        ("taxa_det_0_14", "var_taxa_0_14"),
        ("casos", "var_casos_novos"),
        ("casos_0_14", "var_casos_0_14"),
        ("cura", "var_curas"),
    ],
)
def test_variacao_vs_ano_anterior(pe_2025, campo, referencia):
    anterior = calc.calcular(Escopo("HANSENIASE", 2024, "UF", uf="PE"))
    delta = getattr(pe_2025, campo) - getattr(anterior, campo)
    assert round(delta, 2) == PE_2025[referencia]


@pytest.mark.parametrize("nome", sorted(MUNICIPIOS))
def test_popup_municipio(nome):
    esperado = REFERENCIA["municipios_2025"][nome]
    k = calc.calcular(Escopo("HANSENIASE", 2025, "MUN", uf="PE", mun=MUNICIPIOS[nome]))
    assert k.casos == esperado["casos_novos"]
    assert round(k.incid, 1) == esperado["taxa"]
    assert k.cura == esperado["curas"]
    assert k.pop == esperado["pop"]


def test_grau2_denominador_do_painel_de_origem(pe_2025):
    """218 sobre 2.171 — avaliados mais 'não avaliado', sem os em branco."""
    assert pe_2025.grau2 == 218
    assert pe_2025.avaliacao_base == 2171


def test_drill_down_na_macrorregiao():
    """Entrar na macro Vale do S. Francisco/Araripe: 62,68 /100 mil e 672 casos."""
    from src.data import leitura

    esperado = REFERENCIA["macro_vale_sao_francisco_araripe"]["2025"]
    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    macro = "Vale S.Francisco/Araripe"
    taxa = leitura.valores_por_regiao(esc, "incid", "macro")[macro]
    casos = leitura.valores_por_regiao(esc, "casos", "macro")[macro]
    curas = leitura.valores_por_regiao(esc, "cura", "macro")[macro]
    assert round(taxa, 2) == esperado["taxa_deteccao"]
    assert casos == esperado["casos_novos"]
    assert curas == esperado["curas"]


def test_cards_da_macrorregiao_batem_com_a_origem():
    """Os três cards que a origem muda ao entrar na macro — e os quatro que ela
    não muda saem da mesma soma."""
    from src.data import recortes

    esperado = REFERENCIA["macro_vale_sao_francisco_araripe"]["2025"]
    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    k = calc.calcular_regiao(esc, recortes.municipios_de(macro="Vale S.Francisco/Araripe"))
    assert round(k.incid, 2) == esperado["taxa_deteccao"]
    assert k.casos == esperado["casos_novos"]
    assert k.cura == esperado["curas"]
    assert k.taxa_det_0_14 is not None and k.prop_mb_pct is not None and k.prop_grau2_pct is not None


def test_soma_das_regioes_fecha_com_o_estado(pe_2025):
    """Invariante: os 185 municípios somados dão exatamente os cards de PE."""
    from src.data import recortes

    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    tudo = calc.calcular_regiao(esc, recortes.municipios_de())
    for campo in ("casos", "cura", "pop", "casos_0_14", "pop_0_14", "multibacilares", "classificados", "grau2", "avaliacao_base"):
        assert getattr(tudo, campo) == getattr(pe_2025, campo), campo
