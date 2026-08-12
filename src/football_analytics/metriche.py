"""Le metriche con cui si giudica un modello xG.

**L'accuratezza non compare in questo modulo, e non e' una dimenticanza.** Su
43.000 tiri se ne segnano il 9,5 %: un modello che risponde «no» a ogni tiro e'
accurato al 90,5 % ed e' completamente inutile. C'e' un test che lo dimostra
invece di limitarsi a dirlo.

Le tre metriche usate misurano cose diverse e servono tutte:

- **Log loss** punisce le previsioni sicure e sbagliate in modo sproporzionato.
  E' la piu' severa e la piu' difficile da barare.
- **Brier score** e' l'errore quadratico medio sulle probabilita'. Si legge
  bene perche' ha una formula chiusa per il riferimento.
- **AUC** dice se il modello *ordina* bene i tiri. Non dice niente su quanto
  siano giuste le probabilita': un modello puo' avere AUC ottima e numeri
  inventati, ed e' esattamente cosa succede con ``class_weight="balanced"``.
  C'e' un test anche per questo.

**Ogni metrica va accompagnata dal punteggio del modello piu' stupido
possibile.** Un Brier score di 0,074 non vuol dire niente finche' non si sa che
rispondere sempre «0,0951» ne ottiene 0,086. Su un evento raro il modello
stupido e' bravissimo, perche' dire «quasi mai» e' quasi sempre giusto: senza
quel confronto ogni punteggio sembra buono.

Il riferimento e' calcolato qui da :func:`riferimento`, non scritto a mano da
nessuna parte. E' successo una volta di stimarlo a mente e di sbagliarlo di
tre millesimi scrivendolo con cinque decimali — il racconto e' in ``NOTES.md``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

if TYPE_CHECKING:
    from collections.abc import Mapping

    import numpy.typing as npt

#: Le due classi possibili, dichiarate per evitare che ``log_loss`` le deduca
#: dai dati: su una piega sfortunata potrebbe vederne una sola e sbagliare.
ETICHETTE: Final[list[bool]] = [False, True]


def riferimento(reali: npt.ArrayLike) -> dict[str, float]:
    r"""Il punteggio di chi risponde sempre la frequenza media dei gol.

    E' il modello piu' stupido che si possa scrivere e resta sorprendentemente
    difficile da battere su un evento raro. Serve come zero della scala: senza,
    un Brier score e' un numero senza unita' di misura.

    Entrambe le formule sono chiuse, quindi esatte e non stimate. Per il Brier:

    .. math:: \\frac{1}{n}\\sum (p - y)^2 = p^2(1-p) + (1-p)^2 p = p(1-p)

    Args:
        reali: Gli esiti veri, uno per tiro.

    Returns:
        ``log_loss``, ``brier`` e ``auc`` del modello di riferimento. L'AUC e'
        0,5 per definizione: una previsione costante non ordina niente.

    Raises:
        ValueError: Se tutti i tiri hanno lo stesso esito. In quel caso il
            riferimento non e' definito — il Brier varrebbe zero e il
            miglioramento relativo sarebbe una divisione per zero.
    """
    esiti = np.asarray(reali, dtype=bool)
    p = float(esiti.mean()) if esiti.size else 0.0
    if not 0.0 < p < 1.0:
        msg = (
            "Il riferimento non e' definito se tutti i tiri hanno lo stesso esito: "
            f"frequenza dei gol {p}, su {esiti.size} tiri."
        )
        raise ValueError(msg)
    return {
        "log_loss": -(p * math.log(p) + (1.0 - p) * math.log1p(-p)),
        "brier": p * (1.0 - p),
        "auc": 0.5,
    }


def metriche(reali: npt.ArrayLike, previste: npt.ArrayLike) -> dict[str, float]:
    """Valuta un insieme di previsioni contro gli esiti veri.

    Args:
        reali: Gli esiti veri, uno per tiro.
        previste: Le probabilita' previste, una per tiro.

    Returns:
        Le tre metriche, i due numeri della calibrazione, il punteggio del
        riferimento e il miglioramento su di esso. ``guadagno_brier`` e
        ``guadagno_log_loss`` valgono 0 per un modello che non ha imparato
        niente, 1 per uno perfetto, e **possono essere negativi**: un modello
        puo' fare peggio del non sapere.

    Raises:
        ValueError: Se le due sequenze hanno lunghezza diversa.
    """
    esiti = np.asarray(reali, dtype=bool)
    stime = np.asarray(previste, dtype=np.float64)
    if esiti.shape != stime.shape:
        msg = f"Esiti e previsioni hanno forme diverse: {esiti.shape} contro {stime.shape}."
        raise ValueError(msg)

    base = riferimento(esiti)
    brier = float(brier_score_loss(esiti, stime))
    perdita = float(log_loss(esiti, stime, labels=ETICHETTE))

    return {
        "log_loss": perdita,
        "brier": brier,
        "auc": float(roc_auc_score(esiti, stime)),
        "xg_medio": float(stime.mean()),
        "gol_reali": float(esiti.mean()),
        "scarto_calibrazione": float(stime.mean() - esiti.mean()),
        "errore_calibrazione": errore_di_calibrazione(esiti, stime),
        "log_loss_riferimento": base["log_loss"],
        "brier_riferimento": base["brier"],
        "guadagno_log_loss": 1.0 - perdita / base["log_loss"],
        "guadagno_brier": 1.0 - brier / base["brier"],
    }


def tabella(punteggi: Mapping[str, Mapping[str, float]]) -> str:
    """Formatta piu' modelli in una tabella allineata e confrontabile.

    La colonna del guadagno c'e' perche' e' l'unica leggibile senza contesto:
    dice quanta parte dell'errore del riferimento il modello ha tolto.

    Args:
        punteggi: Nome del modello, e il dizionario restituito da
            :func:`metriche`.

    Returns:
        La tabella pronta da stampare.
    """
    larghezza = max((len(nome) for nome in punteggi), default=0)
    righe = [
        f"{'modello':<{larghezza}}{'log loss':>11}{'Brier':>10}{'AUC':>9}"
        f"{'guadagno':>11}{'xG medio':>11}"
    ]
    for nome, m in punteggi.items():
        righe.append(
            f"{nome:<{larghezza}}{m['log_loss']:>11.5f}{m['brier']:>10.5f}"
            f"{m['auc']:>9.4f}{m['guadagno_brier'] * 100:>10.1f}%{m['xg_medio']:>11.4f}"
        )
    return "\n".join(righe)


def riga_riferimento(reali: npt.ArrayLike) -> dict[str, float]:
    """Il riferimento nel formato di :func:`metriche`, per entrare in tabella.

    Args:
        reali: Gli esiti veri, uno per tiro.

    Returns:
        Lo stesso dizionario di :func:`metriche`, con guadagno nullo.
    """
    esiti = np.asarray(reali, dtype=bool)
    base = riferimento(esiti)
    media = float(esiti.mean())
    return {
        "log_loss": base["log_loss"],
        "brier": base["brier"],
        "auc": base["auc"],
        "xg_medio": media,
        "gol_reali": media,
        "scarto_calibrazione": 0.0,
        "errore_calibrazione": 0.0,
        "log_loss_riferimento": base["log_loss"],
        "brier_riferimento": base["brier"],
        "guadagno_log_loss": 0.0,
        "guadagno_brier": 0.0,
    }


#: Quanti gruppi per la curva di calibrazione. Dieci e' la scelta abituale e
#: su 8.600 tiri lascia circa 860 righe per gruppo, abbastanza perche'
#: l'incertezza di ciascuno sia piccola rispetto agli scarti che interessano.
GRUPPI_CALIBRAZIONE: Final[int] = 10


def curva_di_calibrazione(
    reali: npt.ArrayLike, previste: npt.ArrayLike, gruppi: int = GRUPPI_CALIBRAZIONE
) -> pd.DataFrame:
    """Confronta xG previsto e gol osservati, gruppo per gruppo.

    Le metriche riassuntive dicono **quanto** un modello sbaglia; la curva di
    calibrazione dice **dove**. Due modelli con lo stesso Brier score possono
    sbagliare in modi opposti — uno gonfia le occasioni facili, l'altro schiaccia
    quelle difficili — e la media non lo mostra.

    **I gruppi sono quantili, non intervalli di ampiezza uguale.** Su un xG
    dove la mediana e' 0,05 e la coda arriva a 0,9, dieci intervalli larghi
    0,1 metterebbero oltre il 90 % dei tiri nel primo e lascerebbero gli altri
    con una manciata di righe ciascuno: la curva risulterebbe piatta dove ci
    sono i dati e rumorosa dove non ce ne sono. Con i quantili ogni gruppo ha
    lo stesso numero di tiri, quindi la stessa incertezza. C'e' un test che
    misura quanto sarebbe degenere l'alternativa.

    La colonna ``scarto_in_se`` esprime la distanza fra previsto e osservato in
    **errori standard**, non in punti: uno scarto di due punti percentuali su un
    gruppo da 100 tiri e' rumore, su un gruppo da 5.000 e' un difetto. Senza
    quella normalizzazione una curva si legge a occhio e si conclude quello che
    si vuole.

    Args:
        reali: Gli esiti veri, uno per tiro.
        previste: Le probabilita' previste, una per tiro.
        gruppi: In quanti quantili dividere le previsioni.

    Returns:
        Una riga per gruppo, con conteggio, xG medio previsto, frequenza dei gol
        osservata, errore standard di quest'ultima e scarto in errori standard.
    """
    tabella = pd.DataFrame(
        {
            "gol": np.asarray(reali, dtype=bool),
            "xg": np.asarray(previste, dtype=np.float64),
        }
    )
    etichette = pd.qcut(tabella["xg"], gruppi, labels=False, duplicates="drop")
    if etichette.isna().all():
        # Tutte le previsioni sono identiche, quindi non ci sono quantili da
        # tagliare: `qcut` restituisce solo NaN e il raggruppamento resterebbe
        # vuoto. Il caso non e' patologico — e' il modello di riferimento, che
        # risponde sempre la frequenza media — e la risposta giusta e' un gruppo
        # solo con dentro tutto.
        etichette = pd.Series(0, index=tabella.index)
    tabella["gruppo"] = etichette.astype("int64")

    curva = (
        tabella.groupby("gruppo", observed=True)
        .agg(tiri=("gol", "size"), xg_previsto=("xg", "mean"), gol_osservati=("gol", "mean"))
        .reset_index()
    )
    osservati = curva["gol_osservati"].to_numpy()
    curva["errore_standard"] = np.sqrt(osservati * (1.0 - osservati) / curva["tiri"].to_numpy())
    scarto = curva["xg_previsto"].to_numpy() - osservati
    curva["scarto"] = scarto
    with np.errstate(divide="ignore", invalid="ignore"):
        curva["scarto_in_se"] = np.where(
            curva["errore_standard"].to_numpy() > 0.0,
            scarto / curva["errore_standard"].to_numpy(),
            np.nan,
        )
    return curva


def errore_di_calibrazione(
    reali: npt.ArrayLike, previste: npt.ArrayLike, gruppi: int = GRUPPI_CALIBRAZIONE
) -> float:
    """Riassume la curva di calibrazione in un numero solo.

    E' la media degli scarti **assoluti** fra previsto e osservato, pesata per
    quanti tiri cadono in ciascun gruppo. Serve accanto allo
    ``scarto_calibrazione`` di :func:`metriche`, che e' una media **con segno** e
    vale zero anche per un modello che sovrastima le occasioni facili
    esattamente quanto sottostima quelle difficili.

    Args:
        reali: Gli esiti veri, uno per tiro.
        previste: Le probabilita' previste, una per tiro.
        gruppi: In quanti quantili dividere le previsioni.

    Returns:
        L'errore di calibrazione atteso. Zero e' perfetto.
    """
    curva = curva_di_calibrazione(reali, previste, gruppi)
    pesi = curva["tiri"].to_numpy()
    return float(np.average(np.abs(curva["scarto"].to_numpy()), weights=pesi))


def accordo(nostro: npt.ArrayLike, altrui: npt.ArrayLike) -> dict[str, float]:
    """Misura **quanto due modelli xG si somigliano**, non quale sia migliore.

    E' una domanda diversa da quella di :func:`metriche`. Un modello puo' essere
    peggiore e somigliante, o migliore e diverso: sapere quale dei due casi si
    ha in mano cambia cosa si puo' dire nella pagina di metodologia.

    La correlazione di Spearman e' calcolata come Pearson sui **ranghi**, che e'
    la sua definizione. Farlo a mano evita di aggiungere SciPy alle dipendenze
    per due righe, su un progetto che deve stare sotto il gigabyte di RAM.

    **``scarto_assoluto_medio`` va letto con cautela.** Uno scarto grande e'
    possibile solo dove l'xG e' grande, e l'xG e' grande sotto porta: la
    quantita' cresce con il livello anche quando l'accordo relativo e' identico.
    Per questo c'e' anche ``scarto_relativo_mediano``, che divide per la media
    dei due valori.

    Args:
        nostro: Le probabilita' previste dal modello del progetto.
        altrui: Le probabilita' del modello di confronto, sugli stessi tiri.

    Returns:
        Correlazioni e scarti. ``scarto_medio`` ha segno: positivo vuol dire che
        il nostro modello assegna piu' xG.

    Raises:
        ValueError: Se le due sequenze hanno lunghezza diversa.
    """
    a = np.asarray(nostro, dtype=np.float64)
    b = np.asarray(altrui, dtype=np.float64)
    if a.shape != b.shape:
        msg = f"Le due serie hanno forme diverse: {a.shape} contro {b.shape}."
        raise ValueError(msg)

    differenza = a - b
    media_coppia = (a + b) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        relativo = np.where(media_coppia > 0.0, np.abs(differenza) / media_coppia, np.nan)

    return {
        "pearson": float(np.corrcoef(a, b)[0, 1]),
        "spearman": float(
            np.corrcoef(pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy())[0, 1]
        ),
        "scarto_medio": float(differenza.mean()),
        "scarto_assoluto_medio": float(np.abs(differenza).mean()),
        "scarto_assoluto_mediano": float(np.median(np.abs(differenza))),
        "scarto_relativo_mediano": float(np.nanmedian(relativo)),
        "xg_totale_nostro": float(a.sum()),
        "xg_totale_altrui": float(b.sum()),
    }


def accordo_aggregato(
    nostro: npt.ArrayLike, altrui: npt.ArrayLike, gruppi: npt.ArrayLike
) -> dict[str, float]:
    """L'accordo dopo aver sommato l'xG dentro ogni gruppo, di solito la partita.

    E' la misura che conta per la dashboard: nessuno guarda l'xG di un singolo
    tiro, si guarda quello di una partita o di un giocatore. Due modelli
    possono discordare parecchio tiro per tiro e concordare bene sui totali,
    perche' gli scarti con segno opposto si compensano.

    Args:
        nostro: Le probabilita' del modello del progetto.
        altrui: Le probabilita' del modello di confronto.
        gruppi: L'identificativo del gruppo di ciascun tiro, per esempio
            ``match_id``.

    Returns:
        Le stesse chiavi di :func:`accordo`, calcolate sui totali di gruppo,
        piu' ``gruppi`` con quanti ne sono stati formati.
    """
    tabella = pd.DataFrame(
        {
            "gruppo": np.asarray(gruppi),
            "nostro": np.asarray(nostro, dtype=np.float64),
            "altrui": np.asarray(altrui, dtype=np.float64),
        }
    )
    somme = tabella.groupby("gruppo", observed=True)[["nostro", "altrui"]].sum()
    risultato = accordo(somme["nostro"].to_numpy(), somme["altrui"].to_numpy())
    risultato["gruppi"] = float(len(somme))
    return risultato


def confronta(
    reali: npt.ArrayLike, previsioni_per_modello: Mapping[str, npt.ArrayLike]
) -> dict[str, dict[str, float]]:
    """Valuta piu' modelli sugli stessi esiti, con il riferimento in testa.

    Args:
        reali: Gli esiti veri, uno per tiro.
        previsioni_per_modello: Nome del modello, e le sue previsioni.

    Returns:
        Un dizionario pronto per :func:`tabella`, con ``riferimento`` come
        prima voce.
    """
    risultati: dict[str, dict[str, float]] = {"riferimento": riga_riferimento(reali)}
    for nome, stime in previsioni_per_modello.items():
        risultati[nome] = metriche(reali, stime)
    return risultati
