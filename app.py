"""Painel de Monitoramento da Hanseníase — Pernambuco.

Reconstrução em Python do painel Shiny ``PE_HANSE_06_01`` da equipe parceira
(inventário em ``docs/inventario-painel-origem.md``), sobre o core do painel
nacional (`../sinan`) e a composição de tela do RecifeTB. Página única, como o
original: cabeçalho com bandeira, faixa de KPIs, mapa à esquerda com as
proporções e as abas à direita, tópicos de interesse embaixo.

**Este arquivo é composição, não lógica.** Toda conta vive em ``src/data/``;
o que está aqui é arranjo de tela e fiação de estado.
"""

from __future__ import annotations

import contextlib

import pandas as pd
import streamlit as st

from src import doencas, grafico_componente, mapa, mapa_componente, resiliencia
from src.data import canal, config, geo, leitura, recortes
from src.data import kpis as calc
from src.data.escopo import Escopo
from src.estado import RECORTES, UF_FIXA, Navegacao
from src.theme import componentes as ui

#: A doença vem do ambiente (``SINAN_DOENCA``), não de um import fixo.
pack = doencas.carregar()

st.set_page_config(
    page_title=f"{pack.TITULO} — Pernambuco",
    layout="wide",
    initial_sidebar_state="collapsed",
)

#: Os cinco cards do painel de origem numa faixa só; as duas proporções ficam
#: na coluna da direita, acima das abas, como lá.
KPIS_FAIXA = tuple(m for m in pack.LAYOUT_KPI if m not in pack.FRACAO_KPI)
KPIS_PROPORCAO = tuple(m for m in pack.LAYOUT_KPI if m in pack.FRACAO_KPI)

ROTULO_RECORTE = {
    "MUN": "Municípios",
    "MACRO": "Macrorregiões",
    "MICRO": "Regiões de saúde",
}

#: Nome da unidade listada, para o título do ranking dizer a verdade.
UNIDADE_RECORTE = {
    "MUN": "municípios",
    "MACRO": "macrorregiões",
    "MICRO": "regiões de saúde",
}

ROTULO_CLASSIFICACAO = {
    "NATURAL": "Quebras naturais",
    "QUARTIL": "Quintis",
    "FIXA": "Endemicidade",
}

AJUDA_CLASSIFICACAO = """Como as cores repartem os valores.

**Quebras naturais** agrupam municípios parecidos e separam os diferentes.

**Quintis** põem um quinto dos municípios em cada cor — é a classificação do painel de origem. Fácil de explicar, mas a régua muda a cada ano.

**Endemicidade** usa os parâmetros oficiais: Baixo (< 2), Médio (2,00–9,99), Alto (10,00–19,99), Muito alto (20,00–39,99) e Hiperendêmico (≥ 40 por 100 mil). É a única que deixa dois anos comparáveis, e só aparece nas taxas de detecção — contagem de casos não tem classe de endemicidade."""

#: Classificação usada quando a métrica escolhida não tem régua oficial.
#: Quebras naturais, e não quintis: com contagem de casos, o quintil coloca
#: 37 municípios em cada cor independentemente do valor, e o mapa deixa de
#: distinguir quem tem 3 casos de quem tem 400.
CLASSIFICACAO_SEM_REGUA = "NATURAL"

TODO_O_ESTADO = "— todo o estado —"

#: Altura do mapa. A coluna da direita empilha as proporções, o canal e a
#: epicurva; o mapa precisa fechar na mesma altura.
#: A fonte dos **dados**, que não é a dos parâmetros: a régua vem do boletim
#: da SES-PE, os números vêm da nossa extração do Sinan. Misturar as duas
#: daria ao gráfico a autoridade de um documento que não o publicou.
FONTE_DADOS = "Fonte: Sinan/Ministério da Saúde; população IBGE"

ALTURA_MAPA = 640
ALTURA_LINHA_1 = ALTURA_MAPA

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


# ---------------------------------------------------------------------------
# Cache — só valores primitivos como chave, nunca `Escopo` nem `Navegacao`.
# ---------------------------------------------------------------------------

TTL_DADOS = 24 * 3600


def _escopo(ano: int, nivel: str, mun: str | None, macro: str | None, micro: str | None) -> Escopo:
    """Escopo do recorte corrente, região de saúde e macro inclusive.

    Município aberto manda sobre a região; região sobre a macro; macro sobre
    o estado. É o que faz cards, evolução, pirâmide e composição responderem
    ao clique no mapa — o painel de origem só muda dois cards.
    """
    if nivel == "MUN":
        return Escopo(pack.DOENCA, ano, "MUN", uf=UF_FIXA, mun=mun)
    if micro:
        muns = recortes.municipios_de(micro=micro, uf=UF_FIXA)
    elif macro:
        muns = recortes.municipios_de(macro=macro, uf=UF_FIXA)
    else:
        muns = None
    return Escopo(pack.DOENCA, ano, "UF", uf=UF_FIXA, municipios=tuple(muns) if muns else None)


@st.cache_resource
def _anos() -> list[int]:
    return leitura.anos_disponiveis(pack.DOENCA)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _kpis(ano: int, nivel: str, mun: str | None, macro: str | None, micro: str | None):
    """KPIs do recorte corrente — e o recorte inclui macro e região de saúde.

    O painel de origem, ao entrar numa macro, muda detecção e casos e deixa
    0–14, MB, grau II e a evolução em PE. Aqui os sete saem da mesma soma
    municipal. Município aberto manda sobre a região; região sobre o estado.
    """
    esc = _escopo(ano, nivel, mun, macro, micro)
    if esc.municipios:
        return calc.calcular_regiao(esc, list(esc.municipios))
    return calc.calcular(esc)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _camada(recorte: str, mun: str | None, detalhe: bool, micro: str | None, macro: str | None):
    """Geometria a desenhar: municípios, macrorregiões ou regiões de saúde."""
    uf = UF_FIXA
    if recorte == "MACRO":
        return geo.regioes(uf, "macro")
    if recorte == "MICRO":
        camada = geo.regioes(uf, "micro")
        # Dentro de uma macro só as regiões de saúde dela, como na origem.
        if macro:
            dentro = {recortes._chave(m) for m in recortes.micros(macro, uf=uf)}
            parte = camada[camada["regiao"].map(recortes._chave).isin(dentro)]
            if not parte.empty:
                return parte
        return camada

    municipios = geo.municipios(uf)
    if detalhe and mun:
        return municipios[municipios["cod_mun6"] == mun]
    if micro:
        dentro = set(recortes.municipios_de(micro=micro, uf=uf))
        parte = municipios[municipios["cod_mun6"].isin(dentro)]
        if not parte.empty:
            return parte
    return municipios


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _geojson(recorte, mun, detalhe, micro, macro):
    return mapa.geometrias_geojson(_camada(recorte, mun, detalhe, micro, macro))


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _valores_mapa(ano: int, metrica: str, recorte: str, macro: str | None) -> pd.Series:
    escopo = Escopo(pack.DOENCA, ano, "UF", uf=UF_FIXA)
    if recorte in ("MACRO", "MICRO"):
        return leitura.valores_por_regiao(
            escopo, metrica, "macro" if recorte == "MACRO" else "micro", macro=macro
        )
    return leitura.valores_por_geografia(escopo, metrica)


#: Linhas do tooltip do mapa, como no painel de origem: casos, curas e
#: população, cada uma na cor da métrica. A métrica pintada não repete.
_COMPONENTES_TOOLTIP = (("casos", 0), ("cura", 0), ("pop", 0))


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _detalhes_tooltip(ano: int, metrica: str, recorte: str, macro: str | None):
    return [
        (pack.rotulo(m), _valores_mapa(ano, m, recorte, macro), pack.cor(m), casas)
        for m, casas in _COMPONENTES_TOOLTIP
        if m != metrica
    ]


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _ranking(ano: int, metrica: str, top_n: int, recorte: str, macro: str | None):
    return leitura.ranking(
        Escopo(pack.DOENCA, ano, "UF", uf=UF_FIXA), metrica, top_n, recorte, macro=macro
    )


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _canal(ano: int, nivel: str, mun: str | None, macro, micro, grau: str | None):
    return canal.montar(_escopo(ano, nivel, mun, macro, micro), grau=grau)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _epicurva(
    ano: int, nivel: str, mun: str | None, macro, micro, ano_min: int | None = None
) -> pd.DataFrame:
    # Aqui a janela entra no leitor, e não no `_recortar`: a epicurva monta a
    # série ano a ano, uma consulta por ano, e com dez anos são seis idas ao
    # disco a menos do que com dezesseis.
    return canal.epicurva(_escopo(ano, nivel, mun, macro, micro), ano_min=ano_min)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_anual(nivel: str, mun: str | None, macro, micro, metrica: str) -> pd.DataFrame:
    return leitura.serie_anual(_escopo(_anos()[-1], nivel, mun, macro, micro), metrica)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _piramide(ano: int, nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.piramide_completa(_escopo(ano, nivel, mun, macro, micro), "CASOS")


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_composicao(nivel: str, mun: str | None, macro, micro, variavel: str) -> pd.DataFrame:
    """A distribuição ano a ano. Sem `ano` na chave: a série é a mesma para
    qualquer ano selecionado, e incluir o ano multiplicaria o cache por 16."""
    return leitura.serie_composicao(
        _escopo(_anos()[-1], nivel, mun, macro, micro),
        variavel,
        rotulos=pack.ROTULOS_VALORES.get(variavel),
        numerica=variavel in pack.VARIAVEIS_NUMERICAS,
        ordem="codigo",
    )


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _composicao(ano: int, nivel: str, mun: str | None, macro, micro, variavel: str) -> pd.DataFrame:
    return leitura.composicao(
        _escopo(ano, nivel, mun, macro, micro),
        variavel,
        rotulos=pack.ROTULOS_VALORES.get(variavel),
        numerica=variavel in pack.VARIAVEIS_NUMERICAS,
        ordem="codigo",
    )


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_classificacao(nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.serie_classificacao_operacional(_escopo(_anos()[-1], nivel, mun, macro, micro))


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_qualidade(nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.serie_qualidade(_escopo(_anos()[-1], nivel, mun, macro, micro))


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_0_14(nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.serie_0_14(_escopo(_anos()[-1], nivel, mun, macro, micro))


@st.cache_data(ttl=TTL_DADOS)
def _meses_com_dado(ano: int) -> int:
    return leitura.meses_com_dado(pack.DOENCA, ano)


@st.cache_data(ttl=TTL_DADOS)
def _municipios() -> dict[str, str]:
    """Código de 6 dígitos → nome."""
    camada = geo.municipios(UF_FIXA)
    return dict(zip(camada["cod_mun6"], camada["nome_mun"], strict=True))


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

def _ano_de_abertura() -> int:
    """O ano em que o painel abre: `ANO_PADRAO`, se existir no disco.

    Não é o último ano. Em 2025 a coorte não fechou, e cura, abandono e
    contatos abrem vazios. O recuo cai para o último disponível se a cópia
    de dados ainda não tiver o ano padrão.
    """
    anos = _anos()
    return config.ANO_PADRAO if config.ANO_PADRAO in anos else anos[-1]


if "nav" not in st.session_state:
    st.session_state.nav = Navegacao(doenca=pack.DOENCA, ano=_ano_de_abertura())
nav: Navegacao = st.session_state.nav


def _ao_mudar_metrica() -> None:
    """Aplica a métrica **antes** do rerun, não durante.

    O seletor fica abaixo dos cards de KPI. Lendo o valor no ponto em que o
    widget é criado, os cards — já desenhados — realçavam a métrica antiga,
    e só o rerun seguinte (um segundo clique em qualquer coisa) os punha em
    dia. O callback roda antes do script, então todo mundo vê o valor novo
    na mesma passada. Desmarcar o botão (o `segmented_control` permite)
    devolve a métrica que estava.
    """
    escolhida = st.session_state.get("metrica_sel")
    if escolhida:
        nav.metrica = escolhida
    else:
        st.session_state["metrica_sel"] = nav.metrica


def _ao_clicar_na_legenda() -> None:
    """Guarda a faixa realçada **antes** do mapa ser desenhado.

    A legenda fica embaixo do mapa que ela comanda. Lido no ponto do widget,
    o clique só chegaria ao mapa no rerun seguinte — é o mesmo tropeço dos
    cards acima do seletor de métrica. Clicar na faixa já
    marcada desmarca, e o mapa volta inteiro.
    """
    st.session_state["faixa_realcada"] = st.session_state.get("faixa_legenda")


if st.session_state.get("metrica_sel") != nav.metrica:
    # Primeira passada, ou a métrica mudou por outro caminho: o widget
    # segue `nav`, nunca o contrário.
    st.session_state["metrica_sel"] = nav.metrica

st.markdown(ui.css_base(), unsafe_allow_html=True)
st.markdown(ui.css_layout(), unsafe_allow_html=True)
st.markdown(
    f"<style>:root{{--intro-accent:{pack.CORES['primary']};}}</style>",
    unsafe_allow_html=True,
)


def _local() -> str:
    """Nome do recorte corrente, para subtítulo de card."""
    if nav.nivel == "MUN":
        return nav.nome_mun or nav.mun or "PE"
    if nav.micro:
        return f"RS {nav.micro}"
    if nav.macro:
        return nav.macro
    return "PE"


# ---------------------------------------------------------------------------
# Cabeçalho e faixa de KPIs
# ---------------------------------------------------------------------------

st.markdown(
    ui.faixa_intro(
        f"Painel de Monitoramento da {pack.TITULO} de PE",
        escopo=nav.trilha(),
        cor=pack.CORES["primary"],
    ),
    unsafe_allow_html=True,
)

# Ano parcial se **detecta** pelos meses com dado, não se presume.
if (meses := _meses_com_dado(nav.ano)) < 12:
    st.warning(
        f"**{nav.ano} está incompleto** — dado até "
        f"{MESES[meses - 1] if meses else '—'} ({meses} de 12 meses). "
        f"Não compare o total com anos fechados.",
        icon=":material/schedule:",
    )


def _quadro(metrica: str) -> None:
    """O quadro de parâmetros do boletim, quando a métrica tem um.

    Vai ao lado do gráfico, como no documento: foi o pedido da reunião de
     — a régua precisa estar junto do número, não só na legenda
    do mapa.
    """
    if texto := pack.texto_parametros(metrica):
        titulo, linhas = texto
        st.markdown(
            ui.quadro_parametros(titulo, linhas),
            unsafe_allow_html=True,
        )


#: Janelas de tempo oferecidas para as séries, em anos.
#:
#: Pedido da equipe parceira. Não é só conforto visual: com 16 anos de
#: barras num gráfico de 500px cada uma some, e o boletim publica os
#: indicadores em seis anos (2019–2024) e a detecção em dez (2015–2024). Dez é
#: o padrão daqui pelo mesmo motivo — é o recorte do Gráfico 1.
JANELAS = (5, 10, 15)
JANELA_PADRAO = 10


def _janela() -> int:
    """Quantos anos as séries mostram."""
    return int(st.session_state.get("janela") or JANELA_PADRAO)


def _ano_inicial() -> int:
    """Primeiro ano da janela, contando de trás para frente a partir do ano
    selecionado."""
    return nav.ano - _janela() + 1


def _recortar(dados: pd.DataFrame) -> pd.DataFrame:
    """Deixa na série só os anos da janela.

    Filtrar aqui, e não no leitor, é de propósito: os leitores são
    cacheados por recorte geográfico, e pôr a janela na chave multiplicaria
    o cache por quatro para devolver sempre o mesmo subconjunto.
    """
    if dados.empty or "ano" not in dados:
        return dados
    return dados[(dados["ano"] <= nav.ano) & (dados["ano"] >= _ano_inicial())]


#: Proporção gráfico/calha. O boletim põe a caixa de parâmetros à direita de
#: cada gráfico e é esse o padrão do Ministério; aqui ela vira uma calha de
#: largura fixa, para que as seções empilhadas fiquem alinhadas na vertical
#: como num documento — foi a decisão tomada com a equipe parceira.
CALHA = [7, 3]


def _com_calha(titulo: str, *, ajuda: str = ""):
    """Título da seção e as duas colunas: o gráfico e a calha da direita.

    Devolver as colunas, em vez de desenhar, é o que deixa cada seção decidir
    o que vai na calha — régua do MS onde ela existe, legenda de séries onde
    há mais de uma, base do cálculo nas distribuições. Inventar faixa de
    classificação para quem não tem seria dar autoridade de parâmetro oficial
    a número escolhido por nós.
    """
    st.markdown(ui.titulo_painel(titulo, ajuda=ajuda), unsafe_allow_html=True)
    return st.columns(CALHA, vertical_alignment="top")


def _calha_base(dados: pd.DataFrame, *, complemento: str = "") -> None:
    """A calha das distribuições: quantos registros sustentam o gráfico.

    Distribuição não tem régua — o boletim não põe caixa nos Gráficos 5 a 9.
    O que falta ali é o denominador, que é justamente o que decide se o
    percentual quer dizer alguma coisa.
    """
    if dados.empty:
        return
    total = int(dados["total"].iloc[0])
    linhas = [f"{ui.formatar_inteiro(total)} casos com o campo preenchido"]
    if complemento:
        linhas.append(complemento)
    st.markdown(
        ui.quadro_parametros("Base do cálculo", tuple(linhas), fonte=FONTE_DADOS),
        unsafe_allow_html=True,
    )


def _card(metrica: str, atual, anterior) -> None:
    """Um card de KPI. Os da faixa realçam a métrica ativa do mapa, como na
    origem; os de proporção levam o nome inteiro e não têm ícone, como lá."""
    proporcao = metrica in pack.FRACAO_KPI
    valor = getattr(atual, metrica, None)
    antes = getattr(anterior, metrica, None) if anterior else None
    taxa = metrica in pack.TAXAS
    sub = f"{_local()} • {nav.ano}"
    if fracao := pack.FRACAO_KPI.get(metrica):
        num, den = (getattr(atual, campo, None) for campo in fracao)
        if num is not None and den:
            sub += f" • {ui.formatar_inteiro(num)} de {ui.formatar_inteiro(den)}"
    # A classificação do boletim ao lado do número — é o que transforma
    # "67,1%" em "precário". Pedido da equipe parceira.
    if classe := pack.classe_de(metrica, valor):
        sub += f" • {classe}"
    st.markdown(
        ui.kpi_card(
            pack.rotulo(metrica) if proporcao else pack.rotulo_card(metrica),
            ui.formatar_decimal(valor) if taxa else ui.formatar_inteiro(valor),
            cor=pack.cor(metrica),
            subtitulo=sub,
            selecionado=(not proporcao) and metrica == nav.metrica,
            badge_delta=ui.delta(
                valor, antes, taxa=taxa, bom_se_cai=metrica in pack.BOM_SE_CAI
            ),
            ajuda=" — ".join(
                parte for parte in (pack.rotulo(metrica), pack.descricao(metrica)) if parte
            ),
            icone="" if proporcao else pack.icone(metrica),
        ),
        unsafe_allow_html=True,
    )


atual = anterior = None
with resiliencia.painel("Indicadores"):
    atual = _kpis(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro)
    anterior = (
        _kpis(nav.ano - 1, nav.nivel, nav.mun, nav.macro, nav.micro)
        if nav.ano > min(_anos()) else None
    )
    for coluna, metrica in zip(st.columns(len(KPIS_FAIXA)), KPIS_FAIXA, strict=True):
        with coluna:
            _card(metrica, atual, anterior)


# ---------------------------------------------------------------------------
# Linha 1: mapa à esquerda, proporções e abas à direita
# ---------------------------------------------------------------------------

# Os controles numa faixa própria, acima das duas colunas — como no RecifeTB.
# Dentro da coluna do mapa eles comiam um terço da altura e quebravam em três
# linhas; numa faixa de largura inteira cabem os cinco lado a lado.
with resiliencia.painel("Controles"), st.container(border=True, key="cartao-controles"):
    col_ano, col_metrica, col_recorte, col_cores, col_busca = st.columns(
        [1.1, 4.2, 3.2, 3.2, 2.3], vertical_alignment="top"
    )
    with col_ano:
        escolhido = st.selectbox("Ano", _anos(), index=_anos().index(nav.ano), key="ano")
        if escolhido != nav.ano:
            nav.ano = escolhido
            st.rerun()
    with col_metrica:
        st.segmented_control(
            "Métrica",
            pack.METRICAS_MAPA,
            format_func=pack.rotulo_curto,
            key="metrica_sel",
            on_change=_ao_mudar_metrica,
            help="Define o que o mapa pinta e o que o ranking ordena.",
        )
    with col_recorte:
        # **Sem `key`**: o clique no mapa também move o recorte, e um widget
        # dono do valor entraria em laço com a navegação.
        recorte = st.segmented_control(
            "Nível do mapa",
            RECORTES,
            format_func=lambda r: ROTULO_RECORTE[r],
            default=nav.recorte,
            help="Municípios, ou agregado por macrorregião e região de saúde.",
        )
        if recorte and recorte != nav.recorte:
            nav.definir_recorte(recorte)
            st.rerun()
    with col_cores:
        # "Endemicidade" só onde ela existe. Para `casos`, `casos_0_14` e
        # `cura` o mapa caía em quebras naturais com o botão aceso dizendo
        # "Endemicidade" — classificava de um jeito e anunciava outro. A
        # equipe parceira pegou isso na revisão de outubro, ao ver os números
        # e as cores mudarem com a opção marcada.
        com_regua = pack.tem_regua_oficial(nav.metrica)
        opcoes = [
            c for c in mapa.CLASSIFICACOES if c != "FIXA" or com_regua
        ]
        preferida = st.session_state.get("classificacao", "FIXA")
        # Caiu para a opção de reserva porque a métrica não tem régua, e não
        # porque alguém clicou nela.
        forcada = preferida not in opcoes
        escolhida = CLASSIFICACAO_SEM_REGUA if forcada else preferida
        classificacao = st.segmented_control(
            "Cores",
            opcoes,
            format_func=lambda c: ROTULO_CLASSIFICACAO[c],
            default=escolhida,
            help=AJUDA_CLASSIFICACAO,
        )
        # A escolha guardada é a do usuário, não a de reserva: trocar para
        # Curas e voltar para Detecção devolve a endemicidade, em vez de
        # exigir reescolher. Sem esta guarda, o próprio `default` do controle
        # volta como valor e sobrescreve a preferência no caminho de ida.
        if classificacao and not (forcada and classificacao == CLASSIFICACAO_SEM_REGUA):
            st.session_state["classificacao"] = classificacao
        classificacao = classificacao or escolhida
    with col_busca:
        nomes = _municipios()
        opcoes = [TODO_O_ESTADO, *sorted(nomes, key=lambda c: nomes[c])]
        selecionado = nav.mun if nav.mun in nomes else None
        municipio = st.selectbox(
            "Buscar município",
            opcoes,
            index=0 if selecionado is None else opcoes.index(selecionado),
            format_func=lambda c: c if c == TODO_O_ESTADO else nomes[c],
        )
        if municipio == TODO_O_ESTADO:
            if nav.nivel == "MUN":
                nav.voltar()
                st.rerun()
        elif municipio != nav.mun:
            nav.entrar_municipio(municipio, nome=nomes[municipio])
            st.rerun()


esquerda, direita = st.columns([5, 6], gap="medium")

with esquerda:
    with resiliencia.painel("Mapa"), st.container(border=True, key="cartao-mapa"):
        recorte_mapa = nav.recorte
        serie_mapa = _valores_mapa(nav.ano, nav.metrica, recorte_mapa, nav.macro)
        camada = _camada(recorte_mapa, nav.mun, nav.detalhe, nav.micro, nav.macro)
        chave = "regiao" if recorte_mapa in ("MACRO", "MICRO") else "cod_mun6"

        if serie_mapa.dropna().empty:
            st.markdown(
                ui.painel_vazio("Mapa", "Sem dado para este recorte.", mapa=True),
                unsafe_allow_html=True,
            )
        else:
            desenho, escala = mapa.deck(
                camada,
                serie_mapa,
                chave=chave,
                rampa=pack.rampa_mapa(nav.metrica),
                rotulo_metrica=pack.rotulo(nav.metrica),
                coluna_nome="regiao" if chave == "regiao" else "nome_mun",
                decimais=1 if nav.metrica in pack.TAXAS else 0,
                altura=ALTURA_MAPA,
                geometrias=_geojson(recorte_mapa, nav.mun, nav.detalhe, nav.micro, nav.macro),
                destacado=nav.destacado or (nav.mun if nav.nivel == "MUN" and not nav.detalhe else None),
                metodo=classificacao,
                cortes_fixos=pack.cortes_fixos(nav.metrica),
                detalhes=_detalhes_tooltip(nav.ano, nav.metrica, recorte_mapa, nav.macro),
                faixa_realcada=st.session_state.get("faixa_realcada"),
            )
            # Componente próprio, com `key` **estável**: é o que mantém o deck
            # vivo entre reruns e faz a câmera voar de um recorte ao outro em
            # vez de trocar de slide. O clique volta com um nonce; o último
            # tratado fica em `session_state` para o mesmo evento não navegar
            # duas vezes. Ver docs/mapa-clique.md, "Transição".
            evento = mapa_componente.desenhar(desenho, altura=ALTURA_MAPA, key="mapa")
            # O N de cada classe vai na própria legenda. O painel de origem
            # tem uma segunda caixa, "regiões por classe", que repete as faixas
            # só para acrescentar a contagem — em quintis ela é sempre 37, e
            # em endemicidade é onde o número diz algo ("9 hiperendêmicos").
            contagem = mapa.classificar(serie_mapa, escala).value_counts()

            # A legenda é clicável (pedido da reunião):
            # clicar numa faixa apaga o resto do mapa, e clicar de novo
            # devolve. Ela é um `st.pills` e não mais HTML puro — os
            # quadradinhos de cor, que o widget não tem, entram por CSS.
            faixas = [r for r in escala.rotulos if r in escala.cores]
            nomes_faixa = (
                pack.nomes_fixos(nav.metrica) if classificacao == "FIXA" else None
            )

            def _rotulo_faixa(r: str, _nomes=nomes_faixa, _faixas=faixas) -> str:
                nome = ""
                if _nomes and r in _faixas:
                    indice = _faixas.index(r)
                    if indice < len(_nomes):
                        nome = f"  {_nomes[indice]}"
                return f"{r}{nome}  ({int(contagem.get(r, 0))})"

            st.markdown(
                ui.titulo_legenda(
                    pack.rotulo_mapa(nav.metrica),
                    UNIDADE_RECORTE[recorte_mapa].capitalize(),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                ui.cores_das_faixas("faixa_legenda", [escala.cores[r] for r in faixas]),
                unsafe_allow_html=True,
            )
            st.pills(
                "Faixa em destaque",
                faixas,
                format_func=_rotulo_faixa,
                selection_mode="single",
                key="faixa_legenda",
                on_change=_ao_clicar_na_legenda,
                label_visibility="collapsed",
            )
            sem_dado = int(contagem.get(mapa.ROTULO_SEM_DADO, 0))
            if sem_dado:
                st.caption(
                    f"{sem_dado} {UNIDADE_RECORTE[recorte_mapa]} sem dado, em cinza."
                )

            alvo, nonce = mapa_componente.alvo_do_clique(
                evento, st.session_state.get("clique_mapa")
            )
            if nonce:
                st.session_state["clique_mapa"] = nonce
            if alvo:
                if recorte_mapa == "MACRO" and alvo != nav.macro:
                    nav.entrar_macro(alvo)
                    st.rerun()
                elif recorte_mapa == "MICRO" and alvo != nav.micro:
                    nav.entrar_micro(alvo)
                    st.rerun()
                elif recorte_mapa == "MUN":
                    if alvo == nav.mun and not nav.detalhe:
                        nav.abrir_detalhe()
                        st.rerun()
                    elif alvo != nav.mun and alvo in nomes:
                        nav.entrar_municipio(alvo, nome=nomes[alvo])
                        st.rerun()

        if nav.pode_voltar:
            b1, b2 = st.columns(2)
            if b1.button("◀ Voltar", key="voltar"):
                nav.voltar()
                st.rerun()
            if b2.button("Ver Pernambuco inteiro", key="voltar_pe"):
                nav.reset()
                st.rerun()


with direita:
    with resiliencia.painel("Proporções"):
        for coluna, metrica in zip(st.columns(len(KPIS_PROPORCAO)), KPIS_PROPORCAO, strict=True):
            with coluna:
                _card(metrica, atual, anterior)

    with st.container(border=True, key="cartao-graficos"):
        aba_evolucao, aba_ranking, aba_piramide = st.tabs(
            ["Evolução temporal", f"Ranking de {UNIDADE_RECORTE[nav.recorte]}", "Pirâmide etária"]
        )

        with aba_evolucao, resiliencia.painel("Evolução temporal"):
            c_h, c_g = st.columns([3, 2], vertical_alignment="bottom")
            horizonte = c_h.radio(
                "Horizonte", ["Meses do ano", "Todos os anos"],
                horizontal=True, label_visibility="collapsed",
            )
            grau = None
            if horizonte == "Meses do ano":
                escolha_grau = c_g.selectbox(
                    "Grau de incapacidade",
                    ["Todos os graus", *leitura.GRAUS_SERIE],
                    format_func=lambda g: g.replace("Nao", "Não"),
                )
                grau = None if escolha_grau == "Todos os graus" else escolha_grau

            if horizonte == "Meses do ano":
                canal_atual = _canal(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro, grau)
                figura = grafico_componente.canal_endemico(
                    canal_atual, rotulo=pack.rotulo("incid"), cor=pack.cor("incid"),
                )
                titulo_serie = "Canal endêmico"
                rodape = ""
                if canal_atual.anos:
                    fora = canal.meses_fora_da_faixa(canal_atual)
                    acima = int((fora["posicao"] == "acima").sum())
                    rodape = grafico_componente.AVISO_CANAL.format(
                        n=len(canal_atual.anos),
                        anos=", ".join(str(a) for a in canal_atual.anos),
                    )
                    if acima:
                        rodape += f" Em {nav.ano}, **{acima} de 12 meses** ficaram acima do topo da faixa."
            else:
                serie = _recortar(
                    _serie_anual(nav.nivel, nav.mun, nav.macro, nav.micro, "incid")
                )
                figura = grafico_componente.evolucao_anual(
                    serie, rotulo=pack.rotulo("incid"), cor=pack.cor("incid"), ano=nav.ano,
                )
                titulo_serie = "Taxa de detecção por ano"
                rodape = ""
            if horizonte == "Meses do ano":
                # A série mensal não separa modo de entrada; os cards, sim.
                rodape = (rodape + " " if rodape else "") + (
                    "A série mensal conta todas as entradas no registro "
                    "(recidivas e transferências inclusive), porque a fonte "
                    "mensal não traz o modo de entrada — a soma dos meses fica "
                    "acima dos casos novos do card."
                )
            st.markdown(ui.titulo_painel(titulo_serie, ajuda=rodape), unsafe_allow_html=True)
            # O quadro de parâmetros à direita, como no boletim — **só na
            # vista anual**. A régua é do coeficiente anual; no canal os
            # valores são mensais (2 por 100 mil em PE), e pô-la ali faria
            # o estado parecer "Baixo" doze vezes por ano.
            anual = horizonte != "Meses do ano"
            colunas = st.columns([7, 3], vertical_alignment="top") if anual else None
            grafico = colunas[0] if anual else contextlib.nullcontext()
            with grafico:
                # ECharts vivo (`grafico_componente`): a linha do ano e a faixa
                # deslizam ao mudar o recorte. A `key` muda com o horizonte
                # porque canal e barras anuais são gráficos diferentes.
                grafico_componente.desenhar(
                    figura, altura=ALTURA_LINHA_1 - 320,
                    key="canal" if horizonte == "Meses do ano" else "anual",
                )
            if anual:
                with colunas[1]:
                    _quadro("incid")

            # Os botões de janela ficam sobre o gráfico e alinhados à
            # direita, como num gráfico de cotação — foi o desenho pedido em
            #: Valem para todas as séries de tempo da página, e
            # não só para esta: é um controle só, no lugar em que ele é mais
            # óbvio de usar.
            titulo_epi, botoes_epi = st.columns([4, 6], vertical_alignment="center")
            with titulo_epi:
                st.markdown(
                    ui.titulo_painel(
                        "Epicurva por mês",
                        ajuda="Casos por mês de diagnóstico, em série contínua. "
                              "A janela vale também para as demais séries de "
                              "tempo da página.",
                    ),
                    unsafe_allow_html=True,
                )
            with botoes_epi:
                st.segmented_control(
                    "Janela",
                    JANELAS,
                    format_func=lambda j: f"{j}a",
                    default=st.session_state.get("janela", JANELA_PADRAO),
                    key="janela",
                    label_visibility="collapsed",
                )
            grafico_componente.desenhar(
                grafico_componente.epicurva(
                    _epicurva(
                        nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro,
                        _ano_inicial(),
                    ),
                    rotulo="Casos", cor=pack.cor("casos"), ano_em_foco=nav.ano,
                ),
                altura=220, key="epicurva",
            )

        with aba_ranking, resiliencia.painel("Ranking"):
            maximo = {"MUN": 30, "MACRO": 4, "MICRO": 12}[nav.recorte]
            top_n = (
                st.slider("Quantos exibir", 5, maximo, min(15, maximo), step=5, key=f"top_n_{nav.recorte}")
                if maximo > 5 else maximo
            )
            tabela = _ranking(nav.ano, nav.metrica, top_n, nav.recorte, nav.macro)
            escala_mapa = mapa.escala(
                _valores_mapa(nav.ano, nav.metrica, nav.recorte, nav.macro),
                pack.rampa_mapa(nav.metrica),
                metodo=classificacao,
                cortes_fixos=pack.cortes_fixos(nav.metrica),
                decimais=1 if nav.metrica in pack.TAXAS else 0,
            )
            # ECharts vivo: ao mudar recorte, ano ou métrica as barras deslizam
            # para o valor e a posição novos.
            evento_rank = grafico_componente.desenhar(
                grafico_componente.ranking(
                    tabela,
                    rotulo=pack.rotulo(nav.metrica),
                    cor=pack.cor(nav.metrica),
                    escala=escala_mapa,
                    selecionado=nav.destacado if nav.recorte == "MUN" else None,
                    largura_rotulo=grafico_componente.LARGURA_ROTULO_RANKING,
                ),
                altura=max(
                    ALTURA_LINHA_1 - 200,
                    grafico_componente.ALTURA_MIN_RANKING,
                    grafico_componente.ALTURA_BARRA_RANKING * len(tabela) + grafico_componente.ALTURA_EIXO_RANKING,
                ),
                key="ranking",
            )
            clicado, nonce_rank = grafico_componente.alvo_do_clique(
                evento_rank, st.session_state.get("clique_ranking")
            )
            if nonce_rank:
                st.session_state["clique_ranking"] = nonce_rank
            if clicado:
                if nav.recorte == "MACRO" and clicado != nav.macro:
                    nav.entrar_macro(clicado)
                    st.rerun()
                elif nav.recorte == "MICRO" and clicado != nav.micro:
                    nav.entrar_micro(clicado)
                    st.rerun()
                elif nav.recorte == "MUN" and clicado != nav.destacado:
                    nav.destacar(clicado, nome=_municipios().get(clicado))
                    st.rerun()

        with aba_piramide, resiliencia.painel("Pirâmide etária"):
            dados_pir = _piramide(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro)
            por_100mil = st.toggle(
                "Taxa de detecção por 100 mil habitantes",
                help=(
                    "Casos da faixa etária ÷ população da mesma faixa × 100.000. "
                    "Desconta o tamanho de cada faixa, então compara grupos de "
                    "tamanhos diferentes. Desligado, o gráfico mostra a contagem "
                    "de casos."
                ),
            )
            grafico_componente.desenhar(
                grafico_componente.piramide(dados_pir, rotulo="Casos", por_100mil=por_100mil),
                altura=max(ALTURA_LINHA_1 - 160, 280, 30 * dados_pir["faixa_etaria"].nunique() + 80),
                key="piramide",
            )


# ---------------------------------------------------------------------------
# Linha 2: indicadores de qualidade do programa
# ---------------------------------------------------------------------------
#
# Os quatro da Tabela 2 do boletim que faltavam no painel: cura, contatos
# examinados, GIF avaliado e abandono. Ficam numa faixa própria, e não entre
# os KPIs do topo, porque respondem outra pergunta — não "quanta doença há",
# mas "como o programa está indo". Cada card traz a classificação oficial.

AJUDA_QUALIDADE = (
    "Indicadores de acompanhamento do programa, nos parâmetros do Boletim "
    "Epidemiológico de Hanseníase. Cura, contatos e abandono são por **ano "
    "de diagnóstico**, não por coorte: o boletim fecha a coorte (PB do ano "
    "anterior, MB de dois anos antes), o que exige o microdado. Em PE 2024 a "
    "diferença é de 1 a 4 pontos — ver docs/paridade-hanseniase.md §8."
)

with resiliencia.painel("Indicadores de qualidade"), st.container(
    border=True, key="cartao-qualidade"
):
    st.markdown(
        ui.titulo_painel(
            "Indicadores de qualidade do programa", ajuda=AJUDA_QUALIDADE
        ),
        unsafe_allow_html=True,
    )
    for coluna, metrica in zip(
        st.columns(len(pack.INDICADORES_QUALIDADE)),
        pack.INDICADORES_QUALIDADE,
        strict=True,
    ):
        with coluna:
            _card(metrica, atual, anterior)

    # A régua destes quatro já vai ao lado dos gráficos deles, na seção de
    # tópicos. Repeti-la aqui, embaixo de cards que já dizem "Regular", era
    # meia tela de texto dizendo o que o card diz. Saiu a
    # pedido da equipe parceira.

    # Coorte aberta: dizer **por que** três dos quatro estão vazios. Sem
    # isto o card em branco parece defeito, e o número que estava ali antes
    # ("30,4% de cura" em 2025) parecia programa ruim.
    if getattr(atual, "coorte_aberta", False):
        st.caption(
            f"Cura, abandono e contatos não aparecem em {nav.ano}: a coorte "
            f"ainda não fechou — {ui.formatar_inteiro(atual.saidas)} de "
            f"{ui.formatar_inteiro(atual.gif_base)} casos têm saída de "
            f"tratamento registrada "
            f"({ui.formatar_decimal((atual.cobertura_saidas or 0) * 100, 0)}%). "
            f"Esses indicadores se preenchem ao longo do acompanhamento; o "
            f"boletim os publica até o último ano de coorte fechada."
        )


# ---------------------------------------------------------------------------
# Linha 3: tópicos de interesse
# ---------------------------------------------------------------------------

ALTURA_MINIMA_TOPICO = 175

#: O tom claro que acompanha o roxo do boletim nas barras empilhadas. O
#: documento não empilha nada, então esta é escolha nossa — e por isso é um
#: clareamento do roxo dele, não uma terceira cor.
COR_BARRA_CLARA = "#B9AFD6"

#: Altura dos tópicos em coluna. Fixa, e não proporcional ao número de
#: categorias: em coluna as categorias crescem para o lado, não para baixo.
ALTURA_TOPICO_COLUNA = 260
LARGURA_ROTULO_TOPICO = 150

AJUDA_TOPICOS = (
    "Distribuição de cada variável da ficha de hanseníase no ano e no "
    "território selecionados — um ano por vez, não a série inteira. "
    "As três que abrem são as que o Boletim Epidemiológico comenta na análise "
    "(Gráficos 6, 8 e 9); raça/cor e escolaridade, que ele também publica, "
    "estão a um clique no seletor. Cada uma é desenhada como lá — coluna ou "
    "barra deitada — e na ordem do campo, não por frequência. Abaixo de cinco "
    "registros o percentual não é publicável e só a contagem aparece."
)


#: As duas vistas de um tópico, e o rótulo no botão.
VISTAS_TOPICO = {
    "ANO": "Ano selecionado",
    "SERIE": "Série histórica",
}


def _vista_dos_topicos() -> str:
    return st.session_state.get("vista_topicos") or "ANO"


def _desenhar_topico_em_serie(variavel: str, rotulo: str) -> None:
    """A distribuição ano a ano, em colunas empilhadas.

    Pedido da equipe parceira em outubro: o gráfico de um ano mostra a
    fotografia, e o que ela queria ver era o movimento. Em forma clínica, a
    tuberculoide cai de 27% para 8% entre 2010 e 2025 enquanto a dimorfa sobe
    de 32% para 45%, e a não classificada quintuplica.
    """
    dados = _recortar(
        _serie_composicao(nav.nivel, nav.mun, nav.macro, nav.micro, variavel)
    )
    grafico, calha = _com_calha(
        f"Proporção de casos segundo {rotulo.lower()} por ano — {_local()}"
    )
    with grafico:
        grafico_componente.desenhar(
            grafico_componente.composicao_por_ano(dados, cor=pack.COR_BOLETIM),
            altura=ALTURA_TOPICO_COLUNA,
            key=f"topico-serie-{variavel}",
        )
    with calha:
        # Calha própria, e não `_calha_base`: aqui o denominador é um por ano,
        # não um só. Dizer "2.466 casos" seria falso — esse é o total de um
        # ano, e a série tem dezesseis.
        if dados.empty:
            return
        anos = sorted(dados["ano"].unique())
        por_ano = dados.groupby("ano")["n"].sum()
        st.markdown(
            ui.quadro_parametros(
                "Base do cálculo",
                (
                    f"{int(anos[0])} a {int(anos[-1])}, "
                    f"{ui.formatar_inteiro(float(por_ano.sum()))} casos com o "
                    f"campo preenchido",
                    f"Por ano: de {ui.formatar_inteiro(float(por_ano.min()))} a "
                    f"{ui.formatar_inteiro(float(por_ano.max()))}",
                    "Cada coluna soma 100%: o que se compara é a composição, "
                    "não o volume de casos.",
                ),
                fonte=FONTE_DADOS,
            ),
            unsafe_allow_html=True,
        )


def _desenhar_topico(variavel: str, rotulo: str) -> None:
    if _vista_dos_topicos() == "SERIE":
        _desenhar_topico_em_serie(variavel, rotulo)
        return
    dados = _composicao(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro, variavel)
    # Coluna ou barra deitada conforme o boletim desenha aquela variável —
    # ele não usa o mesmo gráfico para tudo. Ver `pack.ORIENTACAO_TOPICO`.
    orientacao = pack.orientacao_topico(variavel, dados.get("categoria", []))
    altura = (
        ALTURA_TOPICO_COLUNA
        if orientacao == "coluna"
        else max(grafico_componente.altura_composicao(len(dados)), ALTURA_MINIMA_TOPICO)
    )
    grafico, calha = _com_calha(
        f"Proporção de casos segundo {rotulo.lower()} — {_local()}, {nav.ano}"
    )
    with grafico:
        # ECharts vivo, uma instância por variável: ao clicar no mapa as barras
        # deslizam juntas para o recorte novo.
        grafico_componente.desenhar(
            grafico_componente.composicao(
                dados,
                rotulo="",
                cor=pack.COR_BOLETIM,
                largura_rotulo=LARGURA_ROTULO_TOPICO,
                # A ordem já vem do leitor (a do campo, como no boletim); o
                # gráfico não reordena por frequência por cima dela.
                ordem_dos_dados=True,
                orientacao=orientacao,
            ),
            altura=altura,
            key=f"topico-{variavel}",
        )
    with calha:
        # "casos" e não "casos novos": a distribuição sai do `sinan_landing`,
        # que não cruza variável com modo de entrada — o boletim escreve
        # "casos novos" nos Gráficos 5 a 9 e nós não podemos. Paridade §1.1.
        _calha_base(
            dados,
            complemento=(
                "Base pequena demais para percentual"
                if not dados.empty and dados["pct"].isna().all()
                else ""
            ),
        )


#: Os indicadores do programa que viram gráfico, e o rótulo no seletor.
#:
#: Entram no **mesmo** seletor das variáveis da ficha:
#: estavam fixos dentro do cartão dos tópicos, e limpar o seletor deixava
#: quatro gráficos órfãos numa caixa que dizia "escolha o que exibir".
INDICADORES_EM_SERIE = {
    "contatos_pct": "Contatos examinados (%)",
    "gif_avaliado_pct": "GIF avaliado no diagnóstico (%)",
    "grau2_pct": "GIF II no diagnóstico (%)",
    "cura_abandono": "Cura e abandono (%)",
}


def _desenhar_indicador(chave: str, serie: pd.DataFrame) -> None:
    """Um dos Gráficos 10 a 13 do boletim, com a régua do MS na calha."""
    if chave == "cura_abandono":
        grafico, calha = _com_calha(
            "Proporção de cura e de abandono de tratamento",
            ajuda="Saídas por cura e por abandono sobre todas as saídas "
                  "registradas no ano de diagnóstico. O boletim fecha a coorte "
                  "(PB do ano anterior, MB de dois anos antes), que só o "
                  "microdado permite; ver docs/paridade-hanseniase.md §8.",
        )
        with grafico:
            grafico_componente.desenhar(
                grafico_componente.comparativo_anual(
                    serie,
                    series={
                        "cura_pct": ("% Cura", pack.COR_BOLETIM),
                        "abandono_pct": ("% Abandono", pack.COR_BOLETIM_SECUNDARIA),
                    },
                ),
                altura=300, key="cura-abandono",
            )
        with calha:
            # Duas caixas, como no boletim: as réguas são diferentes, e a do
            # abandono corre ao contrário — lá, "Bom" é o valor **baixo**.
            _quadro("cura_pct")
            _quadro("abandono_pct")
        return

    titulo, ajuda, metrica, tipo = {
        "contatos_pct": (
            "Proporção de contatos examinados entre os registrados",
            "Soma dos contatos examinados dividida pela dos registrados, por "
            "ano de diagnóstico. Anos de coorte aberta ficam vazios: o exame "
            "de contatos acontece ao longo do acompanhamento.",
            "contatos_pct",
            # Linha, e não barra: o Gráfico 10 do boletim é uma linha com
            # marcador quadrado. Barra dava a impressão de contagem.
            "linha",
        ),
        "gif_avaliado_pct": (
            "Proporção de casos com grau de incapacidade avaliado no diagnóstico",
            "Casos com grau 0, I ou II registrado, sobre o total de casos. "
            "Mede preenchimento da ficha, não gravidade.",
            "gif_avaliado_pct",
            "barra",
        ),
        "grau2_pct": (
            "Proporção de casos com grau de incapacidade física II no diagnóstico",
            "Grau II sobre os casos com o campo de avaliação preenchido, "
            "incluindo 'não avaliado' — o denominador do painel de origem.",
            "prop_grau2_pct",
            "barra",
        ),
    }[chave]

    grafico, calha = _com_calha(titulo, ajuda=ajuda)
    with grafico:
        grafico_componente.desenhar(
            # Eixo em 0–100 como no boletim, e não colado nos valores: o grau
            # II anda entre 5% e 13%, e um eixo automático faria essa faixa
            # ocupar a tela inteira.
            grafico_componente.indicador_anual(
                serie,
                coluna=chave,
                rotulo="Proporção (%)",
                cor=pack.COR_BOLETIM,
                ano=nav.ano,
                tipo=tipo,
            ),
            altura=260, key=f"indicador-{chave}",
        )
    with calha:
        _quadro(metrica)
        if chave == "gif_avaliado_pct":
            # O Gráfico 11 tem **duas** séries: avaliado no diagnóstico e na
            # cura. A segunda exige cruzar o grau com o desfecho caso a caso,
            # e a extração agregada não cruza — dizer isso é melhor que
            # desenhar meio gráfico e deixar quem conhece o boletim
            # procurando a barra que falta. Ver docs/pedido-microdado.md.
            st.caption(
                "O boletim traz também o **% avaliado na cura**, que depende "
                "do microdado: a extração não cruza grau de incapacidade com "
                "desfecho de tratamento."
            )


with resiliencia.painel("Tópicos de interesse"), st.container(border=True, key="cartao-composicao"):
    st.markdown(ui.titulo_painel("Tópicos de interesse", ajuda=AJUDA_TOPICOS), unsafe_allow_html=True)
    planas = pack.variaveis_planas()
    # Um seletor só para o cartão inteiro: os indicadores do boletim primeiro,
    # depois as variáveis da ficha. Dois grupos numa lista só, e não dois
    # seletores, porque o que o usuário decide é a mesma coisa nos dois casos
    # — o que aparece nesta caixa.
    escolhidas = st.multiselect(
        "O que exibir",
        [*INDICADORES_EM_SERIE, *planas],
        default=[*INDICADORES_EM_SERIE, *pack.VARIAVEIS_DESTAQUE],
        format_func=lambda c: INDICADORES_EM_SERIE.get(c) or planas[c],
        label_visibility="collapsed",
        placeholder="Escolha os indicadores e as variáveis a exibir",
    )
    st.segmented_control(
        "Vista",
        list(VISTAS_TOPICO),
        format_func=lambda v: VISTAS_TOPICO[v],
        default=_vista_dos_topicos(),
        key="vista_topicos",
        label_visibility="collapsed",
        help=(
            "**Ano selecionado** mostra a distribuição do ano escolhido acima, "
            "como o boletim publica. **Série histórica** mostra como essa "
            "distribuição mudou ano a ano, em colunas que somam 100%."
        ),
    )
    if not escolhidas:
        st.caption("Nada escolhido. Use o campo acima para trazer o que interessa.")
    else:
        # A série dos indicadores é uma consulta só, e só acontece se algum
        # deles estiver na tela.
        serie_indicadores = (
            _recortar(_serie_qualidade(nav.nivel, nav.mun, nav.macro, nav.micro))
            if any(c in INDICADORES_EM_SERIE for c in escolhidas)
            else pd.DataFrame()
        )
        for escolha in escolhidas:
            if escolha in INDICADORES_EM_SERIE:
                _desenhar_indicador(escolha, serie_indicadores)
            else:
                _desenhar_topico(escolha, planas[escolha])


# ---------------------------------------------------------------------------
# Linha 4: os dois temporais do rodapé do painel de origem
# ---------------------------------------------------------------------------

with resiliencia.painel("Séries anuais"), st.container(border=True, key="cartao-series"):
    # Um por linha, e não mais lado a lado: com a calha da
    # legenda ao lado, dois gráficos por linha deixariam cada um com um terço
    # da página. O boletim também dá uma linha inteira a cada gráfico.
    grafico_mb, calha_mb = _com_calha(
        "Classificação operacional por ano",
        ajuda="Casos PB e MB por ano de diagnóstico; a linha é a proporção "
              "de multibacilares sobre os classificados.",
    )
    with grafico_mb:
        grafico_componente.desenhar(
            grafico_componente.barras_empilhadas_com_linha(
                _recortar(_serie_classificacao(nav.nivel, nav.mun, nav.macro, nav.micro)),
                barras={"pb": "PB - Paucibacilar", "mb": "MB - Multibacilar"},
                linha="prop_mb",
                rotulo_linha="Proporção MB (%)",
                cores={"pb": COR_BARRA_CLARA, "mb": pack.COR_BOLETIM},
                cor_linha=pack.COR_BOLETIM_SECUNDARIA,
            ),
            altura=300, key="classificacao-operacional",
        )
    with calha_mb:
        # Classificação operacional não tem parâmetro no boletim, e inventar
        # um seria dar régua oficial a corte nosso. A calha fica com a base do
        # cálculo; a legenda das séries vai embaixo do gráfico, como lá.
        st.markdown(
            ui.quadro_parametros(
                "Base do cálculo",
                ("Casos com classificação operacional preenchida",),
                fonte=FONTE_DADOS,
            ),
            unsafe_allow_html=True,
        )

    grafico_014, calha_014 = _com_calha(
        "Casos de 0 a 14 anos por ano",
        ajuda="Casos em menores de 15 anos por ano de diagnóstico; a linha "
              "é a taxa por 100 mil habitantes dessa faixa etária. Conta "
              "todas as entradas no registro, não só casos novos: a "
              "extração não cruza idade com modo de entrada, e por isso "
              "a taxa fica acima da régua ao lado, que o Ministério "
              "define sobre casos novos.",
    )
    with grafico_014:
        grafico_componente.desenhar(
            grafico_componente.barras_empilhadas_com_linha(
                _recortar(_serie_0_14(nav.nivel, nav.mun, nav.macro, nav.micro)),
                barras={"casos": "Casos (0 a 14)"},
                linha="taxa",
                rotulo_linha="Taxa de detecção 0–14 (por 100 mil)",
                cores={"casos": pack.COR_BOLETIM},
                cor_linha=pack.COR_BOLETIM_SECUNDARIA,
                casas_linha=1,
                # O N dentro da barra e o coeficiente sobre o ponto, como o
                # Gráfico 2 imprime.
                rotulos=True,
            ),
            altura=300, key="casos-0-14",
        )
    with calha_014:
        # Este tem régua: é o Gráfico 2 do boletim, e é só ela que a calha
        # carrega — a legenda das séries ficou embaixo do gráfico, como lá.
        _quadro("taxa_det_0_14")


st.caption(
    f"Fonte: Sinan/Ministério da Saúde; população IBGE. Recorte por município de "
    f"residência. Série exibida: {_anos()[0]}–{_anos()[-1]}. Dados preliminares, "
    f"sujeitos a alteração — o Sinan é atualizado retroativamente.  \n"
    f"Reconstrução do painel de monitoramento da hanseníase de PE da equipe parceira, "
    f"conferida card a card — ver tests/paridade/referencia_origem.json. Como cada "
    f"número é calculado, e onde difere do Ministério da Saúde: docs/metodologia.md "
    f"e docs/paridade-hanseniase.md."
)
