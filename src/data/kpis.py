"""Cálculo dos KPIs.

Fórmulas em docs/contrato-dados.md. Todas devolvem ``None`` quando o
denominador é zero ou o dado não existe — nunca zero, que seria confundido
com um valor real.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from . import leitura
from .escopo import Escopo

POR_100K = 100_000

#: Quanto das saídas de tratamento precisa estar registrado para cura,
#: abandono e contatos significarem alguma coisa.
#:
#: Esses três se preenchem ao longo do acompanhamento, não no diagnóstico:
#: medido em PE, a cobertura (saídas registradas ÷ casos) vai de 97% em 2018
#: a 19% em 2025. Com 19%, a "proporção de cura" dá 30% — e não é programa
#: ruim, é coorte aberta. O boletim resolve publicando esses indicadores só
#: até o último ano de coorte fechada; aqui o número é suprimido, como o
#: percentual de base pequena em `leitura.MINIMO_PARA_PERCENTUAL`.
#:
#: 50% é folgado: 2024 fecha com 65,7% e reproduz o boletim (67,1% contra
#: 65,0%), e 2023 com 74,2%.
COBERTURA_MINIMA_COORTE = 0.5


def _div(numerador, denominador, fator: float = 1.0) -> float | None:
    try:
        n, d = float(numerador), float(denominador)
    except (TypeError, ValueError):
        return None
    if d <= 0 or n != n or d != d:  # NaN não é igual a si mesmo
        return None
    return (n / d) * fator


def _sem_acento(texto) -> str:
    s = str(texto or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Regra do indicador de interrupção de tratamento
# ---------------------------------------------------------------------------
# Três regras, e a diferença entre elas não é detalhe de implementação: é
# qual pergunta o indicador responde.
#
#   paridade  {2}    / todos      reproduz o dashboard em R
#   ms        {2,10} / avaliados  o indicador do Ministério, que exclui os
#                                 não avaliados do denominador
#   boletim   {2,10} / todos      como a Tabela 9 do Boletim Epidemiológico
#                                 apresenta a distribuição de desfechos
#
# As duas últimas são ambas "do MS" e não se contradizem: uma é definição de
# indicador de monitoramento, a outra é apresentação de distribuição — no
# boletim, cura, interrupção e "não avaliados" são três colunas da **mesma**
# base, o que só fecha com o denominador completo.
#
# Medido para o Brasil em 2024:
#
#     paridade = 14,91%      ms = 17,20%      boletim = 15,52%
#     Tabela 9 do boletim, casos novos de TB: 15,2%
#
# `boletim` é a que reproduz o publicado; os 0,32 pontos restantes são a
# defasagem de extração. Nosso denominador tem 75.404 encerramentos e as
# porcentagens do MS implicam 77.467, com a diferença concentrada em "não
# avaliados" — 9,7% aqui contra 12,6% lá, que é o que se espera de casos ainda
# sem encerramento numa extração anterior. Aplicando `{2,10}` sobre o
# denominador **deles**, dá 15,11%.
#
# **Atenção à população.** A Tabela 9 publica três: todos os casos novos de TB
# (86.204), só pulmonar (74.885) e pulmonar confirmada em laboratório
# (56.388), com interrupção de 15,2%, 15,9% e 16,5%. A nossa é a primeira.
# Comparar com 16,5% — como se chegou a fazer aqui — é comparar populações
# diferentes.
#
# Qual exibir continua sendo decisão com a equipe de R, e agora com três
# opções em vez de duas. Ver tests/paridade/excecoes.md.

REGRA_INTERRUPCAO = "boletim"

#: Códigos de SITUA_ENCE contados como interrupção. O MS soma abandono (2) e
#: abandono primário (10) — quem nunca chegou a iniciar também interrompeu.
_ABANDONO = {
    "paridade": {"2"},
    "ms": {"2", "10"},
    "boletim": {"2", "10"},
}

#: Ordem e composição dos desfechos empilhados da evolução, no formato da
#: Figura 22 do Boletim de TB 2026 — cura, interrupção, óbito e o resto.
#:
#: O denominador é **todos os encerramentos**, o mesmo de
#: `interrupcao_trat_pct` sob a regra `boletim`, e por isso as quatro fatias
#: somam 100% por construção: a última é o complemento, não uma lista. Listar
#: os códigos dela deixaria um código novo do SINAN sumir do gráfico sem
#: ninguém notar; sendo complemento, ele aparece — no balde errado, mas
#: aparece, e o total continua fechando.
#:
#: O boletim exclui do denominador os encerramentos por TB drogarresistente,
#: mudança de esquema e falência. Nós não excluímos, para o gráfico usar o
#: mesmo denominador do card de interrupção — ver `tests/paridade/excecoes.md`.
GRUPOS_DESFECHO: tuple[tuple[str, frozenset[str]], ...] = (
    ("cura", frozenset({"1"})),
    ("interrupcao", frozenset(_ABANDONO[REGRA_INTERRUPCAO])),
    ("obito", frozenset({"3", "4"})),
    ("outros", frozenset()),  # complemento; ver acima
)

def grupo_do_desfecho(codigo: str) -> str:
    """Em que fatia do empilhado um código de `SITUA_ENCE` cai.

    **Normaliza o zero à esquerda.** O dataset traz `03` e `04` convivendo com
    `3` e `4` — só em 2018 e 2019, 177 registros —, e `trim` não resolve isso.
    Sem normalizar, esses óbitos cairiam silenciosamente em "outros".
    """
    limpo = str(codigo).strip().lstrip("0") or "0"
    for nome, codigos in GRUPOS_DESFECHO:
        if limpo in codigos:
            return nome
    return "outros"


#: Códigos excluídos do denominador. Só o indicador de monitoramento do MS os
#: exclui; o R e o boletim usam todos os encerramentos.
_NAO_AVALIADOS = {
    "paridade": set(),
    "ms": {"0", "5", "7", "8"},
    "boletim": set(),
}


@dataclass(frozen=True, slots=True)
class Kpis:
    casos: float | None = None
    obitos: float | None = None
    cura: float | None = None
    #: Encerramentos por cura sobre **todos os encerramentos**, que é o
    #: denominador da Tabela 9 do Boletim de TB 2026 e o mesmo de
    #: `interrupcao_trat_pct` sob a regra `boletim`.
    #:
    #: Era sobre os casos novos do ano, e dava 57,15% no Brasil em 2024 contra
    #: 65,1% agora. Trocou em 21/ago/2026: com o empilhado de desfechos na
    #: evolução, a tela passou a ter dois números de cura para o mesmo ano,
    #: oito pontos apart e ambos rotulados "cura".
    #:
    #: Continua sendo aproximação de coorte — o tratamento leva cerca de seis
    #: meses, então parte dos casos de um ano só encerra no seguinte, e não há
    #: como fechar a coorte com os agregados que recebemos. `letalidade`
    #: convive com a mesma aproximação, pelo mesmo motivo.
    cura_pct: float | None = None
    pop: float | None = None
    incid: float | None = None
    mortalidade: float | None = None
    letalidade: float | None = None
    casos_0_14: float | None = None
    pop_0_14: float | None = None
    taxa_det_0_14: float | None = None
    hiv_pos_pct: float | None = None
    interrupcao_trat_pct: float | None = None
    #: Encerramentos por cura e total de encerramentos, os dois de
    #: `SITUA_ENCE`. Existem para a fração sob o card bater com a porcentagem
    #: dele: `incidence.casos_cura` e `SITUA_ENCE = 1` diferem em alguns casos
    #: por UF — 2.619 contra 2.621 em PE — porque um é por residência e o
    #: outro por notificação. Misturar as fontes faria a conta exibida não
    #: fechar com o número exibido.
    cura_encerrada: float | None = None
    encerramentos: float | None = None
    #: Hanseníase. Proporções clínicas do painel de origem, com numerador e
    #: denominador guardados para a fração sob o card sair da mesma conta.
    #: `avaliacao_base` inclui "não avaliado" e exclui os sem `AVALIA_N` —
    #: é o denominador do painel de origem, não o do Ministério (só avaliados).
    prop_mb_pct: float | None = None
    multibacilares: float | None = None
    classificados: float | None = None
    prop_grau2_pct: float | None = None
    grau2: float | None = None
    avaliacao_base: float | None = None
    #: Indicadores de qualidade do programa, nos parâmetros do Boletim
    #: Epidemiológico de Hanseníase (SES-PE). Todos com numerador e
    #: denominador guardados, para a fração do card sair da mesma conta.
    abandono_pct: float | None = None
    abandonos: float | None = None
    saidas: float | None = None
    contatos_pct: float | None = None
    contatos_examinados: float | None = None
    contatos_registrados: float | None = None
    gif_avaliado_pct: float | None = None
    gif_avaliados: float | None = None
    gif_base: float | None = None
    #: A coorte do ano ainda não fechou — cura, abandono e contatos vêm
    #: nulos. Ver `COBERTURA_MINIMA_COORTE`.
    coorte_aberta: bool = False
    #: Saídas registradas ÷ casos, o que decidiu a supressão acima.
    cobertura_saidas: float | None = None


def encerramentos(esc: Escopo):
    """Distribuição de ``SITUA_ENCE`` no recorte, ou ``None`` fora da TB.

    Existe para ser lida **uma vez** por :func:`calcular` e emprestada a quem
    precisa. Antes, a contagem de desfechos e a interrupção liam cada uma a
    sua cópia, e o conjunto de KPIs pagava duas idas ao `sinan_landing` pelo
    mesmo dado — 7 dos 23 ms do recorte nacional.
    """
    if esc.doenca != "TUBERCULOSE":
        return None
    return leitura.variavel_sinan(esc, "SITUA_ENCE")


def contagem_desfechos(esc: Escopo, df=None) -> dict[str, float]:
    """Encerramentos por grupo de desfecho no recorte, mais ``total``.

    Mesma regra do empilhado da evolução e do mapa — os três leem
    :func:`grupo_do_desfecho`, então não há como um contar cura de um jeito e
    outro de outro.

    ``df`` evita reler: passe o que :func:`encerramentos` já devolveu.
    """
    if df is None:
        df = encerramentos(esc)
    if df is None or df.empty:
        return {}
    por_grupo = df.assign(g=df["valor"].map(grupo_do_desfecho)).groupby("g")["n"].sum()
    contagem = {nome: float(por_grupo.get(nome, 0.0)) for nome, _ in GRUPOS_DESFECHO}
    contagem["total"] = float(por_grupo.sum())
    return contagem


def calcular(esc: Escopo, regra_interrupcao: str | None = None) -> Kpis:
    """Todos os KPIs do recorte."""
    inc = leitura.incidencia(esc)
    inc14 = leitura.incidencia_0_14(esc)
    # Lido uma vez e emprestado aos dois consumidores abaixo.
    enc = encerramentos(esc)
    desfechos = contagem_desfechos(esc, enc)

    casos = inc.get("casos_total")
    if esc.doenca == "HANSENIASE":
        # Casos novos pela definição do Ministério (`MODOENTR = 1`). O
        # `casos_total` da extração é toda entrada no registro ativo —
        # recidiva e transferência inclusive — e é o que o painel de origem
        # mostra. Decisão de 20/set/2026: docs/paridade-hanseniase.md §1.
        casos = leitura.casos_novos_ms(esc)
    cura = inc.get("casos_cura")
    pop = inc.get("pop_total")

    # Óbitos vêm do SIM, não de incidence — lá o campo é zero para TB.
    obitos = leitura.obitos_sim(esc)

    casos_0_14 = inc14.get("casos_0_14_total")
    pop_0_14 = inc14.get("pop_0_14_total")

    # Cura e encerramentos: na TB saem de `SITUA_ENCE`; na hanseníase, de
    # `TPALTA_N`, dentro de `proporcoes_hanseniase` — que entra no fim e traz
    # os três campos. Por isso aqui eles só existem fora da hanseníase.
    desfecho_tb = (
        {}
        if esc.doenca == "HANSENIASE"
        else {
            "cura_pct": _div(desfechos.get("cura"), desfechos.get("total"), 100),
            "cura_encerrada": _num(desfechos.get("cura")),
            "encerramentos": _num(desfechos.get("total")),
        }
    )

    return Kpis(
        casos=_num(casos),
        obitos=_num(obitos),
        cura=_num(cura),
        pop=_num(pop),
        incid=_div(casos, pop, POR_100K),
        mortalidade=_div(obitos, pop, POR_100K),
        letalidade=_div(obitos, casos, 100),
        **desfecho_tb,
        casos_0_14=_num(casos_0_14),
        pop_0_14=_num(pop_0_14),
        taxa_det_0_14=_div(casos_0_14, pop_0_14, POR_100K),
        hiv_pos_pct=hiv_pos_pct(esc),
        interrupcao_trat_pct=interrupcao_trat_pct(esc, regra_interrupcao, enc),
        **proporcoes_hanseniase(esc, inc),
    )


def proporcoes_hanseniase(esc: Escopo, inc: dict) -> dict[str, float | None]:
    """Multibacilar e grau II, como o painel de origem calcula. Vazio fora da hanseníase.

    - MB = `CLASSOPERA = 2` sobre PB + MB (`sinan_landing`).
    - Grau II = `casos_grau_II` sobre grau 0 + I + II + não avaliado
      (`incidence`), que é o denominador do painel de origem: 218/2.171 =
      10,0% em PE 2025. Sobre o total dá 9,3%; sobre os avaliados (regra do
      MS) dá 12,0%. Ver docs/paridade-hanseniase.md.
    """
    if esc.doenca != "HANSENIASE":
        return {}

    classe = leitura.variavel_sinan(esc, "CLASSOPERA")
    mb = float(classe.loc[classe["valor"] == "2", "n"].sum()) if not classe.empty else None
    classificados = (
        float(classe.loc[classe["valor"].isin(["1", "2"]), "n"].sum())
        if not classe.empty else None
    )

    grau2 = _num(inc.get("casos_grau_II"))
    partes = [inc.get(c) for c in ("casos_grau_0", "casos_grau_I", "casos_grau_II", "casos_nao_avaliado")]
    base = sum(float(v) for v in partes if _num(v) is not None) if any(_num(v) is not None for v in partes) else None

    # --- indicadores de qualidade do programa (parâmetros SES-PE/MS) ------
    #
    # Cura e abandono saem de `TPALTA_N`, sobre **todas as saídas
    # registradas** no ano de diagnóstico — transferências e erro diagnóstico
    # inclusive. O boletim usa a coorte de casos novos (PB do ano anterior,
    # MB de dois anos antes), que só o microdado permite fechar; medido em PE
    # 2024, a aproximação dá 67,1% de cura contra 65,0% publicados e 12,2% de
    # abandono contra 13,5%. Ver docs/paridade-hanseniase.md §8.
    saida = leitura.variavel_sinan(esc, "TPALTA_N")
    saidas = float(saida["n"].sum()) if not saida.empty else None
    curados = float(saida.loc[saida["valor"] == "1", "n"].sum()) if not saida.empty else None
    abandonos = float(saida.loc[saida["valor"] == "7", "n"].sum()) if not saida.empty else None

    # Contatos: o valor da ficha é a **quantidade** por caso, não um código.
    examinados = leitura.soma_ponderada(esc, "CONTEXAM")
    registrados = leitura.soma_ponderada(esc, "CONTREG")

    # GIF avaliado no diagnóstico: quantos casos tiveram o grau de
    # incapacidade avaliado (grau 0, I ou II) sobre o total de casos.
    avaliados = sum(
        float(v) for v in (inc.get("casos_grau_0"), inc.get("casos_grau_I"), inc.get("casos_grau_II"))
        if _num(v) is not None
    ) or None
    casos_total = inc.get("casos_total")

    # Coorte aberta: os três indicadores de acompanhamento saem nulos, e o
    # card mostra "—" em vez de um número que só diz que o ano é recente.
    cobertura = _div(saidas, casos_total)
    aberta = cobertura is not None and cobertura < COBERTURA_MINIMA_COORTE

    return {
        "coorte_aberta": aberta,
        "cobertura_saidas": cobertura,
        "prop_mb_pct": _div(mb, classificados, 100),
        "multibacilares": _num(mb),
        "classificados": _num(classificados),
        "prop_grau2_pct": _div(grau2, base, 100),
        "grau2": grau2,
        "avaliacao_base": _num(base),
        "cura_pct": None if aberta else _div(curados, saidas, 100),
        "cura_encerrada": _num(curados),
        "encerramentos": _num(saidas),
        "abandono_pct": None if aberta else _div(abandonos, saidas, 100),
        "abandonos": _num(abandonos),
        "saidas": _num(saidas),
        "contatos_pct": None if aberta else _div(examinados, registrados, 100),
        "contatos_examinados": _num(examinados),
        "contatos_registrados": _num(registrados),
        "gif_avaliado_pct": _div(avaliados, casos_total, 100),
        "gif_avaliados": _num(avaliados),
        "gif_base": _num(casos_total),
    }


def _num(valor) -> float | None:
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def hiv_pos_pct(esc: Escopo) -> float | None:
    """Positividade do HIV entre os testados (tuberculose).

    Denominador = positivos + negativos. "Não realizado" e "em andamento"
    ficam de fora — testar a regra pelo rótulo, porque os códigos de HIV não
    são estáveis entre versões da ficha.
    """
    if esc.doenca != "TUBERCULOSE":
        return None

    df = leitura.variavel_sinan(esc, "HIV")
    if df.empty:
        return None

    rotulos = df["valor_lbl"].map(_sem_acento)
    negativo = rotulos.str.contains("negativ|nao reag", regex=True, na=False)
    positivo = ~negativo & rotulos.str.contains("positiv|reagente", regex=True, na=False)

    pos = float(df.loc[positivo, "n"].sum())
    testados = float(df.loc[positivo | negativo, "n"].sum())
    return _div(pos, testados, 100)


def interrupcao_trat_pct(
    esc: Escopo, regra: str | None = None, df=None
) -> float | None:
    """Interrupção de tratamento a partir de SITUA_ENCE (tuberculose).

    Três regras disponíveis — ver docs/contrato-dados.md, armadilha 4:

    ``paridade``
        Reproduz o dashboard em R: conta apenas o código 2 e usa todos os
        encerramentos no denominador. Confirmado pela responsável pelo painel
        em R em 20/ago/2026: "eu conto só o 2".
    ``ms``
        Indicador de monitoramento do Ministério: soma abandono (2) e abandono
        primário (10), e tira os não avaliados (0, 5, 7, 8) do denominador.
    ``boletim``
        Como a Tabela 9 do Boletim Epidemiológico apresenta: mesmo numerador
        que ``ms``, mas com todos os encerramentos no denominador.

    Filtra por **código**, nunca por rótulo: ``valor_lbl`` vem reagrupado e
    põe abandono, óbito e falência todos como "Desfavorável".
    """
    if esc.doenca != "TUBERCULOSE":
        return None

    regra = (regra or REGRA_INTERRUPCAO).strip().lower()
    if regra not in _ABANDONO:
        raise ValueError(
            f"Regra inválida: {regra!r}. Esperado uma de {sorted(_ABANDONO)}."
        )

    if df is None:
        df = leitura.variavel_sinan(esc, "SITUA_ENCE")
    if df.empty:
        return None

    abandono = float(df.loc[df["valor"].isin(_ABANDONO[regra]), "n"].sum())
    denominador = float(df.loc[~df["valor"].isin(_NAO_AVALIADOS[regra]), "n"].sum())
    return _div(abandono, denominador, 100)


def calcular_regiao(esc: Escopo, municipios: list[str]) -> Kpis:
    """KPIs de um conjunto de municípios — macrorregião ou região de saúde.

    Mesmas fórmulas de :func:`calcular`, sobre as somas municipais de
    `leitura.componentes_de_regiao`. Só o que a hanseníase exibe; os campos
    de TB ficam em ``None``.
    """
    from dataclasses import replace

    c = leitura.componentes_de_regiao(esc, municipios)
    if not c:
        return Kpis()
    # As proporções saem do mesmo caminho do estado e do município — um
    # `Escopo` com a lista de municípios da região faz `variavel_sinan` ler
    # a partição municipal e somar só eles.
    regiao = replace(esc, municipios=tuple(municipios))
    casos = c.get("casos_novos_ms")
    return Kpis(
        casos=_num(casos),
        cura=_num(c.get("casos_cura")),
        pop=_num(c.get("pop_total")),
        incid=_div(casos, c.get("pop_total"), POR_100K),
        casos_0_14=_num(c.get("casos_0_14_total")),
        pop_0_14=_num(c.get("pop_0_14_total")),
        taxa_det_0_14=_div(c.get("casos_0_14_total"), c.get("pop_0_14_total"), POR_100K),
        **proporcoes_hanseniase(regiao, c),
    )
