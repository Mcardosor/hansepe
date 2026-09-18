"""Testes do canal endêmico.

A regra foi **reconstruída** do painel de origem, não documentada por eles:
quartis dos três anos anteriores, interpolação linear. O teste mais valioso
aqui é o que prende essa reconstrução contra os valores que eles publicam —
se a nossa faixa deixar de bater com a deles, ou nós mudamos a regra, ou eles
mudaram, e as duas exigem parar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import canal
from src.data.escopo import Escopo

ANO = 2025

#: Q1 e Q3 de cada mês de 2023, lidos da especificação ECharts do painel no ar
#: em 28/ago/2026. Ver `tests/paridade/referencia_r.json`.
Q1_DELES = [
    10.016567, 9.451368, 10.738764, 9.262969, 7.096376, 8.132573,
    9.859567, 10.204966, 10.675964, 10.204966, 9.985167, 10.173566,
]
Q3_DELES = [
    11.272562, 11.209763, 13.690354, 10.958563, 11.146963, 9.828167,
    11.743561, 12.026160, 11.335362, 12.465758, 11.492362, 13.187956,
]


@pytest.fixture(scope="module")
def esc() -> Escopo:
    return Escopo("HANSENIASE", ANO, "UF", uf="PE")


@pytest.fixture(scope="module")
def canal_2023(esc: Escopo):
    """O canal como o painel desenha: cinco anos, o padrão decidido."""
    return canal.montar(esc)


@pytest.fixture(scope="module")
def canal_como_deles(esc: Escopo):
    """Três anos, que é o que o painel de origem usa.

    Existe só para a conferência da regra: é a prova de que entendemos o
    método deles, e ela não pode depender da nossa escolha de quantos anos
    usar. Ver `docs/paridade-com-o-painel-r.md` §6.
    """
    return canal.montar(esc, anos_referencia=3)


# ---------------------------------------------------------------------------
# Forma
# ---------------------------------------------------------------------------


def test_o_padrao_e_cinco_anos(canal_2023) -> None:
    """Cinco por decisão nossa; o painel de origem usa três — `docs/paridade-com-o-painel-r.md` §6."""
    assert canal.ANOS_REFERENCIA == 5
    assert canal_2023.anos == tuple(range(ANO - 5, ANO))


def test_as_tres_camadas_vem_preenchidas(canal_2023) -> None:
    assert len(canal_2023.faixa) == 12
    assert len(canal_2023.atual) == 12
    assert len(canal_2023.referencia) == 60  # 5 anos × 12 meses
    assert not canal_2023.vazio


def test_faixa_nunca_invertida(canal_2023) -> None:
    """Q1 acima de Q3 desenha uma área de altura negativa, que o Altair
    representa sem reclamar — e o gráfico fica sutilmente errado."""
    assert (canal_2023.faixa["q3"] >= canal_2023.faixa["q1"]).all()


def test_ano_corrente_fora_da_referencia(canal_2023) -> None:
    """O ano selecionado não pode entrar no próprio histórico, ou a faixa se
    ajusta para conter a linha e o canal perde a função."""
    assert ANO not in set(canal_2023.referencia["ano"])


# ---------------------------------------------------------------------------
# A regra reconstruída — o teste central
# ---------------------------------------------------------------------------



def test_quartil_sai_de_interpolacao_linear(canal_2023) -> None:
    """Com três pontos, o quartil cai entre dois deles. A escolha da
    interpolação muda o número, e é ela que reproduz o painel deles."""
    janeiro = canal_2023.referencia.query("mes == 1")["valor"].to_numpy()
    faixa = canal_2023.faixa.query("mes == 1").iloc[0]
    assert faixa["q1"] == pytest.approx(np.quantile(janeiro, 0.25))
    assert faixa["q3"] == pytest.approx(np.quantile(janeiro, 0.75))


def test_denominador_e_o_de_cada_ano(canal_2023) -> None:
    """Registro executável da §5.

    Se um dia passarmos a usar população fixa como eles, este teste falha e
    manda revisitar a decisão em vez de deixá-la mudar em silêncio.
    """
    populacoes = {
        ano: grupo["valor"].iloc[0]
        for ano, grupo in canal_2023.referencia.query("mes == 1").groupby("ano")
    }
    assert len(set(populacoes.values())) == len(populacoes), (
        "as três taxas de janeiro ficaram iguais — sinal de denominador fixo"
    )


# ---------------------------------------------------------------------------
# A leitura que o canal entrega
# ---------------------------------------------------------------------------



def test_meses_fora_traz_os_dois_lados(canal_2023) -> None:
    fora = canal.meses_fora_da_faixa(canal_2023)
    assert set(fora.columns) >= {"mes", "mes_nome", "valor", "q1", "q3", "posicao"}
    assert set(fora["posicao"]) <= {"acima", "abaixo"}
    # Coerência: o que está marcado como acima está mesmo acima do Q3.
    assert (fora.query("posicao == 'acima'")["valor"]
            > fora.query("posicao == 'acima'")["q3"]).all()


# ---------------------------------------------------------------------------
# Bordas
# ---------------------------------------------------------------------------


def test_primeiro_ano_do_dado_nao_estoura() -> None:
    """Em 2010 não há três anos anteriores. O gráfico ainda tem o que mostrar —
    a linha do ano —, e a faixa simplesmente não existe."""
    esc = Escopo("HANSENIASE", 2010, "UF", uf="PE")
    c = canal.montar(esc)
    assert len(c.atual) == 12
    assert c.anos == ()
    assert canal.meses_fora_da_faixa(c).empty



@pytest.mark.parametrize("n", [3, 5, 8])
def test_numero_de_anos_e_configuravel(esc: Escopo, n: int) -> None:
    c = canal.montar(esc, anos_referencia=n)
    assert len(c.anos) == n
    assert len(c.referencia) == 12 * n



# ---------------------------------------------------------------------------
# Gráfico
# ---------------------------------------------------------------------------


def _spec(canal_obj) -> dict:
    from src import graficos
    from src.doencas import hanseniase as pack

    return graficos.canal_endemico(
        canal_obj, rotulo=pack.rotulo("incid"), cor=pack.cor("incid")
    ).to_dict()


def test_faixa_e_area_entre_duas_linhas(canal_2023) -> None:
    """Área com `y`/`y2`, e não duas áreas empilhadas como o ECharts obriga.

    A primeira camada é a faixa; se ela perder o `y2`, virou empilhamento e o
    desenho passa a depender da ordem das séries.
    """
    area = _spec(canal_2023)["layer"][0]
    assert area["mark"]["type"] == "area"
    assert "y2" in area["encoding"]


def test_camadas_na_ordem_de_leitura(canal_2023) -> None:
    """Faixa, bordas Q1 e Q3, anos anteriores, ano corrente, régua do tooltip.

    Ordem é z-order no Altair: a linha do ano corrente tem de vir depois das
    tracejadas de referência, ou elas passam por cima dela. A régua fica por
    último para capturar o ponteiro sem que uma linha a intercepte.
    """
    camadas = _spec(canal_2023)["layer"]
    marcas = [
        c["mark"]["type"] if isinstance(c["mark"], dict) else c["mark"]
        for c in camadas
    ]
    assert marcas == ["area", "line", "line", "line", "line", "rule"]

    espessuras = [
        c["mark"].get("strokeWidth", 0)
        for c in camadas
        if isinstance(c["mark"], dict) and c["mark"]["type"] == "line"
    ]
    assert espessuras[-1] == max(espessuras), "o ano corrente não é a linha mais grossa"


def test_legenda_nomeia_todas_as_series(canal_2023) -> None:
    """"Ano selecionado", cada ano de referência, Q1 e Q3 — os mesmos nomes do
    painel de origem, para quem usa os dois não reaprender o vocabulário.

    Uma escala de cor só é o que junta a legenda: com escalas independentes por
    camada o Altair desenha as linhas certas e não monta legenda nenhuma.
    """
    from src import graficos

    camadas = _spec(canal_2023)["layer"]
    coloridas = [c for c in camadas if "color" in c.get("encoding", {})]
    assert coloridas, "nenhuma camada encodifica cor — a legenda sumiu"

    dominios = {tuple(c["encoding"]["color"]["scale"]["domain"]) for c in coloridas}
    assert len(dominios) == 1, "camadas com domínios diferentes quebram a legenda"

    esperado = (
        graficos.SERIE_ATUAL,
        *[str(a) for a in canal_2023.anos],
        graficos.SERIE_Q1,
        graficos.SERIE_Q3,
    )
    assert dominios.pop() == esperado


def test_tooltip_e_unificado(canal_2023) -> None:
    """Uma régua mostra todas as séries do mês de uma vez.

    Tooltip por linha obrigaria a acertar o cursor em cada uma para comparar
    março de 2023 com março de 2021 — que é a leitura que o gráfico existe
    para dar.
    """
    from src import graficos

    regua = _spec(canal_2023)["layer"][-1]
    assert regua["mark"]["type"] == "rule"
    titulos = [t["title"] for t in regua["encoding"]["tooltip"]]
    assert titulos[0] == "Mês"
    for serie in (graficos.SERIE_ATUAL, graficos.SERIE_Q1, graficos.SERIE_Q3):
        assert serie in titulos
    for ano in canal_2023.anos:
        assert str(ano) in titulos
    # Do mais recente ao mais antigo, a ordem de leitura do gráfico.
    anos_no_tooltip = [t for t in titulos if t.isdigit()]
    assert anos_no_tooltip == sorted(anos_no_tooltip, reverse=True)


def test_grafico_vazio_nao_estoura() -> None:
    from src import graficos

    vazio = canal.Canal(
        faixa=pd.DataFrame(columns=["mes", "mes_nome", "q1", "q3"]),
        referencia=pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"]),
        atual=pd.DataFrame(columns=["mes", "mes_nome", "valor"]),
        anos=(),
    )
    assert graficos.canal_endemico(vazio, rotulo="x", cor="#000") is not None


# ---------------------------------------------------------------------------
# Epicurva
# ---------------------------------------------------------------------------


def test_epicurva_cobre_a_serie_inteira(esc: Escopo) -> None:
    """Catorze anos × doze meses. O painel de origem para em 2019-12 com dado
    até 2023 — a pergunta §4 do `docs/paridade-com-o-painel-r.md`, sem resposta —, e não copiamos
    o corte: num painel cuja leitura principal é "a incidência subiu desde
    2020", esconder 2020 a 2023 apagaria o que ele tem a dizer."""
    e = canal.epicurva(esc)
    assert len(e) == 12 * (ANO - 2010 + 1)
    assert e["ano_mes"].iloc[0] == "2010-01"
    assert e["ano_mes"].iloc[-1] == f"{ANO}-12"


def test_epicurva_vem_em_ordem_cronologica(esc: Escopo) -> None:
    """Fora de ordem, a linha do gráfico vira um novelo — e o Altair desenha
    sem reclamar."""
    e = canal.epicurva(esc)
    assert list(e["ano_mes"]) == sorted(e["ano_mes"])


def test_epicurva_fecha_com_o_canal_no_ano_corrente(esc: Escopo, canal_2023) -> None:
    """As duas saem da mesma fonte; se divergirem, os dois gráficos da mesma
    aba passam a contar histórias diferentes do mesmo mês."""
    do_ano = canal.epicurva(esc).query(f"ano == {ANO}")
    assert len(do_ano) == 12
    assert list(do_ano["mes"]) == list(canal_2023.atual.sort_values("mes")["mes"])



def test_grafico_da_epicurva_usa_eixo_temporal(esc: Escopo) -> None:
    """São 168 pontos: num eixo de categoria o Altair escreveria os 168
    rótulos e o eixo viraria uma tarja."""
    from src import graficos
    from src.doencas import hanseniase as pack

    spec = graficos.epicurva(
        canal.epicurva(esc), rotulo="Casos", cor=pack.cor("casos"), ano_em_foco=ANO
    ).to_dict()
    camadas = spec.get("layer", [spec])
    assert camadas[0]["encoding"]["x"]["type"] == "temporal"
    # Série inteira, trecho do ano em foco (mais grosso), régua do tooltip e o
    # ponto que acende sob o cursor.
    assert len(camadas) == 4
    grossuras = [
        c["mark"].get("strokeWidth")
        for c in camadas
        if isinstance(c["mark"], dict) and c["mark"]["type"] == "line"
    ]
    assert grossuras[1] > grossuras[0], "o ano em foco não é a linha mais grossa"


def test_epicurva_pega_a_coluna_do_mes_e_nao_o_ponto(esc: Escopo) -> None:
    """Com 168 pontos em poucos pixels, exigir que o cursor acerte o vértice
    torna o dado inalcançável — era preciso caçar as pontinhas da linha.

    A régua com `nearest` sobre a data resolve, pelo mesmo mecanismo do canal.
    """
    from src import graficos
    from src.doencas import hanseniase as pack

    spec = graficos.epicurva(
        canal.epicurva(esc), rotulo="Casos", cor=pack.cor("casos"), ano_em_foco=ANO
    ).to_dict()
    marcas = [
        c["mark"]["type"] if isinstance(c["mark"], dict) else c["mark"]
        for c in spec["layer"]
    ]
    assert "rule" in marcas, "a régua do tooltip sumiu"

    regua = spec["layer"][marcas.index("rule")]
    assert [t["title"] for t in regua["encoding"]["tooltip"]] == ["Mês", "Casos"]

    # A seleção precisa ser `nearest`, ou a régua volta a exigir pontaria.
    selecao = next(iter(spec["params"] if "params" in spec else regua["params"]))
    assert selecao["select"]["nearest"] is True
    assert selecao["select"]["fields"] == ["data"]



def test_canal_com_filtro_de_grau_e_subconjunto_do_total() -> None:
    """O filtro por grau de incapacidade do painel de origem: a taxa de um
    estrato nunca passa a de todos os graus somados, mês a mês."""
    esc = Escopo("HANSENIASE", 2025, "UF", uf="PE")
    todos = canal.montar(esc).atual.set_index("mes")["valor"]
    grau2 = canal.montar(esc, grau="Grau II").atual.set_index("mes")["valor"]
    assert (grau2 <= todos + 1e-9).all()
    assert grau2.sum() > 0
