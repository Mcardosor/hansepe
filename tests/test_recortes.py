"""Recortes administrativos de saúde.

Hoje só PE tem, mas a camada é genérica: acrescentar uma UF é registrar uma
entrada em `CONFIGURACOES`, sem tocar em código.

A junção é por **nome** de região entre duas fontes independentes — o
`municipios.csv` e os shapefiles — e a agregação precisa recalcular taxas em
vez de tirar média delas. São os dois pontos onde isto quebra em silêncio.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data import geo, leitura, recortes
from src.data.escopo import Escopo

ESCOPO = Escopo("HANSENIASE", 2024, "UF", uf="PE")


def test_lookup_cobre_todos_os_municipios_de_pe() -> None:
    tabela = recortes.lookup()
    assert len(tabela) == 185
    assert tabela["cod_mun6"].is_unique
    assert tabela["cod_mun6"].str.fullmatch(r"\d{6}").all()


def test_codigo_e_arredondado_e_nao_truncado() -> None:
    """Oito dos 185 municípios estão gravados com erro de ponto flutuante.

    São Vicente Férrer aparece como 2613799.9999999995 no CSV. Truncar dá
    261379 em vez de 261380, o município deixa de casar com os dados e some da
    agregação por região — sem erro nenhum, só um total menor.
    """
    codigos = set(recortes.lookup()["cod_mun6"])
    assert "261380" in codigos, "São Vicente Férrer truncado"
    assert "261460" in codigos, "Tabira truncado"
    assert "261379" not in codigos
    assert "261459" not in codigos


def test_lookup_casa_com_os_dados_sem_sobra() -> None:
    """Qualquer município fora da junção seria caso desaparecendo do mapa."""
    componentes = leitura.componentes_municipais(ESCOPO)
    codigos_lookup = set(recortes.lookup()["cod_mun6"])
    assert set(componentes.index) == codigos_lookup


def test_nomes_de_regiao_batem_com_a_geometria() -> None:
    """Duas fontes independentes; um acento a mais quebraria a junção."""
    for nivel, coluna in (("macro", "macro"), ("micro", "micro")):
        do_csv = {recortes._chave(v) for v in recortes.lookup()[coluna]}
        da_malha = {recortes._chave(v) for v in geo.regioes('PE', nivel)["regiao"]}
        assert do_csv == da_malha, f"{nivel}: {do_csv ^ da_malha}"


def test_quatro_macros_e_doze_regioes_de_saude() -> None:
    assert len(recortes.macros()) == 4
    assert len(recortes.micros()) == 12


def test_micros_filtradas_por_macro() -> None:
    assert recortes.micros("Agreste") == ["Caruaru", "Garanhuns"]
    todas = {m for macro in recortes.macros() for m in recortes.micros(macro)}
    assert todas == set(recortes.micros())


def test_municipios_de_uma_regiao() -> None:
    recife = recortes.municipios_de(micro="Recife")
    assert "261160" in recife
    soma = sum(len(recortes.municipios_de(macro=m)) for m in recortes.macros())
    assert soma == 185, "todo município pertence a exatamente uma macro"


# ---------------------------------------------------------------------------
# Agregação
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nivel", ["macro", "micro"])
@pytest.mark.parametrize("metrica", ["casos", "cura", "pop"])
def test_contagens_fecham_com_a_uf(nivel: str, metrica: str) -> None:
    componentes = leitura.componentes_municipais(ESCOPO)
    por_regiao = leitura.valores_por_regiao(ESCOPO, metrica, nivel)
    assert por_regiao.sum() == pytest.approx(componentes[metrica].sum())


@pytest.mark.parametrize("nivel", ["macro", "micro"])
def test_taxa_e_recalculada_e_nao_promediada(nivel: str) -> None:
    """Média de taxas municipais pesaria Recife igual a um município de 2 mil.

    A incidência de uma região tem de sair de `casos/pop` somados, o que dá
    resultado diferente da média simples das incidências municipais.
    """
    componentes = leitura.componentes_municipais(ESCOPO)
    coluna = "macro" if nivel == "macro" else "micro"
    tabela = recortes.lookup().set_index("cod_mun6")[[coluna]]
    juncao = componentes.join(tabela, how="inner")

    correto = leitura.valores_por_regiao(ESCOPO, "incid", nivel)
    somas = juncao.groupby(coluna).sum(numeric_only=True)
    esperado = somas["casos"] / somas["pop"] * 100_000
    assert correto.reindex(esperado.index).to_numpy() == pytest.approx(
        esperado.to_numpy()
    )

    # E tem de diferir da média simples, senão o teste não prova nada.
    juncao["incid_mun"] = juncao["casos"] / juncao["pop"].replace(0, pd.NA) * 100_000
    media = juncao.groupby(coluna)["incid_mun"].mean()
    assert not correto.reindex(media.index).to_numpy() == pytest.approx(
        media.to_numpy()
    )


def test_metrica_sem_componentes_devolve_vazio() -> None:
    componentes = leitura.componentes_municipais(ESCOPO)
    assert recortes.agregar(componentes, "cura_pct", "macro").empty


def test_agregacao_com_entrada_vazia_nao_quebra() -> None:
    vazio = pd.DataFrame(columns=["casos", "pop"], index=pd.Index([], name="cod_mun6"))
    assert recortes.agregar(vazio, "casos", "macro").empty


def test_indice_da_agregacao_e_o_nome_da_regiao() -> None:
    """A geometria identifica a região pelo nome; o índice tem de bater."""
    valores = leitura.valores_por_regiao(ESCOPO, "casos", "macro")
    assert set(valores.index) == set(geo.regioes("PE", "macro")["regiao"])


# ---------------------------------------------------------------------------
# Rótulo da busca
# ---------------------------------------------------------------------------


def test_regiao_desempata_municipios_de_nome_parecido() -> None:
    """A busca mostra "Nome — Região de saúde", como no original.

    PE tem municípios de nome próximo em regiões diferentes; sem o sufixo, a
    lista fica ambígua.
    """
    tabela = recortes.lookup()
    regiao = tabela.set_index("cod_mun6")["micro"]
    assert regiao.notna().all()
    assert not regiao.eq("").any()
    # todo município tem exatamente uma região de saúde
    assert len(regiao) == len(tabela)


def test_toda_regiao_de_saude_tem_municipio() -> None:
    for micro in recortes.micros():
        assert recortes.municipios_de(micro=micro), f"{micro} sem município"


def test_recorte_por_regiao_e_subconjunto_da_uf() -> None:
    """O mapa filtra a malha pela região; o subconjunto tem de ser válido."""
    todos = set(geo.municipios("PE")["cod_mun6"])
    for micro in recortes.micros():
        dentro = set(recortes.municipios_de(micro=micro))
        assert dentro <= todos, f"{micro} tem município fora da malha de PE"
        assert dentro, f"{micro} vazia"


# ---------------------------------------------------------------------------
# A camada é genérica
# ---------------------------------------------------------------------------
# O projeto é nacional; o recorte de saúde é uma camada por cima, hoje só de
# PE. O que importa nestes testes é que acrescentar um estado seja
# configuração, não refatoração.


def test_registro_expoe_as_ufs_configuradas() -> None:
    assert "PE" in recortes.ufs_com_recorte()
    assert recortes.configurada("pe"), "a sigla deve ser case-insensitive"
    assert not recortes.configurada("BA")
    assert not recortes.configurada(None)


def test_uf_sem_recorte_falha_com_mensagem_util() -> None:
    """A mensagem tem de dizer quais existem, não só que a pedida não existe."""
    with pytest.raises(ValueError, match="BA"):
        recortes.config_de("BA")
    with pytest.raises(ValueError, match="PE"):
        recortes.config_de("BA")


def test_configuracao_carrega_os_rotulos() -> None:
    """A nomenclatura varia entre estados; a interface mostra a do estado."""
    cfg = recortes.config_de("PE")
    assert cfg.rotulo_macro and cfg.rotulo_micro
    assert cfg.arquivo == "municipios.csv"


def test_funcoes_aceitam_a_uf_como_parametro() -> None:
    """Sem isso, um segundo estado exigiria mexer em cada função."""
    import inspect

    for fn in (recortes.lookup, recortes.macros, recortes.micros,
               recortes.municipios_de, recortes.agregar):
        assert "uf" in inspect.signature(fn).parameters, f"{fn.__name__} sem `uf`"


def test_geometria_e_enderecada_por_uf() -> None:
    """`geo.regioes` monta o caminho pela sigla, não com 'pe' fixo."""
    import inspect

    from src.data import geo

    assert "uf" in inspect.signature(geo.regioes).parameters
    assert len(geo.regioes("PE", "macro")) == 4


def test_navegacao_consulta_o_registro() -> None:
    """A máquina de estados não compara com a string 'PE'."""
    from src.estado import Navegacao

    nav = Navegacao()
    nav.entrar_uf("PE")
    assert nav.tem_recortes_de_saude
    nav.entrar_uf("BA")
    assert not nav.tem_recortes_de_saude
    with pytest.raises(ValueError, match="recorte de saúde"):
        nav.definir_recorte("MACRO")


# ---------------------------------------------------------------------------
# Forma clínica no mapa
# ---------------------------------------------------------------------------


def test_a_chave_da_metrica_de_forma_e_a_mesma_nos_dois_lados() -> None:
    """A constante é repetida de propósito, e por isso precisa de guarda.

    A camada de dados não importa pacote de doença, e o pacote não conhece o
    leitor. Se as duas divergirem, o mapa não estoura: cai no caminho
    genérico e pinta outra coisa, em silêncio.
    """
    from src.data import leitura
    from src.doencas import hanseniase as pack

    assert leitura.METRICA_FORMA == pack.METRICA_FORMA


def test_casos_por_forma_somam_o_que_a_tabela_agregada_diz() -> None:
    """O mapa por forma tem de bater com o gráfico de composição.

    São a mesma variável lida de dois jeitos: a composição soma o estado, o
    mapa reparte por município. Divergir aqui seria o painel discordar de si
    mesmo em duas telas.
    """
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    esc = Escopo(pack.DOENCA, 2024, "UF", uf="PE")
    composicao = leitura.composicao(esc, "FORMACLINI").set_index("categoria")["n"]

    for codigo in pack.FORMAS_CLINICAS:
        no_mapa = leitura.valores_por_geografia(esc, pack.METRICA_FORMA, forma=codigo)
        assert no_mapa.sum() == composicao.get(codigo, 0), pack.rotulo_forma(codigo)


def test_municipio_sem_a_forma_vale_zero_e_nao_sem_dado() -> None:
    """Zero é informação; "sem dado" é a falta dela.

    A tabela de variáveis só lista quem notificou — em 2024 são 152 dos 185
    municípios de PE. Usando o universo dela, os 33 restantes sairiam cinza,
    como se nada se soubesse deles. Sabe-se: não houve caso.
    """
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    valores = leitura.valores_por_geografia(
        Escopo(pack.DOENCA, 2024, "UF", uf="PE"), pack.METRICA_FORMA, forma="2"
    )
    assert len(valores) == 185, "o mapa pinta os 185 municípios"
    assert not valores.isna().any(), "município sem a forma virou sem dado"
    assert (valores == 0).any(), "nenhum município zerado é improvável"


@pytest.mark.parametrize("nivel", ["macro", "micro"])
def test_a_soma_por_regiao_nao_perde_nem_inventa_caso(nivel: str) -> None:
    """Contagem se soma; é só o que a agregação por região faz aqui.

    Taxa precisa de denominador e passa pela agregação geral. Casos por forma
    não: somar os municípios da região é a conta inteira.
    """
    from src.data import leitura
    from src.data.escopo import Escopo
    from src.doencas import hanseniase as pack

    esc = Escopo(pack.DOENCA, 2024, "UF", uf="PE")
    por_municipio = leitura.valores_por_geografia(esc, pack.METRICA_FORMA, forma="3")
    por_regiao = leitura.valores_por_regiao(esc, pack.METRICA_FORMA, nivel, forma="3")

    assert por_regiao.sum() == por_municipio.sum()
    assert len(por_regiao) == (4 if nivel == "macro" else 12)
