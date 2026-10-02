"""Monta uma extração só de hanseníase, a partir do lago do painel nacional.

O `data/` deste painel era uma **junção** para `../sinan/data`, o lago inteiro:
241 MB, dos quais 94 de dengue, 52 de tuberculose e 13 de zika que o painel
nunca lê. Funcionava, e escondia duas coisas — que um painel de hanseníase
parecia carregar cinco doenças, e que a entrega dependia do painel nacional
estar na mesma máquina.

Este script copia do lago **só o que este painel abre**: as partições
``doenca=HANS`` e ``doenca=HANSENIASE`` dos datasets em :data:`DATASETS`, mais
``geo/`` e ``support/`` inteiros. Dá cerca de 45 MB.

    python -m scripts.extrair_dados_hanseniase                 # para ./data
    python -m scripts.extrair_dados_hanseniase --destino /tmp/x
    python -m scripts.extrair_dados_hanseniase --origem ~/lago

**Sobre a junção:** quando o destino é um link (junção do Windows ou symlink),
o script remove **o link**, não o alvo — `os.rmdir` sobre um ponto de reparo
apaga o ponto, e o lago do sinan continua onde estava. Apagar com `rm -rf`
pelo Git Bash faria o contrário, e levaria os quatro painéis junto.

O que sai é uma cópia, e cópia envelhece: `PROCEDENCIA.json` grava a origem, a
data e o tamanho de cada dataset. Quando a extração do sinan for atualizada, é
rodar de novo — ver o README.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

#: Datasets que o painel abre, com as partições de hanseníase filtradas.
#:
#: Fora: `dim_geo` (31 MB), `obitos` e os dois do SIM (`cache_ts_sim_obitos`,
#: `obitos_sim_faixa`). Nenhum leitor os menciona desde 02/out/2026 — a
#: hanseníase não mostra óbito, mortalidade nem letalidade em lugar nenhum do
#: painel, e `kpis.calcular` lia o SIM a cada troca de recorte para calcular
#: três números que ninguém via.
DATASETS = (
    "_cache_ts",
    "cases_new",
    "incidence",
    "incidence_0_14",
    "piramides",
    "sinan_dict",
    "sinan_landing",
)

#: Os dois códigos da doença. O `sinan_landing` e o `sinan_dict` usam `HANS`;
#: os agregados usam `HANSENIASE`. Ver `src/data/config.py`.
PARTICOES = ("doenca=HANS", "doenca=HANSENIASE")

#: Pastas copiadas por inteiro — malha e apoio não são por doença.
PASTAS_INTEIRAS = ("geo", "support")

RAIZ = Path(__file__).resolve().parents[1]


def _tamanho(caminho: Path) -> int:
    if not caminho.exists():
        return 0
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file())


def _mb(bytes_: int) -> str:
    return f"{bytes_ / 1024 / 1024:,.1f} MB".replace(",", ".")


def _limpar_destino(destino: Path) -> None:
    """Tira o destino da frente sem levar o lago junto.

    Junção e symlink são removidos como **link**; diretório de verdade é
    apagado com o conteúdo, que é nosso mesmo.
    """
    if not destino.exists() and not destino.is_symlink():
        return
    if destino.is_symlink() or os.path.islink(destino):
        os.rmdir(destino) if destino.is_dir() else destino.unlink()
        print(f"  link anterior removido (o alvo continua intacto): {destino}")
        return
    # No Windows a junção não é `islink` para o Python antes do 3.13 em alguns
    # casos; `st_reparse_tag` resolve, e errar aqui é caro.
    tag = getattr(destino.lstat(), "st_reparse_tag", 0)
    if tag:
        os.rmdir(destino)
        print(f"  junção anterior removida (o alvo continua intacto): {destino}")
        return
    shutil.rmtree(destino)
    print(f"  cópia anterior apagada: {destino}")


def copiar(origem: Path, destino: Path) -> dict[str, int]:
    """Copia as partições de hanseníase e devolve o tamanho de cada dataset."""
    fonte = origem / "parquet" / "dashboard"
    if not fonte.is_dir():
        raise SystemExit(f"não achei {fonte} — passe --origem")

    _limpar_destino(destino)
    (destino / "parquet" / "dashboard").mkdir(parents=True)

    tamanhos: dict[str, int] = {}
    for dataset in DATASETS:
        raiz_ds = fonte / dataset
        if not raiz_ds.is_dir():
            print(f"  ! {dataset} não existe na origem, pulando")
            continue
        copiados = 0
        for arquivo in raiz_ds.rglob("*"):
            if not arquivo.is_file():
                continue
            partes = arquivo.relative_to(raiz_ds).parts
            # Partição no caminho, e não filtro por coluna: a ordem das
            # partições muda de dataset para dataset (`_cache_ts` começa por
            # `nivel=`, `incidence` por `doenca=`), então o que vale é a
            # presença do segmento, em qualquer profundidade.
            if not any(p in PARTICOES for p in partes):
                continue
            alvo = destino / "parquet" / "dashboard" / dataset / Path(*partes)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arquivo, alvo)
            copiados += 1
        tamanhos[dataset] = _tamanho(destino / "parquet" / "dashboard" / dataset)
        print(f"  {dataset:<22} {copiados:>4} arquivos  {_mb(tamanhos[dataset]):>10}")

    for pasta in PASTAS_INTEIRAS:
        if not (origem / pasta).is_dir():
            print(f"  ! {pasta}/ não existe na origem, pulando")
            continue
        shutil.copytree(origem / pasta, destino / pasta)
        tamanhos[pasta] = _tamanho(destino / pasta)
        print(f"  {pasta + '/':<22} {'':>4}           {_mb(tamanhos[pasta]):>10}")

    return tamanhos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--origem", type=Path, default=RAIZ.parent / "sinan" / "data",
        help="lago do painel nacional (padrão: ../sinan/data)",
    )
    parser.add_argument(
        "--destino", type=Path, default=RAIZ / "data",
        help="onde gravar a extração enxuta (padrão: ./data)",
    )
    args = parser.parse_args()

    origem, destino = args.origem.resolve(), args.destino
    print(f"origem : {origem}  ({_mb(_tamanho(origem))})")
    print(f"destino: {destino}\n")

    tamanhos = copiar(origem, destino)
    total = sum(tamanhos.values())

    (destino / "PROCEDENCIA.json").write_text(
        json.dumps(
            {
                "_leia": (
                    "Extração só de hanseníase, copiada do lago do painel "
                    "nacional por scripts/extrair_dados_hanseniase.py. É uma "
                    "cópia: quando o lago for atualizado, rode o script de novo."
                ),
                "origem": str(origem),
                "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
                "bytes_por_dataset": tamanhos,
                "bytes_total": total,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\ntotal: {_mb(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
