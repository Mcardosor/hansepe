"""Recortes-limite: ano não consolidado, município sem caso.

O painel é demonstrado ao vivo, e é nos cantos que ele quebra. O caso do ano
foi encontrado assim: o slider oferece 2025 porque `incidence` tem 2025, mas
o SIM fecha depois e `cache_ts_sim_obitos` para em 2024 — arrastar o slider
até o fim derrubava a página com um erro de arquivo não encontrado.
"""

from __future__ import annotations

import pytest

from src.data import conexao, geo, leitura
from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import hanseniase as pack

#: Ano oferecido pelo slider que o SIM ainda não fechou.
ANO_SEM_SIM = 2025


def test_o_slider_realmente_alcanca_um_ano_sem_sim() -> None:
    """A premissa do módulo. Se deixar de valer, estes testes viram teatro."""
    assert ANO_SEM_SIM in leitura.anos_disponiveis(pack.DOENCA)


def test_particao_ausente_e_distinta_de_dataset_ausente() -> None:
    """Ano não consolidado é ausência de dado; dataset sumido é configuração."""
    with pytest.raises(conexao.ParticaoAusente):
        conexao.caminho(
            "cache_ts_sim_obitos", nivel="BR", doenca="TUBE", ano=ANO_SEM_SIM
        )

    with pytest.raises(FileNotFoundError) as erro:
        conexao.caminho("dataset_que_nao_existe", nivel="BR")
    assert not isinstance(erro.value, conexao.ParticaoAusente)


@pytest.mark.parametrize("nivel,uf", [("BR", None), ("UF", "PE")])
def test_ano_sem_sim_nao_levanta(nivel: str, uf: str | None) -> None:
    esc = Escopo(pack.DOENCA, ANO_SEM_SIM, nivel, uf=uf)
    k = calc.calcular(esc)
    # Casos existem (vêm do SINAN); mortalidade não, e isso é um vazio
    # legítimo, não um zero — zero diria que ninguém morreu.
    assert k.casos
    assert k.obitos is None
    assert k.mortalidade is None
    assert k.letalidade is None


def test_piramide_de_obitos_vazia_no_ano_sem_sim() -> None:
    esc = Escopo(pack.DOENCA, ANO_SEM_SIM, "BR")
    assert leitura.piramide_completa(esc, "OBITOS").empty
    # Casos continuam, porque vêm de outra fonte.
    assert not leitura.piramide_completa(esc, "CASOS").empty


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
