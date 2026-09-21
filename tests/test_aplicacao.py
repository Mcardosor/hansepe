"""Roda o `app.py` inteiro, de verdade.

**O buraco que este arquivo fecha.** O resto da suíte nunca executou o
`app.py`: importá-lo dispara o script, então `test_app.py` faz checagem
estática com `ast` — ver CLAUDE.md, armadilha 8. São 950 linhas de
orquestração que nenhum teste percorria, e é exatamente onde os erros deste
projeto têm acontecido: uma constante usada antes de existir, uma variável
definida depois do primeiro uso, um `zip` que trunca.

O `AppTest` do Streamlit resolve isso sem contradizer a armadilha: ele executa
o script num contexto controlado, em vez de importá-lo. A aplicação inteira
sobe em cerca de 1,5 s.

**O que se verifica em cada estado:** nenhuma exceção, e nenhum painel caído.
A segunda parte importa mais que parece — `resiliencia.painel` contém a falha
de um painel no próprio painel, o que é ótimo em produção e péssimo num teste
ingênuo: sem olhar o aviso, a página "sobe" com metade dos gráficos quebrados
e o teste passa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import resiliencia  # noqa: E402
from src.estado import Navegacao  # noqa: E402

#: Generoso porque a primeira execução paga a leitura de geometria; as demais
#: pegam cache. Um teste que falha por lentidão de máquina vira ruído.
LIMITE = 180

#: Caminho absoluto: o `AppTest` resolve relativo ao diretório do teste, não à
#: raiz do repositório.
APLICACAO = str(Path(__file__).resolve().parents[1] / "app.py")


def _rodar(**estado) -> AppTest:
    """Sobe a aplicação, opcionalmente com a navegação já posicionada.

    Entrar numa UF é clique no mapa, que o `AppTest` não alcança — o deck.gl é
    componente externo. Então o recorte é posto direto no estado, que é o
    mesmo objeto que o clique manipularia.
    """
    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE)
    if estado:
        nav = Navegacao(doenca="HANSENIASE", ano=estado.pop("ano", 2024))
        for chave, valor in estado.items():
            setattr(nav, chave, valor)
        at.session_state["nav"] = nav
    return at.run()


def _conferir(at: AppTest, contexto: str) -> None:
    assert not at.exception, (
        f"{contexto}: {[e.value for e in at.exception]}"
    )
    caidos = [w.value for w in at.warning if resiliencia.AVISO in w.value]
    assert not caidos, f"{contexto}: painel caído — {caidos}"


def test_a_aplicacao_sobe_em_pernambuco() -> None:
    """O caso mais simples, e o que pega erro de importação e de ordem."""
    at = _rodar()
    _conferir(at, "PE")
    assert at.markdown, "a página subiu vazia"
    assert any("Painel de Monitoramento da Hanseníase de PE" in m.value for m in at.markdown)


@pytest.mark.parametrize("metrica", ["incid", "taxa_det_0_14", "casos", "casos_0_14", "cura"])
def test_toda_metrica_do_mapa_monta(metrica: str) -> None:
    _conferir(_rodar(metrica=metrica), metrica)


@pytest.mark.parametrize("recorte", ["MUN", "MACRO", "MICRO"])
def test_todo_recorte_de_saude_monta(recorte: str) -> None:
    _conferir(_rodar(recorte=recorte), recorte)


def test_entrar_numa_macrorregiao_recorta_as_regioes() -> None:
    at = _rodar(recorte="MICRO", macro="Vale S.Francisco/Araripe")
    _conferir(at, "macro")


def test_a_aplicacao_sobe_com_municipio_selecionado() -> None:
    """Nível de município, que tem painéis com dado escasso."""
    _conferir(_rodar(nivel="MUN", mun="261160", nome_mun="Recife"), "Recife")


def test_a_aplicacao_sobe_com_municipio_pequeno() -> None:
    """Município sem caso no ano: nada pode cair por série vazia."""
    _conferir(_rodar(nivel="MUN", mun="260030", nome_mun="Agrestina"), "Agrestina")


def test_a_aplicacao_sobe_com_municipio_destacado() -> None:
    _conferir(_rodar(destacado="261160", nome_destacado="Recife"), "PE com destaque")


@pytest.mark.parametrize("ano", [2010, 2019, 2025])
def test_a_aplicacao_sobe_em_anos_extremos(ano: int) -> None:
    """2010 não tem ano anterior nem anos de referência para o canal; 2025 é
    o último e não tem SIM."""
    _conferir(_rodar(ano=ano), str(ano))


def test_ano_fechado_nao_recebe_aviso_de_incompleto() -> None:
    """Ano parcial se detecta pelos meses com dado, não se presume. 2025 tem
    12 meses no `_cache_ts` e não pode ser marcado como incompleto."""
    at = _rodar(ano=2025)
    _conferir(at, "2025")
    assert not any("incompleto" in w.value for w in at.warning)


def test_as_duas_vistas_da_evolucao_montam() -> None:
    at = _rodar()
    radio = next(r for r in at.radio if "Todos os anos" in r.options)
    radio.set_value("Todos os anos").run()
    _conferir(at, "todos os anos")


def test_o_filtro_de_grau_do_canal_monta() -> None:
    at = _rodar()
    sel = next(s for s in at.selectbox if "Grau II" in s.options)
    sel.set_value("Grau II").run()
    _conferir(at, "grau II")


def test_a_piramide_por_100_mil_monta() -> None:
    at = _rodar()
    toggle = next(t for t in at.toggle if "100 mil" in t.label)
    toggle.set_value(True).run()
    _conferir(at, "pirâmide por 100 mil")


def test_toda_variavel_da_composicao_monta() -> None:
    from src.doencas import hanseniase as pack

    at = _rodar()
    multi = next(m for m in at.multiselect if m.label == "Variáveis")
    multi.set_value(list(pack.variaveis_planas())).run()
    _conferir(at, "todas as variáveis")


def test_os_sete_cards_aparecem_com_numero() -> None:
    at = _rodar(ano=2025)
    _conferir(at, "cards")
    html = " ".join(m.value for m in at.markdown)
    # Casos novos e detecção pela definição do MS (paridade §1); os demais
    # como na origem.
    for texto in ("16,63", "4,02", "1.590", "78", "135", "82,93", "10,04"):
        assert texto in html, f"card com {texto} não apareceu"
