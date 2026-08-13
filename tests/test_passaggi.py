"""Verifiche della rete dei passaggi (M6-T4).

Gli errori possibili qui sono tutti silenziosi: un arco contato due volte, un
giocatore che compare nella rete senza essere fra i titolari, un
autopassaggio. Nessuno di questi rompe niente — producono solo un disegno
plausibile e sbagliato.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import passaggi
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "passes.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


def giocatori_finti() -> pd.DataFrame:
    """Cinque giocatori, uno senza posizione.

    Returns:
        Le statistiche minime che :func:`passaggi.titolari` usa.
    """
    return pd.DataFrame(
        {
            "giocatore_id": [1, 2, 3, 4, 5],
            "giocatore_breve": ["Uno", "Due", "Tre", "Quattro", "Cinque"],
            "ruolo": ["Goalkeeper", "Left Back", "Center Midfield", "Left Wing", "Striker"],
            "minuti": [900, 800, 700, 600, 500],
            "x_media": [10.0, 40.0, 60.0, 75.0, None],
            "y_media": [40.0, 20.0, 40.0, 60.0, None],
        }
    )


def passaggi_finti() -> pd.DataFrame:
    """Passaggi con un doppio verso, un autopassaggio e un estraneo."""
    return pd.DataFrame(
        {
            "passatore_id": [1, 2, 2, 3, 3, 9],
            "ricevitore_id": [2, 1, 3, 2, 3, 1],
            "passaggi": [10, 5, 20, 4, 99, 50],
        }
    )


def test_i_titolari_sono_i_piu_impiegati_con_una_posizione() -> None:
    """Chi non ha una posizione media non puo' stare su un campo.

    Capita a chi ha giocato pochissimo: senza tocchi non c'e' una posizione, e
    disegnarlo all'origine lo metterebbe in un angolo del campo come se ci
    avesse giocato davvero.
    """
    scelti = passaggi.titolari(giocatori_finti(), quanti=4)

    assert list(scelti["giocatore_breve"]) == ["Uno", "Due", "Tre", "Quattro"]
    assert "Cinque" not in set(scelti["giocatore_breve"])


def test_gli_archi_sono_senza_verso_e_sommati() -> None:
    """Uno-Due e Due-Uno sono lo stesso legame, e vale 15 passaggi.

    E' il difetto piu' probabile: tenendo i due versi separati la stessa
    coppia comparirebbe due volte, con due linee sovrapposte di spessore
    diverso.
    """
    scelti = passaggi.titolari(giocatori_finti())

    archi = passaggi.rete(passaggi_finti(), scelti)

    coppia = archi[((archi["da"] == "Uno") & (archi["a"] == "Due"))]
    assert len(coppia) == 1
    assert int(coppia.iloc[0]["passaggi"]) == 15


def test_gli_autopassaggi_spariscono() -> None:
    # Tre verso Tre vale 99 passaggi nei dati finti: se passasse sarebbe il
    # legame piu' spesso della rete, e sarebbe un cappio su un pallino.
    scelti = passaggi.titolari(giocatori_finti())

    archi = passaggi.rete(passaggi_finti(), scelti)

    assert (archi["da"] != archi["a"]).all()
    assert int(archi["passaggi"].max()) == 24


def test_chi_non_e_titolare_resta_fuori() -> None:
    # Il giocatore 9 non e' fra i titolari e ha cinquanta passaggi: se
    # entrasse, la rete mostrerebbe un nodo senza posizione.
    scelti = passaggi.titolari(giocatori_finti())

    archi = passaggi.rete(passaggi_finti(), scelti)

    nomi = set(archi["da"]) | set(archi["a"])
    assert nomi <= set(scelti["giocatore_breve"])


def test_il_coinvolgimento_conta_ogni_arco_da_entrambi_i_lati() -> None:
    """La somma dei coinvolgimenti e' il doppio dei passaggi disegnati.

    Ogni legame tocca due giocatori: se il totale non fosse il doppio,
    vorrebbe dire che un estremo di qualche arco non viene contato, e quel
    giocatore apparirebbe piu' piccolo di quanto e'.
    """
    scelti = passaggi.titolari(giocatori_finti())
    archi = passaggi.rete(passaggi_finti(), scelti)

    conteggi = passaggi.coinvolgimento(archi, scelti)

    assert conteggi.sum() == 2 * archi["passaggi"].sum()
    assert set(conteggi.index) == set(scelti["giocatore_breve"])


def test_niente_dati_niente_rete() -> None:
    vuoti = giocatori_finti().head(0)
    scelti = passaggi.titolari(giocatori_finti())

    assert passaggi.titolari(vuoti).empty
    assert passaggi.rete(passaggi_finti().head(0), scelti).empty
    assert passaggi.rete(passaggi_finti(), vuoti).empty
    assert passaggi.coinvolgimento(passaggi_finti().head(0), scelti).sum() == 0


@senza_magazzino
def test_la_rete_del_psg_ha_senso_calcistico() -> None:
    """Un controllo di plausibilita' sui dati veri.

    Non verifica un numero — verifica che la rete non sia rumore: il regista
    deve essere fra i piu' coinvolti e la difesa deve stare dietro l'attacco.
    Se il ribaltamento delle coordinate saltasse, questo test fallirebbe.
    """
    passi = pd.read_parquet(DATA_PROCESSED / "passes.parquet")
    giocatori = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")
    quali = (slice(None), "ligue1_2015_16", "Paris Saint-Germain")
    suoi = giocatori[(giocatori["competizione"] == quali[1]) & (giocatori["squadra"] == quali[2])]
    suoi_passi = passi[(passi["competizione"] == quali[1]) & (passi["squadra"] == quali[2])]

    scelti = passaggi.titolari(suoi)
    archi = passaggi.rete(suoi_passi, scelti)
    conteggi = passaggi.coinvolgimento(archi, scelti)

    assert len(scelti) == passaggi.TITOLARI
    assert len(archi) == passaggi.ARCHI
    posizioni = scelti.set_index("giocatore_breve")["x_media"]
    assert posizioni["Kevin Trapp"] < posizioni["Thiago Silva"], "il portiere sta dietro"
    assert posizioni["Thiago Silva"] < posizioni["Zlatan Ibrahimović"], "l'attacco sta avanti"
    assert conteggi.idxmax() == "Thiago Motta", "il regista tocca piu' palloni"
