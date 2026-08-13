"""L'albo d'oro ricostruito dalle finali (M6-T4).

I numeri di questo modulo sono verificabili **fuori dai dati**: chi ha vinto la
Champions nel 2005 non e' una questione di implementazione. Ogni test qui
confronta il risultato con la storia, non con un'altra funzione del progetto.
"""

from __future__ import annotations

import pandas as pd

from football_analytics import albo


def finale(
    match_id: int,
    anno: int,
    casa: str,
    ospite: str,
    *,
    gol_casa: int,
    gol_ospite: int,
    fase: str,
) -> dict[str, object]:
    """Una riga di partita, con i soli campi che l'albo guarda.

    Args:
        match_id: L'identificativo.
        anno: L'anno della finale.
        casa: La squadra di casa.
        ospite: L'ospite.
        gol_casa: I gol della casa.
        gol_ospite: I gol dell'ospite.
        fase: La fase, per distinguere le finali dal resto.

    Returns:
        La riga.
    """
    return {
        "match_id": match_id,
        "data": pd.Timestamp(f"{anno}-05-30"),
        "fase": fase,
        "casa": casa,
        "ospite": ospite,
        "gol_casa": gol_casa,
        "gol_ospite": gol_ospite,
    }


def test_le_partite_che_non_sono_finali_restano_fuori() -> None:
    """La competizione delle finali contiene anche una partita di girone.

    Nel magazzino vero c'e' Fiorentina — Manchester United del 23 novembre
    1999, fase ``1st Round``. Filtrando per competizione invece che per fase, la
    Fiorentina finirebbe nell'albo d'oro della Champions League: un errore che
    la pagina mostrerebbe con la faccia seria.
    """
    partite = pd.DataFrame(
        [
            finale(
                1, 2019, "Tottenham Hotspur", "Liverpool", gol_casa=0, gol_ospite=2, fase="Final"
            ),
            finale(
                2,
                1999,
                "Fiorentina",
                "Manchester United",
                gol_casa=2,
                gol_ospite=0,
                fase="1st Round",
            ),
        ]
    )

    tavola = albo.albo(partite, pd.DataFrame(columns=["match_id", "squadra", "gol"]))

    assert "Fiorentina" not in set(tavola["squadra"])
    assert set(tavola["squadra"]) == {"Tottenham Hotspur", "Liverpool"}


def test_la_finale_ai_rigori_ha_un_vincitore() -> None:
    """Nel tabellino resta 3-3: senza i rigori la coppa sparirebbe.

    Milan — Liverpool 2005 fini' 3-3 e il Liverpool vinse 3-2 ai rigori. Se il
    vincitore si leggesse solo dai gol, quella coppa non risulterebbe a
    nessuno e nessun controllo se ne accorgerebbe.
    """
    partite = pd.DataFrame(
        [finale(1, 2005, "AC Milan", "Liverpool", gol_casa=3, gol_ospite=3, fase="Final")]
    )
    rigori = pd.DataFrame(
        [
            {"match_id": 1, "squadra": "AC Milan", "gol": True, "rigori_finali": True},
            {"match_id": 1, "squadra": "AC Milan", "gol": True, "rigori_finali": True},
            {"match_id": 1, "squadra": "Liverpool", "gol": True, "rigori_finali": True},
            {"match_id": 1, "squadra": "Liverpool", "gol": True, "rigori_finali": True},
            {"match_id": 1, "squadra": "Liverpool", "gol": True, "rigori_finali": True},
        ]
    )

    voce = albo.di_squadra(albo.albo(partite, rigori), "Liverpool")

    assert voce == albo.Palmares(giocate=1, vinte=1, anni_vinti=(2005,))


def test_senza_i_rigori_nessuno_vince() -> None:
    """Un pareggio senza tiebreak nei dati non assegna la coppa a nessuno.

    Inventare un vincitore sarebbe peggio che non averlo: la finale resta
    contata fra le disputate, e la colonna delle vinte non si gonfia.
    """
    partite = pd.DataFrame(
        [finale(1, 2005, "AC Milan", "Liverpool", gol_casa=3, gol_ospite=3, fase="Final")]
    )

    tavola = albo.albo(partite, pd.DataFrame(columns=["match_id", "squadra", "gol"]))

    assert list(tavola["vinte"]) == [0, 0]
    assert list(tavola["giocate"]) == [1, 1]


def test_chi_non_ha_finali_non_ha_una_riga() -> None:
    """Non e' un palmares da zero, e' un palmares sconosciuto.

    La differenza conta per chi disegna: ``None`` significa «non mostrare
    niente», mentre uno zero verrebbe letto come «non ha mai vinto».
    """
    partite = pd.DataFrame(
        [finale(1, 2019, "Tottenham Hotspur", "Liverpool", gol_casa=0, gol_ospite=2, fase="Final")]
    )

    tavola = albo.albo(partite, pd.DataFrame(columns=["match_id", "squadra", "gol"]))

    assert albo.di_squadra(tavola, "Napoli") is None
    assert albo.di_squadra(tavola, "Tottenham Hotspur") == albo.Palmares(
        giocate=1, vinte=0, anni_vinti=()
    )


def test_senza_finali_la_tavola_e_vuota_ma_ha_le_colonne() -> None:
    """Chi legge non deve incontrare un ``KeyError`` su una selezione senza finali."""
    tavola = albo.albo(
        pd.DataFrame(columns=["match_id", "data", "fase", "casa", "ospite"]),
        pd.DataFrame(columns=["match_id", "squadra", "gol"]),
    )

    assert tavola.empty
    assert set(tavola.columns) == {"squadra", "giocate", "vinte", "anni_vinti"}
    assert albo.di_squadra(tavola, "Ajax") is None
