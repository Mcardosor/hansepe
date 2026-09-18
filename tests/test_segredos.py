"""Guarda contra credencial versionada.

Existe por um quase-acidente em 22/ago/2026: as credenciais do banco foram
preenchidas no `.env.exemplo` em vez do `.env`. O primeiro é **versionado**, o
segundo é ignorado — a diferença entre um arquivo local e uma senha pública no
GitHub. Não chegou a ser commitada, mas só porque ninguém rodou `git add -A`
naquele intervalo.

Um teste é a única barreira que não depende de alguém lembrar.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Chaves do modelo que precisam ficar vazias. `CENARIOS_HOST` e as demais têm
#: valor de propósito — são endereço, não segredo.
CHAVES_SECRETAS = ("CENARIOS_USER", "CENARIOS_PASSWORD")


def test_o_modelo_de_env_nao_tem_credencial_preenchida() -> None:
    """`.env.exemplo` é versionado. Preenchê-lo publica a senha."""
    modelo = RAIZ / ".env.exemplo"
    assert modelo.is_file(), "o modelo sumiu — sem ele ninguém sabe o que preencher"

    for linha in modelo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = (p.strip() for p in linha.split("=", 1))
        if chave in CHAVES_SECRETAS:
            assert not valor, (
                f"{chave} está preenchida em .env.exemplo, que é VERSIONADO. "
                f"Mova para .env (ignorado pelo git) e restaure o modelo com "
                f"`git checkout -- .env.exemplo`."
            )


def test_o_env_de_verdade_continua_ignorado() -> None:
    """Se alguém tirar `.env` do `.gitignore`, o próximo `add -A` publica tudo."""
    ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(linha.strip() == ".env" for linha in ignorados), (
        ".env saiu do .gitignore"
    )


def test_nenhum_arquivo_versionado_carrega_senha() -> None:
    """Varredura ampla, para o caso de a senha ir parar em outro lugar.

    Procura atribuição a uma chave de aparência secreta com valor não vazio.
    Ignora o que é claramente exemplo — `<sua-senha>`, `xxx`, `troque-me`.
    """
    import subprocess

    saida = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    )
    # Duas formas, e nao uma: chave em MAIUSCULAS, como manda a convencao de
    # configuracao, **ou** valor entre aspas. Sem essa restricao a anotacao de
    # tipo `def _px(token: str)` casava, e o teste acusava `src/graficos.py`.
    padrao = re.compile(
        r"""^(?!\s*\#).*?(?:
              (?P<maiuscula>[A-Z_]*(?:PASSWORD|SENHA|SECRET|TOKEN|API_KEY)[A-Z_]*)
              \s*[=:]\s*(?P<v1>[^\s"',\#]+)
            | (?i:password|senha|secret|token|api_key)
              \s*[=:]\s*["'](?P<v2>[^"']+)["']
        )""",
        re.VERBOSE,
    )
    placeholders = {"", "none", "null", "xxx", "troque-me", "sua-senha", "changeme"}

    suspeitos = []
    for nome in saida.stdout.splitlines():
        caminho = RAIZ / nome
        if not caminho.is_file() or caminho.suffix in {".png", ".jpg", ".jpeg", ".ico"}:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            achado = padrao.match(linha)
            if not achado:
                continue
            valor = (achado.group("v1") or achado.group("v2") or "").strip("<>{}")
            if valor.lower() in placeholders or valor.startswith(("os.", "$", "%")):
                continue
            suspeitos.append(f"{nome}:{n}")

    assert not suspeitos, "possível segredo em arquivo versionado: " + ", ".join(suspeitos)
