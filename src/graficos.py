"""Gráficos do painel direito.

Altair, e não ECharts como no original: `st.altair_chart` tem evento de clique
nativo — verificado com clique real antes da escolha, não só pela assinatura —
e já vem com o Streamlit, sem componente de terceiros. O ranking precisa desse
evento para navegar o mapa ao clicar numa barra.

A configuração visual vive em :func:`tema` e é aplicada a todo gráfico, para a
linguagem não divergir entre eles como divergia no original.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from .theme import tokens

def _px(token: str) -> int:
    """`"12px"` para `12`. O Altair quer número, o CSS quer unidade."""
    return int(token.rstrip("px"))


#: Altura padrão dos gráficos do painel direito.
ALTURA = 300

#: Faixa vertical por barra do ranking, na **área de plotagem**.
#:
#: Medido no navegador: a caixa do rótulo tem 16px de altura com a fonte de
#: 12px, e o Vega esconde um nome sim outro não assim que o passo entre eles
#: fica abaixo disso. Com 27 UFs em 512px de área útil o passo caía para
#: 15,3px — colidia por menos de um pixel, e metade dos nomes sumia.
#:
#: 22 deixa 6px de folga sobre a caixa, o bastante para a variação de métrica
#: de fonte entre navegadores.
ALTURA_BARRA_RANKING = 22

#: Altura que o eixo x, seu título e as margens comem antes de sobrar espaço
#: para as barras. Medido no navegador: 594px de gráfico davam 512px de área
#: de plotagem.
#:
#: Entra na conta porque a primeira tentativa de conserto reservou 22px por
#: barra sobre a altura **total** e continuou escondendo nomes — as faixas
#: recebiam 19px, não 22.
ALTURA_EIXO_RANKING = 82

#: Piso do ranking, para uma lista de 5 não virar uma tira.
ALTURA_MIN_RANKING = 180

#: Espaço para o nome no eixo do ranking, em pixels.
#:
#: **O critério não é estética, é identificação.** Cortado curto demais, dois
#: municípios diferentes da mesma UF viram o mesmo texto, e o ranking deixa de
#: dizer de quem é a barra. Medido sobre os 5.571 nomes, com a largura de
#: :data:`PX_POR_CARACTERE`:
#:
#: ====== ======== =========
#: limite cortados ambíguos
#: ====== ======== =========
#: 98         891        49
#: 120        429         4
#: **150**     23         0
#: 175          2         0
#: ====== ======== =========
#:
#: 98 era o que o Vega dava sozinho, e ali "São Domingos do Maranhão" e "São
#: Domingos do Azeitão" apareciam idênticos. 150 é o **menor** valor onde
#: nenhum par colide; os 23 que ainda cortam continuam únicos, e o nome
#: inteiro está no tooltip. Subir para 175 salvaria dois nomes e custaria 25px
#: de barra a todo mundo.
LARGURA_ROTULO_RANKING = 150

#: Largura média de um caractere do rótulo, medida no navegador com a fonte de
#: 12px do tema: "José Gonçalves de Minas" ocupa 132px em 23 caracteres.
#:
#: Serve para o teste conferir a propriedade de identificação sem abrir um
#: navegador. É aproximação — nome cheio de "i" ocupa menos que um de "m" —,
#: mas o erro é da ordem de um caractere e a margem entre 150 e o primeiro
#: valor que colide (120) é de seis.
PX_POR_CARACTERE = 5.74

#: Tooltip escuro do original: fundo quase preto, cantos arredondados.
TOOLTIP_FUNDO = "#111827"


def tema(grafico: alt.Chart, *, altura: int = ALTURA) -> alt.Chart:
    """Aplica a linguagem visual do projeto.

    Sem eixo de cor de fundo e sem grade vertical: o painel já tem superfície
    própria, e a grade horizontal basta para ler valor.
    """
    return (
        grafico.properties(height=altura)
        .configure_view(strokeWidth=0, fill=None)
        .configure_axis(
            labelFont=tokens.FONTE,
            titleFont=tokens.FONTE,
            labelFontSize=_px(tokens.TEXTO_XS),
            titleFontSize=_px(tokens.TEXTO_XS),
            titleFontWeight="normal",
            labelColor="currentColor",
            titleColor="currentColor",
            domainColor="rgba(128,128,128,.35)",
            tickColor="rgba(128,128,128,.35)",
            gridColor="rgba(128,128,128,.18)",
        )
        .configure_axisX(grid=False)
        .configure_legend(
            labelFont=tokens.FONTE,
            titleFont=tokens.FONTE,
            labelFontSize=_px(tokens.TEXTO_XS),
            titleFontSize=_px(tokens.TEXTO_XS),
            labelColor="currentColor",
            titleColor="currentColor",
            orient="top",
            direction="horizontal",
            title=None,
        )
        .configure_title(font=tokens.FONTE, fontSize=13, color="currentColor")
    )


def sem_dado(mensagem: str) -> alt.Chart:
    """Gráfico vazio com um recado, no lugar de um painel em branco."""
    return (
        alt.Chart(pd.DataFrame({"t": [mensagem]}))
        .mark_text(font=tokens.FONTE, fontSize=13, opacity=0.55, color="gray")
        .encode(text="t:N")
        .properties(height=ALTURA)
    )


def evolucao_mensal(dados: pd.DataFrame, *, rotulo: str, cor: str, altura: int = ALTURA) -> alt.Chart:
    """Casos por mês do ano selecionado."""
    if dados.empty:
        return sem_dado("Sem série mensal para este recorte")

    base = dados.assign(mes_rotulo=dados["mes_nome"].str.slice(0, 3).str.capitalize())
    return tema(
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=cor)
        .encode(
            x=alt.X("mes_rotulo:N", sort=list(base["mes_rotulo"]), title=None),
            y=alt.Y("valor:Q", title=rotulo),
            tooltip=[
                alt.Tooltip("mes_nome:N", title="Mês"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.0f"),
            ],
        ),
        altura=altura,
    )


def evolucao_anual(dados: pd.DataFrame, *, rotulo: str, cor: str, altura: int = ALTURA, ano: int) -> alt.Chart:
    """Série histórica anual, com o ano selecionado destacado."""
    if dados.empty:
        return sem_dado("Sem série histórica para este recorte")

    base = dados.assign(atual=dados["ano"] == ano)
    return tema(
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("ano:O", title=None),
            y=alt.Y("valor:Q", title=rotulo),
            # O ano selecionado fica opaco e os demais recuam: mantém o
            # contexto histórico sem competir com o recorte ativo.
            color=alt.value(cor),
            opacity=alt.condition(alt.datum.atual, alt.value(1.0), alt.value(0.45)),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.0f"),
            ],
        ),
        altura=altura,
    )


def ranking(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    selecao: alt.Parameter,
    altura_minima: int = 0,
    escala=None,
) -> alt.Chart:
    """Barras horizontais das maiores geografias, clicáveis.

    Horizontal e não vertical: nome de município não cabe num eixo x sem
    rotacionar, e rótulo rotacionado é mais difícil de ler que uma barra a
    mais de altura.

    ``altura_minima`` é **piso, não teto**. Serve para o ranking dividir a
    linha com o mapa, que tem altura fixa: sem ela a coluna da direita termina
    antes e sobra um vão. Cada barra recebe :data:`ALTURA_BARRA_RANKING`, e o
    painel cresce quando a lista pede mais que o piso.

    Já foi sobrescrita, e era um teto disfarçado: com 484px fixos e 25
    municípios, cada faixa ficava com 19px e o Vega passava a esconder um
    rótulo sim, outro não — metade dos nomes sumia sem nenhum aviso. É uma
    forma de degradação silenciosa: o gráfico continua bonito e responde a
    perguntas erradas, porque a barra que se lê não é a que se pensa estar
    lendo.

    ``escala`` é a do mapa ao lado. Passando-a, cada barra recebe a cor do
    polígono correspondente, e os dois painéis viram uma leitura só: o
    Amazonas é o tom mais escuro nos dois lugares. Sem ela, todas as barras
    saem na cor da métrica — que é o que havia antes, e fazia o ranking
    parecer desligado do mapa.

    A cor é redundante com o comprimento, de propósito: não acrescenta
    informação, acrescenta **ligação**. Por isso a legenda fica desligada —
    a do mapa, logo abaixo, já explica as faixas e vale para os dois.
    """
    if dados.empty:
        return sem_dado("Sem dados para ranquear neste recorte")

    if escala is None:
        cor_da_barra = alt.value(cor)
    else:
        # Importado aqui e nao no topo: `graficos` nao depende de `mapa` em
        # nenhum outro ponto, e subir esse acoplamento para o modulo inteiro
        # por causa de uma funcao seria pagar caro por pouco.
        from . import mapa

        dados = dados.assign(classe=mapa.classificar(dados["valor"], escala))
        cor_da_barra = alt.Color(
            "classe:N",
            scale=alt.Scale(
                domain=list(escala.cores),
                range=list(escala.cores.values()),
            ),
            legend=None,
        )

    return tema(
        alt.Chart(dados)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            y=alt.Y(
                "nome:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=LARGURA_ROTULO_RANKING),
            ),
            x=alt.X("valor:Q", title=rotulo),
            color=cor_da_barra,
            # O item sob o cursor destaca; os demais recuam. Dá retorno de
            # que a barra é clicável sem precisar de instrução escrita.
            opacity=alt.condition(selecao, alt.value(1.0), alt.value(0.55)),
            tooltip=[
                alt.Tooltip("nome:N", title="Local"),
                alt.Tooltip("valor:Q", title=rotulo, format=",.1f"),
            ],
        )
        .add_params(selecao),
        altura=max(
            altura_minima,
            ALTURA_MIN_RANKING,
            ALTURA_BARRA_RANKING * len(dados) + ALTURA_EIXO_RANKING,
        ),
    )


def alvo_do_clique(evento, nome_selecao: str = "barra") -> str | None:
    """Chave da barra clicada no ``st.altair_chart``.

    Tolerante ao formato, pelo mesmo motivo do mapa: o payload é detalhe
    interno do Streamlit e já mudou entre versões. Vindo algo inesperado, o
    gráfico apenas não navega, em vez de derrubar a página.
    """
    if not evento:
        return None

    selecao = getattr(evento, "selection", None)
    if selecao is None and isinstance(evento, dict):
        selecao = evento.get("selection")
    if not isinstance(selecao, dict):
        return None

    itens = selecao.get(nome_selecao)
    if not itens:
        return None

    primeiro = itens[0]
    if not isinstance(primeiro, dict):
        return None
    valor = primeiro.get("chave")
    return str(valor) if valor not in (None, "") else None


#: Cores dos dois lados da pirâmide. Deliberadamente não é rosa e azul: a
#: convenção de gênero por cor é ruído num gráfico epidemiológico, e o azul
#: já está tomado pela métrica de mortalidade.
COR_HOMENS = "#1C5D99"
COR_MULHERES = "#B8860B"


def piramide(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    por_100mil: bool = False,
    altura: int | None = None,
) -> alt.Chart:
    """Pirâmide etária: homens à esquerda, mulheres à direita.

    Escala única. A tentação é desenhar a população como barra de fundo, no
    estilo IBGE, mas população e casos diferem em três ordens de grandeza —
    o fundo só cabe junto com um segundo eixo x, e aí o comprimento de uma
    barra não diz nada sobre a outra. Quem quer o efeito da estrutura etária
    usa ``por_100mil``, que é a leitura correta e cabe num eixo só.
    """
    if dados.empty:
        return sem_dado("Sem dado por faixa etária para este recorte")

    base = dados.copy()
    if por_100mil:
        pop = pd.to_numeric(base["pop"], errors="coerce")
        base["valor"] = (base["valor"] / pop * 100_000).where(pop > 0)
        base = base.dropna(subset=["valor"])
        if base.empty:
            return sem_dado("Sem população para calcular a taxa")
        rotulo = f"{rotulo} por 100 mil hab."

    base["lado"] = base["sexo"].map({"M": -1, "F": 1}).fillna(1)
    base["sexo_rotulo"] = base["sexo"].map({"M": "Homens", "F": "Mulheres"})
    base["evento"] = base["valor"] * base["lado"]

    faixas = [f for _, f in sorted({(r.faixa_ord, r.faixa_etaria) for r in base.itertuples()})]
    formato = ",.1f" if por_100mil else ",.0f"

    # Domínio simétrico. Em tuberculose os homens somam quase o triplo das
    # mulheres, e sem isso o eixo cresce só para a esquerda: a pirâmide fica
    # torta e o excesso masculino, que é o achado, vira efeito de escala.
    limite = float(base["evento"].abs().max()) or 1.0
    dominio = [-limite, limite]

    grafico = (
        alt.Chart(base)
        .mark_bar()
        .encode(
            # Sem sinal no eixo: o lado já diz o sexo, e "-500 casos" não existe.
            x=alt.X(
                "evento:Q",
                title=rotulo,
                scale=alt.Scale(domain=dominio, nice=False),
                axis=alt.Axis(labelExpr=f"format(abs(datum.value), '{formato}')"),
            ),
            y=alt.Y(
                "faixa_etaria:N",
                sort=list(reversed(faixas)),
                title=None,
                # Sem isso o Altair rareia os rótulos e some com faixas.
                axis=alt.Axis(labelOverlap=False),
            ),
            color=alt.Color(
                "sexo_rotulo:N",
                scale=alt.Scale(
                    domain=["Homens", "Mulheres"], range=[COR_HOMENS, COR_MULHERES]
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("faixa_etaria:N", title="Faixa"),
                alt.Tooltip("sexo_rotulo:N", title="Sexo"),
                alt.Tooltip("valor:Q", title=rotulo, format=formato),
            ],
        )
    )
    # `altura` é **piso e não teto**, como no ranking: o painel pede uma
    # altura para dividir a linha com o mapa, que é fixo em 500px, mas uma
    # pirâmide com onze faixas precisa de 30px por faixa ou as barras
    # encavalam. Quem manda é o maior dos dois.
    return tema(grafico, altura=max(altura or 0, 280, 30 * len(faixas)))


#: Espaço vertical de cada barra da composição.
ALTURA_BARRA_COMPOSICAO = 30

#: Espaço que não é barra: título, eixo x e o rótulo do eixo.
#:
#: **Precisa entrar na conta separado.** A primeira versão da grade usava
#: `max(altura, 30 * n)`, e com cinco categorias isso dava exatamente os 150px
#: pedidos pelo painel — os mesmos 150 de um gráfico de três. Como o cromo come
#: os primeiros 85, sobravam 65px para cinco barras, 13 cada, e os rótulos
#: encavalavam. O sintoma era só em "Tipo de entrada", que é a variável com
#: mais categorias entre as dez que abrem.
CROMO_COMPOSICAO = 85


def altura_composicao(categorias: int) -> int:
    """Altura total de um gráfico de composição com ``categorias`` barras."""
    return CROMO_COMPOSICAO + ALTURA_BARRA_COMPOSICAO * max(categorias, 1)


def composicao(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    altura: int | None = None,
    largura_rotulo: int = 220,
    ordem_dos_dados: bool = False,
) -> alt.Chart:
    """Distribuição de uma variável do SINAN, em barras horizontais.

    Mostra percentual quando a base sustenta e contagem quando não — a
    decisão vem pronta da camada de dados, em ``leitura.composicao``, que
    anula ``pct`` abaixo do limiar. Aqui só se obedece.
    """
    if dados.empty:
        return sem_dado("Sem registro desta variável no recorte")

    base = dados.copy()
    percentual = "pct" in base.columns and base["pct"].notna().any()

    if percentual:
        base["valor"] = pd.to_numeric(base["pct"], errors="coerce")
        # Inteiro no eixo, decimal só no tooltip: com passo de 2% o eixo
        # ganhava 28 marcações e virava uma régua.
        titulo_x, formato = "% dos casos", ".0f"
    else:
        base["valor"] = pd.to_numeric(base["n"], errors="coerce")
        titulo_x, formato = "Casos", ",.0f"

    # Por frequência, salvo quando a ordem já vem pronta da leitura — variáveis
    # numéricas (nº de contatos, de nervos, de doses) se leem em ordem
    # crescente, não da barra maior para a menor.
    if ordem_dos_dados:
        ordem = base["categoria"].tolist()
    else:
        ordem = base.sort_values("valor", ascending=False)["categoria"].tolist()

    grafico = (
        alt.Chart(base)
        .mark_bar(color=cor, cornerRadiusTopRight=2, cornerRadiusBottomRight=2)
        .encode(
            x=alt.X(
                "valor:Q",
                title=titulo_x,
                axis=alt.Axis(format=formato, tickCount=6),
            ),
            y=alt.Y("categoria:N", sort=ordem, title=None,
                    # `largura_rotulo` acompanha o espaço disponível: 220px
                    # num gráfico de largura inteira, menos numa grade de
                    # pequenos múltiplos. Sem isso, "5ª a 8ª série incompleta
                    # do EF (antigo ginásio/1º grau)" reserva 220px de coluna
                    # de rótulo num gráfico de 350px, e sobra menos eixo que
                    # texto. O nome completo continua no tooltip.
                    axis=alt.Axis(labelLimit=largura_rotulo, labelOverlap=False)),
            tooltip=[
                alt.Tooltip("categoria:N", title=rotulo),
                alt.Tooltip("n:Q", title="Casos", format=",.0f"),
            ] + ([alt.Tooltip("pct:Q", title="% dos casos", format=".1f")]
                 if percentual else []),
        )
    )
    # **O nome da variável vira título do gráfico.**
    #
    # Antes ele só alimentava o tooltip, e bastava: havia um gráfico por vez, e
    # quem dizia qual variável era o seletor logo acima. Numa grade de dez, o
    # seletor não aponta para nenhum em particular — dez gráficos de barras
    # horizontais sem título são dez gráficos idênticos.
    grafico = grafico.properties(
        title=alt.TitleParams(
            rotulo, anchor="start", fontSize=13, fontWeight=600, offset=6
        )
    )

    return tema(grafico, altura=altura or altura_composicao(len(base)))


#: Paleta do canal endêmico, aproximada do painel de origem.
#:
#: Lá a faixa é azul-clara, o Q1 e o Q3 são linhas cinzas com ponto, e cada ano
#: anterior tem cor própria — 2022 azul, 2021 vermelho, 2020 cinza-escuro. O
#: ano selecionado é uma linha azul-marinho grossa, que é a cor institucional
#: de Recife e a única coisa que o leitor precisa achar de imediato.
#:
#: A diferença é que aqui são **cinco** anos de referência, não três
#: (`docs/paridade-com-o-painel-r.md` §6). Cinco linhas coloridas competiriam com a do ano
#: corrente, então elas saem numa rampa fria do mais antigo ao mais recente:
#: quem é mais velho é mais apagado, e a ordem se lê sem consultar a legenda.
#: Nomes das séries na legenda, iguais aos do painel de origem — quem usa os
#: dois painéis não deveria ter de reaprender o vocabulário.
SERIE_ATUAL = "Ano selecionado"
SERIE_Q1 = "Q1"
SERIE_Q3 = "Q3"

COR_FAIXA = "#CBDCEF"
COR_BORDA_FAIXA = "#8FA9C4"
RAMPA_REFERENCIA = ("#C3CBD4", "#A8B6C6", "#8C9FB8", "#6E88AA", "#4A78B0")

#: Seleção que segue o mês mais próximo do cursor, para o tooltip unificado.
#: `nearest` faz a régua grudar na coluna do mês em vez de exigir que o
#: cursor acerte a linha — comparar março de 2023 com março de 2021 não pode
#: depender de pontaria.
_FOCO_MES = alt.selection_point(
    name="foco_mes", on="pointerover", nearest=True,
    fields=["mes_rotulo"], empty=False,
)

AVISO_CANAL = (
    "A faixa azul é o intervalo interquartil dos {n} anos anteriores "
    "({anos}): metade dos meses históricos caiu dentro dela. Mês acima do "
    "topo da faixa está fora do padrão desta cidade para aquele mês."
)


def canal_endemico(
    canal,
    *,
    rotulo: str,
    cor: str,
    altura: int = ALTURA,
) -> alt.Chart:
    """Canal endêmico: ano corrente sobre a faixa interquartil histórica.

    ``canal`` é o `src.data.canal.Canal`.

    **A faixa é uma área com `y` e `y2`, não duas áreas empilhadas.** O painel
    de origem, em ECharts, precisa do truque de empilhar uma série invisível no
    Q1 e outra com a altura da diferença, porque aquela biblioteca não desenha
    área entre duas linhas arbitrárias — e paga o preço de duas séries mudas
    (``name = " "``) que precisa esconder do tooltip uma a uma. O Altair
    desenha entre duas linhas, e essas séries fantasma não existem.

    **Todas as séries entram numa escala de cor só.** É o que faz a legenda
    listar "Ano selecionado", cada ano de referência, Q1 e Q3 — como no painel
    de origem. Com escalas independentes por camada o Altair desenha as linhas
    certas e não monta legenda nenhuma, que foi a primeira versão: cinco linhas
    frias no fundo viram textura, e o leitor vê que houve anos antes sem
    conseguir dizer qual é qual.

    **O tooltip é unificado**, também como no deles: uma régua sobre o mês mais
    próximo mostra o valor de todas as séries de uma vez. Tooltip por linha
    obrigaria a acertar o cursor em cada uma para comparar março de 2023 com
    março de 2021, que é justamente a leitura que o gráfico existe para dar.
    """
    if getattr(canal, "vazio", True):
        return sem_dado("Sem série mensal para montar o canal")

    def _rotular(df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(mes_rotulo=df["mes_nome"].str.slice(0, 3).str.capitalize())

    atual = _rotular(canal.atual).assign(serie=SERIE_ATUAL)
    faixa = _rotular(canal.faixa)
    vazia = pd.DataFrame(columns=["mes", "mes_rotulo", "serie", "valor"])
    referencia = (
        _rotular(canal.referencia).assign(serie=lambda d: d["ano"].astype(str))
        if not canal.referencia.empty
        else vazia
    )
    anos = [str(a) for a in canal.anos]

    ordem = list(atual.sort_values("mes")["mes_rotulo"])
    eixo_x = alt.X("mes_rotulo:N", sort=ordem, title=None)

    # Domínio e cores de todas as séries, numa escala só — é o que junta a
    # legenda. A rampa é recortada ao número de anos: com três, usa os tons
    # mais fortes, para o mais recente não sair apagado demais.
    rampa = list(RAMPA_REFERENCIA[-len(anos):]) if anos else []
    dominio = [SERIE_ATUAL, *anos, SERIE_Q1, SERIE_Q3]
    tons = [cor, *rampa, COR_BORDA_FAIXA, COR_BORDA_FAIXA]
    escala_cor = alt.Scale(domain=dominio, range=tons)
    legenda = alt.Legend(title=None, symbolType="stroke", orient="top")

    def _cor() -> alt.Color:
        return alt.Color("serie:N", scale=escala_cor, legend=legenda, title=None)

    camadas = [
        # A faixa. Sem encodificação de cor: ela é fundo, não série — entrar na
        # legenda a poria em pé de igualdade com as linhas.
        alt.Chart(faixa)
        .mark_area(color=COR_FAIXA, opacity=0.85)
        .encode(x=eixo_x, y=alt.Y("q1:Q", title=rotulo), y2=alt.Y2("q3:Q"))
    ]

    # As bordas da faixa, nomeadas — é o "Q1" e o "Q3" da legenda deles.
    for campo, nome in (("q1", SERIE_Q1), ("q3", SERIE_Q3)):
        camadas.append(
            alt.Chart(faixa.assign(serie=nome))
            .mark_line(strokeWidth=1.5, point=alt.OverlayMarkDef(size=20))
            .encode(x=eixo_x, y=alt.Y(f"{campo}:Q"), color=_cor())
        )

    if not referencia.empty:
        camadas.append(
            alt.Chart(referencia)
            .mark_line(strokeWidth=1.3, strokeDash=[4, 3])
            .encode(x=eixo_x, y=alt.Y("valor:Q"), color=_cor(), detail="serie:N")
        )

    camadas.append(
        alt.Chart(atual)
        .mark_line(strokeWidth=2.8, point=alt.OverlayMarkDef(size=48))
        .encode(x=eixo_x, y=alt.Y("valor:Q"), color=_cor())
    )

    camadas.append(_regua_do_canal(canal, atual, faixa, referencia, eixo_x))

    return tema(alt.layer(*camadas), altura=altura)


def _regua_do_canal(canal, atual, faixa, referencia, eixo_x) -> alt.Chart:
    """Régua que entrega o tooltip unificado do mês sob o cursor.

    Uma tabela **larga** — um registro por mês, uma coluna por série — porque o
    tooltip do Vega-Lite lê campos de *um* registro. Em formato longo ele
    mostraria uma série por vez, que é o que se quer evitar.
    """
    largo = atual[["mes", "mes_rotulo", "valor"]].rename(
        columns={"valor": SERIE_ATUAL}
    )
    largo = largo.merge(faixa[["mes", "q1", "q3"]], on="mes", how="left").rename(
        columns={"q1": SERIE_Q1, "q3": SERIE_Q3}
    )

    if not referencia.empty:
        for ano, grupo in referencia.groupby("serie"):
            largo = largo.merge(
                grupo[["mes", "valor"]].rename(columns={"valor": str(ano)}),
                on="mes",
                how="left",
            )

    # Ordem do tooltip: ano corrente, anos de referência do mais recente ao
    # mais antigo, e a faixa por último — a mesma ordem de leitura do gráfico.
    anos = sorted((str(a) for a in canal.anos), reverse=True)
    campos = [SERIE_ATUAL, *anos, SERIE_Q1, SERIE_Q3]

    return (
        alt.Chart(largo)
        .mark_rule(color="rgba(128,128,128,.55)", strokeWidth=1)
        .encode(
            x=eixo_x,
            opacity=alt.condition(_FOCO_MES, alt.value(0.4), alt.value(0)),
            tooltip=[
                alt.Tooltip("mes_rotulo:N", title="Mês"),
                *[
                    alt.Tooltip(f"{campo}:Q", title=campo, format=",.2f")
                    for campo in campos
                    if campo in largo.columns
                ],
            ],
        )
        .add_params(_FOCO_MES)
    )


#: Régua da epicurva. Separada da do canal porque o campo de referência é
#: outro — lá o mês, aqui a data — e uma seleção só serve a um campo.
_FOCO_DATA = alt.selection_point(
    name="foco_data", on="pointerover", nearest=True, fields=["data"], empty=False
)


def epicurva(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    altura: int = 220,
    ano_em_foco: int | None = None,
) -> alt.Chart:
    """Série mensal contínua, atravessando os anos.

    O par do canal endêmico, e a pergunta é outra: o canal dobra o tempo em
    doze meses para perguntar "julho está dentro do padrão de julho?", e esta
    estica o tempo numa linha só para perguntar "para onde isto vem indo?".

    **Eixo temporal, e não categórico.** São 168 pontos; num eixo de categoria
    o Altair tentaria escrever os 168 rótulos e o eixo viraria uma tarja preta.
    Com ``:T`` ele escolhe os anos e escreve doze marcas.

    ``ano_em_foco`` acende o trecho do ano selecionado no seletor. Sem isso a
    linha é uma corda de catorze anos sem indicação de onde o resto do painel
    está olhando — o painel de origem não marca, e o leitor precisa contar os
    ticks para se achar.

    **O tooltip pega a coluna inteira do mês, não o ponto.** Com 168 pontos em
    poucos pixels, exigir que o cursor acerte o vértice torna o dado
    praticamente inalcançável: era preciso caçar as pontinhas da linha. A régua
    invisível resolve pelo mesmo mecanismo do canal — `nearest` sobre a data.
    """
    if dados.empty:
        return sem_dado("Sem série mensal para este recorte")

    base = dados.assign(
        data=pd.to_datetime(dict(year=dados["ano"], month=dados["mes"], day=1))
    )
    eixo_x = alt.X("data:T", title=None, axis=alt.Axis(format="%Y", tickCount="year"))

    camadas = [
        alt.Chart(base)
        .mark_line(color=cor, strokeWidth=1.6)
        .encode(x=eixo_x, y=alt.Y("casos:Q", title=rotulo))
    ]

    if ano_em_foco is not None:
        foco = base[base["ano"] == ano_em_foco]
        if not foco.empty:
            camadas.append(
                alt.Chart(foco)
                .mark_line(color=cor, strokeWidth=3)
                .encode(x=eixo_x, y=alt.Y("casos:Q"))
            )

    camadas.append(
        alt.Chart(base)
        .mark_rule(color="rgba(128,128,128,.55)", strokeWidth=1)
        .encode(
            x=eixo_x,
            opacity=alt.condition(_FOCO_DATA, alt.value(0.4), alt.value(0)),
            tooltip=[
                alt.Tooltip("ano_mes:N", title="Mês"),
                alt.Tooltip("casos:Q", title=rotulo, format=",.0f"),
            ],
        )
        .add_params(_FOCO_DATA)
    )

    # O ponto sob o cursor, para o olho confirmar de qual mês o número saiu.
    camadas.append(
        alt.Chart(base)
        .mark_point(color=cor, size=55, filled=True)
        .encode(
            x=eixo_x,
            y=alt.Y("casos:Q"),
            opacity=alt.condition(_FOCO_DATA, alt.value(1), alt.value(0)),
        )
    )

    return tema(alt.layer(*camadas), altura=altura)


def barras_empilhadas_com_linha(
    dados: pd.DataFrame,
    *,
    barras: dict[str, str],
    linha: str,
    rotulo_linha: str,
    cores: dict[str, str],
    cor_linha: str,
    altura: int = 260,
    formato_linha: str = ".1f",
) -> alt.Chart:
    """Barras empilhadas por ano com uma linha em eixo próprio à direita.

    É o formato dos dois gráficos de rodapé do painel de origem: MB e PB
    empilhados com a proporção MB em linha; casos 0–14 com a taxa em linha.
    ``barras`` é ``coluna → rótulo``; ``linha`` é a coluna da linha.
    """
    if dados.empty:
        return sem_dado("Sem série para este recorte")

    longo = dados.melt(
        id_vars=["ano", linha], value_vars=list(barras), var_name="serie", value_name="n"
    )
    longo["serie"] = longo["serie"].map(barras)
    dominio = list(barras.values())
    paleta = [cores[c] for c in barras]

    base = alt.Chart(longo).encode(x=alt.X("ano:O", title="Ano"))
    colunas = base.mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        y=alt.Y("n:Q", title="Casos", stack="zero"),
        color=alt.Color(
            "serie:N",
            scale=alt.Scale(domain=dominio, range=paleta),
            title=None,
            legend=alt.Legend(orient="top", direction="horizontal"),
        ),
        tooltip=[
            alt.Tooltip("ano:O", title="Ano"),
            alt.Tooltip("serie:N", title="Série"),
            alt.Tooltip("n:Q", title="Casos", format=",.0f"),
        ],
    )
    traco = (
        alt.Chart(dados)
        .mark_line(point=True, color=cor_linha, strokeWidth=2)
        .encode(
            x=alt.X("ano:O"),
            y=alt.Y(f"{linha}:Q", title=rotulo_linha, axis=alt.Axis(orient="right")),
            tooltip=[
                alt.Tooltip("ano:O", title="Ano"),
                alt.Tooltip(f"{linha}:Q", title=rotulo_linha, format=formato_linha),
            ],
        )
    )
    grafico = alt.layer(colunas, traco).resolve_scale(y="independent")
    return tema(grafico, altura=altura)
