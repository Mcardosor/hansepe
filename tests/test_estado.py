"""Testes da máquina de navegação.

O `voltar` do original encadeia cinco regras e é onde estado inconsistente
nasce. O teste mais valioso aqui não é caso a caso: é percorrer o caminho de
ida inteiro e voltar passo a passo, conferindo que se chega exatamente ao
ponto de partida.
"""

from __future__ import annotations

import pytest

from src import estado
from src.data.escopo import Escopo
from src.estado import Navegacao


def instantaneo(nav: Navegacao) -> tuple:
    """Só o que define o recorte — ignora doença, ano e métrica."""
    return (nav.nivel, nav.uf, nav.mun, nav.detalhe, nav.recorte, nav.macro, nav.micro)


# ---------------------------------------------------------------------------
# Ida
# ---------------------------------------------------------------------------


def test_comeca_em_pernambuco() -> None:
    """O topo é a UF: não existe nível Brasil neste painel."""
    nav = Navegacao()
    assert nav.nivel == "UF"
    assert nav.uf == "PE"
    assert not nav.pode_voltar


def test_entrar_em_uf_e_municipio() -> None:
    nav = Navegacao()
    nav.entrar_uf("pe")
    assert (nav.nivel, nav.uf) == ("UF", "PE")

    nav.entrar_municipio("2611606", nome="Recife")
    assert nav.nivel == "MUN"
    assert nav.mun == "261160", "o código tem de ser normalizado para 6 dígitos"
    assert nav.nome_mun == "Recife"


def test_escopo_reflete_a_navegacao() -> None:
    nav = Navegacao(ano=2024)
    nav.entrar_uf("PE")
    assert nav.escopo.nivel == "UF"
    assert nav.escopo.uf == "PE"
    assert nav.escopo.ano == 2024


# ---------------------------------------------------------------------------
# Recortes de saúde, exclusivos de PE
# ---------------------------------------------------------------------------


def test_recortes_de_saude_so_existem_em_pe() -> None:
    nav = Navegacao()
    nav.entrar_uf("SP")
    assert not nav.tem_recortes_de_saude
    with pytest.raises(ValueError, match="PE"):
        nav.definir_recorte("MACRO")


def test_trocar_de_uf_para_fora_de_pe_limpa_o_recorte() -> None:
    """Sem isso, sobraria uma macro de PE selecionada num mapa de SP."""
    nav = Navegacao()
    nav.entrar_uf("PE")
    nav.entrar_macro("Sertão")
    nav.entrar_uf("SP")
    assert (nav.recorte, nav.macro, nav.micro) == ("MUN", None, None)


def test_recorte_invalido_falha_claramente() -> None:
    nav = Navegacao()
    nav.entrar_uf("PE")
    with pytest.raises(ValueError, match="Recorte inválido"):
        nav.definir_recorte("ESTADO")


def test_entrar_em_macro_abre_as_regioes_de_saude() -> None:
    nav = Navegacao()
    nav.entrar_uf("PE")
    nav.entrar_macro("Sertão")
    assert (nav.recorte, nav.macro, nav.micro) == ("MICRO", "Sertão", None)


def test_entrar_em_micro_abre_os_municipios() -> None:
    nav = Navegacao()
    nav.entrar_uf("PE")
    nav.entrar_macro("Sertão")
    nav.entrar_micro("Petrolina")
    assert (nav.recorte, nav.macro, nav.micro) == ("MUN", "Sertão", "Petrolina")


# ---------------------------------------------------------------------------
# Volta
# ---------------------------------------------------------------------------


def test_voltar_no_topo_nao_faz_nada() -> None:
    nav = Navegacao()
    antes = instantaneo(nav)
    nav.voltar()
    assert instantaneo(nav) == antes


def test_voltar_fecha_o_detalhe_primeiro() -> None:
    nav = Navegacao()
    nav.entrar_uf("PE")
    nav.entrar_municipio("261160")
    nav.abrir_detalhe()

    nav.voltar()
    assert nav.nivel == "MUN" and not nav.detalhe, "o primeiro voltar só fecha o detalhe"

    nav.voltar()
    assert nav.nivel == "UF"


def test_detalhe_so_existe_em_municipio() -> None:
    nav = Navegacao()
    nav.entrar_uf("PE")
    with pytest.raises(ValueError, match="município"):
        nav.abrir_detalhe()


def test_voltar_do_municipio_retoma_as_regioes_de_saude() -> None:
    """Se o município foi alcançado por uma região de saúde, voltar retoma a lista."""
    nav = Navegacao()
    nav.entrar_uf("PE")
    nav.entrar_macro("Sertão")
    nav.entrar_micro("Petrolina")
    nav.entrar_municipio("261110")

    nav.voltar()
    assert nav.nivel == "UF"
    assert nav.recorte == "MICRO"
    assert nav.micro is None
    assert nav.macro == "Sertão", "a macro continua filtrando"


def test_caminho_completo_de_pe_ida_e_volta() -> None:
    """Percorre o desvio de PE inteiro e volta passo a passo até o início."""
    nav = Navegacao()
    marcos = [instantaneo(nav)]

    for passo in (
        lambda: nav.entrar_uf("PE"),
        lambda: nav.definir_recorte("MACRO"),
        lambda: nav.entrar_macro("Sertão"),
        lambda: nav.entrar_micro("Petrolina"),
        lambda: nav.entrar_municipio("261110", nome="Petrolina"),
        nav.abrir_detalhe,
    ):
        passo()
        marcos.append(instantaneo(nav))

    assert nav.nivel == "MUN" and nav.detalhe

    # Desfaz até o Brasil e confere que não sobra nada preso.
    for _ in range(10):
        nav.voltar()
    assert instantaneo(nav) == marcos[0], "voltar não chegou ao estado inicial"


def test_voltar_de_uf_sem_recorte_fica_na_uf() -> None:
    nav = Navegacao()
    nav.voltar()
    assert nav.nivel == "UF"
    assert nav.uf == "PE"


def test_reset_limpa_tudo_menos_o_ano() -> None:
    nav = Navegacao(ano=2018)
    nav.entrar_uf("PE")
    nav.entrar_macro("Sertão")
    nav.entrar_micro("Petrolina")
    nav.entrar_municipio("261110")
    nav.abrir_detalhe()

    nav.reset()
    assert instantaneo(nav) == ("UF", "PE", None, False, "MUN", None, None)
    assert nav.ano == 2018, "o ano é recorte temporal, não geográfico"


def test_voltar_repetido_e_estavel() -> None:
    """Chamar voltar além do topo não pode produzir estado inválido."""
    nav = Navegacao()
    nav.entrar_macro("Sertão")
    for _ in range(5):
        nav.voltar()
    assert instantaneo(nav) == ("UF", "PE", None, False, "MUN", None, None)


# ---------------------------------------------------------------------------
# Trilha
# ---------------------------------------------------------------------------


def test_trilha_em_cada_etapa() -> None:
    nav = Navegacao(ano=2024)
    assert nav.trilha() == "UF PE • Ano: 2024"

    nav.definir_recorte("MACRO")
    assert "Macrorregiões" in nav.trilha()

    nav.entrar_macro("Sertão")
    assert "Macro: Sertão" in nav.trilha()
    assert "Regiões de saúde" in nav.trilha()

    nav.entrar_micro("Petrolina")
    assert "Micro: Petrolina" in nav.trilha()
    assert "Municípios" in nav.trilha()

    nav.entrar_municipio("261110", nome="Petrolina")
    assert "Município: Petrolina" in nav.trilha()

    nav.abrir_detalhe()
    assert "detalhe" in nav.trilha()


def test_trilha_usa_o_codigo_quando_falta_o_nome() -> None:
    nav = Navegacao(ano=2024)
    nav.entrar_uf("PE")
    nav.entrar_municipio("261160")
    assert "261160" in nav.trilha()


def test_voltar_de_macro_pula_a_visao_de_municipios() -> None:
    """Assimetria herdada do original, reproduzida de propósito.

    A ida é ``UF (municípios) → UF (macrorregiões)``, mas o voltar em
    ``UF (macrorregiões)`` sai direto para o Brasil, sem passar pela visão de
    municípios. Como o recorte também é um controle visível na barra lateral,
    o usuário consegue voltar a municípios sem usar o botão. Se um dia isso
    for considerado defeito, este teste é o lugar de mudar.
    """
    nav = Navegacao()
    nav.definir_recorte("MACRO")
    nav.voltar()
    assert nav.nivel == "UF"
    assert nav.recorte == "MUN"


# ---------------------------------------------------------------------------
# Nível agregado — regressão de queda em produção
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nivel,esperado", [("BR", "BR"), ("UF", "UF"), ("MUN", "UF"), ("mun", "UF")]
)
def test_nivel_agregado_nunca_devolve_mun(nivel: str, esperado: str) -> None:
    """Mapa e ranking listam o nível *abaixo* do escopo, e MUN não é um deles.

    Sem esta redução o ranking montava ``Escopo(nivel="MUN")`` sem ``mun`` e
    derrubava a página inteira ao entrar num município — o mapa já reduzia,
    o ranking não, e a regra duplicada divergiu.
    """
    assert estado.nivel_agregado(nivel) == esperado


def test_escopo_do_ranking_e_valido_em_toda_a_navegacao() -> None:
    """Percorre o caminho de ida e monta o escopo do ranking em cada parada."""
    nav = estado.Navegacao()
    paradas = [lambda: None, lambda: nav.entrar_uf("PE"),
               lambda: nav.entrar_municipio("261160", "Recife"),
               lambda: nav.abrir_detalhe()]
    for passo in paradas:
        passo()
        # Não pode levantar — era exatamente aqui que estourava.
        Escopo(nav.doenca, nav.ano, estado.nivel_agregado(nav.nivel), uf=nav.uf)
