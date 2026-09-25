"""Pacote de configuração da Hanseníase — Pernambuco.

Reconstrói o painel Shiny ``PE_HANSE_06_01`` da equipe parceira (inventário
em ``docs/inventario-painel-origem.md``). Só constantes: o core lê daqui
cores, rótulos, ordem dos KPIs, métricas do mapa e variáveis de composição.

**Casos novos e taxa de detecção seguem a definição do Ministério**
(``MODOENTR = 1``), decisão de 20/set/2026 — o painel de origem usa
``casos_total``, que na extração é toda entrada no registro (recidiva,
transferência e reingresso inclusive). Os demais números reproduzem a
origem. Ver ``docs/paridade-hanseniase.md`` §1.
"""

from __future__ import annotations

from ..theme import cores

DOENCA = "HANSENIASE"
TITULO = "Hanseníase"

#: Cor por **métrica**, não por doença — a decisão 6 da família. O cromo
#: institucional é o azul do RecifeTB; a semântica (detecção ocre, cura verde)
#: é a mesma dos outros painéis, para o leitor não reaprender a legenda.
CORES = {
    "primary": "#12346B",
    "secondary": "#1E73BE",
    "casos": "#C1440A",
    "obitos": "#DC2626",
    "cura": "#16A34A",
    "cura_pct": "#16A34A",
    "pop": "#6B7280",
    "incid": "#92400E",
    "mortalidade": "#1D4ED8",
    "letalidade": "#6D28D9",
    "casos_0_14": "#B45309",
    "taxa_det_0_14": "#B45309",
    # Roxos do painel de origem, para as duas proporções clínicas.
    "prop_mb_pct": "#6D28D9",
    "prop_grau2_pct": "#7C3AED",
    # Indicadores de qualidade do programa: cura verde e abandono ocre são a
    # semântica da família; contatos e GIF avaliado medem **cobertura**, e
    # ganham o azul-petróleo que nenhuma métrica de dano usa.
    "abandono_pct": "#B45309",
    "contatos_pct": "#0E7490",
    "gif_avaliado_pct": "#0369A1",
}

ROTULOS = {
    "casos": "Casos novos",
    "obitos": "Óbitos",
    "cura": "Curas",
    "pop": "População",
    "incid": "Taxa de detecção (por 100 mil hab.)",
    "mortalidade": "Taxa de mortalidade (por 100 mil hab.)",
    "letalidade": "Letalidade (%)",
    "casos_0_14": "Casos novos de 0 a 14 anos",
    "taxa_det_0_14": "Taxa de detecção 0–14 (por 100 mil hab.)",
    # Nomes como o painel de origem escreve nos cards.
    "prop_mb_pct": "Proporção multibacilar (MB)",
    "prop_grau2_pct": "Proporção grau II (diagnóstico)",
    # Nomes como o Boletim Epidemiológico de Hanseníase (SES-PE) escreve.
    "cura_pct": "Proporção de cura",
    "abandono_pct": "Proporção de abandono",
    "contatos_pct": "Contatos examinados",
    "gif_avaliado_pct": "GIF avaliado no diagnóstico",
}

#: De onde vêm os parâmetros de classificação exibidos na tela. Pedido da
#: reunião de 22/set/2026: a legenda precisa dizer que régua está usando.
FONTE_PARAMETROS = (
    "Parâmetros do Boletim Epidemiológico de Hanseníase — "
    "SES-PE/SEVSAP, 2025 (dados tabulados em 16/04/2025)"
)

#: Os quadros de parâmetros do boletim, **palavra por palavra**, para irem
#: ao lado do gráfico como lá. Título e linhas na ordem em que o boletim
#: escreve — do mais grave para o menos, o contrário da legenda do mapa.
#:
#: Copiar o texto em vez de gerá-lo a partir de `CORTES_FIXOS` é deliberado:
#: é citação de documento. O teste de paridade confere que os dois dizem a
#: mesma coisa, então divergir exige mexer nos dois lugares.
TEXTO_PARAMETROS: dict[str, tuple[str, tuple[str, ...]]] = {
    "incid": (
        "Coeficiente de detecção geral",
        (
            "Hiperendêmico: >40,0/100 mil hab.",
            "Muito alto: 20,00 a 39,99/100 mil hab.",
            "Alto: 10,00 a 19,99/100 mil hab.",
            "Médio: 2,00 a 9,99/100 mil hab.",
            "Baixo: < 2,00/100 mil hab.",
        ),
    ),
    "taxa_det_0_14": (
        "Coeficiente de detecção <15 anos",
        (
            "Hiperendêmico: ≥10,00 por 100 mil hab.",
            "Muito alto: 5,00 a 9,99 por 100 mil hab.",
            "Alto: 2,50 a 4,99 por 100 mil hab.",
            "Médio: 0,50 a 2,49 por 100 mil hab.",
            "Baixo: < 0,50 por 100 mil hab.",
        ),
    ),
    "prop_grau2_pct": (
        "% GIF II",
        ("Baixo < 5%", "Médio 5 a 9,99%", "Alto ≥ 10%"),
    ),
    "cura_pct": (
        "% Cura",
        ("Bom ≥ 90%", "Regular ≥ 75 a 89,9%", "Precário < 75%"),
    ),
    "abandono_pct": (
        "% Abandono",
        ("Bom < 10 %", "Regular =10-25%", "Precário > 25%"),
    ),
    "contatos_pct": (
        "% Contatos examinados",
        ("Bom ≥ 90%", "Regular ≥ 75 a 89,9%", "Precário < 75%"),
    ),
    "gif_avaliado_pct": (
        "% Grau de incapacidade",
        ("Bom ≥ 90%", "Regular ≥ 75 a 89,9%", "Precário < 75%"),
    ),
}


def texto_parametros(metrica: str) -> tuple[str, tuple[str, ...]] | None:
    """(título, linhas) do quadro do boletim, ou ``None`` quando não há."""
    return TEXTO_PARAMETROS.get(metrica)


#: Os quatro indicadores de qualidade do programa, na ordem da Tabela 2 do
#: boletim. Não entram na faixa de KPIs nem no mapa: têm seção própria.
INDICADORES_QUALIDADE = (
    "cura_pct",
    "contatos_pct",
    "gif_avaliado_pct",
    "abandono_pct",
)

#: Os cinco cards clicáveis do painel de origem, na ordem de lá, e as duas
#: proporções que lá são cards fixos.
LAYOUT_KPI = (
    "incid",
    "taxa_det_0_14",
    "casos",
    "casos_0_14",
    "cura",
    "prop_mb_pct",
    "prop_grau2_pct",
)

#: Fração exibida sob o valor do card, saída da mesma conta que o percentual.
FRACAO_KPI = {
    "prop_mb_pct": ("multibacilares", "classificados"),
    "prop_grau2_pct": ("grau2", "avaliacao_base"),
    "cura_pct": ("cura_encerrada", "encerramentos"),
    "abandono_pct": ("abandonos", "saidas"),
    "contatos_pct": ("contatos_examinados", "contatos_registrados"),
    "gif_avaliado_pct": ("gif_avaliados", "gif_base"),
}

#: Métricas que o mapa e o ranking sabem desenhar — os cinco clicáveis.
METRICAS_MAPA = ("incid", "taxa_det_0_14", "casos", "casos_0_14", "cura")

#: Métricas em que uma queda é boa.
BOM_SE_CAI = frozenset(
    {"casos", "obitos", "incid", "mortalidade", "letalidade",
     "casos_0_14", "taxa_det_0_14", "prop_grau2_pct", "abandono_pct"}
)

#: Métricas exibidas com casas decimais.
TAXAS = frozenset(
    {"incid", "mortalidade", "letalidade", "taxa_det_0_14",
     "cura_pct", "prop_mb_pct", "prop_grau2_pct",
     "abandono_pct", "contatos_pct", "gif_avaliado_pct"}
)

#: Rampa roxa do painel de origem, para as taxas de detecção.
#:
#: O primeiro tom era ``#EDE9FE``, quase branco: no tema claro os municípios
#: de classe "Baixo" sumiam no fundo da página e o mapa parecia furado.
#: A rampa foi levantada em 25/set/2026 para começar num lilás que se lê
#: sobre branco, mantendo a progressão até o roxo quase preto do topo.
_ROXOS = (
    "#DCD3FA", "#C7B8F7", "#AE99F2", "#9173E8",
    "#7A56DA", "#5B34B4", "#3B1E7A",
)

PALETA_MAPA = {
    "incid": _ROXOS,
    "taxa_det_0_14": _ROXOS,
    "casos": (
        "#F5A878", "#EF8450", "#E56028", "#D04010",
        "#B82E08", "#921800", "#5E0C00",
    ),
}


def cor(metrica: str) -> str:
    return CORES.get(metrica, CORES["secondary"])


ROTULOS_CURTOS = {
    # A unidade fica na legenda do mapa e no título do card completo; aqui é
    # botão, e cinco botões precisam caber numa linha.
    "incid": "Detecção",
    "taxa_det_0_14": "Detecção 0–14",
    "casos": "Casos novos",
    "casos_0_14": "Casos 0–14",
    "cura": "Curas",
    "prop_mb_pct": "Multibacilar",
    "prop_grau2_pct": "Grau II",
    "cura_pct": "Cura",
    "abandono_pct": "Abandono",
    "contatos_pct": "Contatos examinados",
    "gif_avaliado_pct": "GIF avaliado",
}


def rotulo(metrica: str) -> str:
    return ROTULOS.get(metrica, metrica)


def rotulo_curto(metrica: str) -> str:
    return ROTULOS_CURTOS.get(metrica, rotulo(metrica))


def rampa_mapa(metrica: str) -> list[str]:
    explicita = PALETA_MAPA.get(metrica)
    return list(explicita) if explicita else cores.rampa(cor(metrica))


#: Cortes da **escala fixa** do mapa — os parâmetros oficiais de endemicidade
#: do Ministério da Saúde, por município. É a régua que não muda de ano para
#: ano, e a que o painel de origem não tem.
CORTES_FIXOS = {
    # Baixo < 2,00 · Médio 2,00–9,99 · Alto 10,00–19,99 ·
    # Muito alto 20,00–39,99 · Hiperendêmico > 40,00 (Gráfico 1 do boletim)
    "incid": (0, 2, 10, 20, 40),
    # Baixo < 0,50 · Médio 0,50–2,49 · Alto 2,50–4,99 ·
    # Muito alto 5,00–9,99 · Hiperendêmico ≥ 10,00 (Gráfico 2)
    "taxa_det_0_14": (0, 0.5, 2.5, 5, 10),
    # Baixo < 5% · Médio 5–9,99% · Alto ≥ 10% (Gráfico 12)
    "prop_grau2_pct": (0, 5, 10),
    # Precário < 75% · Regular 75–89,9% · Bom ≥ 90% (Gráficos 10, 11 e 13)
    "cura_pct": (0, 75, 90, 100),
    "contatos_pct": (0, 75, 90, 100),
    "gif_avaliado_pct": (0, 75, 90, 100),
    # Bom < 10% · Regular 10–25% · Precário > 25% (Gráfico 13)
    "abandono_pct": (0, 10, 25, 100),
    "casos": (0, 5, 10, 25, 50, 100),
}


#: Nome de cada classe da escala fixa, na ordem dos cortes — é como o
#: Ministério chama as faixas, e é o que a legenda mostra ao lado do número.
#: No masculino, como o boletim escreve — a concordância é com
#: "coeficiente", não com "taxa".
NOMES_FIXOS = {
    "incid": ("Baixo", "Médio", "Alto", "Muito alto", "Hiperendêmico"),
    "taxa_det_0_14": ("Baixo", "Médio", "Alto", "Muito alto", "Hiperendêmico"),
    "prop_grau2_pct": ("Baixo", "Médio", "Alto"),
    "cura_pct": ("Precário", "Regular", "Bom"),
    "contatos_pct": ("Precário", "Regular", "Bom"),
    "gif_avaliado_pct": ("Precário", "Regular", "Bom"),
    "abandono_pct": ("Bom", "Regular", "Precário"),
}


def cortes_fixos(metrica: str) -> tuple[float, ...] | None:
    return CORTES_FIXOS.get(metrica)


def nomes_fixos(metrica: str) -> tuple[str, ...] | None:
    return NOMES_FIXOS.get(metrica)


def classe_de(metrica: str, valor: float | None) -> str | None:
    """Em que classe do boletim o valor cai — "Alto", "Precário"…

    ``None`` quando a métrica não tem régua oficial ou o valor não existe.
    O último corte é o teto da escala e não delimita classe: um valor igual
    ou acima do penúltimo já é a classe de cima.
    """
    cortes, nomes = CORTES_FIXOS.get(metrica), NOMES_FIXOS.get(metrica)
    if valor is None or not cortes or not nomes:
        return None
    for i, nome in enumerate(nomes):
        if i + 1 >= len(nomes) or float(valor) < cortes[i + 1]:
            return nome
    return nomes[-1]


ICONES_KPI = {
    "incid": '<path d="M12 14l3.5-5"/><path d="M4 18a8 8 0 1 1 16 0"/>',
    "taxa_det_0_14": '<path d="M12 14l3.5-5"/><path d="M4 18a8 8 0 1 1 16 0"/>',
    "casos": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "casos_0_14": '<circle cx="9" cy="7" r="3"/><path d="M3 20a6 6 0 0 1 12 0"/><circle cx="17" cy="9" r="2"/><path d="M15 20a4 4 0 0 1 6-3"/>',
    "cura": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "prop_mb_pct": '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "prop_grau2_pct": '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
}


def icone(metrica: str) -> str:
    return ICONES_KPI.get(metrica, "")


#: Rótulos que o ``sinan_dict`` da hanseníase não traz. Fonte: dicionário de
#: dados da ficha de notificação/investigação de hanseníase do SINAN.
ROTULOS_VALORES: dict[str, dict[str, str]] = {
    "FORMACLINI": {
        "1": "Indeterminada",
        "2": "Tuberculoide",
        "3": "Dimorfa",
        "4": "Virchowiana",
        "5": "Não classificada",
    },
    "EPIS_RACIO": {
        "1": "Reação tipo 1",
        "2": "Reação tipo 2",
        "3": "Reação tipo 1 e 2",
        "4": "Sem reação",
    },
}

#: Variáveis numéricas da ficha: o valor **é** a quantidade (contatos, nervos,
#: doses), não um código. O painel de composição as mostra como estão, em
#: ordem numérica, sem procurar rótulo.
VARIAVEIS_NUMERICAS = frozenset({"CONTEXAM", "CONTREG", "NERVOSAFET", "DOSE_RECEB"})

#: Variáveis do SINAN oferecidas no painel de composição, agrupadas.
#:
#: O painel de origem mostra as 23 do ``sinan_landing`` sem curadoria. Ficam
#: de fora, de propósito: ``NDUPLIC_N`` e ``IN_VINCULA`` (controle do
#: sistema, 100% num valor), ``UFATUAL``/``UFRESAT`` (quase 100% PE),
#: ``DTMUDESQ`` (uma barra por data) e ``CLASSATUAL``/``ESQ_ATU_N``/
#: ``AVAL_ATU_N`` (situação atual, redundante com a do diagnóstico e pior
#: preenchida — 804 contra 2.322 em 2024).
VARIAVEIS: dict[str, dict[str, str]] = {
    "Clínica e diagnóstico": {
        "CLASSOPERA": "Classificação operacional no diagnóstico",
        "FORMACLINI": "Forma clínica",
        "AVALIA_N": "Grau de incapacidade no diagnóstico",
        "BACILOSCOP": "Baciloscopia",
        "NERVOSAFET": "Nº de nervos afetados",
        "EPIS_RACIO": "Reação hansênica",
    },
    "Entrada e tratamento": {
        "MODOENTR": "Modo de entrada",
        "MODODETECT": "Modo de detecção do caso novo",
        "ESQ_INI_N": "Esquema terapêutico inicial",
        "DOSE_RECEB": "Nº de doses supervisionadas",
        "TPALTA_N": "Tipo de saída",
    },
    "Contatos": {
        "CONTREG": "Nº de contatos registrados",
        "CONTEXAM": "Nº de contatos examinados",
    },
    "Perfil": {
        "CS_RACA": "Raça/cor",
        "CS_ESCOL_N": "Escolaridade",
        "CS_GESTANT": "Gestante",
    },
}

#: As que abrem de saída — o que a vigilância da hanseníase olha primeiro.
VARIAVEIS_DESTAQUE = (
    "CLASSOPERA",
    "AVALIA_N",
    "FORMACLINI",
    "MODOENTR",
    "TPALTA_N",
    "CS_RACA",
)


def variaveis_planas() -> dict[str, str]:
    return {c: r for grupo in VARIAVEIS.values() for c, r in grupo.items()}


def grupo_da(codigo: str) -> str:
    for grupo, itens in VARIAVEIS.items():
        if codigo in itens:
            return grupo
    return "Outras"


#: Explicação de cada KPI, mostrada ao passar o cursor. O que se explica é o
#: **denominador** — e onde a conta difere da do Ministério.
DESCRICOES = {
    "incid": (
        "Casos novos por 100 mil habitantes, por município de residência — "
        "a definição do Ministério da Saúde: só o modo de entrada 'caso "
        "novo'. O painel de origem conta todas as entradas no registro "
        "(recidivas e transferências inclusive) e por isso mostra uma taxa "
        "cerca de 30% maior. Ver docs/paridade-hanseniase.md."
    ),
    "taxa_det_0_14": (
        "Casos de 0 a 14 anos por 100 mil habitantes dessa faixa. É o "
        "indicador de transmissão recente: criança com hanseníase significa "
        "contato próximo e contínuo com caso não tratado."
    ),
    "casos": (
        "Casos novos (modo de entrada 'caso novo') no ano, por município de "
        "residência. Recidivas, transferências e reingressos não contam."
    ),
    "casos_0_14": (
        "Entradas no registro ativo em menores de 15 anos. Aqui não dá para "
        "separar caso novo de reingresso — a extração não cruza idade com "
        "modo de entrada; a diferença é pequena nessa faixa."
    ),
    "cura": (
        "Saídas por cura entre todos os casos do ano. Não é "
        "coorte: o tratamento leva 6 (PB) ou 12 (MB) meses, então o número "
        "do ano corrente é sempre baixo e sobe nas extrações seguintes."
    ),
    "prop_mb_pct": (
        "Multibacilares sobre os casos com classificação operacional "
        "preenchida (PB + MB)."
    ),
    "prop_grau2_pct": (
        "Casos com grau 2 de incapacidade sobre os casos com o campo de "
        "avaliação preenchido — grau 0, 1, 2 e 'não avaliado', como no painel "
        "de origem. O Ministério usa só os avaliados (grau 0, 1 e 2) no "
        "denominador, o que dá cerca de 2 pontos a mais."
    ),
    "pop": "População estimada do recorte.",
    "cura_pct": (
        "Saídas por cura sobre todas as saídas registradas no ano de "
        "diagnóstico. Parâmetros do boletim: Bom ≥ 90%, Regular 75–89,9%, "
        "Precário < 75%. O boletim calcula por coorte (PB do ano anterior, "
        "MB de dois anos antes), que exige o microdado: em PE 2024 esta "
        "aproximação dá 67,1% contra 65,0% publicados."
    ),
    "abandono_pct": (
        "Saídas por abandono sobre todas as saídas registradas. Parâmetros: "
        "Bom < 10%, Regular 10–25%, Precário > 25%. Mesma aproximação de "
        "coorte da cura — 12,2% aqui contra 13,5% no boletim de 2024."
    ),
    "contatos_pct": (
        "Contatos examinados sobre contatos registrados dos casos do ano — "
        "os dois campos guardam quantidades, e a conta é a soma de um sobre "
        "a soma do outro. Parâmetros: Bom ≥ 90%, Regular 75–89,9%, Precário "
        "< 75%. Em PE 2024: 81,6% aqui contra 77,3% no boletim, que usa a "
        "coorte de casos novos."
    ),
    "gif_avaliado_pct": (
        "Casos com grau de incapacidade física avaliado no diagnóstico "
        "(grau 0, I ou II) sobre o total de casos. Mede **cobertura da "
        "avaliação**, não dano. Parâmetros: Bom ≥ 90%, Regular 75–89,9%, "
        "Precário < 75%. Em PE 2024: 82,7% aqui contra 83,6% no boletim."
    ),
}


def descricao(metrica: str) -> str | None:
    return DESCRICOES.get(metrica)


#: Indicadores de qualidade do programa. Os da hanseníase (contatos
#: examinados, cura de coorte) precisam do microdado — fase 2.
INDICADORES_PROGRAMA = ()
