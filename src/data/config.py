"""Localização dos dados e constantes de domínio.

Os parquets não são versionados. A raiz é resolvida nesta ordem:

1. variável de ambiente ``SINAN_DATA_DIR``
2. ``data/`` na raiz do projeto (padrão)
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Raiz dos dados. Ver docstring do módulo para a ordem de resolução."""
    env = os.environ.get("SINAN_DATA_DIR", "").strip()
    return Path(env).resolve() if env else PROJECT_ROOT / "data"


def dashboard_dir() -> Path:
    """Diretório com os datasets parquet particionados."""
    return data_dir() / "parquet" / "dashboard"


def support_dir() -> Path:
    """Arquivos de apoio de PE (shapefiles e lookup de municípios)."""
    return data_dir() / "support"


# ---------------------------------------------------------------------------
# Doenças
# ---------------------------------------------------------------------------
# O código da doença muda entre datasets — ver docs/contrato-dados.md,
# armadilha 2. Este é o mapa canônico: a aplicação usa sempre a chave
# canônica e traduz na fronteira da query.

TUBERCULOSE = "TUBERCULOSE"
HANSENIASE = "HANSENIASE"
DENGUE = "DENGUE"
ZIKA = "ZIKA"

#: Código usado nos datasets do SINAN agregado
#: (``incidence``, ``incidence_0_14``, ``_cache_ts``, ``piramides``, ``cases_new``).
_COD_AGREGADO = {
    TUBERCULOSE: "TUBERCULOSE",
    HANSENIASE: "HANSENIASE",
    DENGUE: "DENG",
    ZIKA: "ZIKA",
}

#: Código usado em ``sinan_landing`` e ``sinan_dict``. Hanseníase é ``HANS`` aqui.
_COD_LANDING = {
    TUBERCULOSE: "TUBERCULOSE",
    HANSENIASE: "HANS",
    DENGUE: "DENG",
    ZIKA: "ZIKA",
}

#: Código usado nos datasets do SIM (``cache_ts_sim_obitos``, ``obitos_sim_faixa``).
#: Dengue é ``DENGUE`` aqui, não ``DENG``.
_COD_SIM = {
    TUBERCULOSE: "TUBERCULOSE",
    HANSENIASE: "HANSENIASE",
    DENGUE: "DENGUE",
    ZIKA: "ZIKA",
}

def cod_agregado(doenca: str) -> str:
    """Código da doença nos datasets do SINAN agregado."""
    return _COD_AGREGADO[_canon(doenca)]


def cod_landing(doenca: str) -> str:
    """Código da doença em ``sinan_landing`` / ``sinan_dict``."""
    return _COD_LANDING[_canon(doenca)]


def cod_sim(doenca: str) -> str:
    """Código da doença nos datasets do SIM."""
    return _COD_SIM[_canon(doenca)]


#: Sinônimos aceitos na entrada, mapeados para a chave canônica.
_SINONIMOS = {
    "TB": TUBERCULOSE,
    "TUBERCULOSIS": TUBERCULOSE,
    "TUBERCULOSE": TUBERCULOSE,
    "HANS": HANSENIASE,
    "HANSENIASE": HANSENIASE,
    "DENG": DENGUE,
    "DENGUE": DENGUE,
    "ZIKA": ZIKA,
}


def _canon(doenca: str) -> str:
    chave = str(doenca or "").strip().upper()
    if chave not in _SINONIMOS:
        raise ValueError(
            f"Doença desconhecida: {doenca!r}. Esperado um de {sorted(set(_SINONIMOS))}."
        )
    return _SINONIMOS[chave]


# ---------------------------------------------------------------------------
# Anos
# ---------------------------------------------------------------------------
#: Havia aqui `ANO_MIN = 2010`, `ANO_MIN_POR_DOENCA = {ZIKA: 2016}` e a função
#: `ano_min()`. Saíram em 2026-08-20: nada os lia. A faixa de anos vem de
#: `leitura.anos_disponiveis()`, que pergunta ao disco em vez de declarar.
#:
#: O fato que morava ali — zika só existe no SINAN a partir de 2016 — fica
#: registrado neste comentário e no histórico. Quando o pack de zika entrar, ele
#: declara a própria cobertura, que é onde isso pertence.
ANO_MAX = 2025

#: Zika só tem registro a partir de 2016.


# ---------------------------------------------------------------------------
# Níveis geográficos
# ---------------------------------------------------------------------------
NIVEIS = ("BR", "UF", "MUN")


# ---------------------------------------------------------------------------
# UF
# ---------------------------------------------------------------------------
#: Os dois primeiros dígitos do código IBGE do município identificam a UF.
#: Alguns datasets (``cases_new``, ``indicadores_tb_*``) só trazem o código do
#: município, então a UF precisa ser derivada daí.
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

CODIGO_POR_UF = {sigla: codigo for codigo, sigla in UF_POR_CODIGO.items()}

#: Nome por extenso, para rótulo lido por gente.
#:
#: A sigla serve para filtro e para o seletor, onde a lista precisa ser
#: escaneável. Na faixa de identificação, não: ali o escopo é lido de longe,
#: às vezes projetado, e "Amazonas" é melhor que "AM". Sem isto a faixa ficava
#: incoerente consigo mesma — mostrava o município por extenso ("Manaus") e a
#: UF em sigla.
NOME_POR_UF = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí",
    "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}


def codigo_uf(sigla: str) -> str:
    """Código IBGE de 2 dígitos a partir da sigla."""
    chave = str(sigla or "").strip().upper()
    if chave not in CODIGO_POR_UF:
        raise ValueError(f"UF desconhecida: {sigla!r}")
    return CODIGO_POR_UF[chave]
