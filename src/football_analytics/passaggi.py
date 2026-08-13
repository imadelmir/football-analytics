"""La rete dei passaggi di una squadra (M6-T4).

**I nodi non sono una formazione, sono le posizioni medie.** Un giocatore che
gioca mezz'ala e poi terzino finisce da qualche parte in mezzo, e nessuna delle
due posizioni e' la sua. E' il limite di ogni rete dei passaggi costruita su
una stagione intera, e va detto: la vista racconta **dove si e' giocato**, non
un modulo.

**Gli archi sono senza verso.** Nei dati un passaggio ha un passatore e un
ricevitore, quindi Verratti-Motta e Motta-Verratti sono due righe diverse:
sommarle dimezza il numero di linee e non toglie niente, perche' su un campo
disegnato la freccia non si vedrebbe comunque. Chi volesse la direzione
guarderebbe un'altra vista.

**Si disegnano solo i legami piu' battuti.** Fra gli undici piu' impiegati del
PSG 2015/16 ci sono 108 archi con verso, cioe' 54 senza: disegnarli tutti da'
una matassa in cui ogni coppia e' collegata a ogni altra e non si legge niente.
Tenendo i primi venti restano le catene di gioco vere.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

#: Quanti giocatori mostrare nella rete.
#:
#: Undici come una formazione, e non e' un caso: sono i piu' impiegati, quindi
#: nella maggior parte dei casi sono davvero gli undici che hanno giocato
#: insieme piu' spesso.
TITOLARI: Final[int] = 11

#: Quanti legami disegnare, dal piu' battuto in giu'.
ARCHI: Final[int] = 20


def titolari(giocatori: pd.DataFrame, quanti: int = TITOLARI) -> pd.DataFrame:
    """I giocatori piu' impiegati, con la loro posizione media.

    Args:
        giocatori: Le statistiche dei giocatori di **una sola** squadra.
        quanti: Quanti tenerne.

    Returns:
        Le righe scelte, con ``giocatore_id``, ``giocatore_breve``, ``ruolo``,
        ``minuti`` e la posizione media. Vuoto se mancano le posizioni.
    """
    colonne = ["giocatore_id", "giocatore_breve", "ruolo", "minuti", "x_media", "y_media"]
    if giocatori.empty:
        return pd.DataFrame(columns=colonne)
    con_posizione = giocatori.dropna(subset=["x_media", "y_media"])
    if con_posizione.empty:
        return pd.DataFrame(columns=colonne)
    return con_posizione.nlargest(quanti, "minuti")[colonne].reset_index(drop=True)


def rete(passaggi: pd.DataFrame, scelti: pd.DataFrame, quanti: int = ARCHI) -> pd.DataFrame:
    """I legami piu' battuti fra i giocatori scelti.

    Args:
        passaggi: I passaggi di **una sola** squadra, con ``passatore_id``,
            ``ricevitore_id`` e ``passaggi``.
        scelti: Il risultato di :func:`titolari`.
        quanti: Quanti legami tenere.

    Returns:
        Una riga per legame, con le coordinate dei due estremi, i nomi e il
        numero di passaggi complessivo nelle due direzioni.
    """
    colonne = ["x0", "y0", "x1", "y1", "da", "a", "passaggi"]
    if passaggi.empty or scelti.empty:
        return pd.DataFrame(columns=colonne)

    dentro = passaggi[
        passaggi["passatore_id"].isin(scelti["giocatore_id"])
        & passaggi["ricevitore_id"].isin(scelti["giocatore_id"])
        & (passaggi["passatore_id"] != passaggi["ricevitore_id"])
    ]
    if dentro.empty:
        return pd.DataFrame(columns=colonne)

    # Ordinare la coppia rende Verratti-Motta e Motta-Verratti la stessa
    # chiave, che e' l'unico modo di sommarle senza contarle due volte.
    coppie = pd.DataFrame(
        {
            "primo": dentro[["passatore_id", "ricevitore_id"]].min(axis=1),
            "secondo": dentro[["passatore_id", "ricevitore_id"]].max(axis=1),
            "passaggi": dentro["passaggi"],
        }
    )
    sommati = (
        coppie.groupby(["primo", "secondo"], observed=True)["passaggi"]
        .sum()
        .reset_index()
        .nlargest(quanti, "passaggi")
    )

    posizioni = scelti.set_index("giocatore_id")
    return pd.DataFrame(
        {
            "x0": posizioni.loc[sommati["primo"], "x_media"].to_numpy(),
            "y0": posizioni.loc[sommati["primo"], "y_media"].to_numpy(),
            "x1": posizioni.loc[sommati["secondo"], "x_media"].to_numpy(),
            "y1": posizioni.loc[sommati["secondo"], "y_media"].to_numpy(),
            "da": posizioni.loc[sommati["primo"], "giocatore_breve"].to_numpy(),
            "a": posizioni.loc[sommati["secondo"], "giocatore_breve"].to_numpy(),
            "passaggi": sommati["passaggi"].to_numpy(),
        }
    )


def coinvolgimento(collegamenti: pd.DataFrame, scelti: pd.DataFrame) -> pd.Series:
    """Quanti passaggi disegnati toccano ciascun giocatore.

    Serve a dimensionare i pallini: un regista sta al centro di molte linee e
    merita di vedersi, un terzino che scambia solo col compagno di fascia no.

    Args:
        collegamenti: Il risultato di :func:`rete`.
        scelti: Il risultato di :func:`titolari`.

    Returns:
        Una serie indicizzata sul nome breve, con zero per chi non compare in
        nessun legame disegnato.
    """
    conteggi = pd.Series(0.0, index=scelti["giocatore_breve"])
    if collegamenti.empty:
        return conteggi
    for estremo in ("da", "a"):
        somme = collegamenti.groupby(estremo, observed=True)["passaggi"].sum()
        conteggi = conteggi.add(somme.reindex(conteggi.index).fillna(0.0), fill_value=0.0)
    return conteggi
