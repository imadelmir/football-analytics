"""Le frasi calcolate dai numeri della selezione (M6-T12).

**Nessun testo statico che possa diventare falso cambiando filtro**, ed e' il
criterio della task: cambiando competizione la frase deve cambiare da sola, con
i numeri giusti. Una frase scritta a mano — «in Serie A si segna poco» —
resterebbe li' a dire il falso il giorno in cui qualcuno sceglie la Premier, e
nessuno se ne accorgerebbe guardando la pagina.

**Sta in `src/` e non nelle pagine**, dove il calcolo viveva finora. Le pagine
disegnano; il testo di una conclusione nasce da un confronto fra numeri, e un
confronto e' logica. Cosi' le frasi si verificano con pytest senza aprire un
browser, ed e' l'unico modo in cui il criterio della task si puo' davvero
controllare.

**Le frasi descrivono, non interpretano.** «Ha segnato piu' di quanto le
occasioni promettessero» e' una misura; «e' stata fortunata» sarebbe una
spiegazione, e su una stagione sola non ci sono i dati per darla. Dove la
distinzione conta — la realizzazione sopra il cento per cento — la frase lo
dichiara invece di lasciarlo intendere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from football_analytics import panoramica

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

#: Quanto la realizzazione deve scostarsi dal pareggio perche' valga dirlo.
#:
#: Sotto il tre per cento e' rumore: su una stagione di trecentottanta partite
#: la differenza fra segnare il 99 % o il 101 % dell'xG non distingue niente, e
#: chiamarla «ha segnato piu' del previsto» sarebbe leggere una fluttuazione.
SCARTO_NOTEVOLE: Final[float] = 0.03

#: Sotto quanti tiri una selezione non merita una conclusione.
#:
#: Con dieci tiri la zona piu' redditizia e' quella dove per caso e' entrata
#: una palla. La frase tace invece di dire una cosa fragile con tono sicuro.
TIRI_MINIMI: Final[int] = 50


def _percentuale(valore: float, decimali: int = 0) -> str:
    """Formatta una quota come percentuale all'italiana.

    Args:
        valore: La quota, dove 1.0 e' il cento per cento.
        decimali: Quante cifre dopo la virgola.

    Returns:
        La percentuale con la virgola decimale.
    """
    return f"{valore * 100:.{decimali}f} %".replace(".", ",")


def _numero(valore: float, decimali: int = 0) -> str:
    """Formatta un numero all'italiana.

    Args:
        valore: Il numero.
        decimali: Quante cifre dopo la virgola.

    Returns:
        Il numero con il punto per le migliaia e la virgola decimale.
    """
    return f"{valore:,.{decimali}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def sintesi(numeri: Mapping[str, float], quota: float, titolo: str = "") -> str:
    """La frase che riassume una selezione in una riga.

    **Il confronto fra gol e xG e' il cuore**, ed e' anche il punto in cui una
    dashboard mente piu' facilmente: chiamare «bravura» uno scarto positivo non
    e' sostenibile su questi numeri. La frase riporta la misura e si ferma li'.

    **Il nome della selezione e' un'etichetta, non un soggetto.** Scriverlo
    dentro la frase — «la Serie A ha segnato», «le finali di Champions ha
    segnato» — obbligherebbe a conoscere il genere e il numero di ogni
    competizione per far tornare la concordanza, e il primo nome plurale
    aggiunto al magazzino produrrebbe una frase sgrammaticata. Messo davanti
    con un trattino, funziona per qualunque nome.

    Args:
        numeri: Il risultato di :func:`~football_analytics.panoramica.kpi`.
        quota: Il risultato di
            :func:`~football_analytics.panoramica.realizzazione`.
        titolo: Come si chiama la selezione. Vuoto lo omette.

    Returns:
        La frase, vuota se la selezione non ha partite.
    """
    if not numeri.get("partite"):
        return ""

    testa = f"{titolo} — " if titolo else ""
    corpo = (
        f"in {_numero(numeri['partite'])} partite si sono visti "
        f"{_numero(numeri['gol'])} gol, {_numero(numeri['gol_per_partita'], 2)} a "
        f"partita, con {_numero(numeri['tiri_per_partita'], 1)} tiri a incontro."
    )

    if abs(quota - 1.0) < SCARTO_NOTEVOLE:
        return (
            f"{testa}{corpo.capitalize() if not testa else corpo} I gol sono in linea "
            f"con le occasioni create: {_percentuale(quota)} dell'xG, dentro il margine "
            f"di rumore."
        )
    verso = "più" if numeri["gol_meno_xg"] > 0 else "meno"
    return (
        f"{testa}{corpo.capitalize() if not testa else corpo} Sono "
        f"{_numero(abs(numeri['gol_meno_xg']), 1)} gol in {verso} di quanto le occasioni "
        f"promettessero — {_percentuale(quota)} dell'xG. È una misura, non una "
        f"spiegazione: per distinguere la mira dal caso servirebbero più stagioni."
    )


def zona_migliore(zone: pd.DataFrame) -> str:
    """Da dove conviene tirare, secondo i dati della selezione.

    Args:
        zone: Il risultato di
            :func:`~football_analytics.panoramica.per_zona`.

    Returns:
        La frase, vuota se non ci sono abbastanza tiri per dirlo.
    """
    if zone.empty:
        return ""
    valide = zone[zone["tiri"] >= TIRI_MINIMI]
    if valide.empty:
        return ""

    ordinate = valide.sort_values("xg_medio", ascending=False)
    prima = ordinate.iloc[0]
    ultima = ordinate.iloc[-1]
    if prima["zona"] == ultima["zona"] or not float(ultima["xg_medio"]):
        return ""

    # I nomi delle zone stanno senza preposizione davanti, e non e' pigrizia:
    # con «dall'» la frase diventerebbe «dall'fuori area» il giorno in cui la
    # zona piu' redditizia non fosse l'area. Un difetto che non si vede
    # scrivendo, perche' con i dati veri quel caso non si presenta mai.
    rapporto = float(prima["xg_medio"]) / float(ultima["xg_medio"])
    return (
        f"Zona più redditizia: {str(prima['zona']).lower()}, "
        f"{_numero(float(prima['xg_medio']), 3)} xG per tiro — {_numero(rapporto, 1)} "
        f"volte quanto vale un tiro dalla zona meno redditizia "
        f"({str(ultima['zona']).lower()}, {_numero(float(ultima['xg_medio']), 3)})."
    )


def quarto_migliore(quarti: pd.DataFrame) -> str:
    """Il quarto d'ora in cui la selezione ha creato di più.

    Args:
        quarti: Il risultato di
            :func:`~football_analytics.panoramica.per_quarto_dora`.

    Returns:
        La frase, vuota se la tabella e' vuota.
    """
    if quarti.empty:
        return ""
    migliore = quarti.sort_values("xg", ascending=False).iloc[0]
    quota = float(migliore["xg"]) / float(quarti["xg"].sum()) if quarti["xg"].sum() else 0.0
    return (
        f"Il quarto d'ora più pericoloso è il {migliore['blocco']}, con "
        f"{_numero(float(migliore['xg']), 0)} xG: il {_percentuale(quota)} di tutto "
        f"quello creato."
    )


def estremi_di_classifica(tabella: pd.DataFrame) -> str:
    """Chi ha segnato molto più e molto meno di quanto creava.

    Args:
        tabella: Il risultato di
            :func:`~football_analytics.classifica.tabella`.

    Returns:
        La frase, vuota se la classifica non ha senso per la selezione.
    """
    if tabella.empty or "scarto_xg" not in tabella.columns:
        return ""
    ordinata = tabella.sort_values("scarto_xg", ascending=False)
    sopra = ordinata.iloc[0]
    sotto = ordinata.iloc[-1]
    return (
        f"{sopra['squadra']} ha segnato {_numero(float(sopra['scarto_xg']), 1)} gol più "
        f"delle proprie occasioni, {sotto['squadra']} "
        f"{_numero(abs(float(sotto['scarto_xg'])), 1)} in meno: è la distanza fra il "
        f"finalizzare bene e lo sprecare, misurata sulla stessa stagione."
    )


def della_selezione(
    tiri: pd.DataFrame,
    partite: pd.DataFrame,
    titolo: str = "",
) -> list[str]:
    """Tutte le frasi che una selezione permette di dire, nell'ordine di lettura.

    **Una frase che non si puo' sostenere non viene scritta.** Le funzioni
    sopra restituiscono stringhe vuote quando i dati non bastano — meno di
    cinquanta tiri in una zona, nessuna partita — e qui vengono scartate. Una
    dashboard che tace su una selezione povera e' piu' credibile di una che
    riempie lo spazio.

    Args:
        tiri: I tiri della selezione, rigori dei tiebreak compresi.
        partite: Le partite della stessa selezione.
        titolo: Come si chiama la selezione. Vuoto lo omette.

    Returns:
        Le frasi non vuote, in ordine.
    """
    numeri = panoramica.kpi(tiri, partite)
    frasi = (
        sintesi(numeri, panoramica.realizzazione(tiri), titolo),
        zona_migliore(panoramica.per_zona(tiri)),
        quarto_migliore(panoramica.per_quarto_dora(tiri)),
    )
    return [frase for frase in frasi if frase]
