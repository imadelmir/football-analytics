"""Il confronto fra i quattro campionati (M6-T8).

I test piu' importanti di questo file non guardano un calcolo: misurano le due
coperture su cui poggiava l'avvertenza della vista, e stanno qui perche' la
prima versione di quella avvertenza era **falsa**.

Diceva che senza i dati 360 l'xG e' stimato «senza sapere dove fossero
difensori e portiere». La prima meta' era giusta — i dati 360 sono a zero in
tutti e quattro i campionati — ma la conseguenza no, perche' i dati 360 e il
fotogramma del tiro sono due prodotti diversi. Il test misura entrambi: il
fotogramma c'e' quasi sempre ovunque, i dati 360 solo nei tornei recenti. Con
tutte e due le coperture scritte, la confusione non si puo' rifare in silenzio.
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

#: Sotto quale quota di tiri col fotogramma il modello spaziale non reggerebbe.
#:
#: Le coperture misurate stanno fra il 95 % delle finali di Champions e il
#: 99,3 % della Premier. La soglia e' larga apposta: serve a distinguere «c'e'
#: quasi sempre» da «non c'e'», non a inchiodare una cifra che cambierebbe se
#: StatsBomb ripubblicasse una stagione.
MINIMA_COPERTURA = 0.90


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
    """I dati 360 sono i fotogrammi di ogni evento: solo nei tornei recenti.

    Il backlog diceva che la Serie A e' il caso particolare. Non lo e': la
    copertura e' zero in tutti e quattro. Il test da solo pero' non basta, e la
    storia di questo file lo dimostra — da questo fatto vero e' stata tratta
    una conseguenza falsa. Va letto insieme a
    :func:`test_il_fotogramma_del_tiro_invece_c_e_quasi_sempre`.
    """
    partite = pd.read_parquet(DATA_PROCESSED / "matches.parquet")

    nei_campionati = partite[partite["competizione"].isin(leghe.campionati())]
    nei_tornei = partite[partite["competizione"].isin(["mondiali_2022", "euro_2024"])]

    assert nei_campionati["ha_360"].sum() == 0, (
        "un campionato ha i dati 360: l'avvertenza va rivista"
    )
    assert nei_tornei["ha_360"].all(), "i tornei dovrebbero avere i dati 360"


@senza_magazzino
def test_il_fotogramma_del_tiro_invece_c_e_quasi_sempre() -> None:
    """Il fatto che rende falsa la prima stesura dell'avvertenza.

    Il *fotogramma del tiro* — la posizione dei giocatori nell'istante del tiro
    — e' allegato agli eventi di tiro anche dove i dati 360 non ci sono. E'
    quello che il modello spaziale legge, ed e' il motivo per cui gira anche
    sui campionati 2015/16.

    La prova che i due prodotti sono indipendenti sta nelle **finali di
    Champions**: dati 360 a zero, fotogramma del tiro sul 95 % dei tiri, e M5
    ci ha applicato sopra il modello spaziale.
    """
    tiri = pd.read_parquet(DATA_PROCESSED / "shots.parquet")

    nei_campionati = tiri[tiri["competizione"].isin(leghe.campionati())]
    nelle_finali = tiri[tiri["competizione"] == "champions_finali"]

    assert nei_campionati["ha_fotogramma"].mean() > MINIMA_COPERTURA, (
        "senza il fotogramma del tiro il modello spaziale non potrebbe girare sui campionati"
    )
    assert nei_campionati["ha_360"].sum() == 0
    assert nelle_finali["ha_360"].sum() == 0
    assert nelle_finali["ha_fotogramma"].mean() > MINIMA_COPERTURA, (
        "le finali hanno il fotogramma del tiro pur senza i dati 360: sono due cose diverse"
    )


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
