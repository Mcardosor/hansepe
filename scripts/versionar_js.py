"""Carimba `?v=<hash do arquivo>` nos `<script src>` dos componentes.

Rode depois de editar `mapa.js` ou `grafico.js`. O Streamlit serve `.js` com
`Cache-Control: public` e só o `index.html` com `no-cache`: sem o carimbo,
o navegador de quem já abriu o painel segue com o JavaScript antigo.
`tests/test_mapa_componente.py` cobra que o carimbo bata com o arquivo.

    python -m scripts.versionar_js
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "src"
PASTAS = ("componente_mapa", "componente_grafico")


def carimbar(pasta: Path) -> list[str]:
    idx = pasta / "index.html"
    html = idx.read_text(encoding="utf-8")

    def sub(m: re.Match) -> str:
        nome = m.group(1)
        h = hashlib.sha1((pasta / nome).read_bytes()).hexdigest()[:8]
        return f'<script src="{nome}?v={h}"></script>'

    novo = re.sub(r'<script src="([^"?]+)(?:\?v=[0-9a-f]+)?"></script>', sub, html)
    idx.write_text(novo, encoding="utf-8")
    return re.findall(r'src="([^"]+)"', novo)


if __name__ == "__main__":
    for nome in PASTAS:
        print(nome, carimbar(RAIZ / nome))
