"""La classifica e gli aggregati per squadra (M6-T4).

**La classifica e' ricostruita dai risultati, non letta da una tabella.**
StatsBomb Open Data non contiene classifiche: contiene partite. Ricostruirle
significa poterle verificare contro la realta', ed e' quello che fa
``tests/test_classifica.py`` — le classifiche calcolate qui riproducono
esattamente quelle vere di Liga, Premier e Serie A 2015/16, Barcellona a 91
punti, Leicester a 81, Juventus a 91.

**La Ligue 1 non torna, e la ragione e' nota.** Nell'Open Data mancano tre
partite delle giornate 14, 23 e 36, quindi sei squadre ne hanno giocate 37
invece di 38 e il PSG risulta a 93 punti invece dei 96 veri. Il modulo non
prova a rattoppare il buco: espone :func:`incomplete`, e la pagina lo dichiara.
Una classifica che sembra ufficiale ed e' sbagliata di tre punti e' peggio di
una che ammette di essere parziale.

**Gli autogol sono gia' dentro il risultato.** Nelle partite del magazzino
``gol_casa`` vale ``gol_casa_da_tiro + autogol_casa`` in tutte le 380 partite
della Liga, quindi ``autogol_casa`` e' l'autogol **accreditato** alla squadra
di casa. La classifica usa direttamente ``gol_casa`` e ``gol_ospite``: sommare
di nuovo gli autogol li conterebbe due volte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pandas as pd

from football_analytics.config import Gruppo
from football_analytics.panoramica import tiri_di_gioco

if TYPE_CHECKING:
    from collections.abc import Sequence

#: I punti di una vittoria e di un pareggio.
PUNTI_VITTORIA: Final[int] = 3
PUNTI_PAREGGIO: Final[int] = 1

#: L'ordine di lettura della classifica.
#:
#: Punti, poi differenza reti, poi gol fatti. **Non e' il regolamento della
#: Liga**, che a parita' di punti guarda gli scontri diretti: e' il criterio
#: piu' diffuso, e l'unico calcolabile senza ricostruire ogni testa a testa.
#: Sui quattro campionati del magazzino produce comunque l'ordine vero, ma
#: resta un'approssimazione dichiarata e non una regola ufficiale.
ORDINE: Final[tuple[str, ...]] = ("punti", "differenza", "gol_fatti")

#: Le colonne che vanno scambiate quando si guarda la partita dall'altra parte.
#:
#: Quattro terne invece di quattro `rename` sparsi: il ribaltamento casa-ospite
#: e' il punto in cui e' piu' facile sbagliare — basta dimenticare una colonna e
#: meta' dei numeri di una squadra diventano quelli dell'avversario, senza che
#: niente si rompa. Concentrandolo qui l'errore o c'e' per tutte le colonne o
#: per nessuna, e i test lo vedono.
COPPIE: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("casa", "ospite", "squadra", "avversario"),
    ("gol_casa", "gol_ospite", "gol_fatti", "gol_subiti"),
    ("xg_casa", "xg_ospite", "xg_fatti", "xg_subiti"),
    ("tiri_casa", "tiri_ospite", "tiri_fatti", "tiri_subiti"),
)

#: Le colonne che restano identiche in entrambe le righe.
ACCOMPAGNANO: Final[tuple[str, ...]] = ("match_id", "data", "giornata")


def a_righe(partite: pd.DataFrame) -> pd.DataFrame:
    """Trasforma le partite in due righe ciascuna, una per squadra.

    E' il passaggio che rende tutto il resto una semplice aggregazione: finche'
    una partita e' una riga con «casa» e «ospite», ogni conteggio per squadra
    richiede di trattare i due casi separatamente e di ricordarsene ogni volta.

    Args:
        partite: Le partite, con ``casa``, ``ospite``, ``gol_casa``,
            ``gol_ospite``.

    Returns:
        Una tabella con ``squadra``, ``avversario``, ``gol_fatti``,
        ``gol_subiti``, ``in_casa`` e ``punti``.
    """
    base = ["squadra", "avversario", "gol_fatti", "gol_subiti", "in_casa"]
    if partite.empty:
        return pd.DataFrame(columns=[*base, "punti"])

    presenti = [coppia for coppia in COPPIE if coppia[0] in partite.columns]
    accompagnano = [nome for nome in ACCOMPAGNANO if nome in partite.columns]
    tenute = [nome for _, _, nome, _ in presenti]
    tenute += [nome for _, _, _, nome in presenti] + accompagnano

    casa = partite.rename(
        columns={dal_casa: fatto for dal_casa, _, fatto, _ in presenti}
        | {dal_fuori: subito for _, dal_fuori, _, subito in presenti}
    ).assign(in_casa=True)
    fuori = partite.rename(
        columns={dal_fuori: fatto for _, dal_fuori, fatto, _ in presenti}
        | {dal_casa: subito for dal_casa, _, _, subito in presenti}
    ).assign(in_casa=False)

    tenute = [*tenute, "in_casa"]
    righe = pd.concat([casa[tenute], fuori[tenute]], ignore_index=True)
    vinte = righe["gol_fatti"] > righe["gol_subiti"]
    pari = righe["gol_fatti"] == righe["gol_subiti"]
    righe["punti"] = vinte * PUNTI_VITTORIA + pari * PUNTI_PAREGGIO
    return righe


def classifica(partite: pd.DataFrame) -> pd.DataFrame:
    """La classifica di una competizione.

    Args:
        partite: Le partite della selezione.

    Returns:
        Una riga per squadra con giocate, vinte, pari, perse, gol fatti e
        subiti, differenza e punti, ordinata secondo :data:`ORDINE`.
    """
    righe = a_righe(partite)
    if righe.empty:
        return pd.DataFrame(
            columns=[
                "squadra",
                "giocate",
                "vinte",
                "pari",
                "perse",
                "gol_fatti",
                "gol_subiti",
                "differenza",
                "punti",
            ]
        )

    righe = righe.assign(
        vinte=righe["gol_fatti"] > righe["gol_subiti"],
        pari=righe["gol_fatti"] == righe["gol_subiti"],
        perse=righe["gol_fatti"] < righe["gol_subiti"],
    )
    tabella = (
        righe.groupby("squadra", observed=True)
        .agg(
            giocate=("punti", "size"),
            vinte=("vinte", "sum"),
            pari=("pari", "sum"),
            perse=("perse", "sum"),
            gol_fatti=("gol_fatti", "sum"),
            gol_subiti=("gol_subiti", "sum"),
            punti=("punti", "sum"),
        )
        .reset_index()
    )
    tabella["differenza"] = tabella["gol_fatti"] - tabella["gol_subiti"]
    return tabella.sort_values(list(ORDINE), ascending=False, ignore_index=True)


def xg_per_squadra(tiri: pd.DataFrame) -> pd.DataFrame:
    """Gli xG creati e concessi da ogni squadra.

    **Gli xG concessi si leggono dalla colonna ``avversario``**, cioe' dai tiri
    che gli altri hanno tirato contro. Non esiste una tabella dei tiri subiti:
    e' lo stesso tiro guardato dall'altra parte.

    I rigori delle serie finali sono esclusi da :func:`panoramica.tiri_di_gioco`
    — cinque rigori a 0,76 di xG ciascuno gonfierebbero una finale di quasi
    quattro gol attesi che non appartengono alla partita.

    Args:
        tiri: I tiri della selezione.

    Returns:
        Una riga per squadra con ``xg_fatti``, ``xg_subiti``, ``tiri_fatti`` e
        ``tiri_subiti``.
    """
    colonne = ["squadra", "xg_fatti", "xg_subiti", "tiri_fatti", "tiri_subiti"]
    giocati = tiri_di_gioco(tiri)
    if giocati.empty:
        return pd.DataFrame(columns=colonne)

    per_tiratore = giocati.groupby("squadra", observed=True)["xg_statsbomb"]
    per_bersaglio = giocati.groupby("avversario", observed=True)["xg_statsbomb"]
    fatti = pd.DataFrame({"xg_fatti": per_tiratore.sum(), "tiri_fatti": per_tiratore.size()})
    subiti = pd.DataFrame({"xg_subiti": per_bersaglio.sum(), "tiri_subiti": per_bersaglio.size()})
    subiti.index.name = "squadra"
    unite = fatti.join(subiti, how="outer").fillna(0.0).reset_index()
    unite[["tiri_fatti", "tiri_subiti"]] = unite[["tiri_fatti", "tiri_subiti"]].astype(int)
    return unite[colonne]


def tabella(partite: pd.DataFrame, tiri: pd.DataFrame) -> pd.DataFrame:
    """La classifica con accanto le colonne dell'xG.

    E' la vista che il progetto puo' offrire e una classifica normale no:
    ``scarto_xg`` dice di quanti gol una squadra ha superato le proprie
    occasioni, e ``differenza_xg`` quanto ha dominato al netto della
    realizzazione.

    Args:
        partite: Le partite della selezione.
        tiri: I tiri della selezione.

    Returns:
        La classifica con ``xg_fatti``, ``xg_subiti``, ``differenza_xg`` e
        ``scarto_xg``. Le squadre senza tiri restano in tabella con zeri.
    """
    punti = classifica(partite)
    if punti.empty:
        return punti

    unite = punti.merge(xg_per_squadra(tiri), on="squadra", how="left")
    numeriche = ["xg_fatti", "xg_subiti", "tiri_fatti", "tiri_subiti"]
    unite[numeriche] = unite[numeriche].fillna(0.0)
    unite["differenza_xg"] = unite["xg_fatti"] - unite["xg_subiti"]
    unite["scarto_xg"] = unite["gol_fatti"] - unite["xg_fatti"]
    return unite


def ha_classifica(partite: pd.DataFrame) -> bool:
    """Se per questa selezione una classifica abbia senso.

    Un girone all'italiana ha una classifica; un torneo a eliminazione diretta
    no, e sommare i punti delle diciotto finali di Champions dal 1971 al 2019
    darebbe una tabella dall'aria autorevole e senza alcun significato.

    **Il criterio e' il gruppo, non la giornata.** La prima stesura guardava se
    la colonna ``giornata`` fosse piena, e le finali passavano: hanno una
    giornata anche loro, perche' StatsBomb numera i turni pure nei tabelloni.
    ``Gruppo.CAMPIONATO`` e' la classificazione del progetto, gia' verificata
    altrove, e dice esattamente la cosa che serve qui.

    Args:
        partite: Le partite della selezione.

    Returns:
        Vero se tutte le partite appartengono a un campionato.
    """
    if partite.empty or "gruppo" not in partite.columns:
        return False
    gruppi = {str(valore) for valore in partite["gruppo"].unique()}
    return gruppi == {str(Gruppo.CAMPIONATO)}


def incomplete(tavola: pd.DataFrame) -> Sequence[str]:
    """Le squadre che hanno giocato meno partite delle altre.

    Serve a dichiarare i buchi invece di nasconderli: nella Ligue 1 2015/16
    mancano tre partite dall'Open Data, sei squadre ne hanno 37 invece di 38 e
    il PSG risulta a 93 punti invece dei 96 veri.

    Args:
        tavola: Il risultato di :func:`classifica` o :func:`tabella`.

    Returns:
        I nomi delle squadre con meno partite del massimo, in ordine.
    """
    if tavola.empty:
        return []
    massimo = int(tavola["giocate"].max())
    mancanti = tavola.loc[tavola["giocate"] < massimo, "squadra"]
    return sorted(str(nome) for nome in mancanti)


def scheda(tavola: pd.DataFrame, squadra: str) -> dict[str, float]:
    """I numeri di una singola squadra, presi dalla tabella gia' calcolata.

    Legge dalla tabella invece di ricalcolare: cosi' la scheda e la riga della
    classifica non possono dire due cose diverse, che e' esattamente il difetto
    che nasce quando due funzioni calcolano lo stesso numero per strade
    diverse.

    Args:
        tavola: Il risultato di :func:`tabella`.
        squadra: Il nome della squadra.

    Returns:
        I valori della scheda, piu' ``posizione``. Vuoto se la squadra non c'e'.
    """
    trovata = tavola.index[tavola["squadra"] == squadra]
    if len(trovata) == 0:
        return {}
    riga = tavola.loc[trovata[0]]
    giocate = float(riga["giocate"]) or 1.0
    tiri = float(riga.get("tiri_fatti", 0.0))
    subiti = float(riga.get("tiri_subiti", 0.0))
    return {
        "posizione": float(trovata[0] + 1),
        "punti": float(riga.get("punti", 0.0)),
        "giocate": float(riga["giocate"]),
        "vinte": float(riga.get("vinte", 0.0)),
        "pari": float(riga.get("pari", 0.0)),
        "perse": float(riga.get("perse", 0.0)),
        "gol_fatti": float(riga["gol_fatti"]),
        "xg_fatti": float(riga["xg_fatti"]),
        "gol_subiti": float(riga["gol_subiti"]),
        "xg_subiti": float(riga["xg_subiti"]),
        "differenza": float(riga.get("differenza", 0.0)),
        "tiri_fatti": tiri,
        "tiri_subiti": subiti,
        "tiri_per_partita": tiri / giocate,
        "tiri_subiti_per_partita": subiti / giocate,
        # La conversione e' gol su tiri, e i tiri sono quelli **su azione**:
        # `xg_per_squadra` scarta i rigori dei tiebreak, quindi il denominatore
        # non gonfia con i tiri dal dischetto delle lotterie finali.
        "conversione": float(riga["gol_fatti"]) / tiri if tiri else 0.0,
        "xg_per_tiro": float(riga["xg_fatti"]) / tiri if tiri else 0.0,
        "xg_per_partita": float(riga["xg_fatti"]) / giocate,
        "scarto_xg": float(riga["scarto_xg"]),
    }


def andamento_squadra(partite: pd.DataFrame, squadra: str) -> pd.DataFrame:
    """Gol e xG di una squadra, cumulati partita dopo partita.

    **La somma cumulata e non il valore di giornata.** Su una singola partita
    gol e xG ballano di due o tre reti e il grafico diventa un pettine; la
    curva cumulata mostra invece se lo scarto e' un episodio o una tendenza
    che dura tutta la stagione — che e' la domanda a cui l'xG serve.

    Args:
        partite: Le partite della selezione.
        squadra: Il nome della squadra.

    Returns:
        Una riga per partita, in ordine di data, con ``gol`` e ``xg`` cumulati.
    """
    colonne = ["data", "gol", "xg"]
    righe = a_righe(partite)
    if righe.empty or "xg_fatti" not in righe.columns:
        return pd.DataFrame(columns=colonne)

    sue = righe[righe["squadra"] == squadra]
    if sue.empty:
        return pd.DataFrame(columns=colonne)

    ordinate = sue.sort_values("data")
    return pd.DataFrame(
        {
            "data": pd.to_datetime(ordinate["data"]).to_numpy(),
            "gol": ordinate["gol_fatti"].cumsum().to_numpy(),
            "xg": ordinate["xg_fatti"].cumsum().to_numpy(),
        }
    )
