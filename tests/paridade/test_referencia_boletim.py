"""Comparação com o Boletim Epidemiológico de Hanseníase (SES-PE).

Este harness é o irmão externo do `test_referencia_origem.py`, e existe
porque aquele não basta. Comparar com o painel da equipe parceira mede
**concordância**: os dois leem a mesma extração, e concordar não prova que o
número está certo — foi assim que a §1 (casos novos × todas as entradas)
passou meses invisível. Fonte oficial e independente pega essa classe de
erro; paridade entre painéis não pega.

Duas coisas são conferidas aqui:

1. **Os parâmetros das legendas** — o pedido da reunião de 22/set/2026. Os
   cortes e os nomes do pack têm de ser exatamente os dos quadros do
   boletim. Aqui não há tolerância: ou é a régua deles, ou não é.
2. **Os números de PE**, com tolerância assimétrica. O boletim foi tabulado
   em 16/04/2025 e nossa extração é posterior; o SINAN é atualizado
   retroativamente, então ficar **acima** é o comportamento correto — medido,
   de +0,4% a +4,4% na detecção geral. Ficar **abaixo** não tem explicação
   benigna.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.data import kpis as calc
from src.data.escopo import Escopo
from src.doencas import hanseniase as pack

REFERENCIA = json.loads(
    (Path(__file__).parent / "referencia_boletim.json").read_text(encoding="utf-8")
)

#: Quanto podemos ficar **acima** do boletim por defasagem de extração.
#: O pior ano medido em 25/set/2026 é 2021, com +4,4%.
MARGEM_ACIMA = 0.08

#: Quanto podemos ficar **abaixo**. Só arredondamento do coeficiente, que o
#: boletim publica com uma casa decimal.
MARGEM_ABAIXO = 0.01

#: Por região de saúde a folga é maior que a do estado, e não por descuido:
#: além das notificações retroativas, a correção do município de residência
#: entre extrações **move** casos de uma região para outra, o que no estado
#: se cancela e na região não. Medido em 2024, II GERES cresceu 14% e IX,
#: 11%. O que este teste precisa pegar é município no recorte errado, que
#: desloca dezenas de casos de uma vez.
MARGEM_REGIAO = 0.20


def _pe(ano: int):
    return calc.calcular(Escopo("HANSENIASE", ano, "UF", uf="PE"))


# --- 1. os parâmetros das legendas -----------------------------------------


@pytest.mark.parametrize("metrica", sorted(REFERENCIA["parametros"]))
def test_cortes_sao_os_do_boletim(metrica: str):
    esperado = REFERENCIA["parametros"][metrica]
    assert list(pack.cortes_fixos(metrica)) == esperado["cortes"], esperado["quadro"]


@pytest.mark.parametrize("metrica", sorted(REFERENCIA["parametros"]))
def test_nomes_das_classes_sao_os_do_boletim(metrica: str):
    esperado = REFERENCIA["parametros"][metrica]
    assert list(pack.nomes_fixos(metrica)) == esperado["nomes"], esperado["quadro"]


@pytest.mark.parametrize("metrica", sorted(REFERENCIA["parametros"]))
def test_quadro_repete_o_texto_do_boletim(metrica: str):
    """O quadro que vai ao lado do gráfico é **citação** do documento.

    Pedido da reunião de 22/set/2026: a régua ao lado do gráfico, como no
    boletim. Gerar o texto a partir dos cortes pareceria mais limpo e
    perderia o ponto — "Regular =10-25%" está assim lá, com o sinal de igual
    e sem espaço. Este teste prende a transcrição.
    """
    titulo, linhas = pack.texto_parametros(metrica)
    assert [titulo, *linhas] == REFERENCIA["parametros"][metrica]["quadro"]


def test_todo_indicador_de_qualidade_tem_quadro():
    for metrica in pack.INDICADORES_QUALIDADE:
        assert pack.texto_parametros(metrica) is not None, metrica


@pytest.mark.parametrize(
    "metrica, valor, classe",
    [
        ("incid", 1.99, "Baixo"),
        ("incid", 2.0, "Médio"),
        ("incid", 9.99, "Médio"),
        ("incid", 10.0, "Alto"),
        ("incid", 19.99, "Alto"),
        ("incid", 20.0, "Muito alto"),
        ("incid", 39.99, "Muito alto"),
        ("incid", 40.0, "Hiperendêmico"),
        ("taxa_det_0_14", 0.49, "Baixo"),
        ("taxa_det_0_14", 0.5, "Médio"),
        ("taxa_det_0_14", 2.49, "Médio"),
        ("taxa_det_0_14", 2.5, "Alto"),
        ("taxa_det_0_14", 9.99, "Muito alto"),
        ("taxa_det_0_14", 10.0, "Hiperendêmico"),
        ("prop_grau2_pct", 4.99, "Baixo"),
        ("prop_grau2_pct", 5.0, "Médio"),
        ("prop_grau2_pct", 10.0, "Alto"),
        ("cura_pct", 74.9, "Precário"),
        ("cura_pct", 75.0, "Regular"),
        ("cura_pct", 89.9, "Regular"),
        ("cura_pct", 90.0, "Bom"),
        ("abandono_pct", 9.9, "Bom"),
        ("abandono_pct", 10.0, "Regular"),
        ("abandono_pct", 25.0, "Precário"),
    ],
)
def test_classificacao_nas_bordas(metrica: str, valor: float, classe: str):
    """As bordas são onde a régua erra em silêncio: 10,00 é 'Alto', não
    'Médio'; 90,0% é 'Bom', não 'Regular'."""
    assert pack.classe_de(metrica, valor) == classe


def test_pe_2024_cai_nas_classes_que_o_boletim_publica():
    k = _pe(2024)
    assert pack.classe_de("incid", k.incid) == "Alto"
    assert pack.classe_de("taxa_det_0_14", k.taxa_det_0_14) == "Muito alto"
    assert pack.classe_de("prop_grau2_pct", k.prop_grau2_pct) == "Alto"
    assert pack.classe_de("cura_pct", k.cura_pct) == "Precário"
    assert pack.classe_de("contatos_pct", k.contatos_pct) == "Regular"
    assert pack.classe_de("gif_avaliado_pct", k.gif_avaliado_pct) == "Regular"
    assert pack.classe_de("abandono_pct", k.abandono_pct) == "Regular"


# --- 2. os números ----------------------------------------------------------


def _anos_da_serie():
    return sorted(int(a) for a in REFERENCIA["serie_pe"] if a.isdigit())


@pytest.mark.parametrize("ano", _anos_da_serie())
def test_casos_novos_acompanham_o_boletim(ano: int):
    """Casos novos do MS, 2015–2024. Acima por defasagem, nunca abaixo."""
    esperado = REFERENCIA["serie_pe"][str(ano)]["casos"]
    nosso = _pe(ano).casos
    assert nosso >= esperado * (1 - MARGEM_ABAIXO), (
        f"{ano}: {nosso} abaixo do boletim ({esperado}) — extração não encolhe"
    )
    assert nosso <= esperado * (1 + MARGEM_ACIMA), (
        f"{ano}: {nosso} muito acima do boletim ({esperado}) — conferir a "
        f"definição de caso novo"
    )


@pytest.mark.parametrize("ano", _anos_da_serie())
def test_taxa_de_deteccao_acompanha_o_boletim(ano: int):
    esperado = REFERENCIA["serie_pe"][str(ano)]["incid"]
    nosso = _pe(ano).incid
    assert esperado * (1 - MARGEM_ABAIXO) <= nosso <= esperado * (1 + MARGEM_ACIMA)


@pytest.mark.parametrize("ano", [2023, 2024])
def test_qualidade_do_programa_acompanha_o_boletim(ano: int):
    """Cura, abandono, contatos e GIF avaliado nos anos de coorte fechada.

    A tolerância é maior porque a nossa é aproximação de coorte — por ano de
    diagnóstico, não PB do ano anterior e MB de dois antes. Medido em 2024:
    cura 67,1 contra 65,0; abandono 12,2 contra 13,5; contatos 81,6 contra
    77,3; GIF avaliado 82,7 contra 83,6.
    """
    esperado = REFERENCIA["qualidade_pe"][str(ano)]
    k = _pe(ano)
    for campo in ("cura_pct", "abandono_pct", "contatos_pct", "gif_avaliado_pct"):
        nosso = getattr(k, campo)
        assert nosso is not None, f"{ano}: {campo} suprimido — coorte deveria estar fechada"
        assert abs(nosso - esperado[campo]) <= 6, (
            f"{ano}: {campo} = {nosso:.1f} contra {esperado[campo]} do boletim"
        )


def test_deteccao_infantil_diverge_e_esta_registrada():
    """0–14 conta todas as entradas — a extração não cruza idade com modo de
    entrada. Ficamos sistematicamente acima do boletim, muito além da
    defasagem: em 2024, 125 contra 108. Ver docs/paridade-hanseniase.md §1.

    O teste prende a divergência: quando o microdado chegar e ela sumir, é
    aqui que se vem apagar esta exceção.
    """
    esperado = REFERENCIA["serie_pe"]["2024"]["casos_0_14"]
    nosso = _pe(2024).casos_0_14
    assert nosso > esperado * (1 + MARGEM_ACIMA), (
        "0–14 passou a bater com o boletim — se o microdado chegou, atualize "
        "a §1 da paridade e troque este teste pelo de igualdade"
    )


def test_coorte_aberta_suprime_os_indicadores_de_acompanhamento():
    """2025 tem 19% das saídas registradas: cura, abandono e contatos saem
    nulos em vez de 30,4%, que seria lido como programa ruim."""
    k = _pe(2025)
    assert k.coorte_aberta is True
    assert k.cura_pct is None and k.abandono_pct is None and k.contatos_pct is None
    # O GIF é preenchido no diagnóstico, não no acompanhamento: continua.
    assert k.gif_avaliado_pct is not None


# --- 3. município a município, com a Tabela 2 -------------------------------
#
# A comparação por município é a mais dura que existe para este painel: são
# 185 unidades, e um erro de recorte geográfico ou de definição de caso novo
# aparece aqui antes de aparecer em qualquer outro lugar.

MUNICIPIOS = json.loads(
    (Path(__file__).parent / "referencia_boletim_municipios.json").read_text(
        encoding="utf-8"
    )
)

#: Numeração oficial das Regionais de Saúde de PE. O boletim escreve
#: "I GERES"; o painel usa o nome da sede, que é como a malha da SES-PE
#: identifica a região. A correspondência foi conferida pelos números de
#: 2024 — três batem exatamente (VI/Arcoverde 100, XI/Serra Talhada 71,
#: V/Garanhuns 51) e as demais ficam dentro da defasagem de extração.
GERES_PARA_REGIAO = {
    "I": "Recife",
    "II": "Limoeiro",
    "III": "Palmares",
    "IV": "Caruaru",
    "V": "Garanhuns",
    "VI": "Arcoverde",
    "VII": "Salgueiro",
    "VIII": "Petrolina",
    "IX": "Ouricuri",
    "X": "Afogados da Ingazeira",
    "XI": "Serra Talhada",
    "XII": "Goiana",
}


@pytest.fixture(scope="module")
def casos_municipais():
    from src.data import leitura

    esc = Escopo("HANSENIASE", 2024, "UF", uf="PE")
    return leitura.valores_por_geografia(esc, "casos")


def _comparaveis(casos_municipais):
    """(nosso, deles) de cada município com caso em pelo menos uma fonte."""
    for codigo, linha in MUNICIPIOS["municipios"].items():
        nosso = float(casos_municipais.get(codigo, 0.0))
        if nosso or linha["casos"]:
            yield linha["nome"], nosso, linha["casos"]


def test_a_tabela_2_cobre_os_185_municipios():
    assert len(MUNICIPIOS["municipios"]) == 185
    assert len(MUNICIPIOS["regionais"]) == 12


def test_maioria_dos_municipios_bate_no_numero(casos_municipais):
    """Medido em 25/set/2026: 95 dos 136 municípios com caso saem idênticos,
    e a mediana da diferença é zero."""
    pares = list(_comparaveis(casos_municipais))
    iguais = sum(1 for _, nosso, deles in pares if nosso == deles)
    assert len(pares) > 100, "amostra pequena demais — conferir o cruzamento"
    assert iguais / len(pares) >= 0.6, (
        f"só {iguais} de {len(pares)} municípios batem — conferir a definição "
        f"de caso novo ou o recorte por residência"
    )


def test_nenhum_municipio_fica_muito_abaixo_do_boletim(casos_municipais):
    """Nossa extração é posterior e o SINAN cresce: ficar abaixo só se
    explica por reclassificação de residência entre extrações, que mexe em
    um ou dois casos. Uma queda grande seria município sumindo do recorte."""
    abaixo = [
        (nome, nosso, deles)
        for nome, nosso, deles in _comparaveis(casos_municipais)
        if nosso < deles - 3
    ]
    assert not abaixo, f"municípios muito abaixo do boletim: {abaixo}"


def test_o_estado_inteiro_fica_acima_do_boletim(casos_municipais):
    nosso = float(casos_municipais.sum())
    deles = sum(linha["casos"] for linha in MUNICIPIOS["municipios"].values())
    assert nosso >= deles, f"{nosso} contra {deles} — extração não encolhe"
    assert nosso <= deles * (1 + MARGEM_ACIMA)


@pytest.mark.parametrize("geres", sorted(GERES_PARA_REGIAO))
def test_regioes_de_saude_batem_com_as_geres(geres: str):
    """Valida a agregação por região de saúde contra a do boletim — é o
    teste do `recortes.py`: município no recorte errado aparece aqui."""
    from src.data import leitura

    esperado = MUNICIPIOS["regionais"][geres]["casos"]
    esc = Escopo("HANSENIASE", 2024, "UF", uf="PE")
    nosso = float(leitura.valores_por_regiao(esc, "casos", "micro")[GERES_PARA_REGIAO[geres]])
    assert nosso >= esperado - 3, f"{geres} GERES: {nosso} contra {esperado}"
    assert nosso <= esperado * (1 + MARGEM_REGIAO) + 5, (
        f"{geres} GERES: {nosso} contra {esperado} — município no recorte errado?"
    )


# --- 3. contatos examinados: o gráfico e o card contam a mesma coisa --------


def test_a_serie_de_qualidade_bate_com_os_cards_no_mesmo_ano():
    """Os Gráficos 10 a 13 e os cards de qualidade saem de contas escritas em
    lugares diferentes — `leitura.serie_qualidade` e `kpis.calcular` — e é
    exatamente assim que dois números do mesmo indicador se separam na mesma
    tela. O teste amarra os quatro.
    """
    from src.data import leitura

    esc = Escopo(doenca="HANSENIASE", ano=2024, nivel="UF", uf="PE", mun=None,
                 municipios=())
    serie = leitura.serie_qualidade(esc).set_index("ano").loc[2024]
    card = calc.calcular(esc)
    for coluna, do_card in (
        ("contatos_pct", card.contatos_pct),
        ("cura_pct", card.cura_pct),
        ("abandono_pct", card.abandono_pct),
        ("gif_avaliado_pct", card.gif_avaliado_pct),
        ("grau2_pct", card.prop_grau2_pct),
    ):
        assert float(serie[coluna]) == pytest.approx(do_card, rel=1e-9), coluna
    assert serie["examinados"] == pytest.approx(card.contatos_examinados)
    assert serie["registrados"] == pytest.approx(card.contatos_registrados)


def test_a_serie_de_qualidade_suprime_a_coorte_aberta():
    """2025 não pode aparecer com percentual de acompanhamento: contatos,
    cura e abandono se acumulam ao longo do tratamento, e o ano corrente
    mostraria uma queda que é do calendário. O grau de incapacidade fica: é
    preenchido no diagnóstico, e suprimi-lo esconderia dado que já existe."""
    from src.data import leitura

    esc = Escopo(doenca="HANSENIASE", ano=2025, nivel="UF", uf="PE", mun=None,
                 municipios=())
    serie = leitura.serie_qualidade(esc).set_index("ano")
    for coluna in ("contatos_pct", "cura_pct", "abandono_pct"):
        assert pd.isna(serie.loc[2025, coluna]), coluna
        assert serie.loc[2024, coluna] > 0, coluna
    assert serie.loc[2025, "gif_avaliado_pct"] > 0
    assert serie.loc[2025, "grau2_pct"] > 0


def test_contatos_saiu_dos_topicos_de_interesse():
    """`CONTEXAM`/`CONTREG` como distribuição era o campo da ficha desenhado
    cru — quantos casos tiveram 1, 2, 3 contatos. Virou proporção, que é o
    indicador. Se voltarem ao menu, os dois convivem dizendo coisas
    diferentes sobre a mesma palavra."""
    assert "CONTEXAM" not in pack.variaveis_planas()
    assert "CONTREG" not in pack.variaveis_planas()
    # Continuam numéricas: `kpis` soma ponderado a partir daí.
    assert {"CONTEXAM", "CONTREG"} <= pack.VARIAVEIS_NUMERICAS
