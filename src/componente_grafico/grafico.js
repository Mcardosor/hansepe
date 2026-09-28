/* Componente de gráfico — o ECharts vivo entre um rerun e outro.
 *
 * Mesma ideia do mapa (`../componente_mapa/mapa.js`): a instância nasce uma
 * vez, no primeiro `streamlit:render`, e os renders seguintes só chamam
 * `setOption` com a opção nova. O ECharts interpola sozinho o que mudou —
 * barra que cresce até o valor novo, barra que troca de posição no ranking,
 * linha que se redesenha — porque os itens são casados pelo `name` de cada
 * dado (por isso o Python manda `name` em todo item).
 *
 * O Python manda a opção pronta (`option`), a altura e o nome do evento de
 * clique. O clique volta como ``{nonce, name, seriesName, dataIndex}``.
 */
(function () {
  "use strict";

  const raiz = document.getElementById("grafico");
  let instancia = null;
  let contador = 0;
  const prefixo = Date.now().toString(36);

  function enviar(tipo, dados) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: tipo }, dados), "*");
  }

  function aoClicar(params) {
    contador += 1;
    enviar("streamlit:setComponentValue", {
      value: {
        nonce: prefixo + "-" + contador,
        name: params.name,
        seriesName: params.seriesName,
        dataIndex: params.dataIndex,
        // A chave de navegação viaja dentro do dado, quando existe.
        chave: params.data && typeof params.data === "object" ? params.data.chave : undefined,
      },
      dataType: "json",
    });
  }

  function devolverFoco() {
    setTimeout(() => {
      if (document.activeElement && document.activeElement !== document.body) {
        document.activeElement.blur();
      }
      try { window.parent.focus(); } catch (e) { /* ignora */ }
    }, 0);
  }

  function render(args, tema) {
    const option = typeof args.option === "string" ? JSON.parse(args.option) : args.option;
    const altura = Number(args.altura) || 300;
    raiz.style.height = altura + "px";
    enviar("streamlit:setFrameHeight", { height: altura });

    // Cor do texto e fonte vêm do tema do Streamlit — o iframe não herda
    // `currentColor` da página, como o Altair herdava.
    const corTexto = (tema && tema.textColor) || "#31333F";
    const fonte = (tema && tema.font) || "system-ui, sans-serif";
    option.textStyle = Object.assign({ color: corTexto, fontFamily: fonte }, option.textStyle || {});
    // Quem pediu menos movimento no sistema não recebe animação nenhuma.
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      option.animation = false;
    }
    // Tooltip em pt-BR: o Python manda o rótulo e as casas; o formatador é
    // função, e função não viaja em JSON.
    // Duas formas: o item traz o HTML pronto (`data.tooltip`), ou o Python
    // manda rótulo e casas e o número é formatado aqui.
    if (option.tooltip) {
      const rotulo = option.tooltip.rotuloValor;
      const casas = Number(option.tooltip.casas) || 0;
      const ocultas = option.tooltip.ocultas || [];
      const fmt = (x) => x === null || x === undefined || Number.isNaN(x) ? "—"
        : Number(x).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
      const mes = (valorEixo) => {
        // "2024-03-01" -> "mar/2024"
        const d = new Date(valorEixo);
        if (Number.isNaN(d.getTime())) return String(valorEixo);
        return d.toLocaleDateString("pt-BR", { month: "short", year: "numeric", timeZone: "UTC" })
          .replace(". de ", "/").replace(".", "");
      };
      option.tooltip.formatter = (p) => {
        if (Array.isArray(p) && option.tooltip.trigger === "axis") {
          const porSerie = option.tooltip.casasPorSerie || {};
          const linhas = p.filter((s) => !ocultas.includes(s.seriesName)).map((s) => {
            const valor = Array.isArray(s.value) ? s.value[1] : s.value;
            const c = porSerie[s.seriesName] !== undefined ? porSerie[s.seriesName] : casas;
            const num = valor === null || valor === undefined ? "\u2014"
              : Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: c, maximumFractionDigits: c });
            return s.marker + " " + s.seriesName + ": <b>" + num + "</b>";
          });
          let cabeca = "";
          if (p[0]) {
            cabeca = option.tooltip.mesNoEixo
              ? mes(Array.isArray(p[0].value) ? p[0].value[0] : p[0].axisValue)
              : p[0].axisValueLabel;
          }
          return "<b>" + cabeca + "</b><br/>" + linhas.join("<br/>");
        }
        const v = Array.isArray(p) ? p[0] : p;
        if (v.data && typeof v.data === "object" && v.data.tooltip) return v.data.tooltip;
        const bruto = Array.isArray(v.value) ? v.value[1] : v.value;
        const num = fmt(option.tooltip.absoluto && bruto !== null && bruto !== undefined ? Math.abs(bruto) : bruto);
        const cabeca = option.tooltip.absoluto ? v.name + " · " + v.seriesName : v.name;
        return "<b>" + cabeca + "</b><br/>" + (rotulo || v.seriesName || "") + ": <b>" + num + "</b>";
      };
    }
    if (option.title && option.title.textStyle && !option.title.textStyle.color) {
      option.title.textStyle.color = corTexto;
    }
    if (option.legend && option.legend.textStyle) option.legend.textStyle.color = corTexto;
    if (option.yAxis && option.yAxis.nameTextStyle) option.yAxis.nameTextStyle.color = corTexto;
    if (option.yAxis && option.yAxis.axisLabel) {
      option.yAxis.axisLabel.color = corTexto;
    }
    if (option.xAxis && option.xAxis.axisLabel) {
      option.xAxis.axisLabel.color = corTexto;
      // Pirâmide: o lado esquerdo é negativo só para ficar à esquerda;
      // "-500 casos" não existe, então o eixo mostra o módulo.
      if (option.xAxis.absoluto) {
        option.xAxis.axisLabel.formatter = (v) => Math.abs(v).toLocaleString("pt-BR");
      }
      if (option.xAxis.nameTextStyle) option.xAxis.nameTextStyle.color = corTexto;
    }

    // Rótulo em cima da barra, como nos indicadores do boletim. O Python
    // manda `label.casas`; o formatador em pt-BR nasce aqui, porque função
    // não atravessa o JSON que o componente recebe. Valor nulo — ano de
    // coorte aberta — não escreve "null" em cima da barra vazia.
    (option.series || []).forEach((s) => {
      if (s.label && s.label.casas !== undefined) {
        const casasRotulo = Number(s.label.casas) || 0;
        // Cor explícita do Python (o branco de dentro da barra) manda; sem
        // ela, o rótulo segue o texto do tema.
        if (!s.label.color) s.label.color = corTexto;
        s.label.formatter = (p) =>
          p.value === null || p.value === undefined
            ? ""
            : Number(p.value).toLocaleString("pt-BR", {
                minimumFractionDigits: casasRotulo,
                maximumFractionDigits: casasRotulo,
              });
      }
    });

    if (!instancia) {
      instancia = echarts.init(raiz, null, { renderer: "canvas" });
      instancia.on("click", aoClicar);
      raiz.addEventListener("pointerup", devolverFoco);
      window.addEventListener("resize", () => instancia && instancia.resize());
      window.__grafico = instancia;
    } else if (instancia.getHeight() !== altura) {
      instancia.resize({ height: altura });
    }
    // `notMerge: false` (o padrão) é o que preserva a animação: o ECharts
    // casa a opção nova com a antiga série a série e interpola. Com
    // `notMerge: true` ele descartaria tudo e desenharia do zero.
    instancia.setOption(option, { replaceMerge: ["series"] });
  }

  window.addEventListener("message", (ev) => {
    const msg = ev.data || {};
    if (msg.type !== "streamlit:render") return;
    try {
      render(msg.args || {}, msg.theme);
    } catch (e) {
      console.error("grafico: falha ao renderizar", e);
    }
  });

  enviar("streamlit:componentReady", { apiVersion: 1 });
})();
