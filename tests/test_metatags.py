"""O HTML que o Streamlit serve, reescrito no build.

O `index.html` do pacote é a única superfície que um rastreador de prévia e
um leitor de tela veem antes do JavaScript rodar. Duas coisas dependem dela:
o cartão que aparece quando o link é compartilhado, e o idioma com que a
página se declara.
"""

from __future__ import annotations

import pytest

from scripts import preparar_metatags as mt

#: O esqueleto que o Streamlit entrega, reduzido ao que o script procura.
BRUTO = (
    '<!doctype html>\n<html lang="en">\n<head>\n'
    "<title>Streamlit</title>\n</head>\n<body></body>\n</html>\n"
)


def test_a_pagina_se_declara_em_portugues() -> None:
    """`lang="en"` numa página em português não é detalhe de validação.

    O leitor de tela escolhe voz e fonética pelo atributo, e "Hanseníase"
    pronunciado com fonética inglesa não se entende. A WCAG cobra no nível A
    (3.1.1).
    """
    html, feito = mt.transformar(BRUTO)
    assert 'lang="pt-BR"' in html
    assert 'lang="en"' not in html
    assert "idioma" in feito


def test_o_link_compartilhado_leva_titulo_e_imagem() -> None:
    html, feito = mt.transformar(BRUTO)
    assert "metatags" in feito
    for marca in ("og:title", "og:image", "og:url", "twitter:card"):
        assert marca in html, marca
    assert "<title>Streamlit</title>" not in html


def test_rodar_duas_vezes_nao_muda_nada() -> None:
    """O build refaz a cada imagem, e a segunda passada não pode duplicar
    metatag nem reclamar de âncora que já foi consumida."""
    uma, _ = mt.transformar(BRUTO)
    duas, feito = mt.transformar(uma)
    assert duas == uma
    assert feito == []


@pytest.mark.parametrize(
    "html, ausente",
    [
        ('<html lang="en"><title>Outro</title>', "título"),
        ('<html lang="fr"><title>Streamlit</title>', "idioma"),
    ],
)
def test_falha_alto_quando_o_streamlit_muda_o_html(html: str, ausente: str) -> None:
    """Falhar o build é melhor que gerar em silêncio uma imagem errada.

    Sem isto, uma versão nova do Streamlit publicaria um painel que se
    anuncia como "Streamlit" no WhatsApp, ou que volta a se declarar em
    inglês — e ninguém veria até alguém reclamar.
    """
    with pytest.raises(LookupError):
        mt.transformar(html)
