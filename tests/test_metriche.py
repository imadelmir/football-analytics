"""Verifiche delle metriche di valutazione (M5-T5).

Due test qui non controllano il codice, **dimostrano un'affermazione**: che
l'accuratezza premia un modello inutile, e che l'AUC non vede una previsione
gonfiata. Sono le due trappole che il progetto dichiara di evitare, e una
trappola dichiarata senza prova e' solo un'opinione.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from football_analytics import metriche as m

FREQUENZA = 0.0951
QUANTI = 20_000


def esiti_finti(frequenza: float = FREQUENZA, quanti: int = QUANTI, seed: int = 0) -> np.ndarray:
    """Genera esiti con una frequenza di gol realistica.

    Args:
        frequenza: Probabilita' che un tiro sia gol.
        quanti: Quanti tiri generare.
        seed: Radice del generatore.

    Returns:
        Un vettore di booleani.
    """
    generatore = np.random.default_rng(seed)
    return generatore.random(quanti) < frequenza


# ---------------------------------------------------------------------------
# Il riferimento
# ---------------------------------------------------------------------------


def test_il_brier_del_riferimento_e_la_formula_chiusa() -> None:
    # La formula p(1-p) si dimostra in tre passaggi, ma un errore di algebra
    # non farebbe rumore. Qui la si confronta con il calcolo diretto.
    esiti = esiti_finti()
    p = float(esiti.mean())
    diretto = float(np.mean((p - esiti.astype(float)) ** 2))

    assert m.riferimento(esiti)["brier"] == pytest.approx(diretto)


def test_il_log_loss_del_riferimento_e_la_formula_chiusa() -> None:
    # E' il numero che una volta ho stimato a mente sbagliandolo di tre
    # millesimi, e scritto con cinque decimali come se fosse misurato.
    esiti = esiti_finti()
    p = float(esiti.mean())
    diretto = float(np.mean(np.where(esiti, -math.log(p), -math.log1p(-p))))

    assert m.riferimento(esiti)["log_loss"] == pytest.approx(diretto)


def test_prevedere_sempre_la_media_da_guadagno_nullo() -> None:
    # E' la definizione dello zero della scala: se il modello non sa niente
    # oltre alla frequenza media, non ha guadagnato niente.
    esiti = esiti_finti()
    costante = np.full(len(esiti), float(esiti.mean()))

    risultato = m.metriche(esiti, costante)

    assert risultato["guadagno_brier"] == pytest.approx(0.0, abs=1e-9)
    assert risultato["guadagno_log_loss"] == pytest.approx(0.0, abs=1e-9)


def test_senza_variazione_il_riferimento_non_e_definito() -> None:
    with pytest.raises(ValueError, match="stesso esito"):
        m.riferimento(np.zeros(100, dtype=bool))


# ---------------------------------------------------------------------------
# Le due trappole, dimostrate
# ---------------------------------------------------------------------------


def test_l_accuratezza_premierebbe_un_modello_che_non_sa_niente() -> None:
    # Il modello che risponde «nessun tiro e' gol» azzecca il 90,5 % delle
    # volte. Sulle metriche che contano fa **peggio** del riferimento: il
    # guadagno e' negativo.
    esiti = esiti_finti()
    mai = np.zeros(len(esiti), dtype=float)

    accuratezza = float((esiti == (mai > 0.5)).mean())
    risultato = m.metriche(esiti, mai)

    assert accuratezza > 0.90
    assert risultato["guadagno_brier"] < 0.0


def test_l_auc_non_vede_una_previsione_gonfiata() -> None:
    # Moltiplicare ogni probabilita' per tre non cambia l'ordine dei tiri,
    # quindi l'AUC resta identica. E' il difetto di class_weight="balanced":
    # il modello sembra uguale e mente sul valore di ogni occasione.
    esiti = esiti_finti()
    generatore = np.random.default_rng(1)
    # Le due distribuzioni si sovrappongono di proposito: con previsioni
    # perfettamente separate l'AUC varrebbe 1 e il test passerebbe da solo.
    oneste = np.clip(esiti * 0.10 + generatore.random(len(esiti)) * 0.20, 0.01, 0.99)
    gonfiate = np.clip(oneste * 3.0, 0.01, 0.99)

    a = m.metriche(esiti, oneste)
    b = m.metriche(esiti, gonfiate)

    assert 0.55 < a["auc"] < 0.95
    assert b["auc"] == pytest.approx(a["auc"])
    assert abs(b["scarto_calibrazione"]) > abs(a["scarto_calibrazione"])
    assert b["guadagno_brier"] < a["guadagno_brier"]


# ---------------------------------------------------------------------------
# Comportamento generale
# ---------------------------------------------------------------------------


def test_un_modello_quasi_perfetto_guadagna_quasi_tutto() -> None:
    esiti = esiti_finti()
    quasi = np.where(esiti, 0.99, 0.01)

    risultato = m.metriche(esiti, quasi)

    assert risultato["guadagno_brier"] > 0.98
    assert risultato["auc"] == pytest.approx(1.0)


def test_le_lunghezze_diverse_vengono_segnalate() -> None:
    with pytest.raises(ValueError, match="forme diverse"):
        m.metriche(np.array([True, False, True]), np.array([0.1, 0.2]))


def test_il_confronto_mette_il_riferimento_per_primo() -> None:
    esiti = esiti_finti(quanti=2000)
    costante = np.full(len(esiti), float(esiti.mean()))

    risultato = m.confronta(esiti, {"costante": costante})

    assert next(iter(risultato)) == "riferimento"
    assert risultato["riferimento"]["brier"] == pytest.approx(risultato["costante"]["brier"])


def test_la_tabella_contiene_una_riga_per_modello() -> None:
    esiti = esiti_finti(quanti=2000)
    costante = np.full(len(esiti), float(esiti.mean()))

    testo = m.tabella(m.confronta(esiti, {"costante": costante}))

    assert len(testo.splitlines()) == 3  # intestazione, riferimento, costante
    assert "riferimento" in testo
