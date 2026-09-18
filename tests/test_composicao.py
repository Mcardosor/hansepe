"""Testes da composição por variável do SINAN.

O ponto sensível é a supressão do percentual em base pequena. Ela mora na
camada de dados de propósito: se ficasse no gráfico, qualquer outro consumidor
— uma exportação, uma API, um notebook — publicaria a proporção sem base.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import graficos
from src.data import leitura
from src.data.escopo import Escopo
from src.doencas import hanseniase as pack


def test_catalogo_nao_tem_codigo_repetido() -> None:
    """Um código em dois grupos faria o seletor mostrar a variável duas vezes."""
    planos = pack.variaveis_planas()
    soma = sum(len(g) for g in pack.VARIAVEIS.values())
    assert len(planos) == soma


def test_catalogo_so_tem_variavel_que_existe_no_dado() -> None:
    """Rótulo bonito de variável inexistente vira painel vazio em produção."""
    existentes = set(leitura.dicionario(pack.DOENCA)["variavel"])
    faltando = [c for c in pack.variaveis_planas() if c not in existentes]
    assert not faltando, f"variáveis fora do dicionário: {faltando}"


def test_pack_nao_tem_catalogo_paralelo() -> None:
    """Havia um segundo catálogo, morto e errado.

    `VARIAVEIS_COMPOSICAO`/`ROTULOS_COMPOSICAO` nunca foram referenciados —
    o painel era placeholder — e listavam `AGRAVDROGAS` e `AGRAVTABACO`, que
    não existem nos parquets. Catálogo que ninguém usa não é conferido por
    ninguém; este teste impede o próximo.
    """
    assert not hasattr(pack, "VARIAVEIS_COMPOSICAO")
    assert not hasattr(pack, "ROTULOS_COMPOSICAO")


def test_catalogo_exclui_as_numericas() -> None:
    """`NU_COMU_EX` tem 141 valores e `EXTRAPUL_O`, 1.587 — viram parede."""
    planos = pack.variaveis_planas()
    assert "NU_COMU_EX" not in planos
    assert "EXTRAPUL_O" not in planos


@pytest.mark.parametrize("variavel", list(pack.variaveis_planas()))
def test_toda_variavel_do_catalogo_devolve_algo(variavel: str) -> None:
    dados = leitura.composicao(Escopo(pack.DOENCA, 2024, "BR"), variavel)
    assert not dados.empty, f"{variavel} sem dado no Brasil em 2024"
    assert list(dados.columns) == ["categoria", "n", "pct", "total"]
    assert (dados["n"] > 0).all()


def test_percentual_soma_cem_quando_a_base_permite() -> None:
    dados = leitura.composicao(Escopo(pack.DOENCA, 2024, "BR"), "CLASSOPERA")
    assert dados["pct"].sum() == pytest.approx(100.0)


def test_base_pequena_nao_produz_percentual() -> None:
    """993 dos 4.148 municípios com notificação em 2024 têm um caso só.

    Sem esta regra, dois registros viravam "100% Não realizado" — ruído
    apresentado como achado, e num município pequeno o cruzamento deixa de
    ser agregado na prática.
    """
    dados = leitura.composicao(
        Escopo(pack.DOENCA, 2024, "MUN", uf="BA", mun="290689"), "CLASSOPERA"
    )
    if dados.empty:
        pytest.skip("município sem registro")
    assert dados["total"].iloc[0] < leitura.MINIMO_PARA_PERCENTUAL
    assert dados["pct"].isna().all()
    # A contagem continua à vista: a regra é estatística, não censura.
    assert (dados["n"] > 0).all()


def test_grafico_troca_o_eixo_conforme_a_base() -> None:
    grande = leitura.composicao(Escopo(pack.DOENCA, 2024, "BR"), "CLASSOPERA")
    pequeno = leitura.composicao(
        Escopo(pack.DOENCA, 2024, "MUN", uf="BA", mun="290689"), "CLASSOPERA"
    )
    eixo = lambda d: graficos.composicao(
        d, rotulo="Classificação operacional", cor="#B4442E"
    ).to_dict()["encoding"]["x"]["title"]

    assert eixo(grande) == "% dos casos"
    if not pequeno.empty:
        assert eixo(pequeno) == "Casos"


def test_grafico_vazio_nao_quebra() -> None:
    vazio = pd.DataFrame(columns=["categoria", "n", "pct", "total"])
    assert graficos.composicao(vazio, rotulo="X", cor="#000") is not None


def test_contagem_nao_conta_em_dobro() -> None:
    """`sinan_landing` tem linha TOTAL além de M, F e I.

    A linha TOTAL já é a soma das outras — conferido em 9,97 milhões de
    combinações, sem exceção. Somar tudo dava exatamente o dobro, e a
    contagem exibida no painel de composição saía dobrada. A proporção nunca
    sentiu, porque numerador e denominador dobravam juntos; foi por isso que
    o defeito sobreviveu à comparação com o painel em R, que tem o mesmo.
    """
    from src.data import conexao, config

    esc = Escopo(pack.DOENCA, 2024, "UF", uf="PE")
    nosso = int(leitura.variavel_sinan(esc, "TPALTA_N")["n"].sum())

    caminho = str(config.dashboard_dir() / "sinan_landing" / "**" / "*.parquet")
    bruto = conexao.conectar().execute(
        """
        SELECT sum(CASE WHEN sexo = 'TOTAL' THEN n ELSE 0 END) AS total,
               sum(CASE WHEN sexo <> 'TOTAL' THEN n ELSE 0 END) AS partes
        FROM read_parquet(?, hive_partitioning=true)
        WHERE ano = 2024 AND variavel = 'TPALTA_N' AND nivel = 'UF' AND uf = 'PE'
        """,
        [caminho],
    ).fetchone()

    assert bruto[0] == bruto[1], "TOTAL deixou de ser a soma das partes"
    assert nosso == bruto[0], "o leitor não está usando só a linha TOTAL"
    assert nosso * 2 == bruto[0] + bruto[1], "somar tudo continua dobrando"
