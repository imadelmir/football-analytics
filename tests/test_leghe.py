"""Il confronto fra i quattro campionati (M6-T8).

Il test piu' importante di questo file non guarda un calcolo: verifica che la
premessa su cui poggia l'intera vista sia vera nei dati. Il backlog chiedeva di
avvertire che «la Serie A usa il modello base», e misurando la copertura 360
risulta che **nessuno** dei quattro campionati ha quei dati. Se un giorno il
magazzino cambiasse, l'avvertenza scritta in pagina diventerebbe falsa senza
che nulla protesti.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import leghe
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "matches.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


def due_campionati() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Due campionati finti, uno che tira molto e male, uno poco e bene.

    Returns:
        Le partite e i tiri.
    """
    chiavi = leghe.campionati()[:2]
    partite = pd.DataFrame(
        [
            {"competizione": chiavi[0], "gol_casa": 2, "gol_ospite": 1},
            {"competizione": chiavi[0], "gol_casa": 1, "gol_ospite": 0},
            {"competizione": chiavi[1], "gol_casa": 3, "gol_ospite": 3},
            {"competizione": chiavi[1], "gol_casa": 1, "gol_ospite": 1},
        ]
    )
    tiri = pd.DataFrame(
        # Il primo: venti tiri da 0,05. Il secondo: quattro tiri da 0,50.
        [{"competizione": chiavi[0], "xg_statsbomb": 0.05, "gol": False} for _ in range(20)]
        + [{"competizione": chiavi[1], "xg_statsbomb": 0.50, "gol": True} for _ in range(4)]
    )
    return partite, tiri


def test_i_numeri_sono_per_partita_o_per_tiro() -> None:
    """Con la Ligue 1 a 377 partite, un totale grezzo mentirebbe.

    Direbbe che in Francia si segna meno, quando semplicemente si e' giocato
    tre volte in meno — un difetto che nessuno noterebbe guardando la pagina.
    """
    partite, tiri = due_campionati()
    chiavi = leghe.campionati()[:2]

    tavola = leghe.riassunto(partite, tiri).set_index("competizione")

    assert tavola.loc[chiavi[0], "gol_per_partita"] == pytest.approx(2.0)
    assert tavola.loc[chiavi[0], "tiri_per_partita"] == pytest.approx(10.0)
    assert tavola.loc[chiavi[0], "xg_per_tiro"] == pytest.approx(0.05)
    assert tavola.loc[chiavi[1], "xg_per_tiro"] == pytest.approx(0.50)


def test_la_conversione_conta_i_gol_da_tiro() -> None:
    """Il denominatore sono i tiri, quindi il numeratore non puo' avere autogol.

    Un autogol sta nel risultato ma non nasce da un tiro di chi lo subisce:
    contarlo qui gonfierebbe la conversione di un campionato per un motivo che
    con la mira non ha niente a che vedere.
    """
    partite, tiri = due_campionati()
    chiavi = leghe.campionati()[:2]

    tavola = leghe.riassunto(partite, tiri).set_index("competizione")

    assert tavola.loc[chiavi[0], "conversione"] == pytest.approx(0.0)
    assert tavola.loc[chiavi[1], "conversione"] == pytest.approx(1.0)


def test_le_curve_di_densita_sommano_a_uno() -> None:
    """Normalizzate, o il grafico mostrerebbe chi tira di piu' invece che da dove.

    I quattro campionati hanno un numero diverso di tiri: sovrapporre i
    conteggi grezzi metterebbe la curva della Serie A sempre sopra quella della
    Ligue 1, e la forma — che e' l'informazione — si perderebbe.
    """
    _, tiri = due_campionati()
    chiavi = leghe.campionati()[:2]

    curve = leghe.distribuzione(tiri)

    for chiave in chiavi:
        assert curve[chiave].sum() == pytest.approx(1.0)


def test_le_curve_stanno_dove_stanno_i_tiri() -> None:
    """Chi tira da 0,50 deve avere il picco a destra di chi tira da 0,05."""
    _, tiri = due_campionati()
    scarso, buono = leghe.campionati()[:2]

    curve = leghe.distribuzione(tiri).set_index("xg")

    # `float()` esplicito: per pandas-stubs `idxmax` ha un tipo unione che
    # comprende le stringhe, e il confronto non compila anche se qui l'indice
    # e' fatto di numeri.
    picco_buono = float(curve[buono].idxmax())
    picco_scarso = float(curve[scarso].idxmax())

    assert picco_buono > picco_scarso


def test_senza_campionati_non_esplode() -> None:
    vuoto = pd.DataFrame(columns=["competizione", "gol_casa", "gol_ospite"])
    tiri = pd.DataFrame(columns=["competizione", "xg_statsbomb", "gol"])

    assert leghe.riassunto(vuoto, tiri).empty
    assert leghe.distribuzione(tiri).empty
    assert leghe.scarti(pd.DataFrame()) == {}


@senza_magazzino
def test_nessun_campionato_ha_i_dati_360() -> None:
    """La premessa dell'avvertenza, verificata invece che ripetuta.

    Il backlog diceva che la Serie A e' il caso particolare. Non lo e': la
    copertura e' zero in tutti e quattro. La pagina scrive che il confronto
    regge fra i campionati e non verso i tornei, e questa affermazione deve
    restare vera anche se il magazzino cambia.
    """
    partite = pd.read_parquet(DATA_PROCESSED / "matches.parquet")

    nei_campionati = partite[partite["competizione"].isin(leghe.campionati())]
    nei_tornei = partite[partite["competizione"].isin(["mondiali_2022", "euro_2024"])]

    assert nei_campionati["ha_360"].sum() == 0, (
        "un campionato ha i dati 360: l'avvertenza va rivista"
    )
    assert nei_tornei["ha_360"].all(), "i tornei dovrebbero avere i dati 360"


@senza_magazzino
def test_i_quattro_campionati_del_magazzino_sono_confrontabili() -> None:
    """Stessa stagione e stesso numero di giornate, tranne il buco dichiarato.

    Tre campionati su quattro hanno 380 partite; la Ligue 1 ne ha 377 perche'
    all'Open Data ne mancano tre. E' la stessa lacuna che la vista Squadre
    dichiara, e qui e' la ragione per cui nessun numero e' un totale.
    """
    partite = pd.read_parquet(DATA_PROCESSED / "matches.parquet")
    tiri = pd.read_parquet(DATA_PROCESSED / "shots.parquet")

    tavola = leghe.riassunto(partite, tiri).set_index("competizione")

    assert len(tavola) == 4
    assert set(tavola["partite"]) == {380.0, 377.0}
    assert tavola.loc["ligue1_2015_16", "partite"] == 377.0
