"""Comparação com o Boletim Epidemiológico de Hanseníase (SES-PE).

Este harness é o irmão externo do `test_referencia_origem.py`, e existe
porque aquele não basta. Comparar com o painel da equipe parceira mede
**concordância**: os dois leem a mesma extração, e concordar não prova que o
número está certo — foi assim que a §1 (casos novos × todas as entradas)
passou meses invisível. Fonte oficial e independente pega essa classe de
erro; paridade entre painéis não pega.

Duas coisas são conferidas aqui:

1. **Os parâmetros das legendas** — o pedido da reunião de 22/set/2026. Os
   cortes e os nomes do pack têm de ser exatamente os dos quadros do
   boletim. Aqui não há tolerância: ou é a régua deles, ou não é.
2. **Os números de PE**, com tolerância assimétrica. O boletim foi tabulado
   em 16/04/2025 e nossa extração é posterior; o SINAN é atualizado
   retroativamente, então ficar **acima** é o comportamento correto — medido,
   de +0,4% a +4,4% na detecção geral. Ficar **abaixo** não tem explicação
   benigna.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import hanseniase as pack

REFERENCIA = json.loads(
    (Path(__file__).parent / "referencia_boletim.json").read_text(encoding="utf-8")
)

#: Quanto podemos ficar **acima** do boletim por defasagem de extração.
#: O pior ano medido em 25/set/2026 é 2021, com +4,4%.
MARGEM_ACIMA = 0.08

#: Quanto podemos ficar **abaixo**. Só arredondamento do coeficiente, que o
#: boletim publica com uma casa decimal.
MARGEM_ABAIXO = 0.01


def _pe(ano: int):
    return calc.calcular(Escopo("HANSENIASE", ano, "UF", uf="PE"))


# --- 1. os parâmetros das legendas -----------------------------------------


@pytest.mark.parametrize("metrica", sorted(REFERENCIA["parametros"]))
def test_cortes_sao_os_do_boletim(metrica: str):
    esperado = REFERENCIA["parametros"][metrica]
    assert list(pack.cortes_fixos(metrica)) == esperado["cortes"], esperado["texto"]


@pytest.mark.parametrize("metrica", sorted(REFERENCIA["parametros"]))
def test_nomes_das_classes_sao_os_do_boletim(metrica: str):
    esperado = REFERENCIA["parametros"][metrica]
    assert list(pack.nomes_fixos(metrica)) == esperado["nomes"], esperado["texto"]


@pytest.mark.parametrize(
    "metrica, valor, classe",
    [
        ("incid", 1.99, "Baixo"),
        ("incid", 2.0, "Médio"),
        ("incid", 9.99, "Médio"),
        ("incid", 10.0, "Alto"),
        ("incid", 19.99, "Alto"),
        ("incid", 20.0, "Muito alto"),
        ("incid", 39.99, "Muito alto"),
        ("incid", 40.0, "Hiperendêmico"),
        ("taxa_det_0_14", 0.49, "Baixo"),
        ("taxa_det_0_14", 0.5, "Médio"),
        ("taxa_det_0_14", 2.49, "Médio"),
        ("taxa_det_0_14", 2.5, "Alto"),
        ("taxa_det_0_14", 9.99, "Muito alto"),
        ("taxa_det_0_14", 10.0, "Hiperendêmico"),
        ("prop_grau2_pct", 4.99, "Baixo"),
        ("prop_grau2_pct", 5.0, "Médio"),
        ("prop_grau2_pct", 10.0, "Alto"),
        ("cura_pct", 74.9, "Precário"),
        ("cura_pct", 75.0, "Regular"),
        ("cura_pct", 89.9, "Regular"),
        ("cura_pct", 90.0, "Bom"),
        ("abandono_pct", 9.9, "Bom"),
        ("abandono_pct", 10.0, "Regular"),
        ("abandono_pct", 25.0, "Precário"),
    ],
)
def test_classificacao_nas_bordas(metrica: str, valor: float, classe: str):
    """As bordas são onde a régua erra em silêncio: 10,00 é 'Alto', não
    'Médio'; 90,0% é 'Bom', não 'Regular'."""
    assert pack.classe_de(metrica, valor) == classe


def test_pe_2024_cai_nas_classes_que_o_boletim_publica():
    k = _pe(2024)
    assert pack.classe_de("incid", k.incid) == "Alto"
    assert pack.classe_de("taxa_det_0_14", k.taxa_det_0_14) == "Muito alto"
    assert pack.classe_de("prop_grau2_pct", k.prop_grau2_pct) == "Alto"
    assert pack.classe_de("cura_pct", k.cura_pct) == "Precário"
    assert pack.classe_de("contatos_pct", k.contatos_pct) == "Regular"
    assert pack.classe_de("gif_avaliado_pct", k.gif_avaliado_pct) == "Regular"
    assert pack.classe_de("abandono_pct", k.abandono_pct) == "Regular"


# --- 2. os números ----------------------------------------------------------


def _anos_da_serie():
    return sorted(int(a) for a in REFERENCIA["serie_pe"] if a.isdigit())


@pytest.mark.parametrize("ano", _anos_da_serie())
def test_casos_novos_acompanham_o_boletim(ano: int):
    """Casos novos do MS, 2015–2024. Acima por defasagem, nunca abaixo."""
    esperado = REFERENCIA["serie_pe"][str(ano)]["casos"]
    nosso = _pe(ano).casos
    assert nosso >= esperado * (1 - MARGEM_ABAIXO), (
        f"{ano}: {nosso} abaixo do boletim ({esperado}) — extração não encolhe"
    )
    assert nosso <= esperado * (1 + MARGEM_ACIMA), (
        f"{ano}: {nosso} muito acima do boletim ({esperado}) — conferir a "
        f"definição de caso novo"
    )


@pytest.mark.parametrize("ano", _anos_da_serie())
def test_taxa_de_deteccao_acompanha_o_boletim(ano: int):
    esperado = REFERENCIA["serie_pe"][str(ano)]["incid"]
    nosso = _pe(ano).incid
    assert esperado * (1 - MARGEM_ABAIXO) <= nosso <= esperado * (1 + MARGEM_ACIMA)


@pytest.mark.parametrize("ano", [2023, 2024])
def test_qualidade_do_programa_acompanha_o_boletim(ano: int):
    """Cura, abandono, contatos e GIF avaliado nos anos de coorte fechada.

    A tolerância é maior porque a nossa é aproximação de coorte — por ano de
    diagnóstico, não PB do ano anterior e MB de dois antes. Medido em 2024:
    cura 67,1 contra 65,0; abandono 12,2 contra 13,5; contatos 81,6 contra
    77,3; GIF avaliado 82,7 contra 83,6.
    """
    esperado = REFERENCIA["qualidade_pe"][str(ano)]
    k = _pe(ano)
    for campo in ("cura_pct", "abandono_pct", "contatos_pct", "gif_avaliado_pct"):
        nosso = getattr(k, campo)
        assert nosso is not None, f"{ano}: {campo} suprimido — coorte deveria estar fechada"
        assert abs(nosso - esperado[campo]) <= 6, (
            f"{ano}: {campo} = {nosso:.1f} contra {esperado[campo]} do boletim"
        )


def test_deteccao_infantil_diverge_e_esta_registrada():
    """0–14 conta todas as entradas — a extração não cruza idade com modo de
    entrada. Ficamos sistematicamente acima do boletim, muito além da
    defasagem: em 2024, 125 contra 108. Ver docs/paridade-hanseniase.md §1.

    O teste prende a divergência: quando o microdado chegar e ela sumir, é
    aqui que se vem apagar esta exceção.
    """
    esperado = REFERENCIA["serie_pe"]["2024"]["casos_0_14"]
    nosso = _pe(2024).casos_0_14
    assert nosso > esperado * (1 + MARGEM_ACIMA), (
        "0–14 passou a bater com o boletim — se o microdado chegou, atualize "
        "a §1 da paridade e troque este teste pelo de igualdade"
    )


def test_coorte_aberta_suprime_os_indicadores_de_acompanhamento():
    """2025 tem 19% das saídas registradas: cura, abandono e contatos saem
    nulos em vez de 30,4%, que seria lido como programa ruim."""
    k = _pe(2025)
    assert k.coorte_aberta is True
    assert k.cura_pct is None and k.abandono_pct is None and k.contatos_pct is None
    # O GIF é preenchido no diagnóstico, não no acompanhamento: continua.
    assert k.gif_avaliado_pct is not None
