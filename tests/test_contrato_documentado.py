"""A lista de variáveis do `contrato-dados.md` contra o que o código lê.

Escrita em 02/out/2026, quando a equipe do banco perguntou se a documentação
listava tudo que a aplicação precisa — e não listava. Um documento que serve
para **pedir dado ao banco** não pode envelhecer em silêncio: se alguém
acrescentar uma variável ao pack e não ao documento, o próximo pedido de view
sai incompleto e o painel quebra em produção, não aqui.
"""

from __future__ import annotations

import pathlib
import re

from src.doencas import hanseniase as pack

CONTRATO = pathlib.Path(__file__).resolve().parents[1] / "docs/contrato-dados.md"


def _variaveis_do_documento() -> set[str]:
    """As variáveis da **tabela** da seção 'O que pedir ao banco'.

    Só as linhas de tabela: o parágrafo seguinte cita as chaves da ficha
    (`CO_MUNI_RESIDENCIA` e companhia), que não são variáveis tabuladas.
    """
    texto = CONTRATO.read_text(encoding="utf-8")
    inicio = texto.index("### SINAN —")
    fim = texto.index("### O que falta", inicio)
    linhas = [l for l in texto[inicio:fim].splitlines() if l.startswith("| `")]
    return set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", chr(10).join(linhas)))


def _variaveis_do_codigo() -> set[str]:
    return {v for grupo in pack.VARIAVEIS.values() for v in grupo} | set(
        pack.VARIAVEIS_NUMERICAS
    )


def test_o_documento_lista_toda_variavel_que_o_painel_le() -> None:
    faltando = _variaveis_do_codigo() - _variaveis_do_documento()
    assert not faltando, (
        f"variáveis lidas pelo painel e ausentes do contrato-dados.md: "
        f"{sorted(faltando)}. Quem pedir a view ao banco não vai pedi-las."
    )


def test_o_documento_nao_inventa_variavel() -> None:
    """O erro simétrico: pedir ao banco um campo que ninguém lê."""
    sobrando = _variaveis_do_documento() - _variaveis_do_codigo()
    assert not sobrando, (
        f"o contrato-dados.md pede {sorted(sobrando)}, que o painel não lê"
    )
