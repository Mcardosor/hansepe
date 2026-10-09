"""O componente ECharts: o que o Python promete ao JavaScript."""

from __future__ import annotations

import json

import pandas as pd

from src import grafico_componente as gc


def test_arquivos_do_componente_existem() -> None:
    for nome in ("index.html", "grafico.js", "echarts.min.js"):
        assert (gc.DIRETORIO / nome).is_file(), nome


def _tabela() -> pd.DataFrame:
    return pd.DataFrame({
        "chave": ["261160", "260790", "261070"],
        "nome": ["Recife", "Jaboatão dos Guararapes", "Olinda"],
        "valor": [101.3, 60.2, 75.0],
    })


def test_ranking_ordena_do_maior_no_topo_e_leva_nome_e_chave() -> None:
    """Eixo de categoria do ECharts cresce de baixo para cima: o maior tem
    de ser o último da lista para ficar no topo. `name` é o que casa o item
    entre dois renders (é a animação); `chave` é o que navega."""
    opt = gc.ranking(_tabela(), rotulo="Incidência", cor="#92400E")
    nomes = opt["yAxis"]["data"]
    assert nomes == ["Jaboatão dos Guararapes", "Olinda", "Recife"]
    itens = opt["series"][0]["data"]
    assert [i["name"] for i in itens] == nomes
    assert [i["chave"] for i in itens] == ["260790", "261070", "261160"]
    assert opt["series"][0]["id"] == "ranking"


def test_ranking_destaca_o_selecionado_e_recua_os_outros() -> None:
    opt = gc.ranking(_tabela(), rotulo="x", cor="#000", selecionado="261160")
    por_nome = {i["name"]: i["itemStyle"]["opacity"] for i in opt["series"][0]["data"]}
    assert por_nome["Recife"] == 1.0
    assert por_nome["Olinda"] == 0.55


def test_ranking_usa_a_cor_da_classe_do_mapa() -> None:
    from src import mapa

    escala = mapa.escala(_tabela()["valor"], ["#111111", "#222222", "#333333"], metodo="NATURAL")
    opt = gc.ranking(_tabela(), rotulo="x", cor="#000", escala=escala)
    cores = {i["itemStyle"]["color"] for i in opt["series"][0]["data"]}
    assert cores <= set(escala.cores.values())


def test_ranking_vazio_tem_recado_e_nao_estoura() -> None:
    opt = gc.ranking(pd.DataFrame(columns=["chave", "nome", "valor"]), rotulo="x", cor="#000")
    assert "Sem dados" in opt["title"]["text"]
    assert "series" not in opt


def test_opcao_serializa_com_numeros_do_numpy() -> None:
    import numpy as np

    tabela = _tabela().assign(valor=np.array([1, 2, 3], dtype=np.int64))
    texto = json.dumps(gc.ranking(tabela, rotulo="x", cor="#000"), default=gc._serializar)
    assert '"value": 3.0' in texto


def test_clique_novo_navega_e_repetido_nao() -> None:
    ev = {"nonce": "a-1", "name": "Recife", "chave": "261160"}
    assert gc.alvo_do_clique(ev, None) == ("261160", "a-1")
    assert gc.alvo_do_clique(ev, "a-1") == (None, None)
    assert gc.alvo_do_clique({"nonce": "a-2", "name": "Agreste"}, "a-1") == ("Agreste", "a-2")
    assert gc.alvo_do_clique(None, None) == (None, None)


def _composicao() -> pd.DataFrame:
    return pd.DataFrame({
        "categoria": ["Favorável", "Desfavorável", "Não avaliado"],
        "n": [2621.0, 985.0, 744.0],
        "pct": [60.25, 22.64, 17.10],
        "total": [4350.0] * 3,
    })


def test_composicao_por_frequencia_com_o_maior_no_topo() -> None:
    opt = gc.composicao(_composicao(), rotulo="Situação de encerramento", cor="#C1440A")
    assert opt["title"]["text"] == "Situação de encerramento"
    assert opt["yAxis"]["data"] == ["Não avaliado", "Desfavorável", "Favorável"]
    assert opt["xAxis"]["name"] == "% dos casos"
    assert opt["series"][0]["id"] == "composicao"
    topo = opt["series"][0]["data"][-1]
    assert topo["name"] == "Favorável" and topo["value"] == 60.25
    assert "Casos: <b>2.621</b>" in topo["tooltip"] and "% dos casos: <b>60,2</b>" in topo["tooltip"]


def test_composicao_sem_percentual_mostra_contagem() -> None:
    base = _composicao().assign(pct=pd.NA)
    opt = gc.composicao(base, rotulo="x", cor="#000")
    assert opt["xAxis"]["name"] == "Casos"
    assert opt["series"][0]["data"][-1]["value"] == 2621.0
    assert "% dos casos" not in opt["series"][0]["data"][-1]["tooltip"]


def test_composicao_numerica_respeita_a_ordem_dos_dados() -> None:
    base = pd.DataFrame({"categoria": ["0", "1", "2"], "n": [5, 50, 20], "pct": [6.7, 66.7, 26.6], "total": [75] * 3})
    opt = gc.composicao(base, rotulo="x", cor="#000", ordem_dos_dados=True)
    assert opt["yAxis"]["data"] == ["2", "1", "0"]


def test_composicao_vazia_tem_recado() -> None:
    opt = gc.composicao(pd.DataFrame(columns=["categoria", "n", "pct", "total"]), rotulo="x", cor="#000")
    assert "Sem registro" in opt["title"]["text"]


def test_canal_tem_faixa_muda_referencias_e_ano_por_cima() -> None:
    from src.data import canal as mod_canal

    faixa = pd.DataFrame({"mes": [1, 2], "mes_nome": ["janeiro", "fevereiro"], "q1": [1.0, 1.5], "q3": [2.0, 2.5]})
    ref = pd.DataFrame({"mes": [1, 2, 1, 2], "mes_nome": ["janeiro", "fevereiro"] * 2, "ano": [2022, 2022, 2023, 2023], "valor": [1.2, 1.8, 1.9, 2.2]})
    atual = pd.DataFrame({"mes": [1, 2], "mes_nome": ["janeiro", "fevereiro"], "valor": [2.4, 1.1]})
    c = mod_canal.Canal(faixa=faixa, referencia=ref, atual=atual, anos=(2022, 2023))
    opt = gc.canal_endemico(c, rotulo="Incidência", cor="#92400E")
    ids = [s["id"] for s in opt["series"]]
    assert ids == [
        "faixa-base", "faixa", "q1", "q3", "ref-2022", "ref-2023",
        "ref-grupo", "atual",
    ]
    # A faixa é empilhada: base no Q1 e altura Q3 − Q1.
    assert opt["series"][0]["data"] == [1.0, 1.5]
    assert opt["series"][1]["data"] == [1.0, 1.0]
    # As duas séries mudas ficam fora da legenda e do tooltip.
    #
    # Os anos de referência entram como **uma** entrada: a rampa os ordena,
    # mas não os identifica — anos vizinhos ficam em ΔE 6,4 a 8,4 em todas as
    # visões, inclusive a normal. O ano continua nomeado no tooltip.
    assert opt["legend"]["data"] == [
        "Ano selecionado", "Anos anteriores", "Q1", "Q3",
    ]
    assert opt["legend"]["selectedMode"] is False
    assert [s["name"] for s in opt["series"] if s["id"].startswith("ref-2")] == [
        "2022", "2023",
    ]
    assert set(opt["tooltip"]["ocultas"]) == {s["name"] for s in opt["series"][:2]}
    assert opt["series"][-1]["data"] == [2.4, 1.1]
    assert opt["xAxis"]["data"] == ["Jan", "Fev"]


def test_epicurva_usa_eixo_de_tempo_e_destaca_o_ano() -> None:
    base = pd.DataFrame({"ano": [2023, 2023, 2024], "mes": [11, 12, 1], "casos": [10, 12, 9], "ano_mes": ["2023-11", "2023-12", "2024-01"]})
    opt = gc.epicurva(base, rotulo="Casos", cor="#C1440A", ano_em_foco=2024)
    assert opt["xAxis"]["type"] == "time"
    assert opt["series"][0]["data"][0] == ["2023-11-01", 10.0]
    assert opt["series"][1]["id"] == "foco" and opt["series"][1]["data"] == [["2024-01-01", 9.0]]
    assert opt["tooltip"]["ocultas"] == ["Casos em 2024"]


def test_evolucao_anual_destaca_o_ano() -> None:
    base = pd.DataFrame({"ano": [2022, 2023, 2024], "valor": [50.0, 52.0, 55.0]})
    opt = gc.evolucao_anual(base, rotulo="x", cor="#000", ano=2024)
    por_ano = {i["name"]: i["itemStyle"]["opacity"] for i in opt["series"][0]["data"]}
    assert por_ano == {"2022": 0.45, "2023": 0.45, "2024": 1.0}


def _piramide() -> pd.DataFrame:
    return pd.DataFrame({
        "sexo": ["M", "F", "M", "F"],
        "faixa_ord": [0, 0, 5, 5],
        "faixa_etaria": ["0 a 4 anos", "0 a 4 anos", "5 a 9 anos", "5 a 9 anos"],
        "valor": [60.0, 49.0, 39.0, 35.0],
        "pop": [300000.0, 290000.0, 340000.0, 330000.0],
    })


def test_piramide_homens_negativos_a_esquerda_e_eixo_simetrico() -> None:
    opt = gc.piramide(_piramide(), rotulo="Casos")
    homens, mulheres = opt["series"]
    assert homens["id"] == "homens" and mulheres["id"] == "mulheres"
    assert homens["data"][0] == {"name": "0 a 4 anos", "value": -60.0}
    assert mulheres["data"][0]["value"] == 49.0
    assert opt["xAxis"]["min"] == -60.0 and opt["xAxis"]["max"] == 60.0
    assert opt["xAxis"]["absoluto"] is True and opt["tooltip"]["absoluto"] is True
    assert opt["yAxis"]["data"] == ["0 a 4 anos", "5 a 9 anos"]


def test_piramide_por_100_mil_recalcula_e_muda_o_rotulo() -> None:
    opt = gc.piramide(_piramide(), rotulo="Casos", por_100mil=True)
    assert opt["xAxis"]["name"] == "Casos por 100 mil hab."
    assert opt["series"][0]["data"][0]["value"] == -20.0
    assert opt["tooltip"]["casas"] == 1


def test_piramide_vazia_tem_recado() -> None:
    opt = gc.piramide(pd.DataFrame(columns=["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"]), rotulo="Casos")
    assert "Sem dado" in opt["title"]["text"]


def test_barras_empilhadas_com_linha_em_eixo_proprio() -> None:
    base = pd.DataFrame({"ano": [2023, 2024], "pb": [100, 120], "mb": [300, 310], "prop_mb": [75.0, 72.1]})
    opt = gc.barras_empilhadas_com_linha(
        base, barras={"pb": "PB", "mb": "MB"}, linha="prop_mb", rotulo_linha="Proporção MB (%)",
        cores={"pb": "#C4B5FD", "mb": "#7C3AED"}, cor_linha="#000",
    )
    assert [s["id"] for s in opt["series"]] == ["barra-pb", "barra-mb", "linha"]
    assert all(s["stack"] == "anos" for s in opt["series"][:2])
    assert opt["series"][2]["yAxisIndex"] == 1 and len(opt["yAxis"]) == 2
    assert opt["series"][2]["data"] == [{"name": "2023", "value": 75.0}, {"name": "2024", "value": 72.1}]
    assert opt["tooltip"]["casasPorSerie"] == {"Proporção MB (%)": 1, "PB": 0, "MB": 0}


def test_o_rotulo_de_valor_cede_quando_a_coluna_e_estreita() -> None:
    """Onze anos em 318px: os N encostam e viram um borrão.

    No celular a coluna do gráfico tem 318px. "Casos de 0 a 14 anos por ano"
    desenha onze barras ali, cada uma com o N escrito dentro, e o resultado
    saiu como `267220228189194102 95112 97125` — deixa de ser número.

    Quem decide é o componente, não o Python: a largura da tela não chega ao
    servidor. A regra divide a área de desenho pelo número de categorias e,
    nas barras agrupadas, pelas colunas que dividem a categoria; a pilha não
    entra na divisão, porque suas fatias ocupam a mesma coluna.

    Só vale com as categorias no eixo horizontal. Na barra deitada o rótulo
    sai na ponta, e o aperto ali seria de altura.
    """
    js = (gc.DIRETORIO / "grafico.js").read_text(encoding="utf-8")
    assert "function rotuloCabe" in js
    # Some o rótulo, não a série: o valor continua no eixo e no toque.
    assert "s.label.show = false" in js
    assert 'eixo.type !== "category"' in js, "a barra deitada não pode entrar na conta"
    assert "!s.stack" in js, "a pilha divide a categoria e não deve contar como coluna"


def test_o_componente_do_grafico_esta_versionado() -> None:
    """O `?v=` é o que faz o navegador buscar o arquivo novo.

    Sem a marca, quem já abriu o painel continua com o JS em cache e a
    correção não chega — é invisível no deploy e só aparece como "aqui não
    mudou nada".
    """
    html = (gc.DIRETORIO / "index.html").read_text(encoding="utf-8")
    import hashlib
    atual = hashlib.sha1((gc.DIRETORIO / "grafico.js").read_bytes()).hexdigest()[:8]
    assert f"grafico.js?v={atual}" in html, "rode `python -m scripts.versionar_js`"


def test_o_quadro_do_grafico_tem_nome_para_leitor_de_tela() -> None:
    """Mesma razão do mapa: o nome do módulo não diz o que o quadro mostra.

    Aqui o título do próprio gráfico serve quando existe; quando não existe,
    o genérico ainda é melhor que "src ponto grafico underscore componente".
    """
    js = (gc.DIRETORIO / "grafico.js").read_text(encoding="utf-8")
    assert "window.frameElement" in js
    assert "option.title && option.title.text" in js
    assert "Gráfico do painel" in js, "falta o nome de quando não há título"
