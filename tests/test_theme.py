"""Testes do sistema visual."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.doencas import hanseniase as tb
from src.theme import componentes as c
from src.theme import cores

#: Campos do `Kpis` que existem só para alimentar outro número e nunca viram
#: card: denominadores e numeradores de fração. Cobrar cor e rótulo do pack
#: para eles seria cobrar por uma tela que não existe.
AUXILIARES = {"pop_0_14", "cura_encerrada", "encerramentos"}

#: Todas as métricas que o pack precisa conhecer, independentemente de
#: aparecerem na tela. Derivada do dataclass para não haver duas listas.
TODOS_OS_KPIS = tuple(
    campo
    for campo in __import__("src.data.kpis", fromlist=["Kpis"]).Kpis.__dataclass_fields__
    if not campo.startswith("_") and campo not in AUXILIARES
)


def luminancia(hexa: str) -> float:
    r, g, b = cores.hex_para_rgb(hexa)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_pack_cobre_os_kpis_que_exibe() -> None:
    from src.data.kpis import Kpis

    campos = {c for c in Kpis.__dataclass_fields__ if not c.startswith("_")}
    assert set(TODOS_OS_KPIS) <= campos, "métrica listada aqui não existe em Kpis"

    # `Kpis` é o do core e carrega campos de TB (HIV, interrupção); o pack só
    # precisa cobrir o que ele exibe.
    for metrica in tb.LAYOUT_KPI + tb.METRICAS_MAPA:
        assert metrica in tb.CORES, f"{metrica} sem cor"
        assert metrica in tb.ROTULOS, f"{metrica} sem rótulo"


def test_todas_as_metricas_tem_contraste_nos_dois_temas() -> None:
    """O valor do KPI é 28px em peso 900 — texto grande, mínimo 3:1 na WCAG.

    Cinco métricas falhavam no tema escuro, `incid` entre elas: é a padrão, e
    portanto o número mais visto do painel, com 2,6:1. A correção não foi
    trocar as cores, e sim misturar o acento com `currentColor` — no claro o
    texto é escuro e a cor escurece de leve; no escuro clareia. Assim o ajuste
    segue o tema do Streamlit, e não o do sistema operacional.
    """
    from src.doencas import hanseniase as pack
    from src.theme import cores

    TEXTO = {"claro": "#0B1220", "escuro": "#E5E7EB"}
    FUNDO = {"claro": "#FFFFFF", "escuro": "#0B1220"}

    ruins = []
    for metrica, cor in pack.CORES.items():
        for tema in TEXTO:
            misturada = cores.misturar(cor, TEXTO[tema], 0.28)
            razao = cores.contraste(misturada, FUNDO[tema])
            if razao < cores.CONTRASTE_MINIMO:
                ruins.append(f"{metrica} no tema {tema}: {razao:.1f}")
    assert not ruins, (
        f"contraste abaixo de {cores.CONTRASTE_MINIMO}:1 — " + "; ".join(ruins)
    )


def test_o_acento_do_kpi_se_mistura_ao_texto() -> None:
    """A mistura é o que faz o contraste seguir o tema sem media query."""
    import re

    bloco = re.search(r"\.kpi-value\s*\{([^}]*)\}", c.css_base()).group(1)
    assert "color-mix" in bloco and "currentColor" in bloco


def test_escala_tipografica_nao_tem_degrau_morto() -> None:
    """Degrau que ninguém usa é convite a contornar a escala.

    `TEXTO_BASE` e `TEXTO_LG` existiam sem uso nenhum, e os componentes
    resolviam com `font-size` fixo — apareceram 11px, 12px e 28px soltos no
    CSS, três tamanhos que a régua não previa.
    """
    from src.theme import tokens

    raiz = Path(__file__).resolve().parents[1] / "src"
    origem = (raiz / "theme" / "componentes.py").read_text(encoding="utf-8")
    origem += (raiz / "grafico_componente.py").read_text(encoding="utf-8")

    # Os degraus são interpolados nas f-strings do CSS, então se procura o
    # nome do token, não o valor em pixels.
    degraus = [
        n for n in dir(tokens)
        if n.startswith("TEXTO_") and n not in ("TEXTO_TITULO", "TEXTO_CLARO", "TEXTO_ESCURO")
    ]
    mortos = [d for d in degraus if f"tokens.{d}" not in origem]
    assert not mortos, f"degraus declarados e nunca usados: {mortos}"


def test_nenhum_tamanho_de_fonte_fixo_no_css() -> None:
    """Todo tamanho sai da escala, para a régua continuar sendo a régua."""
    import re

    css = c.css_base() + c.css_layout()
    fixos = re.findall(r"font-size:\s*(\d+(?:\.\d+)?px)", css)
    da_escala = {"12px", "14px", "24px"}
    fora = [f for f in fixos if f not in da_escala]
    assert not fora, f"tamanhos fora da escala: {sorted(set(fora))}"


def test_card_de_kpi_e_so_leitura() -> None:
    """O card voltou a ser indicador, e não controle disfarçado.

    Ele não avisava que era clicável — a única pista era o realce no hover,
    que não existe em toque. A troca de métrica passou a ter controle próprio,
    nativo, com teclado e foco de graça.
    """
    assert not hasattr(c, "kpi_clicavel")
    assert not hasattr(c, "script_estado_kpis")

    css = c.css_base() + c.css_layout()
    assert "st-key-kpi-" not in css, "CSS do botão invisível sobreviveu"


def test_card_nao_e_mais_escondido_do_leitor_de_tela() -> None:
    """Com o botão por cima, o card era `aria-hidden` e o nome vinha dele.

    Agora o card é o conteúdo, então precisa ser lido.
    """
    html = c.kpi_card("Incidência", "40,42", cor="#92400E")
    assert "aria-hidden" not in html


@pytest.mark.dado
def test_seletor_do_mapa_so_oferece_metrica_que_o_mapa_pinta() -> None:
    """Oferecer opção que leva a painel vazio é pior que não oferecer.

    Cura e contatos vêm do `sinan_landing`, que o leitor consulta uma
    geografia por vez — não dá para pintar o estado inteiro de uma vez.
    """
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    for metrica in pack.METRICAS_MAPA:
        valores = leitura.valores_por_geografia(Escopo(pack.DOENCA, 2024, "BR"), metrica)
        assert not valores.empty, f"{metrica} está no seletor mas não pinta"


@pytest.mark.parametrize("chave", ["incid", "casos", "cura", "cura_pct"])
def test_todo_kpi_renderiza(chave: str) -> None:
    from src.doencas import hanseniase as pack

    html = c.kpi_card(pack.rotulo(chave), "1,0", cor=pack.cor(chave))
    assert pack.rotulo(chave) in html or "&" in html



def test_a_unidade_repetida_sobe_para_o_titulo() -> None:
    """O boletim escreve "por 100 mil hab." nas cinco faixas; na caixa do
    painel isso vira cinco linhas quebradas dizendo o mesmo. A citação
    literal fica no pack — aqui só a exibição enxuga."""
    from src.theme.componentes import _fatorar_unidade

    titulo, linhas = _fatorar_unidade(
        "Coeficiente de detecção geral",
        (
            "Hiperendêmico: >40,0/100 mil hab.",
            "Muito alto: 20,00 a 39,99/100 mil hab.",
            "Baixo: < 2,00/100 mil hab.",
        ),
    )
    assert titulo == "Coeficiente de detecção geral (por 100 mil hab.)"
    assert linhas == ("Hiperendêmico: >40,0", "Muito alto: 20,00 a 39,99", "Baixo: < 2,00")


def test_sufixo_curto_nao_e_fatorado() -> None:
    """"Bom ≥ 90%" e "Precário < 75%" só compartilham o `%`, que é parte do
    número e não uma unidade a destacar."""
    from src.theme.componentes import _fatorar_unidade

    original = ("Bom ≥ 90%", "Regular ≥ 75 a 89,9%", "Precário < 75%")
    assert _fatorar_unidade("% Cura", original) == ("% Cura", original)
