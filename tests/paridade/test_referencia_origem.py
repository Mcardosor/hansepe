"""Paridade com o painel Shiny de origem (``PE_HANSE_06_01``).

Os valores em ``referencia_origem.json`` foram lidos da tela em 18/set/2026 —
cards, popup do mapa e tooltips — antes de existir uma linha de código aqui.
O painel de origem lê a **mesma extração** que nós, então a tolerância é só
o arredondamento de exibição: divergir é defeito, não defasagem.

**Divergir de propósito é permitido; divergir em silêncio, não.** Desde
20/set/2026 "casos novos" e a taxa de detecção seguem a definição do
Ministério (`MODOENTR = 1`), e a origem conta todas as entradas no registro
— `docs/paridade-hanseniase.md` §1. Esses dois cards **têm** de divergir da
origem, e o teste prende os dois lados: o nosso número e a distância dele.
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

#: Os números pela definição do MS, calculados em 20/set/2026 quando a
#: decisão foi tomada. `casos_total` da origem é 2.356 / 24,64.
MS_2025 = {"casos_novos": 1590, "taxa_deteccao": 16.63}
MS_2024 = {"casos_novos": 1761, "taxa_deteccao": 18.46}

#: Código IBGE (6 dígitos) dos municípios cujo popup foi lido.
MUNICIPIOS = {
    "Abreu e Lima": "260005",
    "Afogados da Ingazeira": "260010",
    "Afranio": "260020",
    "Agrestina": "260030",
}

#: Casos novos do MS por município em 2025 — a origem mostra todas as
#: entradas (18, 14, 15, 2).
MUNICIPIOS_MS = {
    "Abreu e Lima": (8, 7.7),
    "Afogados da Ingazeira": (13, 30.5),
    "Afranio": (10, 51.5),
    "Agrestina": (1, 4.1),
}


@pytest.fixture(scope="module")
def pe_2025():
    return calc.calcular(Escopo("HANSENIASE", 2025, "UF", uf="PE"))


@pytest.fixture(scope="module")
def pe_2024():
    return calc.calcular(Escopo("HANSENIASE", 2024, "UF", uf="PE"))


# --- o que reproduz a origem no dígito ------------------------------------


@pytest.mark.parametrize(
    "campo, referencia, casas",
    [
        ("taxa_det_0_14", "taxa_deteccao_0_14", 2),
        ("casos_0_14", "casos_novos_0_14", 0),
        ("cura", "curas", 0),
        ("prop_mb_pct", "prop_mb_pct", 1),
        ("prop_grau2_pct", "prop_grau2_pct", 1),
    ],
)
def test_cards_que_reproduzem_a_origem(pe_2025, campo, referencia, casas):
    assert round(getattr(pe_2025, campo), casas) == PE_2025[referencia]


@pytest.mark.parametrize(
    "campo, referencia",
    [
        ("taxa_det_0_14", "var_taxa_0_14"),
        ("casos_0_14", "var_casos_0_14"),
        ("cura", "var_curas"),
    ],
)
def test_variacao_vs_ano_anterior(pe_2025, pe_2024, campo, referencia):
    delta = getattr(pe_2025, campo) - getattr(pe_2024, campo)
    assert round(delta, 2) == PE_2025[referencia]


@pytest.mark.parametrize("nome", sorted(MUNICIPIOS))
def test_popup_municipio_curas_e_populacao(nome):
    esperado = REFERENCIA["municipios_2025"][nome]
    k = calc.calcular(Escopo("HANSENIASE", 2025, "MUN", uf="PE", mun=MUNICIPIOS[nome]))
    assert k.cura == esperado["curas"]
    assert k.pop == esperado["pop"]


def test_grau2_denominador_do_painel_de_origem(pe_2025):
    """218 sobre 2.171 — avaliados mais 'não avaliado', sem os em branco."""
    assert pe_2025.grau2 == 218
    assert pe_2025.avaliacao_base == 2171


# --- o que diverge da origem de propósito: casos novos do MS ---------------


def test_casos_novos_seguem_a_definicao_do_ms(pe_2025, pe_2024):
    assert pe_2025.casos == MS_2025["casos_novos"]
    assert round(pe_2025.incid, 2) == MS_2025["taxa_deteccao"]
    assert pe_2024.casos == MS_2024["casos_novos"]
    assert round(pe_2024.incid, 2) == MS_2024["taxa_deteccao"]


def test_a_divergencia_com_a_origem_continua_registrada(pe_2025):
    """Se um dia isto passar a bater, a decisão da §1 foi desfeita sem
    ninguém atualizar a paridade — o teste avisa."""
    assert pe_2025.casos != PE_2025["casos_novos"]
    assert PE_2025["casos_novos"] - pe_2025.casos == 2356 - 1590
    assert round(pe_2025.incid, 2) != PE_2025["taxa_deteccao"]


@pytest.mark.parametrize("nome", sorted(MUNICIPIOS_MS))
def test_popup_municipio_casos_novos_ms(nome):
    casos, taxa = MUNICIPIOS_MS[nome]
    k = calc.calcular(Escopo("HANSENIASE", 2025, "MUN", uf="PE", mun=MUNICIPIOS[nome]))
    assert k.casos == casos
    assert round(k.incid, 1) == taxa


# --- agregação por região --------------------------------------------------


def test_drill_down_na_macrorregiao():
    """Curas batem com a origem; casos e taxa são os do MS (413 / 38,52
    contra 672 / 62,68 lá)."""
    from src.data import leitura

    esperado = REFERENCIA["macro_vale_sao_francisco_araripe"]["2025"]
    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    macro = "Vale S.Francisco/Araripe"
    assert leitura.valores_por_regiao(esc, "cura", "macro")[macro] == esperado["curas"]
    assert leitura.valores_por_regiao(esc, "casos", "macro")[macro] == 413
    assert round(leitura.valores_por_regiao(esc, "incid", "macro")[macro], 2) == 38.52


def test_cards_da_macrorregiao_batem_com_o_mapa():
    from src.data import leitura, recortes

    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    macro = "Vale S.Francisco/Araripe"
    k = calc.calcular_regiao(esc, recortes.municipios_de(macro=macro))
    assert k.casos == leitura.valores_por_regiao(esc, "casos", "macro")[macro]
    assert round(k.incid, 2) == round(leitura.valores_por_regiao(esc, "incid", "macro")[macro], 2)
    assert k.taxa_det_0_14 is not None and k.prop_mb_pct is not None and k.prop_grau2_pct is not None


def test_soma_das_regioes_fecha_com_o_estado(pe_2025):
    """Invariante: os 185 municípios somados dão exatamente os cards de PE —
    inclusive os casos novos do MS, que vêm de outra tabela."""
    from src.data import leitura, recortes

    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    tudo = calc.calcular_regiao(esc, recortes.municipios_de())
    for campo in ("casos", "cura", "pop", "casos_0_14", "pop_0_14", "multibacilares", "classificados", "grau2", "avaliacao_base"):
        assert getattr(tudo, campo) == getattr(pe_2025, campo), campo
    assert leitura.valores_por_geografia(esc, "casos").sum() == pe_2025.casos
