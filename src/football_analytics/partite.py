"""Le singole partite, e cosa l'xG dice del risultato (M6-T7).

**La domanda di questa vista e' una sola: chi meritava di vincere.** E' l'unica
a cui l'xG risponde meglio del tabellino, e in Serie A 2015/16 succede **30
volte su 380**, cioe' l'8 %.

Il conto grezzo — chi ha vinto avendo meno xG, senza altre condizioni — ne
darebbe 71. La differenza sono quaranta partite in cui le due squadre hanno
creato praticamente la stessa cosa, e chiamare «immeritata» una vittoria per
0,05 di xG sarebbe leggere rumore. La soglia sta in :data:`SCARTO_MINIMO`.

**Il confronto e' fra le due squadre della stessa partita**, quindi non ha
nessuno dei problemi che avevano le graduatorie: stesso campo, stesso arbitro,
stessi novanta minuti. E' l'unico posto della dashboard dove due valori di xG
si possono mettere accanto senza cautele.

**Gli autogol restano fuori dall'xG e dentro il risultato.** Un autogol non e'
un'occasione creata da chi lo subisce e non ne ha una: il magazzino tiene le
due cose separate — ``gol_casa`` conta tutto, ``gol_casa_da_tiro`` solo cio'
che nasce da un tiro — e qui si usa la colonna giusta per ciascuna domanda.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Scheda:
    """I numeri di una partita, pronti per essere disegnati.

    E' un tipo e non un ``dict[str, object]``, ed e' la terza volta che il
    progetto impara la stessa lezione: con il dizionario generico mypy non sa
    che ``xg_casa`` e' un numero, e ogni lettura nella pagina andrebbe
    silenziata con un ``type: ignore``.

    Attributes:
        casa: La squadra di casa.
        ospite: La squadra ospite.
        gol_casa: I gol della casa, autogol compresi.
        gol_ospite: I gol dell'ospite, autogol compresi.
        xg_casa: L'xG generato dalla casa.
        xg_ospite: L'xG generato dall'ospite.
        tiri_casa: I tiri della casa.
        tiri_ospite: I tiri dell'ospite.
        autogol_casa: Gli autogol subiti dalla casa.
        autogol_ospite: Gli autogol subiti dall'ospite.
        data: La data della partita.
        giornata: Il turno.
        vincitrice: Chi ha vinto, stringa vuota in caso di pareggio.
        favorita_xg: Chi ha creato di piu', stringa vuota se si equivalgono.
        ribaltata: Se ha vinto la squadra che aveva creato meno.
        ai_rigori: Se la partita si e' decisa ai rigori.
    """

    casa: str
    ospite: str
    gol_casa: int
    gol_ospite: int
    xg_casa: float
    xg_ospite: float
    tiri_casa: int
    tiri_ospite: int
    autogol_casa: int
    autogol_ospite: int
    data: pd.Timestamp
    giornata: int
    vincitrice: str
    favorita_xg: str
    ribaltata: bool
    ai_rigori: bool


#: Quanto scarto di xG serve per dire che una squadra ha meritato.
#:
#: Sotto questa soglia le due squadre hanno creato **la stessa cosa**, e
#: assegnare un merito a chi ha 0,05 di xG in piu' sarebbe leggere rumore. Il
#: valore corrisponde grosso modo a un tiro da fuori area: meno di cosi' non e'
#: una differenza di gioco.
SCARTO_MINIMO: Final[float] = 0.5

#: Quante partite nelle liste dei casi notevoli.
QUANTE_NOTEVOLI: Final[int] = 5


def con_esiti(partite: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge risultato, differenze e giudizio dell'xG.

    Args:
        partite: Le partite della selezione.

    Returns:
        Una copia con ``risultato``, ``differenza_xg``, ``vincitrice``,
        ``favorita_xg`` e ``ribaltata``. ``vincitrice`` e ``favorita_xg``
        valgono stringa vuota quando non c'e' un vincitore o quando le due
        squadre si equivalgono.
    """
    if partite.empty:
        return partite.assign(
            risultato="", differenza_xg=0.0, vincitrice="", favorita_xg="", ribaltata=False
        )

    tavola = partite.copy()
    # Nel magazzino `data` e' una **stringa**, non un timestamp: convertirla qui
    # significa che chi disegna non deve ricordarselo. Senza, la colonna data
    # di `st.dataframe` mostrerebbe testo e formattare la data in una f-string
    # solleverebbe «Invalid format specifier».
    tavola["data"] = pd.to_datetime(tavola["data"])
    casa = tavola["casa"].astype(str)
    ospite = tavola["ospite"].astype(str)
    tavola["risultato"] = (
        tavola["gol_casa"].astype(int).astype(str)
        + "–"
        + tavola["gol_ospite"].astype(int).astype(str)
    )
    tavola["differenza_xg"] = tavola["xg_casa"] - tavola["xg_ospite"]

    tavola["vincitrice"] = ""
    tavola.loc[tavola["gol_casa"] > tavola["gol_ospite"], "vincitrice"] = casa
    tavola.loc[tavola["gol_ospite"] > tavola["gol_casa"], "vincitrice"] = ospite

    tavola["favorita_xg"] = ""
    tavola.loc[tavola["differenza_xg"] > SCARTO_MINIMO, "favorita_xg"] = casa
    tavola.loc[tavola["differenza_xg"] < -SCARTO_MINIMO, "favorita_xg"] = ospite

    # Ribaltata solo quando **entrambe** le cose esistono: senza un vincitore o
    # senza una favorita chiara non c'e' niente da ribaltare, e un confronto
    # fra due stringhe vuote direbbe di si'.
    tavola["ribaltata"] = (
        (tavola["vincitrice"] != "")
        & (tavola["favorita_xg"] != "")
        & (tavola["vincitrice"] != tavola["favorita_xg"])
    )
    return tavola


def di_squadra(partite: pd.DataFrame, squadra: str | None) -> pd.DataFrame:
    """Le partite in cui una squadra compare, in casa **o** in trasferta.

    Filtrare la sola colonna ``casa`` darebbe meta' campionato — diciannove
    partite su trentotto — e il numero resterebbe plausibile.

    Args:
        partite: Le partite della selezione.
        squadra: Il nome della squadra, oppure ``None`` per tutte.

    Returns:
        Le sole partite di quella squadra.
    """
    if squadra is None or partite.empty:
        return partite
    return partite[(partite["casa"] == squadra) | (partite["ospite"] == squadra)]


def elenco(partite: pd.DataFrame) -> pd.DataFrame:
    """Le partite in ordine di data, pronte per la tabella.

    Args:
        partite: Le partite della selezione.

    Returns:
        Le colonne che la vista mostra, dalla piu' recente.
    """
    if partite.empty:
        return partite
    colonne = [
        "match_id",
        "data",
        "giornata",
        "casa",
        "risultato",
        "ospite",
        "xg_casa",
        "xg_ospite",
        "differenza_xg",
        "tiri_casa",
        "tiri_ospite",
        "ribaltata",
    ]
    tavola = con_esiti(partite).sort_values("data", ascending=False)
    return tavola[[c for c in colonne if c in tavola.columns]]


def ribaltate(partite: pd.DataFrame, quante: int = QUANTE_NOTEVOLI) -> pd.DataFrame:
    """Le partite vinte da chi aveva creato meno, dalla piu' clamorosa.

    Args:
        partite: Le partite della selezione.
        quante: Quante righe restituire.

    Returns:
        Le partite con l'esito contrario all'xG, ordinate per distanza fra le
        due squadre.
    """
    tavola = con_esiti(partite)
    if tavola.empty:
        return tavola
    contrarie = tavola[tavola["ribaltata"]].copy()
    if contrarie.empty:
        return contrarie
    contrarie["distanza"] = contrarie["differenza_xg"].abs()
    return contrarie.sort_values("distanza", ascending=False).head(quante)


def piu_aperte(partite: pd.DataFrame, quante: int = QUANTE_NOTEVOLI) -> pd.DataFrame:
    """Le partite con piu' occasioni complessive, da spettacolo.

    Args:
        partite: Le partite della selezione.
        quante: Quante righe restituire.

    Returns:
        Le partite con la somma di xG piu' alta.
    """
    tavola = con_esiti(partite)
    if tavola.empty:
        return tavola
    tavola = tavola.copy()
    tavola["xg_totale"] = tavola["xg_casa"] + tavola["xg_ospite"]
    return tavola.sort_values("xg_totale", ascending=False).head(quante)


def numeri(partite: pd.DataFrame) -> dict[str, float]:
    """I totali della competizione, per la striscia degli indicatori.

    Args:
        partite: Le partite della selezione.

    Returns:
        ``partite``, ``gol``, ``xg``, ``ribaltate`` e ``quota_ribaltate``.
    """
    if partite.empty:
        return {"partite": 0.0, "gol": 0.0, "xg": 0.0, "ribaltate": 0.0, "quota_ribaltate": 0.0}
    tavola = con_esiti(partite)
    quante = float(len(tavola))
    contrarie = float(tavola["ribaltata"].sum())
    return {
        "partite": quante,
        "gol": float(tavola["gol_casa"].sum() + tavola["gol_ospite"].sum()),
        "xg": float(tavola["xg_casa"].sum() + tavola["xg_ospite"].sum()),
        "ribaltate": contrarie,
        "quota_ribaltate": contrarie / quante,
    }


def scheda(partite: pd.DataFrame, match_id: int) -> Scheda | None:
    """I numeri di una singola partita.

    Args:
        partite: Le partite della selezione.
        match_id: L'identificativo della partita.

    Returns:
        La :class:`Scheda`, oppure ``None`` se la partita non c'e'.
    """
    trovata = con_esiti(partite)
    trovata = trovata[trovata["match_id"] == match_id]
    if trovata.empty:
        return None
    riga = trovata.iloc[0]
    return Scheda(
        casa=str(riga["casa"]),
        ospite=str(riga["ospite"]),
        gol_casa=int(riga["gol_casa"]),
        gol_ospite=int(riga["gol_ospite"]),
        xg_casa=float(riga["xg_casa"]),
        xg_ospite=float(riga["xg_ospite"]),
        tiri_casa=int(riga["tiri_casa"]),
        tiri_ospite=int(riga["tiri_ospite"]),
        autogol_casa=int(riga.get("autogol_casa", 0)),
        autogol_ospite=int(riga.get("autogol_ospite", 0)),
        data=pd.Timestamp(riga["data"]),
        giornata=int(riga["giornata"]),
        vincitrice=str(riga["vincitrice"]),
        favorita_xg=str(riga["favorita_xg"]),
        ribaltata=bool(riga["ribaltata"]),
        ai_rigori=bool(riga.get("ai_rigori", False)),
    )


def corsa_xg(tiri: pd.DataFrame, match_id: int, squadre: Sequence[str]) -> pd.DataFrame:
    """L'xG accumulato minuto per minuto dalle due squadre.

    **I rigori dei tiebreak restano fuori.** Sono una lotteria dopo la partita,
    e sommarli alla corsa dell'xG farebbe salire una curva quando la partita e'
    gia' finita.

    Args:
        tiri: I tiri della selezione.
        match_id: L'identificativo della partita.
        squadre: Le due squadre, nell'ordine casa e ospite.

    Returns:
        Una riga per minuto con una colonna per squadra, gia' cumulata. Vuota
        se la partita non ha tiri.
    """
    suoi = tiri[tiri["match_id"] == match_id]
    if "rigori_finali" in suoi.columns:
        suoi = suoi[~suoi["rigori_finali"]]
    if suoi.empty:
        return pd.DataFrame(columns=["minuto", *squadre])

    per_minuto = suoi.pivot_table(
        index="minuto",
        columns="squadra",
        values="xg_statsbomb",
        aggfunc="sum",
        fill_value=0.0,
        # `squadra` e' categorica e comprende tutte le squadre del magazzino:
        # senza `observed`, pandas creerebbe una colonna per ognuna e la
        # tabella avrebbe centocinquanta colonne di zeri.
        observed=True,
    )
    for nome in squadre:
        if nome not in per_minuto.columns:
            per_minuto[nome] = 0.0

    # La riga a zero all'inizio non e' cosmetica: senza, la curva parte dal
    # primo tiro e sembra che la partita cominci al minuto in cui qualcuno
    # calcia.
    completo = per_minuto.reindex(range(0, int(suoi["minuto"].max()) + 1), fill_value=0.0)
    cumulato = completo[list(squadre)].cumsum().reset_index()
    return cumulato.rename(columns={"index": "minuto"})
