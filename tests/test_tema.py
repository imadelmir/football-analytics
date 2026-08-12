"""Verifiche del tema della dashboard (M6-T1).

Il criterio del backlog e' che **un test verifichi che `viz.py` non contenga
colori letterali**. Qui la verifica e' piu' larga: cerca in **tutto il
pacchetto** tranne `tema.py`, perche' la regola non riguarda un file ma
un'architettura — i colori stanno in un posto solo, e chiunque ne scriva uno
altrove rompe la build invece di scoprirlo fra sei mesi.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from football_analytics import tema
from football_analytics.config import Gruppo

#: Il sorgente del pacchetto, che il test legge come testo.
PACCHETTO: Path = Path(tema.__file__).parent

#: Le forme in cui un colore puo' nascondersi in un sorgente Python.
COLORI_LETTERALI: re.Pattern[str] = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\s*\(|hsla?\s*\(",
)

#: I nomi di colore CSS che capita di scrivere per distrazione.
NOMI_COLORE: frozenset[str] = frozenset(
    {"white", "black", "green", "blue", "red", "yellow", "grey", "gray", "orange"}
)


def moduli() -> list[Path]:
    """Elenca i moduli del pacchetto in cui i colori sono vietati.

    Returns:
        Tutti i ``.py`` del pacchetto tranne ``tema.py``, che e' il posto dove
        i colori devono stare.
    """
    return sorted(p for p in PACCHETTO.glob("*.py") if p.name != "tema.py")


# ---------------------------------------------------------------------------
# Il criterio del backlog
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("modulo", moduli(), ids=lambda p: p.name)
def test_nessun_colore_letterale_fuori_da_tema(modulo: Path) -> None:
    """Nessun modulo del pacchetto contiene un colore scritto a mano.

    Un colore dentro un grafico e' invisibile finche' non serve cambiarlo, e
    sopravvive al cambio di tema: la vista resterebbe verde anche quando tutto
    il resto e' diventato blu.
    """
    sorgente = modulo.read_text(encoding="utf-8")

    trovati = COLORI_LETTERALI.findall(sorgente)

    assert not trovati, f"{modulo.name} contiene colori letterali: {trovati}"


@pytest.mark.parametrize("modulo", moduli(), ids=lambda p: p.name)
def test_nessun_nome_di_colore_css_fuori_da_tema(modulo: Path) -> None:
    parole = set(re.findall(r"[a-z]+", modulo.read_text(encoding="utf-8").lower()))

    sospette = parole & NOMI_COLORE

    assert not sospette, f"{modulo.name} usa nomi di colore: {sorted(sospette)}"


def test_il_test_saprebbe_riconoscere_un_colore() -> None:
    # Un test che cerca qualcosa deve dimostrare di saperlo trovare, o non
    # distingue «nessun colore» da «espressione regolare sbagliata».
    assert COLORI_LETTERALI.search('colore = "#1b7f4f"')
    assert COLORI_LETTERALI.search("colore = 'rgb(27, 127, 79)'")
    assert COLORI_LETTERALI.search('sfondo = "rgba(0,0,0,.5)"')
    assert not COLORI_LETTERALI.search("distanza = 120.0")


# ---------------------------------------------------------------------------
# La scelta del tema
# ---------------------------------------------------------------------------


def test_le_finali_sono_blu() -> None:
    assert tema.per_gruppo(Gruppo.FINALI) is tema.BLU
    assert tema.per_gruppo("finali") is tema.BLU


def test_campionati_e_tornei_sono_verdi() -> None:
    assert tema.per_gruppo(Gruppo.CAMPIONATO) is tema.VERDE
    assert tema.per_gruppo(Gruppo.TORNEO) is tema.VERDE


def test_un_gruppo_sconosciuto_non_rompe_la_dashboard() -> None:
    # Meglio una vista verde che una pagina bianca: se domani nasce un gruppo
    # nuovo, l'app deve continuare a disegnare.
    assert tema.per_gruppo("gruppo_inventato") is tema.VERDE


# ---------------------------------------------------------------------------
# Le palette
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_ogni_tema_definisce_tutti_i_ruoli(scelto: tema.Tema) -> None:
    # Se un tema dimenticasse un campo, la vista che lo usa fallirebbe solo
    # quando qualcuno la apre con quel tema attivo.
    for campo in scelto.__slots__:
        valore = getattr(scelto, campo)
        assert isinstance(valore, str)
        assert valore


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_i_colori_sono_esadecimali_validi(scelto: tema.Tema) -> None:
    for campo in scelto.__slots__:
        if campo == "nome":
            continue
        valore = str(getattr(scelto, campo))
        assert re.fullmatch(r"#[0-9a-f]{6}", valore), f"{campo} = {valore}"


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_il_testo_si_legge_sullo_sfondo(scelto: tema.Tema) -> None:
    """Il contrasto fra testo e sfondo rispetta lo standard WCAG AA.

    Non e' un dettaglio estetico: sotto 4,5 a 1 il testo diventa faticoso da
    leggere per chiunque e illeggibile per qualcuno. La soglia e' quella
    ufficiale per il testo normale.
    """
    assert contrasto(scelto.testo, scelto.sfondo) >= 4.5
    assert contrasto(scelto.testo, scelto.superficie) >= 4.5
    assert contrasto(scelto.testo_tenue, scelto.sfondo) >= 3.0


def test_il_tema_statico_di_streamlit_non_diverge_da_quello_dinamico() -> None:
    """L'unica duplicazione di colori del progetto resta allineata.

    ``.streamlit/config.toml`` deve ripetere i colori del tema verde, perche'
    Streamlit lo legge prima che Python parta e non puo' importare niente. Un
    commento non impedisce che i due si separino; questo test si'.

    Se divergessero, l'app mostrerebbe per una frazione di secondo i colori
    vecchi a ogni caricamento — il tipo di difetto che nessuno segnala e tutti
    notano.
    """
    percorso = PACCHETTO.parents[1] / ".streamlit" / "config.toml"
    # Il confronto ignora le maiuscole: in un file TOML `#0F6E56` e `#0f6e56`
    # sono lo stesso colore, e far fallire un test su quello sarebbe rumore.
    configurazione = percorso.read_text(encoding="utf-8").lower()

    for campo in ("primario", "sfondo", "superficie", "bordo", "testo", "barra", "barra_testo"):
        colore = str(getattr(tema.VERDE, campo)).lower()
        assert colore in configurazione, f"config.toml non contiene {campo} = {colore}"


def luminanza(colore: str) -> float:
    """Calcola la luminanza relativa di un colore esadecimale.

    Args:
        colore: Il colore in forma ``#rrggbb``.

    Returns:
        La luminanza secondo la formula WCAG, fra 0 e 1.
    """
    canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def contrasto(primo: str, secondo: str) -> float:
    """Rapporto di contrasto fra due colori, secondo WCAG.

    Args:
        primo: Il primo colore, in forma ``#rrggbb``.
        secondo: Il secondo colore.

    Returns:
        Il rapporto, fra 1 (identici) e 21 (nero su bianco).
    """
    a, b = sorted((luminanza(primo), luminanza(secondo)), reverse=True)
    return (a + 0.05) / (b + 0.05)
