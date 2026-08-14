"""Le singole partite e il giudizio dell'xG (M6-T7).

Il giudizio «ha vinto la squadra sbagliata» e' una conclusione, non un dato: se
la soglia o il confronto fossero storti, la vista continuerebbe a produrre
frasi sensate su partite sbagliate. Questi test guardano i casi limite in cui
la conclusione puo' essere falsa restando plausibile.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import partite
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "matches.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


def incontro(
    match_id: int,
    casa: str,
    ospite: str,
    *,
    gol: tuple[int, int],
    xg: tuple[float, float],
) -> dict[str, object]:
    """Una partita con i soli campi che questo modulo guarda.

    Args:
        match_id: L'identificativo.
        casa: La squadra di casa.
        ospite: L'ospite.
        gol: I gol di casa e ospite.
        xg: L'xG di casa e ospite.

    Returns:
        La riga.
    """
    return {
        "match_id": match_id,
        "data": f"2016-01-{match_id:02d}",
        "giornata": match_id,
        "casa": casa,
        "ospite": ospite,
        "gol_casa": gol[0],
        "gol_ospite": gol[1],
        "xg_casa": xg[0],
        "xg_ospite": xg[1],
        "tiri_casa": 10,
        "tiri_ospite": 10,
        "autogol_casa": 0,
        "autogol_ospite": 0,
    }


def quattro() -> pd.DataFrame:
    """Quattro partite scelte per coprire i casi che contano.

    Returns:
        Le partite di prova.
    """
    return pd.DataFrame(
        [
            # Vince chi ha creato di piu': nessun ribaltamento.
            incontro(1, "Alfa", "Beta", gol=(2, 0), xg=(2.4, 0.6)),
            # Vince chi ha creato molto meno: ribaltamento vero.
            incontro(2, "Gamma", "Delta", gol=(0, 1), xg=(2.2, 0.4)),
            # Vince di misura chi ha 0,1 di xG in meno: **non** e' un
            # ribaltamento, e' rumore.
            incontro(3, "Epsilon", "Zeta", gol=(1, 0), xg=(1.0, 1.1)),
            # Pareggio con una squadra nettamente superiore: nessun vincitore,
            # quindi niente da ribaltare.
            incontro(4, "Eta", "Theta", gol=(1, 1), xg=(2.8, 0.5)),
        ]
    )


def test_il_ribaltamento_chiede_uno_scarto_vero() -> None:
    """Con 0,1 di xG di differenza le due squadre hanno creato la stessa cosa.

    Senza soglia la vista chiamerebbe «immeritata» una vittoria decisa da un
    tiro da fuori area in piu', e la lista delle sorprese si riempirebbe di
    partite in cui non e' successo niente di strano.
    """
    tavola = partite.con_esiti(quattro())

    per_id = dict(zip(tavola["match_id"], tavola["ribaltata"], strict=True))
    assert per_id[2] is True or per_id[2]
    assert not per_id[3]


def test_un_pareggio_non_ribalta_niente() -> None:
    """Senza vincitore non c'e' niente da ribaltare.

    E' il caso in cui un confronto fra stringhe vuote direbbe di si': la
    vincitrice e' ``""``, la favorita e' «Eta», e ``"" != "Eta"``.
    """
    tavola = partite.con_esiti(quattro())
    pari = tavola[tavola["match_id"] == 4].iloc[0]

    assert pari["vincitrice"] == ""
    assert pari["favorita_xg"] == "Eta"
    assert not pari["ribaltata"]


def test_le_sorprese_partono_dalla_piu_clamorosa() -> None:
    """L'ordine e' l'informazione: la prima riga deve essere la piu' assurda."""
    sorprese = partite.ribaltate(quattro())

    assert list(sorprese["match_id"]) == [2]


def test_i_totali_e_la_quota_di_sorprese() -> None:
    """La quota va sul totale delle partite, non sulle sole decise."""
    totali = partite.numeri(quattro())

    assert totali["partite"] == 4.0
    assert totali["ribaltate"] == 1.0
    assert totali["quota_ribaltate"] == pytest.approx(0.25)


def test_la_data_diventa_un_timestamp() -> None:
    """Nel magazzino e' una stringa, e chi disegna non deve saperlo.

    Senza la conversione, formattare la data in una f-string solleva «Invalid
    format specifier» — un errore che compare **solo** aprendo una scheda, non
    caricando la pagina.
    """
    numeri = partite.scheda(quattro(), 1)

    assert numeri is not None
    assert isinstance(numeri.data, pd.Timestamp)
    assert f"{numeri.data:%d/%m/%Y}" == "01/01/2016"


def test_una_partita_che_non_esiste_non_rompe_la_scheda() -> None:
    assert partite.scheda(quattro(), 999) is None
    assert partite.numeri(pd.DataFrame())["partite"] == 0.0
    assert partite.elenco(pd.DataFrame()).empty


def test_la_corsa_dell_xg_parte_da_zero_e_cumula() -> None:
    """Senza la riga iniziale la curva comincerebbe al primo tiro.

    Sembrerebbe che la partita inizi al minuto in cui qualcuno calcia, e due
    partite con primi tiri a minuti diversi non sarebbero confrontabili a
    occhio.
    """
    tiri = pd.DataFrame(
        [
            {"match_id": 1, "minuto": 10, "squadra": "Alfa", "xg_statsbomb": 0.3},
            {"match_id": 1, "minuto": 30, "squadra": "Beta", "xg_statsbomb": 0.2},
            {"match_id": 1, "minuto": 30, "squadra": "Alfa", "xg_statsbomb": 0.5},
            {"match_id": 2, "minuto": 5, "squadra": "Alfa", "xg_statsbomb": 9.9},
        ]
    )

    corsa = partite.corsa_xg(tiri, 1, ["Alfa", "Beta"])

    assert corsa.iloc[0]["Alfa"] == 0.0
    assert corsa[corsa["minuto"] == 10].iloc[0]["Alfa"] == pytest.approx(0.3)
    assert corsa.iloc[-1]["Alfa"] == pytest.approx(0.8)
    assert corsa.iloc[-1]["Beta"] == pytest.approx(0.2)


def test_i_rigori_dei_tiebreak_restano_fuori_dalla_corsa() -> None:
    """Sono una lotteria dopo la partita, non occasioni create durante."""
    tiri = pd.DataFrame(
        [
            {
                "match_id": 1,
                "minuto": 10,
                "squadra": "Alfa",
                "xg_statsbomb": 0.3,
                "rigori_finali": False,
            },
            {
                "match_id": 1,
                "minuto": 121,
                "squadra": "Alfa",
                "xg_statsbomb": 0.76,
                "rigori_finali": True,
            },
        ]
    )

    corsa = partite.corsa_xg(tiri, 1, ["Alfa", "Beta"])

    assert corsa["minuto"].max() == 10
    assert corsa.iloc[-1]["Alfa"] == pytest.approx(0.3)


@senza_magazzino
def test_le_sorprese_della_serie_a_sono_quelle_misurate() -> None:
    """Il numero scritto nella documentazione va tenuto onesto.

    Il modulo dichiara 30 partite su 380: se qualcuno cambiasse la soglia
    quel numero diventerebbe falso senza che nulla protesti, e resterebbe
    scritto in un docstring che nessuno rilegge.
    """
    tutte = pd.read_parquet(DATA_PROCESSED / "matches.parquet")
    serie_a = tutte[tutte["competizione"] == "serie_a_2015_16"]

    totali = partite.numeri(serie_a)

    assert totali["partite"] == 380
    assert totali["ribaltate"] == 30
