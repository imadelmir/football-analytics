"""Le frasi calcolate (M6-T12).

Il criterio della task e' che **cambiando competizione la frase cambi da sola,
con i numeri giusti**, e questi test lo verificano nell'unico modo che conta:
generando le frasi su due selezioni diverse e controllando che i numeri dentro
siano quelli di quella selezione, non di un'altra.

Il test piu' severo del file e' :func:`test_nessun_numero_e_scritto_a_mano`:
prende ogni numero che compare nel testo e lo ricalcola dai dati. Una frase con
dentro una cifra copiata passerebbe qualunque altro controllo.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from football_analytics import insights, panoramica
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "shots.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)

#: Due competizioni con numeri diversi, per il confronto.
PRIMA = "serie_a_2015_16"
SECONDA = "premier_2015_16"


def magazzino() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Partite e tiri del magazzino.

    Returns:
        Le due tabelle.
    """
    return (
        pd.read_parquet(DATA_PROCESSED / "matches.parquet"),
        pd.read_parquet(DATA_PROCESSED / "shots.parquet"),
    )


def di(chiave: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """La selezione di una competizione.

    Args:
        chiave: La chiave della competizione.

    Returns:
        I tiri e le partite di quella competizione.
    """
    partite, tiri = magazzino()
    return tiri[tiri["competizione"] == chiave], partite[partite["competizione"] == chiave]


def test_una_selezione_vuota_non_produce_frasi() -> None:
    """Meglio tacere che riempire lo spazio con una conclusione senza dati."""
    vuoti = pd.DataFrame(
        columns=["competizione", "xg_statsbomb", "gol", "x", "minuto", "rigori_finali"]
    )
    partite = pd.DataFrame(columns=["gol_casa", "gol_ospite"])

    assert insights.della_selezione(vuoti, partite, "Niente") == []
    assert insights.sintesi({"partite": 0.0}, 0.0, "Niente") == ""
    assert insights.zona_migliore(pd.DataFrame()) == ""
    assert insights.quarto_migliore(pd.DataFrame()) == ""
    assert insights.estremi_di_classifica(pd.DataFrame()) == ""


def test_la_zona_tace_quando_i_tiri_non_bastano() -> None:
    """Con pochi tiri la zona piu' redditizia e' quella dove e' entrata una palla.

    La soglia esiste perche' una frase fragile detta con tono sicuro e' peggio
    di nessuna frase.
    """
    poche = pd.DataFrame(
        [
            {"zona": "Area piccola", "tiri": 3, "gol": 2, "xg_medio": 0.6, "xg": 1.8},
            {"zona": "Fuori area", "tiri": 5, "gol": 0, "xg_medio": 0.02, "xg": 0.1},
        ]
    )

    assert insights.zona_migliore(poche) == ""


@senza_magazzino
def test_la_frase_cambia_cambiando_competizione() -> None:
    """Il criterio della task, verificato generando due volte.

    Non basta che il testo sia diverso: devono essere diversi **i numeri**. Due
    frasi identiche nella forma e uguali nelle cifre vorrebbero dire che il
    filtro non arriva fino al calcolo.
    """
    prime = insights.della_selezione(*di(PRIMA), "Serie A")
    seconde = insights.della_selezione(*di(SECONDA), "Premier League")

    assert prime and seconde
    assert prime != seconde
    assert numeri_nel_testo(" ".join(prime)) != numeri_nel_testo(" ".join(seconde))


def numeri_nel_testo(frase: str) -> list[str]:
    """Estrae i numeri scritti in una frase, all'italiana.

    Args:
        frase: Il testo.

    Returns:
        I numeri trovati, come stringhe.
    """
    return re.findall(r"\d+(?:\.\d{3})*(?:,\d+)?", frase)


@senza_magazzino
def test_nessun_numero_e_scritto_a_mano() -> None:
    """Ogni cifra della sintesi si ritrova ricalcolandola dai dati.

    E' il controllo che nessun altro test puo' sostituire: una frase con dentro
    un numero copiato — «2,58 gol a partita» rimasto li' da quando si guardava
    la Serie A — supererebbe qualunque verifica sulla forma.
    """
    tiri, partite = di(SECONDA)
    numeri = panoramica.kpi(tiri, partite)

    frase = insights.sintesi(numeri, panoramica.realizzazione(tiri), "Premier League")
    presenti = numeri_nel_testo(frase)

    for atteso in (
        f"{numeri['partite']:,.0f}".replace(",", "."),
        f"{numeri['gol']:,.0f}".replace(",", "."),
        f"{numeri['gol_per_partita']:.2f}".replace(".", ","),
        f"{numeri['tiri_per_partita']:.1f}".replace(".", ","),
    ):
        assert atteso in presenti, f"{atteso} non compare in: {frase}"


@senza_magazzino
def test_il_titolo_e_un_etichetta_e_non_un_soggetto() -> None:
    """Con un nome plurale la frase deve restare grammaticale.

    «Le finali di Champions ha segnato» e' l'errore che si ottiene mettendo il
    nome della competizione come soggetto: il genere e il numero cambiano da
    una competizione all'altra e la concordanza non si puo' indovinare.
    """
    tiri, partite = di("champions_finali")
    numeri = panoramica.kpi(tiri, partite)

    frase = insights.sintesi(numeri, panoramica.realizzazione(tiri), "Finali di Champions")

    assert frase.startswith("Finali di Champions — in ")
    assert " ha segnato" not in frase
    assert " hanno segnato" not in frase


@senza_magazzino
def test_senza_titolo_la_frase_comincia_con_la_maiuscola() -> None:
    """Il titolo e' facoltativo, e senza non deve restare una frase monca."""
    tiri, partite = di(PRIMA)
    numeri = panoramica.kpi(tiri, partite)

    frase = insights.sintesi(numeri, panoramica.realizzazione(tiri))

    assert frase.startswith("In ")
    assert "—" not in frase.split(".")[0]


@senza_magazzino
def test_la_frase_dichiara_che_e_una_misura_e_non_una_spiegazione() -> None:
    """Dove lo scarto e' notevole, la frase deve fermarsi prima di interpretarlo.

    Chiamare «bravura» uno scarto positivo su una stagione sola e' la
    scorciatoia che rende una dashboard inaffidabile: si legge bene e non si
    puo' sostenere.
    """
    tiri, partite = di(PRIMA)
    numeri = panoramica.kpi(tiri, partite)
    quota = panoramica.realizzazione(tiri)
    assert abs(quota - 1.0) >= insights.SCARTO_NOTEVOLE, "serve una selezione con scarto"

    frase = insights.sintesi(numeri, quota, "Serie A")

    assert "misura, non una spiegazione" in frase
    for parola in ("fortuna", "bravura", "sfortuna", "cinismo"):
        assert parola not in frase.lower()


@senza_magazzino
def test_la_zona_non_produce_contrazioni_sbagliate() -> None:
    """I nomi delle zone non hanno preposizioni davanti, e non e' pigrizia.

    Con «dall'» la frase diventerebbe «dall'fuori area» il giorno in cui la
    zona piu' redditizia non fosse un'area — un difetto che con i dati veri non
    si presenta mai, e che quindi non si scoprirebbe guardando.
    """
    tiri, _ = di(PRIMA)

    frase = insights.zona_migliore(panoramica.per_zona(tiri))

    assert frase
    for sbagliata in ("dall'fuori", "dall'area di", "da area", "dalla fuori"):
        assert sbagliata not in frase


@senza_magazzino
def test_gli_estremi_di_classifica_nominano_due_squadre_diverse() -> None:
    """Prima e ultima per scarto: se coincidessero, la frase non direbbe niente."""
    from football_analytics import classifica  # noqa: PLC0415

    partite, tiri = magazzino()
    tabella = classifica.tabella(
        partite[partite["competizione"] == PRIMA],
        tiri[tiri["competizione"] == PRIMA],
    )

    frase = insights.estremi_di_classifica(tabella)

    ordinata = tabella.sort_values("scarto_xg", ascending=False)
    prima = str(ordinata.iloc[0]["squadra"])
    ultima = str(ordinata.iloc[-1]["squadra"])
    assert prima != ultima
    assert prima in frase
    assert ultima in frase
