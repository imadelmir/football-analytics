"""La cache del magazzino, verificata contando le letture (M6-T13).

Il criterio della task e' che **cambiare un filtro non rilegga i file da
disco**, e finora era stato dato per soddisfatto leggendo il codice: il
decoratore c'e', quindi funziona. Non e' una verifica, e' una deduzione — e
questo file la sostituisce con una misura.

Il modo e' contare le chiamate reali a ``pandas.read_parquet`` mentre la
dashboard viene usata. Se la cache funziona, il contatore sale una volta per
tabella all'avvio e poi si ferma, qualunque cosa si tocchi.

**Perche' conta davvero.** Streamlit riesegue lo script da capo a ogni
interazione. Senza cache, ogni clic rileggerebbe ``shots.parquet`` — 43.849
righe — e su Streamlit Cloud, che concede meno di un gigabyte di RAM, sarebbe
il modo piu' rapido per far morire l'app al primo utente che tocca un filtro.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest

from football_analytics.config import DATA_PROCESSED

if TYPE_CHECKING:
    from collections.abc import Iterator

#: La pagina da cui parte ogni prova.
PAGINA: Path = Path(__file__).parents[1] / "app" / "Panoramica.py"

#: Quanti secondi concedere: la prima esecuzione legge tutto il magazzino.
ATTESA: int = 120

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "shots.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


class Contatore:
    """Conta le letture reali dal disco, senza impedirle.

    Un semplice contatore e non un finto ``read_parquet``: se sostituissimo la
    lettura, il test verificherebbe che la cache viene chiamata e non che i
    file non vengono aperti — che e' proprio la differenza in questione.

    Attributes:
        letture: I nomi dei file letti, nell'ordine.
    """

    def __init__(self) -> None:
        """Parte da zero letture."""
        self.letture: list[str] = []

    def __call__(self, percorso: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
        """Registra la lettura e la esegue davvero.

        Args:
            percorso: Il file da leggere.
            args: Il resto degli argomenti di ``read_parquet``.
            kwargs: Il resto degli argomenti nominati.

        Returns:
            La tabella letta.
        """
        self.letture.append(Path(str(percorso)).name)
        return self._vero(percorso, *args, **kwargs)

    _vero = staticmethod(pd.read_parquet)


@pytest.fixture
def contatore(monkeypatch: pytest.MonkeyPatch) -> Iterator[Contatore]:
    """Sostituisce ``pandas.read_parquet`` con un contatore che legge davvero.

    Args:
        monkeypatch: Lo strumento di pytest.

    Yields:
        Il contatore.
    """
    spia = Contatore()
    monkeypatch.setattr(pd, "read_parquet", spia)
    yield spia


@senza_magazzino
def test_cambiare_filtro_non_rilegge_i_file(contatore: Contatore) -> None:
    """Il criterio di M6-T13, misurato invece che dedotto.

    Si avvia la Home, si conta quante letture sono servite, poi si muove il
    filtro competizione due volte. Il contatore non deve salire di un'unita'.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    dopo_avvio = len(contatore.letture)
    assert dopo_avvio > 0, "la pagina non ha letto niente: il contatore non e' agganciato"

    app.selectbox[0].set_value("serie_a_2015_16").run()
    app.selectbox[0].set_value("premier_2015_16").run()

    assert not app.exception, [str(e.value) for e in app.exception]
    assert len(contatore.letture) == dopo_avvio, (
        f"la cache non ha retto: letture in piu' {contatore.letture[dopo_avvio:]}"
    )


@senza_magazzino
def test_ogni_tabella_si_legge_una_volta_sola(contatore: Contatore) -> None:
    """Nessun file viene aperto due volte nella stessa sessione.

    Due letture dello stesso Parquet vorrebbero dire che qualcuno chiama la
    lettura fuori dalla funzione in cache — o che la chiave della cache cambia
    a ogni giro, che e' lo stesso difetto travestito.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()

    assert len(contatore.letture) == len(set(contatore.letture)), (
        f"qualche tabella e' stata letta due volte: {contatore.letture}"
    )


@senza_magazzino
def test_cambiare_pagina_non_rilegge_i_file(contatore: Contatore) -> None:
    """La cache di Streamlit e' della sessione, non della pagina.

    Passando fra le viste il magazzino resta in memoria: un utente che gira
    per sette pagine non deve pagare sette volte la lettura.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    dopo_avvio = len(contatore.letture)

    for pagina in ("pages/Squadre.py", "pages/Partite.py", "pages/Giocatori.py"):
        app.switch_page(pagina)
        app.run()
        assert not app.exception, f"{pagina}: {[str(e.value) for e in app.exception]}"

    nuove = list(contatore.letture[dopo_avvio:])
    assert len(set(nuove)) == len(nuove), f"stessa tabella riletta: {nuove}"


def test_la_lettura_dal_disco_avviene_in_un_posto_solo() -> None:
    """Un controllo sul codice, che gira anche senza magazzino.

    La cache protegge ``dati.leggi``. Se una pagina leggesse un Parquet per
    conto suo, la protezione non varrebbe per quella lettura e il difetto si
    vedrebbe solo con il profiler in mano.
    """
    app = Path(__file__).parents[1] / "app"
    colpevoli = [
        percorso.relative_to(app).as_posix()
        for percorso in app.rglob("*.py")
        if "read_parquet" in percorso.read_text(encoding="utf-8")
    ]

    assert colpevoli == ["dati.py"], f"letture dal disco fuori da dati.py: {colpevoli}"
