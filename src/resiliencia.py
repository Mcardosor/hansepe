"""Isolamento de falha por painel.

No Streamlit, exceção no corpo do script troca a **página inteira** pelo
traceback. Aconteceu de verdade: o ranking montava um escopo inválido no nível
de município e o dashboard sumia — mapa, KPIs, gráficos, tudo — restando uma
parede de stack trace. Ver o commit `a83d36b`.

Aquele defeito foi corrigido, mas a fragilidade é estrutural: qualquer recorte
com dado inesperado tem o mesmo poder. Num painel que vai ser demonstrado, um
gráfico quebrado precisa custar um gráfico, não a tela.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

#: Texto mostrado no lugar do painel que falhou. Não expõe a exceção: o
#: visitante não tem o que fazer com um `KeyError`, e o traceback completo vai
#: para o log do servidor, onde é útil.
AVISO = "Não foi possível montar este painel. Os demais seguem válidos."


def _avisar_streamlit(nome: str, erro: Exception) -> None:
    import streamlit as st

    st.warning(f"**{nome}** — {AVISO}", icon=":material/error_outline:")


@contextmanager
def painel(nome: str, *, avisar: Callable[[str, Exception], None] | None = None) -> Iterator[None]:
    """Contém a falha de um painel no próprio painel.

    ``avisar`` existe para o teste — em produção o padrão desenha o recado no
    lugar do painel que caiu.

    Captura ``Exception``, e **não** ``BaseException``, de propósito: o
    ``st.rerun()`` funciona levantando ``RerunException``, que herda de
    ``BaseException`` justamente para atravessar ``except Exception``. Ampliar
    esta captura engoliria toda a navegação por clique, sem erro nenhum
    aparecendo — o mapa simplesmente pararia de responder.
    """
    try:
        yield
    # `Exception` e não `BaseException`: a contenção é o objetivo, mas
    # `st.rerun()` levanta `RerunException`, que herda de `BaseException`
    # para atravessar daqui. Ampliar a captura mata a navegação por
    # clique sem erro nenhum aparecer.
    except Exception as erro:
        logger.exception("painel %r falhou", nome)
        (avisar or _avisar_streamlit)(nome, erro)
