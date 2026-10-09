"""Roda o `app.py` inteiro, de verdade.

**O buraco que este arquivo fecha.** O resto da suíte nunca executou o
`app.py`: importá-lo dispara o script, então `test_app.py` faz checagem
estática com `ast` — ver docs/manutencao.md, armadilha 8. São 950 linhas de
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

import re  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

from src import resiliencia  # noqa: E402
from src.data import config  # noqa: E402
from src.doencas import hanseniase as pack  # noqa: E402
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
    at = _rodar()
    multi = next(m for m in at.multiselect if m.label == "O que exibir")
    multi.set_value(list(pack.variaveis_planas())).run()
    _conferir(at, "todas as variáveis")


def test_o_seletor_governa_o_cartao_inteiro() -> None:
    """Os indicadores do boletim entraram no mesmo seletor das variáveis da
    ficha (29/set/2026): ficavam fixos, e limpar o seletor deixava quatro
    gráficos órfãos numa caixa que dizia "escolha o que exibir". Esvaziar
    agora esvazia o cartão."""
    at = _rodar()
    multi = next(m for m in at.multiselect if m.label == "O que exibir")
    assert len(multi.value) == 7  # 4 indicadores + 3 distribuições do boletim
    multi.set_value([]).run()
    _conferir(at, "cartão vazio")
    assert any("Nada escolhido" in c.value for c in at.caption if c.value)


def test_os_sete_cards_aparecem_com_numero() -> None:
    at = _rodar(ano=2025)
    _conferir(at, "cards")
    html = " ".join(m.value for m in at.markdown)
    # Casos novos e detecção pela definição do MS (paridade §1); os demais
    # como na origem.
    for texto in ("16,63", "4,02", "1.590", "78", "135", "82,93", "10,04"):
        assert texto in html, f"card com {texto} não apareceu"


def test_um_clique_na_metrica_realca_o_card_na_mesma_passada() -> None:
    """Os cards ficam acima do seletor de métrica. Lendo o valor onde o widget
    é criado, os cards realçavam a métrica antiga e só o rerun seguinte — um
    segundo clique em qualquer coisa — os punha em dia (21/set/2026). A
    métrica muda num callback, antes do script, e o card acompanha no
    primeiro clique."""
    import re

    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE).run()
    from src import doencas

    pack = doencas.carregar()
    seletor = next(w for w in at.segmented_control if w.label == "Métrica")
    # `options` do AppTest são os rótulos formatados; o valor é a chave.
    alvo = next(m for m in pack.METRICAS_MAPA if m != seletor.value)
    seletor.set_value(alvo).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state.nav.metrica == alvo
    html = " ".join(m.value for m in at.markdown)
    # Até o começo do card seguinte, e não uma janela de N caracteres: o
    # `title` do card carrega a explicação da métrica, que cresce quando a
    # ressalva cresce, e uma janela fixa empurrava o rótulo para fora sem
    # que nada tivesse quebrado (28/set/2026).
    cards = re.findall(r'class="kpi-card is-selected[^"]*"((?:(?!kpi-card)[\s\S])*)', html)
    assert len(cards) == 1
    # `rotulo_card`, e não `rotulo_curto`: o botão da métrica continua curto
    # ("Detecção"), mas o card diz "Taxa de detecção" — no card ele compete
    # com "Casos novos" ao lado, e os dois falam de detecção.
    assert pack.rotulo_card(alvo) in cards[0]


@pytest.mark.parametrize("janela", [5, 15])
def test_toda_janela_de_tempo_monta(janela: int) -> None:
    """A janela recorta cinco séries de uma vez — detecção anual, epicurva,
    contatos, classificação operacional e 0–14 — e cada uma tem um formato
    diferente. Um recorte que esvazie qualquer uma delas aparece aqui."""
    at = _rodar()
    botoes = next(c for c in at.segmented_control if c.label == "Janela")
    botoes.set_value(janela).run()
    _conferir(at, f"janela {janela}")


def test_a_janela_abre_em_dez_anos() -> None:
    """Dez é o recorte do Gráfico 1 do boletim. Se o padrão mudar sem
    discussão, este teste é onde a mudança encosta."""
    at = _rodar()
    botoes = next(c for c in at.segmented_control if c.label == "Janela")
    assert botoes.value == 10


def test_o_painel_abre_no_ultimo_ano_de_coorte_fechada() -> None:
    """Abre em 2024, não no último ano disponível.

    Em 2025 a coorte não fechou: cura, abandono e contatos aparecem vazios, e
    quem abre o painel sozinho vê três cards em branco antes de ler o porquê.
    A equipe parceira pediu isso em 02/out/2026.

    Nasceu de um erro: eu troquei o valor padrão do campo `ano` no `Navegacao`
    e não vi que o `app.py` o sobrescrevia com o último ano do disco. Os 423
    testes passaram e o painel subiu abrindo em 2025 do mesmo jeito. O teste é
    sobre o ano que aparece **na tela**, que é onde o erro estava.
    """
    at = _rodar()
    seletor = next(s for s in at.selectbox if s.label == "Ano")
    assert seletor.value == config.ANO_PADRAO
    assert config.ANO_PADRAO != max(seletor.options)


def test_a_vista_em_serie_dos_topicos_monta() -> None:
    """A distribuição ano a ano, pedida pela equipe parceira em outubro.

    Nasceu de um erro meu: a calha reaproveitava `_calha_base`, que lê a
    coluna `total` — existe na composição de um ano, não na série, onde o
    denominador é um por ano. O `KeyError` derrubava a seção inteira de
    tópicos, e a suíte passou porque nenhum teste chegava a trocar a vista.

    O teste roda os três tópicos padrão na vista de série, que é o caminho
    que ninguém exercitava.
    """
    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE)
    at.session_state["vista_topicos"] = "SERIE"
    at.run()
    _conferir(at, "tópicos em série")

    titulos = " ".join(m.value for m in at.markdown)
    assert "por ano" in titulos
    # A calha diz o intervalo e o aviso de que cada coluna soma 100%.
    assert "Cada coluna soma 100%" in titulos


def test_a_serie_de_composicao_fecha_em_cem_por_ano() -> None:
    """Cada coluna é uma distribuição: a soma do ano tem de dar 100.

    Se um dia o leitor passar a trazer categoria repetida, ou a somar o
    percentual sobre a série inteira em vez de sobre o ano, a coluna deixa de
    fechar e o empilhado mente sobre a composição.
    """
    from src.data import leitura
    from src.data.escopo import Escopo

    serie = leitura.serie_composicao(
        Escopo("HANSENIASE", 2024, "UF", uf="PE"),
        "FORMACLINI",
        rotulos=pack.ROTULOS_VALORES.get("FORMACLINI"),
        ordem="codigo",
    )
    assert not serie.empty
    soma = serie.groupby("ano")["pct"].sum()
    assert soma.between(99.9, 100.1).all(), soma[~soma.between(99.9, 100.1)]

    # A ordem de empilhamento é a mesma em todos os anos, senão a faixa de
    # uma categoria troca de altura de um ano para o outro.
    ordens = {tuple(g) for _, g in serie.groupby("ano")["categoria"]}
    assert len(ordens) == 1, f"a ordem das categorias muda entre anos: {ordens}"


def test_a_serie_dos_topicos_ignora_a_janela_de_anos() -> None:
    """A série vai de 2010 em diante, mesmo com a janela em 5 anos.

    A janela de 5/10/15 anos mora na seção de evolução temporal. Respeitá-la
    aqui faria este gráfico mudar por um controle que não está à vista, e o
    pedido era justamente ver o movimento ao longo de todo o período.
    """
    at = AppTest.from_file(APLICACAO, default_timeout=LIMITE)
    at.session_state["vista_topicos"] = "SERIE"
    at.session_state["janela"] = 5
    at.run()
    _conferir(at, "tópicos em série com janela curta")

    texto = " ".join(m.value for m in at.markdown)
    assert "2010 a" in texto, "a calha deveria anunciar a série inteira"


def test_a_base_do_calculo_mostra_a_completude_do_campo() -> None:
    """Quantos preenchidos **de quantos** — pedido da revisão de outubro.

    Com só o número preenchido, a caixa levantava a pergunta que não
    respondia: "tem muita incompletude nessa informação?". A tabela agregada
    não traz os brancos — registros sem o campo simplesmente não têm linha —,
    então o universo vem de fora, do modo de entrada, que todo registro tem.

    Em 2024, em PE, são 2.466 casos, e forma clínica está em 2.337 deles.
    """
    at = _rodar()
    _conferir(at, "base do cálculo com universo")

    texto = " ".join(m.value for m in at.markdown)
    assert "casos com o campo preenchido" in texto
    assert re.search(r"\d[\d.]* de \d[\d.]* casos com o campo preenchido \(\d+,\d%\)", texto), (
        "a caixa deveria trazer preenchidos, total e o percentual"
    )


def test_o_gif_avaliado_nao_repete_a_regua_ao_lado_do_grafico() -> None:
    """A caixa saiu da tela, a citação do boletim ficou no lugar.

    "Eu tiraria a mensagem que está abaixo do % grau de incapacidade. Ela não
    traz nada importante" — revisão de outubro. Não traz mesmo: o card do
    mesmo indicador já termina em "Regular", e a caixa ao lado só reexplicava
    de onde veio a palavra.

    O que não pode sumir é a régua no pacote da doença. Ela é transcrição do
    documento, o teste de paridade a guarda letra por letra, e é dela que sai
    a classe que o card exibe. Apagar o texto para esconder a caixa teria
    levado as três coisas juntas.
    """
    at = _rodar()
    _conferir(at, "sem o quadro do GIF avaliado")

    texto = " ".join(m.value for m in at.markdown)
    assert "% Grau de incapacidade" not in texto, "o quadro voltou à tela"
    # A régua segue no pacote, e o card segue classificando por ela.
    assert pack.texto_parametros("gif_avaliado_pct") is not None
    assert pack.classe_de("gif_avaliado_pct", 82.66) == "Regular"
    # E os outros indicadores de qualidade continuam com o quadro deles.
    assert "% Cura" in texto and "% Abandono" in texto
