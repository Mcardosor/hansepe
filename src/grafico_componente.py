"""Gráficos ECharts como componente próprio — para a transição existir.

O Altair redesenha do zero a cada rerun: o Vega-Lite não anima entre dois
estados. Este módulo serve `src/componente_grafico/` (ECharts 5 vendorado)
como componente estático: o iframe e a instância do gráfico ficam vivos
entre reruns, e cada render é um `setOption` — o ECharts interpola o que
mudou (barra crescendo, barra trocando de posição, linha se redesenhando).

A migração é gráfico a gráfico. O `graficos.py` Altair continua valendo
para o que ainda não passou; o que passou tem aqui uma função que devolve a
**opção** ECharts (um dict), e o `app.py` a entrega a :func:`desenhar`.

Regras da opção, para a animação funcionar:

- todo item de dado leva ``name``: é por ele que o ECharts casa o item
  antigo com o novo e anima a diferença;
- a série leva ``id`` fixo, pelo mesmo motivo;
- o clique volta como ``{"nonce", "name", "chave"}``, com nonce novo a cada
  clique (mesma regra do mapa — `mapa_componente`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

from .theme import componentes as ui
from .theme import tokens

DIRETORIO = Path(__file__).resolve().parent / "componente_grafico"

#: Durações da animação, em ms. Mais curtas que o voo do mapa (700): o
#: gráfico é secundário na leitura e não pode terminar depois dele.
ANIMACAO_ENTRADA_MS = 500
ANIMACAO_ATUALIZACAO_MS = 550

#: Fonte e tamanhos do tema do Altair (`graficos.tema`), para os dois
#: conviverem sem parecer duas famílias.
_FONTE_PX = 12
_COR_EIXO = "rgba(128,128,128,.35)"
_COR_GRADE = "rgba(128,128,128,.18)"

_componente = components.declare_component("grafico_echarts", path=str(DIRETORIO))


def desenhar(option: dict, *, altura: int, key: str):
    """Renderiza a opção ECharts e devolve o último clique (ou ``None``).

    A ``key`` é estável por gráfico — é ela que mantém a instância viva.
    """
    return _componente(
        option=json.dumps(option, ensure_ascii=False, default=_serializar),
        altura=int(altura),
        key=key,
        default=None,
    )


def _serializar(valor):
    """Números do numpy/pandas viram números; o resto, texto."""
    try:
        import numpy as np

        if isinstance(valor, np.generic):
            return valor.item()
    except ImportError:  # pragma: no cover
        pass
    if valor is pd.NA or (isinstance(valor, float) and valor != valor):
        return None
    return str(valor)


def alvo_do_clique(evento, nonce_visto: str | None) -> tuple[str | None, str | None]:
    """``(chave clicada, nonce)`` se o evento é novo; ``(None, None)`` se não."""
    if not isinstance(evento, dict):
        return None, None
    nonce = evento.get("nonce")
    if not nonce or nonce == nonce_visto:
        return None, None
    chave = evento.get("chave")
    if chave in (None, ""):
        chave = evento.get("name")
    return (str(chave) if chave not in (None, "") else None), nonce


def _base() -> dict:
    """O que todo gráfico ECharts daqui compartilha: fonte, animação, eixo."""
    return {
        "animationDuration": ANIMACAO_ENTRADA_MS,
        "animationDurationUpdate": ANIMACAO_ATUALIZACAO_MS,
        "animationEasingUpdate": "cubicOut",
        "textStyle": {"fontFamily": tokens.FONTE, "fontSize": _FONTE_PX},
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(17,24,39,.96)",
            "borderWidth": 0,
            "textStyle": {"color": "#fff", "fontSize": _FONTE_PX},
        },
    }


def ranking(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    escala=None,
    selecionado: str | None = None,
    largura_rotulo: int = 150,
) -> dict:
    """Barras horizontais das maiores geografias, clicáveis — em ECharts.

    Mesmas decisões do `graficos.ranking` Altair: horizontal, cor por classe
    do mapa quando há ``escala`` (a barra é da cor do polígono), legenda
    desligada porque a do mapa vale para os dois. O que muda é o que o
    ECharts dá de graça: ao mudar recorte, ano ou métrica, cada barra
    **desliza** para o valor e a posição novos, casada pelo nome.

    ``dados`` tem ``chave``, ``nome`` e ``valor``. A barra ``selecionado``
    (chave) fica opaca e as demais recuam — o destaque do mapa e do ranking
    é o mesmo.
    """
    opt = _base()
    if dados.empty:
        opt.update({
            "title": {
                "text": "Sem dados para ranquear neste recorte",
                "left": "center", "top": "middle",
                "textStyle": {"fontSize": _FONTE_PX, "fontWeight": "normal"},
            },
        })
        return opt

    ordenado = dados.sort_values(["valor", "nome"], ascending=[True, True])
    if escala is not None:
        from . import mapa

        classes = mapa.classificar(ordenado["valor"], escala)
        cores = [escala.cores.get(c, cor) for c in classes]
    else:
        cores = [cor] * len(ordenado)

    itens = []
    for (chave, nome, valor), tom in zip(
        ordenado[["chave", "nome", "valor"]].itertuples(index=False), cores, strict=True
    ):
        recuado = selecionado is not None and str(chave) != str(selecionado)
        itens.append({
            "name": str(nome),
            "value": None if pd.isna(valor) else float(valor),
            "chave": str(chave),
            "itemStyle": {"color": tom, "opacity": 0.55 if recuado else 1.0},
        })

    opt.update({
        "grid": {"left": largura_rotulo + 8, "right": 16, "top": 8, "bottom": 40},
        "xAxis": {
            "type": "value",
            "name": rotulo,
            "nameLocation": "middle",
            "nameGap": 26,
            "nameTextStyle": {"fontSize": _FONTE_PX},
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"lineStyle": {"color": _COR_EIXO}},
            "splitLine": {"lineStyle": {"color": _COR_GRADE}},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": {
            "type": "category",
            "data": [i["name"] for i in itens],
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {
                "fontSize": _FONTE_PX,
                "width": largura_rotulo,
                "overflow": "truncate",
            },
        },
        "series": [{
            "id": "ranking",
            "type": "bar",
            "data": itens,
            "barCategoryGap": "28%",
            "itemStyle": {"borderRadius": [0, 3, 3, 0]},
            "emphasis": {"itemStyle": {"opacity": 1.0}},
            "cursor": "pointer",
        }],
    })
    # O formato pt-BR (vírgula, uma casa) é montado no JavaScript a partir
    # deste rótulo: um `formatter` de texto do ECharts não formata número.
    opt["tooltip"]["rotuloValor"] = rotulo
    opt["tooltip"]["casas"] = 1
    return opt


def composicao(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    largura_rotulo: int = 220,
    ordem_dos_dados: bool = False,
) -> dict:
    """Distribuição de uma variável do SINAN, em barras horizontais — ECharts.

    Mesmas decisões do `graficos.composicao` Altair: percentual quando a base
    sustenta e contagem quando não (a decisão vem de `leitura.composicao`),
    ordem por frequência salvo variável numérica, o nome da variável como
    título. Ao mudar o recorte, cada categoria desliza para o valor novo —
    casada pelo nome —, e as dez do painel trocam juntas.

    O tooltip vem pronto de cada item (``tooltip``, HTML), formatado em
    pt-BR aqui: o ECharts não formata número por texto.
    """
    opt = _base()
    opt["title"] = {
        "text": rotulo,
        "left": 0,
        "top": 0,
        "textStyle": {"fontSize": 13, "fontWeight": 600},
    }
    if dados.empty:
        opt["title"] = {
            "text": "Sem registro desta variável no recorte",
            "left": "center", "top": "middle",
            "textStyle": {"fontSize": _FONTE_PX, "fontWeight": "normal"},
        }
        return opt

    base = dados.copy()
    percentual = "pct" in base.columns and base["pct"].notna().any()
    base["valor"] = pd.to_numeric(base["pct"] if percentual else base["n"], errors="coerce")
    titulo_x = "% dos casos" if percentual else "Casos"

    if not ordem_dos_dados:
        base = base.sort_values("valor", ascending=False)
    # Eixo de categoria cresce de baixo para cima: o primeiro da lista fica
    # embaixo, então a ordem de leitura se inverte aqui.
    base = base.iloc[::-1]

    itens = []
    for linha in base.itertuples(index=False):
        n = getattr(linha, "n", None)
        pct = getattr(linha, "pct", None)
        partes = [f"<b>{linha.categoria}</b>", f"Casos: <b>{ui.formatar_inteiro(None if pd.isna(n) else float(n))}</b>"]
        if percentual and pct is not None and not pd.isna(pct):
            partes.append(f"% dos casos: <b>{ui.formatar_decimal(float(pct), 1)}</b>")
        itens.append({
            "name": str(linha.categoria),
            "value": None if pd.isna(linha.valor) else float(linha.valor),
            "tooltip": "<br/>".join(partes),
        })

    opt.update({
        "grid": {"left": largura_rotulo + 8, "right": 16, "top": 34, "bottom": 40},
        "xAxis": {
            "type": "value",
            "name": titulo_x,
            "nameLocation": "middle",
            "nameGap": 26,
            "nameTextStyle": {"fontSize": _FONTE_PX},
            "splitNumber": 5,
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"lineStyle": {"color": _COR_EIXO}},
            "splitLine": {"lineStyle": {"color": _COR_GRADE}},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": {
            "type": "category",
            "data": [i["name"] for i in itens],
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {
                "fontSize": _FONTE_PX,
                "width": largura_rotulo,
                "overflow": "truncate",
            },
        },
        "series": [{
            "id": "composicao",
            "type": "bar",
            "data": itens,
            "barCategoryGap": "30%",
            "itemStyle": {"color": cor, "borderRadius": [0, 2, 2, 0]},
        }],
    })
    return opt


# ---------------------------------------------------------------------------
# Evolução temporal: canal endêmico, série anual e epicurva
# ---------------------------------------------------------------------------

#: Cores do canal, as mesmas do Altair (`graficos.py`): faixa azul-clara com
#: borda cinza-azulada, anos de referência numa rampa fria do mais antigo ao
#: mais recente, ano selecionado na cor da métrica.
SERIE_ATUAL = "Ano selecionado"
SERIE_Q1 = "Q1"
SERIE_Q3 = "Q3"
COR_FAIXA = "#CBDCEF"
COR_BORDA_FAIXA = "#8FA9C4"
RAMPA_REFERENCIA = ("#C3CBD4", "#A8B6C6", "#8C9FB8", "#6E88AA", "#4A78B0")

#: Nomes das duas séries mudas que desenham a faixa (ver `canal_endemico`).
_FAIXA_BASE = "\u200b"
_FAIXA_ALTURA = "\u200b\u200b"


def _eixo_valor(rotulo: str) -> dict:
    return {
        "type": "value",
        "name": rotulo,
        "nameLocation": "middle",
        "nameGap": 40,
        "nameTextStyle": {"fontSize": _FONTE_PX},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitLine": {"lineStyle": {"color": _COR_GRADE}},
        "axisLabel": {"fontSize": _FONTE_PX},
    }


def _eixo_categoria(rotulos: list[str]) -> dict:
    return {
        "type": "category",
        "data": rotulos,
        "boundaryGap": False,
        "axisLine": {"lineStyle": {"color": _COR_EIXO}},
        "axisTick": {"lineStyle": {"color": _COR_EIXO}},
        "axisLabel": {"fontSize": _FONTE_PX},
    }


def _valor(v) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def _recado(opt: dict, texto: str) -> dict:
    opt["title"] = {
        "text": texto,
        "left": "center", "top": "middle",
        "textStyle": {"fontSize": _FONTE_PX, "fontWeight": "normal"},
    }
    return opt


def canal_endemico(canal, *, rotulo: str, cor: str) -> dict:
    """Canal endêmico em ECharts: ano corrente sobre a faixa interquartil.

    A faixa é o truque que o painel de origem (também ECharts) usa: duas
    séries empilhadas — uma invisível no Q1 e outra com a altura Q3 − Q1 e
    área pintada —, porque a biblioteca não desenha área entre duas linhas
    arbitrárias. As duas ficam fora da legenda e do tooltip (`ocultas`).

    O que o ECharts dá em troca: ao mudar o recorte, a linha do ano e a faixa
    **deslizam** para os valores novos; os anos de referência entram e saem
    com transição. Séries com `id` fixo por papel (`atual`, `q1`, `q3`,
    `ref-<ano>`) para o casamento entre renders.

    Tooltip unificado por mês (trigger ``axis``), como no Altair: comparar
    março de 2024 com março de 2021 não pode depender de pontaria.
    """
    opt = _base()
    if getattr(canal, "vazio", True):
        return _recado(opt, "Sem série mensal para montar o canal")

    atual = canal.atual.sort_values("mes")
    meses = [str(m)[:3].capitalize() for m in atual["mes_nome"]]
    faixa = canal.faixa.set_index("mes").reindex(atual["mes"])
    anos = [int(a) for a in canal.anos]
    rampa = list(RAMPA_REFERENCIA[-len(anos):]) if anos else []

    q1 = [_valor(v) for v in faixa["q1"]]
    q3 = [_valor(v) for v in faixa["q3"]]
    altura_faixa = [
        None if a is None or b is None else max(b - a, 0.0)
        for a, b in zip(q1, q3, strict=True)
    ]

    series: list[dict] = [
        {
            "id": "faixa-base", "name": _FAIXA_BASE, "type": "line", "stack": "faixa",
            "data": q1, "symbol": "none", "lineStyle": {"opacity": 0},
            "silent": True, "z": 1,
        },
        {
            "id": "faixa", "name": _FAIXA_ALTURA, "type": "line", "stack": "faixa",
            "data": altura_faixa, "symbol": "none", "lineStyle": {"opacity": 0},
            "areaStyle": {"color": COR_FAIXA, "opacity": 0.85}, "silent": True, "z": 1,
        },
    ]
    for nome, dados_serie, ident in ((SERIE_Q1, q1, "q1"), (SERIE_Q3, q3, "q3")):
        series.append({
            "id": ident, "name": nome, "type": "line", "data": dados_serie,
            "symbol": "circle", "symbolSize": 4,
            "lineStyle": {"width": 1.5, "color": COR_BORDA_FAIXA},
            "itemStyle": {"color": COR_BORDA_FAIXA}, "z": 2,
        })
    if not canal.referencia.empty:
        for ano, tom in zip(anos, rampa, strict=True):
            grupo = (
                canal.referencia[canal.referencia["ano"] == ano]
                .set_index("mes").reindex(atual["mes"])
            )
            series.append({
                "id": f"ref-{ano}", "name": str(ano), "type": "line",
                "data": [_valor(v) for v in grupo["valor"]],
                "symbol": "none",
                "lineStyle": {"width": 1.3, "type": [4, 3], "color": tom},
                "itemStyle": {"color": tom}, "z": 3,
            })
    series.append({
        "id": "atual", "name": SERIE_ATUAL, "type": "line",
        "data": [_valor(v) for v in atual["valor"]],
        "symbol": "circle", "symbolSize": 7,
        "lineStyle": {"width": 2.8, "color": cor}, "itemStyle": {"color": cor}, "z": 5,
    })

    legenda = [SERIE_ATUAL, *[str(a) for a in anos], SERIE_Q1, SERIE_Q3]
    opt.update({
        "grid": {"left": 56, "right": 16, "top": 40, "bottom": 32},
        "legend": {
            "data": legenda, "top": 0, "left": 0, "icon": "roundRect",
            "itemWidth": 14, "itemHeight": 3, "textStyle": {"fontSize": _FONTE_PX},
        },
        "xAxis": _eixo_categoria(meses),
        "yAxis": _eixo_valor(rotulo),
        "series": series,
    })
    opt["tooltip"].update({
        "trigger": "axis",
        "axisPointer": {"type": "line", "lineStyle": {"color": "rgba(128,128,128,.55)"}},
        "ocultas": [_FAIXA_BASE, _FAIXA_ALTURA],
        "casas": 2,
    })
    return opt


def evolucao_anual(dados: pd.DataFrame, *, rotulo: str, cor: str, ano: int) -> dict:
    """Série histórica anual em barras, com o ano selecionado destacado."""
    opt = _base()
    if dados.empty:
        return _recado(opt, "Sem série histórica para este recorte")
    base = dados.sort_values("ano")
    itens = [
        {
            "name": str(int(a)), "value": _valor(v),
            "itemStyle": {"opacity": 1.0 if int(a) == int(ano) else 0.45},
        }
        for a, v in zip(base["ano"], base["valor"], strict=True)
    ]
    opt.update({
        "grid": {"left": 56, "right": 16, "top": 16, "bottom": 32},
        "xAxis": {
            "type": "category", "data": [i["name"] for i in itens],
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": _eixo_valor(rotulo),
        "series": [{
            "id": "anual", "type": "bar", "data": itens,
            "itemStyle": {"color": cor, "borderRadius": [3, 3, 0, 0]},
            "barCategoryGap": "25%",
        }],
    })
    opt["tooltip"].update({"rotuloValor": rotulo, "casas": 1})
    return opt


def epicurva(dados: pd.DataFrame, *, rotulo: str, cor: str, ano_em_foco: int | None = None) -> dict:
    """Série mensal contínua, atravessando os anos, com o ano em foco grosso.

    Eixo de tempo (não categoria): são ~180 pontos, e o ECharts escolhe os
    anos para rotular. O trecho do ano selecionado é uma segunda série sobre
    a primeira, mais grossa — ao trocar o ano, o destaque desliza.
    """
    opt = _base()
    if dados.empty:
        return _recado(opt, "Sem série mensal para este recorte")
    base = dados.sort_values(["ano", "mes"])

    def pontos(df: pd.DataFrame) -> list:
        return [
            [f"{int(a)}-{int(m):02d}-01", _valor(c)]
            for a, m, c in zip(df["ano"], df["mes"], df["casos"], strict=True)
        ]

    nome_foco = f"{rotulo} em {ano_em_foco}"
    series = [{
        "id": "serie", "name": rotulo, "type": "line", "data": pontos(base),
        "symbol": "circle", "symbolSize": 6, "showSymbol": False,
        "lineStyle": {"width": 1.6, "color": cor}, "itemStyle": {"color": cor},
    }]
    if ano_em_foco is not None:
        foco = base[base["ano"] == ano_em_foco]
        if not foco.empty:
            series.append({
                "id": "foco", "name": nome_foco, "type": "line", "data": pontos(foco),
                "symbol": "none", "lineStyle": {"width": 3, "color": cor},
                "itemStyle": {"color": cor}, "z": 3,
            })
    opt.update({
        "grid": {"left": 56, "right": 16, "top": 12, "bottom": 32},
        "xAxis": {
            "type": "time",
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"lineStyle": {"color": _COR_EIXO}},
            "axisLabel": {"fontSize": _FONTE_PX, "formatter": "{yyyy}"},
            "splitLine": {"show": False},
        },
        "yAxis": _eixo_valor(rotulo),
        "series": series,
    })
    opt["tooltip"].update({
        "trigger": "axis",
        "axisPointer": {"type": "line", "lineStyle": {"color": "rgba(128,128,128,.55)"}},
        "ocultas": [nome_foco],
        "casas": 0,
        "mesNoEixo": True,
    })
    return opt


# ---------------------------------------------------------------------------
# Pirâmide etária
# ---------------------------------------------------------------------------

#: Cores dos dois lados, as mesmas do Altair: deliberadamente não é rosa e
#: azul, e o azul da mortalidade já está tomado.
COR_HOMENS = "#1C5D99"
COR_MULHERES = "#B8860B"


def piramide(dados: pd.DataFrame, *, rotulo: str, por_100mil: bool = False) -> dict:
    """Pirâmide etária em ECharts: homens à esquerda, mulheres à direita.

    Escala única e simétrica, como no Altair: em tuberculose os homens somam
    quase o triplo das mulheres, e sem simetria o eixo cresce só para a
    esquerda e o excesso masculino — o achado — vira efeito de escala. Os
    valores dos homens vão negativos para ficarem à esquerda; o eixo e o
    tooltip mostram o módulo (`absoluto`, montado no JavaScript).

    Duas séries com `id` fixo (`homens`, `mulheres`), itens casados pela
    faixa etária: ao mudar o recorte, cada barra desliza para o valor novo.
    """
    opt = _base()
    if dados.empty:
        return _recado(opt, "Sem dado por faixa etária para este recorte")

    base = dados.copy()
    if por_100mil:
        pop = pd.to_numeric(base["pop"], errors="coerce")
        base["valor"] = (base["valor"] / pop * 100_000).where(pop > 0)
        base = base.dropna(subset=["valor"])
        if base.empty:
            return _recado(opt, "Sem população para calcular a taxa")
        rotulo = f"{rotulo} por 100 mil hab."
    casas = 1 if por_100mil else 0

    faixas = [f for _, f in sorted({(r.faixa_ord, r.faixa_etaria) for r in base.itertuples()})]
    por_sexo = {
        sexo: base[base["sexo"] == sexo].set_index("faixa_etaria")["valor"].reindex(faixas)
        for sexo in ("M", "F")
    }
    limite = float(pd.to_numeric(base["valor"], errors="coerce").abs().max() or 0) or 1.0

    def serie(ident, nome, sexo, cor, sinal):
        return {
            "id": ident, "name": nome, "type": "bar", "stack": "piramide",
            "data": [
                {"name": faixa, "value": None if pd.isna(v) else sinal * float(v)}
                for faixa, v in por_sexo[sexo].items()
            ],
            "itemStyle": {"color": cor},
            "barCategoryGap": "22%",
        }

    opt.update({
        "grid": {"left": 112, "right": 16, "top": 34, "bottom": 40},
        "legend": {
            "data": ["Homens", "Mulheres"], "top": 0, "left": 0,
            "icon": "roundRect", "itemWidth": 12, "itemHeight": 12,
            "textStyle": {"fontSize": _FONTE_PX},
        },
        "xAxis": {
            **_eixo_valor(rotulo),
            "min": -limite, "max": limite,
            "nameGap": 26,
            "absoluto": True,
        },
        "yAxis": {
            "type": "category",
            "data": faixas,
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {"fontSize": _FONTE_PX, "interval": 0},
        },
        "series": [
            serie("homens", "Homens", "M", COR_HOMENS, -1),
            serie("mulheres", "Mulheres", "F", COR_MULHERES, 1),
        ],
    })
    opt["tooltip"].update({"rotuloValor": rotulo, "casas": casas, "absoluto": True})
    return opt


# ---------------------------------------------------------------------------
# Barras empilhadas por ano com linha em eixo próprio (rodapé da hanseníase)
# ---------------------------------------------------------------------------


def barras_empilhadas_com_linha(
    dados: pd.DataFrame,
    *,
    barras: dict[str, str],
    linha: str,
    rotulo_linha: str,
    cores: dict[str, str],
    cor_linha: str,
    casas_linha: int = 1,
) -> dict:
    """Barras empilhadas por ano com uma linha em eixo próprio à direita.

    É o formato dos dois gráficos de rodapé do painel de origem: MB e PB
    empilhados com a proporção MB em linha; casos 0–14 com a taxa em linha.
    ``barras`` é ``coluna → rótulo``; ``linha`` é a coluna da linha. Séries
    com `id` fixo por coluna: ao mudar o recorte, barras e linha deslizam.
    """
    opt = _base()
    if dados.empty:
        return _recado(opt, "Sem série para este recorte")
    base = dados.sort_values("ano")
    anos = [str(int(a)) for a in base["ano"]]

    series = []
    for coluna, rotulo in barras.items():
        series.append({
            "id": f"barra-{coluna}", "name": rotulo, "type": "bar", "stack": "anos",
            "data": [{"name": a, "value": _valor(v)} for a, v in zip(anos, base[coluna], strict=True)],
            "itemStyle": {"color": cores[coluna]},
            "barCategoryGap": "30%",
        })
    # Só a última fatia da pilha leva o canto arredondado, senão cada fatia
    # fecha em arco e a pilha fica com "juntas".
    series[-1]["itemStyle"]["borderRadius"] = [2, 2, 0, 0]
    series.append({
        "id": "linha", "name": rotulo_linha, "type": "line", "yAxisIndex": 1,
        "data": [{"name": a, "value": _valor(v)} for a, v in zip(anos, base[linha], strict=True)],
        "symbol": "circle", "symbolSize": 6,
        "lineStyle": {"width": 2, "color": cor_linha}, "itemStyle": {"color": cor_linha},
        "z": 4,
    })

    opt.update({
        "grid": {"left": 56, "right": 64, "top": 40, "bottom": 32},
        "legend": {
            "data": [*barras.values(), rotulo_linha], "top": 0, "left": 0,
            "icon": "roundRect", "itemWidth": 12, "itemHeight": 12,
            "textStyle": {"fontSize": _FONTE_PX},
        },
        "xAxis": {
            "type": "category", "data": anos, "name": "Ano",
            "nameLocation": "middle", "nameGap": 22,
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": [
            _eixo_valor("Casos"),
            {**_eixo_valor(rotulo_linha), "position": "right", "splitLine": {"show": False}},
        ],
        "series": series,
    })
    opt["tooltip"].update({
        "trigger": "axis",
        "axisPointer": {"type": "shadow"},
        "ocultas": [],
        "casas": casas_linha,
        "casasPorSerie": {rotulo_linha: casas_linha, **{r: 0 for r in barras.values()}},
    })
    return opt
