"""Pacote de configuração da Hanseníase — Pernambuco.

Reconstrói o painel Shiny ``PE_HANSE_06_01`` da equipe parceira (inventário
em ``docs/inventario-painel-origem.md``). Só constantes: o core lê daqui
cores, rótulos, ordem dos KPIs, métricas do mapa e variáveis de composição.

**As fórmulas reproduzem o painel de origem**, para a paridade fechar — em
especial "casos novos" = ``casos_total`` do ``incidence``, que na extração da
hanseníase conta **todas as entradas** no registro (recidiva, transferência e
reingresso inclusive). A definição do Ministério (``MODOENTR = 1``) fica
documentada em ``docs/paridade-hanseniase.md`` como divergência conhecida.
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
}

ROTULOS = {
    "casos": "Casos novos",
    "obitos": "Óbitos",
    "cura": "Curas entre casos novos",
    "cura_pct": "Proporção de cura (%)",
    "pop": "População",
    "incid": "Taxa de detecção (por 100 mil hab.)",
    "mortalidade": "Taxa de mortalidade (por 100 mil hab.)",
    "letalidade": "Letalidade (%)",
    "casos_0_14": "Casos novos de 0 a 14 anos",
    "taxa_det_0_14": "Taxa de detecção 0–14 (por 100 mil hab.)",
    "prop_mb_pct": "Proporção multibacilar (%)",
    "prop_grau2_pct": "Proporção grau II no diagnóstico (%)",
}

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
}

#: Métricas que o mapa e o ranking sabem desenhar — os cinco clicáveis.
METRICAS_MAPA = ("incid", "taxa_det_0_14", "casos", "casos_0_14", "cura")

#: Métricas em que uma queda é boa.
BOM_SE_CAI = frozenset(
    {"casos", "obitos", "incid", "mortalidade", "letalidade",
     "casos_0_14", "taxa_det_0_14", "prop_grau2_pct"}
)

#: Métricas exibidas com casas decimais.
TAXAS = frozenset(
    {"incid", "mortalidade", "letalidade", "taxa_det_0_14",
     "cura_pct", "prop_mb_pct", "prop_grau2_pct"}
)

#: Rampa roxa do painel de origem, para as taxas de detecção.
_ROXOS = (
    "#EDE9FE", "#C4B5FD", "#A78BFA", "#8B5CF6",
    "#7C3AED", "#5B21B6", "#2D1B69",
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
    # baixa < 2 · média 2–10 · alta 10–20 · muito alta 20–40 · hiperendêmica ≥ 40
    "incid": (0, 2, 10, 20, 40),
    # baixa < 0,5 · média 0,5–2,5 · alta 2,5–5 · muito alta 5–10 · hiper ≥ 10
    "taxa_det_0_14": (0, 0.5, 2.5, 5, 10),
    # baixo < 5% · médio 5–10% · alto ≥ 10%
    "prop_grau2_pct": (0, 5, 10),
    "casos": (0, 5, 10, 25, 50, 100),
}


def cortes_fixos(metrica: str) -> tuple[float, ...] | None:
    return CORTES_FIXOS.get(metrica)


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
        "Casos novos por 100 mil habitantes, por município de residência. "
        "Como no painel de origem, 'casos novos' são todas as entradas no "
        "registro do ano — recidivas e transferências inclusive; pela "
        "definição do Ministério (só modo de entrada 'caso novo') a taxa "
        "fica cerca de 25% menor. Ver docs/paridade-hanseniase.md."
    ),
    "taxa_det_0_14": (
        "Casos de 0 a 14 anos por 100 mil habitantes dessa faixa. É o "
        "indicador de transmissão recente: criança com hanseníase significa "
        "contato próximo e contínuo com caso não tratado."
    ),
    "casos": "Entradas no registro ativo no ano, por município de residência.",
    "casos_0_14": "Entradas no registro ativo em menores de 15 anos.",
    "cura": (
        "Saídas por cura entre os casos diagnosticados no mesmo ano. Não é "
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
}


def descricao(metrica: str) -> str | None:
    return DESCRICOES.get(metrica)


#: Indicadores de qualidade do programa. Os da hanseníase (contatos
#: examinados, cura de coorte) precisam do microdado — fase 2.
INDICADORES_PROGRAMA = ()
