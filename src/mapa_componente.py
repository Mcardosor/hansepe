"""O mapa como componente próprio do Streamlit — para a transição existir.

`st.pydeck_chart` recria o canvas do deck a cada rerun, e por isso a câmera
nunca teve de onde partir (`docs/mapa-clique.md`, "Transição"). Este módulo
serve `src/componente_mapa/` como componente estático: o iframe fica vivo
entre reruns, recebe o mesmo spec JSON que o pydeck produz e é o JavaScript
lá dentro (`mapa.js`) que chama `setProps` na instância viva — com
`FlyToInterpolator` para o enquadramento e `transitions` para as cores.

O clique volta como ``{"nonce", "properties"}``. O `nonce` muda a cada
clique, inclusive no mesmo polígono — é o que permite o clique repetido
abrir o modo detalhe sem o laço de rerun que a chave estável do
`st.pydeck_chart` provocava. Quem consome guarda o último nonce tratado em
`st.session_state` e ignora o valor enquanto ele não mudar.
"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

DIRETORIO = Path(__file__).resolve().parent / "componente_mapa"

#: Duração do voo entre enquadramentos, em ms. Acima de ~900 parece lentidão;
#: abaixo de ~400 não dá para acompanhar de onde veio.
TRANSICAO_MS = 700

#: Chaves das feições deste painel, na ordem de precedência.
CAMPOS_CLIQUE = ('cod_mun6', 'regiao', 'uf')

_componente = components.declare_component("mapa_deck", path=str(DIRETORIO))


def desenhar(mapa_deck, *, altura: int, key: str = "mapa", transicao: int = TRANSICAO_MS):
    """Renderiza o `pydeck.Deck` no componente e devolve o último clique.

    A ``key`` é **estável de propósito**: é ela que mantém o iframe — e a
    instância do deck — vivos entre reruns. Não inclua o recorte nela.
    """
    return _componente(
        spec=mapa_deck.to_json(),
        tooltip=getattr(mapa_deck, "_tooltip", None),
        altura=int(altura),
        transicao=int(transicao),
        key=key,
        default=None,
    )


def alvo_do_clique(
    evento, nonce_visto: str | None, campos: tuple[str, ...] = CAMPOS_CLIQUE
) -> tuple[str | None, str | None]:
    """``(chave clicada, nonce)`` se o evento é novo; ``(None, None)`` se não.

    ``campos`` são as chaves procuradas nas propriedades, na ordem do
    `mapa.alvo_do_clique` — a primeira que existir ganha.
    """
    if not isinstance(evento, dict):
        return None, None
    nonce = evento.get("nonce")
    if not nonce or nonce == nonce_visto:
        return None, None
    props = evento.get("properties")
    if not isinstance(props, dict):
        return None, nonce
    for campo in campos:
        if props.get(campo):
            return str(props[campo]), nonce
    return None, nonce
