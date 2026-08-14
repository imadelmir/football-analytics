"""Le graduatorie dei giocatori (M6-T5).

**Due vincoli decisi prima di scrivere una riga, e la pagina li rispetta senza
scorciatoie.**

*Una competizione alla volta.* Un xG per novanta minuti in Ligue 1 e uno a un
Mondiale non misurano la stessa cosa: cambiano gli avversari, il numero di
partite e il modo in cui i minuti si distribuiscono. Mettere i 4.810 giocatori
del magazzino in un'unica graduatoria produrrebbe un ordinamento che sembra
significativo e non lo e'. Qui le funzioni ricevono gia' una selezione, e la
pagina obbliga a sceglierla.

*Soglia fissa a 500 minuti.* Sotto quella quota i valori per novanta minuti
esplodono: un attaccante con un gol in 90 minuti giocati fa 1,00 gol/90 e
scavalcherebbe chiunque. La colonna ``sopra_soglia`` esiste gia' nel magazzino,
calcolata in M4 con :data:`~football_analytics.config.SOGLIA_MINUTI`, e questo
modulo la usa invece di ricalcolarla: un secondo posto dove sta scritto 500
sarebbe un secondo posto da cui puo' divergere.

**I ruoli vanno raggruppati, e il raggruppamento e' una scelta.** StatsBomb
registra la posizione esatta in campo — ventiquattro valori distinti nel
magazzino, da ``Left Wing Back`` a ``Secondary Striker`` — che come filtro sono
troppi e come etichetta dicono dove il giocatore si e' schierato, non che
mestiere fa. I quattro reparti sono la lettura comune, e la mappa e' esplicita:
nessun tentativo di indovinare dal nome, perche' ``Center Attacking Midfield``
e ``Center Defensive Midfield`` condividono due parole su tre e finiscono in
reparti diversi.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pandas as pd

from football_analytics import config

if TYPE_CHECKING:
    from collections.abc import Sequence

#: I minuti di una partita, per i valori «per novanta».
NOVANTA: Final[int] = 90

#: I quattro reparti, nell'ordine in cui si leggono in una formazione.
REPARTI: Final[tuple[str, ...]] = ("Portiere", "Difesa", "Centrocampo", "Attacco")

#: Da posizione StatsBomb a reparto.
#:
#: Scritta a mano e non dedotta dal nome. Le ali sono in **Attacco** e non a
#: centrocampo: nei dati sono i secondi tiratori dopo le punte, e metterle fra i
#: centrocampisti renderebbe il filtro «Attacco» una lista di soli centravanti.
#: I ``Wing Back`` restano in **Difesa**, che e' dove partono.
DA_POSIZIONE: Final[dict[str, str]] = {
    "Goalkeeper": "Portiere",
    "Right Back": "Difesa",
    "Left Back": "Difesa",
    "Right Center Back": "Difesa",
    "Left Center Back": "Difesa",
    "Center Back": "Difesa",
    "Right Wing Back": "Difesa",
    "Left Wing Back": "Difesa",
    "Right Defensive Midfield": "Centrocampo",
    "Left Defensive Midfield": "Centrocampo",
    "Center Defensive Midfield": "Centrocampo",
    "Right Center Midfield": "Centrocampo",
    "Left Center Midfield": "Centrocampo",
    "Right Midfield": "Centrocampo",
    "Left Midfield": "Centrocampo",
    "Center Attacking Midfield": "Centrocampo",
    "Right Attacking Midfield": "Centrocampo",
    "Left Attacking Midfield": "Centrocampo",
    "Right Wing": "Attacco",
    "Left Wing": "Attacco",
    "Center Forward": "Attacco",
    "Right Center Forward": "Attacco",
    "Left Center Forward": "Attacco",
    "Secondary Striker": "Attacco",
}

#: Il reparto di chi ha una posizione che la mappa non conosce.
#:
#: Non e' un ripiego silenzioso: un test verifica che nel magazzino non ce ne
#: siano: se StatsBomb aggiungesse una posizione, il test lo direbbe invece di
#: lasciarla scivolare in un gruppo a caso.
IGNOTO: Final[str] = "Altro"


def reparto(posizione: str) -> str:
    """Il reparto di una posizione StatsBomb.

    Args:
        posizione: La posizione, per esempio ``"Left Wing"``.

    Returns:
        Uno dei :data:`REPARTI`, oppure :data:`IGNOTO`.
    """
    return DA_POSIZIONE.get(posizione, IGNOTO)


def con_reparto(tabella: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge la colonna ``reparto`` senza toccare il resto.

    Args:
        tabella: Le statistiche dei giocatori.

    Returns:
        Una copia con ``reparto`` in piu'.
    """
    copia = tabella.copy()
    copia["reparto"] = copia["ruolo"].astype(str).map(reparto)
    return copia


def per_giocatore(tabella: pd.DataFrame) -> pd.DataFrame:
    """Una riga per giocatore, sommando chi ha cambiato squadra a stagione in corso.

    **Nel magazzino la chiave e' (competizione, giocatore, squadra)**, ed e'
    giusto cosi': la scheda di una squadra deve contare solo i gol segnati con
    quella maglia. Per una classifica di competizione la stessa struttura e'
    sbagliata, e in modo silenzioso: Éder nel 2015/16 ha 12 gol con la
    Sampdoria e 1 con l'Inter, e senza questa somma il tabellone dei marcatori
    ne mostrerebbe 12. Il numero sembra giusto perche' e' quasi giusto.

    Sono 83 righe su 4.810 nel magazzino: abbastanza poche da non notarsi,
    abbastanza da falsare una graduatoria.

    **Le squadre restano tutte**, unite da una virgola: nascondere il
    trasferimento renderebbe la riga incomprensibile a chi conosce la stagione.

    **I valori per novanta e la soglia si ricalcolano sui minuti totali.** Il
    valore per novanta di una somma non e' la somma dei valori per novanta, e
    la soglia va confrontata con quanto il giocatore ha giocato davvero, non
    con quanto ha giocato in una delle due maglie.

    Args:
        tabella: Le statistiche per giocatore e squadra.

    Returns:
        Una riga per giocatore, con le stesse colonne piu' ``squadre``.
    """
    if tabella.empty:
        return tabella

    somme = {
        colonna: "sum"
        for colonna in ("partite", "minuti", "tiri", "gol", "xg", "gol_meno_xg")
        if colonna in tabella.columns
    }
    gruppi = tabella.groupby(["giocatore_id", "giocatore", "giocatore_breve"], observed=True)
    unito = gruppi.agg(somme).reset_index()
    unito["squadra"] = (
        gruppi["squadra"]
        .apply(lambda nomi: ", ".join(dict.fromkeys(str(nome) for nome in nomi)))
        .to_numpy()
    )
    unito["ruolo"] = gruppi["ruolo"].first().to_numpy()

    minuti = unito["minuti"].astype(float)
    for metrica in ("tiri", "gol", "xg"):
        unito[f"{metrica}_90"] = (unito[metrica] / minuti.where(minuti > 0) * NOVANTA).fillna(0.0)
    unito["sopra_soglia"] = unito["minuti"] >= config.SOGLIA_MINUTI
    return unito


def qualificati(tabella: pd.DataFrame) -> pd.DataFrame:
    """I soli giocatori che superano la soglia di minuti.

    Legge ``sopra_soglia`` invece di confrontare i minuti con un numero: la
    soglia e' decisa in un posto solo, e riscriverla qui vorrebbe dire poterla
    cambiare in un posto e non nell'altro.

    Args:
        tabella: Le statistiche dei giocatori.

    Returns:
        Le sole righe qualificate.
    """
    if "sopra_soglia" not in tabella.columns:
        return tabella
    return tabella[tabella["sopra_soglia"]]


def graduatoria(
    tabella: pd.DataFrame, colonna: str, quanti: int = 10, *, crescente: bool = False
) -> pd.DataFrame:
    """Le prime posizioni per una metrica, fra i soli qualificati.

    Args:
        tabella: Le statistiche dei giocatori.
        colonna: La metrica su cui ordinare.
        quanti: Quante righe restituire.
        crescente: Se vero ordina dal peggiore, per le graduatorie al contrario.

    Returns:
        Le righe scelte, gia' ordinate. Vuota se la colonna non c'e' o se
        nessuno supera la soglia.
    """
    validi = qualificati(tabella)
    if validi.empty or colonna not in validi.columns:
        return validi.iloc[0:0]
    ordinata = validi.sort_values(colonna, ascending=crescente, kind="stable")
    return ordinata.head(quanti)


def numeri(tabella: pd.DataFrame) -> dict[str, float]:
    """I totali che vanno nella striscia degli indicatori.

    **I totali sono su tutti i giocatori, non sui soli qualificati**: i gol di
    chi ha giocato poco sono comunque gol della competizione, e un totale che
    ne escludesse una parte non tornerebbe con quello mostrato altrove nella
    dashboard.

    Args:
        tabella: Le statistiche dei giocatori.

    Returns:
        ``giocatori``, ``qualificati``, ``gol``, ``xg`` e ``minuti``.
    """
    if tabella.empty:
        return {"giocatori": 0.0, "qualificati": 0.0, "gol": 0.0, "xg": 0.0, "minuti": 0.0}
    return {
        "giocatori": float(len(tabella)),
        "qualificati": float(len(qualificati(tabella))),
        "gol": float(tabella["gol"].sum()),
        "xg": float(tabella["xg"].sum()),
        "minuti": float(tabella["minuti"].sum()),
    }


def per_reparto(tabella: pd.DataFrame) -> pd.DataFrame:
    """Quanto produce ogni reparto, per capire da dove arrivano i gol.

    Args:
        tabella: Le statistiche dei giocatori, anche senza la colonna
            ``reparto``: viene aggiunta se manca.

    Returns:
        Una riga per reparto con ``giocatori``, ``gol``, ``xg`` e
        ``quota_gol``, nell'ordine di :data:`REPARTI`.
    """
    if tabella.empty:
        return pd.DataFrame(columns=["reparto", "giocatori", "gol", "xg", "quota_gol"])

    con = tabella if "reparto" in tabella.columns else con_reparto(tabella)
    gruppi = con.groupby("reparto", observed=True)
    riassunto = pd.DataFrame(
        {
            "giocatori": gruppi.size(),
            "gol": gruppi["gol"].sum(),
            "xg": gruppi["xg"].sum(),
        }
    ).reset_index()

    totale = float(riassunto["gol"].sum())
    riassunto["quota_gol"] = riassunto["gol"] / totale if totale else 0.0
    ordine = {nome: posto for posto, nome in enumerate((*REPARTI, IGNOTO))}
    riassunto["_ordine"] = riassunto["reparto"].map(ordine).fillna(len(ordine))
    return riassunto.sort_values("_ordine").drop(columns="_ordine").reset_index(drop=True)


def filtra_reparto(tabella: pd.DataFrame, scelti: Sequence[str]) -> pd.DataFrame:
    """Restringe ai reparti scelti.

    Args:
        tabella: Le statistiche dei giocatori.
        scelti: I reparti da tenere. Vuoto significa tutti.

    Returns:
        Le righe dei reparti scelti.
    """
    if not scelti:
        return tabella
    con = tabella if "reparto" in tabella.columns else con_reparto(tabella)
    return con[con["reparto"].isin(list(scelti))]


def scheda(tabella: pd.DataFrame, giocatore: str) -> dict[str, float]:
    """I numeri di un singolo giocatore.

    Args:
        tabella: Le statistiche dei giocatori.
        giocatore: Il nome completo.

    Returns:
        I suoi valori, vuoto se non compare nella selezione.
    """
    trovato = tabella[tabella["giocatore"] == giocatore]
    if trovato.empty:
        return {}
    riga = trovato.iloc[0]
    tiri = float(riga["tiri"])
    return {
        "partite": float(riga["partite"]),
        "minuti": float(riga["minuti"]),
        "tiri": tiri,
        "gol": float(riga["gol"]),
        "xg": float(riga["xg"]),
        "gol_meno_xg": float(riga["gol_meno_xg"]),
        "gol_90": float(riga["gol_90"]),
        "xg_90": float(riga["xg_90"]),
        "xg_per_tiro": float(riga["xg"]) / tiri if tiri else 0.0,
    }


#: Gli assi del radar: etichetta, colonna, quante cifre mostrare.
#:
#: Cinque metriche gia' nel magazzino, tutte normalizzate sui minuti tranne
#: ``xg_per_tiro``, che e' un rapporto e quindi lo e' per costruzione. Insieme
#: separano le tre cose che l'xG permette di distinguere: **quanto** si tira,
#: **da dove** — cioe' la qualita' delle occasioni — e **quanto si realizza**.
ASSI_RADAR: Final[tuple[tuple[str, str, int], ...]] = (
    ("Tiri/90", "tiri_90", 2),
    ("xG/90", "xg_90", 2),
    ("Gol/90", "gol_90", 2),
    ("xG per tiro", "xg_per_tiro", 3),
    ("Gol − xG", "gol_meno_xg", 1),
)

#: Quanti giocatori servono in un reparto perche' un percentile significhi qualcosa.
#:
#: Con meno di questi il percentile diventa una posizione in una fila corta:
#: «meglio del 66 %» su quattro giocatori vuol dire «terzo su quattro», che e'
#: un'informazione diversa e molto piu' debole.
MINIMO_CONFRONTO: Final[int] = 20


def con_xg_per_tiro(tabella: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge ``xg_per_tiro``, che il magazzino non ha.

    Args:
        tabella: Le statistiche dei giocatori.

    Returns:
        Una copia con la colonna in piu'. Chi non ha tirato vale zero, non
        indefinito: sul radar un buco e un valore basso si leggono allo stesso
        modo, ma un ``NaN`` farebbe sparire l'asse.
    """
    copia = tabella.copy()
    # La divisione con `where` invece di `replace(0, pd.NA)`: quest'ultimo
    # rende la colonna di tipo oggetto, e il `fillna` che segue emette un
    # avviso di deprecazione a ogni chiamata.
    tiri = copia["tiri"].astype(float)
    copia["xg_per_tiro"] = (copia["xg"] / tiri.where(tiri > 0)).fillna(0.0)
    return copia


def percentili(tabella: pd.DataFrame, giocatore_id: int) -> dict[str, float]:
    """Dove sta un giocatore rispetto al proprio reparto, asse per asse.

    **Percentile e non rapporto sulla media.** Gli assi hanno unita' diverse —
    tiri, gol, xG, differenze — e un rapporto le renderebbe incomparabili; peggio,
    su ``gol_meno_xg`` la media di reparto e' vicina a zero e il rapporto
    esploderebbe. Il percentile porta tutto su una scala 0-100 che si legge come
    «meglio dell'85 % del reparto».

    **Il confronto e' dentro il reparto e fra i soli qualificati.** Un attaccante
    misurato contro i portieri risulterebbe fenomenale su ogni asse, e chi ha
    giocato duecento minuti sporcherebbe la distribuzione con valori per novanta
    fuori scala.

    Args:
        tabella: Le statistiche di **una sola competizione**.
        giocatore_id: L'identificativo del giocatore.

    Returns:
        Il percentile 0-100 per ogni asse di :data:`ASSI_RADAR`, piu'
        ``confronto`` con quanti giocatori compongono la distribuzione. Vuoto se
        il giocatore non c'e' o se il suo reparto ha meno di
        :data:`MINIMO_CONFRONTO` qualificati.
    """
    completa = con_xg_per_tiro(con_reparto(tabella))
    suo = completa[completa["giocatore_id"] == giocatore_id]
    if suo.empty:
        return {}

    reparto_suo = str(suo.iloc[0]["reparto"])
    pari = qualificati(completa[completa["reparto"] == reparto_suo])
    if len(pari) < MINIMO_CONFRONTO:
        return {}

    riga = suo.iloc[0]
    posizioni: dict[str, float] = {"confronto": float(len(pari))}
    for _, colonna, _ in ASSI_RADAR:
        valori = pari[colonna].to_numpy()
        # Chi vale quanto la mediana sta al 50: contare i pari a meta' evita
        # che una colonna con molti zeri — i difensori su gol/90 — mandi tutti
        # al percentile zero o cento a seconda del verso della disuguaglianza.
        sotto = float((valori < riga[colonna]).sum())
        uguali = float((valori == riga[colonna]).sum())
        posizioni[colonna] = (sotto + uguali / 2) / len(pari) * 100
    return posizioni


def andamento(tiri: pd.DataFrame, giocatore_id: int) -> pd.DataFrame:
    """Gol e xG accumulati partita dopo partita.

    Args:
        tiri: I tiri della competizione.
        giocatore_id: L'identificativo del giocatore.

    Returns:
        Una riga per partita con ``gol`` e ``xg`` cumulati. Vuota se non ha
        mai tirato.
    """
    suoi = tiri[tiri["giocatore_id"] == giocatore_id]
    if "rigori_finali" in suoi.columns:
        suoi = suoi[~suoi["rigori_finali"]]
    if suoi.empty:
        return pd.DataFrame(columns=["match_id", "gol", "xg"])

    per_partita = (
        suoi.groupby("match_id", observed=True)
        .agg(gol=("gol", "sum"), xg=("xg_statsbomb", "sum"))
        .reset_index()
    )
    per_partita[["gol", "xg"]] = per_partita[["gol", "xg"]].cumsum()
    return per_partita


def tiri_di(tiri: pd.DataFrame, giocatore_id: int) -> pd.DataFrame:
    """Il dettaglio dei tiri di un giocatore, dal piu' pericoloso.

    Args:
        tiri: I tiri della competizione.
        giocatore_id: L'identificativo del giocatore.

    Returns:
        Le colonne che la scheda mostra, ordinate per xG.
    """
    suoi = tiri[tiri["giocatore_id"] == giocatore_id]
    if suoi.empty:
        return suoi
    colonne = ["minuto", "avversario", "esito", "xg_statsbomb", "parte_corpo", "tipo"]
    return suoi[[c for c in colonne if c in suoi.columns]].sort_values(
        "xg_statsbomb", ascending=False
    )
