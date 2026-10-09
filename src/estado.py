"""Estado de navegação do dashboard.

Deliberadamente sem dependência do Streamlit: a máquina de estados é testada
sozinha, e a aplicação só guarda uma instância em ``st.session_state``.

**O topo é Pernambuco.** O painel nacional de onde este código veio começava
no Brasil; aqui o nível ``BR`` não existe para o usuário — o caminho de ida é

    PE → (macrorregião → região de saúde) → município

e o ``voltar`` desfaz esse caminho um passo por vez, parando na UF. O
``Escopo`` continua aceitando ``BR`` porque os leitores são os do painel
nacional; só a navegação não vai até lá.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import config, recortes
from .data.escopo import Escopo, mun6

#: Recortes do mapa no nível UF. ``MUN`` é o padrão; os outros dois são
#: exclusivos de Pernambuco e vêm dos shapefiles de apoio.
RECORTES = ("MUN", "MACRO", "MICRO")

#: A UF deste painel. Fixa por decisão: um container serve um estado.
UF_FIXA = "PE"

def nivel_agregado(nivel: str) -> str:
    """Nível de quem é *listado* sob o escopo — no Brasil as UFs, senão os
    municípios da UF.

    Município não entra: dentro de um município, mapa e ranking continuam
    mostrando os municípios da UF, para o usuário ver onde ele se situa. Sem
    esta redução, montar um ``Escopo`` de nível ``MUN`` sem ``mun`` estoura —
    foi assim que o ranking derrubou a página ao entrar num município.
    """
    return "BR" if str(nivel).strip().upper() == "BR" else "UF"


@dataclass
class Navegacao:
    """Recorte corrente. Mutável — a aplicação guarda uma instância viva."""

    doenca: str = config.HANSENIASE
    ano: int = config.ANO_PADRAO
    metrica: str = "incid"

    nivel: str = "UF"
    uf: str | None = UF_FIXA
    mun: str | None = None
    detalhe: bool = False

    recorte: str = "MUN"
    macro: str | None = None
    micro: str | None = None

    #: Rótulo do município corrente, só para exibição.
    nome_mun: str | None = None

    #: Municipio apontado no mapa sem entrar nele, vindo do clique na barra do
    #: ranking. E so localizacao: o escopo continua na UF, e os KPIs, a serie e
    #: a composicao seguem falando do estado inteiro.
    #:
    #: Existe porque as duas perguntas sao diferentes. "Onde fica esse
    #: municipio?" se responde olhando o mapa com ele aceso; "como esta esse
    #: municipio?" se responde entrando nele, o que o clique no proprio mapa e
    #: a busca por nome ja fazem.
    destacado: str | None = None
    nome_destacado: str | None = None

    _historico: list[str] = field(default_factory=list, repr=False)

    # -- consultas ----------------------------------------------------------

    @property
    def escopo(self) -> Escopo:
        """Recorte no formato que a camada de dados consome."""
        return Escopo(
            doenca=self.doenca,
            ano=self.ano,
            nivel=self.nivel,
            uf=self.uf,
            mun=self.mun,
        )

    @property
    def tem_recortes_de_saude(self) -> bool:
        """A UF corrente tem macrorregião e região de saúde configuradas?

        Hoje só PE, mas a resposta vem do registro — acrescentar um estado não
        exige tocar aqui.
        """
        return recortes.configurada(self.uf)

    @property
    def pode_voltar(self) -> bool:
        return not (
            self.nivel == "UF" and self.macro is None and self.micro is None
            and self.recorte == "MUN" and not self.detalhe
        )

    # -- ida ----------------------------------------------------------------

    def entrar_uf(self, uf: str) -> None:
        self.uf = str(uf).strip().upper()
        self.nivel = "UF"
        self.mun = None
        self.nome_mun = None
        self.detalhe = False
        self.limpar_destaque()
        if not self.tem_recortes_de_saude:
            self.recorte = "MUN"
            self.macro = None
            self.micro = None

    def entrar_municipio(self, mun: str, nome: str | None = None) -> None:
        self.mun = mun6(mun)
        self.nome_mun = nome
        self.nivel = "MUN"
        self.detalhe = False
        self.limpar_destaque()

    def destacar(self, mun: str, nome: str | None = None) -> None:
        """Acende um municipio no mapa sem mudar o escopo.

        **Idempotente de proposito, e nao um interruptor.** A selecao do
        grafico persiste entre execucoes: o clique nao chega como evento, mas
        como estado que continua la na proxima passada. Um `destacar` que
        alternasse acendia, reiniciava a pagina, apagava, reiniciava -- laco
        infinito, e foi o que aconteceu na primeira versao.

        Quem apaga e `limpar_destaque`, pelo botao ao lado do mapa.
        """
        self.destacado = mun6(mun)
        self.nome_destacado = nome

    def limpar_destaque(self) -> None:
        self.destacado = None
        self.nome_destacado = None

    def abrir_detalhe(self) -> None:
        if self.nivel != "MUN":
            raise ValueError("Detalhe só existe no nível de município.")
        self.detalhe = True

    def definir_recorte(self, recorte: str) -> None:
        """Troca entre município, macrorregião e região de saúde."""
        valor = str(recorte or "MUN").strip().upper()
        if valor not in RECORTES:
            raise ValueError(f"Recorte inválido: {recorte!r}. Esperado {RECORTES}.")
        if valor != "MUN" and not self.tem_recortes_de_saude:
            raise ValueError(
                f"{self.uf} não tem recorte de saúde. "
                f"Configuradas: {recortes.ufs_com_recorte()}."
            )
        self.recorte = valor
        # Trocar de recorte descarta a seleção do recorte anterior.
        if valor in ("MUN", "MACRO"):
            self.macro = self.micro = None
        else:
            self.micro = None

    def entrar_macro(self, macro: str) -> None:
        """Clicar numa macrorregião filtra as regiões de saúde dentro dela."""
        self.macro = str(macro).strip()
        self.recorte = "MICRO"
        self.micro = None

    def entrar_micro(self, micro: str) -> None:
        """Clicar numa região de saúde filtra os municípios dentro dela."""
        self.micro = str(micro).strip()
        self.recorte = "MUN"

    # -- volta --------------------------------------------------------------

    def voltar(self) -> None:
        """Desfaz um passo do caminho de ida.

        A ordem das regras importa e reproduz o ``mod_state.R``:

        1. município em detalhe → fecha o detalhe
        2. município → UF, voltando ao recorte de região de saúde se foi por lá
        3. UF vendo regiões de saúde de uma macro → volta a ver as macros
        4. UF → BR, limpando tudo
        5. BR → não faz nada
        """
        if self.nivel == "MUN" and self.detalhe:
            self.detalhe = False
            return

        if self.nivel == "MUN":
            self.nivel = "UF"
            self.mun = None
            self.nome_mun = None
            self.detalhe = False
            if self.micro is not None:
                self.micro = None
                self.recorte = "MICRO"
            return

        if self.nivel == "UF":
            if self.recorte == "MICRO" and self.macro is not None:
                self.macro = None
                self.recorte = "MACRO"
                return
            # Acima da UF não há nada: voltar do estado inteiro só limpa o
            # recorte, e a página fica onde está.
            self.reset(manter_ano=True)
            return

    def reset(self, manter_ano: bool = True) -> None:
        """Volta a Pernambuco inteiro, limpando todo o recorte geográfico."""
        self.nivel = "UF"
        self.uf = UF_FIXA
        self.mun = None
        self.nome_mun = None
        self.detalhe = False
        self.limpar_destaque()
        self.recorte = "MUN"
        self.macro = None
        self.micro = None
        if not manter_ano:
            self.ano = config.ANO_PADRAO

    # -- exibição -----------------------------------------------------------

    def trilha(self) -> str:
        """Breadcrumb do recorte, no formato do original."""
        partes: list[str] = []

        if self.nivel == "BR":
            partes.append("Brasil")
        elif self.nivel == "UF":
            partes.append(f"UF {self.uf}")
            if self.recorte == "MACRO":
                partes.append("Macrorregiões")
            elif self.recorte == "MICRO":
                if self.macro:
                    partes.append(f"Macro: {self.macro}")
                partes.append("Regiões de saúde")
            elif self.micro:
                partes.append(f"Micro: {self.micro}")
                partes.append("Municípios")
        else:
            partes.append(str(self.uf or "—"))
            partes.append(f"Município: {self.nome_mun or self.mun or '—'}")
            if self.detalhe:
                partes.append("detalhe")

        # "Ano de notificação", e não "Ano".
        #
        # A equipe parceira perguntou na revisão de outubro de qual ano se
        # trata, e ninguém soube responder na hora. A resposta veio do
        # microdado liberado depois: o `NU_ANO` que organiza as tabelas é
        # idêntico ao ano de `DT_NOTIFIC` em 25.843 de 25.843 registros.
        #
        # É aqui que a informação entra, e não no rótulo do seletor: a
        # coluna dele tem 91px e o texto pede 125, então cortaria com
        # reticências. Esta linha tem 1.083px de folga, é dinâmica — muda
        # junto com o recorte — e é a que faz uma captura de tela se
        # explicar sozinha. Procedência, como o resto dela.
        partes.append(f"Ano de notificação: {self.ano}")
        return " • ".join(partes)
