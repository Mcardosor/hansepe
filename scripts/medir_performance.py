"""Quanto custa cada leitura do painel, sem o cache do Streamlit.

Mede o tempo real por consulta nos três recortes que a navegação oferece —
estado, região de saúde e município —, que é o que o usuário percorre ao
clicar no mapa. O cache do Streamlit fica de fora de propósito: o que interessa
aqui é o custo da primeira vez, que é o que ele sente.

Uso::

    python -m scripts.medir_performance

Os números entram em `docs/performance.md`; quando mudarem de forma relevante,
é ali que se atualiza.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import replace

from src.data import canal, kpis, leitura, recortes
from src.data.escopo import Escopo

REPETICOES = 5

#: 2025 é o ano que o painel abre. Município: Recife, o maior do estado.
ANO = 2025

_ESTADO = Escopo("HANSENIASE", ANO, "UF", uf="PE")
_REGIAO = replace(
    _ESTADO,
    municipios=tuple(recortes.municipios_de(macro=recortes.macros("PE")[0], uf="PE")),
)
_MUNICIPIO = Escopo("HANSENIASE", ANO, "MUN", uf="PE", mun="261160")

ESCOPOS = {
    "PE": _ESTADO,
    "macrorregião": _REGIAO,
    "Recife": _MUNICIPIO,
}

#: Só o que o painel realmente chama. A ordem é a da tela, de cima para baixo.
OPERACOES: dict[str, Callable[[Escopo], object]] = {
    "kpis.calcular (os 7 cards)": kpis.calcular,
    "casos_novos_ms": leitura.casos_novos_ms,
    "valores_por_geografia (mapa)": lambda e: leitura.valores_por_geografia(e, "incid"),
    "ranking": lambda e: leitura.ranking(e, "incid"),
    "canal.montar": canal.montar,
    "canal.epicurva (10 anos)": lambda e: canal.epicurva(e, ano_min=ANO - 9),
    "piramide_completa": leitura.piramide_completa,
    "serie_qualidade (gráficos 10–13)": leitura.serie_qualidade,
    "serie_0_14": leitura.serie_0_14,
    "serie_classificacao_operacional": leitura.serie_classificacao_operacional,
    "composicao (um tópico)": lambda e: leitura.composicao(e, "CLASSOPERA"),
}


def cronometrar(fn: Callable[[Escopo], object], esc: Escopo) -> tuple[float, float]:
    """(mediana, pior) em milissegundos, descartando a primeira chamada.

    A primeira paga a leitura dos metadados do parquet, que o sistema de
    arquivos passa a guardar — contá-la mediria o disco frio, não a consulta.
    """
    fn(esc)
    tempos = []
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        fn(esc)
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos), max(tempos)


def main() -> None:
    print(f"Hanseníase, {ANO}. Mediana de {REPETICOES} execuções, em ms.\n")
    largura = max(len(n) for n in OPERACOES)
    print(f"{'operação':<{largura}}" + "".join(f"{r:>22}" for r in ESCOPOS))

    totais = dict.fromkeys(ESCOPOS, 0.0)
    for nome, fn in OPERACOES.items():
        linha = f"{nome:<{largura}}"
        for rotulo, esc in ESCOPOS.items():
            try:
                mediana, pior = cronometrar(fn, esc)
            except Exception as erro:  # noqa: BLE001 — medição não pode derrubar
                linha += f"{'—':>14}{'':>8}"
                print(f"  ! {nome} em {rotulo}: {type(erro).__name__}")
                continue
            if not nome.startswith("kpis.calcular"):
                totais[rotulo] += mediana
            linha += f"{mediana:>14.1f}{pior:>8.1f}"
        print(linha)

    print(f"\n{'soma dos leitores':<{largura}}" + "".join(
        f"{totais[r]:>14.1f}{'':>8}" for r in ESCOPOS
    ))
    print("\n(cada célula: mediana / pior caso)")


if __name__ == "__main__":
    main()
