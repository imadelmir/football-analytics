"""Il confronto fra i quattro campionati (M6-T8).

**Solo i quattro campionati 2015/16, e non e' una semplificazione.** Sono
l'unico gruppo del magazzino davvero confrontabile: stessa stagione, trentotto
giornate, stessa generazione di dati StatsBomb, e soprattutto **nessuno dei
quattro ha i dati 360**.

Il backlog chiedeva di avvertire che «la Serie A usa il modello base», come se
fosse l'eccezione. Misurando la copertura nel magazzino risulta il contrario:
la quota di partite con freeze frame e' **zero in tutti e quattro** — Liga,
Premier, Serie A, Ligue 1 — mentre e' del 100 % nei Mondiali 2022 e negli
Europei, e del 2 % in Coppa d'Africa. L'avvertenza serve quindi verso i tornei,
non fra i campionati, e la pagina la scrive cosi'.

**Resta un buco dichiarato:** la Ligue 1 ha 377 partite invece di 380, perche'
all'Open Data ne mancano tre. Ogni numero di questo modulo e' normalizzato per
partita o per tiro proprio per questo — un totale grezzo metterebbe la Ligue 1
in svantaggio per un motivo che non ha niente a che vedere con il calcio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd

from football_analytics import config

if TYPE_CHECKING:
    import numpy.typing as npt

#: Le colonne del riassunto: etichetta, chiave, decimali.
#:
#: **Tutte per partita o per tiro.** Con la Ligue 1 a 377 partite un totale
#: grezzo direbbe che ci si segna meno, quando semplicemente si e' giocato meno.
VOCI: Final[tuple[tuple[str, str, int], ...]] = (
    ("Gol per partita", "gol_per_partita", 2),
    ("xG per partita", "xg_per_partita", 2),
    ("Tiri per partita", "tiri_per_partita", 1),
    ("xG per tiro", "xg_per_tiro", 3),
    ("Conversione", "conversione", 3),
)

#: Quante fasce nella curva di densita' dell'xG per tiro.
#:
#: Cinquanta su un intervallo 0-1 danno celle da 0,02: abbastanza fini da
#: mostrare la forma, abbastanza larghe da non trasformare il rumore in picchi.
FASCE: Final[int] = 50

#: Ampiezza della sfocatura della curva, in fasce.
SFOCATURA: Final[int] = 2


def campionati() -> list[str]:
    """Le chiavi dei quattro campionati, dalla configurazione.

    Returns:
        Le chiavi, nell'ordine in cui la configurazione le elenca.
    """
    return [voce.chiave for voce in config.CAMPIONATI]


def riassunto(partite: pd.DataFrame, tiri: pd.DataFrame) -> pd.DataFrame:
    """Una riga per campionato con i numeri normalizzati.

    **I tiri sono quelli su azione**: i rigori dei tiebreak non esistono nei
    campionati, ma passare comunque da
    :func:`~football_analytics.panoramica.tiri_di_gioco` tiene la definizione
    identica a quella di tutte le altre viste. Due definizioni di «tiro» nella
    stessa app sono due numeri che non torneranno mai.

    Args:
        partite: Le partite di tutto il magazzino.
        tiri: I tiri di tutto il magazzino, gia' ripuliti dai tiebreak.

    Returns:
        Una riga per campionato con le colonne di :data:`VOCI`, piu'
        ``partite``. Vuota se nel magazzino non c'e' nessun campionato.
    """
    righe = []
    for chiave in campionati():
        sue_partite = partite[partite["competizione"] == chiave]
        suoi_tiri = tiri[tiri["competizione"] == chiave]
        if sue_partite.empty or suoi_tiri.empty:
            continue
        quante = float(len(sue_partite))
        quanti_tiri = float(len(suoi_tiri))
        gol = float(sue_partite["gol_casa"].sum() + sue_partite["gol_ospite"].sum())
        xg = float(suoi_tiri["xg_statsbomb"].sum())
        righe.append(
            {
                "competizione": chiave,
                "partite": quante,
                "gol_per_partita": gol / quante,
                "xg_per_partita": xg / quante,
                "tiri_per_partita": quanti_tiri / quante,
                "xg_per_tiro": xg / quanti_tiri,
                # La conversione conta i gol **da tiro**, coerente con il
                # denominatore: gli autogol stanno nel risultato ma non nascono
                # da un tiro di chi li subisce.
                "conversione": float(suoi_tiri["gol"].sum()) / quanti_tiri,
            }
        )
    return pd.DataFrame(righe)


def _sfoca(valori: npt.NDArray[np.float64], raggio: int = SFOCATURA) -> npt.NDArray[np.float64]:
    """Smussa una curva con una media pesata sui vicini.

    Args:
        valori: I conteggi per fascia.
        raggio: Quante fasce per lato entrano nella media.

    Returns:
        La curva smussata, della stessa lunghezza.
    """
    distanze = np.arange(-raggio, raggio + 1, dtype=np.float64)
    pesi = np.exp(-((distanze / raggio) ** 2) * 2.0)
    pesi /= pesi.sum()
    return np.convolve(valori, pesi, mode="same")


def distribuzione(tiri: pd.DataFrame, limite: float = 1.0) -> pd.DataFrame:
    """La densita' dell'xG per tiro, una colonna per campionato.

    **Densita' e non conteggi.** I quattro campionati hanno un numero diverso
    di tiri — dalla Ligue 1 con 8.813 alla Serie A con 9.998 — e sovrapporre i
    conteggi grezzi mostrerebbe chi tira di piu', non da dove tira. Ogni curva
    e' normalizzata a somma uno, quindi le quattro sono confrontabili.

    Args:
        tiri: I tiri di tutto il magazzino, gia' ripuliti dai tiebreak.
        limite: L'xG massimo da rappresentare. Oltre 1,0 non esiste niente.

    Returns:
        Una riga per fascia con ``xg`` al centro della fascia e una colonna per
        campionato. Vuota se non ci sono tiri.
    """
    bordi = np.linspace(0.0, limite, FASCE + 1)
    centri = (bordi[:-1] + bordi[1:]) / 2
    curve: dict[str, npt.NDArray[np.float64]] = {"xg": centri}

    for chiave in campionati():
        suoi = tiri[tiri["competizione"] == chiave]
        if suoi.empty:
            continue
        conteggi, _ = np.histogram(suoi["xg_statsbomb"].to_numpy(), bins=bordi)
        smussati = _sfoca(conteggi.astype(np.float64))
        totale = float(smussati.sum())
        curve[chiave] = smussati / totale if totale else smussati

    if len(curve) == 1:
        return pd.DataFrame(columns=["xg"])
    return pd.DataFrame(curve)


def scarti(riassunto_leghe: pd.DataFrame) -> dict[str, float]:
    """Quanto i campionati differiscono davvero, metrica per metrica.

    Serve alla frase calcolata della pagina: dire «i campionati si somigliano»
    o «si distinguono» deve venire dai numeri, non da un'impressione.

    Args:
        riassunto_leghe: Il risultato di :func:`riassunto`.

    Returns:
        Il rapporto fra massimo e minimo per ogni metrica. Vuoto se la tabella
        ha meno di due campionati.
    """
    minimo_confronto = 2
    if len(riassunto_leghe) < minimo_confronto:
        return {}
    return {
        colonna: float(riassunto_leghe[colonna].max() / riassunto_leghe[colonna].min())
        for _, colonna, _ in VOCI
        if riassunto_leghe[colonna].min() > 0
    }
