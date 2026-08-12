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

from football_analytics import features, model
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
