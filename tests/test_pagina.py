"""La pagina Streamlit viene **eseguita**, non solo importata (M6-T3).

Questo test esiste per un errore preciso: la Panoramica e' stata scritta,
riscritta tre volte e mostrata all'utente **senza essere mai eseguita**. I test
coprivano le funzioni sotto — aggregazioni, grafici, tema — ma nessuno faceva
girare la pagina, e un difetto nel modo in cui quelle funzioni vengono messe
insieme non sarebbe emerso finche' qualcuno non apriva il browser.

``AppTest`` esegue lo script Streamlit senza browser e senza server, e riporta
qualunque eccezione. Non verifica come appare la pagina — quello resta un
lavoro per gli occhi — ma verifica che appaia.

Il test si salta se il magazzino non e' stato costruito: i Parquet entrano in
git solo a M7-T1, quindi in CI non ci sono ancora.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from football_analytics.config import DATA_PROCESSED

#: La pagina da eseguire.
PAGINA: Path = Path(__file__).parents[1] / "app" / "Panoramica.py"

#: Quanti secondi concedere: la prima esecuzione legge tutti i Parquet.
ATTESA: int = 120

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "shots.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


@pytest.fixture(scope="module")
def eseguita() -> object:
    """Esegue la Panoramica una volta sola per tutto il modulo.

    Returns:
        L'applicazione dopo l'esecuzione.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    return app


@senza_magazzino
def test_la_pagina_gira_senza_eccezioni(eseguita: object) -> None:
    """Il test che sarebbe servito tre riscritture fa."""
    errori = [str(e.value) for e in eseguita.exception]  # type: ignore[attr-defined]

    assert not errori, f"la pagina ha sollevato: {errori}"


@senza_magazzino
def test_i_due_filtri_ci_sono_e_nascono_dal_magazzino(eseguita: object) -> None:
    """Due filtri, non tre: la stagione e' sparita perche' non poteva scegliere.

    Ogni competizione del magazzino ha una sola stagione, quindi il menu aveva
    sempre una voce sola. Il test controlla anche che le opzioni vengano dai
    dati e non da un elenco scritto a mano: aggiungere una competizione deve
    farla comparire da sola.
    """
    filtri = eseguita.selectbox  # type: ignore[attr-defined]

    assert [s.label for s in filtri] == ["Competizione", "Squadra"]
    assert len(filtri[0].options) == len(dati_competizioni())
    assert len(filtri[1].options) > 1


def dati_competizioni() -> list[str]:
    """Le competizioni del magazzino, lette senza passare per l'app.

    Returns:
        Le chiavi delle competizioni.
    """
    import pandas as pd  # noqa: PLC0415

    return sorted(pd.read_parquet(DATA_PROCESSED / "matches.parquet")["competizione"].unique())


@senza_magazzino
def test_ci_sono_i_quattro_grafici_previsti(eseguita: object) -> None:
    # Mappa dei tiri, andamento, anello dell'xG realizzato, distribuzione.
    assert len(eseguita.get("plotly_chart")) == 4  # type: ignore[attr-defined]


@senza_magazzino
def test_cambiare_competizione_non_rompe_la_pagina(eseguita: object) -> None:
    """Il filtro si muove davvero, e la pagina regge il rerun.

    E' il momento in cui Streamlit riesegue tutto lo script da capo: se una
    funzione dipendesse da uno stato lasciato dal giro precedente, e' qui che
    salterebbe fuori.
    """
    app = eseguita
    filtro = app.selectbox[0]  # type: ignore[attr-defined]
    seconda = filtro.options[1]

    filtro.set_value(seconda).run()

    assert not app.exception, f"cambiando competizione: {[str(e.value) for e in app.exception]}"  # type: ignore[attr-defined]


def test_la_pagina_non_usa_piu_use_container_width() -> None:
    """``use_container_width`` e' scaduto il 31 dicembre 2025.

    Legge il sorgente, quindi gira anche senza magazzino: e' un controllo sul
    codice, non sul comportamento.

    Streamlit lo accetta ancora per compatibilita' ma lo segnala a ogni
    chiamata. Un avviso ignorato e' un errore rimandato: il test lo trasforma
    in un fallimento adesso, invece che in una pagina rotta al prossimo
    aggiornamento.
    """
    sorgente = PAGINA.read_text(encoding="utf-8")

    assert "use_container_width" not in sorgente


@senza_magazzino
def test_scegliere_un_campionato_ricolora_la_pagina() -> None:
    """Il tema segue davvero il filtro, fino al foglio di stile iniettato.

    E' la verifica che manca a :mod:`tests.test_tema`: li' si controlla che
    ``per_competizione`` restituisca il tema giusto, che e' vero anche se
    nessuno chiama quella funzione. Qui si muove il filtro vero e si legge il
    CSS che finisce nella pagina.

    Il confronto e' sul fondo, non sull'accento: il fondo e' l'unica cosa che
    cambia in **tutta** la finestra, ed e' quello che si nota.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    from football_analytics import tema  # noqa: PLC0415

    attesi = {
        "premier_2015_16": tema.PREMIER,
        "la_liga_2015_16": tema.LIGA,
        "serie_a_2015_16": tema.SERIE_A,
        "ligue1_2015_16": tema.LIGUE1,
        "champions_finali": tema.BLU,
        "euro_2024": tema.VERDE,
    }

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()

    # ``options`` restituisce le etichette gia' passate per ``format_func``,
    # mentre ``set_value`` vuole il valore grezzo. Iterare sulle opzioni
    # sembrava naturale e non selezionava niente: il ciclo girava, nessun
    # confronto veniva eseguito e il test passava. Le chiavi stanno qui sotto
    # proprio per non ripescarle da li'.
    for chiave, scelto in attesi.items():
        app.selectbox[0].set_value(chiave).run()

        assert not app.exception, f"{chiave}: {[str(e.value) for e in app.exception]}"
        fogli = [str(m.value) for m in app.markdown if "--st-sfondo" in str(m.value)]
        assert len(fogli) == 1, f"{chiave}: fogli di stile trovati {len(fogli)}"
        assert f"--st-sfondo: {scelto.sfondo};" in fogli[0], chiave
        assert scelto.striscia[0] in fogli[0], f"fascia mancante: {chiave}"


@senza_magazzino
def test_cambiare_competizione_azzera_una_squadra_che_non_esiste_piu() -> None:
    """Il caso che rompe i filtri a cascata.

    Si sceglie il Real Madrid nella Liga e poi si passa alla Premier: la
    squadra selezionata non e' piu' fra le opzioni. Streamlit riporta il
    filtro a vuoto invece di sollevare, e la pagina mostra tutta la Premier —
    ma e' un comportamento su cui il codice fa affidamento senza dirlo, quindi
    vale la pena inchiodarlo.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.selectbox[0].set_value("la_liga_2015_16").run()
    app.selectbox[1].set_value("Real Madrid").run()
    assert app.selectbox[1].value == "Real Madrid"

    app.selectbox[0].set_value("premier_2015_16").run()

    assert not app.exception, [str(e.value) for e in app.exception]
    assert app.selectbox[1].value is None
    assert "Real Madrid" not in app.selectbox[1].options
