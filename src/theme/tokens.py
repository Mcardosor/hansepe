"""Tokens de design.

Extraídos do dashboard em R, com três correções deliberadas — ver
docs/inventario-funcionalidades.md:

- alturas fixas viraram mínimos, para não quebrar em telas menores;
- escala tipográfica explícita, que o original não tinha;
- tema escuro, ausente no original.
"""

from __future__ import annotations

# --- Superfícies -----------------------------------------------------------
RAIO_CARD = "18px"
RAIO_PAINEL = "14px"
RAIO_PILL = "999px"

BORDA = "1px solid color-mix(in srgb, currentColor 14%, transparent)"
SOMBRA_REPOUSO = "0 10px 26px rgba(2,6,23,.08)"
SOMBRA_HOVER = "0 18px 44px rgba(2,6,23,.12)"
SOMBRA_ATIVO = "0 22px 56px rgba(2,6,23,.14)"

#: A superfície do card é derivada de `currentColor`, não declarada.
#:
#: Declarar "branco no claro, escuro no escuro" obriga o CSS a saber qual tema
#: está ativo — e não há como saber com segurança: `prefers-color-scheme` segue
#: o sistema operacional, não o Streamlit, e `st.context.theme` erra no
#: primeiro quadro e ao trocar de tema (issue #11920 do Streamlit). Misturando
#: a cor do texto com o fundo, a superfície acompanha o tema sozinha, porque
#: `currentColor` já vem invertido.
MISTURA_CARD = "4%"
MISTURA_CARD_TOPO = "7%"
# --- Tipografia ------------------------------------------------------------
FONTE = (
    "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, "
    "'Apple Color Emoji', 'Segoe UI Emoji', sans-serif"
)

#: Escala tipográfica. O original usava tamanhos avulsos; aqui há uma razão fixa.
#: Escala tipográfica, razão 1,2 a partir de 14px.
#:
#: Antes eram seis degraus, dos quais **dois nunca foram usados** — os
#: componentes contornavam com `font-size` fixo, e apareceram 11px, 12px e
#: 28px soltos no CSS. Uma escala que ninguém segue não é escala.
#:
#: Todo degrau declarado aqui é usado; acrescentar um pede um caso de uso,
#: não um espaço vago na régua — cheguei a declarar um 17px "para subtítulo
#: de painel" que nada usava, e o teste o pegou na mesma hora.
#: `tests/test_theme.py` confere as duas coisas.
TEXTO_XS = "12px"    # legenda, detalhe, rótulo de eixo, tooltip
TEXTO_SM = "14px"    # corpo
TEXTO_XL = "24px"    # valor de KPI e de indicador
#: O piso é 24px, e não 18px, para o título nunca ficar **menor que o valor
#: de um KPI** (`TEXTO_XL`). Com piso 18 isso acontecia em qualquer viewport
#: abaixo de ~1140px: o nome da doença encolhia enquanto os números dos cards
#: ficavam parados, e a página passava a ter a hierarquia invertida.
TEXTO_TITULO = "clamp(24px, 2.1vw, 30px)"

# --- Semântica -------------------------------------------------------------
BOM = "#16A34A"
RUIM = "#B42318"
NEUTRO_OPACIDADE = ".74"

#: Usados só onde a cor precisa ser absoluta (favicon, exportações).
TEXTO_CLARO = "#0B1220"
TEXTO_ESCURO = "#E5E7EB"

# --- Espaçamento e layout --------------------------------------------------
GAP = "12px"
PADDING = "12px"

#: Respiro da página, substituindo o padrão do Streamlit (`96px 80px 160px`).
#:
#: Aquele default é de página de documento, não de painel: 144px de nada antes
#: do título e 160px depois do último gráfico, num painel que o usuário abre
#: para ler números. Os 80px laterais custavam 160px de largura — e largura é
#: exatamente o que falta ao mapa, que não preenche a coluna.
#:
#: A base fica maior que o topo de propósito: o rodapé de procedência precisa
#: descolar do último painel para não parecer legenda dele.
PAGINA_TOPO = "40px"
PAGINA_LADOS = "40px"
PAGINA_BASE = "56px"

#: Abaixo disto o respiro lateral vira desperdício: em tela estreita cada pixel
#: de padding sai da largura do gráfico.
PAGINA_LADOS_ESTREITO = "16px"

#: No original eram alturas travadas (`height: 520px !important`). Viraram
#: mínimos para o layout sobreviver a telas baixas.
ALTURA_MIN_MAPA = "520px"
ALTURA_MIN_PAINEL = "560px"

# --- Gráficos --------------------------------------------------------------
TOOLTIP_FUNDO = "rgba(17,24,39,.96)"