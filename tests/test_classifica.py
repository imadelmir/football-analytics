"""Verifiche della classifica e degli aggregati per squadra (M6-T4).

**La verifica principale non e' un test unitario: e' la realta'.** Le
classifiche di Liga, Premier e Serie A 2015/16 sono pubbliche e note, e una
classifica ricostruita dai risultati o riproduce quei numeri o e' sbagliata.
Barcellona 91, Leicester 81, Juventus 91 — non c'e' margine di
interpretazione, ed e' una verifica molto piu' forte di qualunque tabella
inventata da chi scrive il codice.

Il resto sono invarianti che valgono su qualunque insieme di partite, comprese
quelle finte: servono a coprire i casi che i dati veri non contengono, come una
selezione vuota.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import classifica
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "matches.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)

#: Le classifiche vere del 2015/16, dalle fonti pubbliche dei campionati.
#:
#: I nomi sono quelli di StatsBomb, che non sempre coincidono con quelli
#: correnti: nella Serie A la Roma e' ``AS Roma`` e nella Ligue 1 il Lione e'
#: ``Lyon``. Scriverli come li scrive il magazzino evita di far fallire un test
#: sui numeri per una questione di targhe.
VERE: dict[str, list[tuple[str, int]]] = {
    "la_liga_2015_16": [("Barcelona", 91), ("Real Madrid", 90), ("Atlético Madrid", 88)],
    "premier_2015_16": [("Leicester City", 81), ("Arsenal", 71), ("Tottenham Hotspur", 70)],
    "serie_a_2015_16": [("Juventus", 91), ("Napoli", 82), ("AS Roma", 80)],
}


def partite_finte() -> pd.DataFrame:
    """Un mini-campionato di quattro squadre, con risultati scelti a mente.

    Sei partite, tutte contro tutte una volta sola. I risultati danno una
    classifica che si controlla a occhio: A vince tutto, D perde tutto.

    Returns:
        Le sei partite.
    """
    incontri = [
        ("A", "B", 2, 0),
        ("A", "C", 3, 1),
        ("A", "D", 1, 0),
        ("B", "C", 1, 1),
        ("B", "D", 2, 1),
        ("C", "D", 0, 0),
    ]
    return pd.DataFrame(
        [
            {
                "match_id": i,
                "casa": casa,
                "ospite": ospite,
                "gol_casa": fatti,
                "gol_ospite": subiti,
                "gruppo": "campionato",
                "giornata": i + 1,
            }
            for i, (casa, ospite, fatti, subiti) in enumerate(incontri)
        ]
    )


def magazzino(nome: str) -> pd.DataFrame:
    """Legge una tabella del magazzino.

    Args:
        nome: Il nome della tabella, senza estensione.

    Returns:
        La tabella.
    """
    return pd.read_parquet(DATA_PROCESSED / f"{nome}.parquet")


# ---------------------------------------------------------------------------
# La verifica contro la realta'
# ---------------------------------------------------------------------------


@senza_magazzino
@pytest.mark.parametrize("competizione", sorted(VERE))
def test_le_classifiche_riproducono_quelle_vere(competizione: str) -> None:
    """I punti calcolati coincidono con quelli ufficiali del 2015/16.

    Se questo test passa, la ricostruzione della classifica e' corretta in un
    senso che nessun test scritto a mano puo' dare: tre campionati interi,
    1.140 partite, contro numeri che non ho scelto io.
    """
    partite = magazzino("matches")
    tavola = classifica.classifica(partite[partite["competizione"] == competizione])
    punti = dict(zip(tavola["squadra"], tavola["punti"], strict=True))

    for posizione, (squadra, attesi) in enumerate(VERE[competizione], start=1):
        assert squadra in punti, f"{squadra} non e' in classifica"
        assert int(punti[squadra]) == attesi, f"{squadra}: {punti[squadra]} invece di {attesi}"
        assert tavola.index[tavola["squadra"] == squadra][0] == posizione - 1


@senza_magazzino
def test_la_ligue_1_e_incompleta_e_lo_dichiara() -> None:
    """Il caso in cui il dato ha un buco, ed e' giusto che si veda.

    Nell'Open Data mancano tre partite della Ligue 1 2015/16, quindi sei
    squadre ne hanno giocate 37 e il PSG risulta a 93 punti invece dei 96
    veri. Il test fissa entrambe le cose: che il numero sia quello che ci si
    aspetta **dato il buco**, e che :func:`incomplete` non lo lasci passare in
    silenzio.
    """
    partite = magazzino("matches")
    ligue1 = partite[partite["competizione"] == "ligue1_2015_16"]
    tavola = classifica.classifica(ligue1)

    parziali = classifica.incomplete(tavola)
    psg = tavola.loc[tavola["squadra"] == "Paris Saint-Germain"].iloc[0]

    assert len(ligue1) == 377, "il buco e' di tre partite su 380"
    assert int(psg["giocate"]) == 37
    assert int(psg["punti"]) == 93, "93 e non i 96 ufficiali: manca una vittoria"
    assert "Paris Saint-Germain" in parziali
    assert len(parziali) == 6


@senza_magazzino
def test_gli_altri_campionati_non_hanno_buchi() -> None:
    # Se `incomplete` segnalasse squadre ovunque non distinguerebbe piu' un
    # magazzino sano da uno rotto.
    partite = magazzino("matches")

    for competizione in VERE:
        tavola = classifica.classifica(partite[partite["competizione"] == competizione])
        assert classifica.incomplete(tavola) == []


@senza_magazzino
def test_la_classifica_esiste_solo_dove_ha_senso() -> None:
    """Il criterio del gruppo concorda con quello della fase del torneo.

    Sono due modi indipendenti di dire la stessa cosa — il gruppo lo assegna
    il progetto in ``config.py``, la fase la scrive StatsBomb — e se
    divergessero vorrebbe dire che una delle due classificazioni ha un errore.
    """
    partite = magazzino("matches")

    for competizione, gruppo in partite.groupby("competizione", observed=True):
        solo_regolare = set(gruppo["fase"].unique()) == {"Regular Season"}
        assert classifica.ha_classifica(gruppo) is solo_regolare, competizione


@senza_magazzino
def test_una_selezione_mista_non_ha_classifica() -> None:
    # Sommare i punti di un campionato e di un tabellone darebbe una tabella
    # dall'aria autorevole e senza significato.
    partite = magazzino("matches")
    mista = partite[partite["competizione"].isin(["la_liga_2015_16", "champions_finali"])]

    assert classifica.ha_classifica(mista) is False


# ---------------------------------------------------------------------------
# Invarianti, veri su qualunque insieme di partite
# ---------------------------------------------------------------------------


def test_i_punti_distribuiti_tornano() -> None:
    """Ogni partita distribuisce tre punti, due se finisce pari.

    E' l'invariante che coglie l'errore piu' probabile in un calcolo di
    classifica: contare due volte una partita, o perderne una.
    """
    partite = partite_finte()
    tavola = classifica.classifica(partite)

    pareggi = int((partite["gol_casa"] == partite["gol_ospite"]).sum())
    attesi = 3 * len(partite) - pareggi

    assert int(tavola["punti"].sum()) == attesi


def test_i_gol_fatti_da_tutti_sono_i_gol_subiti_da_tutti() -> None:
    tavola = classifica.classifica(partite_finte())

    assert int(tavola["gol_fatti"].sum()) == int(tavola["gol_subiti"].sum())
    assert int(tavola["differenza"].sum()) == 0


def test_ogni_partita_produce_due_righe() -> None:
    partite = partite_finte()

    righe = classifica.a_righe(partite)

    assert len(righe) == 2 * len(partite)
    assert int(righe["in_casa"].sum()) == len(partite)


def test_la_classifica_del_mini_campionato_e_quella_attesa() -> None:
    # A vince tre partite, B ne vince una e ne pareggia una, C pareggia due
    # volte, D pareggia una volta.
    tavola = classifica.classifica(partite_finte())

    assert list(tavola["squadra"]) == ["A", "B", "C", "D"]
    assert list(tavola["punti"]) == [9, 4, 2, 1]
    assert list(tavola["giocate"]) == [3, 3, 3, 3]


@senza_magazzino
def test_gli_xg_creati_sono_anche_quelli_concessi() -> None:
    """Lo stesso tiro, contato una volta da chi tira e una da chi subisce.

    I due totali devono coincidere: se non lo facessero vorrebbe dire che un
    tiro ha un tiratore ma non un avversario, cioe' che le due colonne non
    descrivono la stessa partita.
    """
    tiri = magazzino("shots")
    liga = tiri[tiri["competizione"] == "la_liga_2015_16"]

    per_squadra = classifica.xg_per_squadra(liga)

    assert per_squadra["xg_fatti"].sum() == pytest.approx(per_squadra["xg_subiti"].sum())
    assert per_squadra["tiri_fatti"].sum() == per_squadra["tiri_subiti"].sum()


@senza_magazzino
def test_la_tabella_unisce_senza_perdere_squadre() -> None:
    partite = magazzino("matches")
    tiri = magazzino("shots")
    liga = partite[partite["competizione"] == "la_liga_2015_16"]

    unita = classifica.tabella(liga, tiri[tiri["competizione"] == "la_liga_2015_16"])

    assert len(unita) == 20
    assert not unita[["xg_fatti", "xg_subiti"]].isna().to_numpy().any()
    assert unita["scarto_xg"].to_numpy() == pytest.approx(
        (unita["gol_fatti"] - unita["xg_fatti"]).to_numpy()
    )


def test_una_selezione_vuota_non_solleva() -> None:
    vuote = partite_finte().head(0)

    assert classifica.classifica(vuote).empty
    assert classifica.tabella(vuote, vuote).empty
    assert classifica.ha_classifica(vuote) is False
    assert classifica.incomplete(classifica.classifica(vuote)) == []


@senza_magazzino
@pytest.mark.parametrize("competizione", ["la_liga_2015_16", "champions_finali"])
def test_gli_xg_delle_partite_coincidono_con_quelli_dei_tiri(competizione: str) -> None:
    """Due fonti per lo stesso numero, e devono dire la stessa cosa.

    ``matches`` porta gli xG di squadra per partita, ``shots`` i singoli tiri:
    la scheda usa i primi per la curva e i secondi per il totale, e se
    divergessero mostrerebbe due valori diversi della stessa quantita' a due
    centimetri di distanza.

    Sulle finali il confronto va fatto **senza** i rigori delle serie finali:
    con quelli i tiri arrivano a 73,5 contro i 52,4 delle partite, ed e'
    ``matches`` ad avere ragione.
    """
    partite = magazzino("matches")
    tiri = magazzino("shots")
    sue_partite = partite[partite["competizione"] == competizione]
    suoi_tiri = tiri[tiri["competizione"] == competizione]

    da_partite = float(sue_partite["xg_casa"].sum() + sue_partite["xg_ospite"].sum())
    da_tiri = float(classifica.xg_per_squadra(suoi_tiri)["xg_fatti"].sum())

    assert da_tiri == pytest.approx(da_partite, rel=1e-4)


@senza_magazzino
def test_la_scheda_legge_dalla_classifica_e_non_ricalcola() -> None:
    """I numeri della scheda sono quelli della riga, non una seconda versione.

    E' la ragione per cui :func:`classifica.scheda` prende la tabella invece
    delle partite: due funzioni che calcolano lo stesso numero per strade
    diverse prima o poi ne danno due.
    """
    partite = magazzino("matches")
    tiri = magazzino("shots")
    liga = partite[partite["competizione"] == "la_liga_2015_16"]
    tavola = classifica.tabella(liga, tiri[tiri["competizione"] == "la_liga_2015_16"])

    numeri = classifica.scheda(tavola, "Barcelona")
    riga = tavola.iloc[0]

    assert numeri["posizione"] == 1
    assert numeri["punti"] == float(riga["punti"])
    assert numeri["gol_fatti"] == float(riga["gol_fatti"])
    assert numeri["xg_fatti"] == pytest.approx(float(riga["xg_fatti"]))
    assert numeri["xg_per_tiro"] == pytest.approx(
        float(riga["xg_fatti"]) / float(riga["tiri_fatti"])
    )
    assert classifica.scheda(tavola, "Squadra Inventata") == {}


@senza_magazzino
def test_la_curva_finisce_sui_totali_di_stagione() -> None:
    """L'ultimo punto della curva cumulata e' il totale della classifica.

    Se il cumulato non arrivasse esattamente li', vorrebbe dire che qualche
    partita e' stata persa per strada o contata due volte — e il grafico
    sarebbe una versione diversa degli stessi dati.
    """
    partite = magazzino("matches")
    tiri = magazzino("shots")
    liga = partite[partite["competizione"] == "la_liga_2015_16"]
    tavola = classifica.tabella(liga, tiri[tiri["competizione"] == "la_liga_2015_16"])

    curva = classifica.andamento_squadra(liga, "Barcelona")
    riga = tavola[tavola["squadra"] == "Barcelona"].iloc[0]

    assert len(curva) == int(riga["giocate"])
    assert float(curva["gol"].iloc[-1]) == float(riga["gol_fatti"])
    assert float(curva["xg"].iloc[-1]) == pytest.approx(float(riga["xg_fatti"]), rel=1e-4)
    assert curva["data"].is_monotonic_increasing


def test_la_curva_di_una_squadra_assente_e_vuota() -> None:
    assert classifica.andamento_squadra(partite_finte(), "Nessuno").empty
