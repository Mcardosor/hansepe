"""Testes do registro de disease packs.

O registro existe para que o painel 2 seja configuração e não refatoração: o
`app.py` recebe o pack, não o importa. O que se confere aqui é o contrato —
que o pack real o cumpre, que um pack incompleto falha no carregamento, e que
nome vindo do ambiente não vira import de módulo arbitrário.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType

import pytest

from src import doencas


def test_padrao_e_tuberculose() -> None:
    assert doencas.carregar().DOENCA == "HANSENIASE"


def test_tuberculose_esta_disponivel() -> None:
    assert "hanseniase" in doencas.disponiveis()


def test_pack_real_cumpre_o_contrato() -> None:
    pack = doencas.carregar("hanseniase")
    assert [a for a in doencas.CONTRATO if not hasattr(pack, a)] == []


def test_ambiente_escolhe_o_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINAN_DOENCA", "hanseniase")
    assert doencas.carregar().TITULO == "Hanseníase"


def test_argumento_vence_o_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINAN_DOENCA", "inexistente")
    assert doencas.carregar("hanseniase").DOENCA == "HANSENIASE"


def test_ambiente_vazio_cai_no_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINAN_DOENCA", "   ")
    assert doencas.carregar().DOENCA == "HANSENIASE"


def test_nome_desconhecido_lista_o_que_existe() -> None:
    with pytest.raises(ValueError, match="hanseniase"):
        doencas.carregar("dengue")


def test_nao_importa_modulo_de_fora_do_pacote() -> None:
    """O nome vem do ambiente — `importlib` com string de fora importaria
    qualquer coisa alcançável, inclusive algo com efeito colateral no topo."""
    with pytest.raises(ValueError):
        doencas.carregar("os")


def test_pack_incompleto_falha_no_carregamento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    falso = ModuleType("src.doencas.falso")
    falso.DOENCA = "FALSA"
    monkeypatch.setitem(sys.modules, "src.doencas.falso", falso)
    monkeypatch.setattr(doencas, "disponiveis", lambda: ("falso", "hanseniase"))

    with pytest.raises(AttributeError, match="TITULO"):
        doencas.carregar("falso")


def test_app_nao_importa_pack_fixo() -> None:
    """A regressão que o registro veio impedir: um `from src.doencas import
    <doenca>` de volta no `app.py` desfaz a troca por configuração em silêncio,
    porque tudo continua funcionando — para uma doença só."""
    arvore = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    fixos = [
        no.module
        for no in ast.walk(arvore)
        if isinstance(no, ast.ImportFrom) and no.module == "src.doencas"
    ]
    assert fixos == []
