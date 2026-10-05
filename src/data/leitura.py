"""Leitores por dataset.

Cada função recebe um ``Escopo`` e devolve dados já normalizados: doença
traduzida para o código do dataset, ``valor`` sem o espaço à esquerda e
código de município no comprimento que cada dataset espera.

Sobre o município: o ``Escopo`` normaliza tudo para o código de 6 dígitos,
que é a chave presente em todos os datasets — ``cod_mun6`` em ``incidence`` e
``geo_id`` nos demais. Cruzar com o ``cod_mun7`` não dá erro, devolve vazio.
Ver docs/contrato-dados.md.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .conexao import ParticaoAusente, caminho, conectar
from .escopo import Escopo, mun6, particao_e_filtro_geo


def _uma_linha(sql: str, params: list) -> dict:
    df = conectar().execute(sql, params).fetchdf()
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def incidencia(esc: Escopo) -> dict:
    """Linha de ``incidence`` para o recorte: casos, cura, população, incidência.

    """
    fonte = caminho(
        "incidence",
        doenca=config.cod_agregado(esc.doenca),
        nivel=esc.nivel,
        ano=esc.ano,
    )
    onde, params = esc.filtro_geo()
    # `SELECT *` de propósito: o esquema varia por doença — a hanseníase traz
    # `casos_grau_0/I/II` e `casos_nao_avaliado`, que a TB não tem — e é uma
    # linha só. Quem consome pega a coluna que existir com `.get`.
    sql = f"""
        SELECT *
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return _uma_linha(sql, params)


def incidencia_0_14(esc: Escopo) -> dict:
    """Linha de ``incidence_0_14``: casos, população e incidência na faixa 0–14."""
    fonte = caminho(
        "incidence_0_14",
        doenca=config.cod_agregado(esc.doenca),
        nivel=esc.nivel,
        ano=esc.ano,
    )
    onde, params = esc.filtro_geo()
    sql = f"""
        SELECT casos_0_14_total, casos_0_14_M, casos_0_14_F, casos_0_14_cura,
               pop_0_14_total, incid_0_14_100k_total
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return _uma_linha(sql, params)



#: Estratos de ``avalia_n`` no ``_cache_ts`` da hanseníase, como vêm gravados
#: (sem acento). É o filtro "grau de incapacidade" do painel de origem.
GRAUS_SERIE = ("Grau zero", "Grau I", "Grau II", "Nao avaliado", "Nao informado")


def serie_mensal(esc: Escopo, grau: str | None = None) -> pd.DataFrame:
    """Série mensal de ``_cache_ts`` para o ano do escopo, uma linha por mês.

    **Agrega por mês.** Para a hanseníase o dataset vem estratificado por
    ``avalia_n`` — cinco linhas por mês, uma por grau de incapacidade —, e
    ler cru dava 60 pontos no gráfico de 12. A população é a mesma em todos
    os estratos, então entra por ``max``; a taxa é recalculada da soma.

    ``grau`` restringe a um estrato (:data:`GRAUS_SERIE`); ``None`` soma todos.
    """
    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho(
        "_cache_ts",
        nivel=particao,
        doenca=config.cod_agregado(esc.doenca),
        ano=esc.ano,
    )
    condicoes: list[str] = [onde_geo] if onde_geo else []
    params: list = list(params_geo)
    if grau:
        if grau not in GRAUS_SERIE:
            raise ValueError(f"Grau inválido: {grau!r}. Esperado um de {GRAUS_SERIE}.")
        condicoes.append("avalia_n = ?")
        params.append(grau)
    onde = f" WHERE {' AND '.join(condicoes)}" if condicoes else ""
    sql = f"""
        SELECT mes, any_value(mes_nome) AS mes_nome,
               sum(casos) AS casos, sum(casos_cura) AS casos_cura, max(pop_total) AS pop_total,
               sum(casos) / nullif(max(pop_total), 0) * 100000 AS incid_100k
        FROM read_parquet('{fonte}', hive_partitioning=true){onde}
        GROUP BY mes ORDER BY mes
    """
    return conectar().execute(sql, params).fetchdf()


def serie_mensal_casos(esc: Escopo, ano_min: int, ano_max: int) -> pd.DataFrame:
    """Casos por ano e mês num intervalo de anos, numa consulta só.

    Existe para a epicurva, que atravessa dez anos. Ela montava a série ano a
    ano chamando `serie_dupla`, e cada ano custava **duas** leituras do
    `_cache_ts` — uma para casos, outra para incidência — mais duas do
    `incidence` quando o recorte é uma região. Dez anos numa macrorregião eram
    quarenta consultas para desenhar uma linha de contagem.

    Aqui a partição `ano` fica **fora** do caminho, então o glob pega todos os
    anos de uma vez e o `WHERE` recorta o intervalo. É a exceção à regra de
    podar pela partição (docs/contrato-dados.md): vale porque o que se lê é
    justamente a série inteira, e os arquivos de um mesmo nível têm o mesmo
    esquema.

    Só `casos`: a epicurva desenha contagem, e trazer população para calcular
    uma incidência que ninguém usa era metade do custo.

    Colunas ``ano``, ``mes``, ``mes_nome``, ``casos``.
    """
    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho("_cache_ts", nivel=particao, doenca=config.cod_agregado(esc.doenca))
    sql = f"""
        SELECT ano, mes, any_value(mes_nome) AS mes_nome, sum(casos) AS casos
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE ano BETWEEN ? AND ?
    """
    params = [ano_min, ano_max, *params_geo]
    if onde_geo:
        sql += f" AND {onde_geo}"
    df = conectar().execute(sql + " GROUP BY ano, mes ORDER BY ano, mes", params).fetchdf()
    if df.empty:
        return pd.DataFrame(columns=["ano", "mes", "mes_nome", "casos"])
    df["ano"] = df["ano"].astype(int)
    return df


def variavel_sinan(esc: Escopo, variavel: str) -> pd.DataFrame:
    """Distribuição de uma variável do SINAN no recorte.

    O ``valor`` bruto vem com espaço à esquerda (``" 2"``, não ``"2"``). Aqui ele
    sai já com ``trim`` aplicado — sem isso, todo filtro por código falha em
    silêncio. Ver docs/contrato-dados.md, armadilha 3.

    **Filtra ``sexo = 'TOTAL'``**, e essa linha é o que separa a contagem certa
    da dobrada. O dataset traz M, F, I *e* uma linha TOTAL que já é a soma
    delas — conferido em 9,97 milhões de combinações de nível, geografia, ano
    e variável, sem uma única divergência. Somar tudo, como fazíamos, dá
    exatamente o dobro.

    Proporção não sentia — numerador e denominador dobravam juntos, e é por
    isso que HIV e interrupção batiam com o painel em R. Contagem sentia: o
    painel de composição exibia o dobro dos casos, e o limiar de supressão de
    base pequena valia metade do que aparentava.
    """
    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho(
        "sinan_landing",
        doenca=config.cod_landing(esc.doenca),
        nivel=particao,
        ano=esc.ano,
    )
    sql = f"""
        SELECT trim(valor) AS valor, any_value(valor_lbl) AS valor_lbl, sum(n) AS n
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE variavel = ? AND sexo = 'TOTAL'
    """
    params: list = [variavel]
    if onde_geo:
        sql += f" AND {onde_geo}"
        params += params_geo
    sql += " GROUP BY 1 ORDER BY n DESC"
    return conectar().execute(sql, params).fetchdf()


def anos_disponiveis(doenca: str) -> list[int]:
    """Anos com dado em ``incidence``, para o slider dar *snap*."""
    fonte = caminho("incidence", doenca=config.cod_agregado(doenca), nivel="BR")
    sql = f"""
        SELECT DISTINCT ano FROM read_parquet('{fonte}', hive_partitioning=true)
        ORDER BY ano
    """
    return [int(a) for a in conectar().execute(sql).fetchdf()["ano"]]


def piramide(esc: Escopo, tipo: str = "CASOS") -> pd.DataFrame:
    """Pirâmide etária: evento e população por sexo e faixa.

    ``tipo`` é ``CASOS`` ou ``CURA``.
    """
    tipo = str(tipo or "CASOS").strip().upper()
    if tipo not in ("CASOS", "CURA"):
        raise ValueError(f"Tipo inválido: {tipo!r}. Esperado CASOS ou CURA.")

    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho(
        "piramides",
        nivel=particao,
        tipo=tipo,
        doenca=config.cod_agregado(esc.doenca),
        ano=esc.ano,
    )
    # Somado por faixa e sexo: numa região de saúde são vários municípios, e
    # a razão é recalculada da soma. Sem região, o `GROUP BY` é inócuo.
    sql = f"""
        SELECT sexo, faixa_ord, any_value(faixa_etaria) AS faixa_etaria,
               sum(valor) AS valor, sum(pop) AS pop,
               sum(valor) / nullif(sum(pop), 0) * 100000 AS ratio
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = list(params_geo)
    if onde_geo:
        sql += f" WHERE {onde_geo}"
    sql += " GROUP BY sexo, faixa_ord ORDER BY faixa_ord, sexo"
    return conectar().execute(sql, params).fetchdf()


def casos_novos(esc: Escopo) -> float | None:
    """Casos novos do recorte.

    ``cases_new`` só traz ``cod_mun6`` — a UF é derivada dos dois primeiros
    dígitos, porque o dataset não tem coluna de UF.
    """
    fonte = caminho("cases_new", doenca=config.cod_agregado(esc.doenca), ano=esc.ano)
    sql = f"SELECT sum(casos_novos) FROM read_parquet('{fonte}', hive_partitioning=true)"
    params: list = []
    if esc.nivel == "UF":
        sql += " WHERE cod_mun6 LIKE ?"
        params.append(config.codigo_uf(esc.uf) + "%")
    elif esc.nivel == "MUN":
        sql += " WHERE cod_mun6 = ?"
        params.append(mun6(esc.mun))
    linha = conectar().execute(sql, params).fetchone()
    return None if linha is None else linha[0]



def dicionario(doenca: str, variavel: str | None = None) -> pd.DataFrame:
    """Dicionário de código → rótulo das variáveis do SINAN.

    O ``valor`` sai com ``trim`` aplicado. Cuidado: o dicionário registra
    ``" 3"`` e ``"03"`` como entradas distintas para o mesmo código, então o
    resultado pode trazer duplicatas legítimas do dado de origem.
    """
    fonte = caminho("sinan_dict", doenca=config.cod_landing(doenca))
    sql = f"""
        SELECT variavel, trim(valor) AS valor, valor_lbl, n_total, n_years
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    params: list = []
    if variavel:
        sql += " WHERE variavel = ?"
        params.append(variavel)
    return conectar().execute(sql + " ORDER BY variavel, valor", params).fetchdf()


#: Colunas de `incidence` que servem uma métrica diretamente.
_COLUNA_DIRETA = {
    "casos": "casos_total",
    "cura": "casos_cura",
    "pop": "pop_total",
    "incid": "incid_100k_total",
}

#: Métricas da faixa 0–14, que moram em `incidence_0_14`.
_COLUNA_0_14 = {
    "casos_0_14": "casos_0_14_total",
    "pop_0_14": "pop_0_14_total",
    "taxa_det_0_14": "incid_0_14_100k_total",
}


#: Razões que saem de duas colunas do próprio `incidence`, sem outra fonte.
#:
#: `cura_pct` morava aqui, como `casos_cura / casos_total`. Saiu daqui
#: quando o card passou a usar o denominador do Ministério — ver
#: :data:`_RAZAO_EM_DESFECHO`. O dicionário fica, vazio, porque o caminho que
#: ele serve continua válido para a próxima razão que nascer no `incidence`.
_RAZAO_EM_INCIDENCE: dict[str, tuple[str, str]] = {}

#: Abaixo deste total, o percentual não é calculado.
#:
#: Não é uma regra de privacidade que alguém nos impôs — é que percentual de
#: base minúscula não significa nada. "100% dos casos são do sexo masculino"
#: apoiado numa pessoa é ruído apresentado como achado, e num município com
#: um caso no ano — 993 dos 4.148 com notificação em 2024 — o cruzamento de
#: município, sexo, idade e agravo deixa de ser agregado na prática.
#:
#: A supressão fica aqui, e não no gráfico, para que nenhum consumidor da
#: camada de dados consiga exibir o percentual por engano.
MINIMO_PARA_PERCENTUAL = 5

def valores_por_geografia(esc: Escopo, metrica: str) -> pd.Series:
    """Valor da métrica para cada geografia dentro do escopo, para o mapa.

    O nível do ``Escopo`` diz o que está **selecionado**; o mapa desenha um
    nível abaixo. No Brasil pinta as UFs; numa UF, os municípios dela.

    O índice é a chave da camada geográfica: sigla no nível de UF, código de
    6 dígitos no de município.
    """
    metrica = str(metrica or "incid")
    desce_para_municipio = esc.nivel in ("UF", "MUN")

    if desce_para_municipio:
        fonte = caminho(
            "incidence",
            doenca=config.cod_agregado(esc.doenca),
            nivel="MUN",
            ano=esc.ano,
        )
        chave, onde, params = "cod_mun6", " WHERE uf = ?", [esc.uf]
    else:
        fonte = caminho(
            "incidence", doenca=config.cod_agregado(esc.doenca), nivel="UF", ano=esc.ano
        )
        chave, onde, params = "uf", "", []

    if metrica in ("casos", "incid") and esc.doenca == config.HANSENIASE and desce_para_municipio:
        # Hanseníase: casos novos pela definição do MS (`MODOENTR = 1`),
        # não `casos_total`, que na extração é toda entrada no registro.
        # Ver docs/paridade-hanseniase.md §1.
        pop = conectar().execute(
            f"SELECT cod_mun6, pop_total FROM read_parquet('{fonte}', hive_partitioning=true){onde}",
            params,
        ).fetchdf().set_index("cod_mun6")["pop_total"]
        novos = casos_novos_por_municipio(esc).set_index("cod_mun6")["casos"]
        casos = novos.reindex(pop.index).fillna(0.0)
        if metrica == "casos":
            return casos
        return casos / pop.replace(0, pd.NA) * 100_000

    if metrica in _COLUNA_DIRETA:
        coluna = _COLUNA_DIRETA[metrica]
        sql = f"SELECT {chave}, {coluna} AS valor FROM read_parquet('{fonte}', hive_partitioning=true){onde}"
        df = conectar().execute(sql, params).fetchdf()
        return df.set_index(chave)["valor"]

    if metrica in _COLUNA_0_14:
        # Mesma partição e mesma chave, outro dataset: `incidence_0_14` tem
        # o mesmo layout do `incidence` para a faixa etária.
        fonte14 = caminho(
            "incidence_0_14",
            doenca=config.cod_agregado(esc.doenca),
            nivel="MUN" if desce_para_municipio else "UF",
            ano=esc.ano,
        )
        coluna = _COLUNA_0_14[metrica]
        sql = f"SELECT {chave}, {coluna} AS valor FROM read_parquet('{fonte14}', hive_partitioning=true){onde}"
        df = conectar().execute(sql, params).fetchdf()
        return df.set_index(chave)["valor"]

    if metrica in _RAZAO_EM_INCIDENCE:
        num, den = _RAZAO_EM_INCIDENCE[metrica]
        df = conectar().execute(
            f"SELECT {chave}, {num} AS num, {den} AS den "
            f"FROM read_parquet('{fonte}', hive_partitioning=true){onde}",
            params,
        ).fetchdf()
        valor = df["num"] / df["den"].replace(0, pd.NA) * 100
        return pd.Series(valor.values, index=df[chave])

    # As demais (0-14, HIV, interrupção) exigem outros datasets e entram
    # quando o mapa passar a aceitá-las. Melhor um mapa vazio e honesto do
    # que um mapa colorido com a métrica errada.
    return pd.Series(dtype=float)


def componentes_municipais(esc: Escopo) -> pd.DataFrame:
    """Casos, cura e população por município da UF.

    Base para agregar por macrorregião e região de saúde: as taxas precisam
    ser recalculadas a partir das somas, não tiradas como média das taxas
    municipais.
    """
    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel="MUN", ano=esc.ano
    )
    juncao = conectar().execute(
        f"SELECT cod_mun6, casos_total AS casos, casos_cura AS cura, "
        f"pop_total AS pop FROM read_parquet('{fonte}', hive_partitioning=true) "
        f"WHERE uf = ?",
        [esc.uf],
    ).fetchdf()

    if esc.doenca == config.HANSENIASE:
        # Casos novos do MS no lugar de `casos_total` — a mesma troca de
        # `valores_por_geografia`, para macro e região somarem o mesmo.
        novos = casos_novos_por_municipio(esc).set_index("cod_mun6")["casos"]
        juncao["casos"] = juncao["cod_mun6"].map(novos).fillna(0.0)

    # Faixa 0–14, para a taxa de detecção infantil por macro e região de
    # saúde sair da soma dos componentes, como as demais.
    fonte14 = caminho(
        "incidence_0_14", doenca=config.cod_agregado(esc.doenca), nivel="MUN", ano=esc.ano
    )
    faixa = conectar().execute(
        f"SELECT cod_mun6, casos_0_14_total AS casos_0_14, pop_0_14_total AS pop_0_14 "
        f"FROM read_parquet('{fonte14}', hive_partitioning=true) WHERE uf = ?",
        [esc.uf],
    ).fetchdf()
    juncao = juncao.merge(faixa, on="cod_mun6", how="left")
    return juncao.set_index("cod_mun6")


def valores_por_regiao(
    esc: Escopo, metrica: str, nivel: str, macro: str | None = None
) -> pd.Series:
    """Valor da métrica por macrorregião ou região de saúde da UF do escopo.

    ``macro`` restringe as regiões de saúde às de uma macrorregião — é o que
    o clique numa macro faz no mapa: as regiões de fora dela saem, em vez de
    continuarem pintadas como se nada tivesse sido escolhido.
    """
    from . import recortes

    valores = recortes.agregar(
        componentes_municipais(esc), metrica, nivel, uf=esc.uf or recortes.UF
    )
    if macro and str(nivel).lower().startswith("mic") and not valores.empty:
        dentro = {recortes._chave(m) for m in recortes.micros(macro, uf=esc.uf or recortes.UF)}
        valores = valores[[recortes._chave(i) in dentro for i in valores.index]]
    return valores


def serie_anual(esc: Escopo, metrica: str = "casos") -> pd.DataFrame:
    """Série histórica anual da métrica no recorte, vinda de ``incidence``.

    Diferente de :func:`serie_mensal`, esta é por **residência**, igual aos
    KPIs — `incidence` e `_cache_ts` usam critérios geográficos diferentes.
    """
    if metrica not in _COLUNA_DIRETA:
        return pd.DataFrame(columns=["ano", "valor"])
    coluna = _COLUNA_DIRETA[metrica]
    particao, onde, params = particao_e_filtro_geo(esc, col_mun="cod_mun6")
    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel=particao
    )
    if metrica in ("casos", "incid") and esc.doenca == config.HANSENIASE:
        return _serie_anual_casos_novos_ms(esc, metrica, fonte, onde, params)
    # Taxa recalculada da soma quando há região: média de taxas municipais
    # pesaria Petrolina igual a um município de dois mil habitantes.
    if esc.municipios and metrica == "incid":
        expressao = "sum(casos_total) / nullif(sum(pop_total), 0) * 100000"
    else:
        expressao = f"sum({coluna})"
    sql = f"SELECT ano, {expressao} AS valor FROM read_parquet('{fonte}', hive_partitioning=true)"
    if onde:
        sql += f" WHERE {onde}"
    return conectar().execute(sql + " GROUP BY ano ORDER BY ano", list(params)).fetchdf()


def ranking(
    esc: Escopo, metrica: str, top_n: int = 15, recorte: str = "MUN",
    macro: str | None = None,
) -> pd.DataFrame:
    """As ``top_n`` maiores geografias do nível abaixo do escopo.

    Mesma fonte que o mapa usa — os dois mostram o mesmo recorte, e ler de
    lugares diferentes seria como o card e a série, que divergem por isso.

    Colunas: ``chave`` (sigla de UF, código de 6 dígitos ou nome de região),
    ``nome`` e ``valor``. Empates são desempatados pelo nome, para a ordem não
    variar entre execuções.

    ``recorte`` acompanha o do mapa: em ``MACRO`` ou ``MICRO`` a lista passa a
    ser de regiões, não de municípios.
    """
    from . import geo

    # O ranking segue o **mesmo recorte do mapa**. Enquanto nao seguia, o
    # mapa mostrava macrorregioes e o ranking listava municipios ao lado, com
    # o titulo dizendo "municipios" -- dois recortes na mesma linha, e as
    # cores, que saem da escala do mapa, deixavam de casar.
    if recorte in ("MACRO", "MICRO") and esc.nivel != "BR":
        valores = valores_por_regiao(
            esc, metrica, "macro" if recorte == "MACRO" else "micro", macro=macro
        )
        nomes = {chave: chave for chave in valores.index}
    else:
        valores = valores_por_geografia(esc, metrica)
        if esc.nivel == "BR":
            nomes = {sigla: sigla for sigla in valores.index}
        else:
            camada = geo.municipios(esc.uf)
            nomes = dict(zip(camada["cod_mun6"], camada["nome_mun"], strict=True))
            # **So quem tem poligono na camada.** O `sinan_landing` traz, sob
            # `uf='PE'`, dez municipios de outros estados -- 13 registros de
            # 4.350, sem nome resolvido na origem. O mapa nunca os mostrou,
            # porque nao ha geometria para pintar; o ranking mostrava, com o
            # codigo cru no lugar do nome. Com um caso curado eles subiam ao
            # topo da cura com 100%.
            valores = valores[valores.index.isin(nomes)]

    if valores.empty:
        return pd.DataFrame(columns=["chave", "nome", "valor"])

    tabela = pd.DataFrame(
        {
            "chave": valores.index,
            "nome": [nomes.get(k, str(k)) for k in valores.index],
            "valor": pd.to_numeric(valores.to_numpy(), errors="coerce"),
        }
    ).dropna(subset=["valor"])

    return (
        tabela.sort_values(["valor", "nome"], ascending=[False, True])
        .head(int(top_n))
        .reset_index(drop=True)
    )


#: Métrica → coluna de ``_cache_ts``. As ausentes precisam de cálculo ou de
#: outro dataset, e a série avisa em vez de mostrar a métrica errada.
_COLUNA_MENSAL = {
    "casos": "casos",
    "cura": "casos_cura",
    "pop": "pop_total",
    "incid": "incid_100k",
}


def serie_mensal_metrica(esc: Escopo, metrica: str, grau: str | None = None) -> pd.DataFrame:
    """Série mensal da métrica pedida, com colunas ``mes``, ``mes_nome``, ``valor``.

    Métricas derivadas são recalculadas mês a mês a partir dos componentes —
    tirar a taxa do total anual e repeti-la nos meses esconderia a
    sazonalidade, que é justamente o que este gráfico existe para mostrar.
    """
    bruto = serie_mensal(esc, grau)
    if bruto.empty:
        return pd.DataFrame(columns=["mes", "mes_nome", "valor"])

    if metrica in _COLUNA_MENSAL:
        valor = bruto[_COLUNA_MENSAL[metrica]]
    else:
        return pd.DataFrame(columns=["mes", "mes_nome", "valor"])

    return bruto.assign(valor=valor)[["mes", "mes_nome", "valor"]]


def serie_dupla(esc: Escopo, horizonte: str = "meses", grau: str | None = None) -> pd.DataFrame:
    """Casos e incidência lado a lado, para o gráfico duplo da tuberculose."""
    if horizonte == "meses":
        casos = serie_mensal_metrica(esc, "casos", grau)
        incid = serie_mensal_metrica(esc, "incid", grau)
        if casos.empty or incid.empty:
            return pd.DataFrame(columns=["mes", "mes_nome", "casos", "incid"])
        return casos.rename(columns={"valor": "casos"}).assign(
            incid=incid["valor"].to_numpy()
        )

    casos = serie_anual(esc, "casos")
    incid = serie_anual(esc, "incid")
    if casos.empty or incid.empty:
        return pd.DataFrame(columns=["ano", "casos", "incid"])
    return casos.rename(columns={"valor": "casos"}).merge(
        incid.rename(columns={"valor": "incid"}), on="ano"
    )


#: Ordem canônica das faixas, vinda de `piramides`.
FAIXAS = (
    (0, "0 a 4 anos"), (5, "5 a 9 anos"), (10, "10 a 14 anos"),
    (15, "15 a 19 anos"), (20, "20 a 29 anos"), (30, "30 a 39 anos"),
    (40, "40 a 49 anos"), (50, "50 a 59 anos"), (60, "60 a 69 anos"),
    (70, "70 a 79 anos"), (80, "80 anos ou mais"),
)

#: Tipos de pirâmide e de onde cada um vem hoje.
#:
#: `piramides` traz CURA zerada para tuberculose — o dado existe na fonte,
#: mas some no pipeline. Ver docs/perguntas-equipe-r.md.
#:
#: Óbito saiu junto com o resto do SIM. A hanseníase não
#: mostra óbito em lugar nenhum do painel.
#:
#: Cura não tem: `incidence` quebra por sexo mas não por idade, e
#: `incidence_0_14` cobre só uma faixa. Precisa do banco.
#: Colunas que `piramide_completa` sempre devolve, mesmo vazia. O contrato
#: estava escrito em três lugares dentro da própria função.
COLUNAS_PIRAMIDE = ["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"]

FONTE_PIRAMIDE = {
    "CASOS": "piramides",
    "CURA": None,
}


def piramide_completa(esc: Escopo, tipo: str = "CASOS") -> pd.DataFrame:
    """Pirâmide etária por sexo, com todas as faixas.

    Devolve ``sexo``, ``faixa_ord``, ``faixa_etaria``, ``valor`` e ``pop``,
    com as onze faixas sempre presentes — faixa sem registro entra zerada,
    para a pirâmide não ficar com degraus faltando.
    """
    tipo = str(tipo or "CASOS").strip().upper()
    if tipo not in FONTE_PIRAMIDE:
        raise ValueError(f"Tipo inválido: {tipo!r}. Esperado {sorted(FONTE_PIRAMIDE)}.")

    if FONTE_PIRAMIDE[tipo] is None:
        return pd.DataFrame(columns=COLUNAS_PIRAMIDE)

    bruto = piramide(esc, "CASOS")
    if bruto.empty:
        return pd.DataFrame(columns=COLUNAS_PIRAMIDE)
    base = bruto[["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"]]

    # Completa as faixas ausentes com zero, por sexo.
    completo = pd.DataFrame(
        [
            {"sexo": s, "faixa_ord": ordem, "faixa_etaria": rotulo}
            for s in sorted(base["sexo"].dropna().unique())
            for ordem, rotulo in FAIXAS
        ]
    )
    juncao = completo.merge(
        base, on=["sexo", "faixa_ord", "faixa_etaria"], how="left"
    )
    juncao["valor"] = juncao["valor"].fillna(0)
    return juncao.sort_values(["faixa_ord", "sexo"]).reset_index(drop=True)




#: Códigos que o SINAN usa para "ignorado/branco" nos campos categóricos.
#: O boletim os imprime **primeiro**, e não escondidos no fim.
CODIGOS_IGNORADO = frozenset({"9", "99", "999", "0"})


def composicao(
    esc: Escopo,
    variavel: str,
    rotulos: dict[str, str] | None = None,
    numerica: bool = False,
    ordem: str = "frequencia",
) -> pd.DataFrame:
    """Distribuição de uma variável do SINAN, com percentual quando cabe.

    Devolve ``categoria``, ``n``, ``pct`` e ``total``. ``pct`` vem nulo
    inteiro quando ``total`` não alcança :data:`MINIMO_PARA_PERCENTUAL` — aí
    só a contagem é publicável.

    ``rotulos`` (código → nome) cobre o que o ``sinan_dict`` não traz —
    ``FORMACLINI`` e ``EPIS_RACIO`` da hanseníase vêm sem ``valor_lbl``, e
    descartá-las por isso apagava a variável inteira do painel. Sem rótulo de
    nenhuma fonte, o código cru é a categoria: número sem nome é melhor que
    variável sumida.

    ``numerica`` é para variáveis em que o valor **é** a quantidade
    (contatos, nervos, doses): a categoria é o próprio valor e a ordem é
    numérica, não por frequência.
    """
    bruto = variavel_sinan(esc, variavel)
    if bruto.empty:
        return pd.DataFrame(columns=["categoria", "n", "pct", "total"])

    rotulos = rotulos or {}
    dados = bruto[["valor", "valor_lbl", "n"]].copy()
    if numerica:
        dados["categoria"] = dados["valor"]
    else:
        dados["categoria"] = dados["valor_lbl"].where(
            dados["valor_lbl"].notna(), dados["valor"].map(lambda v: rotulos.get(v, v))
        )
    dados["n"] = pd.to_numeric(dados["n"], errors="coerce").fillna(0)
    dados = dados[dados["n"] > 0]
    if dados.empty:
        return pd.DataFrame(columns=["categoria", "n", "pct", "total"])

    total = float(dados["n"].sum())
    dados["pct"] = (dados["n"] / total * 100) if total >= MINIMO_PARA_PERCENTUAL else pd.NA
    dados["total"] = total
    if numerica:
        dados["_ordem"] = pd.to_numeric(dados["valor"], errors="coerce")
        dados = dados.sort_values("_ordem")
    elif ordem == "codigo":
        # A ordem do **campo**, como o boletim publica: ignorado/branco
        # primeiro, depois os códigos em ordem. Ordenar por frequência, que
        # era o que fazíamos, muda a posição da categoria conforme o recorte —
        # "Ign/Branco" salta do fim para o meio ao clicar num município, e
        # quem compara dois recortes lado a lado compara posições diferentes.
        codigo = dados["valor"].astype(str).str.strip()
        dados["_ign"] = (~codigo.str.fullmatch(r"\d+")) | codigo.isin(CODIGOS_IGNORADO)
        dados["_ordem"] = pd.to_numeric(codigo, errors="coerce")
        dados = dados.sort_values(["_ign", "_ordem"], ascending=[False, True])
    else:
        dados = dados.sort_values("n", ascending=False)
    return dados[["categoria", "n", "pct", "total"]].reset_index(drop=True)


def meses_com_dado(doenca: str, ano: int) -> int:
    """Quantos meses do ano já têm notificação, no Brasil.

    Serve para marcar ano parcial. Sem esse aviso o painel mente por omissão:
    em 2025 a incidência aparece como 0,83 contra 40,42 em 2024, e quem olha
    conclui que a tuberculose despencou, não que o ano está pela metade.
    """
    try:
        fonte = caminho(
            "_cache_ts",
            nivel="BR",
            doenca=config.cod_agregado(doenca),
            ano=int(ano),
        )
    except ParticaoAusente:
        return 0
    sql = f"""
        SELECT count(DISTINCT mes)
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE casos > 0
    """
    linha = conectar().execute(sql).fetchone()
    return int(linha[0]) if linha and linha[0] else 0


def componentes_de_regiao(esc: Escopo, municipios: list[str]) -> dict:
    """Somas municipais de tudo que os KPIs precisam, para um conjunto de
    municípios da UF do escopo — uma macrorregião ou uma região de saúde.

    É o que faz os sete cards mudarem ao entrar numa macro: o painel de
    origem só muda detecção e casos, e os demais continuam mostrando o
    estado. Aqui todos saem da mesma soma. Junta três fontes, todas ao
    nível de município: `incidence` (casos, cura, população, graus),
    `incidence_0_14` e `sinan_landing` (`CLASSOPERA`, para a proporção MB).
    """
    codigos = [mun6(m) for m in municipios]
    if not codigos:
        return {}
    marcadores = ", ".join("?" for _ in codigos)

    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel="MUN", ano=esc.ano
    )
    base = _uma_linha(
        f"""
        SELECT sum(casos_total) AS casos_total, sum(casos_cura) AS casos_cura,
               sum(pop_total) AS pop_total,
               sum(casos_grau_0) AS casos_grau_0, sum(casos_grau_I) AS casos_grau_I,
               sum(casos_grau_II) AS casos_grau_II,
               sum(casos_nao_avaliado) AS casos_nao_avaliado
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE uf = ? AND cod_mun6 IN ({marcadores})
        """,
        [esc.uf, *codigos],
    )

    fonte14 = caminho(
        "incidence_0_14", doenca=config.cod_agregado(esc.doenca), nivel="MUN", ano=esc.ano
    )
    faixa = _uma_linha(
        f"""
        SELECT sum(casos_0_14_total) AS casos_0_14_total,
               sum(pop_0_14_total) AS pop_0_14_total
        FROM read_parquet('{fonte14}', hive_partitioning=true)
        WHERE uf = ? AND cod_mun6 IN ({marcadores})
        """,
        [esc.uf, *codigos],
    )

    landing = caminho(
        "sinan_landing", doenca=config.cod_landing(esc.doenca), nivel="MUN", ano=esc.ano
    )
    novos = conectar().execute(
        f"""
        SELECT sum(n) FROM read_parquet('{landing}', hive_partitioning=true)
        WHERE variavel = 'MODOENTR' AND sexo = 'TOTAL' AND trim(valor) = ?
          AND geo_id IN ({marcadores})
        """,
        [CASO_NOVO_MS, *codigos],
    ).fetchone()
    return {
        **base, **faixa,
        "casos_novos_ms": float(novos[0]) if novos and novos[0] is not None else 0.0,
    }


def serie_classificacao_operacional(esc: Escopo) -> pd.DataFrame:
    """MB e PB por ano de diagnóstico, com a proporção de multibacilares.

    O gráfico de rodapé do painel de origem. Uma consulta para todos os anos:
    a partição de `sinan_landing` é doença/nível/ano, e omitir o ano varre
    todos. Colunas ``ano``, ``mb``, ``pb``, ``prop_mb`` (%).
    """
    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho(
        "sinan_landing", doenca=config.cod_landing(esc.doenca), nivel=particao
    )
    sql = f"""
        SELECT ano,
               sum(n) FILTER (WHERE trim(valor) = '2') AS mb,
               sum(n) FILTER (WHERE trim(valor) = '1') AS pb
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE variavel = 'CLASSOPERA' AND sexo = 'TOTAL'
    """
    if onde_geo:
        sql += f" AND {onde_geo}"
    df = conectar().execute(sql + " GROUP BY ano ORDER BY ano", list(params_geo)).fetchdf()
    if df.empty:
        return pd.DataFrame(columns=["ano", "mb", "pb", "prop_mb"])
    df["mb"] = df["mb"].fillna(0).astype(float)
    df["pb"] = df["pb"].fillna(0).astype(float)
    df["prop_mb"] = 100 * df["mb"] / (df["mb"] + df["pb"]).replace(0, pd.NA)
    return df


def serie_qualidade(esc: Escopo) -> pd.DataFrame:
    """Os indicadores de acompanhamento do programa, ano a ano.

    É o que os Gráficos 10 a 13 do boletim publicam, na mesma conta dos cards
    de qualidade: contatos examinados sobre registrados, cura e abandono sobre
    as saídas, GIF avaliado e GIF II sobre os casos.

    Colunas ``ano``, ``examinados``, ``registrados``, ``contatos_pct``,
    ``cura_pct``, ``abandono_pct``, ``gif_avaliado_pct`` e ``grau2_pct``.

    **Coorte aberta zera só os três de acompanhamento** — contatos, cura e
    abandono —, pela mesma regra dos cards (`kpis.COBERTURA_MINIMA_COORTE`).
    O grau de incapacidade é preenchido **no diagnóstico**, não ao longo do
    tratamento: suprimi-lo no ano corrente esconderia dado que já existe.

    ``CONTEXAM`` e ``CONTREG`` guardam a quantidade por caso, não um código,
    então o total do ano é a soma ponderada — ver :func:`soma_ponderada`.
    """
    from . import kpis

    particao, onde_geo, params_geo = particao_e_filtro_geo(esc)
    fonte = caminho(
        "sinan_landing", doenca=config.cod_landing(esc.doenca), nivel=particao
    )
    # `TRY_CAST` e não `CAST`: `valor` é texto e traz "ign" e vazios em alguns
    # anos — um `CAST` derruba a consulta inteira por causa de uma linha.
    sql = f"""
        SELECT ano,
               sum(TRY_CAST(trim(valor) AS DOUBLE) * n)
                   FILTER (WHERE variavel = 'CONTEXAM') AS examinados,
               sum(TRY_CAST(trim(valor) AS DOUBLE) * n)
                   FILTER (WHERE variavel = 'CONTREG') AS registrados,
               sum(n) FILTER (WHERE variavel = 'TPALTA_N') AS saidas,
               sum(n) FILTER (
                   WHERE variavel = 'TPALTA_N' AND trim(valor) = '{CURA_TPALTA}'
               ) AS curas,
               sum(n) FILTER (
                   WHERE variavel = 'TPALTA_N' AND trim(valor) = '{ABANDONO_TPALTA}'
               ) AS abandonos
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE variavel IN ('CONTEXAM', 'CONTREG', 'TPALTA_N') AND sexo = 'TOTAL'
    """
    if onde_geo:
        sql += f" AND {onde_geo}"
    df = conectar().execute(sql + " GROUP BY ano ORDER BY ano", list(params_geo)).fetchdf()
    if df.empty:
        return pd.DataFrame(columns=COLUNAS_QUALIDADE)
    df["ano"] = df["ano"].astype(int)

    graus = _serie_graus(esc).set_index("ano")
    casos = graus["casos"].reindex(df["ano"]).to_numpy()
    saidas = df["saidas"].astype("Float64")
    cobertura = saidas / pd.Series(casos, index=df.index).replace(0, pd.NA)
    aberta = cobertura < kpis.COBERTURA_MINIMA_COORTE

    df["contatos_pct"] = 100 * df["examinados"] / df["registrados"].replace(0, pd.NA)
    df["cura_pct"] = 100 * df["curas"] / saidas.replace(0, pd.NA)
    df["abandono_pct"] = 100 * df["abandonos"] / saidas.replace(0, pd.NA)
    df.loc[aberta, ["contatos_pct", "cura_pct", "abandono_pct"]] = pd.NA

    # Grau de incapacidade: preenchido no diagnóstico, então não depende da
    # coorte fechar. `gif_avaliado_pct` é sobre todos os casos (é cobertura de
    # preenchimento); `grau2_pct` repete o denominador da origem, que inclui
    # "não avaliado" — ver docs/paridade-hanseniase.md §2.
    for coluna in ("avaliados", "base_grau2", "grau_II"):
        df[coluna] = graus[coluna].reindex(df["ano"]).to_numpy()
    df["gif_avaliado_pct"] = 100 * df["avaliados"] / pd.Series(casos, index=df.index).replace(0, pd.NA)
    df["grau2_pct"] = 100 * df["grau_II"] / df["base_grau2"].replace(0, pd.NA)
    return df[COLUNAS_QUALIDADE]


#: Código de `TPALTA_N` para cura e para abandono.
CURA_TPALTA = "1"
ABANDONO_TPALTA = "7"

#: O que :func:`serie_qualidade` devolve, na ordem.
COLUNAS_QUALIDADE = [
    "ano", "examinados", "registrados", "contatos_pct",
    "cura_pct", "abandono_pct", "gif_avaliado_pct", "grau2_pct",
]


def _serie_graus(esc: Escopo) -> pd.DataFrame:
    """Casos e graus de incapacidade por ano, do `incidence`.

    ``casos`` conta **todas as entradas**: é o denominador com que as saídas
    se comparam para saber se a coorte fechou, e o que a origem usa no grau.
    """
    particao, onde, params = particao_e_filtro_geo(esc, col_mun="cod_mun6")
    fonte = caminho(
        "incidence", doenca=config.cod_agregado(esc.doenca), nivel=particao
    )
    sql = f"""
        SELECT ano,
               sum(casos_total) AS casos,
               sum(casos_grau_0) + sum(casos_grau_I) + sum(casos_grau_II) AS avaliados,
               sum(casos_grau_0) + sum(casos_grau_I) + sum(casos_grau_II)
                   + sum(casos_nao_avaliado) AS base_grau2,
               sum(casos_grau_II) AS grau_II
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return conectar().execute(sql + " GROUP BY ano ORDER BY ano", list(params)).fetchdf()


def serie_0_14(esc: Escopo) -> pd.DataFrame:
    """Casos de 0 a 14 anos por ano e a taxa por 100 mil dessa faixa.

    O outro gráfico de rodapé da origem. Colunas ``ano``, ``casos``, ``taxa``.
    Taxa recalculada da soma quando o escopo é uma região.
    """
    particao, onde, params = particao_e_filtro_geo(esc, col_mun="cod_mun6")
    fonte = caminho(
        "incidence_0_14", doenca=config.cod_agregado(esc.doenca), nivel=particao
    )
    sql = f"""
        SELECT ano, sum(casos_0_14_total) AS casos,
               sum(casos_0_14_total) / nullif(sum(pop_0_14_total), 0) * 100000 AS taxa
        FROM read_parquet('{fonte}', hive_partitioning=true)
    """
    if onde:
        sql += f" WHERE {onde}"
    return conectar().execute(sql + " GROUP BY ano ORDER BY ano", list(params)).fetchdf()


#: Código de `MODOENTR` que o Ministério conta como caso novo. Recidiva (6),
#: transferências (2–5) e outros reingressos (7) são entradas no registro
#: ativo, mas não casos novos — e a taxa de detecção é sobre casos novos.
CASO_NOVO_MS = "1"


def casos_novos_por_municipio(esc: Escopo, todos_os_anos: bool = False) -> pd.DataFrame:
    """Casos novos (`MODOENTR = 1`) por município de residência da UF.

    Colunas ``cod_mun6``, ``ano``, ``casos``. Município sem caso novo no ano
    não tem linha no `sinan_landing` — quem consome preenche com zero a
    partir da lista de municípios do `incidence`, ou some do mapa.
    """
    particoes = {"doenca": config.cod_landing(esc.doenca), "nivel": "MUN"}
    if not todos_os_anos:
        particoes["ano"] = esc.ano
    fonte = caminho("sinan_landing", **particoes)
    df = conectar().execute(
        f"""
        SELECT geo_id AS cod_mun6, ano, sum(n) AS casos
        FROM read_parquet('{fonte}', hive_partitioning=true)
        WHERE variavel = 'MODOENTR' AND sexo = 'TOTAL' AND trim(valor) = ?
          AND uf = ?
        GROUP BY geo_id, ano
        """,
        [CASO_NOVO_MS, esc.uf],
    ).fetchdf()
    df["cod_mun6"] = df["cod_mun6"].map(mun6)
    return df


def casos_novos_ms(esc: Escopo) -> float | None:
    """Casos novos do recorte pela definição do MS, via `variavel_sinan`
    (que já sabe de UF, município e região)."""
    df = variavel_sinan(esc, "MODOENTR")
    if df.empty:
        return None
    return float(df.loc[df["valor"] == CASO_NOVO_MS, "n"].sum())


def _serie_anual_casos_novos_ms(esc, metrica, fonte_pop, onde, params) -> pd.DataFrame:
    """Casos novos do MS por ano — e a taxa sobre a população do `incidence`."""
    novos = casos_novos_por_municipio(esc, todos_os_anos=True)
    if esc.municipios:
        novos = novos[novos["cod_mun6"].isin(esc.municipios)]
    elif esc.nivel == "MUN":
        novos = novos[novos["cod_mun6"] == mun6(esc.mun)]
    por_ano = novos.groupby("ano")["casos"].sum()
    pop = conectar().execute(
        f"SELECT ano, sum(pop_total) AS pop FROM read_parquet('{fonte_pop}', hive_partitioning=true)"
        + (f" WHERE {onde}" if onde else "") + " GROUP BY ano ORDER BY ano",
        list(params),
    ).fetchdf().set_index("ano")["pop"]
    casos = por_ano.reindex(pop.index).fillna(0.0)
    valor = casos if metrica == "casos" else casos / pop.replace(0, pd.NA) * 100_000
    return pd.DataFrame({"ano": pop.index, "valor": valor.to_numpy()})


def soma_ponderada(esc: Escopo, variavel: str) -> float | None:
    """Σ(valor × n) de uma variável **numérica** da ficha.

    ``CONTEXAM`` e ``CONTREG`` guardam o número de contatos examinados e
    registrados de cada caso, não um código: a linha ``valor = "3", n = 317``
    quer dizer 317 casos com três contatos. O total do recorte é a soma
    ponderada. Ver `doencas.hanseniase.VARIAVEIS_NUMERICAS`.

    Vai por :func:`variavel_sinan`, então respeita UF, município e região.
    """
    df = variavel_sinan(esc, variavel)
    if df.empty:
        return None
    valores = pd.to_numeric(df["valor"], errors="coerce")
    pesos = pd.to_numeric(df["n"], errors="coerce")
    validos = valores.notna() & pesos.notna()
    if not validos.any():
        return None
    return float((valores[validos] * pesos[validos]).sum())
