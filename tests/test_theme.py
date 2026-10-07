"""Testes do sistema visual."""

from __future__ import annotations

import re
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


def test_bloco_de_css_injetado_nao_ocupa_espaco() -> None:
    """Os `st.markdown("<style>…")` não podem custar espaçamento.

    Cada um vira um `stElementContainer` de altura zero, mas o bloco vertical
    do Streamlit é flex com `gap`: três blocos de CSS antes do título custavam
    48px de branco acima do cabeçalho — foi o que a equipe viu na tela em
    02/out/2026, medido no painel em produção.

    A regra exige `style:only-child`: um markdown com conteúdo visível junto
    do `<style>` continua aparecendo. Se alguém trocar o seletor por um mais
    frouxo, o conteúdo some sem aviso.
    """
    css = c.css_base() + c.css_layout()
    assert 'style:only-child' in css, (
        "a regra que recolhe os blocos de CSS injetado sumiu do tema"
    )


def test_o_icone_de_ajuda_nao_cresce_a_linha_do_rotulo() -> None:
    """Cinco pixels bastam para a faixa de controles parecer torta.

    O ícone de ajuda vem com 27px numa linha de texto de 22. Como ele fica
    dentro do rótulo, o rótulo cresce, e o controle abaixo começa mais baixo:
    os seletores (sem ícone) abriam em y=363 e as pílulas (com ícone) em 368.
    Medido na tela em 05/out/2026.
    """
    css = c.css_base() + c.css_layout()
    assert '[data-testid="stTooltipIcon"]' in css


def test_a_barra_de_abas_nao_soma_dois_respiros() -> None:
    """O painel da aba já traz 16px; a margem da barra somava mais 14.

    Trinta pixels é o dobro do ritmo de 16 que separa todo o resto da página,
    e era o maior buraco da tela depois do que já foi corrigido no topo.
    """
    css = c.css_base() + c.css_layout()
    trecho = css[css.index('[role="tablist"]'):]
    trecho = trecho[: trecho.index("}")]
    assert "margin-bottom: 0" in trecho, "a margem que dobrava o respiro voltou"


def test_o_respiro_entre_controles_nao_sobra_no_ultimo() -> None:
    """Margem no último controle da coluna não separa nada — e desalinha.

    Numa linha alinhada pela base, ela entra na conta da altura: o rádio
    "Meses do ano" ficava 14px abaixo do seletor de grau ao lado dele.
    """
    css = c.css_base() + c.css_layout()
    assert css.count(':not(:last-child):has([data-testid="stButtonGroup"])') == 1
    assert css.count(':not(:last-child):has([data-testid="stSelectbox"])') == 1


def test_o_rotulo_de_controle_e_legivel_nos_dois_temas() -> None:
    """O acento institucional some sobre o fundo escuro.

    O rótulo é uma pílula com fundo de 11% do acento e texto no acento puro.
    No tema claro isso dá 9,97:1; no escuro, 1,49:1 — contra o mínimo de
    4,5:1 da WCAG para texto normal (14px em negrito não alcança a faixa de
    "texto grande", que começa em 18,66px).

    A correção é a mesma do acento dos KPIs: misturar com a cor do texto do
    tema, para o ajuste seguir o tema do Streamlit e não o do sistema.
    """
    from src.theme import cores

    MINIMO = 4.5
    ACENTO = "#12346B"
    TEXTO = {"claro": "#0B1220", "escuro": "#E5E7EB"}
    FUNDO = {"claro": "#FFFFFF", "escuro": "#0B1220"}

    ruins = []
    for tema in TEXTO:
        pilula = cores.misturar(ACENTO, FUNDO[tema], 0.89)  # 11% de acento
        cor = cores.misturar(ACENTO, TEXTO[tema], 0.50)
        razao = cores.contraste(cor, pilula)
        if razao < MINIMO:
            ruins.append(f"{tema}: {razao:.2f}")
    assert not ruins, f"rótulo abaixo de {MINIMO}:1 — " + "; ".join(ruins)

    css = c.css_base() + c.css_layout()
    assert "var(--intro-accent, #12346B) 50%, currentColor" in css


def test_as_superficies_usam_um_raio_so() -> None:
    """Dois raios na mesma tela leem como descuido, não como hierarquia."""
    from src.theme import tokens

    assert tokens.RAIO_CARD == tokens.RAIO_PAINEL == "14px"


def test_o_rotulo_de_controle_fica_numa_linha_so() -> None:
    """Rótulo que quebra em duas linhas desloca o controle e torna a faixa.

    Em 1024px, "Nível do mapa" quebrava e a coluna descia 23px — o mesmo
    desalinhamento que o ícone de ajuda causava, por outro caminho.
    """
    css = c.css_base() + c.css_layout()
    trecho = css[css.index('[data-testid="stWidgetLabel"] > span'):]
    trecho = trecho[: trecho.index("}")]
    assert "white-space: nowrap" in trecho
    assert "text-overflow: ellipsis" in trecho


def test_a_variacao_do_kpi_e_legivel_nos_dois_temas() -> None:
    """Verde e vermelho foram escolhidos cada um pensando num tema.

    O verde dava 3,30:1 sobre o branco; o vermelho, 2,85:1 sobre o fundo
    escuro. São 12px em peso 800 — texto normal pela WCAG, mínimo 4,5:1.
    Varredura da tela em 05/out/2026.
    """
    from src.theme import cores, tokens

    MINIMO = 4.5
    FUNDO = {"claro": "#FFFFFF", "escuro": "#0B1220"}
    TEXTO = {"claro": "#0B1220", "escuro": "#E5E7EB"}

    ruins = []
    for nome, cor in (("bom", tokens.BOM), ("ruim", tokens.RUIM)):
        for tema in FUNDO:
            misturada = cores.misturar(cor, TEXTO[tema], 0.40)
            razao = cores.contraste(misturada, FUNDO[tema])
            if razao < MINIMO:
                ruins.append(f"{nome} no {tema}: {razao:.2f}")
    assert not ruins, f"abaixo de {MINIMO}:1 — " + "; ".join(ruins)


def test_o_chip_do_multiselect_usa_a_cor_da_pagina() -> None:
    """Nenhuma cor fixa passa nos dois laranjas do tema.

    O primário é #C1440A no claro e #ED853A no escuro. Branco dá 5,12:1 no
    primeiro e 2,62:1 no segundo; um texto escuro inverte o problema
    (3,65:1 e 7,15:1). `Canvas` resolve porque acompanha o tema.
    """
    css = c.css_base() + c.css_layout()
    trecho = css[css.index("stMultiSelectTagsContainer"):]
    assert "color: Canvas" in trecho[: trecho.index("}")]


def test_o_numero_dentro_da_barra_e_legivel_sobre_qualquer_cor() -> None:
    """O boletim escreve o N em branco dentro da barra — e isso só serve
    para barra escura.

    Sobre o roxo #5B4B8A o branco dá 7,45:1; sobre o laranja #E8701A cai
    para 3,10:1, contra o mínimo de 4,5:1 da WCAG para 12px. Conferência
    das cores dos gráficos em 05/out/2026, que o navegador não alcança
    porque o ECharts desenha em canvas.
    """
    from src import grafico_componente
    from src.doencas import hanseniase as pack
    from src.theme import cores

    for cor in (pack.COR_BOLETIM, pack.COR_BOLETIM_SECUNDARIA, "#FFFFFF", "#000000"):
        escolhida = grafico_componente.cor_sobre(cor)
        razao = cores.contraste(escolhida, cor)
        assert razao >= 4.5, f"{escolhida} sobre {cor}: {razao:.2f}"


def test_o_rotulo_de_ilha_do_mapa_nao_depende_do_tema() -> None:
    """O canvas do mapa é transparente: sem lapela, o fundo do texto é a
    superfície do tema, e nenhum cinza passa nos dois.

    O cinza anterior dava 4,17:1 no claro e 3,21:1 no escuro.
    """
    import inspect

    from src import mapa

    fonte = inspect.getsource(mapa)
    assert "get_color=[110, 110, 110, 230]" not in fonte, "o cinza ilegível voltou"


def test_o_titulo_do_card_cabe_em_duas_linhas() -> None:
    """Os rótulos cresceram e a reserva de uma linha deixou de bastar.

    Com "Taxa de detecção 0–14", pedido pela equipe parceira, a largura
    disponível em 1366px — o mínimo que a documentação declara — é exatamente
    a necessária. Medido na tela: 196px de 196px. A reserva vale para todos
    os cards, e não só para quem quebra: título de altura diferente entre
    cards desalinha o valor de um em relação ao vizinho.
    """
    css = c.css_base() + c.css_layout()
    # A primeira ocorrência é `.kpi-card:has(.kpi-icon) .kpi-title`, que só
    # ajusta o respiro do ícone. A regra da reserva é a declarada sozinha.
    inicio = css.index(chr(10) + ".kpi-title {")
    trecho = css[inicio : css.index("}", inicio)]
    assert "min-height: 2.5em" in trecho
    assert "-webkit-line-clamp: 2" in trecho
    assert "white-space: nowrap" not in trecho


def test_o_painel_se_reorganiza_no_celular() -> None:
    """Três regras que o aparelho de 375px exige, e que faltavam.

    O cabeçalho em três colunas dava 77px ao título, que quebrava letra a
    letra — dez linhas — e o cartão comia 334px dos 812 da tela. A largura
    mínima dos cards, escrita para a faixa de KPIs, vazava pela linha do mapa
    por causa de um `:has(.kpi-card)` que casava os cards de proporção dentro
    da coluna da direita: o mapa ficava com 125px de largura. E o título do
    card, em duas linhas, corta em 164px.
    """
    css = c.css_base() + c.css_layout()
    assert "@media (max-width: 639px)" in css
    # A regra da faixa de KPIs mira a chave, e não a presença de um card.
    assert ".st-key-faixa-kpis [data-testid=\"stColumn\"]" in css
    assert ':has(.kpi-card) > [data-testid="stColumn"]' not in css


def test_o_css_nao_tem_chave_solta() -> None:
    """Uma chave sobrando apaga a regra seguinte, em silêncio.

    Aconteceu: ao mover o bloco do celular para o fim do arquivo ficou um `}`
    órfão logo antes de `.sinan-intro-bandeira`, e o navegador descartou
    exatamente essa regra. A bandeira perdeu o `height: 58px` e passou a
    render no tamanho natural do arquivo — 586 x 391px ao lado de um título de
    30px. Nenhum teste reclamou porque o seletor continuava no texto do CSS;
    o que se perdeu foi o casamento das chaves.

    Daí a verificação ser estrutural, e não por seletor: vale para toda regra
    que venha a ser escrita depois desta.
    """
    css = re.sub(r"/\*.*?\*/", "", c.css_base() + c.css_layout(), flags=re.S)
    profundidade = 0
    for linha, texto in enumerate(css.splitlines(), start=1):
        for caractere in texto:
            if caractere == "{":
                profundidade += 1
            elif caractere == "}":
                profundidade -= 1
                assert profundidade >= 0, f"chave fechada a mais na linha {linha}: {texto!r}"
    assert profundidade == 0, f"{profundidade} bloco(s) sem fechar"
