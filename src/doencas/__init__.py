"""Pacotes de configuração por doença.

O core é único e a doença é configuração: cores, rótulos, ordem dos KPIs e
métricas do mapa saem de um módulo deste pacote, e o mapa, os gráficos e a
navegação nunca sabem que doença estão desenhando.

O pack em uso é resolvido nesta ordem:

1. o nome passado a :func:`carregar`
2. variável de ambiente ``SINAN_DOENCA``
3. ``tuberculose`` (padrão)

Env var e não parâmetro de URL porque o deploy é um container por painel — o
processo serve uma doença só, e o nome dela é do ambiente, não do visitante.
Um parâmetro de URL faria o pack mudar entre reruns do Streamlit, com o
``st.cache_resource`` da geometria já quente para a doença anterior.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from types import ModuleType

#: Pack usado quando ninguém pede outro.
PADRAO = "hanseniase"

#: O que o core lê de qualquer pack. É a lista de atributos que o ``app.py``
#: de fato consome — conferida no carregamento para que um pack incompleto
#: falhe aqui, com o nome do que falta, e não a meia tela de distância num
#: ``AttributeError`` dentro de um painel contido por `resiliencia.painel`.
CONTRATO = (
    "DOENCA",
    "TITULO",
    "LAYOUT_KPI",
    "FRACAO_KPI",
    "METRICAS_MAPA",
    "BOM_SE_CAI",
    "TAXAS",
    "INDICADORES_PROGRAMA",
    "ROTULOS_VALORES",
    "VARIAVEIS_NUMERICAS",
    "cor",
    "rampa_mapa",
    "rotulo",
    "rotulo_curto",
    "descricao",
    "grupo_da",
    "variaveis_planas",
)


def disponiveis() -> tuple[str, ...]:
    """Nomes dos packs presentes no pacote, em ordem alfabética."""
    return tuple(sorted(m.name for m in pkgutil.iter_modules(__path__)))


def carregar(nome: str | None = None) -> ModuleType:
    """Devolve o pack pedido. Ver docstring do módulo para a ordem de resolução.

    O nome é conferido contra `disponiveis` antes do import: o valor vem do
    ambiente, e ``importlib`` com string de fora importaria qualquer módulo
    alcançável.
    """
    nome = (nome or os.environ.get("SINAN_DOENCA", "")).strip() or PADRAO
    if nome not in disponiveis():
        raise ValueError(
            f"doença desconhecida: {nome!r}. "
            f"Disponíveis: {', '.join(disponiveis())}"
        )
    pack = importlib.import_module(f"{__name__}.{nome}")
    if faltando := [attr for attr in CONTRATO if not hasattr(pack, attr)]:
        raise AttributeError(
            f"o pack {nome!r} não cumpre o contrato: falta "
            f"{', '.join(faltando)}"
        )
    return pack
