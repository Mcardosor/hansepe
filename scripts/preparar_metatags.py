"""Injeta título, descrição e Open Graph no HTML que o Streamlit serve.

Sem isto, compartilhar o link mostra **"Streamlit"** como título e nada mais:
o `page_title` do `st.set_page_config` é aplicado por JavaScript depois da
carga, e nenhum rastreador de prévia — WhatsApp, Slack, Teams — espera o JS
rodar. Eles leem o HTML cru, que traz `<title>Streamlit</title>` e nenhuma
meta de descrição.

O Streamlit não expõe configuração para isso, então o jeito é reescrever o
`index.html` do pacote. Roda no `Dockerfile`, depois do `pip install`: a
alteração fica versionada aqui, é refeita a cada build e some junto com a
imagem — nada é modificado na máquina de quem desenvolve.

**Falha alto de propósito.** Se uma versão nova do Streamlit mudar o HTML e a
âncora não for encontrada, o build quebra em vez de gerar em silêncio uma
imagem que volta a se anunciar como "Streamlit".
"""

from __future__ import annotations

import io
import pathlib
import sys

TITULO = "Painel de Hanseníase · Pernambuco — Cenários+"
DESCRICAO = (
    "Vigilância epidemiológica da hanseníase em Pernambuco: 185 municípios, "
    "12 regiões e 4 macrorregiões de saúde, com a escala de endemicidade do "
    "Ministério da Saúde. Dados do SINAN."
)
URL = "https://painel.cenarios.unb.br/cenarios/hansepe/"
IMAGEM = URL + "preview.png"

ANCORA = "<title>Streamlit</title>"

NOVO = f"""<title>{TITULO}</title>
    <meta name="description" content="{DESCRICAO}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="Cenários+" />
    <meta property="og:title" content="{TITULO}" />
    <meta property="og:description" content="{DESCRICAO}" />
    <meta property="og:url" content="{URL}" />
    <meta property="og:image" content="{IMAGEM}" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{TITULO}" />
    <meta name="twitter:description" content="{DESCRICAO}" />
    <meta name="twitter:image" content="{IMAGEM}" />"""


def main() -> int:
    import streamlit

    estatico = pathlib.Path(streamlit.__file__).parent / "static"
    indice = estatico / "index.html"
    # Com `with`, e não `io.open(...).read()`: o alvo é reescrito logo abaixo,
    # e no Windows um descritor ainda aberto no mesmo arquivo faz a escrita
    # falhar — em build de container passa despercebido porque lá é Linux.
    with io.open(indice, encoding="utf-8") as arquivo:
        html = arquivo.read()

    if "og:title" in html:
        print("metatags já presentes — nada a fazer")
        return 0

    if ANCORA not in html:
        print(
            f"ERRO: não encontrei {ANCORA!r} em {indice}.\n"
            "O HTML do Streamlit mudou. Ajuste `ANCORA` antes de seguir — sem "
            "isso o painel volta a se anunciar como 'Streamlit' ao ser "
            "compartilhado.",
            file=sys.stderr,
        )
        return 1

    with io.open(indice, "w", encoding="utf-8") as arquivo:
        arquivo.write(html.replace(ANCORA, NOVO, 1))
    print(f"metatags injetadas em {indice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
