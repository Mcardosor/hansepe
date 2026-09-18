"""Recorte geográfico e temporal — o ``Escopo``.

Todo leitor e todo KPI recebe um ``Escopo``. Ele carrega o nível (BR, UF, MUN),
a UF e o município quando aplicáveis, a doença e o ano.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True, slots=True)
class Escopo:
    """Recorte de análise.

    ``mun`` aceita o código IBGE com 6 ou 7 dígitos. Internamente tudo passa a
    usar o de **6**, que é a única chave presente em todos os datasets:
    ``incidence`` traz ``cod_mun6`` e ``cod_mun7``, mas os demais só têm
    ``geo_id``, de 6 dígitos. O 7º é dígito verificador e não é reconstruível
    por truncamento, então serve só para exibição.
    """

    doenca: str
    ano: int
    nivel: str = "BR"
    uf: str | None = None
    mun: str | None = None
    #: Conjunto de municípios da UF — uma macrorregião ou região de saúde.
    #: Com isto preenchido, os leitores que sabem descer a município leem a
    #: partição ``MUN`` e somam só estes; os demais seguem a UF. Só faz
    #: sentido no nível ``UF``.
    municipios: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        nivel = str(self.nivel or "BR").strip().upper()
        if nivel not in config.NIVEIS:
            raise ValueError(f"Nível inválido: {self.nivel!r}. Esperado {config.NIVEIS}.")
        object.__setattr__(self, "nivel", nivel)
        object.__setattr__(self, "doenca", config._canon(self.doenca))
        object.__setattr__(self, "ano", int(self.ano))

        if self.uf is not None:
            object.__setattr__(self, "uf", str(self.uf).strip().upper())
        if self.mun is not None:
            object.__setattr__(self, "mun", mun6(self.mun))

        if self.municipios is not None:
            if nivel != "UF":
                raise ValueError("`municipios` só se aplica ao nível UF.")
            object.__setattr__(
                self, "municipios", tuple(mun6(m) for m in self.municipios)
            )
        if nivel == "UF" and not self.uf:
            raise ValueError("Nível UF exige o parâmetro `uf`.")
        if nivel == "MUN" and not self.mun:
            raise ValueError("Nível MUN exige o parâmetro `mun`.")

    def filtro_geo(self, col_mun: str = "cod_mun6") -> tuple[str, list]:
        """Cláusula WHERE do recorte geográfico, sem o nível nem a doença."""
        if self.nivel == "UF":
            return "uf = ?", [self.uf]
        if self.nivel == "MUN":
            return f"{col_mun} = ?", [self.mun]
        return "", []

    @property
    def ano_anterior(self) -> int:
        return self.ano - 1


def mun6(codigo) -> str:
    """Chave canônica de município: os 6 primeiros dígitos do código IBGE.

    Aceita 6 ou 7 dígitos e descarta o dígito verificador. É a única forma
    de município que existe em todos os datasets.
    """
    return "".join(ch for ch in str(codigo or "") if ch.isdigit())[:6]


def particao_e_filtro_geo(esc: Escopo, col_mun: str = "geo_id") -> tuple[str, str, list]:
    """(nível da partição, cláusula, parâmetros) para leitores por ``geo_id``.

    Existe por causa de `Escopo.municipios`: uma região de saúde é lida na
    partição ``MUN`` com ``geo_id IN (...)``, e não na ``UF``. Sem
    municípios, é o filtro de sempre.
    """
    if esc.municipios:
        marcadores = ", ".join("?" for _ in esc.municipios)
        return "MUN", f"{col_mun} IN ({marcadores})", list(esc.municipios)
    if esc.nivel == "UF":
        return "UF", "uf = ?", [esc.uf]
    if esc.nivel == "MUN":
        return "MUN", f"{col_mun} = ?", [mun6(esc.mun)]
    return "BR", "", []
