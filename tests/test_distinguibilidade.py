"""As séries do painel sob daltonismo.

Exame de 05/out/2026, com `src/theme/visao.py`. Contraste com o fundo já
tem teste próprio em `test_theme.py`; aqui a pergunta é outra — duas séries
podem ter ótimo contraste com o fundo e nenhuma diferença entre si.

O que **não** está preso aqui, de propósito: a separação entre anos
vizinhos do canal endêmico e entre faixas vizinhas do mapa. Nos dois casos
são cinco a sete degraus numa escala sequencial, e eles não cabem com
separação confortável — a resposta foi tirar a cor do papel de identificar
(uma entrada de legenda no canal; contorno próprio no mapa), não espalhar
as cores. O que se exige das rampas está no teste de monotonia.
"""

from __future__ import annotations

import pytest

from src import grafico_componente as gc
from src.doencas import hanseniase as pack
from src.theme import visao


def _pior(a: str, b: str) -> float:
    """A menor distância entre duas cores, no pior tipo de visão."""
    return min(visao.delta_e(visao.simular(a, v), visao.simular(b, v)) for v in visao.VISOES)


@pytest.mark.parametrize(
    "nome,a,b",
    [
        ("roxo x laranja do boletim", pack.COR_BOLETIM, pack.COR_BOLETIM_SECUNDARIA),
        ("barra clara x barra escura", "#B9AFD6", pack.COR_BOLETIM),
        ("barra clara x linha", "#B9AFD6", pack.COR_BOLETIM_SECUNDARIA),
    ],
)
def test_series_que_dividem_o_mesmo_grafico_se_distinguem(nome: str, a: str, b: str) -> None:
    """Pares que aparecem juntos e sem rótulo colado em cada traço.

    São os que a leitura depende mesmo da cor. Medidos entre 28 e 64 no
    exame; o limite de 20 dá folga para ajuste de tom sem perder o que
    importa.
    """
    distancia = _pior(a, b)
    assert distancia >= visao.LIMITE_CONFORTAVEL, f"{nome}: {distancia:.1f}"


def test_o_ano_selecionado_se_destaca_de_todo_ano_de_referencia() -> None:
    """A leitura central do canal endêmico: este ano contra os anteriores."""
    for tom in gc.RAMPA_REFERENCIA:
        distancia = _pior(pack.CORES["incid"], tom)
        assert distancia >= visao.LIMITE_CONFORTAVEL, f"{tom}: {distancia:.1f}"


@pytest.mark.parametrize("metrica", ["incid", "casos"])
def test_a_rampa_do_mapa_ordena_em_qualquer_visao(metrica: str) -> None:
    """A propriedade que faz uma escala sequencial funcionar.

    Não é a distância entre faixas vizinhas — com sete degraus ela fica em
    torno de 9, e é a legenda que carrega os valores exatos. É a
    luminosidade cair sempre no mesmo sentido: assim "mais escuro = mais"
    nunca inverte, nem para quem não distingue cores.
    """
    rampa = pack.PALETA_MAPA[metrica]
    for v in visao.VISOES:
        luz = [visao.luminosidade(visao.simular(c, v)) for c in rampa]
        assert all(a > b for a, b in zip(luz, luz[1:])), f"{v}: {[round(x, 1) for x in luz]}"


def test_sem_dado_nao_depende_de_cor_para_se_distinguir() -> None:
    """Nenhum cinza separa "sem dado" da rampa — a prova de que o contorno
    é necessário, e não enfeite.

    Os claros colidem com o lilás mais baixo; os escuros, com uma faixa do
    meio. Se um dia alguém tentar resolver trocando a cor de novo, este
    teste mostra por que não vai dar.
    """
    from src import mapa

    candidatos = ("#F3F4F6", "#FFFFFF", "#FAFAFA", "#E5E7EB", "#D1D5DB", "#9CA3AF", "#6B7280")
    assert mapa.SEM_DADO in candidatos
    for cinza in candidatos:
        pior = min(_pior(cinza, faixa) for faixa in pack._ROXOS)
        assert pior < visao.LIMITE_CONFORTAVEL, (
            f"{cinza} se distingue da rampa inteira ({pior:.1f}) — se isto "
            f"passar a valer, o contorno de `CONTORNO_SEM_DADO` pode sair"
        )

    # O contorno é escuro o bastante para marcar a diferença por luminosidade,
    # que é o canal que nenhum daltonismo apaga.
    contorno = "#%02X%02X%02X" % tuple(mapa.CONTORNO_SEM_DADO[:3])
    assert visao.luminosidade(contorno) < 40
    assert visao.luminosidade(mapa.SEM_DADO) > 90
