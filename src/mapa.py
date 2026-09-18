"""Mapa coroplético.

Desenhado com **pydeck**. A escolha começou no Plotly, pelo evento de clique
nativo do ``st.plotly_chart``, mas o coroplético do Plotly não dispara esse
evento — nem na versão maplibre nem na SVG. O ``GeoJsonLayer`` do deck.gl faz
*picking* por GPU e resolveu. O caminho descartado está registrado em
docs/mapa-clique.md; o código dele foi removido para não dar a impressão de
que há duas rotas mantidas.

A escala é por **quantil**, como no original. Em dados epidemiológicos poucos
municípios concentram o volume, e uma escala linear achata todo o resto numa
cor só.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Número de classes da escala. Valor do original.
CLASSES = 6

#: Cor de quem não tem dado. Precisa ser distinguível de qualquer tom da rampa.
SEM_DADO = "#F3F4F6"

#: Altura do mapa, em pixels. O painel reserva `ALTURA_MIN_MAPA`.
#:
#: Casada com `LARGURA_PAINEL`, não escolhida à parte. O Brasil é quase
#: quadrado — 45,1 graus de largura por 41,2 em Mercator — e o enquadramento
#: pega o menor dos dois ajustes, então altura de menos faz a altura virar o
#: teto e a largura nova ser desperdiçada: com 580x460 o país saía 504x460,
#: preso pela altura. 530 é o que 580 de largura pede (580 x 41,2 / 45,1), e o
#: Brasil desenha 580x529.
#:
#: Eram 460, casados com os 430 de largura de quando a barra lateral existia.
#: Baixar mais aperta o ranking, que divide a linha e recebe `ALTURA - 46`.
ALTURA = 530

ROTULO_SEM_DADO = "sem dado"

def _caracteres(textos) -> tuple[str, ...]:
    """Conjunto de caracteres para o atlas de fonte de uma camada de texto.

    O `TextLayer` do deck.gl monta o atlas com um conjunto fixo, e o que fica
    fora dele não vira caractere errado: vira **espaço em branco**. "Maués"
    aparecia como "Mau s", e o defeito só se manifesta em nome acentuado — que
    é a maioria dos municípios brasileiros.

    **Lista explícita, e não `"auto"`.** O deck aceita a string `"auto"`, mas
    o pydeck a converte em acessor de dado — vira `@@=auto`, o deck procura um
    campo chamado `auto` em cada linha, não acha, e cai no conjunto padrão. É
    a mesma armadilha que já custou o `size_units="pixels"` virar `@@=pixels`
    e fazer o texto do mapa escalar junto com o zoom.

    **Tupla, e não lista.** O pydeck converte lista em acessor do mesmo jeito
    que converte string: `["a", "é"]` vira `@@=[a, é]`. Tupla ele serializa
    como array JSON, que é o que o deck.gl espera. Testadas as quatro formas.

    Montado a partir do texto que a camada de fato desenha, então o atlas fica
    do tamanho do necessário.
    """
    return tuple(sorted({c for t in textos for c in str(t)}))


@dataclass(frozen=True, slots=True)
class Escala:
    """Classes de uma escala por quantil."""

    cortes: list[float]
    rotulos: list[str]
    cores: dict[str, str]

    @property
    def classes(self) -> int:
        return len(self.rotulos)


def _formatar(valor: float, decimais: int) -> str:
    texto = f"{valor:,.{decimais}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _quebras_naturais(v, classes: int, iteracoes: int = 50) -> list[float]:
    """Cortes que minimizam a variancia dentro de cada classe (Jenks).

    k-medias em uma dimensao, partindo dos quantis e iterando ate estabilizar.
    Deterministico: mesma entrada, mesmos cortes.
    """
    v = np.sort(np.asarray(v, dtype=float))
    centros = np.quantile(v, np.linspace(0, 1, classes + 2)[1:-1])
    for _ in range(iteracoes):
        rotulo = np.abs(v[:, None] - centros[None, :]).argmin(1)
        novos = np.array(
            [
                v[rotulo == i].mean() if (rotulo == i).any() else centros[i]
                for i in range(classes)
            ]
        )
        if np.allclose(novos, centros):
            break
        centros = np.sort(novos)
    meios = [(centros[i] + centros[i + 1]) / 2 for i in range(classes - 1)]
    return sorted(set([float(v[0]), *map(float, meios), float(v[-1])]))


def escala_natural(
    valores: pd.Series, rampa: list[str], classes: int = CLASSES, decimais: int = 1
) -> Escala:
    """Divide os valores em classes por **quebras naturais**.

    Era por quantis, classes de igual frequencia, herdado do painel em R.
    Trocou em 24/ago/2026 porque a incidencia tem cauda longa e o quantil
    comprime justamente o topo, que e onde a vigilancia olha: em Pernambuco,
    **29 municipios dividiam a mesma cor cobrindo de 59 a 445 por 100 mil** --
    Itapissuma e Goiana pintados iguais com seis vezes de diferenca.

    Medido pelo GVF, que e quanto da variancia dos dados a classificacao
    explica -- 1,0 seria perfeito:

    ==========  ========  ==========  ========
    recorte     quantil   naturais    iguais
    ==========  ========  ==========  ========
    Brasil         0,895       0,958     0,962
    PE             0,463       0,964     0,823
    MG             0,791       0,939     0,916
    ==========  ========  ==========  ========

    Intervalos iguais ganham por pouco no Brasil e perdem feio em PE, e ainda
    empilham quase tudo na classe de baixo -- o defeito espelhado. Quebras
    naturais e o unico que vai bem nos tres.

    Custa 2,5 ms em MG, o maior recorte, contra 0,1 do quantil. Cabe no
    orcamento de 300 ms por interacao com folga; ver docs/performance.md.

    Cortes repetidos sao colapsados: quando mais da metade dos municipios tem
    zero caso -- comum em recortes pequenos -- varios cortes caem no mesmo
    numero e produziriam classes vazias.
    """
    limpos = pd.to_numeric(valores, errors="coerce").dropna()
    limpos = limpos[np.isfinite(limpos)]
    if limpos.empty:
        return Escala(cortes=[], rotulos=[], cores={ROTULO_SEM_DADO: SEM_DADO})

    if limpos.nunique() <= classes:
        cortes = sorted(set(limpos.tolist()))
        if len(cortes) > 1:
            cortes = cortes[:1] + [
                (cortes[i] + cortes[i + 1]) / 2 for i in range(len(cortes) - 1)
            ] + cortes[-1:]
    else:
        cortes = _quebras_naturais(limpos.to_numpy(), classes)
    if len(cortes) < 2:
        unico = float(cortes[0])
        rotulo = _formatar(unico, decimais)
        return Escala(
            cortes=[unico, unico],
            rotulos=[rotulo],
            cores={rotulo: rampa[len(rampa) // 2], ROTULO_SEM_DADO: SEM_DADO},
        )

    # A rampa tem 7 tons; com menos classes, pega tons distribuídos nela.
    usadas = len(cortes) - 1
    indices = np.linspace(0, len(rampa) - 1, usadas).round().astype(int)
    tons = [rampa[i] for i in indices]

    rotulos = [
        f"{_formatar(cortes[i], decimais)} a {_formatar(cortes[i + 1], decimais)}"
        for i in range(usadas)
    ]
    # `strict=True` prende a invariante: rótulos e tons saem os dois de
    # `usadas`, e se um dia divergirem, classes sumiriam da legenda sem
    # erro — o mapa continuaria colorido e a legenda incompleta.
    cores = dict(zip(rotulos, tons, strict=True))
    cores[ROTULO_SEM_DADO] = SEM_DADO
    return Escala(cortes=[float(c) for c in cortes], rotulos=rotulos, cores=cores)


#: Como o mapa reparte os valores em classes de cor.
#:
#: As três convivem porque respondem a exigências diferentes, e nenhuma vence
#: nas três ao mesmo tempo:
#:
#: ==========  ==============  ==================  =====================
#: método      ajuste (GVF)    classes iguais?     comparável entre anos?
#: ==========  ==============  ==================  =====================
#: NATURAL          0,842            não                   não
#: QUARTIL          0,239            sim                   não
#: FIXA             varia            não                   **sim**
#: ==========  ==============  ==================  =====================
#:
#: Medido na incidência por bairro de Recife em 2023, 94 bairros.
CLASSIFICACOES = ("NATURAL", "QUARTIL", "FIXA")

ROTULO_CLASSIFICACAO = {
    "NATURAL": "Quebras naturais",
    "QUARTIL": "Quartis",
    "FIXA": "Escala fixa",
}


def _montar(
    cortes: list[float], rampa: list[str], decimais: int, abertas: bool = False
) -> Escala:
    """Monta a `Escala` a partir dos cortes já decididos.

    Extraído de `escala_natural` quando os outros dois métodos entraram: os
    três diferem só em **onde cortar**, e rótulo e cor se montam igual. Deixar
    isso duplicado seria como uma classificação ganhar um rótulo diferente da
    outra sem ninguém decidir.

    ``abertas`` é para a escala fixa: a primeira classe se lê "< 2" e a
    última "≥ 40", como a régua oficial se escreve — "40,0 a 112,8" mistura o
    corte declarado com o máximo observado do ano, que é só o teto do `cut`.
    """
    cortes = [float(c) for c in cortes]
    if len(cortes) < 2:
        unico = cortes[0] if cortes else 0.0
        rotulo = _formatar(unico, decimais)
        return Escala(
            cortes=[unico, unico],
            rotulos=[rotulo],
            cores={rotulo: rampa[len(rampa) // 2], ROTULO_SEM_DADO: SEM_DADO},
        )

    usadas = len(cortes) - 1
    indices = np.linspace(0, len(rampa) - 1, usadas).round().astype(int)
    tons = [rampa[i] for i in indices]
    def faixa(i: int) -> str:
        de, ate = _formatar(cortes[i], decimais), _formatar(cortes[i + 1], decimais)
        if abertas and i == 0:
            return f"< {ate}"
        if abertas and i == usadas - 1:
            return f"≥ {de}"
        return f"{de} a {ate}"

    rotulos = [faixa(i) for i in range(usadas)]
    cores = dict(zip(rotulos, tons, strict=True))
    cores[ROTULO_SEM_DADO] = SEM_DADO
    return Escala(cortes=cortes, rotulos=rotulos, cores=cores)


#: Quantas classes de igual frequência. Cinco, e não quatro: o painel de
#: origem reparte os 185 municípios de PE em **quintis** (37 por classe), e a
#: paridade visual pede a mesma régua. O nome do método continua "QUARTIL"
#: no contrato para não quebrar o RecifeTB, que usa quatro.
QUANTIS = 5


def escala_quartis(
    valores: pd.Series, rampa: list[str], decimais: int = 1, quantis: int = QUANTIS
) -> Escala:
    """Classes de igual **frequência** — a mesma fração das geografias em cada.

    É o que a vigilância costuma pedir por ser fácil de explicar: "este bairro
    está no quarto superior". A conta é o percentil 25, 50 e 75 da própria
    série, com interpolação linear.

    **O custo aparece quando a cauda é longa**, e a de Recife é: em 2023 a
    classe de cima vai de 202 a 3.610, dezessete vezes de diferença numa cor
    só — Boa Viagem e o bairro do Recife ficam indistinguíveis. Medido pelo
    GVF, quanto da variância a classificação explica: 0,239 contra 0,842 das
    quebras naturais.

    Fica disponível porque a escolha é de quem lê o mapa, não de quem o
    escreve — e porque "um quarto dos bairros" é um recorte legítimo mesmo
    quando ajusta mal.
    """
    limpos = pd.to_numeric(valores, errors="coerce").dropna()
    if limpos.empty:
        return _montar([], rampa, decimais)
    cortes = list(np.quantile(limpos.to_numpy(), np.linspace(0.0, 1.0, quantis + 1)))
    # Cortes colapsados viram uma classe só: acontece quando mais de um quarto
    # das geografias tem o mesmo valor, tipicamente zero.
    #
    # **Sem arredondar.** Arredondar para dez casas parecia inofensivo e
    # excluía o mínimo: com o Distrito Sanitário III em 72,2660471147612, o
    # corte inferior virava 72,2660471148 — maior que o próprio valor —, o
    # `pd.cut` devolvia nulo e o distrito saía pintado de "sem dado", branco,
    # justamente o que mais chama atenção num mapa. Os quantis já devolvem
    # floats idênticos quando colapsam, então `dict.fromkeys` basta para
    # deduplicar sem tocar no valor.
    cortes = sorted(dict.fromkeys(float(c) for c in cortes))
    return _montar(cortes, rampa, decimais)


def escala_fixa(
    valores: pd.Series, rampa: list[str], cortes: list[float], decimais: int = 1
) -> Escala:
    """Cortes declarados de fora, iguais em todo ano.

    **É a única das três que torna dois anos comparáveis.** Os outros métodos
    recalculam os limites a partir dos dados do ano, então a régua muda debaixo
    do mapa: medido em Recife, a segunda quebra natural foi 93 em 2021, 105 em
    2022 e 101 em 2023. Um bairro pode escurecer de um ano para o outro tendo
    incidência menor.

    O preço é que os cortes precisam ser **decididos**, e uma decisão ruim
    entrega um mapa de uma cor só. Por isso eles vivem no *disease pack*, com a
    âncora de cada um escrita ao lado — ver `CORTES_FIXOS` em
    `src/doencas/tuberculose.py`.

    A última classe é **aberta**: quando a série passa do teto declarado, o
    máximo entra como corte **a mais**, e não no lugar do último. Substituir
    apagava a âncora de cima — com cortes até 624 e máximo em 3.610, a legenda
    exibia "312 a 3.610" e o 4× Recife desaparecia. Acrescentando, ela exibe
    "312 a 624" e "624 a 3.610", que é o que se quis declarar.
    """
    limpos = pd.to_numeric(valores, errors="coerce").dropna()
    limites = sorted(float(c) for c in cortes)
    # Cortes declarados inteiros se escrevem inteiros: "< 2", não "< 2,0".
    # Os de 0–14 (0,5 · 2,5) continuam com a casa decimal.
    if all(float(c).is_integer() for c in limites):
        decimais = 0
    if limpos.empty or len(limites) < 2:
        return _montar(limites, rampa, decimais, abertas=True)

    teto = float(limpos.max())
    if teto > limites[-1]:
        limites = [*limites, teto]
    piso = float(limpos.min())
    if piso < limites[0]:
        limites = [piso, *limites[1:]]
    return _montar(limites, rampa, decimais, abertas=True)


def escala(
    valores: pd.Series,
    rampa: list[str],
    *,
    metodo: str = "NATURAL",
    cortes_fixos: list[float] | None = None,
    classes: int = CLASSES,
    decimais: int = 1,
) -> Escala:
    """Despacha para o método de classificação pedido.

    ``cortes_fixos`` só é usado por ``FIXA``; sem ele, o método cai em
    ``NATURAL`` em vez de estourar. Mapa sem cor por falta de configuração é
    pior que mapa classificado de outro jeito.
    """
    alvo = str(metodo or "NATURAL").strip().upper()
    if alvo not in CLASSIFICACOES:
        raise ValueError(
            f"Classificação desconhecida: {metodo!r}. Esperado {CLASSIFICACOES}."
        )
    if alvo == "QUARTIL":
        return escala_quartis(valores, rampa, decimais)
    if alvo == "FIXA" and cortes_fixos:
        return escala_fixa(valores, rampa, list(cortes_fixos), decimais)
    return escala_natural(valores, rampa, classes=classes, decimais=decimais)


def classificar(valores: pd.Series, escala: Escala) -> pd.Series:
    """Rótulo da classe de cada valor. Ausente e não-finito viram "sem dado"."""
    numeros = pd.to_numeric(valores, errors="coerce")
    if not escala.rotulos:
        return pd.Series([ROTULO_SEM_DADO] * len(numeros), index=numeros.index)

    # `cut` não inclui o limite inferior da primeira classe; `include_lowest`
    # resolve, e o `duplicates` cobre cortes colapsados.
    faixas = pd.cut(
        numeros,
        bins=escala.cortes,
        labels=escala.rotulos,
        include_lowest=True,
        duplicates="drop",
    )
    return faixas.astype(object).where(faixas.notna(), ROTULO_SEM_DADO)


def _mercator(lat: float) -> float:
    """Latitude em graus de Mercator, na mesma escala da longitude.

    É o que permite comparar a extensão vertical com a horizontal: no
    Mercator um grau de latitude ocupa mais pixels quanto mais longe do
    equador, e o Brasil cobre de -33° a +5°.
    """
    limitada = max(-85.0, min(85.0, float(lat)))
    radianos = np.radians(limitada)
    return float(np.degrees(np.log(np.tan(np.pi / 4 + radianos / 2))))


def _mercator_inverso(y: float) -> float:
    """Volta de graus de Mercator para latitude."""
    radianos = np.radians(float(y))
    return float(np.degrees(2 * np.arctan(np.exp(radianos)) - np.pi / 2))


#: Largura assumida do painel do mapa, em pixels — o **pior caso**, não o
#: comum. A altura é :data:`ALTURA`, e as duas andam juntas.
#:
#: O Streamlit não informa ao servidor a largura da janela, então o zoom é
#: calculado contra um número fixo enquanto a coluna real varia. Medido no
#: navegador, a coluna é `(janela - 106) / 2` — 80px de respiro da página, 16
#: do vão entre as colunas e ~10 da barra de rolagem:
#:
#: ===========  ======
#: janela       coluna
#: ===========  ======
#: 1280            587
#: 1366            630
#: 1536            715
#: 1920            907
#: ===========  ======
#:
#: Errar para cima **corta a geometria**: a 1280 o Acre saía pela borda
#: esquerda. Errar para baixo só deixa margem. Entre um mapa incompleto e um
#: mapa pequeno, o incompleto é pior num painel de vigilância — margem se vê,
#: recorte não.
#:
#: 580 cobre qualquer janela a partir de 1266px, que é o alvo do projeto.
#: Eram 430, o que sobrava depois de a barra lateral de 300px comer a tela;
#: sem ela, a mesma janela de 1280 dá 587.
#:
#: O preço continua sendo margem em telas largas — a 1536 sobram 135px em
#: volta do mapa. Isto move o pior caso, não elimina o problema: a correção de
#: verdade é medir a largura no cliente e devolvê-la ao servidor, ver
#: `docs/deploy.md`.
LARGURA_PAINEL = 580


#: Fração da área total que define o "corpo" da camada. O que sobra são
#: partes minúsculas — ilhas oceânicas, no nosso caso.
COBERTURA_CORPO = 0.999

#: Quantos graus uma parte precisa estar fora do corpo para contar como
#: afastada. 1° são cerca de 110 km: mais que qualquer ilha costeira e muito
#: menos que Fernando de Noronha (4,5°) ou Trindade (5,9°).
FOLGA_AFASTADA = 1.0

#: Onde e de que tamanho fica o quadro da ilha, em fracao do enquadramento.
#:
#: Canto superior direito porque as ilhas brasileiras ficam a leste, e o olho
#: procura no lado de onde elas vieram. A ilha e escalada para ocupar
#: `DESTAQUE_TAMANHO` da largura do quadro principal -- Fernando de Noronha
#: tem 17 km2 contra os 98 mil de Pernambuco, entao em escala real ela e menor
#: que um pixel.
DESTAQUE_TAMANHO = 0.11
DESTAQUE_MARGEM = 0.02

_LIMITES: dict[tuple, tuple] = {}


def limites_uteis(camada) -> tuple[tuple[float, float, float, float], list]:
    """Retângulo de enquadramento ignorando ilhas oceânicas, e quem elas são.

    O ``total_bounds`` cru é dominado por pedaços de terra longe de tudo, e o
    enquadramento é calculado sobre ele — então o território que se quer ver
    encolhe para caber junto com uma ilha de 17 km². Medido:

    ==================  =========  ==========
    camada              cru        útil
    ==================  =========  ==========
    Brasil (27 UFs)     45,1°      39,2°
    PE (185 municípios)  9,0°       6,6°
    MG, SP              iguais     iguais
    ==================  =========  ==========

    No Brasil quem estica são **Trindade e Martim Vaz**, ilhas do Espírito
    Santo a 1.100 km da costa; em PE, **Fernando de Noronha**. O país inteiro
    desenhava 13% menor por causa de duas ilhas onde ninguém mora.

    Devolve também a lista de índices das feições que ficaram **inteiramente**
    fora — só essas somem da tela e precisam de um destaque. Trindade não
    entra na lista: ela é parte do Espírito Santo, que continua visível pelo
    continente.
    """
    import warnings

    import numpy as np

    chave = (len(camada), tuple(round(v, 4) for v in camada.total_bounds))
    if chave in _LIMITES:
        return _LIMITES[chave]

    partes = camada.geometry.explode(index_parts=False)
    # `area` em graus avisa que não é área de verdade, e não precisa ser: só
    # serve para ordenar partes da mesma camada, e a ordem é a mesma em
    # qualquer projeção razoável. Reprojetar 5.571 municípios a cada mapa
    # custaria mais que tudo o que esta função faz.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*geographic CRS.*")
        areas = partes.area.to_numpy()
    ordem = np.argsort(areas)[::-1]
    corte = int(np.searchsorted(np.cumsum(areas[ordem]) / areas.sum(), COBERTURA_CORPO))
    corpo = partes.iloc[ordem[: corte + 1]]

    # O retângulo do corpo serve só para medir distância. Devolver ele seria
    # cortar território: em São Paulo, as ilhas costeiras de Cananéia caem no
    # rabo de 0,1% da área e ficariam de fora por 0,046° — perto demais para
    # serem "afastadas", e ainda assim recortadas. O que vale é o retângulo de
    # tudo **menos** as partes distantes.
    cx0, cy0, cx1, cy1 = (float(v) for v in corpo.total_bounds)
    b = partes.bounds
    distante = (
        (b.minx < cx0 - FOLGA_AFASTADA)
        | (b.maxx > cx1 + FOLGA_AFASTADA)
        | (b.miny < cy0 - FOLGA_AFASTADA)
        | (b.maxy > cy1 + FOLGA_AFASTADA)
    )
    fora = partes.index[distante]
    xmin, ymin, xmax, ymax = (float(v) for v in partes[~distante].total_bounds)
    # Uma feição só some da tela se **nenhuma** parte dela ficou no corpo.
    dentro = set(corpo.index)
    inteiramente_fora = [i for i in dict.fromkeys(fora) if i not in dentro]

    resultado = ((xmin, ymin, xmax, ymax), inteiramente_fora)
    _LIMITES[chave] = resultado
    return resultado


def extensao_visivel(limites, largura=None, altura=None):
    """Retangulo que o painel mostra, que e maior que o dos dados.

    `enquadrar` faz o bounding box caber, e sobra margem no eixo que nao
    limitou. Pernambuco tem 6,6 graus de largura por 1,7 de altura: cabe pela
    largura, e restam quatro graus de ceu e mar acima e abaixo.

    E nessa margem que o quadro da ilha vai, e nao no canto do bounding box --
    ali ele cairia em cima da costa nordeste do proprio estado.
    """
    largura = LARGURA_PAINEL if largura is None else largura
    altura = ALTURA if altura is None else altura

    xmin, ymin, xmax, ymax = limites
    dx = xmax - xmin
    dy = abs(_mercator(ymax) - _mercator(ymin))
    escalas = [largura / dx] if dx > 0 else []
    if dy > 0:
        escalas.append(altura / dy)
    if not escalas:
        return limites
    px_por_grau = min(escalas)

    meia_x = largura / px_por_grau / 2
    meia_y = altura / px_por_grau / 2
    cx = (xmin + xmax) / 2
    cy_merc = (_mercator(ymin) + _mercator(ymax)) / 2
    return (
        cx - meia_x,
        _mercator_inverso(cy_merc - meia_y),
        cx + meia_x,
        _mercator_inverso(cy_merc + meia_y),
    )


#: Quantas vezes o municipio destacado cabe na largura enquadrada.
#:
#: 5 e nao 1: enquadrar so o municipio responde "como ele e por dentro", e a
#: pergunta do destaque e "onde ele fica". Com cinco vezes, os vizinhos
#: aparecem e da para se localizar sem perder o municipio de vista.
FOCO_VIZINHANCA = 5

#: Piso do enquadramento, como fracao do recorte inteiro. Sem ele, um
#: municipio de 8 km2 levaria a um zoom em que nada mais e reconhecivel.
FOCO_MINIMO = 0.28


def enquadrar_foco(limites, alvo):
    """Retangulo em volta de ``alvo``, com vizinhanca e preso dentro de ``limites``.

    Devolve `None` quando nao ha o que focar, e ai o chamador segue com o
    enquadramento do recorte inteiro.
    """
    if alvo is None:
        return None

    ax0, ay0, ax1, ay1 = alvo
    x0, y0, x1, y1 = limites
    largura_recorte, altura_recorte = x1 - x0, y1 - y0

    lado = max(
        (ax1 - ax0) * FOCO_VIZINHANCA,
        (ay1 - ay0) * FOCO_VIZINHANCA,
        largura_recorte * FOCO_MINIMO,
        altura_recorte * FOCO_MINIMO,
    )
    cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    meia = lado / 2

    # Preso dentro do recorte: um municipio na borda puxaria o enquadramento
    # para fora do estado, e sobraria oceano ou territorio vizinho sem dado.
    meia_x = min(meia, largura_recorte / 2)
    meia_y = min(meia, altura_recorte / 2)
    cx = min(max(cx, x0 + meia_x), x1 - meia_x)
    cy = min(max(cy, y0 + meia_y), y1 - meia_y)
    return (cx - meia_x, cy - meia_y, cx + meia_x, cy + meia_y)


def destacar_ilhas(dados, limites, indices):
    """Move ilhas oceanicas para um quadro no canto, fora de escala.

    Devolve o ``dados`` com a geometria das feicoes de ``indices`` substituida
    por uma copia ampliada e reposicionada, mais o retangulo do quadro.

    **Por que mover em vez de abrir uma segunda vista.** O deck.gl desenha
    varias `MapView` no mesmo canvas, e seria o certo, mas o componente do
    Streamlit gerencia o estado da vista por conta propria: le
    ``initialViewState.height`` para dimensionar o grafico e passa um
    controlador unico. Com duas vistas o mapa nao renderiza -- ``deck.gl:
    assertion failed`` em ``_rebuildViewports``. Testado.

    **Por que mover e honesto.** E o recurso classico dos atlas, e so vale
    acompanhado do aviso de que esta fora de escala -- por isso o quadro tem
    borda e rotulo. A alternativa era enquadrar a ilha junto, encolhendo o
    territorio em 37%, ou deixa-la fora da tela, somindo com um municipio que
    tem casos. Num painel de vigilancia, mapa incompleto e pior.

    A feicao movida conserta a geometria e **mantem as propriedades**, entao o
    clique continua entrando no municipio e o tooltip continua certo.
    """
    from shapely import affinity

    xmin, ymin, xmax, ymax = limites
    largura = xmax - xmin
    lado = largura * DESTAQUE_TAMANHO
    margem = largura * DESTAQUE_MARGEM

    quadro = (xmax - margem - lado, ymax - margem - lado, xmax - margem, ymax - margem)
    alvo_x = (quadro[0] + quadro[2]) / 2
    alvo_y = (quadro[1] + quadro[3]) / 2

    dados = dados.copy()
    ilhas = dados.loc[indices]
    ix0, iy0, ix1, iy1 = ilhas.total_bounds
    extensao = max(ix1 - ix0, iy1 - iy0) or 1e-9
    fator = (lado * 0.72) / extensao

    for i in indices:
        g = dados.at[i, "geometry"]
        g = affinity.scale(g, xfact=fator, yfact=fator, origin="center")
        cx, cy = g.centroid.x, g.centroid.y
        dados.at[i, "geometry"] = affinity.translate(g, alvo_x - cx, alvo_y - cy)

    return dados, quadro


def enquadrar(
    limites: tuple[float, float, float, float],
    *,
    largura: int = LARGURA_PAINEL,
    altura: int = ALTURA,
) -> dict:
    """Centro e zoom para o bounding box caber no painel.

    O deck.gl não expõe `fitBounds` no spec JSON, então o zoom é calculado
    aqui. **Considera as duas dimensões do painel**, e não só a maior do
    bounding box: o painel é mais alto que largo, e uma geometria larga e
    baixa — Pernambuco é o caso extremo — desperdiçava metade da altura
    quando o ajuste era feito só pela maior extensão.

    A conta é a do Mercator: no zoom 0 os 360° de longitude ocupam 256px, e
    cada nível dobra. Fica o menor dos dois zooms possíveis, que é o que faz
    a geometria caber inteira.
    """
    xmin, ymin, xmax, ymax = limites

    # O centro vertical é a média em **Mercator**, não em graus. Para o
    # Brasil, que vai de -33,7° a +5,3°, a média aritmética cai 0,8° ao norte
    # do centro real da projeção — o bastante para Roraima e Amapá saírem
    # pela borda de cima depois que o enquadramento passou a ser justo.
    centro = {
        "lat": _mercator_inverso((_mercator(ymin) + _mercator(ymax)) / 2),
        "lon": (xmin + xmax) / 2,
    }

    dx, dy = xmax - xmin, ymax - ymin
    if dx <= 0 and dy <= 0:
        return {"center": centro, "zoom": 9.0}

    # A latitude precisa ir para unidades de Mercator antes de virar escala:
    # o mapa estica conforme se afasta do equador, e o Brasil vai de -33° a
    # +5°. Tratando grau de latitude como grau de longitude, a geometria
    # estouraria a borda de baixo nos recortes mais ao sul.
    dy_merc = abs(_mercator(ymax) - _mercator(ymin))

    escalas = []
    if dx > 0:
        escalas.append(largura / dx)
    if dy_merc > 0:
        escalas.append(altura / dy_merc)
    px_por_grau = min(escalas)

    # A folga é maior do que a conta pediria. O zoom do deck.gl não segue
    # exatamente este modelo de 256px por 360° — medido no navegador, ele
    # desenha cerca de 10% maior que o previsto —, e errar para o lado de
    # cortar a geometria é pior do que errar para o lado da margem.
    # Verificação final é olhar o mapa do Brasil inteiro na tela.
    # 512 e não 256: o deck.gl usa tile de 512px, ao contrário do Leaflet.
    # Com 256 o zoom saía um nível alto demais e o Brasil era cortado no
    # norte e no sul — foi assim que Roraima sumiu da tela.
    zoom = float(np.log2(px_por_grau * 360 / 512) - 0.05)
    return {"center": centro, "zoom": max(2.0, min(zoom, 11.0))}


def _rgb(cor: str) -> list[int]:
    """`#RRGGBB` para `[r, g, b]`, que é como o deck.gl espera."""
    texto = cor.lstrip("#")
    return [int(texto[i : i + 2], 16) for i in (0, 2, 4)]


#: Casas decimais mantidas nas coordenadas enviadas ao navegador.
#:
#: A malha traz seis, o que é 11 cm de precisão. O mapa é desenhado em cerca de
#: 430px cobrindo um estado inteiro — em Minas, um pixel vale perto de 2 km. As
#: cinco casas restantes são exatidão que nunca chega à tela e que o payload
#: paga por inteiro: em MG são 0,62 MB, e arredondar tira 14%.
#:
#: Cinco casas, e não quatro: são 1,1 m, com folga para o modo detalhe, que
#: enquadra um único município. Quatro dariam 11 m, e ali isso já se aproxima
#: de um pixel.
CASAS_COORDENADA = 5


def _arredondar(o):
    """Arredonda recursivamente as coordenadas de uma geometria GeoJSON."""
    if isinstance(o, float):
        return round(o, CASAS_COORDENADA)
    if isinstance(o, (list, tuple)):
        return [_arredondar(x) for x in o]
    if isinstance(o, dict):
        return {k: _arredondar(v) for k, v in o.items()}
    return o


def geometrias_geojson(camada) -> list:
    """Geometrias da camada em GeoJSON, sem as propriedades.

    Converter a malha custa 75 ms em Minas Gerais e é o item mais caro de
    montar o mapa — mais que todas as leituras de dado somadas. O resultado é
    idêntico entre renderizações: a geometria não muda quando o usuário troca
    de métrica ou de ano, só as cores mudam.

    Fica separado de :func:`deck` para o chamador poder memoizar. **Só a
    geometria** — propriedade carrega cor e valor, que mudam a cada interação,
    e guardar junto serviria mapa velho.

    As coordenadas são arredondadas a :data:`CASAS_COORDENADA`. A malha vem com
    seis casas, precisão de 11 centímetros, num mapa onde um pixel vale
    quilômetros — é peso que atravessa a rede sem chegar aos olhos de ninguém.
    """
    bruto = [f["geometry"] for f in camada[["geometry"]].__geo_interface__["features"]]
    return [_arredondar(g) for g in bruto]


def _compactar(mapa_deck) -> None:
    """Faz o deck serializar sem indentação.

    O `pydeck.serialize` chama ``json.dumps(..., indent=2)``, e o
    ``st.pydeck_chart`` envia ao navegador exatamente o que ``to_json()``
    devolver. Com a geometria aninhada em listas de coordenadas, essa
    indentação é a maior parte do que trafega: em Minas Gerais, com 853
    municípios, são 2,76 MB dos quais 2,0 MB são espaço em branco.

    E não é custo só da primeira carga — as cores fazem parte do mesmo spec,
    então o mosaico inteiro volta pela rede a cada navegação e a cada troca
    de métrica.

    Substituir o método na instância é feio, mas é o único ponto de entrada:
    o Streamlit não expõe opção de serialização e o `pydeck` não parametriza
    o `indent`. Se a API interna do pydeck mudar, o `except` devolve o
    comportamento padrão — payload grande, nunca página quebrada.
    """
    try:
        import json

        from pydeck.bindings.json_tools import default_serialize

        compacto = json.dumps(
            mapa_deck,
            sort_keys=True,
            default=default_serialize,
            separators=(",", ":"),
        )
    # Captura ampla de propósito: otimização não pode derrubar o mapa. E
    # `Exception`, nunca `BaseException` — `RerunException` herda desta
    # última justamente para atravessar blocos como este.
    except Exception:
        return

    mapa_deck.to_json = lambda: compacto


def _camada_rotulos(pydeck, dados):
    """Valor impresso sobre cada polígono, como no boletim do Ministério.

    O tooltip cobre a leitura interativa, mas some em toque e não sobrevive a
    uma captura de tela — que é como painel de vigilância circula em reunião e
    em relatório. O boletim do MS imprime o número em cada UF justamente por
    isso.

    Três decisões que não são óbvias:

    - **`representative_point`, não `centroid`.** O centroide de um polígono
      côncavo cai fora dele; o Amapá e o Maranhão põem o rótulo no vizinho.
      `representative_point` garante um ponto interno.
    - **`pickable=False`.** Sem isso a camada de texto intercepta o clique e
      mata o drill-down bem no meio de cada estado, que é onde as pessoas
      clicam.
    - **Placa branca sob o texto**, em vez de contorno. A rampa vai de laranja
      claro a marrom, e texto escuro sem placa some no topo da escala
      enquanto texto claro some na base.

    Sem rótulo para quem não tem dado: "—" sobre o mapa é ruído, e a ausência
    já é comunicada pela cor neutra e pela legenda.

    **Rótulo que colide não é exibido.** Na primeira versão todos entravam, e
    no Brasil isso produzia `13,914,8` — dois números encavalados lendo como
    um só — mais sete rótulos empilhados no Nordeste. O deck.gl não faz
    *declutter*, então é feito aqui: os polígonos entram do maior para o
    menor, cada um reserva a área do seu rótulo, e quem cair sobre área já
    reservada fica de fora.

    A ordem por área é o que decide bem o desempate: o rótulo sobrevive onde
    há espaço para lê-lo. O valor de quem ficou de fora continua no tooltip.

    Cortar por limiar de área seria mais simples e pior — derrubaria o Rio de
    Janeiro, que é pequeno no mapa e dos mais relevantes na doença, mesmo
    quando ninguém disputa aquele espaço.
    """
    com_valor = dados[dados["valor"].notna()]
    if com_valor.empty:
        return None

    minx, miny, maxx, maxy = dados.total_bounds
    largura, altura = (maxx - minx) or 1.0, (maxy - miny) or 1.0

    # Área que um rótulo ocupa, em fração da extensão do mapa — a placa branca
    # conta, não só o texto. Calibrado contra a geometria real do Brasil: com
    # 0,045 x 0,022 nenhum par era detectado (Alagoas e Sergipe distam 1,0° na
    # vertical e a caixa tinha 0,86°), e todos os 27 continuavam colidindo na
    # tela. Com os valores abaixo ficam 23, e saem AL, PB, RN e DF — que é
    # exatamente o aglomerado ilegível. Rio de Janeiro, Sergipe e Piauí são
    # pequenos mas sobrevivem, porque ninguém disputa o espaço deles.
    meia_larg = largura * 0.070 / 2
    meia_alt = altura * 0.034 / 2

    # Tudo de uma vez, e não um `representative_point()` por iteração: em
    # polígono de UF a operação é cara, e chamada 27 vezes dentro do laço ela
    # sozinha levava o tempo de montar o mapa do Brasil de 203 ms para 528 ms
    # — mais que o mapa de Minas Gerais inteiro, com 853 municípios.
    pontos = com_valor.geometry.representative_point()
    # Ordena por área do bounding box calculada dos próprios limites, e não
    # por `.area` da geometria: em CRS geográfico o geopandas emite um aviso a
    # cada chamada ("results are likely incorrect"), e o mapa é redesenhado a
    # cada interação — o log de produção viraria só isso. Aqui a área serve só
    # para desempatar quem fica com o rótulo, então grau ao quadrado basta.
    lim = com_valor.geometry.bounds
    ordem = (
        ((lim["maxx"] - lim["minx"]) * (lim["maxy"] - lim["miny"]))
        .sort_values(ascending=False)
        .index
    )

    fonte: list[dict] = []
    ocupados: list[tuple[float, float, float, float]] = []
    for idx in ordem:
        ponto = pontos.loc[idx]
        x, y = float(ponto.x), float(ponto.y)
        caixa = (x - meia_larg, y - meia_alt, x + meia_larg, y + meia_alt)
        if any(
            caixa[0] < ox2 and caixa[2] > ox1 and caixa[1] < oy2 and caixa[3] > oy1
            for ox1, oy1, ox2, oy2 in ocupados
        ):
            continue
        ocupados.append(caixa)
        fonte.append({"posicao": [x, y], "texto": com_valor["exibicao"].loc[idx]})

    return pydeck.Layer(
        "TextLayer",
        character_set=_caracteres(d["texto"] for d in fonte),
        data=fonte,
        get_position="posicao",
        get_text="texto",
        # Nada de `size_units="pixels"`: o pydeck converte string solta em
        # acessor de dados (`@@=pixels`), o deck.gl recebe unidade inválida e
        # o texto passa a escalar com o zoom, virando garrafal. O default do
        # deck.gl já é pixels. Quando um literal for mesmo necessário, ele vai
        # entre aspas internas — como em `get_text_anchor` abaixo.
        get_size=11,
        get_color=[17, 24, 39],
        background=True,
        get_background_color=[255, 255, 255, 225],
        background_padding=[3, 1, 3, 1],
        get_text_anchor="'middle'",
        get_alignment_baseline="'center'",
        pickable=False,
    )


#: Estilo MapLibre sem fontes nem camadas: tela em branco atrás dos polígonos.
#:
#: Como URL `data:` e não como dict: o Streamlit faz `mapStyle.indexOf(...)`
#: no navegador e quebra com objeto. O MapLibre busca a URL como qualquer
#: outra, e o navegador resolve `data:` sem ir à rede.
ESTILO_SEM_FUNDO = 'data:application/json,{"version":8,"sources":{},"layers":[]}'


def deck(
    camada,
    valores: pd.Series,
    *,
    chave: str,
    rampa: list[str],
    rotulo_metrica: str,
    coluna_nome: str = "bairro_nome",
    decimais: int = 1,
    altura: int = ALTURA,
    geometrias: list | None = None,
    rotulos_valor: bool = False,
    destacado: str | None = None,
    metodo: str = "NATURAL",
    cortes_fixos: list[float] | None = None,
    detalhes: list[tuple[str, pd.Series, str, int]] | None = None,
):
    """Mapa em pydeck, para o drill-down por clique.

    ``detalhes`` é a lista de linhas extras do tooltip, no formato do painel
    de origem — ``(rótulo, série indexada pela chave, cor, decimais)``. O
    título e a métrica pintada vêm sempre; estas são os componentes que
    dão contexto ao número (casos, curas, população).

    O coroplético do Plotly não emite evento de clique — ver
    docs/mapa-clique.md. O ``GeoJsonLayer`` do deck.gl faz *picking* por GPU,
    que é o caminho que sobrou.

    Devolve ``(deck, escala)``: a escala sai junto porque o deck.gl não desenha
    legenda, e ela é montada em HTML por :func:`legenda`.
    """
    import pydeck

    colunas = list(dict.fromkeys([chave, coluna_nome if coluna_nome in camada else chave]))
    dados = camada[[*colunas, "geometry"]].copy()
    dados["valor"] = dados[chave].map(valores)

    escala_ = escala(
        dados["valor"],
        rampa,
        metodo=metodo,
        cortes_fixos=cortes_fixos,
        decimais=decimais,
    )
    dados["classe"] = classificar(dados["valor"], escala_)
    dados["cor"] = dados["classe"].map(
        lambda c: _rgb(escala_.cores.get(c, SEM_DADO))
    )
    dados["exibicao"] = dados["valor"].map(
        lambda v: "—" if pd.isna(v) else _formatar(float(v), decimais)
    )
    dados["rotulo"] = dados[colunas[-1]].astype(str)
    # O deck escapa HTML vindo das propriedades, então cada linha extra do
    # tooltip entra como **valor** já formatado (`d0`, `d1`, …) e rótulo e
    # cor — iguais para todas as feições — ficam no template.
    for i, (_, serie, _, casas) in enumerate(detalhes or []):
        dados[f"d{i}"] = dados[chave].astype(str).map(
            lambda k, serie=serie, casas=casas: (
                "—" if serie.get(k) is None or pd.isna(serie.get(k))
                else _formatar(float(serie.get(k)), casas)
            )
        )

    limites, ilhas = limites_uteis(camada)

    # Destaque tambem aproxima. Sem isso, um municipio pequeno acende como um
    # contorno de tres pixels no meio do estado e a pergunta "onde fica"
    # continua sem resposta.
    #
    # A ilha e a excecao: ela ja aparece ampliada no quadro do canto, e
    # aproximar nela levaria o enquadramento para o oceano.
    foco = None
    if destacado is not None and destacado not in {str(i) for i in ilhas}:
        alvo = dados[dados[chave].astype(str) == str(destacado)]
        if not alvo.empty and str(destacado) not in {
            str(camada.loc[i, chave]) for i in ilhas
        }:
            foco = enquadrar_foco(limites, tuple(alvo.total_bounds))

    quadro = enquadrar(foco or limites)

    # A ilha vai para o canto **antes** de virar GeoJSON, para que o clique,
    # o tooltip e a cor sigam a feicao movida sem tratamento especial.
    #
    # Isto invalida a geometria memoizada pelo chamador, que foi feita a
    # partir da camada crua -- por isso o caminho rapido e desligado quando
    # ha ilha. Custa uma conversao a mais so nas UFs que tem uma, hoje so PE.
    moldura = None
    if ilhas:
        dados, moldura = destacar_ilhas(
            dados, extensao_visivel(foco or limites, altura=altura), ilhas
        )
        geometrias = None

    # As geometrias chegam prontas quando o chamador as memoizou; as
    # propriedades são sempre montadas do zero, porque carregam a cor.
    if geometrias is not None and len(geometrias) == len(dados):
        propriedades = dados.drop(columns="geometry").to_dict("records")
        colecao = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": g, "properties": p}
                for g, p in zip(geometrias, propriedades, strict=True)
            ],
        }
    else:
        # Arredonda aqui também, para os dois caminhos desenharem a mesma
        # geometria — `tests/test_mapa.py` prende isso.
        #
        # **Só a geometria.** Arredondar a coleção inteira alcançaria também o
        # `valor` das propriedades, que alimenta o tooltip: 39,100684 virava
        # 39,10068 num caminho e não no outro.
        colecao = dados.__geo_interface__
        for feicao in colecao["features"]:
            feicao["geometry"] = _arredondar(feicao["geometry"])

    camada_geo = pydeck.Layer(
        "GeoJsonLayer",
        data=colecao,
        get_fill_color="properties.cor",
        get_line_color=[255, 255, 255, 150],
        line_width_min_pixels=0.6,
        stroked=True,
        filled=True,
        # `pickable` é o que faz o clique existir; `auto_highlight` dá o
        # retorno visual que o hover do Plotly dava de graça.
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
    )

    camadas = [camada_geo]

    if moldura is not None:
        x0, y0, x1, y1 = moldura
        camadas.append(
            pydeck.Layer(
                "PolygonLayer",
                data=[{"poligono": [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]}],
                get_polygon="poligono",
                filled=False,
                stroked=True,
                get_line_color=[120, 120, 120, 170],
                line_width_min_pixels=1,
                # A moldura nao pode roubar o clique da ilha que ela emoldura.
                pickable=False,
            )
        )
        nomes = ", ".join(str(n) for n in dados.loc[ilhas, colunas[-1]])
        camadas.append(
            pydeck.Layer(
                "TextLayer",
                character_set=_caracteres([f"{nomes} (fora de escala)"]),
                data=[{"posicao": [(x0 + x1) / 2, y0], "texto": f"{nomes} (fora de escala)"}],
                get_position="posicao",
                get_text="texto",
                get_size=10,
                get_color=[110, 110, 110, 230],
                get_alignment_baseline="'top'",
                get_text_anchor="'middle'",
                pickable=False,
            )
        )

    if rotulos_valor:
        rotulos = _camada_rotulos(pydeck, dados)
        if rotulos is not None:
            camadas.append(rotulos)

    if destacado is not None:
        camadas += _camadas_destaque(pydeck, dados, chave, destacado, colunas[-1])

    mapa_deck = pydeck.Deck(
        layers=camadas,
        initial_view_state=pydeck.ViewState(
            latitude=quadro["center"]["lat"],
            longitude=quadro["center"]["lon"],
            zoom=quadro["zoom"],
            bearing=0,
            pitch=0,
            height=altura,
            # Sem `transition_duration` nem `FlyToInterpolator`: o pydeck
            # emite os dois, e eles não fazem nada aqui. Medido no navegador —
            # o Streamlit **recria o contêiner e o canvas do deck a cada
            # rerun**, inclusive quando a `key` do widget não muda. Sem
            # instância anterior não há câmera de onde partir, e
            # `initialViewState` é sempre inicial de fato.
        ),
        map_provider=None,
        # **Sem mapa de fundo**, como no painel de origem. `map_style=None`
        # não basta: o Streamlit faz `mapStyle ||= <Carto positron/dark>` no
        # navegador e desenha um basemap com rótulos de estados vizinhos em
        # volta de PE. Um estilo MapLibre vazio é "verdadeiro" para esse
        # `||=` e não desenha nada — é o único jeito de dizer "nenhum". Entra
        # depois do construtor, abaixo: o pydeck só aceita dict de estilo com
        # `map_provider="mapbox"`, que puxaria o Mapbox de volta.
        map_style=None,
        # Formato do painel de origem: título, a métrica pintada em destaque
        # e, abaixo, os componentes com a bolinha na cor de cada métrica.
        tooltip={
            "html": (
                "<div style='font-weight:700;font-size:13px'>{rotulo}</div>"
                f"<div style='opacity:.85;margin-bottom:4px'>{rotulo_metrica}: "
                "<b>{exibicao}</b></div>" + _template_detalhes(detalhes or [])
            ),
            "style": {
                "backgroundColor": "rgba(17,24,39,.96)",
                "color": "#fff",
                "fontSize": "12px",
                "borderRadius": "10px",
                "padding": "8px 10px",
                "lineHeight": "1.5",
            },
        },
    )

    mapa_deck.map_style = ESTILO_SEM_FUNDO
    _compactar(mapa_deck)

    # O zoom pela roda do mouse é bloqueado no DOM, por
    # `componentes.script_travar_zoom`. Declarar `controller: false` aqui não
    # adianta: o `DeckGlJsonChart` do Streamlit renderiza
    # `<DeckGL controller={true}>` fixo e descarta o que vem no JSON. Havia
    # duas declarações inertes neste ponto — saíram, porque código que não faz
    # nada mas parece fazer engana quem for mexer depois.

    return mapa_deck, escala_


#: Espessura das duas linhas do destaque, em pixels. A de baixo e branca e
#: mais larga, a de cima e escura -- o par funciona sobre qualquer tom da
#: rampa, que vai de creme a quase preto. Uma linha so sumiria numa ponta ou
#: na outra.
DESTAQUE_HALO = 5
DESTAQUE_TRACO = 2


def _camadas_destaque(pydeck, dados, chave, destacado, coluna_nome):
    """Contorno e nome do municipio apontado pelo clique na barra.

    Nao pinta o interior: a cor da feicao e o dado, e sobrepor tinta ali
    esconderia justamente o que o mapa esta dizendo. O destaque e um contorno
    e um nome, e nada mais.
    """
    alvo = dados[dados[chave].astype(str) == str(destacado)]
    if alvo.empty:
        return []

    colecao = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": _arredondar(f["geometry"]), "properties": {}}
            for f in alvo.__geo_interface__["features"]
        ],
    }

    def contorno(cor, largura):
        return pydeck.Layer(
            "GeoJsonLayer",
            data=colecao,
            filled=False,
            stroked=True,
            get_line_color=cor,
            line_width_min_pixels=largura,
            # Nao pode roubar o clique de quem esta embaixo, que e a propria
            # feicao destacada -- o mapa continua servindo para entrar nela.
            pickable=False,
        )

    camadas = [
        contorno([255, 255, 255, 235], DESTAQUE_HALO),
        contorno([17, 24, 39, 245], DESTAQUE_TRACO),
    ]

    # A etiqueta traz nome **e** valor, e nao so o nome.
    #
    # O contorno ja diz onde; o que falta e quanto, que e a pergunta do painel.
    # Sem o valor, quem destaca um municipio tem de procurar a barra dele no
    # ranking para saber o numero -- ida e volta que a etiqueta resolve.
    #
    # `font_weight` saiu: a camada de rotulos de valor, que funciona ha
    # semanas, nao usa, e a diferenca entre as duas era essa mais o
    # alinhamento. Nao vale carregar uma propriedade a mais numa camada que
    # precisa ser legivel acima de tudo.
    centro = alvo.geometry.iloc[0].centroid
    nome = str(alvo.iloc[0][coluna_nome])
    exibicao = alvo.iloc[0].get("exibicao")
    texto = f"{nome}  {exibicao}" if exibicao not in (None, "", "\u2014") else nome
    camadas.append(
        pydeck.Layer(
            "TextLayer",
            character_set=_caracteres([texto]),
            data=[{"posicao": [centro.x, centro.y], "texto": texto}],
            get_position="posicao",
            get_text="texto",
            # 14 contra os 11 dos rotulos de valor: a etiqueta e uma so na
            # tela, entao pode ser maior sem virar poluicao, e ela precisa se
            # destacar do proprio mapa que esta anotando.
            get_size=14,
            get_color=[17, 24, 39, 255],
            get_text_anchor="'middle'",
            get_alignment_baseline="'center'",
            get_pixel_offset=[0, -22],
            background=True,
            get_background_color=[255, 255, 255, 235],
            background_padding=[6, 3, 6, 3],
            get_border_color=[17, 24, 39, 180],
            get_border_width=1,
            pickable=False,
        )
    )
    return camadas


def _template_detalhes(detalhes) -> str:
    """Trecho do template do tooltip com as linhas extras.

    Cada linha é ``● rótulo  {dN}``, com a bolinha na cor da métrica, como
    no painel de origem. Só o valor é interpolado pelo deck; rótulo e cor
    são estáticos porque são os mesmos para toda feição.
    """
    from html import escape

    return "".join(
        f"<div style='display:flex;justify-content:space-between;gap:14px'>"
        f"<span><i style='display:inline-block;width:8px;height:8px;"
        f"border-radius:50%;background:{cor};margin-right:6px'></i>"
        f"{escape(rotulo)}</span><b>{{d{i}}}</b></div>"
        for i, (rotulo, _, cor, _) in enumerate(detalhes)
    )


def legenda(
    escala: Escala,
    titulo: str,
    contagem: pd.Series | None = None,
    nomes: tuple[str, ...] | None = None,
) -> str:
    """Legenda em HTML — o deck.gl não desenha uma.

    ``contagem`` (rótulo → n) põe ao lado de cada faixa quantas unidades
    caem nela — substitui a tabela "regiões por classe" do painel de origem,
    que repetia as faixas da legenda só para acrescentar o N. ``nomes`` dá
    a cada classe o nome que a régua oficial usa ("baixa", "hiperendêmica"),
    quando a escala é fixa e tem nome.
    """
    from html import escape

    def texto(i: int, r: str) -> str:
        partes = [escape(r)]
        if nomes and i < len(nomes):
            partes.append(f"<em>{escape(nomes[i])}</em>")
        if contagem is not None:
            partes.append(f"<b>{int(contagem.get(r, 0))}</b>")
        return " &nbsp;".join(partes)

    rotulos = [*escala.rotulos, ROTULO_SEM_DADO]
    itens = "".join(
        f'<span class="mapa-legenda-item">'
        f'<i style="background:{escape(escala.cores[r])}"></i>{texto(i, r)}</span>'
        for i, r in enumerate(rotulos)
        if r in escala.cores
        # "sem dado" só aparece quando há alguém sem dado.
        and (r != ROTULO_SEM_DADO or contagem is None or contagem.get(r, 0))
    )
    return (
        f'<div class="mapa-legenda">'
        f'<div class="mapa-legenda-titulo">{escape(titulo)}</div>{itens}</div>'
    )


def alvo_do_clique(evento) -> str | None:
    """Chave da geografia clicada no ``st.pydeck_chart``.

    O evento traz os objetos selecionados por camada; cada objeto é a feição
    GeoJSON, então a chave está em ``properties``.
    """
    if not evento:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if not isinstance(selecao, dict):
        return None

    objetos = selecao.get("objects") or {}
    for lista in objetos.values():
        if not lista:
            continue
        props = lista[0].get("properties") if isinstance(lista[0], dict) else None
        if isinstance(props, dict):
            # As chaves das camadas de PE: município, macro/região de saúde
            # (`regiao`) e UF. `cod_mun6` primeiro, porque a feição de
            # município pode carregar a região junto.
            for campo in ("cod_mun6", "regiao", "uf"):
                if props.get(campo):
                    return str(props[campo])
    return None
