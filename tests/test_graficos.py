"""Gráficos do painel direito.

Altair e não ECharts: `st.altair_chart` tem evento de clique nativo, o que o
ranking precisa para navegar o mapa. Verificado com clique real antes da
escolha — ter na assinatura e disparar são coisas diferentes, lição da
semana 3.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import graficos
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import hanseniase as tb

ESCOPO = Escopo("HANSENIASE", 2024, "UF", uf="PE")
COR = tb.cor("casos")


def _mensal():
    return leitura.serie_mensal(ESCOPO).rename(columns={"casos": "valor"})


def test_serie_mensal_cobre_o_ano() -> None:
    assert len(_mensal()) == 12


def test_serie_anual_cobre_a_historia() -> None:
    serie = leitura.serie_anual(ESCOPO, "casos")
    assert len(serie) >= 15
    assert serie["ano"].is_monotonic_increasing


def test_mensal_e_anual_divergem_por_criterio_geografico() -> None:
    """`_cache_ts` é por notificação e `incidence` por residência.

    Medido no SINAN bruto — ver contrato-dados, armadilha 7. O teste fixa a
    divergência: se um dia os dois passarem a bater, é porque a fonte mudou e
    o aviso na tela deixou de ser necessário.
    """
    mensal = _mensal()["valor"].sum()
    anual = leitura.serie_anual(ESCOPO, "casos").query("ano == 2024")["valor"].iloc[0]
    assert mensal != anual, "se convergiram, revisar o aviso na interface"
    # Na hanseníase a série anual é de casos novos do MS (1.761 em 2024) e a
    # mensal do `_cache_ts` é toda entrada no registro (2.475): a distância é
    # a da paridade §1, ~40%, e não o 1% de residência × notificação.
    assert 0.3 < (mensal - anual) / anual < 0.5, "distância fora do esperado (MS × todas as entradas)"


def test_grafico_mensal_usa_a_cor_da_metrica() -> None:
    g = graficos.evolucao_mensal(_mensal(), rotulo="Casos", cor=COR)
    assert g.mark["type"] == "bar"
    assert g.mark["color"] == COR


def test_grafico_anual_destaca_o_ano_selecionado() -> None:
    serie = leitura.serie_anual(ESCOPO, "casos")
    g = graficos.evolucao_anual(serie, rotulo="Casos", cor=COR, ano=2024)
    # O destaque é por opacidade: o ano ativo opaco, o histórico recuado.
    assert "opacity" in g.encoding.to_dict()


@pytest.mark.parametrize("construtor", ["mensal", "anual"])
def test_serie_vazia_mostra_recado_em_vez_de_painel_branco(construtor: str) -> None:
    vazio = pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"])
    g = (
        graficos.evolucao_mensal(vazio, rotulo="Casos", cor=COR)
        if construtor == "mensal"
        else graficos.evolucao_anual(vazio, rotulo="Casos", cor=COR, ano=2024)
    )
    assert g.mark["type"] == "text"


def test_tema_nao_pinta_fundo() -> None:
    """O painel já tem superfície própria; fundo opaco brigaria com o tema."""
    import altair as alt

    g = graficos.tema(
        alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    )
    assert g.config.view.fill is None


def test_tema_herda_a_cor_do_texto() -> None:
    """Igual aos cards: `currentColor` acompanha o tema sem detectá-lo."""
    import altair as alt

    g = graficos.tema(
        alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    )
    assert g.config.axis.labelColor == "currentColor"



# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _ranking(nivel="BR", uf=None, metrica="incid", top_n=15):
    return leitura.ranking(Escopo("HANSENIASE", 2024, nivel, uf=uf), metrica, top_n)


def test_ranking_no_brasil_lista_ufs() -> None:
    r = _ranking()
    assert len(r) == 15
    assert r["chave"].str.len().eq(2).all(), "no Brasil a chave é a sigla da UF"


def test_ranking_numa_uf_lista_municipios_com_nome() -> None:
    r = _ranking("UF", "PE")
    assert r["chave"].str.len().eq(6).all()
    assert (r["nome"] != r["chave"]).all(), "o nome deve ser resolvido, não o código"


def test_ranking_vem_ordenado_do_maior() -> None:
    valores = _ranking("UF", "PE")["valor"]
    assert valores.is_monotonic_decreasing


def test_empate_e_desempatado_pelo_nome() -> None:
    """Sem critério estável, a ordem varia entre execuções e confunde."""
    r1 = _ranking("UF", "PE", "casos", 30)
    r2 = _ranking("UF", "PE", "casos", 30)
    assert r1["chave"].tolist() == r2["chave"].tolist()


@pytest.mark.parametrize("top_n", [5, 15, 30])
def test_top_n_e_respeitado(top_n: int) -> None:
    assert len(_ranking("UF", "PE", top_n=top_n)) == top_n


def test_ranking_usa_a_mesma_fonte_do_mapa() -> None:
    """Ler de lugares diferentes é como o card e a série, que divergem."""
    escopo = Escopo("HANSENIASE", 2024, "UF", uf="PE")
    do_mapa = leitura.valores_por_geografia(escopo, "incid")
    do_ranking = _ranking("UF", "PE", "incid", 5)
    for linha in do_ranking.itertuples():
        assert do_mapa[linha.chave] == pytest.approx(linha.valor)


def test_metrica_sem_suporte_devolve_ranking_vazio() -> None:
    r = _ranking("BR", metrica="hiv_pos_pct")
    assert r.empty
    assert list(r.columns) == ["chave", "nome", "valor"]


def test_grafico_de_ranking_vazio_mostra_recado() -> None:
    import altair as alt

    g = graficos.ranking(
        pd.DataFrame(columns=["chave", "nome", "valor"]),
        rotulo="Casos",
        cor=COR,
        selecao=alt.selection_point(name="barra"),
    )
    assert g.mark["type"] == "text"


def test_grafico_de_ranking_cresce_com_o_numero_de_barras() -> None:
    """Altura fixa espremeria 30 municípios num espaço de 5."""
    import altair as alt

    def altura(n):
        return graficos.ranking(
            _ranking("UF", "PE", top_n=n),
            rotulo="Casos",
            cor=COR,
            selecao=alt.selection_point(name="barra"),
        ).height

    assert altura(30) > altura(5)


# --- clique na barra --------------------------------------------------------


class _Evento:
    def __init__(self, selection):
        self.selection = selection


def test_extrai_a_chave_da_barra_clicada() -> None:
    ev = _Evento({"barra": [{"chave": "AM", "nome": "AM", "valor": 94.5}]})
    assert graficos.alvo_do_clique(ev, "barra") == "AM"


@pytest.mark.parametrize(
    "evento",
    [
        None,
        _Evento(None),
        _Evento({}),
        _Evento({"barra": []}),
        _Evento({"barra": [{}]}),
        _Evento({"barra": ["texto solto"]}),
        _Evento({"outra": [{"chave": "AM"}]}),
        {"selection": {"barra": [{"chave": "BA"}]}},
    ],
)
def test_evento_estranho_nao_derruba_a_pagina(evento) -> None:
    resultado = graficos.alvo_do_clique(evento, "barra")
    assert resultado is None or isinstance(resultado, str)


# ---------------------------------------------------------------------------
# Série seguindo a métrica ativa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metrica", ["casos", "cura", "obitos", "pop", "incid"])
def test_serie_mensal_cobre_as_metricas_diretas(metrica: str) -> None:
    serie = leitura.serie_mensal_metrica(ESCOPO, metrica)
    assert len(serie) == 12
    assert list(serie.columns) == ["mes", "mes_nome", "valor"]


@pytest.mark.parametrize("metrica", ["mortalidade", "letalidade"])
def test_taxas_sao_recalculadas_mes_a_mes(metrica: str) -> None:
    """Repetir a taxa anual nos meses esconderia a sazonalidade.

    Como o gráfico existe justamente para mostrar sazonalidade, a taxa precisa
    variar entre os meses — se todos os valores fossem iguais, seria sinal de
    que a taxa veio do total anual.
    """
    serie = leitura.serie_mensal_metrica(ESCOPO, metrica)
    assert len(serie) == 12
    assert serie["valor"].nunique() > 1, "a taxa não variou entre os meses"


@pytest.mark.parametrize("metrica", ["hiv_pos_pct", "interrupcao_trat_pct", "taxa_det_0_14"])
def test_metrica_sem_serie_devolve_vazio(metrica: str) -> None:
    """Melhor painel com recado que série da métrica errada."""
    assert leitura.serie_mensal_metrica(ESCOPO, metrica).empty
    assert leitura.serie_anual(ESCOPO, metrica).empty


# ---------------------------------------------------------------------------
# Série dupla: casos e incidência
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("horizonte", ["meses", "anos"])
def test_serie_dupla_traz_as_duas_grandezas(horizonte: str) -> None:
    d = leitura.serie_dupla(ESCOPO, horizonte)
    assert {"casos", "incid"} <= set(d.columns)
    assert len(d) == (12 if horizonte == "meses" else 16)


def test_serie_dupla_bate_com_as_series_isoladas() -> None:
    dupla = leitura.serie_dupla(ESCOPO, "meses")
    casos = leitura.serie_mensal_metrica(ESCOPO, "casos")
    assert dupla["casos"].to_numpy() == pytest.approx(casos["valor"].to_numpy())




#: Altura da caixa de um rótulo do eixo y, medida no navegador com a fonte de
#: 12px do tema. O Vega esconde um nome sim, outro não assim que o passo entre
#: rótulos fica abaixo disso.
CAIXA_ROTULO = 16


@pytest.mark.parametrize("top_n", [5, 15, 20, 25, 30])
def test_o_ranking_reserva_faixa_para_todo_rotulo(top_n: int) -> None:
    """Nome de município não pode sumir porque a lista cresceu.

    Com altura fixa em 484px e 25 municípios, cada faixa ficava com 15,3px
    contra uma caixa de rótulo de 16 — colidia por menos de um pixel e o Vega
    escondia metade dos nomes, sem aviso nenhum. O gráfico continuava bonito e
    respondia a perguntas erradas: a barra que se lê não era a que se pensava
    estar lendo.

    A primeira correção reservou 22px por barra sobre a altura **total** e não
    resolveu — o eixo x e o título comem 82px antes de sobrar espaço para as
    faixas. É por isso que a conta desconta `ALTURA_EIXO_RANKING`.
    """
    import altair as alt

    dados = _ranking("UF", "PE", top_n=top_n)
    figura = graficos.ranking(
        dados,
        rotulo="Incidência",
        cor="#C1440A",
        selecao=alt.selection_point(name="barra", fields=["chave"]),
        altura_minima=484,
    )
    util = figura.height - graficos.ALTURA_EIXO_RANKING
    por_faixa = util / len(dados)
    assert por_faixa >= CAIXA_ROTULO, (
        f"{top_n} barras: {por_faixa:.1f}px por faixa contra {CAIXA_ROTULO} "
        f"de rótulo — o Vega vai esconder um nome sim, outro não"
    )


def test_altura_do_ranking_e_piso_e_nao_teto() -> None:
    """Listas curtas fecham com o mapa; listas longas passam dele.

    O piso existe para o ranking não terminar antes do mapa e deixar um vão na
    linha. Virar teto foi o que escondeu os rótulos.
    """
    import altair as alt

    def altura(n: int) -> int:
        return graficos.ranking(
            _ranking("UF", "PE", top_n=n),
            rotulo="Incidência",
            cor="#C1440A",
            selecao=alt.selection_point(name="barra", fields=["chave"]),
            altura_minima=484,
        ).height

    assert altura(5) == 484, "lista curta tem de fechar com o mapa"
    assert altura(15) == 484, "o padrão tem de fechar com o mapa"
    assert altura(30) > 484, "lista longa tem de crescer além do piso"


def test_o_rotulo_do_ranking_nunca_deixa_dois_municipios_iguais() -> None:
    """Cortar o nome curto demais faz o ranking mentir sobre quem é a barra.

    Com os 98px que o Vega dava sozinho, 891 dos 5.571 municípios cortavam e
    **49 ficavam ambíguos** — "São Domingos do Maranhão" e "São Domingos do
    Azeitão" apareciam com o mesmo texto, na mesma UF, no mesmo gráfico.

    Este teste não confere largura: confere a propriedade que a largura existe
    para garantir. Baixar `LARGURA_ROTULO_RANKING` volta a colidir e ele
    acusa, dizendo quais nomes.
    """
    import collections

    from src.data import config, geo

    cabem = int(graficos.LARGURA_ROTULO_RANKING / graficos.PX_POR_CARACTERE)
    colisoes = []
    for uf in sorted(config.CODIGO_POR_UF):
        vistos = collections.defaultdict(list)
        for nome in geo.municipios(uf)["nome_mun"]:
            exibido = nome if len(nome) <= cabem else nome[: cabem - 1] + "…"
            vistos[exibido].append(nome)
        for exibido, originais in vistos.items():
            if len(originais) > 1 and exibido.endswith("…"):
                colisoes.append(f"{uf}: {originais}")

    assert not colisoes, (
        f"nomes que viram o mesmo texto no eixo, com {cabem} caracteres: "
        + "; ".join(colisoes[:3])
    )


@pytest.mark.parametrize(
    "nivel,uf", [("BR", None), ("UF", "PE"), ("UF", "MG")], ids=["BR", "PE", "MG"]
)
def test_ranking_e_mapa_classificam_pelos_mesmos_cortes(nivel: str, uf: str | None) -> None:
    """A barra de um estado tem de sair na cor do polígono dele.

    O mapa calcula a escala depois de juntar os valores à geometria; o ranking
    a calcula da série crua, porque é outro fragmento e recarrega sozinho
    quando o slider mexe. Se as duas contas divergirem, um estado aparece num
    tom no mapa e noutro na barra — pior que a cor única de antes, porque
    parece informação.
    """
    from src import mapa
    from src.data import geo

    esc = Escopo("HANSENIASE", 2024, nivel, uf=uf)
    valores = leitura.valores_por_geografia(esc, "incid")
    rampa = tb.rampa_mapa("incid")

    camada = geo.ufs() if nivel == "BR" else geo.municipios(uf)
    chave = "uf" if nivel == "BR" else "cod_mun6"
    do_mapa = mapa.escala_natural(camada[chave].map(valores), rampa, decimais=1)
    do_ranking = mapa.escala_natural(valores, rampa, decimais=1)

    assert do_mapa.cortes == pytest.approx(do_ranking.cortes)
    assert do_mapa.cores == do_ranking.cores


def test_o_ranking_sem_escala_volta_a_cor_unica() -> None:
    """O parâmetro é opcional, e a ausência dele não pode quebrar nada.

    Serve a quem chamar o gráfico fora do painel — testes e o script de
    medição — sem ter uma escala à mão.
    """
    import altair as alt

    figura = graficos.ranking(
        _ranking("UF", "PE", top_n=5),
        rotulo="Incidência",
        cor="#C1440A",
        selecao=alt.selection_point(name="barra", fields=["chave"]),
    )
    assert figura.encoding.color.to_dict() == {"value": "#C1440A"}, (
        "sem escala, todas as barras saem na cor da métrica"
    )


# ---------------------------------------------------------------------------
# Ranking e recorte
# ---------------------------------------------------------------------------

PE = Escopo("HANSENIASE", 2024, "UF", uf="PE")


@pytest.mark.parametrize(
    "recorte,esperado",
    [("MACRO", {"Metropolitana", "Agreste"}), ("MICRO", {"Recife", "Caruaru"})],
)
def test_ranking_segue_o_recorte_do_mapa(recorte: str, esperado: set) -> None:
    """Mapa e ranking têm de mostrar o mesmo recorte.

    Enquanto não seguia, o mapa desenhava macrorregiões e o ranking listava
    municípios ao lado, com o título dizendo "municípios" — dois recortes na
    mesma linha. E as cores, que saem da escala do mapa, deixavam de casar:
    valor de município classificado contra faixas de macrorregião.
    """
    tabela = leitura.ranking(PE, "casos", 15, recorte)
    assert not tabela.empty
    assert esperado <= set(tabela["nome"]), (
        f"recorte {recorte} devia listar regiões, veio {list(tabela['nome'])[:4]}"
    )


def test_ranking_so_lista_quem_tem_poligono_no_mapa() -> None:
    """O `sinan_landing` traz municípios de outros estados sob `uf='PE'`.

    São dez, com 13 registros de 4.350, e sem nome resolvido na origem. O mapa
    nunca os mostrou — não há geometria para pintar. O ranking mostrava, com o
    código cru no lugar do nome, e como bastava um caso curado para dar 100%,
    eles ocupavam o topo do ranking de cura.
    """
    from src.data import geo

    de_pe = set(geo.municipios("PE")["cod_mun6"])
    for metrica in ("incid", "casos", "cura_pct"):
        tabela = leitura.ranking(PE, metrica, 30)
        intrusos = set(tabela["chave"]) - de_pe
        assert not intrusos, f"{metrica}: fora de PE no ranking — {intrusos}"


def test_proporcao_com_base_pequena_nao_entra_no_ranking() -> None:
    """Cura de 100% sobre três encerramentos não é o melhor município do estado.

    A regra já existia para o painel de composição e não alcançava o mapa nem
    o ranking. Em PE, 84 dos 178 municípios com encerramento têm menos de
    cinco, e 29 deles apareciam com 100% — o topo inteiro era base pequena.
    """
    desfechos = leitura.desfechos_por_geografia(PE)
    tabela = leitura.ranking(PE, "cura_pct", 15)

    for chave in tabela["chave"]:
        base = float(desfechos.loc[chave, "total"])
        assert base >= leitura.MINIMO_PARA_PERCENTUAL, (
            f"{chave} entrou no ranking de cura com {base:.0f} encerramentos"
        )


@pytest.mark.skip(reason="cura_pct sai de SITUA_ENCE (TB); a hanseníase não a pinta no mapa")
def test_a_supressao_de_base_pequena_vale_tambem_no_mapa() -> None:
    """Mapa e ranking têm de suprimir o mesmo — ou um pinta o que o outro nega."""
    desfechos = leitura.desfechos_por_geografia(PE)
    valores = leitura.valores_por_geografia(PE, "cura_pct")

    pequenos = desfechos.index[desfechos["total"] < leitura.MINIMO_PARA_PERCENTUAL]
    assert len(pequenos) > 0, "amostra sem base pequena — o teste perdeu o alvo"
    assert valores.reindex(pequenos).isna().all(), (
        "município com base pequena continua pintado no mapa"
    )
