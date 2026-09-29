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


def test_o_pack_padrao_e_hanseniase() -> None:
    assert doencas.carregar().DOENCA == "HANSENIASE"


def test_hanseniase_esta_no_registro() -> None:
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


@pytest.mark.parametrize("metrica", ["casos_0_14", "taxa_det_0_14"])
def test_o_0_14_avisa_que_conta_todas_as_entradas(metrica: str) -> None:
    """A régua do MS ao lado do 0–14 é definida sobre **casos novos**, e o
    número não é de casos novos: a extração não cruza idade com modo de
    entrada (paridade §1.1).

    O tooltip já dizia isso de `casos_0_14`, mas concluía que "a diferença é
    pequena nessa faixa" — medida em 28/set/2026, ela é de 8% a 22%. O teste
    existe para que a ressalva não volte a sumir nem a virar diminutivo: quem
    apagar o aviso tem de vir aqui apagá-lo também.
    """
    hanseniase = doencas.carregar("hanseniase")
    texto = hanseniase.DESCRICOES[metrica].lower()
    assert "entradas" in texto and "modo de entrada" in texto
    assert "diferença é pequena" not in texto
