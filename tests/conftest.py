"""Configuração da suíte.

Os dados não são versionados — são 892 MB — então um clone novo não tem como
rodar a maior parte dos testes. Sem isto, o pytest quebra na **coleta**, com um
`FileNotFoundError` vindo do topo de um módulo, e nem os testes que não
dependem de dado chegam a rodar.

Com isto, quem clona o repositório e roda `pytest` vê os testes de tema,
navegação e resiliência passarem, e uma mensagem dizendo exatamente o que
falta para os demais.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Importado com outro nome porque os hooks do pytest exigem um parâmetro
# chamado `config`, e o choque de nomes já custou um erro de coleta.
from src.data import config as config_dados

#: Módulos que leem parquet, geometria ou os arquivos de apoio.
#: Os demais — tema, estado, resiliência — rodam em qualquer clone.
PRECISAM_DE_DADOS = (
    "test_aplicacao.py",
    "test_cache.py",
    "test_composicao.py",
    "test_desfechos.py",
    "test_estados_vazios.py",
    "test_geo.py",
    "test_graficos.py",
    "test_indicadores_programa.py",
    "test_mapa.py",
    "test_navegacao_mapa.py",
    "test_performance.py",
    "test_piramide.py",
    "test_publicacao.py",
    "test_recortes.py",
)


def _dados_presentes() -> bool:
    """Confere os três diretórios que a aplicação exige para funcionar."""
    dados = config_dados.data_dir()
    return (
        (dados / "parquet" / "dashboard").is_dir()
        and (dados / "geo").is_dir()
        and (dados / "support" / "municipios.csv").is_file()
    )


#: Marca para o teste isolado que precisa de dado dentro de um módulo que não
#: precisa. Melhor que exilar o arquivo inteiro: `test_theme.py` tem onze
#: testes de CSS que são justamente os que alguém sem os 892 MB quer rodar.
def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers", "dado: precisa dos parquets; pulado quando eles não estão lá"
    )


def pytest_collection_modifyitems(items) -> None:
    if _dados_presentes():
        return
    pular = pytest.mark.skip(reason="precisa dos parquets — ver README")
    for item in items:
        if item.get_closest_marker("dado"):
            item.add_marker(pular)


collect_ignore: list[str] = []

if not _dados_presentes():
    collect_ignore = [*PRECISAM_DE_DADOS, "paridade"]
    print(
        f"\n[conftest] Dados ausentes em {config_dados.data_dir()} — "
        f"{len(collect_ignore)} módulos ignorados.\n"
        f"           Coloque os parquets em data/parquet/dashboard/, "
        f"a geometria em data/geo/ e o apoio em data/support/,\n"
        f"           ou aponte SINAN_DATA_DIR. Ver README e docs/contrato-dados.md.\n"
    )


def pytest_report_header() -> str:
    origem = Path(config_dados.data_dir())
    estado = "presentes" if _dados_presentes() else "AUSENTES"
    return f"dados: {estado} ({origem})"


def test_a_lista_de_modulos_com_dado_esta_completa() -> None:
    """A lista envelhece calada, e foi o que aconteceu.

    Cinco módulos passaram a depender de dado sem entrar aqui, e a execução
    sem os parquets — que o README promete verde — acumulou 24 falhas. Quem
    clona o repositório sem os 892 MB via uma suíte quebrada e não sabia se
    era a máquina dele.

    Este teste lê os imports de cada módulo e cobra o registro de quem toca a
    camada de dados. Roda em qualquer modo: sem dado ele nem é coletado, com
    dado ele guarda a lista para o próximo que clonar sem.
    """
    import ast

    faltando = []
    for arquivo in sorted(Path(__file__).parent.glob("test_*.py")):
        if arquivo.name in PRECISAM_DE_DADOS:
            continue
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        alvos = {"src.data.leitura", "src.data.geo", "src.data.kpis", "src.data.recortes"}
        usa = any(
            isinstance(no, ast.Import) and any(a.name in alvos for a in no.names)
            or isinstance(no, ast.ImportFrom)
            and (
                f"{no.module}.{a.name}" in alvos or no.module in alvos
                for a in no.names
            )
            for no in ast.walk(arvore)
        )
        # `importorskip` é a outra forma de declarar a dependência.
        protegido = "importorskip" in arquivo.read_text(encoding="utf-8")
        if usa and not protegido:
            faltando.append(arquivo.name)

    assert not faltando, (
        "módulos que leem dado e não estão em PRECISAM_DE_DADOS: " + ", ".join(faltando)
    )
