"""Simulação de daltonismo e distância perceptual entre cores.

Serve ao exame de **distinguibilidade**, que é outra pergunta que a de
contraste: contraste responde "dá para ler?"; aqui a pergunta é "dá para
dizer qual é qual?". Duas séries podem ter ótimo contraste com o fundo e
nenhuma diferença entre si.

Simulação pelo método de Viénot, Brettel & Mollon (1999): converte para o
espaço LMS, colapsa o eixo do cone ausente e volta. É o que o Color Oracle
usa. Distância em CIEDE2000, que aproxima a percepção melhor que a
diferença euclidiana em RGB.

Escrito em 05/out/2026, junto com o exame das séries do painel.
"""
import math

LIMITE_CONFORTAVEL = 20.0
LIMITE_MINIMO = 10.0

VISOES = ("normal", "protanopia", "deuteranopia", "tritanopia")


def _srgb_para_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_para_srgb(c):
    c = max(0.0, min(1.0, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return round(max(0.0, min(1.0, v)) * 255)


def hex_para_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def simular(hexa, visao):
    """A cor como alguém com essa visão a vê."""
    if visao == "normal":
        return hexa
    r, g, b = (_srgb_para_linear(x) for x in hex_para_rgb(hexa))
    # RGB linear -> LMS (Hunt-Pointer-Estevez normalizado em D65)
    L = 0.31399022 * r + 0.63951294 * g + 0.04649755 * b
    M = 0.15537241 * r + 0.75789446 * g + 0.08670142 * b
    S = 0.01775239 * r + 0.10944209 * g + 0.87256922 * b
    if visao == "protanopia":
        L = 1.05118294 * M - 0.05116099 * S
    elif visao == "deuteranopia":
        M = 0.9513092 * L + 0.04866992 * S
    else:  # tritanopia
        S = -0.86744736 * L + 1.86727089 * M
    r2 = 5.47221206 * L - 4.6419601 * M + 0.16963708 * S
    g2 = -1.1252419 * L + 2.29317094 * M - 0.1678952 * S
    b2 = 0.02980165 * L - 0.19318073 * M + 1.16364789 * S
    return "#%02X%02X%02X" % tuple(_linear_para_srgb(x) for x in (r2, g2, b2))


def _para_lab(hexa):
    r, g, b = (_srgb_para_linear(x) for x in hex_para_rgb(hexa))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.0
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(c1, c2):
    """CIEDE2000."""
    L1, a1, b1 = _para_lab(c1)
    L2, a2, b2 = _para_lab(c2)
    kL = kC = kH = 1.0
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7))) if Cm else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    else:
        dhp = h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lm, Cp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hm = (h1p + h2p + 360) / 2
    else:
        hm = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm))
         + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.20 * math.cos(math.radians(4 * hm - 63)))
    dTheta = 30 * math.exp(-(((hm - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cp ** 7 / (Cp ** 7 + 25 ** 7)) if Cp else 0
    Sl = 1 + (0.015 * (Lm - 50) ** 2) / math.sqrt(20 + (Lm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cp, 1 + 0.015 * Cp * T
    Rt = -math.sin(math.radians(2 * dTheta)) * Rc
    return math.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2 + (dHp / (kH * Sh)) ** 2
                     + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


def luminosidade(hexa: str) -> float:
    """L* da cor, de 0 (preto) a 100 (branco).

    É o canal que sobrevive a qualquer daltonismo: separar duas coisas por
    luminosidade funciona para todo mundo, separar por matiz não.
    """
    return _para_lab(hexa)[0]
