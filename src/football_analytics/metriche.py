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
        "log_loss_riferimento": base["log_loss"],
        "brier_riferimento": base["brier"],
        "guadagno_log_loss": 0.0,
        "guadagno_brier": 0.0,
    }


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
