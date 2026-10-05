"""Canal endêmico: o ano corrente contra a faixa histórica.

O gráfico de meses do painel de origem não é uma série simples. São o ano
selecionado, os anos anteriores desenhados atrás, e uma **faixa interquartil**
entre eles — o canal endêmico clássico da vigilância. O que ele responde não é
"quantos casos houve em março", mas "março está dentro do que esta cidade
costuma ter em março".

A regra, reconstruída do painel deles
-------------------------------------

Os quartis saem dos anos imediatamente anteriores, com interpolação linear — a
mesma que o ``numpy`` usa por padrão. A regra foi reconstruída dos números que
eles publicam, não de documentação: com **três** anos de referência, de 2020,
2021 e 2022 saem exatamente o Q1 e o Q3 que o painel deles desenha para
janeiro, no sexto decimal. `tests/test_canal.py` mantém essa conferência
fixada em três, porque ela é a prova de que entendemos o método.

**Mas o padrão aqui é cinco.** Três é o que o
painel de origem usa, e é pouco: com três pontos por mês cada quartil cai
entre dois valores, e a faixa oscila com qualquer ano atípico. Com três anos,
2020 — o mínimo da série, deprimido pela pandemia — pesa um terço da faixa.

O limite que nenhum número de anos resolve
------------------------------------------

**A tuberculose em Recife está em alta sustentada, e isso limita o que este
gráfico pode afirmar.** A incidência anual foi 111,2 em 2018, caiu a 103,9 em
2020 e subiu a 156,1 em 2023 — cerca de 50% acima do piso, em três anos.

O canal endêmico pressupõe um padrão **estacionário**: a faixa histórica é o
"esperado" e o ano corrente é comparado contra ele. Sob tendência de alta, a
faixa fica sempre atrás, e o ano corrente aparece acima quase todo mês — foi o
que aconteceu: onze dos doze meses de 2023 estão acima do Q3.

Isso é leitura verdadeira e é útil, mas **diz "a doença cresceu", e não
"houve um surto em março"**. Quem usar o gráfico para detectar anomalia
sazonal precisa saber disso; passar de três para cinco anos melhora a
estabilidade da faixa, não resolve a tendência.

A divergência de número de anos com o painel de origem está registrada em
`../RecifeTB/docs/paridade-com-o-painel-r.md` §6.

A divergência de denominador
----------------------------

**Eles usam a população do ano selecionado para todos os anos da série.**
Medido: a população implicada nas séries de 2020, 2021 e 2022 é 1.592.362 nos
três, que é a de 2023. Nós usamos a população de cada ano.

A diferença é de 0,37% e a escolha não é indiferente. Com denominador fixo, a
linha de 2020 não é a incidência de 2020 — é a contagem de 2020 medida contra
a população de hoje, um número que não é a taxa de ano nenhum. Como o canal
existe para dizer se o mês corrente está fora do padrão **histórico**, o
padrão tem de ser o que de fato aconteceu.

Ver `../RecifeTB/docs/paridade-com-o-painel-r.md` §5.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import leitura
from .escopo import Escopo

#: Primeiro ano da epicurva. É o começo da série do SINAN nesta extração —
#: anos anteriores simplesmente não existem, e o laço os pula sem reclamar.
_ANO_MIN = 2010

#: Quantos anos anteriores compõem a faixa.
#:
#: Cinco por decisão nossa; o painel de origem usa três. Ver a docstring do
#: módulo e `../RecifeTB/docs/paridade-com-o-painel-r.md` §6 — mudar este
#: número muda o que o gráfico
#: **afirma**, não só como ele parece.
ANOS_REFERENCIA = 5


@dataclass(frozen=True, slots=True)
class Canal:
    """As três camadas do gráfico, já prontas para desenhar.

    Separadas, e não numa tabela longa só, porque cada uma vira uma camada
    diferente do Altair — área, linhas finas, linha grossa — e reuni-las
    obrigaria a fatiar de novo na hora de desenhar.
    """

    #: ``mes``, ``mes_nome``, ``q1``, ``q3``.
    faixa: pd.DataFrame
    #: ``mes``, ``mes_nome``, ``ano``, ``valor`` — um por ano de referência.
    referencia: pd.DataFrame
    #: ``mes``, ``mes_nome``, ``valor`` — o ano selecionado.
    atual: pd.DataFrame
    #: Anos que entraram na faixa, para a legenda dizer a verdade.
    anos: tuple[int, ...]

    @property
    def vazio(self) -> bool:
        return self.atual.empty or self.faixa.empty


def _incidencia_mensal(esc: Escopo, ano: int, grau: str | None = None) -> pd.DataFrame:
    """Incidência por 100 mil em cada mês de ``ano``, no escopo dado.

    Sai de `leitura.serie_dupla`, que já traz `casos` e `incid` do
    ``_cache_ts`` — **a mesma fonte dos KPIs**, para a linha do gráfico e o
    card não divergirem como divergiram no painel nacional.
    """
    from dataclasses import replace

    return leitura.serie_dupla(replace(esc, ano=ano), "meses", grau=grau)


def montar(
    esc: Escopo, anos_referencia: int = ANOS_REFERENCIA, grau: str | None = None
) -> Canal:
    """Monta o canal endêmico do ano de ``esc``.

    Funciona em qualquer escopo que o ``_cache_ts`` cubra — UF e município.
    Num município pequeno a taxa mensal por 100 mil oscila muito; o gráfico
    continua honesto, só mais ruidoso.

    Anos de referência que não existem no dado são simplesmente pulados: em
    2010 não há três anteriores, e o gráfico ainda assim tem o que dizer.
    """
    cidade = esc
    atual = _incidencia_mensal(cidade, cidade.ano, grau)
    if atual.empty:
        vazia = pd.DataFrame(columns=["mes", "mes_nome", "valor"])
        return Canal(
            faixa=pd.DataFrame(columns=["mes", "mes_nome", "q1", "q3"]),
            referencia=pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"]),
            atual=vazia,
            anos=(),
        )

    anteriores: list[pd.DataFrame] = []
    for ano in range(cidade.ano - anos_referencia, cidade.ano):
        try:
            serie = _incidencia_mensal(cidade, ano, grau)
        except FileNotFoundError:
            continue
        if not serie.empty:
            anteriores.append(serie.assign(ano=ano))

    meses = atual[["mes", "mes_nome"]].drop_duplicates().sort_values("mes")

    if not anteriores:
        return Canal(
            faixa=meses.assign(q1=np.nan, q3=np.nan),
            referencia=pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"]),
            atual=atual.rename(columns={"incid": "valor"})[["mes", "mes_nome", "valor"]],
            anos=(),
        )

    historico = pd.concat(anteriores, ignore_index=True)
    quartis = (
        historico.groupby("mes")["incid"]
        .agg(
            # Interpolação linear, o padrão do numpy — é o que reproduz os
            # valores publicados pelo painel de origem no sexto decimal.
            q1=lambda s: float(np.quantile(s, 0.25)),
            q3=lambda s: float(np.quantile(s, 0.75)),
        )
        .reset_index()
    )

    return Canal(
        faixa=meses.merge(quartis, on="mes", how="left"),
        referencia=historico.rename(columns={"incid": "valor"})[
            ["mes", "mes_nome", "ano", "valor"]
        ],
        atual=atual.rename(columns={"incid": "valor"})[["mes", "mes_nome", "valor"]],
        anos=tuple(sorted(historico["ano"].unique())),
    )


def meses_fora_da_faixa(canal: Canal) -> pd.DataFrame:
    """Meses do ano corrente acima do Q3 ou abaixo do Q1.

    É a leitura que o canal existe para dar, e que o painel de origem deixa
    por conta do olho. Devolve ``mes``, ``mes_nome``, ``valor``, ``q1``, ``q3``
    e ``posicao`` — ``"acima"`` ou ``"abaixo"``.
    """
    if canal.vazio:
        return pd.DataFrame(
            columns=["mes", "mes_nome", "valor", "q1", "q3", "posicao"]
        )

    juncao = canal.atual.merge(canal.faixa[["mes", "q1", "q3"]], on="mes", how="left")
    acima = juncao["valor"] > juncao["q3"]
    abaixo = juncao["valor"] < juncao["q1"]
    fora = juncao[acima | abaixo].copy()
    fora["posicao"] = np.where(fora["valor"] > fora["q3"], "acima", "abaixo")
    return fora.reset_index(drop=True)


def epicurva(esc: Escopo, ano_min: int | None = None) -> pd.DataFrame:
    """Série mensal contínua, atravessando todos os anos disponíveis.

    Colunas ``ano_mes`` (``"2023-07"``), ``ano``, ``mes`` e ``casos``.

    É o segundo gráfico da aba de evolução no painel de origem, embaixo do
    canal. Os dois respondem perguntas diferentes e por isso convivem: o canal
    pergunta "julho está dentro do padrão de julho?", dobrando o tempo em doze
    meses; a epicurva pergunta "para onde isto vem indo?", esticando o tempo
    numa linha só.

    **Vai até o último ano com dado, e não até 2019.** A epicurva do painel
    deles tem 120 pontos e termina em ``2019-12`` com dado disponível até 2023
    — janela fixa de dez anos ou truncamento, é a pergunta §4 do
    `../RecifeTB/docs/paridade-com-o-painel-r.md`, ainda sem resposta. Reproduzir o corte por imitação seria
    herdar um comportamento que ninguém sabe explicar; e num painel cuja
    leitura principal é "a incidência subiu desde 2020", esconder 2020 a 2023
    apagaria justamente o que ele tem a dizer.

    Só Recife inteiro, pelo mesmo motivo do canal: o ``_cache_ts`` não desce a
    bairro.
    """
    primeiro = ano_min if ano_min is not None else _ANO_MIN
    try:
        tudo = leitura.serie_mensal_casos(esc, primeiro, esc.ano)
    except FileNotFoundError:
        return pd.DataFrame(columns=["ano_mes", "ano", "mes", "casos"])

    if tudo.empty:
        return pd.DataFrame(columns=["ano_mes", "ano", "mes", "casos"])

    tudo["ano_mes"] = (
        tudo["ano"].astype(str) + "-" + tudo["mes"].astype(int).astype(str).str.zfill(2)
    )
    return (
        tudo.sort_values(["ano", "mes"])[["ano_mes", "ano", "mes", "casos"]]
        .reset_index(drop=True)
    )
