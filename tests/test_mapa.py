"""Testes da escala do mapa.

A escala por quantil é o que faz um coroplético epidemiológico ser legível:
poucos municípios concentram o volume, e uma escala linear jogaria quase todos
na mesma cor. Os casos difíceis não são os dados bem-comportados — são os
recortes onde metade dos municípios tem zero.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import mapa
from src.data import geo
from src.doencas import hanseniase as tb

RAMPA = tb.rampa_mapa("casos")


def _gvf(valores: pd.Series, escala) -> float:
    """Quanto da variância a classificação explica. 1,0 seria perfeito.

    É o critério do Jenks: soma dos desvios dentro de cada classe contra a
    soma dos desvios em torno da média geral.
    """
    import numpy as np

    v = valores.to_numpy(dtype=float)
    total = ((v - v.mean()) ** 2).sum()
    if not total:
        return 1.0
    idx = np.clip(np.searchsorted(escala.cortes, v, side="right") - 1, 0, len(escala.cortes) - 2)
    dentro = sum(((v[idx == i] - v[idx == i].mean()) ** 2).sum() for i in set(idx))
    return 1 - dentro / total


def test_escala_uniforme_fica_equilibrada() -> None:
    """Sem cauda, quebras naturais dão classes parecidas com os quantis.

    Serve de piso: a troca de esquema não pode desequilibrar o caso fácil.
    """
    valores = pd.Series(range(600))
    escala = mapa.escala_natural(valores, RAMPA)

    assert escala.classes == mapa.CLASSES
    contagem = mapa.classificar(valores, escala).value_counts()
    assert contagem.max() / contagem.min() < 1.5, (
        f"classes desequilibradas em dado uniforme: {dict(contagem)}"
    )


def test_a_escala_nao_comprime_a_cauda() -> None:
    """O motivo da troca, preso em teste.

    A incidência tem cauda longa, e classe de igual frequência põe tudo que é
    extremo no mesmo balde: em PE, 29 municípios dividiam uma cor cobrindo de
    59 a 445 por 100 mil — Itapissuma e Goiana pintados iguais com seis vezes
    de diferença. Num painel de vigilância o topo é o que se olha.

    O teste compara com o esquema antigo no mesmo dado: quebras naturais têm
    de explicar mais variância que os quantis.
    """
    import numpy as np

    rng = np.random.default_rng(42)
    cauda = pd.Series(np.concatenate([rng.gamma(1.2, 8, 400), [180, 240, 445]]))

    escala = mapa.escala_natural(cauda, RAMPA)
    quantis = mapa.Escala(
        cortes=sorted(set(np.quantile(cauda, np.linspace(0, 1, mapa.CLASSES + 1)))),
        rotulos=[],
        cores={},
    )

    assert _gvf(cauda, escala) > _gvf(cauda, quantis) + 0.2, (
        f"naturais {_gvf(cauda, escala):.3f} contra quantis {_gvf(cauda, quantis):.3f} — "
        f"a vantagem sumiu; a classificação voltou a comprimir a cauda?"
    )

    # E o topo não pode virar um balde só: o maior valor tem de estar numa
    # classe menor que a metade dos dados.
    no_topo = int((cauda >= escala.cortes[-2]).sum())
    assert no_topo < len(cauda) / 8, f"{no_topo} de {len(cauda)} na classe do topo"


def test_toda_classe_tem_cor() -> None:
    escala = mapa.escala_natural(pd.Series(range(100)), RAMPA)
    for rotulo in escala.rotulos:
        assert rotulo in escala.cores
    assert escala.cores[mapa.ROTULO_SEM_DADO] == mapa.SEM_DADO


def test_valor_minimo_entra_na_primeira_classe() -> None:
    """`pd.cut` exclui o limite inferior por padrão — o menor viraria "sem dado"."""
    valores = pd.Series([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    escala = mapa.escala_natural(valores, RAMPA)
    classes = mapa.classificar(valores, escala)
    assert classes.iloc[0] != mapa.ROTULO_SEM_DADO


def test_maioria_zerada_nao_gera_classes_vazias() -> None:
    """Recorte pequeno: 70 municípios sem caso e 30 com.

    Sem colapsar quantis repetidos, vários cortes cairiam em zero e a legenda
    mostraria classes "0,0 a 0,0" idênticas.
    """
    valores = pd.Series([0] * 70 + list(range(1, 31)))
    escala = mapa.escala_natural(valores, RAMPA)

    assert len(set(escala.rotulos)) == len(escala.rotulos), "há classes repetidas"
    classes = mapa.classificar(valores, escala)
    assert classes.notna().all()
    assert set(classes.unique()) <= set(escala.rotulos) | {mapa.ROTULO_SEM_DADO}


def test_valor_unico_produz_uma_classe() -> None:
    escala = mapa.escala_natural(pd.Series([7.0] * 20), RAMPA)
    assert escala.classes == 1
    classes = mapa.classificar(pd.Series([7.0] * 20), escala)
    assert (classes != mapa.ROTULO_SEM_DADO).all()


def test_serie_vazia_nao_quebra() -> None:
    escala = mapa.escala_natural(pd.Series([], dtype=float), RAMPA)
    assert escala.classes == 0
    classes = mapa.classificar(pd.Series([1.0, 2.0]), escala)
    assert (classes == mapa.ROTULO_SEM_DADO).all()


@pytest.mark.parametrize("ruim", [np.nan, np.inf, -np.inf, None])
def test_valores_invalidos_viram_sem_dado(ruim) -> None:
    valores = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, ruim], dtype=float)
    escala = mapa.escala_natural(valores, RAMPA)
    classes = mapa.classificar(valores, escala)
    assert classes.iloc[-1] == mapa.ROTULO_SEM_DADO


def test_cor_de_sem_dado_nao_colide_com_a_rampa() -> None:
    """Cinza tem de ser distinguível de qualquer tom, senão some no mapa."""
    escala = mapa.escala_natural(pd.Series(range(100)), RAMPA)
    tons = {v.upper() for k, v in escala.cores.items() if k != mapa.ROTULO_SEM_DADO}
    assert mapa.SEM_DADO.upper() not in tons


def test_rotulos_em_portugues() -> None:
    escala = mapa.escala_natural(pd.Series([0.0, 1234.5, 2000.0] * 5), RAMPA)
    assert any("," in r for r in escala.rotulos), "decimal tem de ser vírgula"


# ---------------------------------------------------------------------------
# Enquadramento
# ---------------------------------------------------------------------------


def test_enquadrar_centraliza_no_bbox() -> None:
    """Longitude é média simples; latitude, média em Mercator.

    O centro vertical da projeção não é a média dos graus: o Mercator estica
    conforme se afasta do equador. Para o Brasil a diferença chega a 0,8°, o
    bastante para Roraima e Amapá saírem pela borda de cima depois que o
    enquadramento passou a ser justo.
    """
    quadro = mapa.enquadrar((-40.0, -10.0, -30.0, -5.0))
    assert quadro["center"]["lon"] == pytest.approx(-35.0)

    esperado = mapa._mercator_inverso(
        (mapa._mercator(-10.0) + mapa._mercator(-5.0)) / 2
    )
    assert quadro["center"]["lat"] == pytest.approx(esperado)
    assert quadro["center"]["lat"] != pytest.approx(-7.5, abs=1e-4), (
        "voltou a centralizar pela média dos graus"
    )


def test_enquadrar_cabe_nas_duas_bordas() -> None:
    """O que o corte do mapa do Brasil denunciou: precisa caber em cima e embaixo."""

    from src.data import geo

    limites = tuple(geo.pais().total_bounds)
    quadro = mapa.enquadrar(limites)
    escala = 256 * 2 ** quadro["zoom"] / 360
    meio = mapa._mercator(quadro["center"]["lat"])

    for lat in (limites[1], limites[3]):
        distancia = abs(mapa._mercator(lat) - meio) * escala
        assert distancia <= mapa.ALTURA / 2, f"latitude {lat} sai do painel"

    for lon in (limites[0], limites[2]):
        distancia = abs(lon - quadro["center"]["lon"]) * escala
        assert distancia <= mapa.LARGURA_PAINEL / 2, f"longitude {lon} sai do painel"


def test_recorte_menor_recebe_zoom_maior() -> None:
    from src.data import geo

    pais = mapa.enquadrar(tuple(geo.pais().total_bounds))
    estado = mapa.enquadrar(tuple(geo.municipios("PE").total_bounds))
    assert estado["zoom"] > pais["zoom"]


def test_zoom_fica_dentro_de_limites_usaveis() -> None:
    minusculo = mapa.enquadrar((-35.0, -8.0, -35.0001, -8.0001))
    enorme = mapa.enquadrar((-180.0, -90.0, 180.0, 90.0))
    assert 2.0 <= minusculo["zoom"] <= 11.0
    assert 2.0 <= enorme["zoom"] <= 11.0


def test_bbox_degenerado_nao_quebra() -> None:
    quadro = mapa.enquadrar((-35.0, -8.0, -35.0, -8.0))
    assert quadro["zoom"] > 0
    assert quadro["center"]["lon"] == pytest.approx(-35.0)


# ---------------------------------------------------------------------------
# Clique no mapa (pydeck)
# ---------------------------------------------------------------------------
# O coroplético do Plotly não emite evento de clique — ver docs/mapa-clique.md.
# O `GeoJsonLayer` do deck.gl faz picking por GPU, e o evento do
# `st.pydeck_chart` traz a feição inteira, com as propriedades dela.


class _Evento:
    def __init__(self, selection):
        self.selection = selection


def _evento_com(props: dict):
    return _Evento({"objects": {"camada-0": [{"properties": props}]}})


def test_extrai_uf_do_clique() -> None:
    assert mapa.alvo_do_clique(_evento_com({"uf": "PE"})) == "PE"


def test_extrai_municipio_do_clique() -> None:
    props = {"cod_mun6": "261160", "nome_mun": "Recife", "uf": "PE"}
    assert mapa.alvo_do_clique(_evento_com(props)) == "261160"


def test_municipio_tem_precedencia_sobre_a_uf() -> None:
    """A feição de município também carrega `uf`; a chave mais específica vence."""
    props = {"uf": "PE", "cod_mun6": "261160"}
    assert mapa.alvo_do_clique(_evento_com(props)) == "261160"


def test_extrai_regiao_de_saude() -> None:
    assert mapa.alvo_do_clique(_evento_com({"regiao": "Sertão"})) == "Sertão"


@pytest.mark.parametrize(
    "evento",
    [
        None,
        _Evento(None),
        _Evento({}),
        _Evento({"objects": {}}),
        _Evento({"objects": {"camada-0": []}}),
        _Evento({"objects": {"camada-0": [{"properties": {}}]}}),
        _Evento({"objects": {"camada-0": ["texto solto"]}}),
        {"selection": {"objects": {"camada-0": [{"properties": {"uf": "SP"}}]}}},
    ],
)
def test_evento_estranho_nao_derruba_a_pagina(evento) -> None:
    """O formato do evento é detalhe interno do Streamlit e já mudou entre
    versões. Se vier algo inesperado, o mapa apenas não navega."""
    resultado = mapa.alvo_do_clique(evento)
    assert resultado is None or isinstance(resultado, str)


def test_evento_em_dicionario_tambem_funciona() -> None:
    bruto = {"selection": {"objects": {"c": [{"properties": {"uf": "BA"}}]}}}
    assert mapa.alvo_do_clique(bruto) == "BA"


# ---------------------------------------------------------------------------
# Legenda em HTML
# ---------------------------------------------------------------------------


def test_a_legenda_apagada_nao_muda_a_cor_de_quem_esta_na_faixa() -> None:
    """Clicar numa faixa apaga o resto: quem está nela mantém RGB de três
    canais (opaco), quem está fora ganha o quarto canal com a opacidade
    baixa. Trocar a cor dos escolhidos, em vez de apagar os outros, faria o
    mapa mentir sobre a classe."""
    escala = mapa.escala_natural(pd.Series(range(100)), RAMPA)
    assert len(mapa._rgb(escala.cores[escala.rotulos[0]])) == 3


def test_faixa_inexistente_nao_apaga_o_mapa_inteiro() -> None:
    """O rótulo da última interação sobrevive no `session_state` quando a
    métrica muda, e as faixas da escala nova são outras. Sem a guarda, todo
    município cairia na condição "fora da faixa" e o mapa sairia apagado."""
    from src.data import geo, leitura
    from src.data.escopo import Escopo

    camada = geo.municipios("PE")
    esc = Escopo(doenca="HANSENIASE", ano=2024, nivel="UF", uf="PE", mun=None,
                 municipios=())
    valores = leitura.valores_por_geografia(esc, "incid")
    _, escala = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=RAMPA,
        rotulo_metrica="Detecção", coluna_nome="nome_mun",
        faixa_realcada="faixa que não existe",
    )
    assert escala.rotulos


def test_deck_pinta_cada_feicao() -> None:
    from src.data import geo, leitura
    from src.data.escopo import Escopo

    camada = geo.municipios("PE")
    valores = leitura.valores_por_geografia(Escopo("HANSENIASE", 2024, "UF", uf="PE"), "incid")
    desenho, escala = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=RAMPA, rotulo_metrica="Incidência"
    )
    # Três e não uma: PE tem Fernando de Noronha, que ganha quadro de destaque
    # com moldura e rótulo. Ver `mapa.destacar_ilhas`.
    assert [c.type for c in desenho.layers] == ["GeoJsonLayer", "PolygonLayer", "TextLayer"]
    assert escala.classes == mapa.CLASSES


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

#: Teto do JSON que o mapa manda ao navegador, em MB, no pior recorte que
#: temos — Minas Gerais, com 853 municípios.
#:
#: Medido em 0,71 MB depois de tirar a indentação. O teto de 1,0 MB dá folga
#: para a malha mudar sem alarme falso, e ainda assim pega uma regressão do
#: tamanho da que existia: com `indent=2` do pydeck eram 2,76 MB.
TETO_PAYLOAD_MB = 1.0


def _payload(uf: str) -> str:
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    camada = geo.municipios(uf)
    valores = leitura.valores_por_geografia(Escopo("HANSENIASE", 2024, "UF", uf=uf), "incid")
    figura, _ = mapa.deck(
        camada,
        valores,
        chave="cod_mun6",
        rampa=pack.rampa_mapa("incid"),
        rotulo_metrica="Incidência",
        coluna_nome="nome_mun",
    )
    return figura.to_json()


def test_payload_do_mapa_cabe_no_teto() -> None:
    """O mosaico volta pela rede a cada navegação e a cada troca de métrica.

    As cores fazem parte do mesmo spec, então não é custo de primeira carga.
    Em localhost isso é invisível; sobre rede real dominava tudo.
    """
    tamanho = len(_payload("MG").encode("utf-8")) / 1e6
    assert tamanho < TETO_PAYLOAD_MB, (
        f"payload de MG em {tamanho:.2f} MB, teto {TETO_PAYLOAD_MB} MB. "
        f"A compactação de `mapa._compactar` provavelmente parou de valer."
    )


def test_payload_sai_sem_indentacao() -> None:
    """Regressão direta: `pydeck.serialize` usa `indent=2` por padrão.

    `_compactar` engole exceções de propósito, para uma mudança de API interna
    do pydeck não derrubar o mapa — o preço é que a falha seria silenciosa.
    Este teste é quem faz barulho.
    """
    texto = _payload("PE")
    assert '\n  "' not in texto, "voltou a indentar"
    assert ", " not in texto[:200], "separadores não estão compactos"


def _montar_features(uf: str, geometrias=None):
    import json

    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    camada = geo.municipios(uf)
    valores = leitura.valores_por_geografia(Escopo("HANSENIASE", 2024, "UF", uf=uf), "incid")
    figura, _ = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=pack.rampa_mapa("incid"),
        rotulo_metrica="Incidência", coluna_nome="nome_mun", geometrias=geometrias,
    )
    return json.loads(figura.to_json())["layers"][0]["data"]["features"]


def test_geometria_pronta_nao_muda_o_desenho() -> None:
    """Reaproveitar a malha convertida não pode alterar o que é desenhado.

    A conversão custa 75 ms em MG e é o item mais caro de montar o mapa — mas
    o ganho não vale nada se servir geometria diferente.
    """
    convertidas = mapa.geometrias_geojson(geo.municipios("PE"))
    sem, com = _montar_features("PE"), _montar_features("PE", convertidas)

    assert len(sem) == len(com)
    for a, b in zip(sem, com, strict=True):
        assert a["geometry"] == b["geometry"]
        assert a["properties"] == b["properties"]


def test_geometria_de_tamanho_errado_e_ignorada() -> None:
    """A guarda que impede servir a malha de outro recorte.

    Se a lista não corresponde à camada, `deck` volta ao caminho normal em vez
    de emparelhar geometria de um município com o dado de outro.
    """
    de_outro_estado = mapa.geometrias_geojson(geo.municipios("MG"))
    assert len(de_outro_estado) != len(geo.municipios("PE"))

    correto = _montar_features("PE")
    com_lista_errada = _montar_features("PE", de_outro_estado)
    assert [f["geometry"] for f in com_lista_errada] == [
        f["geometry"] for f in correto
    ], "a lista de tamanho errado foi usada em vez de descartada"


def test_coordenadas_vao_arredondadas_para_o_navegador() -> None:
    """Precisão além do pixel é peso que atravessa a rede sem chegar aos olhos.

    A malha vem com seis casas decimais — 11 cm. O mapa é desenhado em cerca
    de 430px cobrindo um estado inteiro; em Minas, um pixel vale perto de 2 km.
    Medido: arredondar a cinco casas tira 29% do payload de MG, de 0,62 para
    0,44 MB, sem diferença visível.

    Cinco casas, e não quatro: 1,1 m dá folga para o modo detalhe, que
    enquadra um único município.
    """
    import json
    import re

    gj = mapa.geometrias_geojson(geo.municipios("PE"))
    texto = json.dumps(gj)
    casas = [len(d) for d in re.findall(r"-?\d+\.(\d+)", texto)]

    assert casas, "não encontrei coordenadas decimais"
    assert max(casas) <= mapa.CASAS_COORDENADA, (
        f"há coordenada com {max(casas)} casas decimais, acima do teto de "
        f"{mapa.CASAS_COORDENADA} — o arredondamento saiu de `geometrias_geojson`"
    )


def test_os_dois_caminhos_arredondam_igual() -> None:
    """Reaproveitar a malha convertida não pode mudar o traçado.

    `deck` aceita a geometria pronta para o chamador memoizar. Se só um dos
    caminhos arredondasse, o mapa mudaria de desenho conforme o cache estivesse
    quente ou frio — e ninguém desconfiaria da causa.
    """
    convertidas = mapa.geometrias_geojson(geo.municipios("PE"))
    sem, com = _montar_features("PE"), _montar_features("PE", convertidas)
    assert [f["geometry"] for f in sem] == [f["geometry"] for f in com]


# ---------------------------------------------------------------------------
# Ilhas oceânicas
# ---------------------------------------------------------------------------


def test_limites_uteis_ignoram_ilha_oceanica() -> None:
    """O enquadramento é calculado sobre o retângulo dos dados.

    Com a ilha dentro, o território que se quer ver encolhe para caber junto
    com um pedaço de terra a centenas de quilômetros. O Brasil inteiro
    desenhava 13% menor por causa de Trindade e Martim Vaz, ilhas do Espírito
    Santo onde ninguém mora.
    """
    largura = lambda lim: lim[2] - lim[0]  # noqa: E731

    pe = geo.municipios("PE")
    assert largura(pe.total_bounds) == pytest.approx(9.0, abs=0.1)
    assert largura(mapa.limites_uteis(pe)[0]) == pytest.approx(6.6, abs=0.1)

    br = geo.ufs()
    assert largura(br.total_bounds) == pytest.approx(45.1, abs=0.1)
    assert largura(mapa.limites_uteis(br)[0]) == pytest.approx(39.2, abs=0.1)


@pytest.mark.parametrize("uf", ["MG", "SP", "BA", "RS"])
def test_limites_uteis_nao_mexem_em_quem_nao_tem_ilha(uf: str) -> None:
    """A regra é geométrica, não uma lista de exceções — e por isso precisa
    provar que não recorta território legítimo de quem não tem ilha."""
    camada = geo.municipios(uf)
    assert tuple(mapa.limites_uteis(camada)[0]) == pytest.approx(
        tuple(camada.total_bounds), abs=0.01
    )


def test_so_vira_destaque_quem_sumiria_da_tela() -> None:
    """Trindade não ganha quadro; Fernando de Noronha ganha.

    A diferença é se a **feição** some. Trindade é parte do Espírito Santo,
    que continua visível pelo continente — tirá-la do enquadramento basta.
    Fernando de Noronha é um município inteiro, com casos: fora do
    enquadramento ele desapareceria do mapa e deixaria de ser clicável.
    """
    _, fora_no_brasil = mapa.limites_uteis(geo.ufs())
    assert fora_no_brasil == [], "nenhuma UF some da tela — todas têm continente"

    pe = geo.municipios("PE")
    _, fora_em_pe = mapa.limites_uteis(pe)
    assert [pe.loc[i, "nome_mun"] for i in fora_em_pe] == ["Fernando de Noronha"]

    # O Espírito Santo é o caso que separa as duas situações. Descendo aos
    # municípios dele, Trindade é uma **parte** de Vitória, não um município.
    # O enquadramento encolhe de 13,03° para 2,21° — o estado deixa de ser
    # espremido para caber junto com uma ilha a 1.100 km —, e ainda assim
    # nenhum quadro é preciso: Vitória continua na tela pelo continente.
    es = geo.municipios("ES")
    limites_es, fora_em_es = mapa.limites_uteis(es)
    assert es.total_bounds[2] - es.total_bounds[0] == pytest.approx(13.03, abs=0.05)
    assert limites_es[2] - limites_es[0] == pytest.approx(2.21, abs=0.05)
    assert fora_em_es == []


def test_a_ilha_destacada_conserva_o_que_a_torna_clicavel() -> None:
    """Mover a geometria não pode mover o município para outro lugar do dado.

    O clique e o tooltip saem das **propriedades** da feição. Se `destacar_ilhas`
    reconstruísse a linha em vez de trocar só a geometria, a ilha continuaria
    desenhada e pararia de responder ao clique — o pior dos dois mundos, porque
    parece funcionar.
    """
    pe = geo.municipios("PE")
    limites, ilhas = mapa.limites_uteis(pe)
    antes = pe.loc[ilhas[0]].drop("geometry")

    movido, moldura = mapa.destacar_ilhas(pe, mapa.extensao_visivel(limites), ilhas)
    depois = movido.loc[ilhas[0]].drop("geometry")

    assert antes.equals(depois)
    assert len(movido) == len(pe), "nenhuma feição pode entrar nem sair"
    assert moldura is not None


def test_a_ilha_destacada_cai_dentro_da_area_visivel() -> None:
    """O quadro vai na margem que o painel mostra, não no canto dos dados.

    Na primeira tentativa ele foi para o canto do retângulo de dados e caiu em
    cima da costa nordeste do próprio estado — PE é largo e baixo, e o canto
    superior direito dos dados é território.
    """
    pe = geo.municipios("PE")
    limites, ilhas = mapa.limites_uteis(pe)
    visivel = mapa.extensao_visivel(limites)
    movido, (x0, y0, x1, y1) = mapa.destacar_ilhas(pe, visivel, ilhas)

    assert visivel[0] <= x0 and x1 <= visivel[2], "quadro sai pela lateral"
    assert visivel[1] <= y0 and y1 <= visivel[3], "quadro sai por cima ou por baixo"
    assert y0 > limites[3], "o quadro precisa ficar acima do território, não sobre ele"

    ilha = movido.loc[ilhas[0]].geometry.bounds
    assert x0 <= ilha[0] and ilha[2] <= x1, "a ilha vazou da moldura"


def test_com_municipio_destacado_o_quadro_da_ilha_nao_e_desenhado() -> None:
    """Com foco num município, o enquadramento é a vizinhança dele — no meio
    do estado. O quadro da ilha, posto no canto dessa janela, caía em cima de
    outros municípios com "fora de escala" escrito sobre a terra (Gameleira,
    21/set/2026). Sem foco o quadro existe; com foco, não."""
    import json

    from src import doencas

    pack = doencas.carregar()
    pe = geo.municipios("PE")
    valores = pd.Series(1.0, index=pe["cod_mun6"].astype(str))

    def moldura(destacado):
        desenho, _ = mapa.deck(
            pe, valores, chave="cod_mun6", rampa=pack.rampa_mapa("incid"),
            rotulo_metrica="x", coluna_nome="nome_mun", destacado=destacado,
        )
        spec = json.loads(desenho.to_json())
        return [c for c in spec["layers"] if c["@@type"] == "PolygonLayer"]

    assert moldura(None), "sem foco o quadro da ilha tem de existir"
    gameleira = pe.loc[pe["nome_mun"].str.contains("Gameleira"), "cod_mun6"].iloc[0]
    assert not moldura(str(gameleira)), "com foco o quadro caía sobre a terra"


def test_o_destaque_aproxima_mas_nao_perde_o_contexto() -> None:
    """Acender sem aproximar deixa a pergunta sem resposta.

    Recife tem 0,23° num estado de 6,55°: o contorno sai com três pixels e
    "onde fica" continua no ar. Mas enquadrar **só** o município responde
    outra pergunta — como ele é por dentro —, e aí some a referência.
    """
    pe = geo.municipios("PE")
    limites, _ = mapa.limites_uteis(pe)
    recife = tuple(pe[pe["nome_mun"] == "Recife"].total_bounds)

    foco = mapa.enquadrar_foco(limites, recife)
    largura_foco = foco[2] - foco[0]

    assert largura_foco > (recife[2] - recife[0]) * 2, "aproximou demais"
    assert largura_foco < (limites[2] - limites[0]), "não aproximou"


def test_o_foco_nao_sai_do_recorte() -> None:
    """Município de borda puxaria o enquadramento para fora do estado.

    Fora dali não há dado nenhum: sobraria oceano, ou território vizinho em
    branco fingindo ser 'sem dado'.
    """
    pe = geo.municipios("PE")
    limites, _ = mapa.limites_uteis(pe)

    for nome in ("Petrolina", "Recife", "Afrânio"):
        alvo = pe[pe["nome_mun"] == nome]
        if alvo.empty:
            continue
        f = mapa.enquadrar_foco(limites, tuple(alvo.total_bounds))
        # Tolerância porque o grampo encosta exatamente na borda, e aí a
        # comparação vira ruído de ponto flutuante.
        folga = 1e-9
        assert limites[0] - folga <= f[0] and f[2] <= limites[2] + folga, (
            f"{nome} vazou na horizontal"
        )
        assert limites[1] - folga <= f[1] and f[3] <= limites[3] + folga, (
            f"{nome} vazou na vertical"
        )


def test_municipio_maior_que_o_estado_nao_estoura_o_foco() -> None:
    """Barcelos sozinho tem quase a largura do Amazonas.

    Cinco vezes o tamanho dele daria um enquadramento maior que a UF, e o
    grampo tem de segurar sem inverter o retângulo.
    """
    am = geo.municipios("AM")
    limites, _ = mapa.limites_uteis(am)
    barcelos = am[am["nome_mun"] == "Barcelos"]
    if barcelos.empty:
        pytest.skip("Barcelos não está na camada")

    f = mapa.enquadrar_foco(limites, tuple(barcelos.total_bounds))
    assert f[0] < f[2] and f[1] < f[3], "retângulo invertido"
    assert f[2] - f[0] <= limites[2] - limites[0] + 1e-9


def test_destacar_ilha_nao_aproxima() -> None:
    """Fernando de Noronha já aparece ampliada no quadro do canto.

    Aproximar nela levaria o enquadramento para o meio do oceano, e o estado
    sumiria da tela.
    """
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    pe = geo.municipios("PE")
    valores = leitura.valores_por_geografia(Escopo("HANSENIASE", 2024, "UF", uf="PE"), "incid")

    def zoom(destacado):
        figura, _ = mapa.deck(
            pe, valores, chave="cod_mun6", rampa=pack.rampa_mapa("incid"),
            rotulo_metrica="Incidência", destacado=destacado,
        )
        return figura.initial_view_state.zoom

    assert zoom("260545") == pytest.approx(zoom(None)), "aproximou na ilha"
    assert zoom("261160") > zoom(None), "não aproximou no continente"


def test_o_atlas_de_fonte_cobre_o_texto_que_a_camada_desenha() -> None:
    """Caractere fora do atlas do deck.gl vira **espaço em branco**.

    Não vira caractere errado nem quadradinho: some. "Maués" saía "Mau s", e
    como quase todo município brasileiro tem acento, o defeito valia para a
    maioria dos nomes — mas só aparecia no destaque, que é onde o mapa escreve
    nome em vez de número.
    """
    import json

    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    camada = geo.municipios("AM")
    alvo = camada[camada["nome_mun"] == "Maués"]
    if alvo.empty:
        pytest.skip("Maués não está na camada")

    valores = leitura.valores_por_geografia(Escopo("HANSENIASE", 2024, "UF", uf="AM"), "incid")
    figura, _ = mapa.deck(
        camada, valores, chave="cod_mun6", rampa=pack.rampa_mapa("incid"),
        rotulo_metrica="Incidência", destacado=alvo["cod_mun6"].iloc[0],
    )

    for camada_json in json.loads(figura.to_json())["layers"]:
        if camada_json["@@type"] != "TextLayer" or not camada_json.get("data"):
            continue
        conjunto = camada_json.get("characterSet")
        assert isinstance(conjunto, list), (
            f"characterSet virou {conjunto!r} — o pydeck converteu em acessor. "
            f"Passe tupla, não lista nem string."
        )
        for linha in camada_json["data"]:
            faltando = [c for c in linha["texto"] if c not in conjunto]
            assert not faltando, f"{linha['texto']!r} perde {faltando} no atlas"
