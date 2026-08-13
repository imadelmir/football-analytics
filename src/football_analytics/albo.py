"""L'albo d'oro ricostruito dalle finali (M6-T4).

**Nel magazzino non esiste una colonna «trofei».** Esistono pero' le finali di
Champions, e da un risultato si ricava chi ha alzato la coppa. Questo modulo fa
solo quello: nessun dato inventato, nessun elenco scritto a mano.

**Due trappole, entrambe verificate sui dati e non supposte.**

- La competizione ``champions_finali`` **non contiene solo finali**: c'e' anche
  Fiorentina — Manchester United del 23 novembre 1999, che e' una partita di
  girone. Filtrare per competizione invece che per ``fase`` metterebbe la
  Fiorentina nell'albo d'oro della Champions League.
- Tre finali sono finite ai rigori, e nel tabellino restano in pareggio. Il
  vincitore si ricava dai tiri con ``rigori_finali``, che nel magazzino ci
  sono: senza, tre coppe sparirebbero e nessuno se ne accorgerebbe guardando la
  pagina.

**Il conteggio non e' l'albo d'oro vero, e la pagina deve dirlo.** L'Open Data
copre diciassette finali, non tutte: per il Liverpool risultano due coppe
invece di sei. Scrivere «Trofei: 2» sarebbe falso, quindi qui si parla sempre
di finali *presenti nei dati* e chi disegna e' tenuto a ripeterlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class Palmares:
    """Le finali di una squadra fra quelle presenti nel magazzino.

    E' un tipo e non un ``dict[str, object]``: con il dizionario generico mypy
    non sa che ``vinte`` e' un intero e che ``anni_vinti`` si puo' scorrere, e
    ogni lettura nella pagina andrebbe silenziata con un ``type: ignore`` —
    che non e' una correzione, e' un silenziatore.

    Attributes:
        giocate: Quante finali ha disputato.
        vinte: Quante ne ha vinte.
        anni_vinti: Gli anni delle vittorie, in ordine.
    """

    giocate: int
    vinte: int
    anni_vinti: tuple[int, ...]


#: Come StatsBomb chiama la fase finale.
FASE_FINALE: Final[str] = "Final"

#: Quante squadre devono aver calciato perche' un tiebreak sia leggibile.
CONTENDENTI: Final[int] = 2


def finali(partite: pd.DataFrame) -> pd.DataFrame:
    """Le sole partite che sono davvero finali.

    Args:
        partite: Le partite, di qualunque competizione.

    Returns:
        Le righe con ``fase`` uguale a :data:`FASE_FINALE`.
    """
    if "fase" not in partite.columns:
        return partite.iloc[0:0]
    return partite[partite["fase"].astype(str) == FASE_FINALE]


def _vincitrice(partita: pd.Series, rigori: pd.DataFrame) -> str | None:
    """Chi ha vinto una finale, rigori compresi.

    Args:
        partita: La riga della finale.
        rigori: I tiri dai rigori dei tiebreak, gia' filtrati.

    Returns:
        Il nome della vincitrice, oppure ``None`` se non e' determinabile —
        cioe' se la finale e' pari e i rigori non sono nel magazzino. Meglio
        nessuna risposta che una sbagliata.
    """
    casa, ospite = str(partita["casa"]), str(partita["ospite"])
    if partita["gol_casa"] > partita["gol_ospite"]:
        return casa
    if partita["gol_ospite"] > partita["gol_casa"]:
        return ospite

    segnati = rigori[rigori["match_id"] == partita["match_id"]]
    segnati = segnati.groupby("squadra", observed=True)["gol"].sum()
    segnati = segnati[segnati.index.isin([casa, ospite])]
    if len(segnati) < CONTENDENTI or segnati.max() == segnati.min():
        return None
    return str(segnati.idxmax())


def _righe(partite: pd.DataFrame, tiri: pd.DataFrame) -> Iterator[dict[str, object]]:
    """Una riga per squadra per finale, con l'esito.

    Args:
        partite: Le sole finali.
        tiri: I tiri della selezione.

    Yields:
        Le partecipazioni, due per finale.
    """
    rigori = tiri[tiri["rigori_finali"]] if "rigori_finali" in tiri.columns else tiri.iloc[0:0]
    for _, partita in partite.iterrows():
        vinta_da = _vincitrice(partita, rigori)
        anno = pd.Timestamp(partita["data"]).year
        for squadra in (str(partita["casa"]), str(partita["ospite"])):
            yield {
                "squadra": squadra,
                "anno": anno,
                "vinta": vinta_da == squadra,
            }


def albo(partite: pd.DataFrame, tiri: pd.DataFrame) -> pd.DataFrame:
    """Quante finali ha giocato e vinto ogni squadra, con gli anni.

    Args:
        partite: Le partite della competizione delle finali.
        tiri: I tiri della stessa selezione, per i rigori dei tiebreak.

    Returns:
        Una riga per squadra con ``giocate``, ``vinte`` e ``anni_vinti``,
        ordinata per coppe e poi per finali. Vuota se non ci sono finali.
    """
    disputate = finali(partite)
    if disputate.empty:
        return pd.DataFrame(columns=["squadra", "giocate", "vinte", "anni_vinti"])

    voci = pd.DataFrame(list(_righe(disputate, tiri)))
    per_squadra = voci.groupby("squadra", observed=True)
    conteggi = pd.DataFrame(
        {
            "giocate": per_squadra.size(),
            "vinte": per_squadra["vinta"].sum(),
        }
    ).reset_index()
    anni = (
        voci[voci["vinta"]]
        .groupby("squadra", observed=True)["anno"]
        .apply(sorted)
        .rename("anni_vinti")
        .reset_index()
    )
    unito = conteggi.merge(anni, on="squadra", how="left")
    unito["anni_vinti"] = unito["anni_vinti"].apply(lambda v: v if isinstance(v, list) else [])
    return unito.sort_values(["vinte", "giocate"], ascending=False).reset_index(drop=True)


def di_squadra(tavola: pd.DataFrame, squadra: str) -> Palmares | None:
    """La riga dell'albo di una squadra, se ha giocato finali.

    Args:
        tavola: Il risultato di :func:`albo`.
        squadra: Il nome della squadra.

    Returns:
        Il :class:`Palmares`, oppure ``None``. Chi disegna deve trattare
        ``None`` come «non si mostra niente»: una squadra senza finali nei dati
        non ha un palmares da zero, ha un palmares che questo progetto non
        conosce.
    """
    # Due uscite invece di un ternario: `tavola.index[...]` e la lista vuota
    # sono tipi diversi, e messi nello stesso ternario mypy non sa piu' che
    # cosa sia `trovata`.
    if tavola.empty:
        return None
    trovata = tavola.index[tavola["squadra"] == squadra]
    if len(trovata) == 0:
        return None
    riga = tavola.loc[trovata[0]]
    return Palmares(
        giocate=int(riga["giocate"]),
        vinte=int(riga["vinte"]),
        anni_vinti=tuple(int(anno) for anno in riga["anni_vinti"]),
    )
