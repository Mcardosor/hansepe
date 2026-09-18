"""Recortes administrativos de saúde, por UF.

O dashboard é **nacional** — os 5.571 municípios navegam. Sobre isso há uma
camada de recortes de saúde que hoje **só Pernambuco tem**, porque só para PE
existem a malha e o lookup.

O módulo é genérico de propósito. Acrescentar outro estado é registrar uma
entrada em :data:`CONFIGURACOES` e soltar os arquivos em ``data/support/``,
sem tocar em código. O projeto em R fixava "pe" no nome das funções e dos
dados (``.read_pe_municipios_lookup``), o que faria de um segundo estado uma
refatoração em vez de uma configuração.

A agregação **soma os componentes e recalcula a taxa**, nunca tira média das
taxas municipais: isso pesaria Recife igual a um município de dois mil
habitantes. É também o que o dashboard em R faz.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from . import config

@dataclass(frozen=True, slots=True)
class Configuracao:
    """Como ler os recortes de uma UF.

    Os rótulos ficam aqui porque a nomenclatura varia: PE usa macrorregião e
    região de saúde, mas outro estado pode nomear diferente, e a interface
    deve mostrar o termo que o estado usa.
    """

    uf: str
    arquivo: str
    col_codigo: str
    col_nome: str
    col_macro: str
    col_micro: str
    rotulo_macro: str = "Macrorregiões"
    rotulo_micro: str = "Regiões de saúde"


#: UFs com recorte de saúde. Hoje só PE — ver o docstring para acrescentar.
CONFIGURACOES: dict[str, Configuracao] = {
    "PE": Configuracao(
        uf="PE",
        arquivo="municipios.csv",
        # `City` traz o código IBGE de 7 dígitos, gravado como decimal.
        col_codigo="City",
        col_nome="Name",
        col_macro="NomeMacro",
        col_micro="NomeRegSau",
    ),
}

#: UF padrão dos parâmetros. Enquanto só PE existe, evita repetir a sigla.
UF = "PE"


def ufs_com_recorte() -> list[str]:
    return sorted(CONFIGURACOES)


def configurada(uf: str | None) -> bool:
    """A UF tem recorte de saúde?"""
    return str(uf or "").strip().upper() in CONFIGURACOES


def config_de(uf: str) -> Configuracao:
    chave = str(uf or "").strip().upper()
    if chave not in CONFIGURACOES:
        raise ValueError(
            f"{chave} não tem recorte de saúde configurado. "
            f"Disponíveis: {ufs_com_recorte()}."
        )
    return CONFIGURACOES[chave]


def _chave(texto) -> str:
    """Normaliza nome de região para comparação.

    Hoje os nomes do CSV e dos shapefiles são idênticos, mas a normalização
    fica como defesa: são duas fontes independentes, mantidas por gente
    diferente, e um acento a mais de um lado quebraria a junção em silêncio.
    """
    bruto = str(texto or "").strip()
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFKD", bruto)
        if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.upper().split())


@lru_cache(maxsize=8)
def lookup(uf: str = UF) -> pd.DataFrame:
    """Município → macrorregião e região de saúde.

    Colunas: ``cod_mun6``, ``nome_mun``, ``macro``, ``micro`` e as chaves
    normalizadas ``macro_chave`` e ``micro_chave``.
    """
    cfg = config_de(uf)
    caminho = config.support_dir() / cfg.arquivo
    if not caminho.is_file():
        raise FileNotFoundError(
            f"{caminho} não encontrado. É a única fonte de macrorregião e "
            f"região de saúde; ver docs/contrato-dados.md."
        )

    bruto = None
    for codificacao in ("utf-8", "latin1", "cp1252"):
        try:
            bruto = pd.read_csv(caminho, encoding=codificacao)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if bruto is None:
        raise ValueError(f"Não consegui decodificar {caminho}.")

    faltando = {cfg.col_codigo, cfg.col_macro, cfg.col_micro} - set(bruto.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes em {caminho.name}: {sorted(faltando)}")

    tabela = pd.DataFrame(
        {
            # O código vem como float e precisa de `round`, não de `int`.
            # Oito dos 185 municípios estão gravados com erro de ponto
            # flutuante — São Vicente Férrer aparece como 2613799.9999999995 —
            # e truncar produziria 261379 em vez de 261380. Em dois casos isso
            # cruza a fronteira dos 6 dígitos e o município deixa de casar com
            # os dados, sumindo da agregação por região sem erro nenhum.
            "cod_mun6": pd.to_numeric(bruto[cfg.col_codigo], errors="coerce")
            .astype("Float64")
            .map(lambda v: "" if pd.isna(v) else str(round(v))[:6]),
            "nome_mun": bruto.get(cfg.col_nome, pd.Series(dtype=str)).astype(str).str.strip(),
            "macro": bruto[cfg.col_macro].astype(str).str.strip(),
            "micro": bruto[cfg.col_micro].astype(str).str.strip(),
        }
    )
    tabela = tabela[tabela["cod_mun6"].str.fullmatch(r"\d{6}")]
    tabela["macro_chave"] = tabela["macro"].map(_chave)
    tabela["micro_chave"] = tabela["micro"].map(_chave)
    return tabela.drop_duplicates("cod_mun6").reset_index(drop=True)


def macros(uf: str = UF) -> list[str]:
    return sorted(lookup(uf)["macro"].unique())


def micros(macro: str | None = None, uf: str = UF) -> list[str]:
    """Regiões de saúde, opcionalmente filtradas por macrorregião."""
    tabela = lookup(uf)
    if macro:
        tabela = tabela[tabela["macro_chave"] == _chave(macro)]
    return sorted(tabela["micro"].unique())


def municipios_de(
    *, macro: str | None = None, micro: str | None = None, uf: str = UF
) -> list[str]:
    """Códigos de 6 dígitos dentro de um recorte."""
    tabela = lookup(uf)
    if macro:
        tabela = tabela[tabela["macro_chave"] == _chave(macro)]
    if micro:
        tabela = tabela[tabela["micro_chave"] == _chave(micro)]
    return sorted(tabela["cod_mun6"])


#: Componentes necessários para recalcular cada métrica depois de agregar.
#: A chave é a métrica; o valor é como derivá-la das somas.
COMPONENTES = ("casos", "cura", "pop", "obitos", "casos_0_14", "pop_0_14")


def agregar(
    componentes: pd.DataFrame, metrica: str, nivel: str = "macro", uf: str = UF
) -> pd.Series:
    """Agrega componentes municipais por região e recalcula a métrica.

    ``componentes`` é indexado por ``cod_mun6`` e traz as colunas de
    :data:`COMPONENTES` que existirem. O índice do resultado é o **nome** da
    região, que é como a geometria a identifica.

    Somar e recalcular, e não tirar média das taxas: a média trataria um
    município de dois mil habitantes como Recife.
    """
    coluna = "macro" if str(nivel).lower().startswith("mac") else "micro"

    tabela = lookup(uf).set_index("cod_mun6")[[coluna]]
    juncao = componentes.join(tabela, how="inner")
    if juncao.empty:
        return pd.Series(dtype=float)

    somas = juncao.groupby(coluna).sum(numeric_only=True)

    if metrica in COMPONENTES:
        return somas[metrica] if metrica in somas else pd.Series(dtype=float)

    if metrica == "taxa_det_0_14" and {"casos_0_14", "pop_0_14"} <= set(somas.columns):
        return somas["casos_0_14"] / somas["pop_0_14"].replace(0, pd.NA) * 100_000

    if metrica == "incid" and {"casos", "pop"} <= set(somas.columns):
        return somas["casos"] / somas["pop"].replace(0, pd.NA) * 100_000
    if metrica == "mortalidade" and {"obitos", "pop"} <= set(somas.columns):
        return somas["obitos"] / somas["pop"].replace(0, pd.NA) * 100_000
    if metrica == "letalidade" and {"obitos", "casos"} <= set(somas.columns):
        return somas["obitos"] / somas["casos"].replace(0, pd.NA) * 100

    return pd.Series(dtype=float)
