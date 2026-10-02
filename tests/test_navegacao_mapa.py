"""Critério de pronto da semana 3.

"Os três níveis e os três recortes navegam sem estado inconsistente."

Cliquei pelos caminhos principais no navegador, mas isso cobre um punhado de
combinações. Aqui elas são percorridas todas, exercitando a mesma cadeia que a
aplicação usa: a máquina de estados decide o recorte, a camada de dados
responde por ele e a geometria tem de casar chave a chave.
"""

from __future__ import annotations

import pytest

from src import mapa
from src.data import geo, leitura, recortes
from src.data.escopo import Escopo
from src.doencas import hanseniase as tb
from src.estado import RECORTES, Navegacao

ANO = 2024

#: As métricas que o mapa sabe pintar hoje.
PINTAVEIS = ("incid", "casos", "cura", "pop")


def _camada_e_chave(nav: Navegacao):
    """Reproduz a escolha de camada que a aplicação faz."""
    if nav.nivel == "BR":
        return geo.ufs(), "uf"
    if nav.recorte == "MACRO":
        return geo.regioes("PE", "macro"), "regiao"
    if nav.recorte == "MICRO":
        return geo.regioes("PE", "micro"), "regiao"
    return geo.municipios(nav.uf), "cod_mun6"


def _valores(nav: Navegacao, metrica: str):
    if nav.recorte in ("MACRO", "MICRO") and nav.nivel != "BR":
        return leitura.valores_por_regiao(
            nav.escopo, metrica, "macro" if nav.recorte == "MACRO" else "micro"
        )
    return leitura.valores_por_geografia(nav.escopo, metrica)


# ---------------------------------------------------------------------------
# Todas as combinações de nível e recorte
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("recorte", RECORTES)
@pytest.mark.parametrize("metrica", PINTAVEIS)
def test_pe_pinta_em_todo_recorte(recorte: str, metrica: str) -> None:
    """Em PE, os três recortes têm de produzir mapa com dado."""
    nav = Navegacao(ano=ANO)
    nav.entrar_uf("PE")
    nav.definir_recorte(recorte)

    camada, chave = _camada_e_chave(nav)
    valores = _valores(nav, metrica)
    assert not valores.empty, f"{recorte}/{metrica} sem valores"

    # Toda geografia desenhada precisa achar valor, senão o mapa fica cinza
    # sem motivo.
    sem_valor = set(camada[chave]) - set(valores.index)
    assert not sem_valor, f"{recorte}/{metrica}: sem valor para {sorted(sem_valor)[:5]}"


@pytest.mark.parametrize("recorte", RECORTES)
def test_escala_e_classificacao_funcionam_em_todo_recorte(recorte: str) -> None:
    nav = Navegacao(ano=ANO)
    nav.entrar_uf("PE")
    nav.definir_recorte(recorte)

    camada, chave = _camada_e_chave(nav)
    valores = _valores(nav, "incid")
    escala = mapa.escala_natural(camada[chave].map(valores), tb.rampa_mapa("incid"))

    assert escala.classes >= 1
    classes = mapa.classificar(camada[chave].map(valores), escala)
    assert (classes != mapa.ROTULO_SEM_DADO).all(), f"{recorte}: geografia sem classe"


@pytest.mark.parametrize("uf", ["PE", "SP", "AC", "DF"])
def test_uf_fora_de_pe_so_tem_o_recorte_de_municipio(uf: str) -> None:
    nav = Navegacao(ano=ANO)
    nav.entrar_uf(uf)
    if uf == "PE":
        assert nav.tem_recortes_de_saude
        return

    assert not nav.tem_recortes_de_saude
    camada, chave = _camada_e_chave(nav)
    valores = _valores(nav, "incid")
    assert not set(camada[chave]) - set(valores.index)


# ---------------------------------------------------------------------------
# Percursos completos, incluindo o detalhe
# ---------------------------------------------------------------------------


def _percursos():
    """Caminhos de ida que a aplicação permite, do Brasil ao detalhe."""
    macro = recortes.macros()[0]
    micro = recortes.micros(macro)[0]
    municipio = recortes.municipios_de(micro=micro)[0]

    yield "direto", [
        lambda n: n.entrar_uf("PE"),
        lambda n: n.entrar_municipio(municipio),
        lambda n: n.abrir_detalhe(),
    ]
    yield "por macro", [
        lambda n: n.entrar_uf("PE"),
        lambda n: n.definir_recorte("MACRO"),
        lambda n: n.entrar_macro(macro),
        lambda n: n.entrar_micro(micro),
        lambda n: n.entrar_municipio(municipio),
        lambda n: n.abrir_detalhe(),
    ]
    yield "fora de PE", [
        lambda n: n.entrar_uf("SP"),
        lambda n: n.entrar_municipio("355030"),
        lambda n: n.abrir_detalhe(),
    ]


@pytest.mark.parametrize("nome,passos", list(_percursos()), ids=lambda v: v if isinstance(v, str) else "")
def test_percurso_desenha_em_cada_passo(nome: str, passos: list) -> None:
    """Nenhum passo pode deixar o mapa sem o que desenhar."""
    nav = Navegacao(ano=ANO)
    for indice, passo in enumerate(passos):
        passo(nav)
        camada, chave = _camada_e_chave(nav)
        assert not camada.empty, f"{nome}: passo {indice} sem geometria"
        valores = _valores(nav, "incid")
        assert not valores.empty, f"{nome}: passo {indice} sem valores"


@pytest.mark.parametrize("nome,passos", list(_percursos()), ids=lambda v: v if isinstance(v, str) else "")
def test_percurso_volta_ao_inicio(nome: str, passos: list) -> None:
    nav = Navegacao(ano=ANO)
    inicio = (nav.nivel, nav.uf, nav.mun, nav.detalhe, nav.recorte, nav.macro, nav.micro)
    for passo in passos:
        passo(nav)
    for _ in range(len(passos) + 3):
        nav.voltar()
    agora = (nav.nivel, nav.uf, nav.mun, nav.detalhe, nav.recorte, nav.macro, nav.micro)
    assert agora == inicio, f"{nome}: sobrou estado preso"


def test_detalhe_isola_um_municipio() -> None:
    nav = Navegacao(ano=ANO)
    nav.entrar_uf("PE")
    nav.entrar_municipio("261160", nome="Recife")

    estado = geo.municipios("PE")
    so_ele = estado[estado["cod_mun6"] == nav.mun]
    assert len(so_ele) == 1

    largura = lambda c: c.total_bounds[2] - c.total_bounds[0]
    assert largura(so_ele) < largura(estado) / 10
    assert mapa.enquadrar(tuple(so_ele.total_bounds))["zoom"] > mapa.enquadrar(
        tuple(estado.total_bounds)
    )["zoom"]


@pytest.mark.parametrize("metrica", ["cura_pct", "contatos_pct"])
def test_metrica_nao_pintavel_devolve_vazio_em_todo_recorte(metrica: str) -> None:
    """Melhor mapa vazio e honesto que colorido com a métrica errada.

    Cura e contatos saem de `TPALTA_N` e `CONTEXAM`, que o leitor consulta uma
    geografia por vez: não há como pintar 185 municípios de uma vez. Por isso
    eles são card e gráfico, nunca opção do mapa."""
    for recorte in RECORTES:
        nav = Navegacao(ano=ANO)
        nav.entrar_uf("PE")
        nav.definir_recorte(recorte)
        assert _valores(nav, metrica).empty, f"{recorte}/{metrica} deveria vir vazio"


@pytest.mark.parametrize("metrica", ["casos_0_14", "taxa_det_0_14"])
@pytest.mark.parametrize("recorte", ["MUN", "MACRO", "MICRO"])
def test_metricas_0_14_pintam_em_todo_recorte(metrica: str, recorte: str) -> None:
    """Os cards de 0–14 são clicáveis no painel de origem e colorem o mapa.

    Saem de `incidence_0_14`, outro dataset com o mesmo layout — e por macro e
    região de saúde a taxa é recalculada da soma, não média das municipais.
    """
    esc = Escopo("HANSENIASE", 2024, "UF", uf="PE")
    if recorte == "MUN":
        valores = leitura.valores_por_geografia(esc, metrica)
        assert len(valores) == 185
    else:
        valores = leitura.valores_por_regiao(
            esc, metrica, "macro" if recorte == "MACRO" else "micro"
        )
        assert len(valores) == (4 if recorte == "MACRO" else 12)
    assert valores.notna().any()
