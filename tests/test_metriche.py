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


# ---------------------------------------------------------------------------
# La curva di calibrazione (M5-T7)
# ---------------------------------------------------------------------------


def previsioni_oneste(quanti: int = QUANTI, seed: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Genera previsioni calibrate per costruzione, con una forma simile all'xG.

    Args:
        quanti: Quanti tiri generare.
        seed: Radice del generatore.

    Returns:
        Gli esiti e le probabilita' che li hanno generati.
    """
    generatore = np.random.default_rng(seed)
    # Beta molto asimmetrica: mediana bassa e coda lunga, come un xG vero.
    probabilita = generatore.beta(1.2, 11.0, quanti)
    return generatore.random(quanti) < probabilita, probabilita


def test_i_gruppi_della_curva_hanno_lo_stesso_numero_di_tiri() -> None:
    esiti, probabilita = previsioni_oneste()

    curva = m.curva_di_calibrazione(esiti, probabilita)

    conteggi = curva["tiri"].to_numpy()
    assert len(curva) == m.GRUPPI_CALIBRAZIONE
    assert conteggi.max() - conteggi.min() <= 1


def test_gli_intervalli_di_ampiezza_uguale_sarebbero_degeneri() -> None:
    """Dimostra la scelta dei quantili invece di dichiararla.

    Su una distribuzione con la forma dell'xG, dieci intervalli larghi 0,1
    mettono il **61 %** dei tiri nel primo e lasciano vuoti gli ultimi cinque:
    la curva risulterebbe precisa dove non serve e priva di dati dove serve.

    Le soglie sono misurate, non stimate. La prima stesura chiedeva oltre il
    75 % nel primo intervallo, un numero scritto a intuito che sarebbe fallito
    su un valore vero del 61 %.
    """
    _, probabilita = previsioni_oneste()

    per_ampiezza = np.histogram(probabilita, bins=10, range=(0.0, 1.0))[0]

    assert per_ampiezza[0] / len(probabilita) > 0.55
    assert (per_ampiezza[5:] < 30).all()


def test_previsioni_tutte_uguali_danno_un_gruppo_solo() -> None:
    """Il caso che ha rotto la prima stesura, ed e' il modello di riferimento.

    Con previsioni identiche non ci sono quantili da tagliare: ``qcut``
    restituisce solo NaN, il raggruppamento resta vuoto e la media pesata
    divide per zero. Sono i quattro test gia' esistenti ad aver segnalato il
    difetto, tutti su un modello costante — cioe' sull'ingresso piu' semplice
    che questa funzione possa ricevere.
    """
    esiti = esiti_finti()
    costante = np.full(len(esiti), float(esiti.mean()))

    curva = m.curva_di_calibrazione(esiti, costante)

    assert len(curva) == 1
    assert int(curva["tiri"].iloc[0]) == len(esiti)
    assert m.errore_di_calibrazione(esiti, costante) == pytest.approx(0.0, abs=1e-9)


def test_un_modello_calibrato_ha_errore_quasi_nullo() -> None:
    esiti, probabilita = previsioni_oneste()

    assert m.errore_di_calibrazione(esiti, probabilita) < 0.01


def test_una_previsione_gonfiata_ha_errore_grande() -> None:
    esiti, probabilita = previsioni_oneste()

    onesto = m.errore_di_calibrazione(esiti, probabilita)
    gonfiato = m.errore_di_calibrazione(esiti, np.clip(probabilita * 3.0, 0.0, 1.0))

    assert gonfiato > 10 * onesto


def test_lo_scarto_medio_con_segno_non_vede_un_difetto_che_si_compensa() -> None:
    # E' il motivo per cui l'errore di calibrazione esiste accanto allo scarto
    # medio: un modello che gonfia i tiri facili quanto schiaccia i difficili
    # ha scarto medio nullo e curva sbagliata ovunque.
    esiti, probabilita = previsioni_oneste()
    mediana = float(np.median(probabilita))
    storto = np.where(probabilita > mediana, probabilita + 0.05, probabilita - 0.05)
    storto = np.clip(storto, 0.001, 0.999)
    # Riporta la media esattamente su quella onesta, cosi' il difetto e'
    # invisibile alla metrica con segno.
    storto = np.clip(storto - (storto.mean() - probabilita.mean()), 0.001, 0.999)

    con_segno = m.metriche(esiti, storto)["scarto_calibrazione"]
    assoluto = m.errore_di_calibrazione(esiti, storto)

    # Misurato: scarto con segno +0,0036, errore assoluto 0,0358.
    assert abs(con_segno) < 0.01
    assert assoluto > 0.025


def test_lo_scarto_in_errori_standard_e_coerente_con_le_colonne() -> None:
    esiti, probabilita = previsioni_oneste()

    curva = m.curva_di_calibrazione(esiti, probabilita)

    atteso = (curva["xg_previsto"] - curva["gol_osservati"]) / curva["errore_standard"]
    assert curva["scarto_in_se"].to_numpy() == pytest.approx(atteso.to_numpy(), nan_ok=True)


# ---------------------------------------------------------------------------
# L'accordo con un altro modello xG (M5-T8)
# ---------------------------------------------------------------------------


def test_un_modello_confrontato_con_se_stesso_e_in_accordo_perfetto() -> None:
    _, probabilita = previsioni_oneste(quanti=5000)

    risultato = m.accordo(probabilita, probabilita)

    assert risultato["pearson"] == pytest.approx(1.0)
    assert risultato["spearman"] == pytest.approx(1.0)
    assert risultato["scarto_assoluto_medio"] == pytest.approx(0.0)


def test_lo_spearman_non_cambia_dopo_una_trasformazione_monotona() -> None:
    # E' la proprieta' che distingue Spearman da Pearson: se un modello e' una
    # versione riscalata dell'altro, l'ordine e' identico e Spearman lo vede.
    _, probabilita = previsioni_oneste(quanti=5000)
    riscalato = probabilita**0.5

    risultato = m.accordo(probabilita, riscalato)

    assert risultato["spearman"] == pytest.approx(1.0)
    assert risultato["pearson"] < 0.99


def test_lo_scarto_medio_ha_segno() -> None:
    _, probabilita = previsioni_oneste(quanti=5000)
    piu_generoso = np.clip(probabilita + 0.02, 0.0, 1.0)

    assert m.accordo(piu_generoso, probabilita)["scarto_medio"] > 0
    assert m.accordo(probabilita, piu_generoso)["scarto_medio"] < 0


def test_lo_scarto_assoluto_cresce_con_il_livello_dell_xg() -> None:
    """Dimostra perche' lo scarto assoluto da solo inganna.

    Due coppie di previsioni con lo **stesso** disaccordo relativo — il 20 % —
    danno scarti assoluti dieci volte diversi solo perche' una coppia sta
    intorno a 0,05 e l'altra intorno a 0,50. Chi legge solo la colonna assoluta
    conclude che sui tiri ravvicinati i modelli discordano di piu', quando
    discordano esattamente uguale.
    """
    bassi = np.full(1000, 0.05)
    alti = np.full(1000, 0.50)

    basso = m.accordo(bassi * 1.2, bassi)
    alto = m.accordo(alti * 1.2, alti)

    assert alto["scarto_assoluto_medio"] > 9 * basso["scarto_assoluto_medio"]
    assert alto["scarto_relativo_mediano"] == pytest.approx(basso["scarto_relativo_mediano"])


def test_aggregare_non_aiuta_se_il_rumore_e_indipendente() -> None:
    """Il contrario di quello che sembra ovvio, e la prima stesura ci e' cascata.

    Sommando ``n`` tiri crescono **sia** il segnale **sia** il rumore, entrambi
    proporzionalmente a ``n``: il rapporto fra i due resta lo stesso e la
    correlazione non si muove. Misurato: da 0,9472 a 0,9464.

    Il test esiste per impedire che qualcuno «corregga» il codice inseguendo un
    miglioramento che non deve esserci.
    """
    generatore = np.random.default_rng(7)
    quanti, per_partita_ = 6000, 30
    vero = generatore.beta(1.2, 11.0, quanti)
    uno = np.clip(vero + generatore.normal(0, 0.02, quanti), 0.001, 0.999)
    due = np.clip(vero + generatore.normal(0, 0.02, quanti), 0.001, 0.999)
    partite = np.repeat(np.arange(quanti // per_partita_), per_partita_)

    per_tiro = m.accordo(uno, due)["pearson"]
    aggregato = m.accordo_aggregato(uno, due, partite)

    assert abs(aggregato["pearson"] - per_tiro) < 0.01
    assert aggregato["gruppi"] == quanti // per_partita_


def test_aggregare_aiuta_se_le_partite_differiscono_fra_loro() -> None:
    """E' il meccanismo che opera sui dati veri.

    Quando le partite hanno una componente condivisa — serate in cui si creano
    occasioni migliori — la varianza dei totali cresce con il **quadrato** del
    numero di tiri mentre quella del rumore cresce solo linearmente, e
    l'aggregazione fa emergere l'accordo. Misurato: da 0,9551 a 0,9916.

    Sui dati veri il nostro modello e quello di StatsBomb passano da 0,9076 per
    tiro a 0,9529 per partita, cioe' si comportano come questo caso e non come
    quello precedente: **le partite differiscono davvero fra loro**, e i due
    modelli lo vedono allo stesso modo anche dove discordano tiro per tiro.
    """
    generatore = np.random.default_rng(7)
    quanti, per_partita_ = 6000, 30
    partite = np.repeat(np.arange(quanti // per_partita_), per_partita_)
    effetto = generatore.normal(0.0, 0.04, quanti // per_partita_)
    vero = np.clip(generatore.beta(1.2, 11.0, quanti) + effetto[partite], 0.001, 0.999)
    uno = np.clip(vero + generatore.normal(0, 0.02, quanti), 0.001, 0.999)
    due = np.clip(vero + generatore.normal(0, 0.02, quanti), 0.001, 0.999)

    per_tiro = m.accordo(uno, due)["pearson"]
    aggregato = m.accordo_aggregato(uno, due, partite)["pearson"]

    assert aggregato > per_tiro + 0.02


def test_le_lunghezze_diverse_vengono_segnalate_anche_nell_accordo() -> None:
    with pytest.raises(ValueError, match="forme diverse"):
        m.accordo(np.array([0.1, 0.2, 0.3]), np.array([0.1, 0.2]))


def test_la_tabella_contiene_una_riga_per_modello() -> None:
    esiti = esiti_finti(quanti=2000)
    costante = np.full(len(esiti), float(esiti.mean()))

    testo = m.tabella(m.confronta(esiti, {"costante": costante}))

    assert len(testo.splitlines()) == 3  # intestazione, riferimento, costante
    assert "riferimento" in testo
