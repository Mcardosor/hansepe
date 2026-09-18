"""Orçamento de tempo por interação, preso em teste.

Não mede tempo de parede — isso varia com a máquina e transformaria a suíte
numa fonte de falha intermitente. Mede o que **causa** o tempo e não depende
de hardware: quantas vezes o dado é lido e quanto trafega para o navegador.

O alvo de tempo de resposta está em `docs/performance.md`. Este arquivo prende
os dois orçamentos que o sustentam.
"""

from __future__ import annotations

import collections

import pytest

from src.data import kpis
from src.data.escopo import Escopo

pytest.importorskip("duckdb")

leitura = pytest.importorskip("src.data.leitura")

BR = Escopo("HANSENIASE", 2024, "BR")
PE = Escopo("HANSENIASE", 2024, "UF", uf="PE")
RECIFE = Escopo("HANSENIASE", 2024, "MUN", uf="PE", mun="261160")


@pytest.fixture
def contar_leituras(monkeypatch):
    """Conta chamadas a `variavel_sinan`, por variável."""
    chamadas: collections.Counter = collections.Counter()
    original = leitura.variavel_sinan

    def espiao(esc, variavel):
        chamadas[variavel] += 1
        return original(esc, variavel)

    monkeypatch.setattr(kpis.leitura, "variavel_sinan", espiao)
    return chamadas


@pytest.mark.parametrize("esc", [BR, PE, RECIFE], ids=["BR", "PE", "Recife"])
def test_calcular_nao_le_a_mesma_variavel_duas_vezes(esc, contar_leituras) -> None:
    """Cada variável do `sinan_landing` custa uma ida ao disco.

    Aconteceu em 22/ago: a contagem de desfechos entrou lendo `SITUA_ENCE` por
    conta própria, sem saber que a interrupção já lia. O conjunto de KPIs
    passou a pagar duas vezes pelo mesmo dado — 7 dos 23 ms do recorte
    nacional, 25% do total, sem que nada quebrasse.
    """
    kpis.calcular(esc)
    repetidas = {v: n for v, n in contar_leituras.items() if n > 1}
    assert not repetidas, (
        f"variável lida mais de uma vez no mesmo calcular(): {repetidas}. "
        f"Leia uma vez e empreste — ver `kpis.encerramentos`."
    )


def test_o_teto_de_payload_do_mapa_continua_existindo() -> None:
    """O outro orçamento mora em `test_mapa.py`, e este arquivo não o duplica.

    Fica o ponteiro, porque quem vier medir performance procura aqui primeiro:
    o spec do mapa volta pela rede a cada navegação e a cada troca de métrica —
    as cores fazem parte dele —, e `TETO_PAYLOAD_MB` prende o pior recorte que
    temos, Minas Gerais com 853 municípios.
    """
    from tests.test_mapa import TETO_PAYLOAD_MB

    assert TETO_PAYLOAD_MB <= 1.0, (
        "o teto de payload do mapa afrouxou; ver docs/performance.md"
    )
