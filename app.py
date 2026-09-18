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

import altair as alt
import pandas as pd
import streamlit as st

from src import doencas, graficos, mapa, resiliencia
from src.data import canal, geo, leitura, recortes
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

**Endemicidade** usa os parâmetros oficiais do Ministério da Saúde: baixa (< 2), média (2–10), alta (10–20), muito alta (20–40) e hiperendêmica (≥ 40 por 100 mil). É a única que deixa dois anos comparáveis."""

TODO_O_ESTADO = "— todo o estado —"

#: Altura do mapa. A coluna da direita empilha as proporções, o canal e a
#: epicurva; o mapa precisa fechar na mesma altura.
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
def _epicurva(ano: int, nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return canal.epicurva(_escopo(ano, nivel, mun, macro, micro))


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_anual(nivel: str, mun: str | None, macro, micro, metrica: str) -> pd.DataFrame:
    return leitura.serie_anual(_escopo(_anos()[-1], nivel, mun, macro, micro), metrica)


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _piramide(ano: int, nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.piramide_completa(_escopo(ano, nivel, mun, macro, micro), "CASOS")


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _composicao(ano: int, nivel: str, mun: str | None, macro, micro, variavel: str) -> pd.DataFrame:
    return leitura.composicao(
        _escopo(ano, nivel, mun, macro, micro),
        variavel,
        rotulos=pack.ROTULOS_VALORES.get(variavel),
        numerica=variavel in pack.VARIAVEIS_NUMERICAS,
    )


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def _serie_classificacao(nivel: str, mun: str | None, macro, micro) -> pd.DataFrame:
    return leitura.serie_classificacao_operacional(_escopo(_anos()[-1], nivel, mun, macro, micro))


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

if "nav" not in st.session_state:
    st.session_state.nav = Navegacao(doenca=pack.DOENCA, ano=_anos()[-1])
nav: Navegacao = st.session_state.nav

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
    st.markdown(
        ui.kpi_card(
            pack.rotulo(metrica) if proporcao else pack.rotulo_curto(metrica),
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
        nav.metrica = st.segmented_control(
            "Métrica",
            pack.METRICAS_MAPA,
            format_func=pack.rotulo_curto,
            default=nav.metrica,
            help="Define o que o mapa pinta e o que o ranking ordena.",
        ) or nav.metrica
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
        classificacao = st.segmented_control(
            "Cores",
            mapa.CLASSIFICACOES,
            format_func=lambda c: ROTULO_CLASSIFICACAO[c],
            default=st.session_state.get("classificacao", "QUARTIL"),
            help=AJUDA_CLASSIFICACAO,
        )
        if classificacao:
            st.session_state["classificacao"] = classificacao
        classificacao = st.session_state.get("classificacao", "QUARTIL")
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
            )
            evento = st.pydeck_chart(
                desenho,
                width="stretch",
                height=ALTURA_MAPA,
                on_select="rerun",
                selection_mode="single-object",
                key=(
                    f"mapa-{recorte_mapa}-{nav.macro or ''}-{nav.micro or ''}-{nav.mun or ''}"
                    f"-{'det' if nav.detalhe else ''}-{nav.ano}-{nav.metrica}-{classificacao}"
                ),
            )
            st.components.v1.html(ui.script_travar_zoom(), height=0)
            legenda, classes = st.columns([3, 2], vertical_alignment="top")
            legenda.markdown(
                mapa.legenda(escala, pack.rotulo(nav.metrica)), unsafe_allow_html=True
            )
            # "Regiões por classe", como no painel de origem: quantas unidades
            # caem em cada cor.
            contagem = mapa.classificar(serie_mapa.dropna(), escala).value_counts().sort_index()
            classes.markdown(
                ui.tabela_classes(escala, contagem, unidade=UNIDADE_RECORTE[recorte_mapa]),
                unsafe_allow_html=True,
            )

            alvo = mapa.alvo_do_clique(evento)
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
                figura = graficos.canal_endemico(
                    canal_atual,
                    rotulo=pack.rotulo("incid"),
                    cor=pack.cor("incid"),
                    altura=ALTURA_LINHA_1 - 320,
                )
                titulo_serie = "Canal endêmico"
                rodape = ""
                if canal_atual.anos:
                    fora = canal.meses_fora_da_faixa(canal_atual)
                    acima = int((fora["posicao"] == "acima").sum())
                    rodape = graficos.AVISO_CANAL.format(
                        n=len(canal_atual.anos),
                        anos=", ".join(str(a) for a in canal_atual.anos),
                    )
                    if acima:
                        rodape += f" Em {nav.ano}, **{acima} de 12 meses** ficaram acima do topo da faixa."
            else:
                serie = _serie_anual(nav.nivel, nav.mun, nav.macro, nav.micro, "incid")
                figura = graficos.evolucao_anual(
                    serie, rotulo=pack.rotulo("incid"), cor=pack.cor("incid"),
                    altura=ALTURA_LINHA_1 - 320, ano=nav.ano,
                )
                titulo_serie = "Taxa de detecção por ano"
                rodape = ""
            st.markdown(ui.titulo_painel(titulo_serie, ajuda=rodape), unsafe_allow_html=True)
            st.altair_chart(figura, width="stretch")

            st.markdown(ui.titulo_painel("Epicurva por mês"), unsafe_allow_html=True)
            st.altair_chart(
                graficos.epicurva(
                    _epicurva(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro),
                    rotulo="Casos", cor=pack.cor("casos"), ano_em_foco=nav.ano,
                ),
                width="stretch",
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
            escolha = alt.selection_point(name="barra", fields=["chave"], on="click")
            evento_rank = st.altair_chart(
                graficos.ranking(
                    tabela,
                    rotulo=pack.rotulo(nav.metrica),
                    cor=pack.cor(nav.metrica),
                    selecao=escolha,
                    altura_minima=ALTURA_LINHA_1 - 200,
                    escala=escala_mapa,
                ),
                width="stretch",
                on_select="rerun",
                key=f"rank-{nav.ano}-{nav.metrica}-{nav.recorte}-{nav.macro or ''}-{classificacao}-{top_n}",
            )
            if clicado := graficos.alvo_do_clique(evento_rank, "barra"):
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
                "Por 100 mil habitantes",
                help="Desconta o tamanho de cada faixa etária na população.",
            )
            st.altair_chart(
                graficos.piramide(
                    dados_pir, rotulo="Casos", por_100mil=por_100mil,
                    altura=ALTURA_LINHA_1 - 160,
                ),
                width="stretch",
            )


# ---------------------------------------------------------------------------
# Linha 2: tópicos de interesse
# ---------------------------------------------------------------------------

TOPICOS_POR_LINHA = 2
ALTURA_MINIMA_TOPICO = 175
LARGURA_ROTULO_TOPICO = 150

AJUDA_TOPICOS = (
    "Distribuição de cada variável da ficha de hanseníase no recorte corrente. "
    "As seis que abrem são as que a vigilância olha primeiro; as demais estão "
    "no seletor. Abaixo de cinco registros o percentual não é publicável e só "
    "a contagem aparece."
)


def _desenhar_topico(variavel: str, rotulo: str, altura: int) -> None:
    dados = _composicao(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro, variavel)
    st.altair_chart(
        graficos.composicao(
            dados,
            rotulo=rotulo,
            cor=pack.cor("prop_mb_pct"),
            altura=altura,
            largura_rotulo=LARGURA_ROTULO_TOPICO,
            ordem_dos_dados=variavel in pack.VARIAVEIS_NUMERICAS,
        ),
        width="stretch",
    )
    if not dados.empty and dados["pct"].isna().all():
        st.caption(
            f"Base de {int(dados['total'].iloc[0])} registros — pequena demais "
            f"para percentual. Só a contagem aparece."
        )


with resiliencia.painel("Tópicos de interesse"), st.container(border=True, key="cartao-composicao"):
    st.markdown(ui.titulo_painel("Tópicos de interesse", ajuda=AJUDA_TOPICOS), unsafe_allow_html=True)
    planas = pack.variaveis_planas()
    escolhidas = st.multiselect(
        "Variáveis",
        list(planas),
        default=list(pack.VARIAVEIS_DESTAQUE),
        format_func=lambda v: planas[v],
        label_visibility="collapsed",
        placeholder="Escolha as variáveis a exibir",
    )
    if not escolhidas:
        st.caption("Nenhuma variável escolhida. Use o campo acima para trazer as que interessam.")
    else:
        for inicio in range(0, len(escolhidas), TOPICOS_POR_LINHA):
            linha = escolhidas[inicio : inicio + TOPICOS_POR_LINHA]
            altura = max(
                graficos.altura_composicao(len(_composicao(nav.ano, nav.nivel, nav.mun, nav.macro, nav.micro, v)))
                for v in linha
            )
            altura = max(altura, ALTURA_MINIMA_TOPICO)
            for coluna, variavel in zip(st.columns(TOPICOS_POR_LINHA, gap="medium"), linha, strict=False):
                with coluna:
                    _desenhar_topico(variavel, planas[variavel], altura)


# ---------------------------------------------------------------------------
# Linha 3: os dois temporais do rodapé do painel de origem
# ---------------------------------------------------------------------------

with resiliencia.painel("Séries anuais"), st.container(border=True, key="cartao-series"):
    col_mb, col_014 = st.columns(2, gap="medium")
    with col_mb:
        st.markdown(
            ui.titulo_painel(
                "Classificação operacional por ano",
                ajuda="Casos PB e MB por ano de diagnóstico; a linha é a proporção "
                      "de multibacilares sobre os classificados.",
            ),
            unsafe_allow_html=True,
        )
        st.altair_chart(
            graficos.barras_empilhadas_com_linha(
                _serie_classificacao(nav.nivel, nav.mun, nav.macro, nav.micro),
                barras={"pb": "PB - Paucibacilar", "mb": "MB - Multibacilar"},
                linha="prop_mb",
                rotulo_linha="Proporção MB (%)",
                cores={"pb": "#C4B5FD", "mb": pack.cor("prop_mb_pct")},
                cor_linha=pack.cor("incid"),
            ),
            width="stretch",
        )
    with col_014:
        st.markdown(
            ui.titulo_painel(
                "Casos de 0 a 14 anos por ano",
                ajuda="Casos em menores de 15 anos por ano de diagnóstico; a linha "
                      "é a taxa por 100 mil habitantes dessa faixa etária.",
            ),
            unsafe_allow_html=True,
        )
        st.altair_chart(
            graficos.barras_empilhadas_com_linha(
                _serie_0_14(nav.nivel, nav.mun, nav.macro, nav.micro),
                barras={"casos": "Casos (0 a 14)"},
                linha="taxa",
                rotulo_linha="Taxa de detecção 0–14 (por 100 mil)",
                cores={"casos": "#C4B5FD"},
                cor_linha=pack.cor("taxa_det_0_14"),
                formato_linha=".2f",
            ),
            width="stretch",
        )


st.caption(
    f"Fonte: Sinan/Ministério da Saúde; população IBGE. Recorte por município de "
    f"residência. Série exibida: {_anos()[0]}–{_anos()[-1]}. Dados preliminares, "
    f"sujeitos a alteração — o Sinan é atualizado retroativamente.  \n"
    f"Reconstrução do painel de monitoramento da hanseníase de PE da equipe parceira, "
    f"conferida card a card — ver tests/paridade/referencia_origem.json. Como cada "
    f"número é calculado, e onde difere do Ministério da Saúde: docs/metodologia.md "
    f"e docs/paridade-hanseniase.md."
)
