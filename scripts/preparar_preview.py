"""Gera a imagem de prévia que WhatsApp, Slack e Teams mostram no link.

O `assets/preview.png` daqui era cópia do painel nacional, e anunciava
"Painel SINAN · Tuberculose" quando alguém compartilhava o link da
hanseníase. Este script existe para a imagem ser reproduzível: mudou o nome
do painel ou a URL, roda de novo e a prévia acompanha.

As medidas de 1200 × 630 e a paleta vêm da imagem do painel nacional, para os
painéis da família aparecerem iguais quando compartilhados lado a lado.

    python -m scripts.preparar_preview
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

LARGURA, ALTURA = 1200, 630

AZUL = (0, 146, 195)
TERRACOTA = (202, 116, 83)
LARANJA = (237, 133, 58)
GRAFITE = (26, 35, 50)
ARDOSIA = (90, 106, 126)
LINHA = (221, 227, 234)
LINK = (43, 123, 185)
BRANCO = (255, 255, 255)

TITULO = "Painel de Hanseníase · Pernambuco"
SUBTITULO = "Vigilância epidemiológica estadual"
DETALHE = "185 municípios · 12 regiões de saúde · dados do Ministério da Saúde"
ENDERECO = "painel.cenarios.unb.br"

#: Fontes do sistema, em ordem de preferência. Se nenhuma existir, o script
#: para: a fonte embutida do Pillow é bitmap de 11px e produziria uma imagem
#: que ninguém quer ver num grupo de WhatsApp.
FAMILIAS = {
    "negrito": ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"),
    "normal": ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"),
}
PASTAS = (
    pathlib.Path("C:/Windows/Fonts"),
    pathlib.Path("/usr/share/fonts/truetype/dejavu"),
    pathlib.Path("/Library/Fonts"),
)


def _fonte(peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    for nome in FAMILIAS[peso]:
        for pasta in PASTAS:
            caminho = pasta / nome
            if caminho.is_file():
                return ImageFont.truetype(str(caminho), tamanho)
    raise SystemExit(
        f"nenhuma fonte {peso} encontrada em {[str(p) for p in PASTAS]}. "
        f"Instale uma das seguintes: {', '.join(FAMILIAS[peso])}"
    )


def _centrado(desenho: ImageDraw.ImageDraw, y: int, texto: str, fonte, cor) -> None:
    largura = desenho.textbbox((0, 0), texto, font=fonte)[2]
    desenho.text(((LARGURA - largura) // 2, y), texto, font=fonte, fill=cor)


def montar() -> Image.Image:
    imagem = Image.new("RGB", (LARGURA, ALTURA), BRANCO)
    desenho = ImageDraw.Draw(imagem)

    # Faixa superior, a assinatura da família.
    desenho.rectangle([(0, 0), (LARGURA, 10)], fill=LARANJA)

    # A marca é desenhada, não colada: o arquivo do logotipo é JPEG, sem canal
    # alfa, e coleria um retângulo branco sobre o fundo.
    marca, mais = _fonte("negrito", 86), _fonte("negrito", 86)
    largura_marca = desenho.textbbox((0, 0), "Cenários", font=marca)[2]
    largura_mais = desenho.textbbox((0, 0), "+", font=mais)[2]
    x = (LARGURA - largura_marca - largura_mais) // 2
    desenho.text((x, 158), "Cenários", font=marca, fill=AZUL)
    desenho.text((x + largura_marca, 158), "+", font=mais, fill=TERRACOTA)

    _centrado(desenho, 318, TITULO, _fonte("negrito", 54), GRAFITE)
    _centrado(desenho, 396, SUBTITULO, _fonte("normal", 30), ARDOSIA)
    _centrado(desenho, 444, DETALHE, _fonte("normal", 26), ARDOSIA)

    desenho.line([(430, 516), (770, 516)], fill=LINHA, width=2)
    _centrado(desenho, 544, ENDERECO, _fonte("normal", 26), LINK)
    return imagem


def main() -> int:
    destino = pathlib.Path(__file__).resolve().parents[1] / "assets" / "preview.png"
    montar().save(destino, "PNG", optimize=True)
    tamanho = destino.stat().st_size / 1024
    print(f"{destino} gerado ({LARGURA}x{ALTURA}, {tamanho:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
