"""Verifiche del modello base, regressione logistica (M5-T4).

Il criterio del backlog e' che il modello sia **salvato e riproducibile con un
seed fisso**. I test coprono quello, piu' le proprieta' che rendono un modello
xG utilizzabile e che nessun messaggio d'errore segnalerebbe se si perdessero.

La piu' importante e' la **calibrazione**: la media delle probabilita' previste
deve somigliare alla frequenza reale dei gol. E' anche il test che smaschera
l'errore piu' tentante su un problema con un gol ogni dieci tiri, cioe'
`class_weight="balanced"`: bilanciare le classi migliora l'ordinamento ma
gonfia le probabilita' verso il 50 %, e un xG che dice 0,5 dove la realta' e'
0,1 non serve a niente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold

from football_analytics import features, metriche, model
from football_analytics.config import SEED

if TYPE_CHECKING:
    from pathlib import Path

    from sklearn.pipeline import Pipeline

NUMERICHE = list(features.VARIABILI_NUMERICHE)
CATEGORICHE = list(features.VARIABILI_CATEGORICHE)
BOOLEANE = list(features.VARIABILI_BOOLEANE)
VARIABILI = list(features.VARIABILI_BASE)


def tiri_finti(partite: int = 200, per_partita: int = 25, seed: int = 0) -> pd.DataFrame:
    """Genera tiri con una relazione vera fra distanza e gol.

    La probabilita' di segnare scende con la distanza, cosi' il modello ha
    qualcosa da imparare e i test possono verificare che l'abbia imparato.

    Args:
        partite: Quante partite generare.
        per_partita: Quanti tiri per partita.
        seed: Radice del generatore.

    Returns:
        Una tabella con le variabili base, ``gol`` e ``match_id``.
    """
    generatore = np.random.default_rng(seed)
    righe = partite * per_partita
    distanza = generatore.uniform(4.0, 35.0, righe)
    angolo = np.clip(np.arctan2(8.0, distanza) * 2, 0.01, np.pi)
    probabilita = 1 / (1 + np.exp(0.5 + 0.12 * (distanza - 10)))

    return pd.DataFrame(
        {
            "distanza": distanza.astype("float32"),
            "angolo": angolo.astype("float32"),
            "parte_corpo": pd.Categorical(
                generatore.choice(["Right Foot", "Left Foot", "Head"], righe)
            ),
            "tipo": pd.Categorical(generatore.choice(["Open Play", "Free Kick"], righe)),
            "schema": pd.Categorical(
                generatore.choice(["Regular Play", "From Corner", "From Throw In"], righe)
            ),
            "sotto_pressione": generatore.random(righe) < 0.25,
            "gol": generatore.random(righe) < probabilita,
            "match_id": np.repeat(np.arange(1000, 1000 + partite), per_partita),
        }
    )


@pytest.fixture
def addestrato() -> tuple[Pipeline, pd.DataFrame, pd.DataFrame]:
    """Un modello base gia' addestrato, con i suoi due insiemi.

    Returns:
        Il modello, l'insieme di addestramento e quello di verifica.
    """
    train, test = model.dividi_per_partita(tiri_finti())
    pipeline = model.pipeline_logistica(NUMERICHE, CATEGORICHE, BOOLEANE)
    return model.addestra(pipeline, train, VARIABILI), train, test


# ---------------------------------------------------------------------------
# Il modello produce probabilita' sensate
# ---------------------------------------------------------------------------


def test_le_previsioni_sono_probabilita(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
) -> None:
    modello, _, test = addestrato
    p = model.previsioni(modello, test, VARIABILI)

    assert len(p) == len(test)
    assert ((p >= 0) & (p <= 1)).all()
    assert not np.isnan(p).any()


def test_da_vicino_si_prevede_piu_gol_che_da_lontano(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
) -> None:
    modello, _, test = addestrato
    p = model.previsioni(modello, test, VARIABILI)
    vicini = p[test["distanza"].to_numpy() < 10]
    lontani = p[test["distanza"].to_numpy() > 28]

    assert vicini.mean() > lontani.mean()


def test_il_modello_e_calibrato_sul_suo_addestramento(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
) -> None:
    # E' il test che smaschera class_weight="balanced": con i pesi bilanciati
    # la media delle probabilita' previste salirebbe verso il 50 % mentre la
    # frequenza reale resta intorno al 10 %.
    modello, train, _ = addestrato
    p = model.previsioni(modello, train, VARIABILI)

    assert p.mean() == pytest.approx(float(train["gol"].mean()), abs=0.01)


def test_le_probabilita_previste_non_si_addensano_a_meta(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
) -> None:
    # Un modello xG deve saper dire «questo tiro vale 0,03». Se le previsioni
    # stanno tutte intorno a 0,5, ordina bene e informa male.
    modello, _, test = addestrato
    p = model.previsioni(modello, test, VARIABILI)

    assert p.min() < 0.1
    assert p.max() > 0.3


# ---------------------------------------------------------------------------
# Riproducibilita' — il criterio di M5-T4
# ---------------------------------------------------------------------------


def test_lo_stesso_seed_da_le_stesse_previsioni() -> None:
    dati = tiri_finti()
    train, test = model.dividi_per_partita(dati)

    uno = model.addestra(
        model.pipeline_logistica(NUMERICHE, CATEGORICHE, BOOLEANE, seed=SEED), train, VARIABILI
    )
    due = model.addestra(
        model.pipeline_logistica(NUMERICHE, CATEGORICHE, BOOLEANE, seed=SEED), train, VARIABILI
    )

    assert model.previsioni(uno, test, VARIABILI) == pytest.approx(
        model.previsioni(due, test, VARIABILI)
    )


def test_il_modello_riletto_prevede_identico(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(model, "MODELS_DIR", tmp_path)
    modello, _, test = addestrato

    percorso = model.salva_modello(modello, "prova")
    riletto = model.carica_modello("prova")

    assert percorso.exists()
    assert model.previsioni(riletto, test, VARIABILI) == pytest.approx(
        model.previsioni(modello, test, VARIABILI)
    )


# ---------------------------------------------------------------------------
# Robustezza del preprocessore
# ---------------------------------------------------------------------------


def test_una_categoria_mai_vista_non_rompe_la_previsione(
    addestrato: tuple[Pipeline, pd.DataFrame, pd.DataFrame],
) -> None:
    # Succede con gli schemi di gioco rari: uno che compare solo in verifica
    # non deve far fallire tutto. `handle_unknown="ignore"` lo tratta come
    # nessuna categoria attiva.
    modello, _, test = addestrato
    sconosciuto = test.copy()
    sconosciuto["schema"] = "Uno Schema Inventato"

    p = model.previsioni(modello, sconosciuto, VARIABILI)

    assert not np.isnan(p).any()


def test_il_preprocessore_scarta_le_colonne_non_dichiarate() -> None:
    # `remainder="drop"`: se domani qualcuno passa una tabella con match_id
    # dentro, il modello non deve impararci sopra.
    dati = tiri_finti(partite=20)
    preparatore = model.costruisci_preprocessore(NUMERICHE, CATEGORICHE, BOOLEANE)
    trasformato = preparatore.fit_transform(dati)

    categorie = sum(dati[c].nunique() for c in CATEGORICHE)
    assert trasformato.shape[1] == len(NUMERICHE) + categorie + len(BOOLEANE)


# ---------------------------------------------------------------------------
# Il modello ad alberi (M5-T5)
# ---------------------------------------------------------------------------

LEGGERI = model.Iperparametri(iterazioni=120, tasso=0.1)


def tiri_a_u(partite: int = 400, per_partita: int = 20, seed: int = 3) -> pd.DataFrame:
    """Genera tiri in cui la probabilita' di gol descrive una U.

    E' la forma che il progetto si aspetta dalla distanza del portiere: si segna
    di piu' quando il portiere e' addosso — perche' vuol dire che il tiro parte
    da vicino — **e** quando e' molto avanzato, perche' la porta e' sguarnita.
    In mezzo si segna meno.

    Una regressione logistica **non puo' rappresentarla**: un coefficiente
    descrive una direzione sola, e la migliore retta attraverso una U e' quasi
    piatta. Un albero la cattura con due tagli.

    La colonna ``probabilita_vera`` e' la probabilita' che ha generato l'esito.
    Serve a costruire l'**oracolo**: il modello che non si puo' battere, perche'
    sa esattamente da dove vengono i dati. Il preprocessore la scarta —
    ``remainder="drop"`` — quindi nessun modello la vede.

    Args:
        partite: Quante partite generare.
        per_partita: Quanti tiri per partita.
        seed: Radice del generatore.

    Returns:
        Una tabella con le variabili base, ``gol``, ``probabilita_vera`` e
        ``match_id``.
    """
    generatore = np.random.default_rng(seed)
    righe = partite * per_partita
    distanza = generatore.uniform(4.0, 35.0, righe)
    posizione = (distanza - 4.0) / 31.0
    probabilita = 0.05 + 0.35 * (2.0 * posizione - 1.0) ** 2

    return pd.DataFrame(
        {
            "distanza": distanza.astype("float32"),
            "angolo": np.full(righe, 0.5, dtype="float32"),
            "parte_corpo": pd.Categorical(generatore.choice(["Right Foot", "Head"], righe)),
            "tipo": pd.Categorical(generatore.choice(["Open Play", "Free Kick"], righe)),
            "schema": pd.Categorical(generatore.choice(["Regular Play", "From Corner"], righe)),
            "sotto_pressione": generatore.random(righe) < 0.25,
            "gol": generatore.random(righe) < probabilita,
            "probabilita_vera": probabilita.astype("float32"),
            "match_id": np.repeat(np.arange(1000, 1000 + partite), per_partita),
        }
    )


def test_gli_alberi_battono_la_logistica_su_una_relazione_a_u() -> None:
    """Verifica la previsione registrata in ``NOTES.md`` prima di misurarla.

    **Le soglie sono espresse in frazione dell'oracolo, non in punti di Brier.**
    La prima versione di questo test chiedeva agli alberi un guadagno superiore
    al 20 %, un numero scritto senza derivarlo: su questi dati il guadagno
    massimo *possibile* e' circa l'8 %, perche' con probabilita' vere fra 0,05 e
    0,40 la maggior parte dell'errore quadratico e' rumore che nessun modello
    puo' togliere. La soglia era irraggiungibile e il test sarebbe fallito
    accusando il codice.

    Misurato su sei semi diversi: la logistica cattura da -6 % a -1 %
    dell'ottenibile — cioe' niente, e a volte peggio del riferimento, perche'
    la retta che meglio attraversa una U punta dalla parte sbagliata. Gli
    alberi catturano dal 25 % al 71 %. Le soglie sotto lasciano margine a
    entrambi gli estremi.
    """
    dati = tiri_a_u()
    train, test = model.dividi_per_partita(dati)

    lineare = model.addestra(
        model.pipeline_logistica(NUMERICHE, CATEGORICHE, BOOLEANE), train, VARIABILI
    )
    alberi = model.addestra(
        model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI), train, VARIABILI
    )

    oracolo = metriche.metriche(test["gol"], test["probabilita_vera"])["guadagno_brier"]
    punteggi = metriche.confronta(
        test["gol"],
        {
            "lineare": model.previsioni(lineare, test, VARIABILI),
            "alberi": model.previsioni(alberi, test, VARIABILI),
        },
    )

    assert oracolo > 0.0
    assert punteggi["lineare"]["guadagno_brier"] / oracolo < 0.05
    assert punteggi["alberi"]["guadagno_brier"] / oracolo > 0.15


def test_gli_alberi_sono_calibrati_sul_loro_addestramento() -> None:
    """Vale per gli alberi quanto per la logistica.

    **La misura si fa sull'addestramento, come per il modello base**, e il nome
    del test lo dice. La prima versione la faceva sull'insieme di verifica e
    falliva: non per colpa del modello, ma perche' quella divisione ha una
    frequenza di gol piu' alta di 4,7 punti rispetto all'addestramento. Il test
    successivo dimostra che era della divisione.

    Misurato su sei semi: lo scarto degli alberi sull'addestramento non supera
    mai 0,00045, quello della logistica 0,00008. La logistica ha lo zero esatto
    per costruzione — massimizzare la verosimiglianza con un'intercetta impone
    che la media prevista uguagli la frequenza osservata — gli alberi ci
    arrivano senza garanzia, ed e' questo che vale la pena verificare.
    """
    train, _ = model.dividi_per_partita(tiri_finti())
    alberi = model.addestra(
        model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI), train, VARIABILI
    )

    risultato = metriche.metriche(train["gol"], model.previsioni(alberi, train, VARIABILI))

    assert risultato["scarto_calibrazione"] == pytest.approx(0.0, abs=0.005)


def test_lo_scarto_sulla_verifica_e_della_divisione_non_del_modello() -> None:
    """Dimostra perche' la calibrazione non si misura sull'insieme di verifica.

    Con questo seme la divisione produce un insieme di verifica che segna 4,7
    punti piu' dell'addestramento — un caso a 3,3 deviazioni standard, raro ma
    non impossibile. Entrambi i modelli sottostimano di circa cinque punti, e
    **sottostimano insieme**: la differenza fra i loro scarti resta sotto il
    mezzo punto, contro i cinque dello scarto comune.

    Se lo scarto fosse un difetto del gradient boosting, la logistica non
    dovrebbe averlo. Ce l'ha, quasi identico. Misurato su sei semi, i due
    modelli non si allontanano mai piu' di 0,0058 l'uno dall'altro.
    """
    train, test = model.dividi_per_partita(tiri_finti())
    lineare = model.addestra(
        model.pipeline_logistica(NUMERICHE, CATEGORICHE, BOOLEANE), train, VARIABILI
    )
    alberi = model.addestra(
        model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI), train, VARIABILI
    )

    scarto_divisione = float(test["gol"].mean()) - float(train["gol"].mean())
    s_lineare = metriche.metriche(test["gol"], model.previsioni(lineare, test, VARIABILI))[
        "scarto_calibrazione"
    ]
    s_alberi = metriche.metriche(test["gol"], model.previsioni(alberi, test, VARIABILI))[
        "scarto_calibrazione"
    ]

    assert scarto_divisione > 0.04
    assert s_lineare < -0.04
    assert s_alberi < -0.04
    assert abs(s_alberi - s_lineare) < 0.02


def test_gli_alberi_reggono_i_valori_mancanti() -> None:
    # Conta a M5-T6: le variabili spaziali sono assenti dove manca il
    # fotogramma, e la regola del progetto vieta di riempirle di zeri. Il
    # gradient boosting a istogrammi non ha bisogno che siano riempite.
    dati = tiri_finti()
    dati.loc[dati.index[::4], "distanza"] = np.nan
    train, test = model.dividi_per_partita(dati)

    alberi = model.addestra(
        model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI), train, VARIABILI
    )
    p = model.previsioni(alberi, test, VARIABILI)

    assert test["distanza"].isna().any()
    assert not np.isnan(p).any()


def test_la_validazione_incrociata_non_spezza_le_partite() -> None:
    # E' l'assunzione su cui si regge logloss_incrociato: se GroupKFold non
    # facesse quello che credo, la scelta degli iperparametri sarebbe presa su
    # un punteggio gonfiato, in silenzio.
    dati = tiri_finti(partite=100)
    gruppi = dati["match_id"].to_numpy()

    for indici_train, indici_prova in GroupKFold(n_splits=model.PIEGHE).split(
        dati, dati["gol"], gruppi
    ):
        assert not set(gruppi[indici_train]) & set(gruppi[indici_prova])


def test_la_validazione_incrociata_da_sempre_lo_stesso_numero() -> None:
    dati = tiri_finti(partite=60)

    def costruisci() -> Pipeline:
        return model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI)

    uno = model.logloss_incrociato(costruisci, dati, VARIABILI, pieghe=3)
    due = model.logloss_incrociato(costruisci, dati, VARIABILI, pieghe=3)

    assert uno == pytest.approx(due)


def test_gli_alberi_salvati_e_riletti_prevedono_identico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(model, "MODELS_DIR", tmp_path)
    train, test = model.dividi_per_partita(tiri_finti(partite=60))
    alberi = model.addestra(
        model.pipeline_alberi(NUMERICHE, CATEGORICHE, BOOLEANE, LEGGERI), train, VARIABILI
    )

    model.salva_modello(alberi, "prova_alberi")
    riletto = model.carica_modello("prova_alberi")

    assert model.previsioni(riletto, test, VARIABILI) == pytest.approx(
        model.previsioni(alberi, test, VARIABILI)
    )
