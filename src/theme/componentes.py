"""Componentes visuais em HTML, para injetar no Streamlit.

O CSS sai uma vez por sessão (:func:`css_base`); os componentes só emitem
marcação. A cor de cada card entra por variável CSS inline, então um único
bloco de estilo serve todas as métricas e todas as doenças.
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

from . import cores

from . import tokens


def css_base() -> str:
    """Folha de estilo da aplicação. Injetar uma única vez, no início da página."""
    return f"""
<style>
/* As superfícies são derivadas de `currentColor`, nunca declaradas.
 *
 * Um tema claro e um escuro exigiriam saber qual está ativo, e não há como
 * saber com segurança: `prefers-color-scheme` segue o sistema operacional, e
 * não o Streamlit — com o tema forçado para claro em `.streamlit/config.toml`
 * e o sistema em escuro, os cards ficariam escuros sobre uma página clara.
 * `st.context.theme` também não serve: erra no primeiro quadro e ao trocar de
 * tema (issue #11920 do Streamlit).
 *
 * Misturando a cor do texto com o fundo, a superfície acompanha o tema
 * sozinha — `currentColor` já vem invertido pelo Streamlit. Um só bloco de
 * CSS serve os dois temas, sem detecção nenhuma. */
:root {{
  --fonte: {tokens.FONTE};
  --borda: {tokens.BORDA};
  --sombra: {tokens.SOMBRA_REPOUSO};
  --sombra-hover: {tokens.SOMBRA_HOVER};
  --sombra-ativo: {tokens.SOMBRA_ATIVO};
  --superficie: color-mix(in srgb, currentColor {tokens.MISTURA_CARD}, transparent);
  --superficie-topo: color-mix(in srgb, currentColor {tokens.MISTURA_CARD_TOPO}, transparent);
}}

/* Havia aqui `.kpi-grid`, um grid CSS com quebras em 1240, 860 e 460px, e a
 * função `grade_kpis()` que o emitia. Saíram em 2026-08-20 sem uso: os cards
 * são dispostos por `st.columns` desde que os botões de navegação entraram, e
 * quem os faz quebrar é a regra `stHorizontalBlock:has(.kpi-card)` em
 * `css_layout`. O grid ficou declarado e nunca emitido. */

.kpi-card {{
  --kpi-accent: #0F766E;
  position: relative;
  overflow: hidden;
  border-radius: {tokens.RAIO_CARD};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: var(--sombra);
  color: inherit;
  font-family: var(--fonte);
  transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}}
.kpi-card::after {{
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: {tokens.RAIO_CARD};
  opacity: 0;
  pointer-events: none;
  transition: opacity .14s ease;
  background:
    radial-gradient(220px 120px at 15% 10%,
      color-mix(in srgb, var(--kpi-accent) 22%, transparent), transparent 65%),
    radial-gradient(220px 120px at 85% 0%,
      color-mix(in srgb, var(--kpi-accent) 8%, transparent), transparent 55%);
}}
.kpi-card:hover {{
  border-color: color-mix(in srgb, currentColor 24%, transparent);
  box-shadow: var(--sombra-hover);
}}
.kpi-card:hover::after {{ opacity: 1; }}
.kpi-card.is-selected {{
  border-color: color-mix(in srgb, var(--kpi-accent) 60%, transparent);
  box-shadow: var(--sombra-ativo),
              0 0 0 2px color-mix(in srgb, var(--kpi-accent) 28%, transparent);
}}
.kpi-card.is-selected::after {{ opacity: 1; }}
.kpi-card:focus-visible {{
  outline: none;
  border-color: color-mix(in srgb, var(--kpi-accent) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--kpi-accent) 35%, transparent),
              var(--sombra-hover);
}}

.kpi-inner {{
  position: relative;
  z-index: 1;
  display: flex;
  gap: {tokens.GAP};
  align-items: center;
  padding: {tokens.PADDING};
  min-width: 0;
}}
.kpi-accent {{
  flex: 0 0 auto;
  width: 9px;
  height: 46px;
  border-radius: {tokens.RAIO_PILL};
  background: var(--kpi-accent);
}}
.kpi-text {{ min-width: 0; flex: 1 1 auto; }}
/* Disco do ícone, no canto superior direito. Fundo é a cor da métrica bem
   diluída e o traço é a cor cheia — o mesmo par da barra de acento, para o
   card continuar tendo uma cor só.

   Posicionado, e não na linha do flex: como coluna ele tirava 46px de
   largura de **todas** as linhas de texto, e o subtítulo "Recife • 2023 •
   351 de 2.018" virava reticências até em 1600px. No canto, só o título
   cede espaço (`padding-right`), e o valor, curto, passa por baixo. */
.kpi-icon {{
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--kpi-accent);
  background: color-mix(in srgb, var(--kpi-accent) 12%, transparent);
}}
.kpi-icon svg {{ width: 16px; height: 16px; }}
.kpi-card:has(.kpi-icon) .kpi-title {{ padding-right: 34px; }}
/* Uma linha, com reticências como último recurso.
   
   Duas linhas era o desenho anterior, e existia porque o rótulo completo
   ("Taxa de mortalidade (por 100 mil hab.)") não cabia em uma. A solução
   passou a ser outra: `pack.rotulo_curto` encurta o **texto**, e aí uma linha
   basta — os seis KPIs cabem numa faixa só, como no painel de origem, sem o
   corte que lá transforma "Taxa de mortalidade" em "Taxa de mort...".
   
   As reticências continuam declaradas para o caso de um rótulo novo passar do
   tamanho: cortar é melhor que empurrar o valor para baixo e desalinhar a
   faixa inteira. O nome completo vive no `title` do card. */
.kpi-title {{
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 3px;
  line-height: 1.25;
  min-height: 1.25em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
/* O acento se ajusta ao tema sem media query. `prefers-color-scheme` segue o
   sistema operacional, e não o tema do Streamlit — com o app em claro e o
   sistema em escuro, pintaria o acento errado.
   Misturar com `currentColor` resolve pela própria página: no tema claro o
   texto é escuro e a cor escurece de leve; no escuro o texto é claro e ela
   clareia. Cinco métricas ficavam abaixo do mínimo de 3:1 para texto grande
   no fundo escuro — `incid`, a padrão, em 2,6. */
.kpi-value {{
  font-size: {tokens.TEXTO_XL};
  font-weight: 900;
  letter-spacing: -.2px;
  line-height: 1.03;
  color: color-mix(in srgb, var(--kpi-accent) 72%, currentColor 28%);
}}
.kpi-sub {{
  font-size: {tokens.TEXTO_XS};
  opacity: .70;
  margin-top: 3px;
  /* Reserva exatamente uma linha, mesmo vazia: div sem conteúdo colapsa para
     zero e o desalinhamento voltaria.
     `line-height` e `min-height` são declarados juntos e com o mesmo valor de
     propósito — separados, eles divergem. A primeira tentativa usou 1.15em
     contra um line-height herdado de 1.6, e sobraram 5px de desalinhamento. */
  line-height: 1.6;
  min-height: 1.6em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.kpi-delta {{ margin-top: 5px; font-size: {tokens.TEXTO_XS}; font-weight: 800; }}
.kpi-bom  {{ color: {tokens.BOM}; }}
.kpi-ruim {{ color: {tokens.RUIM}; }}
.kpi-igual {{ opacity: {tokens.NEUTRO_OPACIDADE}; }}

/* Conteúdo redesenhado entra com fade, em vez de piscar no lugar.

   Isto só passou a fazer sentido depois dos fragmentos. Antes, qualquer
   clique redesenhava a página inteira e um fade universal seria ruído — tudo
   pulsando a cada interação. Agora só o painel que mudou é reconstruído, e o
   fade vira **informação**: marca onde a mudança aconteceu, que é o que a
   pessoa quer saber ao mexer num controle.

   180ms é curto de propósito. Acima de ~250ms a animação deixa de suavizar e
   passa a parecer lentidão, e este painel responde em menos de 20ms na camada
   de dados — não há espera real a disfarçar.

   Sem `transform`: mover o gráfico ao aparecer disputaria com a leitura do
   eixo. Só opacidade. */
@keyframes sinan-surgir {{
  from {{ opacity: 0; }}
  to   {{ opacity: 1; }}
}}
[data-testid="stVegaLiteChart"] {{
  animation: sinan-surgir .18s ease-out;
}}

/* O mapa entra crescendo de leve, e só ele.

   Ao navegar de Brasil para um estado, o Streamlit **remonta** o widget: a
   chave inclui `nivel` e `uf`. O Brasil some e o estado aparece já
   enquadrado, sem continuidade espacial nenhuma — parece troca de slide, não
   aproximação.

   O certo seria um `FlyToInterpolator` do deck.gl, mas ele exige que o
   componente sobreviva à navegação, ou seja, chave estável. E chave estável
   custa caro aqui: reabre o laço de rerun que a seleção anterior provoca, e
   quebra o clique repetido que abre o modo detalhe — com a seleção
   inalterada, o Streamlit nem dispara rerun. Ver `app.py`, na montagem do
   `st.pydeck_chart`.

   Então o que se faz é perceptivo, não espacial: 0,975 para 1 sugere
   aprofundamento sem prometer continuidade que não existe. Começou em 0,985 e
   subiu para 0,975 depois de olhar em tela — sutil demais para se notar.
   Abaixo de ~0,97 vira "pop" e chama atenção para si; acima de 0,99 não se
   percebe. O valor é de calibragem visual, não de cálculo.

   Duração maior que a dos gráficos (260ms contra 180ms) porque aqui há uma
   troca de contexto a acompanhar, não só um redesenho. `ease-out` para a
   chegada desacelerar, que é o que dá a sensação de assentar. */
/* **O mapa não anima.** A animação de entrada acima foi removida em
   24/ago/2026, e o comentário fica porque a razão vale para qualquer tentativa
   futura.

   Ela era `opacity: 0 -> 1` com escala, e o Streamlit **recria o contêiner e
   o canvas do deck a cada rerun** — inclusive quando a `key` do widget não
   muda, medido no navegador. Então a animação de entrada tocava a cada
   interação, e como o mapa nascia transparente sobre o branco da página, isso
   lia como piscada.

   O que se queria de verdade era outra coisa: a câmera deslizando da vista
   antiga para a nova. Isso o deck.gl faz com `transitionDuration` e
   `FlyToInterpolator`, e o pydeck emite os dois — mas eles não têm efeito
   aqui, porque sem instância anterior não há de onde partir. `initialViewState`
   é sempre inicial de fato.

   Entre uma piscada e nenhum movimento, nenhum movimento é melhor: o mapa
   simplesmente está no lugar novo, e o retorno ao clique é imediato. */

@media (prefers-reduced-motion: reduce) {{
  .kpi-card {{ transition: none !important; transform: none !important; }}
  /* Quem pediu menos movimento não recebe nem o fade. Vestibular é o motivo:
     animação repetida a cada interação é gatilho, e aqui ela é decoração.

     O mapa continua listado embora já não anime: se alguém reintroduzir
     movimento ali, ele nasce respeitando a preferência em vez de precisar
     lembrar deste bloco. */
  [data-testid="stVegaLiteChart"],
  [data-testid="stDeckGlJsonChart"] {{
    animation: none !important;
    transform: none !important;
  }}
}}
</style>
"""


def formatar_inteiro(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.0f}".replace(",", ".")


def formatar_decimal(valor: float | None, casas: int = 2) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def delta(
    atual: float | None,
    anterior: float | None,
    *,
    taxa: bool = False,
    bom_se_cai: bool = True,
    sufixo: str = "vs ano anterior",
) -> str:
    """Badge de variação contra o ano anterior.

    ``bom_se_cai`` inverte a semântica de cor. Para cura, queda é ruim; para
    casos, óbitos e incidência, queda é boa. Herdado do original.
    """
    if atual is None or anterior is None:
        return ""

    diferenca = atual - anterior
    if abs(diferenca) < 1e-9:
        return f'<div class="kpi-delta kpi-igual">≈ sem variação {escape(sufixo)}</div>'

    caiu = diferenca < 0
    classe = "kpi-bom" if caiu == bom_se_cai else "kpi-ruim"
    seta = "↓" if caiu else "↑"
    texto = formatar_decimal(abs(diferenca)) if taxa else formatar_inteiro(abs(diferenca))
    return f'<div class="kpi-delta {classe}">{seta} {texto} {escape(sufixo)}</div>'


def kpi_card(
    titulo: str,
    valor: str,
    *,
    cor: str,
    subtitulo: str | None = None,
    badge_delta: str = "",
    selecionado: bool = False,
    ajuda: str = "",
    icone: str = "",
) -> str:
    """Card de KPI — indicador, e só.

    ``icone`` é o miolo de um SVG 24×24 (os ``<path>``), desenhado à direita
    num disco na cor da métrica — o painel de origem tem um por card e é
    parte do que faz a família se reconhecer. Vazio, o disco não existe.

    A cor entra como variável CSS inline (``--kpi-accent``), o que permite um
    único bloco de estilo servir todas as métricas.

    **Não é controle.** Já foi: um ``<button>`` transparente ficava esticado
    por cima para trocar a métrica do mapa. Saiu porque o card não avisava que
    era clicável — parecia indicador porque é indicador —, e a interação
    custou quatro rodadas de conserto. Quem troca a métrica agora é um
    controle próprio, ao lado do mapa, com teclado e foco nativos.

    ``selecionado`` continua existindo para o card espelhar a métrica ativa,
    o que é leitura, não interação.
    """
    classes = "kpi-card is-selected" if selecionado else "kpi-card"
    # A explicação vive no `title`, agora que não há botão para receber `help`.
    titulo_ajuda = f' title="{escape(ajuda)}"' if ajuda else ""
    # A linha do subtítulo existe sempre, vazia quando não há texto.
    #
    # Só um card a usa hoje — "Proporção de cura" mostra "49.114 de 85.932" —
    # e isso o deixava 22px mais alto que os vizinhos, quebrando o alinhamento
    # da linha inteira. Reservar a altura é o mesmo tratamento que `.kpi-title`
    # já recebe para títulos de duas linhas.
    #
    # Esticar o card com `height: 100%` não funciona: a coluna do Streamlit
    # tem altura automática, então não há contra o que esticar.
    sub = f'<div class="kpi-sub">{escape(subtitulo) if subtitulo else ""}</div>'
    # O miolo do SVG vem do pack, não do usuário: não passa por `escape`.
    glifo = (
        '<div class="kpi-icon"><svg viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{icone}</svg></div>'
        if icone
        else ""
    )

    return (
        f'<div class="{classes}" '
        f'style="--kpi-accent:{escape(cor)};'
        f'--kpi-accent-escuro:{escape(cores.para_fundo_escuro(cor))};"'
        f'{titulo_ajuda}>'
        f'<div class="kpi-inner">'
        f'<div class="kpi-accent"></div>'
        f'<div class="kpi-text">'
        f'<div class="kpi-title">{escape(titulo)}</div>'
        f'<div class="kpi-value">{escape(valor)}</div>'
        f"{sub}{badge_delta}"
        f"</div>{glifo}</div></div>"
    )

def css_layout() -> str:
    """Estrutura da página: barra lateral, faixa de intro e as linhas.

    Separado de :func:`css_base` porque estas regras dependem de detalhes
    internos do Streamlit e tendem a precisar de manutenção a cada versão,
    enquanto os componentes acima são HTML próprio e estáveis.
    """
    return f"""
<style>
/* Barra lateral com a largura do original — mas só quando há espaço. O
   original fixava 380px sem media query, e em telas estreitas isso espremia
   o conteúdo até os rótulos quebrarem no meio da palavra.

   Recolher a barra deixava o conteúdo preso a 66% da janela, com uma faixa
   morta à esquerda e os rótulos quebrando letra a letra — o mesmo defeito que
   a media query acima existe para evitar, por outro caminho.

   A causa: o Streamlit recolhe deslizando com `transform: translateX(-100%)`
   e **mantém `width: 300px` inline** na seção. O elemento some da vista mas
   continua reservando a largura. Sem uma regra que zere isso, o buraco fica —
   e o `min-width` fixo daqui só piorava, porque também vencia qualquer
   tentativa do próprio Streamlit de encolher.

   Por isso as duas regras. Prender a largura ao estado aberto evita que ela
   valha na barra recolhida; zerar explicitamente no estado fechado é o que de
   fato recupera o espaço. Medido: sem a segunda regra o conteúdo continua em
   66% da janela mesmo com a primeira aplicada. */
/* Conteúdo recalculando esmaece — mas só se demorar.

   O Streamlit marca `data-stale="true"` nos elementos enquanto o script
   roda. Sem estilo, a troca é seca: o valor antigo fica firme e é
   substituído de repente, sem sinal nenhum de que algo estava acontecendo.

   **O atraso é o ponto todo.** Trocar de ano custa 87 ms no servidor; um
   fade que comece imediatamente estaria ainda correndo quando o conteúdo já
   chegou, e faria a interação parecer mais lenta do que é. Com 150 ms de
   espera, tudo que responde rápido não pisca — o esmaecimento só aparece nos
   casos que realmente demoram, como entrar numa UF com centenas de
   municípios.

   A volta é imediata, sem atraso: assim que o dado chega, ele aparece.
   Esconder a chegada seria o inverso do que se quer.

   Isto substitui o overlay que cobre a tela por 3 s no painel em R — ver
   `docs/paridade-com-o-painel-r.md` §4. O sinal existe, mas não bloqueia e não anuncia uma
   lentidão que não temos. */
[data-stale] {{
  transition: opacity .12s ease;
}}
[data-stale="true"] {{
  opacity: .45;
  transition-delay: .15s;
}}
@media (prefers-reduced-motion: reduce) {{
  [data-stale] {{ transition: none; }}
}}

/* Respiro da página. O padrão do Streamlit é `96px 80px 160px`, medida de
   página de documento: 144px de nada antes do título e 160px depois do último
   gráfico, num painel aberto para ler número. Os 80px laterais ainda custavam
   160px de largura, e largura é o que falta ao mapa.

   `!important` porque a regra que estamos sobrescrevendo é do próprio
   Streamlit e tem especificidade de classe gerada, que muda a cada versão. */
[data-testid="stMainBlockContainer"] {{
  padding: {tokens.PAGINA_TOPO} {tokens.PAGINA_LADOS} {tokens.PAGINA_BASE} !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{
    padding-left: {tokens.PAGINA_LADOS_ESTREITO} !important;
    padding-right: {tokens.PAGINA_LADOS_ESTREITO} !important;
  }}
}}

/* A mãozinha do deck.gl some sobre o fundo branco do mapa.

   O deck escreve `cursor: grab` inline no `#deckgl-wrapper` — mão aberta, que
   no Windows é branca com um contorno fino e desaparece contra a área vazia do
   painel. Ficou pior quando o painel passou de 430x460 para 715x530: sobrou
   muito mais branco em volta da geometria.

   O seletor casa a **string do style inline**, e só nos estados de arrastar
   (`grab` e `grabbing`). Assim o `pointer` que o deck põe ao passar sobre um
   polígono continua intacto — é ele que avisa que dá para clicar e entrar no
   recorte, que é a interação de verdade deste mapa.

   Vale a mesma razão de bloquear o zoom pela roda: arrastar desenquadra um
   mapa cujo enquadramento é calculado para caber, e sem volta a não ser
   recarregando. Não é affordance que queiramos anunciar. */
#deckgl-wrapper[style*="cursor: grab"] {{
  cursor: default !important;
}}

/* O `st.columns` é uma linha flex que não quebra. Deixando quebrar, e com um
   mínimo por coluna, recupera-se o comportamento do grid `auto-fit` do
   original — que a troca por colunas reais (necessária para os botões) havia
   custado. */
[data-testid="stHorizontalBlock"]:has(.kpi-card) {{
  flex-wrap: wrap;
  /* A faixa de KPIs é uma seção, e estava a 16px da linha de baixo — o mesmo
     respiro que separa dois controles irmãos. Com isso os cards encostavam
     nas abas e nos rótulos, e a leitura era de um bloco só em vez de dois.
     32px é o degrau de seção; o `gap` interno entre cards continua menor, e é
     a diferença entre os dois que agrupa a faixa. */
  margin-bottom: 32px;
}}
[data-testid="stHorizontalBlock"]:has(.kpi-card) > [data-testid="stColumn"] {{
  /* 150px para os seis caberem lado a lado numa tela de trabalho, e a
     quebra do `flex-wrap` acima continuar cuidando das estreitas: em telas
     menores eles viram três e três, depois dois e dois, sem media query. */
  min-width: 150px;
}}

/* Título de painel — o degrau que faltava entre o título da página e o
   corpo.

   Estas linhas ("Mapa — unidades da federação", "Ranking — UFs, por
   incidência") são o que identifica cada painel, mas saíam como `st.caption`:
   14px peso 400, exatamente o mesmo que um rótulo de widget e que a nota de
   rodapé. Sem contraste de peso, o olho não encontrava onde um painel começa
   e o outro termina — a página tinha seis blocos e nenhum cabeçalho.

   Peso, e não tamanho: subir para 16px ou 18px competiria com o valor dos
   KPIs, que é o que precisa saltar primeiro. Peso 700 com opacidade alta
   separa sem disputar.

   Caixa alta foi descartada: "Ranking — UFs, por incidência (por 100 mil
   hab.)" em maiúsculas fica pior de ler, e é justamente o rótulo mais longo. */
.titulo-painel {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .85;
  line-height: 1.3;
  margin: 0 0 6px;
}}

.sinan-intro {{
  position: relative;
  overflow: hidden;
  display: grid;
  /* Três colunas como no painel de origem: bandeira · título · marca. As
     laterais são `auto` e o meio estica, então o título fica centrado na
     faixa inteira mesmo com bandeira e marca de larguras diferentes. */
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 12px 18px;
  margin-bottom: 6px;
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  /* Liso, como o painel de origem: cartão branco, sem degradê e sem a barra
     de acento que os KPIs têm. A cor institucional já está na bandeira e no
     título; a barra era ruído ao lado dela. */
  background: var(--superficie);
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}

.sinan-intro-texto {{
  min-width: 0;
  text-align: center;
}}
/* A bandeira tem a altura do bloco de texto e cantos discretos. `flex-shrink`
   zero: em janela estreita quem cede é o título, que quebra linha — a
   bandeira espremida vira uma listra azul. */
.sinan-intro-bandeira {{
  height: 58px;
  width: auto;
  flex-shrink: 0;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, .25);
}}
.sinan-procedencia {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin: 0 4px {tokens.GAP} 0;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  line-height: 1.35;
  text-align: right;
  opacity: .78;
}}
.sinan-procedencia b {{ font-weight: 700; }}
.sinan-procedencia-ajuda {{
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #0F9D8A;
  color: #fff;
  font-size: {tokens.TEXTO_XS};
  font-weight: 700;
  font-style: italic;
  cursor: help;
}}
/* Sem o arquivo da bandeira, duas colunas — e o título segue centrado. */
.sinan-intro-sem-bandeira {{
  grid-template-columns: minmax(0, 1fr) auto;
}}

/* Escopo do recorte, na própria faixa.

   Com a barra lateral recolhida — que é como o painel é projetado — não havia
   **nada na tela** dizendo de que ano e de que território eram os números. O
   mesmo layout serve Brasil/2024 e Pernambuco/2018, e uma captura de tela não
   se explicava sozinha. Num painel de vigilância isso é procedência, não
   enfeite.

   É dinâmico de propósito: vira "Pernambuco · 2018" ao navegar. Foi por isso
   que o título ficou só "Tuberculose" — pôr "nacional" nele seria mentira no
   instante em que alguém clica numa UF, que é a interação principal. */
.sinan-intro-escopo {{
  margin-top: 2px;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 400;
  opacity: .68;
  line-height: 1.35;
}}

/* O seletor precisa do `h1` e do ancestral: o título é um `<h1>`, e o
   Streamlit estiliza `.st-emotion-cache-… h1` com `font-size: 2.75rem`. Esse
   seletor tem especificidade (0,1,1) e vencia `.sinan-intro-titulo` (0,1,0) —
   o `clamp` abaixo estava declarado e nunca chegava à tela, com o título
   fixo em 44px contra os 30px de teto. Era o que fazia "Tuberculose" quebrar
   em duas ou três linhas em janela estreita.

   `.sinan-intro h1.sinan-intro-titulo` dá (0,2,1) e ganha com folga, sem
   precisar de `!important` — que aqui seria pior, porque calaria também
   qualquer ajuste futuro do próprio pack de doença. */
.sinan-intro h1.sinan-intro-titulo {{
  margin: 0;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_TITULO};
  font-weight: 900;
  line-height: 1.08;
  /* Negativo, e não positivo: em peso 900 o espaçamento aberto espalha a
     palavra e ela perde solidez. Fechar um pouco faz o título ler como bloco,
     que é o que se quer de um nome de painel. */
  letter-spacing: -.015em;
  text-align: center;
  text-wrap: balance;
  color: inherit;
}}
/* A marca é texto, não imagem.

   Era um JPEG sobre uma placa branca explícita. A placa existia porque JPEG
   não tem canal alfa: sem ela, o fundo branco do arquivo virava um bloco no
   tema escuro. Só que a placa resolvia um problema criando outro — um
   retângulo branco recortado contra a superfície da faixa, visível nos dois
   temas e mais chamativo que a própria marca.

   Como palavra, a marca não tem fundo para esconder: herda o tema, fica
   nítida em qualquer tamanho, não pesa no payload e não depende de arquivo
   presente em disco. As cores saem do próprio logotipo, amostradas do
   `assets/cenarios_logo_full.jpeg`: azul #0092C3 e o "+" em terracota
   #CA6F43. */
.sinan-intro-marca {{
  justify-self: end;
  align-self: center;
  font-family: var(--fonte);
  /* Degrau da escala, não número solto: `TEXTO_XL` é o mesmo do valor de KPI.
     Escrevi 22px aqui na primeira versão e o `test_nenhum_tamanho_de_fonte_fixo`
     pegou — que é o teste fazendo exatamente o trabalho dele. */
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  letter-spacing: -.005em;
  line-height: 1;
  white-space: nowrap;
  color: #0092C3;
}}
.sinan-intro-marca-mais {{
  color: #CA6F43;
  font-weight: 900;
}}
.indicador-programa {{
  padding: 14px 16px;
  border-radius: {tokens.RAIO_CARD};
  border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
  background: color-mix(in srgb, currentColor 3%, transparent);
}}
.indicador-titulo {{
  font-size: {tokens.TEXTO_XS};
  font-weight: 600;
  opacity: .75;
  margin-bottom: 4px;
}}
.indicador-valor {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  line-height: 1.1;
  color: var(--ind-cor);
}}
/* A trilha usa `currentColor` para funcionar nos dois temas sem duplicar
   regra — no claro ela escurece o fundo, no escuro ela o clareia. */
.indicador-barra {{
  height: 6px;
  margin: 8px 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 12%, transparent);
  overflow: hidden;
}}
.indicador-barra > span {{
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ind-cor);
}}
.indicador-detalhe {{ font-size: {tokens.TEXTO_XS}; opacity: .65; }}

/* Sem logotipo não há segunda coluna: o título ocupa a faixa toda. */

/* Linha principal: mapa à esquerda, gráficos à direita.
   O original travava `height` em 520px e 760px, o que quebra em telas baixas;
   aqui são mínimos. */
.sinan-painel {{
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
  padding: {tokens.PADDING};
  color: inherit;
  font-family: var(--fonte);
}}
.sinan-painel-mapa {{ min-height: {tokens.ALTURA_MIN_MAPA}; }}
.sinan-painel-graficos {{ min-height: {tokens.ALTURA_MIN_PAINEL}; }}
/* Legenda do mapa. O deck.gl não desenha uma, então ela é HTML — mesmo
   padrão dos cards de KPI.

   **Flutua sobre o mapa**, como no painel de origem, e a subida é por margem
   negativa e não por `position: absolute`. Absoluto exigiria um ancestral
   posicionado, e o único candidato é a coluna do Streamlit, cuja estrutura
   interna muda de versão para versão — foi a classe de acoplamento que o
   `css_layout` já avisa que dá manutenção a cada atualização. Com margem
   negativa a legenda continua no fluxo, alinhada horizontalmente com o mapa
   de graça, e o pior caso de o mapa mudar de altura é ela encostar na borda
   em vez de sair do lugar. */
.mapa-legenda {{
  /* Duas colunas, e não uma.
     
     Em coluna única a caixa ficava com 219px de altura e tapava uma faixa de
     132px do canto inferior direito do mapa — bairros inteiros sumiam atrás
     dela. Em duas, a altura cai pela metade e a margem negativa menor deixa
     só a borda superior encostando na moldura, onde não há polígono.
     
     A cada item novo a caixa cresce em largura, não em altura, que é a
     direção onde há folga: o mapa tem 500px de altura e sobra lateral. */
  display: grid;
  /* Quantas colunas couberem: com nome e contagem cada item tem ~200px,
     e numa coluna estreita a segunda coluna vazava para fora da caixa. */
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  align-content: start;
  gap: 5px 18px;
  /* Abaixo do mapa, e não flutuando sobre ele: em PE o estado ocupa a
     largura toda e a caixa tapava o litoral sul. Ao lado dela vai a tabela
     "municípios por classe", como no painel de origem. */
  position: relative;
  width: 100%;
  margin: 8px 0 4px 0;
  padding: 10px 14px;
  border-radius: {tokens.RAIO_PAINEL};
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  background: color-mix(in srgb, currentColor 5%, Canvas 95%);
  box-shadow: {tokens.SOMBRA_REPOUSO};
  backdrop-filter: blur(6px);
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  color: inherit;
}}
.mapa-legenda-titulo {{
  grid-column: 1 / -1;
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 2px;
}}
.mapa-legenda-item {{ display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }}
.mapa-legenda-item em {{ font-style: italic; opacity: .8; }}
.mapa-legenda-item i {{
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
}}

/* ---------------------------------------------------------------------
   Aproximação da aparência do painel de origem.

   Lá os controles são pílulas e aqui eram texto solto. É cosmético, mas
   cosmético com função: a pílula delimita o controle, e numa coluna com três
   controles empilhados ao lado do mapa é o que separa "o que eu posso mexer"
   de "o que é rótulo".

   **Os seletores vêm de inspeção do DOM, não de suposição.** O Streamlit 1.61
   troca `role="tab"` por `data-testid="stTab"`, e o sublinhado da aba ativa é
   um `div.react-aria-SelectionIndicator` — não um `border-bottom`, que foi o
   primeiro palpite e não funcionou. As classes `st-emotion-cache-*` mudam a
   cada build e não servem de gancho; `data-testid` e `.st-key-<key>` servem.
   --------------------------------------------------------------------- */

/* --- Escala de espaçamento dos controles ---------------------------------
   O rótulo vinha com 4px sob si, encostando no widget. Com a pílula isso
   piorou: a pílula tem fundo, então o encosto vira duas caixas coladas. */
[data-testid="stWidgetLabel"] {{
  margin-bottom: 10px;
}}
/* Respiro entre um controle e o próximo na mesma coluna. */
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stButtonGroup"]),
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stSelectbox"]) {{
  margin-bottom: 14px;
}}

/* --- Abas: pílulas ------------------------------------------------------- */
[data-testid="stTabs"] [role="tablist"] {{
  gap: 10px;
  border-bottom: none;
  margin-bottom: 14px;
}}
[data-testid="stTabs"] [data-testid="stTab"] {{
  border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
  border-radius: {tokens.RAIO_PILL};
  padding: 6px 18px;
  background: color-mix(in srgb, currentColor 4%, transparent);
  font-weight: 600;
}}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {{
  border-color: color-mix(in srgb, var(--intro-accent, #12346B) 55%, transparent);
  background: color-mix(in srgb, var(--intro-accent, #12346B) 12%, transparent);
  color: var(--intro-accent, #12346B);
}}
/* O sublinhado que o Streamlit desenha sob a aba ativa sai: com a pílula ele
   vira um segundo indicador de seleção dizendo a mesma coisa, e em cor que
   briga com a do cromo. */
[data-testid="stTabs"] .react-aria-SelectionIndicator {{ display: none; }}

/* --- Controle segmentado: pílulas, para não sobrar o único canto vivo ---- */
[data-testid="stButtonGroup"] {{ gap: 8px; }}
[data-testid="stButtonGroup"] button {{
  border-radius: {tokens.RAIO_PILL} !important;
  border: 1px solid color-mix(in srgb, currentColor 16%, transparent) !important;
  padding: 5px 16px;
  font-weight: 600;
}}
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"] {{
  border-color: color-mix(in srgb, var(--intro-accent, #12346B) 55%, transparent) !important;
  background: color-mix(in srgb, var(--intro-accent, #12346B) 12%, transparent);
}}

/* --- Rótulo de widget: pílula, como "Ano: 2023" e "Métrica: Incidência" -- */
[data-testid="stWidgetLabel"] > span {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  border-radius: {tokens.RAIO_PILL};
  background: color-mix(in srgb, var(--intro-accent, #12346B) 11%, transparent);
  color: var(--intro-accent, #12346B);
  font-weight: 700;
  font-size: {tokens.TEXTO_XS};
}}
[data-testid="stWidgetLabel"] p {{ margin: 0; font-weight: 700; }}

/* O contêiner do Streamlit que carrega um título colapsa para 8px, e o texto
   de 18px transborda por cima do gráfico seguinte — visível como título pela
   metade. O `overflow` é `visible`, então nada corta: o que falta é o
   contêiner reservar a própria altura.

   `min-height` no contêiner, e não no título: o título já declara a sua e o
   problema é o pai não a respeitar. */
[data-testid="stElementContainer"]:has(.titulo-painel) {{
  min-height: 26px;
}}

/* Marcador de ajuda ao lado do título de um painel. Círculo pequeno, cor do
   cromo — o mesmo "i" que o painel de origem põe ao lado do nome da aba. */
.titulo-painel-ajuda {{
  display: inline-grid;
  place-items: center;
  width: 17px;
  height: 17px;
  margin-left: 7px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--intro-accent, #12346B) 14%, transparent);
  color: var(--intro-accent, #12346B);
  font-size: 12px;
  font-weight: 700;
  font-style: italic;
  cursor: help;
  vertical-align: middle;
}}

/* --- Cartão por função --------------------------------------------------
   No painel de origem cada função mora no próprio retângulo branco: o
   seletor de ano é um, a métrica é outro, o mapa é outro. Sem isso os
   controles boiam no fundo e nada diz onde um termina e o outro começa.

   O gancho é `.st-key-cartao-*`, a classe que o Streamlit carimba no
   contêiner de um `st.container(border=True, key=...)`. A borda que ele
   desenha por padrão é uma linha seca; aqui ela recebe o mesmo tratamento
   de `.sinan-painel` — superfície, raio e sombra — para o cartão ser irmão
   dos cards de KPI em vez de um retângulo à parte. */
[class*="st-key-cartao-"] {{
  border-radius: {tokens.RAIO_PAINEL} !important;
  border: var(--borda) !important;
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
  padding: {tokens.PADDING};
  margin-bottom: 14px;
}}
/* O último rótulo de um cartão não precisa de margem inferior: o padding do
   cartão já é o respiro, e as duas somadas afastavam o widget do título. */
/* Os controles dentro do cartão único precisam de respiro entre si — sem
   isto o seletor de ano encosta no rótulo do recorte. Um valor só, e não
   `gap: 0` como antes: agora há três controles irmãos num cartão, e não um. */
[class*="st-key-cartao-controles"] [data-testid="stVerticalBlock"] {{ gap: 12px; }}
[class*="st-key-cartao-mapa"] [data-testid="stVerticalBlock"],
[class*="st-key-cartao-graficos"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
[class*="st-key-cartao-"] > div > [data-testid="stElementContainer"]:last-child {{
  margin-bottom: 0;
}}

/* --- "Ver Pernambuco inteiro": pílula com borda ------------------------------
   O seletor é `.st-key-<key>`, a classe que o Streamlit carimba no contêiner
   de um widget com `key`. É o único gancho estável para um botão específico:
   um seletor de `button` pega todos os da página. */
.st-key-voltar_recife {{ margin: 12px 0 4px; }}
.st-key-voltar_recife button {{
  border-radius: {tokens.RAIO_PILL};
  border: 1.5px solid color-mix(in srgb, var(--intro-accent, #12346B) 45%, transparent);
  color: var(--intro-accent, #12346B);
  font-weight: 700;
  padding: 7px 20px;
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}
.st-key-voltar_recife button:hover {{
  background: color-mix(in srgb, var(--intro-accent, #12346B) 10%, transparent);
  border-color: var(--intro-accent, #12346B);
}}

.sinan-painel-vazio {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: {tokens.TEXTO_SM};
  opacity: .55;
}}
</style>
"""


def titulo_painel(texto: str, ajuda: str = "") -> str:
    """Cabeçalho de um painel, com explicação opcional no marcador de ajuda.

    Existe porque `st.caption` não distingue papéis: o mesmo 14px peso 400
    servia para identificar um painel, rotular um widget e escrever a nota de
    procedência no rodapé. Ver `.titulo-painel` em :func:`css_layout`.

    ``ajuda`` vira um "i" ao lado do título, com o texto no ``title`` — mesmo
    tratamento do `kpi_card`. É onde vive a explicação de um gráfico que
    precisa de uma, e o motivo é de espaço: como parágrafo abaixo do gráfico,
    ela empurrava o título do gráfico seguinte e os dois colidiam. Explicação
    de três linhas ocupa mais tela que o próprio eixo.
    """
    marca = ""
    if ajuda:
        marca = (
            f'<span class="titulo-painel-ajuda" title="{escape(ajuda)}"'
            f' aria-label="{escape(ajuda)}" tabindex="0">i</span>'
        )
    return f'<div class="titulo-painel">{escape(texto)}{marca}</div>'


#: Bandeira de Pernambuco, embutida como data URI.
#:
#: Embutida, e não servida: o Streamlit só serve `static/` com configuração
#: extra, e um `<img src>` para um caminho que não existe é um ícone quebrado
#: no cabeçalho. São 6,7 KB em WebP — cabe no HTML sem custo perceptível.
_BANDEIRA = Path(__file__).resolve().parents[2] / "assets" / "bandeira_pernambuco.jpeg"


def _bandeira_data_uri() -> str | None:
    try:
        dados = _BANDEIRA.read_bytes()
    except OSError:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(dados).decode("ascii")


def faixa_intro(titulo: str, *, escopo: str, cor: str) -> str:
    """Faixa de identificação: bandeira à esquerda, título ao centro, marca à direita.

    É a composição do painel de origem, e foi pedida de propósito: a família
    de painéis se reconhece pelo cabeçalho antes de qualquer gráfico. Aqui a
    bandeira faz sentido — o painel é de Recife e nunca sai de Recife —, ao
    contrário do nacional, onde ela lia como recorte e saiu.

    Sem o arquivo da bandeira a faixa degrada para duas colunas, sem ícone
    quebrado: a coluna some e o título continua centrado.

    A marca é **texto**, não imagem — ver o comentário de `.sinan-intro-marca`
    em :func:`css_layout`. O usuário preferiu a nossa à do painel de origem.
    """
    bandeira = _bandeira_data_uri()
    img = (
        f'<img class="sinan-intro-bandeira" src="{bandeira}" alt="Bandeira de Pernambuco">'
        if bandeira
        else ""
    )
    classe = "sinan-intro" + ("" if bandeira else " sinan-intro-sem-bandeira")
    return (
        f'<div class="{classe}" style="--intro-accent:{escape(cor)};">'
        f"{img}"
        '<div class="sinan-intro-texto">'
        f'<h1 class="sinan-intro-titulo">{escape(titulo)}</h1>'
        f'<div class="sinan-intro-escopo">{escape(escopo)}</div>'
        "</div>"
        '<span class="sinan-intro-marca">Cenários'
        '<span class="sinan-intro-marca-mais">+</span></span>'
        "</div>"
    )


def procedencia(dados_ate: str, processado_em: str, *, ajuda: str = "") -> str:
    """"Dados até … / Processado em …", à direita, sob o cabeçalho.

    É a linha de procedência do painel de origem, e aqui ela vale mais do que
    lá: a imagem que a outra equipe roda tem os dados dentro, então a única
    forma de saber se estão desatualizados é esta linha.
    """
    marcador = (
        f'<span class="sinan-procedencia-ajuda" title="{escape(ajuda)}">i</span>'
        if ajuda
        else ""
    )
    return (
        '<div class="sinan-procedencia"><div>'
        f"Dados até <b>{escape(dados_ate)}</b><br>"
        f"Processado em <b>{escape(processado_em)}</b></div>"
        f"{marcador}</div>"
    )


def painel_vazio(titulo: str, aviso: str, *, mapa: bool = False) -> str:
    """Espaço reservado de um painel que ainda não existe."""
    variante = "sinan-painel-mapa" if mapa else "sinan-painel-graficos"
    return (
        f'<div class="sinan-painel {variante} sinan-painel-vazio">'
        f"<div><strong>{escape(titulo)}</strong><br>{escape(aviso)}</div></div>"
    )


#: Seletor do contêiner do mapa no DOM do Streamlit.
SELETOR_MAPA = '[data-testid="stDeckGlJsonChart"]'


#: Os botoes de zoom do mapa. Sao controles do mapbox que o deck.gl monta
#: dentro do proprio wrapper, e por isso precisam ser realocados para fora --
#: ver `script_travar_zoom`.
SELETOR_CONTROLE_ZOOM = ".mapboxgl-ctrl-group"


def script_travar_zoom() -> str:
    """Trava a roda do mouse no mapa e isola os botoes de zoom dele.

    O caminho declarativo não existe: o ``DeckGlJsonChart`` do Streamlit passa
    ``controller={true}`` fixo para o ``<DeckGL>`` e descarta o que vier no
    JSON do pydeck. Sem isto, rolar a página com o cursor sobre o mapa aplica
    zoom, o enquadramento se perde e só recarregando volta — e o mapa ocupa
    metade da tela, então acontece o tempo todo.

    A interceptação é na fase de captura, antes de o evento descer até o
    deck.gl, e **sem** ``preventDefault``: a rolagem normal da página segue
    acontecendo. Só o zoom morre.

    **Os botoes de zoom precisam de outro remedio, pelo mesmo motivo de
    fundo.** Eles sao controles do mapbox que o deck monta **dentro** do
    ``#deckgl-wrapper``, e o deck escuta o ponteiro no wrapper, na fase de
    captura. Com um poligono debaixo do botao, o clique dava zoom e **entrava
    no municipio**: a pagina recarregava com o enquadramento inicial e o zoom
    sumia junto. Sem poligono embaixo funcionava, o que fazia o defeito
    parecer aleatorio.

    ``stopPropagation`` nao resolve, e as duas tentativas mostram por que:

    - na **captura**, do documento, o evento morre antes de chegar ao botao --
      troca "as vezes nao funciona" por "nunca funciona";
    - na **borbulha**, no proprio controle, o deck ja viu o evento na captura,
      la em cima -- o botao funciona e o mapa navega junto, que era o defeito
      original.

    O que resta e tirar o controle de dentro do wrapper. Ele vai para o
    contentor do grafico, posicionado no mesmo lugar, e o clique deixa de
    atravessar territorio do deck. Verificado no navegador: zooma e nao
    navega.

    Precisa rodar via ``st.components.v1.html`` — o ``st.markdown`` remove
    ``<script>``. O componente vira um iframe de mesma origem, daí o
    ``window.parent``.
    """
    return f"""
<script>
(function () {{
  var doc = window.parent && window.parent.document;
  if (!doc || doc.__travaZoomMapa) return;   // idempotente: o Streamlit
  doc.__travaZoomMapa = true;                // reexecuta o script a cada rerun
  doc.addEventListener('wheel', function (e) {{
    var alvo = (e.target && e.target.closest) ? e.target : null;
    if (alvo && alvo.closest('{SELETOR_MAPA}')) {{
      e.stopPropagation();
    }}
  }}, {{ capture: true, passive: true }});

  // Os botoes de zoom saem de dentro do wrapper do deck.
  //
  // Mover, e nao barrar o evento: ver a docstring: o deck escuta na captura,
  // entao qualquer `stopPropagation` ou chega tarde demais ou mata o botao.
  function realocar() {{
    var grupo = doc.querySelector('{SELETOR_CONTROLE_ZOOM}');
    var caixa = doc.querySelector('{SELETOR_MAPA}');
    if (!grupo || !caixa || grupo.__realocado) return;

    // O grupo anterior morre junto com o mapa que o Streamlit remontou, mas
    // como ele agora mora fora do wrapper, o Streamlit nao o leva embora.
    var antigo = caixa.querySelector(':scope > [data-zoom-realocado]');
    if (antigo) antigo.remove();

    var r = grupo.getBoundingClientRect();
    var rc = caixa.getBoundingClientRect();
    grupo.__realocado = true;
    grupo.setAttribute('data-zoom-realocado', '1');
    grupo.style.position = 'absolute';
    grupo.style.left = (r.left - rc.left) + 'px';
    grupo.style.top = (r.top - rc.top) + 'px';
    grupo.style.margin = '0';
    grupo.style.zIndex = '5';
    caixa.appendChild(grupo);
  }}

  realocar();
  // O Streamlit remonta o mapa a cada rerun, e os controles voltam dentro.
  new window.parent.MutationObserver(realocar).observe(doc.body, {{
    childList: true, subtree: true
  }});
}})();
</script>
"""



