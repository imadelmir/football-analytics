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

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from football_analytics import __version__
from football_analytics.config import MODELS_DIR, SEED
from football_analytics.metriche import ETICHETTE

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    import numpy.typing as npt

#: Quota di partite che finisce nell'insieme di verifica.
QUOTA_TEST: Final[float] = 0.2

#: La colonna che identifica il gruppo da non spezzare.
COLONNA_GRUPPO: Final[str] = "match_id"

#: La colonna da prevedere.
BERSAGLIO: Final[str] = "gol"

#: I nomi con cui i modelli vengono salvati in ``models/``.
#:
#: ``xg_logistica`` e' il riferimento di M5-T4: resta salvato perche' i numeri
#: di un confronto vanno riproducibili, non ricordati. ``xg_base`` e
#: ``xg_360`` sono i due modelli che la dashboard usa davvero.
NOME_LOGISTICA: Final[str] = "xg_logistica"
NOME_BASE: Final[str] = "xg_base"
NOME_SPAZIALE: Final[str] = "xg_360"

#: Pieghe della validazione incrociata, sempre raggruppate per partita.
PIEGHE: Final[int] = 5


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


@dataclass(frozen=True, slots=True)
class Iperparametri:
    """Gli iperparametri del gradient boosting.

    Stanno insieme in una classe invece che sparsi come argomenti perche'
    vanno **scelti insieme** — abbassare il tasso senza alzare le iterazioni
    produce un modello che non ha finito di imparare — e perche' cosi' la
    combinazione usata si puo' salvare, confrontare e citare in una relazione.

    I valori predefiniti sono prudenti di proposito: tasso basso e molte
    iterazioni imparano piu' lentamente ma piu' stabilmente, e su 34.000 righe
    costa qualche secondo.

    Attributes:
        iterazioni: Quanti alberi costruire.
        tasso: Quanto pesa ogni albero. Piu' basso, piu' alberi servono.
        foglie: Larghezza massima di un albero.
        minimo_per_foglia: Quanti tiri servono per giustificare una foglia.
            Con un gol ogni dieci tiri, una foglia da 20 righe puo' contenere
            zero gol per puro caso.
        regolarizzazione: Penalita' L2 sui valori delle foglie.
    """

    iterazioni: int = 300
    tasso: float = 0.05
    foglie: int = 31
    minimo_per_foglia: int = 40
    regolarizzazione: float = 1.0


def pipeline_alberi(
    numeriche: Sequence[str],
    categoriche: Sequence[str],
    booleane: Sequence[str],
    iper: Iperparametri | None = None,
    seed: int = SEED,
) -> Pipeline:
    """Costruisce il modello ad alberi: gradient boosting a istogrammi.

    **Usa lo stesso preprocessore della regressione logistica, di proposito.**
    Per un albero standardizzare e' inutile — un taglio su ``x > 18`` e uno su
    ``x > 1,4`` dopo la standardizzazione separano le stesse righe, e le soglie
    di binning sono quantili, quindi invarianti per trasformazioni affini. E'
    tenuto perche' il confronto con M5-T4 deve cambiare **una cosa sola**: la
    classe di modello. Un preprocessore diverso renderebbe impossibile dire da
    dove viene la differenza.

    **``early_stopping=False`` e' deliberato.** L'arresto anticipato di
    scikit-learn ritaglia da solo un 10 % di validazione **a caso**, e finirebbe
    per mettere tiri della stessa partita da entrambe le parti: e' lo stesso
    difetto che abbiamo evitato al livello superiore, che rientra dalla finestra
    un piano piu' sotto. Non falserebbe la verifica finale, ma sceglierebbe male
    dove fermarsi. Il numero di iterazioni si sceglie con
    :func:`logloss_incrociato`, che raggruppa per partita.

    **Gli alberi a istogrammi trattano i valori mancanti da soli**, mandandoli
    dal lato che riduce di piu' l'errore. Conta a M5-T6: le variabili spaziali
    sono assenti dove non c'e' il fotogramma, e la regola del progetto e' che un
    dato mancante non si riempie mai di zeri. Qui non serve nemmeno riempirlo.

    Args:
        numeriche: Le colonne continue.
        categoriche: Le colonne a categorie.
        booleane: Le colonne binarie.
        iper: Gli iperparametri. Se assente, quelli predefiniti.
        seed: Radice del generatore, per la riproducibilita'.

    Returns:
        La pipeline non ancora addestrata.
    """
    scelti = iper if iper is not None else Iperparametri()
    return Pipeline(
        [
            ("preparazione", costruisci_preprocessore(numeriche, categoriche, booleane)),
            (
                "modello",
                HistGradientBoostingClassifier(
                    max_iter=scelti.iterazioni,
                    learning_rate=scelti.tasso,
                    max_leaf_nodes=scelti.foglie,
                    min_samples_leaf=scelti.minimo_per_foglia,
                    l2_regularization=scelti.regolarizzazione,
                    early_stopping=False,
                    random_state=seed,
                ),
            ),
        ]
    )


def logloss_incrociato(
    costruisci: Callable[[], Pipeline],
    dati: pd.DataFrame,
    variabili: Sequence[str],
    pieghe: int = PIEGHE,
) -> float:
    """Stima il log loss con validazione incrociata **raggruppata per partita**.

    Serve a scegliere gli iperparametri **senza mai guardare l'insieme di
    verifica**. Provare due configurazioni sul test e tenere la migliore
    significa usare il test per decidere: da quel momento non misura piu' come
    il modello si comporta su dati mai visti, perche' li ha visti attraverso la
    scelta.

    Prende una **funzione** che costruisce la pipeline, non una pipeline: ogni
    piega deve partire da un modello non addestrato, e riusare lo stesso oggetto
    lo addestrerebbe cinque volte di fila sugli stessi parametri gia' adattati.

    Args:
        costruisci: Funzione senza argomenti che restituisce una pipeline nuova.
        dati: Le righe di addestramento, con ``match_id`` e ``gol``.
        variabili: Le colonne da usare come predittori.
        pieghe: Quante pieghe. ``GroupKFold`` e' deterministico, quindi due
            esecuzioni sugli stessi dati danno lo stesso numero.

    Returns:
        Il log loss medio sulle pieghe. Piu' basso e' meglio.
    """
    gruppi = dati[COLONNA_GRUPPO].to_numpy()
    esiti = dati[BERSAGLIO].to_numpy()
    divisore = GroupKFold(n_splits=pieghe)

    punteggi: list[float] = []
    for indici_train, indici_prova in divisore.split(dati, esiti, gruppi):
        modello = addestra(costruisci(), dati.iloc[indici_train], variabili)
        stime = previsioni(modello, dati.iloc[indici_prova], variabili)
        punteggi.append(float(log_loss(esiti[indici_prova], stime, labels=ETICHETTE)))

    return float(np.mean(punteggi))


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


def coefficienti(modello: Pipeline) -> pd.DataFrame:
    """Legge i coefficienti di una regressione logistica, in due scale.

    **Una regressione logistica e' gia' la sua spiegazione.** Non serve una
    libreria di attribuzione per sapere cosa ha imparato: i coefficienti *sono*
    quello che ha imparato. E' il motivo per cui il piano di completamento
    chiede di provare questa strada prima di SHAP, e per cui qui SHAP non
    compare.

    Le due scale rispondono a due domande diverse:

    - ``odds_ratio_per_deviazione_standard`` risponde a «**quale variabile pesa
      di piu'**». Confronta variabili con unita' incompatibili — metri contro
      conteggi di giocatori — mettendole tutte sulla stessa scala.
    - ``odds_ratio_per_unita`` risponde a «**quanto cambia se aggiungo un
      difensore**». Si ottiene dividendo il coefficiente per la deviazione
      standard usata dallo standardizzatore, ed e' il numero che si puo'
      scrivere in una frase.

    **Tre avvertenze, tutte necessarie per non leggere male la tabella.**

    1. Le categorie sono codificate senza scartarne una, quindi i loro
       coefficienti sono identificati solo **a meno di una costante**: ha senso
       confrontare due categorie della stessa variabile fra loro, non leggere
       il valore assoluto di una sola.
    2. Un coefficiente vale «a parita' di tutto il resto». Distanza del tiro e
       distanza del portiere sono correlate, e tenerne una ferma muovendo
       l'altra descrive una situazione che sul campo non si presenta quasi mai.
    3. Il segno e' una direzione, non una causa. Il modello vede associazioni.

    Args:
        modello: Una pipeline addestrata con :func:`pipeline_logistica`.

    Returns:
        Una riga per variabile prodotta dal preprocessore, ordinata per peso
        decrescente.

    Raises:
        TypeError: Se il modello finale non ha coefficienti, come un gradient
            boosting. Per quello servirebbe un'altra tecnica, e il progetto non
            ne ha bisogno perche' in produzione va la logistica.
    """
    preparazione = modello.named_steps["preparazione"]
    finale = modello.named_steps["modello"]
    if not hasattr(finale, "coef_"):
        msg = (
            f"{type(finale).__name__} non espone coefficienti: questa lettura vale solo "
            "per i modelli lineari."
        )
        raise TypeError(msg)

    nomi_grezzi = [str(nome) for nome in preparazione.get_feature_names_out()]
    pesi = np.asarray(finale.coef_).ravel()
    numeriche = list(preparazione.transformers_[0][2])
    scale = dict(
        zip(
            numeriche, np.asarray(preparazione.named_transformers_["numeriche"].scale_), strict=True
        )
    )

    righe = []
    for nome_grezzo, peso in zip(nomi_grezzi, pesi, strict=True):
        gruppo, _, nome = nome_grezzo.partition("__")
        sigma = float(scale.get(nome, 1.0))
        righe.append(
            {
                "variabile": nome,
                "tipo": {"numeriche": "numerica", "categoriche": "categoria"}.get(
                    gruppo, "booleana"
                ),
                "coefficiente": float(peso),
                "odds_ratio_per_deviazione_standard": float(np.exp(peso)),
                "unita_per_deviazione_standard": sigma,
                "odds_ratio_per_unita": float(np.exp(peso / sigma)),
                "direzione": "aumenta" if peso > 0 else "riduce",
            }
        )

    tabella = pd.DataFrame(righe)
    tabella["peso"] = tabella["coefficiente"].abs()
    return tabella.sort_values("peso", ascending=False).drop(columns="peso").reset_index(drop=True)


def impronta(percorso: Path, cifre: int = 12) -> str:
    """Identifica la versione di un file di dati con le prime cifre del suo sha256.

    Serve a rispondere alla domanda «questo modello e' stato addestrato su
    questi dati?» senza conservare una copia del dataset. Se il magazzino viene
    rigenerato dopo un cambio in ``transform.py``, l'impronta cambia e i
    metadati di un modello vecchio smettono di corrispondere.

    Args:
        percorso: Il file da identificare.
        cifre: Quante cifre esadecimali tenere. Dodici bastano ampiamente per
            distinguere un pugno di versioni.

    Returns:
        Le prime ``cifre`` dello sha256, in esadecimale.
    """
    digest = hashlib.sha256()
    with percorso.open("rb") as file:
        for blocco in iter(lambda: file.read(1 << 20), b""):
            digest.update(blocco)
    return digest.hexdigest()[:cifre]


def metadati(
    nome: str,
    modello: Pipeline,
    variabili: Sequence[str],
    punteggi: Mapping[str, float],
    contesto: Mapping[str, object],
) -> dict[str, object]:
    """Descrive un modello salvato, perche' un ``.pkl`` da solo non si racconta.

    Un file pickle e' opaco: non dice su quali variabili e' stato addestrato,
    con quale seed, su quali dati, ne' che punteggi aveva il giorno in cui e'
    stato scritto. Senza queste informazioni un modello salvato sei mesi fa non
    e' riproducibile, e' solo riutilizzabile — che e' un'altra cosa.

    Args:
        nome: Il nome logico del modello.
        modello: La pipeline addestrata, da cui si legge la classe finale.
        variabili: Le colonne usate come predittori, **in ordine**.
        punteggi: Le metriche misurate al momento del salvataggio.
        contesto: Conteggi della divisione, impronta dei dati e versioni delle
            librerie.

    Returns:
        Il dizionario da scrivere accanto al ``.pkl``.
    """
    return {
        "nome": nome,
        "versione_pacchetto": __version__,
        "classe": type(modello.named_steps["modello"]).__name__,
        "variabili": list(variabili),
        "seed": SEED,
        "quota_test": QUOTA_TEST,
        "colonna_gruppo": COLONNA_GRUPPO,
        "addestrato_il": datetime.now(UTC).isoformat(timespec="seconds"),
        "metriche": dict(punteggi),
        **dict(contesto),
    }


def salva_metadati(nome: str, contenuto: Mapping[str, object]) -> Path:
    """Scrive i metadati accanto al modello, con lo stesso nome ed estensione json.

    Args:
        nome: Il nome logico del modello.
        contenuto: Il dizionario prodotto da :func:`metadati`.

    Returns:
        Il percorso del file scritto.
    """
    percorso = percorso_modello(nome).with_suffix(".json")
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(
        json.dumps(dict(contenuto), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return percorso


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
