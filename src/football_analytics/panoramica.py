"""Le aggregazioni della vista Panoramica (M6-T3).

**Qui non si disegna niente e non si importa Streamlit.** Sono funzioni che
prendono tabelle e restituiscono tabelle, quindi si verificano senza aprire un
browser — ed e' l'unico modo per rispettare il criterio del backlog, che chiede
numeri coincidenti con quelli calcolati a mano su dieci partite.

Due scelte attraversano tutto il modulo.

**I gol si contano dalla tabella delle partite, non da quella dei tiri.** Il
risultato di una partita comprende gli autogol, che nei tiri non compaiono
perche' vengono attribuiti a chi tira e non alla squadra che segna. Sommare i
gol dai tiri darebbe un totale piu' basso del risultato reale, e nessuno se ne
accorgerebbe guardando la dashboard.

**Un tiro ha una squadra, una partita ne ha due.** Le aggregazioni per squadra
partono dai tiri; quelle per partita dalla tabella delle partite. Mescolare le
due strade e' il modo piu' rapido di contare due volte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pandas as pd

from football_analytics.config import SOGLIA_MINUTI

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Quanti nomi mostrare nelle classifiche.
QUANTI: Final[int] = 10


def tiri_di_gioco(tiri: pd.DataFrame) -> pd.DataFrame:
    """Toglie i tiri della serie di rigori, che non sono gol della partita.

    **Un rigore della serie finale ha ``gol = True`` ma non entra nel
    risultato.** Su dieci partite scelte a caso ne sono comparsi diciannove, e
    contarli gonfiava i gol da 33 a 48 senza che niente lo segnalasse.

    Con l'esclusione l'identita' torna, e vale su tutto il magazzino:

        gol dai tiri + autogol = gol del risultato

    E' la stessa regola che il modello applica in
    :func:`~football_analytics.features.tiri_modellabili`, per lo stesso
    motivo: quei tiri appartengono a un'altra competizione, che si gioca dopo
    che la partita e' finita.

    Il filtro sta **dentro** le aggregazioni invece che a carico di chi le
    chiama. In una dashboard con nove viste, prima o poi qualcuno lo
    dimenticherebbe, e il risultato sarebbe plausibile.

    **``astype(bool)`` non e' ridondante**, e il motivo e' una trappola di
    pandas che si vede solo sui casi limite. Se la colonna ha tipo ``object``
    — cosa che accade su una tabella vuota costruita senza dichiarare i tipi —
    ``~colonna`` non e' una maschera booleana, e ``tabella[serie_vuota]`` viene
    interpretato come **selezione di colonne per nome** invece che come filtro
    di righe: il risultato e' una tabella senza colonne, non una tabella vuota.
    L'errore poi esplode altrove, quando qualcuno cerca ``xg_statsbomb`` e non
    la trova, e da li' la causa non si risale.

    Sui dati veri la colonna e' booleana e la conversione non cambia niente.

    Args:
        tiri: I tiri, con la colonna ``rigori_finali``.

    Returns:
        I soli tiri giocati durante la partita, con tutte le colonne anche
        quando non ne resta nessuno.
    """
    if "rigori_finali" not in tiri.columns:
        return tiri
    return tiri[~tiri["rigori_finali"].astype(bool)]


def kpi(tiri: pd.DataFrame, partite: pd.DataFrame) -> dict[str, float]:
    """Calcola i numeri di testa della Panoramica.

    Args:
        tiri: I tiri della selezione corrente. I rigori della serie finale
            vengono esclusi qui dentro.
        partite: Le partite della stessa selezione.

    Returns:
        Partite, gol, tiri, xG totale, conversione, gol e xG per partita, e lo
        scarto fra gol e xG. Su selezione vuota restituisce zeri invece di
        NaN: una dashboard non deve mostrare «nan» a chi filtra troppo.
    """
    giocati = tiri_di_gioco(tiri)
    quante = len(partite)
    gol = float(partite["gol_casa"].sum() + partite["gol_ospite"].sum())
    quanti_tiri = len(giocati)
    xg = float(giocati["xg_statsbomb"].sum())

    return {
        "partite": float(quante),
        "gol": gol,
        "tiri": float(quanti_tiri),
        "xg": xg,
        "conversione": gol / quanti_tiri if quanti_tiri else 0.0,
        "gol_per_partita": gol / quante if quante else 0.0,
        "xg_per_partita": xg / quante if quante else 0.0,
        "tiri_per_partita": quanti_tiri / quante if quante else 0.0,
        "gol_meno_xg": gol - xg,
    }


def per_squadra(tiri: pd.DataFrame, quante: int | None = None) -> pd.DataFrame:
    """Aggrega tiri, gol e xG per squadra.

    I gol qui vengono **dai tiri**, non dalle partite, ed e' corretto: la
    domanda e' «quanto ha prodotto questa squadra tirando», e un autogol
    avversario non e' produzione offensiva. E' una definizione diversa da
    quella dei :func:`kpi`, e la differenza va detta a chi legge la vista.

    Args:
        tiri: I tiri della selezione corrente. I rigori della serie finale
            vengono esclusi qui dentro.
        quante: Quante squadre restituire, dalla migliore per xG. Se assente,
            tutte.

    Returns:
        Una riga per squadra, ordinata per xG decrescente.
    """
    giocati = tiri_di_gioco(tiri)
    if giocati.empty:
        return pd.DataFrame(columns=["squadra", "tiri", "gol", "xg", "gol_meno_xg", "xg_per_tiro"])

    tabella = (
        giocati.groupby("squadra", observed=True)
        .agg(tiri=("gol", "size"), gol=("gol", "sum"), xg=("xg_statsbomb", "sum"))
        .reset_index()
    )
    tabella["gol"] = tabella["gol"].astype("int32")
    tabella["gol_meno_xg"] = tabella["gol"] - tabella["xg"]
    tabella["xg_per_tiro"] = tabella["xg"] / tabella["tiri"]
    ordinata = tabella.sort_values("xg", ascending=False).reset_index(drop=True)
    return ordinata.head(quante) if quante else ordinata


def top_giocatori(
    giocatori: pd.DataFrame, quanti: int = QUANTI, soglia: int = SOGLIA_MINUTI
) -> pd.DataFrame:
    """I giocatori piu' prolifici, con la soglia dei minuti applicata.

    **La soglia non e' cosmetica.** Senza, il miglior marcatore per novanta
    minuti e' sempre qualcuno entrato al 90esimo che ha segnato: un gol in due
    minuti fa 45 gol per novanta. La soglia di cinquecento minuti — circa sei
    partite intere — e' quella dichiarata in ``config.SOGLIA_MINUTI`` e usata
    ovunque nel progetto.

    I giocatori sotto soglia **non vengono cancellati** dalle tabelle
    complete: qui si toglie solo dalla classifica, che e' la vista in cui il
    confronto per novanta minuti ha senso.

    Args:
        giocatori: La tabella ``player_stats``.
        quanti: Quante righe restituire.
        soglia: I minuti minimi per entrare in classifica.

    Returns:
        Una riga per giocatore, ordinata per gol decrescenti.
    """
    if giocatori.empty:
        return giocatori
    ammessi = giocatori[giocatori["minuti"] >= soglia]
    return ammessi.sort_values(["gol", "xg"], ascending=False).head(quanti).reset_index(drop=True)


#: I confini delle zone di tiro, nel sistema di StatsBomb.
#:
#: Coincidono con l'area di rigore e l'area piccola, quindi con quelle che il
#: modello usa in :mod:`football_analytics.features`. Non e' una griglia
#: arbitraria: sono i confini che un allenatore userebbe per parlare di tiri.
ZONE: Final[tuple[tuple[str, float, float], ...]] = (
    ("Fuori area", 0.0, 102.0),
    ("Area di rigore", 102.0, 114.0),
    ("Area piccola", 114.0, 120.0),
)

#: L'ampiezza dei blocchi in cui si divide la partita, in minuti.
QUARTO: Final[int] = 15


def realizzazione(tiri: pd.DataFrame) -> float:
    """Quanta parte dell'xG si e' trasformata in gol.

    Sopra il 100 % la selezione ha segnato piu' di quanto le occasioni
    promettessero. **Non e' bravura ne' fortuna in modo netto**: su una
    stagione intera e' quasi tutto rumore, su cinque anni comincia a essere
    qualcosa. La vista lo mostra, non lo interpreta.

    Args:
        tiri: I tiri della selezione.

    Returns:
        Il rapporto fra gol e xG. Zero se non ci sono tiri.
    """
    giocati = tiri_di_gioco(tiri)
    atteso = float(giocati["xg_statsbomb"].sum())
    return float(giocati["gol"].sum()) / atteso if atteso else 0.0


def per_zona(tiri: pd.DataFrame) -> pd.DataFrame:
    """Quanto vale un tiro, zona per zona.

    Args:
        tiri: I tiri della selezione.

    Returns:
        Una riga per zona, con quanti tiri, quanti gol e l'xG medio.
    """
    giocati = tiri_di_gioco(tiri)
    righe = []
    for nome, da, a in ZONE:
        parte = giocati[(giocati["x"] >= da) & (giocati["x"] < a)]
        righe.append(
            {
                "zona": nome,
                "tiri": len(parte),
                "gol": int(parte["gol"].sum()),
                "xg_medio": float(parte["xg_statsbomb"].mean()) if len(parte) else 0.0,
                "xg": float(parte["xg_statsbomb"].sum()),
            }
        )
    return pd.DataFrame(righe)


def per_quarto_dora(tiri: pd.DataFrame) -> pd.DataFrame:
    """Come si distribuisce l'xG lungo i novanta minuti.

    I blocchi sono di un quarto d'ora: piu' stretti diventano rumore, piu'
    larghi nascondono il finale di tempo, che e' proprio il momento in cui le
    partite cambiano.

    Args:
        tiri: I tiri della selezione.

    Returns:
        Una riga per blocco, in ordine di minuto.
    """
    giocati = tiri_di_gioco(tiri)
    if giocati.empty:
        return pd.DataFrame(columns=["blocco", "da", "tiri", "gol", "xg"])

    blocchi = (giocati["minuto"] // QUARTO).clip(upper=5)
    tabella = (
        giocati.assign(blocco=blocchi)
        .groupby("blocco", observed=True)
        .agg(tiri=("gol", "size"), gol=("gol", "sum"), xg=("xg_statsbomb", "sum"))
        .reset_index()
    )
    tabella["da"] = tabella["blocco"] * QUARTO
    tabella["blocco"] = tabella["da"].map(lambda m: f"{int(m)}′–{int(m) + QUARTO}′")
    return tabella.sort_values("da").reset_index(drop=True)


def andamento(partite: pd.DataFrame, colonne: Sequence[str] = ("gol", "xg")) -> pd.DataFrame:
    """Gol e xG per data, per vedere se una stagione cambia strada.

    Aggrega **per data** e non per giornata: le competizioni di questo progetto
    non hanno tutte le giornate — un torneo a eliminazione diretta ha fasi, non
    turni numerati — e la data e' l'unico asse comune a tutte.

    Args:
        partite: Le partite della selezione corrente.
        colonne: Quali serie calcolare. Serve ai test piu' che alle viste.

    Returns:
        Una riga per data, con gol e xG totali di giornata.
    """
    if partite.empty:
        return pd.DataFrame(columns=["data", *colonne])

    tabella = partite.copy()
    tabella["gol"] = tabella["gol_casa"] + tabella["gol_ospite"]
    tabella["xg"] = tabella["xg_casa"] + tabella["xg_ospite"]
    return (
        tabella.groupby("data", observed=True)[list(colonne)]
        .sum()
        .reset_index()
        .sort_values("data")
        .reset_index(drop=True)
    )
