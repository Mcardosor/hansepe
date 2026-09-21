/* Componente de mapa — o deck.gl vivo entre um rerun e outro.
 *
 * O `st.pydeck_chart` recria o canvas do deck a cada rerun, e por isso nem
 * `FlyToInterpolator` nem fade tinham de onde partir (ver `docs/mapa-clique.md`,
 * "Transição"). Aqui a instância do Deck nasce uma vez, no primeiro
 * `streamlit:render`, e os renders seguintes só chamam `setProps`: as camadas
 * novas entram com a cor interpolando (`transitions` na camada, definido em
 * `src/mapa.py`) e a câmera voa do quadro antigo para o novo.
 *
 * Fala com o Streamlit pelo protocolo de componente (v1), sem a lib npm: três
 * mensagens — `componentReady`, `setFrameHeight`, `setComponentValue` — e a
 * escuta de `streamlit:render`. O spec que chega é o JSON do pydeck, convertido
 * pelo `JSONConverter` do próprio deck.gl, que é o que o widget do pydeck faz.
 */
(function () {
  "use strict";

  const raiz = document.getElementById("mapa");
  const converter = new deck.JSONConverter({
    configuration: new deck.JSONConfiguration({ classes: Object.assign({}, deck) }),
  });

  let instancia = null;
  let quadroAtual = null;     // "lat,lon,zoom" do último enquadramento pedido
  let vistaAtual = null;      // viewState corrente, para os botões de zoom
  let tooltipSpec = null;
  let contador = 0;
  // Prefixo por carga do iframe: se ele recarregar no meio da sessão, o nonce
  // não repete o que o Python já viu.
  const prefixo = Date.now().toString(36);

  function enviar(tipo, dados) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: tipo }, dados), "*");
  }

  // --- tooltip: o template `{campo}` do pydeck, resolvido pelas properties --
  function tooltip(info) {
    if (!info.object || !tooltipSpec) return null;
    const props = info.object.properties || {};
    const html = tooltipSpec.html.replace(/\{([^}]+)\}/g, (_, k) => {
      const v = props[k] !== undefined ? props[k] : info.object[k];
      return v === undefined || v === null ? "" : String(v);
    });
    return { html, style: tooltipSpec.style || {} };
  }

  function aoClicar(info) {
    if (!info.object) return;
    contador += 1;
    enviar("streamlit:setComponentValue", {
      value: { nonce: prefixo + "-" + contador, properties: info.object.properties || {} },
      dataType: "json",
    });
  }

  function zoom(delta) {
    if (!instancia || !vistaAtual) return;
    instancia.setProps({
      initialViewState: Object.assign({}, vistaAtual, {
        zoom: Math.max(2, Math.min(12, vistaAtual.zoom + delta)),
        transitionDuration: 300,
        transitionEasing: (t) => 1 - Math.pow(1 - t, 3),
      }),
    });
  }
  document.getElementById("mais").addEventListener("click", () => zoom(1));
  document.getElementById("menos").addEventListener("click", () => zoom(-1));

  function render(args) {
    const spec = typeof args.spec === "string" ? JSON.parse(args.spec) : args.spec;
    tooltipSpec = args.tooltip || null;
    const altura = Number(args.altura) || 500;
    const duracao = Number(args.transicao) || 0;

    raiz.style.height = altura + "px";
    enviar("streamlit:setFrameHeight", { height: altura });

    // Só as camadas passam pelo conversor: o resto do spec (views, mapStyle,
    // initialViewState) é decidido aqui.
    const camadas = converter.convert({ layers: spec.layers || [] }).layers || [];
    const vs = spec.initialViewState || {};
    const alvo = {
      latitude: vs.latitude, longitude: vs.longitude, zoom: vs.zoom,
      bearing: 0, pitch: 0,
    };
    const quadro = [alvo.latitude, alvo.longitude, alvo.zoom].join(",");

    if (!instancia) {
      vistaAtual = alvo;
      instancia = new deck.Deck({
        parent: raiz,
        width: "100%",
        height: "100%",
        initialViewState: alvo,
        // Roda do mouse desligada, como no painel de origem: rolar a página
        // sobre o mapa não pode virar zoom. Arrastar continua.
        controller: { scrollZoom: false, doubleClickZoom: false, touchZoom: false, keyboard: false },
        layers: camadas,
        getTooltip: tooltip,
        onClick: aoClicar,
        getCursor: ({ isHovering, isDragging }) => (isDragging ? "grabbing" : isHovering ? "pointer" : "grab"),
        onViewStateChange: ({ viewState }) => { vistaAtual = viewState; },
      });
      quadroAtual = quadro;
      window.__mapa = instancia; // para inspeção no navegador
      return;
    }

    instancia.setProps({ layers: camadas });
    if (quadro === quadroAtual) return;

    // Voo da câmera: só quando o enquadramento pedido mudou. Trocar de
    // métrica não move o mapa, e quem arrastou não é puxado de volta.
    //
    // O voo começa **depois** que a página assentou, não junto com o rerun:
    // o `streamlit:render` chega enquanto o Streamlit ainda redesenha os
    // cards e os gráficos, e nesse pico o laço de animação do deck não ganha
    // frame — medido, o voo de 700 ms saía como um salto. Esperar o navegador
    // ficar ocioso (com teto, para não esperar demais) dá ao voo os frames
    // que ele precisa.
    quadroAtual = quadro;
    vistaAtual = alvo;
    const voo = Object.assign({}, alvo, {
      transitionDuration: duracao,
      transitionInterpolator: new deck.FlyToInterpolator({ speed: 1.4 }),
      transitionEasing: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    });
    const partir = () => {
      if (quadroAtual !== quadro) return; // outro enquadramento chegou antes
      instancia.setProps({ initialViewState: voo });
    };
    if (window.requestIdleCallback) {
      window.requestIdleCallback(partir, { timeout: 350 });
    } else {
      setTimeout(partir, 120);
    }
  }

  window.addEventListener("message", (ev) => {
    const msg = ev.data || {};
    if (msg.type !== "streamlit:render") return;
    try {
      render(msg.args || {});
    } catch (e) {
      console.error("mapa: falha ao renderizar", e);
    }
  });

  enviar("streamlit:componentReady", { apiVersion: 1 });
})();
