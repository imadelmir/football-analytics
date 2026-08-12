"""Strato 3, seconda parte: addestramento e valutazione del modello xG.

**La divisione train/test si fa per partita, non per tiro.** E' la regola che
decide se i numeri di questo progetto valgono qualcosa, e il modo piu' comune
di sbagliare senza accorgersene.

I tiri della stessa partita si somigliano: stesso campo, stesse due squadre,
stesso arbitro, stessa serata, spesso le stesse azioni ripetute. Se meta'
finiscono in addestramento e meta' in verifica, il modello ha gia' visto
qualcosa di quella partita quando la valuta, e il punteggio che ottiene e'
migliore di quello che otterrebbe su una partita mai vista. Il modello sembra
buono e non lo e'.

Il difetto e' invisibile: nessun errore, nessun avviso, solo metriche
lusinghiere. Si scopre quando il modello incontra dati veri — o quando in un
colloquio qualcuno chiede «come hai diviso i dati?».
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, cast

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from football_analytics.config import MODELS_DIR, SEED

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import numpy.typing as npt
    import pandas as pd

#: Quota di partite che finisce nell'insieme di verifica.
QUOTA_TEST: Final[float] = 0.2

#: La colonna che identifica il gruppo da non spezzare.
COLONNA_GRUPPO: Final[str] = "match_id"

#: La colonna da prevedere.
BERSAGLIO: Final[str] = "gol"

#: I nomi con cui i modelli vengono salvati in ``models/``.
NOME_BASE: Final[str] = "xg_base"
NOME_SPAZIALE: Final[str] = "xg_360"


def partite_di_verifica(
    dati: pd.DataFrame, quota_test: float = QUOTA_TEST, seed: int = SEED
) -> set[int]:
    """Sceglie quali partite finiscono nell'insieme di verifica.

    L'elenco delle partite viene **ordinato** prima di essere mescolato: senza,
    il risultato dipenderebbe dall'ordine in cui pandas restituisce i valori
    unici, e due esecuzioni sugli stessi dati potrebbero dare divisioni diverse.

    Args:
        dati: Le righe da dividere, con la colonna ``match_id``.
        quota_test: Frazione delle partite da destinare alla verifica.
        seed: Radice del generatore, per rendere la divisione riproducibile.

    Returns:
        Gli identificativi delle partite di verifica.
    """
    partite = np.array(sorted(dati[COLONNA_GRUPPO].unique()))
    generatore = np.random.default_rng(seed)
    generatore.shuffle(partite)
    quante = round(len(partite) * quota_test)
    return {int(p) for p in partite[:quante]}


def dividi_per_partita(
    dati: pd.DataFrame, quota_test: float = QUOTA_TEST, seed: int = SEED
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide i tiri in addestramento e verifica **senza spezzare le partite**.

    Args:
        dati: Le righe da dividere, con la colonna ``match_id``.
        quota_test: Frazione delle partite da destinare alla verifica.
        seed: Radice del generatore.

    Returns:
        Addestramento e verifica, nell'ordine. Nessuna partita compare in
        entrambi.
    """
    verifica = partite_di_verifica(dati, quota_test, seed)
    in_verifica = dati[COLONNA_GRUPPO].isin(verifica)
    return dati[~in_verifica].copy(), dati[in_verifica].copy()


def costruisci_preprocessore(
    numeriche: Sequence[str], categoriche: Sequence[str], booleane: Sequence[str]
) -> ColumnTransformer:
    """Prepara le variabili per un modello lineare.

    Le numeriche vengono standardizzate — non per il risultato, che una
    regressione logistica darebbe uguale, ma perche' l'ottimizzatore converge
    molto piu' in fretta quando le scale sono confrontabili: la distanza arriva
    a 100, l'angolo sta sotto 3,15.

    Le categoriche diventano indicatori binari, con ``handle_unknown="ignore"``
    perche' una categoria vista solo in verifica non deve far fallire la
    previsione: succede con gli schemi di gioco rari.

    Args:
        numeriche: Le colonne continue.
        categoriche: Le colonne a categorie.
        booleane: Le colonne gia' binarie, che passano intatte.

    Returns:
        Il trasformatore, pronto per entrare in una pipeline.
    """
    return ColumnTransformer(
        [
            ("numeriche", StandardScaler(), list(numeriche)),
            (
                "categoriche",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(categoriche),
            ),
            ("booleane", "passthrough", list(booleane)),
        ],
        remainder="drop",
    )


def pipeline_logistica(
    numeriche: Sequence[str],
    categoriche: Sequence[str],
    booleane: Sequence[str],
    seed: int = SEED,
) -> Pipeline:
    """Costruisce il modello base: preprocessore piu' regressione logistica.

    **Senza ``class_weight="balanced"``, ed e' una scelta deliberata.** Con un
    gol ogni dieci tiri la tentazione di bilanciare le classi e' forte, e su un
    problema di classificazione sarebbe ragionevole. Qui no: bilanciare i pesi
    gonfia le probabilita' previste verso il 50 % e **distrugge la
    calibrazione**, che e' l'unica cosa che un modello xG deve avere. Un xG che
    dice 0,5 dove la realta' e' 0,1 non serve a niente, per quanto bene ordini
    i tiri.

    Args:
        numeriche: Le colonne continue.
        categoriche: Le colonne a categorie.
        booleane: Le colonne binarie.
        seed: Radice del generatore, per la riproducibilita'.

    Returns:
        La pipeline non ancora addestrata.
    """
    return Pipeline(
        [
            ("preparazione", costruisci_preprocessore(numeriche, categoriche, booleane)),
            (
                "modello",
                LogisticRegression(max_iter=1000, random_state=seed),
            ),
        ]
    )


def addestra(modello: Pipeline, dati: pd.DataFrame, variabili: Sequence[str]) -> Pipeline:
    """Addestra un modello sulle variabili indicate.

    Args:
        modello: La pipeline da addestrare.
        dati: Le righe di addestramento, con la colonna ``gol``.
        variabili: Le colonne da usare come predittori.

    Returns:
        Lo stesso modello, addestrato.
    """
    modello.fit(dati[list(variabili)], dati[BERSAGLIO])
    return modello


def previsioni(
    modello: Pipeline, dati: pd.DataFrame, variabili: Sequence[str]
) -> npt.NDArray[np.float64]:
    """Calcola la probabilita' di gol prevista per ogni tiro.

    Args:
        modello: Il modello addestrato.
        dati: Le righe da valutare.
        variabili: Le colonne usate come predittori.

    Returns:
        Le probabilita' della classe positiva, una per riga.
    """
    probabilita: npt.NDArray[np.float64] = modello.predict_proba(dati[list(variabili)])[:, 1]
    return probabilita


def percorso_modello(nome: str) -> Path:
    """Percorso del file in cui un modello viene salvato.

    Args:
        nome: Il nome logico del modello.

    Returns:
        Il percorso di ``models/<nome>.pkl``.
    """
    return MODELS_DIR / f"{nome}.pkl"


def salva_modello(modello: Pipeline, nome: str) -> Path:
    """Scrive un modello addestrato su disco.

    Args:
        modello: La pipeline addestrata.
        nome: Il nome logico con cui salvarla.

    Returns:
        Il percorso del file scritto.
    """
    percorso = percorso_modello(nome)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modello, percorso)
    return percorso


def carica_modello(nome: str) -> Pipeline:
    """Rilegge un modello salvato.

    Args:
        nome: Il nome logico del modello.

    Returns:
        La pipeline addestrata.
    """
    return cast("Pipeline", joblib.load(percorso_modello(nome)))


def riepilogo_divisione(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, float]:
    """Descrive una divisione, per poterla dichiarare invece che assumerla.

    Args:
        train: L'insieme di addestramento.
        test: L'insieme di verifica.

    Returns:
        Conteggi e frequenza dei gol nei due insiemi. La frequenza serve a
        controllare che la divisione non abbia sbilanciato la classe positiva:
        con un gol ogni dieci tiri, una divisione sfortunata puo' produrre due
        insiemi che non si somigliano.
    """
    return {
        "tiri_train": float(len(train)),
        "tiri_test": float(len(test)),
        "partite_train": float(train[COLONNA_GRUPPO].nunique()),
        "partite_test": float(test[COLONNA_GRUPPO].nunique()),
        "quota_test": float(len(test) / (len(train) + len(test)))
        if len(train) + len(test)
        else 0.0,
        "gol_train": float(train["gol"].mean()) if len(train) else 0.0,
        "gol_test": float(test["gol"].mean()) if len(test) else 0.0,
    }
