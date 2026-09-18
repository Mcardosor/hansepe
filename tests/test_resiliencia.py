"""Testes do isolamento de falha por painel."""

from __future__ import annotations

import pytest
from streamlit.runtime.scriptrunner_utils.exceptions import RerunException

from src.resiliencia import painel


def test_falha_fica_contida_e_e_reportada() -> None:
    vistos: list[tuple[str, str]] = []

    with painel("Mapa", avisar=lambda nome, erro: vistos.append((nome, str(erro)))):
        raise ValueError("coluna sumiu")

    # Chegar aqui já é o teste: a exceção não escapou.
    assert vistos == [("Mapa", "coluna sumiu")]


def test_sucesso_nao_aciona_o_aviso() -> None:
    vistos: list[str] = []
    with painel("Ranking", avisar=lambda nome, erro: vistos.append(nome)):
        pass
    assert vistos == []


def test_rerun_atravessa_a_contencao() -> None:
    """O `st.rerun()` levanta `RerunException`, que precisa passar direto.

    Se esta captura fosse ampliada para `BaseException`, todo clique no mapa
    e no ranking pararia de navegar — sem erro visível, o que é pior que a
    queda que este módulo evita.
    """
    with pytest.raises(RerunException):
        with painel("Mapa", avisar=lambda nome, erro: None):
            raise RerunException(None)


def test_rerun_nao_e_uma_exception() -> None:
    """A premissa do módulo, presa por teste caso o Streamlit mude."""
    assert not issubclass(RerunException, Exception)
    assert issubclass(RerunException, BaseException)
