"""Recortes-limite: ano não consolidado, município sem caso.

O painel é demonstrado ao vivo, e é nos cantos que ele quebra. O caso do ano
foi encontrado assim: o slider oferece um ano que um dos datasets ainda não
tem, e arrastar o slider até o fim derrubava a página com um erro de arquivo
não encontrado. O SIM, que era o dataset atrasado, saiu em 02/out/2026 — a
distinção entre partição ausente e dataset ausente continua valendo para os
que ficaram.
"""

from __future__ import annotations

import pytest

from src.data import conexao, geo, leitura
from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import hanseniase as pack

#: Último ano oferecido pelo slider.
ANO_LIMITE = 2025


def test_o_slider_realmente_alcanca_o_ano_limite() -> None:
    """A premissa do módulo. Se deixar de valer, estes testes viram teatro."""
    assert ANO_LIMITE in leitura.anos_disponiveis(pack.DOENCA)


def test_particao_ausente_e_distinta_de_dataset_ausente() -> None:
    """Ano não consolidado é ausência de dado; dataset sumido é configuração."""
    with pytest.raises(conexao.ParticaoAusente):
        conexao.caminho(
            "incidence", doenca="HANSENIASE", nivel="BR", ano=1999
        )

    with pytest.raises(FileNotFoundError) as erro:
        conexao.caminho("dataset_que_nao_existe", nivel="BR")
    assert not isinstance(erro.value, conexao.ParticaoAusente)


def _municipio_sem_caso(uf: str = "MG") -> str | None:
    for cod in geo.municipios(uf)["cod_mun6"][:150]:
        if not calc.calcular(Escopo(pack.DOENCA, 2024, "MUN", uf=uf, mun=cod)).casos:
            return cod
    return None


def test_municipio_sem_caso_devolve_vazio_e_nao_erro() -> None:
    cod = _municipio_sem_caso()
    if cod is None:
        pytest.skip("nenhum município sem caso na amostra")

    esc = Escopo(pack.DOENCA, 2024, "MUN", uf="MG", mun=cod)
    assert leitura.piramide_completa(esc, "CASOS").empty
    assert leitura.composicao(esc, "CLASSOPERA").empty
    # População existe mesmo sem caso: o município não sumiu do mapa.
    assert calc.calcular(esc).pop


# ---------------------------------------------------------------------------
# Ano parcial
# ---------------------------------------------------------------------------


def test_ano_fechado_tem_doze_meses() -> None:
    assert leitura.meses_com_dado(pack.DOENCA, 2024) == 12


def test_ano_corrente_e_parcial() -> None:
    """O que justifica o aviso na barra lateral.

    Em 2025 a incidência do Brasil aparece como 0,83 contra 40,42 em 2024 —
    sem dizer que o ano está pela metade, a leitura natural é queda.
    """
    meses = leitura.meses_com_dado(pack.DOENCA, 2026)
    assert 0 < meses < 12


def test_ano_fechado_nao_e_marcado_como_parcial() -> None:
    """A lição do tbpe: ano parcial se **detecta**, não se presume.

    O painel de origem marca 2025 como "dados parciais" só por ser o último
    ano; o `_cache_ts` tem os 12 meses de 2025. Marcar ano fechado como
    parcial desacredita o aviso quando ele for verdadeiro.
    """
    assert leitura.meses_com_dado(pack.DOENCA, 2025) == 12


def test_ano_inexistente_devolve_zero_em_vez_de_erro() -> None:
    assert leitura.meses_com_dado(pack.DOENCA, 1999) == 0
