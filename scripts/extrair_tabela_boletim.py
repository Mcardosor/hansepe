"""Extrai a Tabela 2 do Boletim Epidemiológico de Hanseníase (SES-PE).

A tabela traz, para 2024, nove indicadores por município e por Regional de
Saúde — é a referência externa do painel, e a única fonte que permite
conferir município a município. O resultado vai para
``tests/paridade/referencia_boletim_municipios.json`` e é comparado pelo
`tests/paridade/test_referencia_boletim.py`.

O PDF **não** entra no repositório: é documento publicado, vive em
``REUNIAO ALINHAMENTO PERNAMBUCO/BOLETIM_EPIDEMIOLOGICO_HANSEN_2025.pdf``
(pasta da reunião de 22/set/2026). O JSON congelado é o que o teste lê; este
script existe para quando sair um boletim novo.

    python -m scripts.extrair_tabela_boletim <caminho do pdf>

Requer `pypdf` — não está no lock do painel, porque nada em produção lê PDF.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

#: Colunas da Tabela 2, na ordem em que saem do PDF.
COLUNAS = (
    "casos",
    "incid",
    "casos_0_14",
    "taxa_det_0_14",
    "cura_pct",
    "contatos_pct",
    "abandono_pct",
    "gif_avaliado_pct",
    "gif_cura_pct",
)

#: Linha da tabela: um nome seguido de nove números com vírgula decimal.
LINHA = re.compile(
    r"^(?P<nome>[^\d]+?)\s+" + r"\s+".join([r"(-?[\d]+(?:,\d+)?)"] * len(COLUNAS)) + r"\s*$"
)

#: Linhas de Regional de Saúde: "I GERES 733 17,5 …".
GERES = re.compile(r"^(?P<geres>[IVX]+)\s+GERES$")


def _numero(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def chave(nome: str) -> str:
    """Nome de município comparável: sem acento, sem caixa, sem espaço duplo."""
    bruto = unicodedata.normalize("NFKD", str(nome or "").strip())
    sem_acento = "".join(c for c in bruto if not unicodedata.combining(c))
    return " ".join(sem_acento.upper().split())


#: Municípios que o boletim escreve diferente da malha do IBGE.
APELIDOS = {
    "ITAMARACA": "ILHA DE ITAMARACA",
    "IGUARACI": "IGUARACY",
    "LAGOA DO ITAENGA": "LAGOA DE ITAENGA",
    "BELEM DE SAO FRANCISCO": "BELEM DO SAO FRANCISCO",
    # Erro de digitação do próprio boletim: a Tabela 2 escreve "Garanhus".
    # Confere pelo número — 4 casos e 2,6/100 mil batem com a população de
    # Garanhuns.
    "GARANHUS": "GARANHUNS",
}


def extrair(caminho_pdf: Path) -> dict:
    from pypdf import PdfReader

    texto = "\n".join(
        (pagina.extract_text() or "") for pagina in PdfReader(caminho_pdf).pages
    )
    # Só o que vem depois do título da Tabela 2 interessa; antes dela há
    # gráficos cujos rótulos também são "nome seguido de números".
    inicio = texto.index("Tabela 2 –")

    linhas: dict[str, dict] = {}
    regionais: dict[str, dict] = {}
    for linha in texto[inicio:].splitlines():
        achado = LINHA.match(linha.strip())
        if not achado:
            continue
        nome = " ".join(achado.group("nome").split())
        valores = {
            coluna: _numero(achado.group(i + 2)) for i, coluna in enumerate(COLUNAS)
        }
        if (regional := GERES.match(chave(nome))) :
            regionais[regional.group("geres")] = valores
        else:
            linhas[chave(nome)] = valores
    return {"municipios": linhas, "regionais": regionais}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    dados = extrair(Path(sys.argv[1]))
    municipios, regionais = dados["municipios"], dados["regionais"]
    print(f"{len(municipios)} municípios e {len(regionais)} regionais lidos")

    # Cruza com a malha para gravar por código IBGE, que é a chave do painel.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.data import geo

    malha = geo.municipios("PE")
    por_nome = {chave(n): c for n, c in zip(malha["nome_mun"], malha["cod_mun6"])}

    saida, orfaos = {}, []
    for nome, valores in municipios.items():
        codigo = por_nome.get(nome) or por_nome.get(APELIDOS.get(nome, ""))
        if codigo is None:
            orfaos.append(nome)
            continue
        saida[codigo] = {"nome": nome, **valores}

    if orfaos:
        print(f"sem correspondência na malha ({len(orfaos)}): {sorted(orfaos)}")
    faltando = set(por_nome.values()) - set(saida)
    if faltando:
        print(f"municípios da malha ausentes no boletim: {len(faltando)}")

    destino = (
        Path(__file__).resolve().parents[1]
        / "tests/paridade/referencia_boletim_municipios.json"
    )
    destino.write_text(
        json.dumps(
            {
                "_fonte": (
                    "Tabela 2 do Boletim Epidemiológico de Hanseníase — SES-PE/SEVSAP, "
                    "Anual 2025. Indicadores de 2024, tabulados em 16/04/2025. "
                    "Extraído por scripts/extrair_tabela_boletim.py."
                ),
                "_colunas": list(COLUNAS),
                "regionais": regionais,
                "municipios": saida,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"gravado em {destino.relative_to(destino.parents[2])}: {len(saida)} municípios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
