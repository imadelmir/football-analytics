"""I numeri congelati del modello, riletti e verificati (M6-T9).

**Questi test girano anche in CI**, a differenza di quasi tutti gli altri della
dashboard: non leggono i Parquet — che entrano in git solo a M7-T1 — ma i tre
JSON prodotti da M5, che in git ci sono gia'. Vuol dire che i numeri mostrati
dalla vista Modello sono verificati a ogni push, non solo sulla macchina di chi
sviluppa.

Il test piu' importante del file non controlla un calcolo ma una **premessa
statistica**: che le variabili categoriche portino una costante non
identificata, e che quindi non possano stare nella stessa classifica delle
variabili continue. E' il difetto che avrebbe reso la pagina falsa in modo
credibile — «il tipo di tiro e' la variabile piu' importante» — e l'unica cosa
che lo impedisce e' il centraggio, verificato qui sotto.
"""

from __future__ import annotations

import json
import math
from typing import Any

import pytest

from football_analytics import rendiconto
from football_analytics.features import VARIABILI_BASE, VARIABILI_SPAZIALI

#: Quanti decili ha ogni curva di calibrazione.
DECILI = 10

#: Quante variabili ha ciascuna delle due varianti.
QUANTE_BASE = 6
QUANTE_360 = 11

#: Il rapporto atteso fra un colpo di testa e un tiro di piede destro, a
#: parita' di tutto il resto. E' un fatto di dominio, non un numero di comodo:
#: se un giorno il modello dicesse che di testa si segna di piu' che di piede,
#: qualcosa nella pipeline sarebbe rotto e questo test lo direbbe.
TESTA_CONTRO_PIEDE = 0.41


def test_i_numeri_congelati_sono_al_loro_posto() -> None:
    """La vista Modello non ha una fonte alternativa: o ci sono, o non c'e' pagina.

    Il percorso e' scritto due volte — qui e in ``scripts/train_model.py`` —
    quindi puo' divergere. Questo test e' cio' che se ne accorge.
    """
    assert rendiconto.disponibile(), f"manca {rendiconto.RISULTATI} o una scheda in models/"


def test_le_due_varianti_sono_quelle_che_vanno_in_produzione() -> None:
    """Base e 360, entrambe logistiche, con il numero giusto di variabili."""
    base, spaziale = rendiconto.varianti()

    assert (base.etichetta, spaziale.etichetta) == ("Base", "360")
    assert base.classe == spaziale.classe == "LogisticRegression"
    assert len(base.variabili) == QUANTE_BASE == len(VARIABILI_BASE)
    assert len(spaziale.variabili) == QUANTE_360 == len(VARIABILI_BASE) + len(VARIABILI_SPAZIALI)


def test_il_360_batte_il_base_su_tutte_e_tre_le_metriche() -> None:
    """Se non fosse cosi', la pagina non avrebbe niente da raccontare.

    Il guadagno e' modesto e la pagina lo dice, ma deve esistere: un modello con
    cinque variabili in piu' che peggiora vorrebbe dire che quelle variabili
    sono rumore, e la vista Finali di Champions non potrebbe usarlo.
    """
    base, spaziale = rendiconto.varianti()

    assert spaziale.brier < base.brier
    assert spaziale.log_loss < base.log_loss
    assert spaziale.auc > base.auc


def test_la_calibrazione_ha_tre_curve_da_dieci_decili() -> None:
    """Tre modelli per dieci gruppi: trenta punti, nessuno perso per strada."""
    curve = rendiconto.calibrazione()

    assert len(curve) == len(rendiconto.CALIBRATI) * DECILI
    assert set(curve["modello"]) == {"Base", "360", "StatsBomb"}
    for nome in curve["modello"].unique():
        suoi = curve[curve["modello"] == nome]
        assert list(suoi["gruppo"]) == list(range(DECILI))


def test_i_decili_salgono_e_hanno_tutti_lo_stesso_peso() -> None:
    """Sono decili, quindi ordinati per probabilita' e larghi uguale.

    Se un gruppo avesse dieci tiri invece di ottocento, il suo punto ballerebbe
    per il caso e il grafico sembrerebbe accusare il modello.
    """
    curve = rendiconto.calibrazione()

    for nome in curve["modello"].unique():
        suoi = curve[curve["modello"] == nome].sort_values("gruppo")
        previsti = list(suoi["xg_previsto"])
        assert previsti == sorted(previsti)
        assert max(suoi["tiri"]) - min(suoi["tiri"]) <= 1


def test_lo_scarto_e_l_errore_standard_sono_coerenti() -> None:
    """Verifica di aver letto le colonne giuste, non di aver rifatto il conto.

    ``scarto`` deve essere previsto meno osservato e ``scarto_in_se`` lo stesso
    diviso l'errore standard. Se un giorno una delle due colonne cambiasse
    significato nel rendiconto, la frase calcolata della pagina — che conta i
    decili oltre i due errori standard — direbbe una cosa per un'altra.
    """
    curve = rendiconto.calibrazione()

    atteso = curve["xg_previsto"] - curve["gol_osservati"]
    assert curve["scarto"].to_numpy() == pytest.approx(atteso.to_numpy(), abs=1e-9)
    in_se = curve["scarto"] / curve["errore_standard"]
    assert curve["scarto_in_se"].to_numpy() == pytest.approx(in_se.to_numpy(), rel=1e-9)


def test_le_categoriche_portano_una_costante_non_identificata() -> None:
    """La premessa di tutto il blocco «cosa guarda», verificata invece che detta.

    La codifica non scarta nessun livello, quindi ogni variabile categorica e'
    definita a meno di una costante. Nel rendiconto la costante e' **la stessa
    per tutte e tre**, e si vede: la somma dei coefficienti di ``parte_corpo``,
    di ``tipo`` e di ``schema`` da' lo stesso valore. E' il motivo per cui la
    pagina non le mette nella classifica delle variabili continue.
    """
    with rendiconto.RISULTATI.open(encoding="utf-8") as flusso:
        misure: dict[str, Any] = json.load(flusso)

    somme: dict[str, float] = {}
    for voce in misure["coefficienti"]:
        if voce["tipo"] != "categoria":
            continue
        gruppo = str(voce["variabile"]).rsplit("_", 1)[0]
        somme[gruppo] = somme.get(gruppo, 0.0) + float(voce["coefficiente"])

    valori = list(somme.values())
    assert len(valori) > 1
    assert valori == pytest.approx([valori[0]] * len(valori), abs=1e-6), (
        "le costanti non coincidono piu': rivedere il centraggio di rendiconto.categorie"
    )


def test_nella_classifica_dei_pesi_entrano_solo_le_variabili_continue() -> None:
    """Otto variabili, tre base e cinque spaziali, nessuna categoria."""
    pesi = rendiconto.pesi()

    assert len(pesi) == len(VARIABILI_SPAZIALI) + 3
    assert not any(" · " in str(nome) for nome in pesi["variabile"])
    assert int(pesi["spaziale"].sum()) == len(VARIABILI_SPAZIALI)


def test_la_distanza_e_la_variabile_che_pesa_di_piu() -> None:
    """La prima riga e la scala logaritmica, insieme.

    Il peso e' il logaritmo in base due dell'odds ratio: e' la scala che rende
    simmetriche le barre del grafico, e se qualcuno la cambiasse in un rapporto
    grezzo tutto cio' che riduce sembrerebbe piccolo.
    """
    pesi = rendiconto.pesi()
    prima = pesi.iloc[0]

    assert prima["variabile"] == rendiconto.ETICHETTE["distanza"]
    assert prima["direzione"] == "riduce"
    assert float(prima["peso"]) == pytest.approx(math.log2(float(prima["odds_ratio"])))


def test_il_centraggio_toglie_la_costante_da_ogni_categoria() -> None:
    """Dopo il centraggio i pesi di ogni variabile sommano a zero.

    E' la definizione di «costante rimossa»: resta solo cio' che distingue un
    livello dagli altri della stessa variabile, che e' la parte identificata.
    """
    categorie = rendiconto.categorie()

    for gruppo, suoi in categorie.groupby("gruppo", observed=True):
        assert float(suoi["peso"].sum()) == pytest.approx(0.0, abs=1e-9), gruppo


def test_di_testa_vale_circa_la_meta_di_un_tiro_di_piede() -> None:
    """Il controllo di dominio: se saltasse, la pipeline sarebbe rotta a monte.

    A parita' di distanza e di angolo un colpo di testa segna molto meno di un
    tiro di piede. E' l'unico risultato che si puo' verificare senza rifare i
    conti, e vale piu' di dieci controlli sulle forme delle tabelle.
    """
    categorie = rendiconto.categorie()
    corpo = rendiconto.per_nome(
        categorie[categorie["gruppo"] == "Parte del corpo"], "livello", "odds_ratio"
    )

    rapporto = corpo["testa"] / corpo["piede destro"]

    assert rapporto == pytest.approx(TESTA_CONTRO_PIEDE, abs=0.02)


def test_ogni_etichetta_e_tradotta_e_nessuna_si_ripete() -> None:
    """Due righe con lo stesso nome sono peggio di una riga in inglese.

    ``tipo_Corner`` e ``schema_From Corner`` sono cose diverse: senza il
    prefisso nell'etichetta diventerebbero entrambe «da corner», nella stessa
    tabella, con due numeri diversi.
    """
    with rendiconto.RISULTATI.open(encoding="utf-8") as flusso:
        misure: dict[str, Any] = json.load(flusso)

    etichette = [
        rendiconto.etichetta_variabile(str(voce["variabile"])) for voce in misure["coefficienti"]
    ]

    assert not [nome for nome in etichette if "_" in nome], "restano nomi non tradotti"
    assert len(set(etichette)) == len(etichette), "due variabili hanno la stessa etichetta"


def test_l_ablazione_aggiunge_i_gruppi_uno_alla_volta() -> None:
    """I sei passi nell'ordine di lettura, dal niente al modello completo."""
    ablazione = rendiconto.ablazione()

    assert list(ablazione["passo"]) == list(rendiconto.PASSI.values())
    auc = rendiconto.per_nome(ablazione, "passo", "auc")
    brier = rendiconto.per_nome(ablazione, "passo", "brier")
    assert auc["Nessun modello"] == pytest.approx(0.5)
    assert brier["Modello 360"] < brier["Modello base"]


def test_nessun_nome_di_modello_arriva_in_pagina_non_tradotto() -> None:
    """Le tabelle mostrano «Base» e «360», mai «logistica spaziale».

    Due nomi per lo stesso modello nella stessa pagina fanno credere che i
    modelli siano quattro.
    """
    leggibili = set(rendiconto.NOMI.values())
    for tabella in (rendiconto.confronto(), rendiconto.fuori_campione()):
        assert set(tabella["modello"]) <= leggibili, "una chiave grezza e' arrivata in tabella"
    assert "logistica spaziale" not in leggibili


def test_le_finali_sono_state_tenute_fuori_dall_addestramento() -> None:
    """La premessa di M6-T10, misurata qui perche' qui c'e' il numero.

    Le finali di Champions escono prima della divisione fra addestramento e
    verifica, quindi il modello non le ha mai viste. Sono la prova che i
    punteggi non dipendono dall'aver imparato a memoria un campionato.
    """
    contesto = rendiconto.contesto()
    fuori = rendiconto.per_nome(rendiconto.fuori_campione(), "modello", "brier")
    _, spaziale = rendiconto.varianti()

    assert contesto.finali_applicazione > 0
    assert contesto.tiri_applicazione > 0
    assert fuori["360"] < spaziale.brier, (
        "sulle finali il modello non deve peggiorare rispetto al proprio test"
    )


def test_la_divisione_e_per_partita_e_non_per_tiro() -> None:
    """Le partite di verifica sono un quinto del totale, non una frazione a caso.

    Se la divisione fosse per tiro, il rapporto fra partite di addestramento e
    di verifica non tornerebbe: due tiri della stessa partita finirebbero da
    parti diverse e il numero di partite verrebbe contato due volte.
    """
    contesto = rendiconto.contesto()

    partite = contesto.partite_train + contesto.partite_test
    assert contesto.partite_test / partite == pytest.approx(0.2, abs=0.01)
    assert contesto.tiri_test / (contesto.tiri_train + contesto.tiri_test) == pytest.approx(
        0.2, abs=0.01
    )


def test_l_accordo_con_statsbomb_e_piu_alto_per_partita_che_per_tiro() -> None:
    """Gli scarti dei singoli tiri si compensano dentro una partita.

    E' il motivo per cui la dashboard puo' mostrare l'xG di una partita con piu'
    fiducia di quanta ne meriti l'xG di un singolo tiro.
    """
    accordo = rendiconto.accordo()

    assert accordo is not None
    assert accordo.pearson_partita > accordo.pearson_tiro


def test_senza_rendiconto_le_tabelle_restano_vuote(monkeypatch: pytest.MonkeyPatch) -> None:
    """Una copia di lavoro incompleta deve dare una pagina spoglia, non un errore."""
    monkeypatch.setattr(rendiconto, "_misure", dict)

    assert rendiconto.calibrazione().empty
    assert rendiconto.pesi().empty
    assert rendiconto.categorie().empty
    assert rendiconto.ablazione().empty
    assert rendiconto.confronto().empty
    assert rendiconto.fuori_campione().empty
    assert rendiconto.accordo() is None
