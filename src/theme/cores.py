"""Manipulação de cor e geração de rampas.

O original em R gera a rampa do mapa a partir de uma única cor base, misturando
com branco e preto em proporções fixas. Isso é o que faz o sistema escalar: a
doença declara uma cor por métrica e todo o resto sai daí.
"""

from __future__ import annotations

Rgb = tuple[float, float, float]

#: Proporções de mistura, na ordem em que compõem a rampa. Os valores são os
#: do dashboard em R, mas o lado escuro é aplicado ao contrário do original.
#:
#: No R, o fallback faz ``mix("#000000", base, t)`` com t crescente — ou seja,
#: t é o peso da *base*, então 0.18 dá quase preto e 0.52 clareia de volta. A
#: rampa resultante não é monotônica: sobe, cai para quase preto, e sobe de
#: novo. O defeito passou despercebido porque a TB declara paletas explícitas
#: e o fallback nunca roda para ela. Aqui t é o peso do preto, que escurece
#: progressivamente como uma escala sequencial exige.
_CLAROS = (0.35, 0.55, 0.72)
_ESCUROS = (0.18, 0.34, 0.52)

BRANCO = "#FFFFFF"
PRETO = "#000000"

#: Cinza usado onde não há dado. Precisa ser distinguível de qualquer tom da rampa.
SEM_DADO = "#F3F4F6"


def hex_para_rgb(cor: str) -> Rgb:
    texto = str(cor or "").strip().lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    if len(texto) != 6:
        raise ValueError(f"Cor hexadecimal inválida: {cor!r}")
    return tuple(int(texto[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_para_hex(rgb: Rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def misturar(a: str, b: str, t: float) -> str:
    """Interpola linearmente entre duas cores. ``t=0`` devolve ``a``, ``t=1`` devolve ``b``."""
    ra, rb = hex_para_rgb(a), hex_para_rgb(b)
    return rgb_para_hex(  # type: ignore[arg-type]
        tuple(x + (y - x) * t for x, y in zip(ra, rb, strict=True))
    )


def rampa(base: str) -> list[str]:
    """Rampa sequencial de 7 tons a partir de uma cor base.

    A base fica no meio; antes dela três tons progressivamente mais claros,
    depois três progressivamente mais escuros.
    """
    claros = [misturar(BRANCO, base, t) for t in _CLAROS]
    escuros = [misturar(base, PRETO, t) for t in _ESCUROS]
    return [*claros, base.upper(), *escuros]


#: Fundo do tema escuro, de `.streamlit/config.toml`.
FUNDO_ESCURO = "#0B1220"

#: Contraste mínimo para texto grande, pela WCAG 2.1 (nível AA). O valor do
#: KPI é 28px em peso 800, então cai nessa faixa.
CONTRASTE_MINIMO = 3.0


def _luminancia(cor: str) -> float:
    # `hex_para_rgb` já devolve 0–1; dividir por 255 outra vez zerava tudo e
    # fazia todo contraste dar 1,0.
    canais = []
    for x in hex_para_rgb(cor):
        canais.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    r, g, b = canais
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razão de contraste entre duas cores, de 1 a 21."""
    la, lb = _luminancia(a), _luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


def para_fundo_escuro(cor: str, fundo: str = FUNDO_ESCURO, alvo: float = 3.5) -> str:
    """Clareia a cor até ela ser legível sobre fundo escuro.

    As cores das métricas foram escolhidas para o tema claro, onde todas
    passam. Sobre o fundo escuro, cinco delas ficavam abaixo do mínimo de
    3:1 para texto grande — incluindo `incid`, que é a métrica padrão e
    portanto o número mais visto do painel, com 2,6:1.

    Clarear preserva a identidade da métrica; trocar por outra cor a
    perderia. O alvo é 3,5 e não 3,0 para haver folga: o valor exato depende
    de arredondamento do navegador.
    """
    if contraste(cor, fundo) >= alvo:
        return cor

    # Mistura com branco em passos pequenos; o primeiro que passa vence.
    for passo in range(1, 21):
        candidato = misturar(cor, "#FFFFFF", passo / 20)
        if contraste(candidato, fundo) >= alvo:
            return candidato
    return "#FFFFFF"
