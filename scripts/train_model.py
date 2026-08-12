"""Addestra i modelli xG, li valuta e **scrive i risultati su file**.

Il backlog colloca questo script a M5-T11. E' stato anticipato a M5-T6 per un
motivo pratico: fino a qui ogni misura passava da un frammento di codice
incollato nel terminale e da una tabella ricopiata a mano nella relazione. Sono
due passaggi manuali su numeri che poi finiscono in un documento pubblico, ed e'
esattamente il modo in cui a M5-T4 un log loss stimato a mente e' finito in un
messaggio di commit.

Da qui in avanti i numeri della milestone escono da un comando solo:

    uv run python scripts/train_model.py

e vengono scritti in ``docs/milestones/M5-risultati.md`` e nel corrispondente
``.json``. La relazione cita quei file invece di ricopiarli, e il ``.json``
conserva tutti i decimali per i confronti fra esecuzioni.

Lo script produce tre cose:

1. **Il confronto 2x2** — regressione logistica e gradient boosting, con e
   senza le variabili del fotogramma. E' il disegno che permette di attribuire
   ogni punto di guadagno o all'informazione o all'algoritmo.
2. **L'ablazione** — quanto vale ciascun gruppo di variabili spaziali preso da
   solo, per rispondere a «da dove viene il guadagno».
3. **I due modelli salvati** in ``models/``, quelli che la dashboard leggera'.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd
import sklearn

from football_analytics import features, metriche, model
from football_analytics.config import DATA_PROCESSED, PROJECT_ROOT

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import numpy.typing as npt
    from sklearn.pipeline import Pipeline

#: Dove finiscono i risultati. Sono file **generati**: non si modificano a mano.
CARTELLA_RISULTATI: Final[Path] = PROJECT_ROOT / "docs" / "milestones"
NOME_RISULTATI: Final[str] = "M5-risultati"

#: Gli iperparametri scelti in validazione incrociata a M5-T5, non sul test.
IPERPARAMETRI: Final[model.Iperparametri] = model.Iperparametri(
    iterazioni=200, tasso=0.10, foglie=15
)

#: I gruppi dell'ablazione. Le chiavi diventano le righe della tabella.
GRUPPI: Final[dict[str, tuple[str, ...]]] = {
    "base": (),
    "+ solo portiere": ("distanza_portiere", "portiere_avanzato"),
    "+ solo difensori": ("difensori_nel_cono", "avversari_vicini", "compagni_in_area"),
    "+ solo cono": ("difensori_nel_cono",),
    "+ tutto": features.VARIABILI_SPAZIALI,
}


def carica() -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Legge il magazzino e costruisce le variabili dei modelli.

    Returns:
        I tiri grezzi modellabili, la tabella delle variabili ridotta ai soli
        tiri con il fotogramma completo, e quanti ne sono stati scartati. I
        primi due condividono l'indice, cosi' l'xG di StatsBomb si riallinea
        senza chiavi di unione.

    Raises:
        FileNotFoundError: Se il magazzino non e' stato ancora costruito.
    """
    tiri_path = DATA_PROCESSED / "shots.parquet"
    fotogrammi_path = DATA_PROCESSED / "freeze_frames.parquet"
    for percorso in (tiri_path, fotogrammi_path):
        if not percorso.exists():
            msg = f"Manca {percorso}. Esegui prima: uv run python scripts/build_dataset.py"
            raise FileNotFoundError(msg)

    tiri = features.tiri_modellabili(pd.read_parquet(tiri_path))
    tutte = features.variabili_complete(tiri, pd.read_parquet(fotogrammi_path))
    completi = features.con_fotogramma_completo(tutte)
    return tiri, completi, len(tutte) - len(completi)


def costruisci(nome_classe: str, numeriche: Sequence[str]) -> Pipeline:
    """Costruisce una pipeline non addestrata della classe richiesta.

    Args:
        nome_classe: ``"logistica"`` oppure ``"alberi"``.
        numeriche: Le colonne continue da standardizzare.

    Returns:
        La pipeline pronta per l'addestramento.

    Raises:
        ValueError: Se la classe non e' fra quelle previste.
    """
    categoriche = list(features.VARIABILI_CATEGORICHE)
    booleane = list(features.VARIABILI_BOOLEANE)
    if nome_classe == "logistica":
        return model.pipeline_logistica(numeriche, categoriche, booleane)
    if nome_classe == "alberi":
        return model.pipeline_alberi(numeriche, categoriche, booleane, IPERPARAMETRI)
    msg = f"Classe di modello sconosciuta: {nome_classe!r}."
    raise ValueError(msg)


def confronto_incrociato(
    train: pd.DataFrame, test: pd.DataFrame, xg_statsbomb: pd.Series
) -> tuple[dict[str, dict[str, float]], dict[str, Pipeline]]:
    """Addestra le quattro combinazioni di classe e insieme di variabili.

    Args:
        train: Le righe di addestramento.
        test: Le righe di verifica.
        xg_statsbomb: L'xG di StatsBomb sulle stesse righe di verifica.

    Returns:
        I punteggi pronti per la tabella, e i modelli addestrati per nome.
    """
    insiemi: dict[str, tuple[Sequence[str], Sequence[str]]] = {
        "base": (features.VARIABILI_BASE, features.VARIABILI_NUMERICHE),
        "spaziale": (features.VARIABILI_COMPLETE, features.VARIABILI_NUMERICHE_COMPLETE),
    }

    previste: dict[str, npt.ArrayLike] = {}
    addestrati: dict[str, Pipeline] = {}
    for nome_insieme, (variabili, numeriche) in insiemi.items():
        for nome_classe in ("logistica", "alberi"):
            pipeline = costruisci(nome_classe, list(numeriche))
            addestrato = model.addestra(pipeline, train, variabili)
            nome = f"{nome_classe} {nome_insieme}"
            addestrati[nome] = addestrato
            previste[nome] = model.previsioni(addestrato, test, variabili)

    previste["StatsBomb"] = xg_statsbomb.to_numpy()
    return metriche.confronta(test["gol"], previste), addestrati


def ablazione(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Misura quanto vale ogni gruppo di variabili spaziali preso da solo.

    Usa sempre la regressione logistica: il confronto riguarda l'informazione,
    e tenere fissa la classe di modello e' cio' che lo rende leggibile.

    Args:
        train: Le righe di addestramento.
        test: Le righe di verifica.

    Returns:
        I punteggi pronti per la tabella, un gruppo per riga.
    """
    previste: dict[str, npt.ArrayLike] = {}
    for nome, aggiunte in GRUPPI.items():
        variabili = [*features.VARIABILI_BASE, *aggiunte]
        numeriche = [*features.VARIABILI_NUMERICHE, *aggiunte]
        addestrato = model.addestra(costruisci("logistica", numeriche), train, variabili)
        previste[nome] = model.previsioni(addestrato, test, variabili)
    return metriche.confronta(test["gol"], previste)


def markdown(titolo: str, punteggi: Mapping[str, Mapping[str, float]]) -> str:
    """Formatta i punteggi come tabella markdown, con la virgola decimale.

    Args:
        titolo: L'intestazione della sezione.
        punteggi: I punteggi restituiti da :func:`metriche.confronta`.

    Returns:
        Il frammento markdown, pronto per essere citato dalla relazione.
    """

    def virgola(valore: float, decimali: int) -> str:
        return f"{valore:.{decimali}f}".replace(".", ",")

    righe = [
        f"### {titolo}",
        "",
        "| Modello | Log loss | Brier | AUC | Guadagno | xG medio |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    righe.extend(
        f"| {nome} | {virgola(m['log_loss'], 5)} | {virgola(m['brier'], 5)} "
        f"| {virgola(m['auc'], 4)} | {virgola(m['guadagno_brier'] * 100, 1)} % "
        f"| {virgola(m['xg_medio'], 4)} |"
        for nome, m in punteggi.items()
    )
    return "\n".join(righe)


def markdown_calibrazione(curva: pd.DataFrame, nome: str) -> str:
    """Formatta una curva di calibrazione come tabella markdown.

    Args:
        curva: La tabella restituita da :func:`metriche.curva_di_calibrazione`.
        nome: Il modello a cui si riferisce.

    Returns:
        Il frammento markdown.
    """

    def virgola(valore: float, decimali: int) -> str:
        return f"{valore:.{decimali}f}".replace(".", ",")

    righe = [
        f"### Curva di calibrazione — {nome}",
        "",
        "| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    # Le colonne passano per numpy invece che per `itertuples`: per pandas-stubs
    # gli attributi di una riga hanno un tipo unione lunghissimo che comprende
    # date e stringhe, e ogni conversione andrebbe silenziata.
    colonne = {
        nome_colonna: curva[nome_colonna].to_numpy()
        for nome_colonna in (
            "gruppo",
            "tiri",
            "xg_previsto",
            "gol_osservati",
            "scarto",
            "scarto_in_se",
        )
    }
    righe.extend(
        f"| {int(colonne['gruppo'][i]) + 1} | {int(colonne['tiri'][i])} "
        f"| {virgola(colonne['xg_previsto'][i], 4)} "
        f"| {virgola(colonne['gol_osservati'][i], 4)} "
        f"| {virgola(colonne['scarto'][i], 4)} "
        f"| {virgola(colonne['scarto_in_se'][i], 1)} |"
        for i in range(len(curva))
    )
    return "\n".join(righe)


def markdown_accordo(per_tiro: Mapping[str, float], per_partita: Mapping[str, float]) -> str:
    """Formatta l'accordo con l'xG di StatsBomb come tabella markdown.

    Args:
        per_tiro: Il risultato di :func:`metriche.accordo`.
        per_partita: Il risultato di :func:`metriche.accordo_aggregato`.

    Returns:
        Il frammento markdown.
    """

    def virgola(valore: float, decimali: int) -> str:
        return f"{valore:.{decimali}f}".replace(".", ",")

    voci = (
        ("Correlazione di Pearson", "pearson", 4),
        ("Correlazione di Spearman", "spearman", 4),
        ("Scarto medio, con segno", "scarto_medio", 5),
        ("Scarto assoluto medio", "scarto_assoluto_medio", 5),
        ("Scarto assoluto mediano", "scarto_assoluto_mediano", 5),
        ("Scarto relativo mediano", "scarto_relativo_mediano", 4),
    )
    righe = [
        "### Accordo con l'xG di StatsBomb",
        "",
        "Non e' una misura di *quale* modello sia migliore — quella e' la tabella",
        "sopra — ma di **quanto i due si somiglino**.",
        "",
        "| | Per tiro | Per partita |",
        "| --- | ---: | ---: |",
    ]
    righe.extend(
        f"| {etichetta} | {virgola(per_tiro[chiave], decimali)} "
        f"| {virgola(per_partita[chiave], decimali)} |"
        for etichetta, chiave, decimali in voci
    )
    return "\n".join(righe)


def scrivi(
    incrociato: Mapping[str, Mapping[str, float]],
    gruppi: Mapping[str, Mapping[str, float]],
    contesto: Mapping[str, float],
    calibrazione: Mapping[str, pd.DataFrame],
    accordi: tuple[Mapping[str, float], Mapping[str, float]],
) -> tuple[Path, Path]:
    """Scrive i risultati in markdown e in JSON.

    Il markdown serve alla relazione, il JSON a confrontare due esecuzioni senza
    che l'arrotondamento nasconda una differenza.

    Args:
        incrociato: I punteggi del confronto 2x2.
        gruppi: I punteggi dell'ablazione.
        contesto: Conteggi della divisione e versioni delle librerie.
        calibrazione: Una curva di calibrazione per modello.
        accordi: L'accordo con StatsBomb, per tiro e per partita.

    Returns:
        I percorsi dei due file scritti.
    """
    ambiente = {
        "scikit_learn": sklearn.__version__,
        "pandas": pd.__version__,
    }

    CARTELLA_RISULTATI.mkdir(parents=True, exist_ok=True)
    percorso_md = CARTELLA_RISULTATI / f"{NOME_RISULTATI}.md"
    percorso_json = CARTELLA_RISULTATI / f"{NOME_RISULTATI}.json"

    def migliaia(valore: float) -> str:
        """Formatta un intero con il punto come separatore delle migliaia."""
        return f"{int(valore):,}".replace(",", ".")

    intestazione = (
        f"# Risultati misurati di M5\n\n"
        f"> **File generato da `scripts/train_model.py`. Non modificare a mano.**\n"
        f"> Rigenerabile con `uv run python scripts/train_model.py`.\n\n"
        f"Addestramento: {migliaia(contesto['tiri_train'])} tiri su "
        f"{migliaia(contesto['partite_train'])} partite. "
        f"Verifica: {migliaia(contesto['tiri_test'])} tiri su "
        f"{migliaia(contesto['partite_test'])} partite, mai viste.\n\n"
        f"Scartati {migliaia(contesto['scartati'])} tiri senza il portiere avversario "
        f"nel fotogramma, da tutti i modelli.\n\n"
        f"Ambiente: scikit-learn {ambiente['scikit_learn']}, pandas {ambiente['pandas']}.\n"
    )

    sezioni = [
        intestazione,
        markdown("Confronto fra classi di modello e insiemi di variabili", incrociato),
        markdown("Da dove viene il guadagno (regressione logistica)", gruppi),
    ]
    sezioni.append(markdown_accordo(*accordi))
    sezioni.extend(markdown_calibrazione(curva, nome) for nome, curva in calibrazione.items())

    percorso_md.write_text("\n\n".join(sezioni) + "\n", encoding="utf-8")
    percorso_json.write_text(
        json.dumps(
            {
                "contesto": dict(contesto),
                "ambiente": ambiente,
                "confronto": {k: dict(v) for k, v in incrociato.items()},
                "ablazione": {k: dict(v) for k, v in gruppi.items()},
                "calibrazione": {
                    nome: curva.to_dict(orient="records") for nome, curva in calibrazione.items()
                },
                "accordo": {"per_tiro": dict(accordi[0]), "per_partita": dict(accordi[1])},
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return percorso_md, percorso_json


def main() -> int:
    """Punto d'ingresso dello script.

    Returns:
        Zero se tutto e' andato bene.
    """
    analizzatore = argparse.ArgumentParser(description=__doc__)
    analizzatore.add_argument(
        "--senza-salvare",
        action="store_true",
        help="Non scrivere i modelli in models/, utile per una prova veloce.",
    )
    argomenti = analizzatore.parse_args()

    inizio = time.perf_counter()
    tiri, dati, scartati = carica()

    train, test = model.dividi_per_partita(dati)
    divisione = model.riepilogo_divisione(train, test)
    print(
        f"addestramento {len(train):,} tiri / {train['match_id'].nunique()} partite\n"
        f"verifica      {len(test):,} tiri / {test['match_id'].nunique()} partite\n"
        f"scartati      {scartati} tiri senza portiere inquadrato\n"
    )

    xg_statsbomb = tiri.loc[test.index, "xg_statsbomb"]
    incrociato, addestrati = confronto_incrociato(train, test, xg_statsbomb)
    print(metriche.tabella(incrociato), "\n")

    gruppi = ablazione(train, test)
    print(metriche.tabella(gruppi), "\n")

    # La curva si guarda per i due modelli che vanno in produzione e per
    # StatsBomb, che fa da riferimento esterno: sapere *dove* sbagliamo rispetto
    # a loro dice piu' di quanto sbagliamo in media.
    stime_per_curva = {
        "logistica base": model.previsioni(
            addestrati["logistica base"], test, features.VARIABILI_BASE
        ),
        "logistica spaziale": model.previsioni(
            addestrati["logistica spaziale"], test, features.VARIABILI_COMPLETE
        ),
        "StatsBomb": xg_statsbomb.to_numpy(),
    }
    calibrazione = {
        nome: metriche.curva_di_calibrazione(test["gol"], stime)
        for nome, stime in stime_per_curva.items()
    }
    for nome, curva in calibrazione.items():
        scarti = curva["scarto_in_se"].to_numpy()
        posizione = int(np.nanargmax(np.abs(scarti)))
        errore = incrociato[nome]["errore_calibrazione"]
        print(
            f"{nome:<20} errore di calibrazione {errore:.5f}   "
            f"gruppo peggiore {int(curva['gruppo'].to_numpy()[posizione]) + 1} su {len(curva)}: "
            f"{float(scarti[posizione]):+.1f} errori standard"
        )
    print()

    if not argomenti.senza_salvare:
        # La regressione logistica va in produzione per entrambi gli insiemi:
        # vince sulle variabili base, pareggia su quelle spaziali, pesa novanta
        # volte meno del gradient boosting e ha la calibrazione garantita dalla
        # forma del modello invece che verificata a posteriori. Su Streamlit
        # Cloud, con meno di 1 GB di RAM, la dimensione non e' un dettaglio.
        for nome_logico, chiave in (
            (model.NOME_BASE, "logistica base"),
            (model.NOME_SPAZIALE, "logistica spaziale"),
        ):
            percorso = model.salva_modello(addestrati[chiave], nome_logico)
            print(f"salvato {percorso.name} ({percorso.stat().st_size / 1024:.0f} KB)")

    nostro = stime_per_curva["logistica spaziale"]
    loro = xg_statsbomb.to_numpy()
    accordi = (
        metriche.accordo(nostro, loro),
        metriche.accordo_aggregato(nostro, loro, test["match_id"].to_numpy()),
    )
    print(
        f"accordo con StatsBomb: Pearson {accordi[0]['pearson']:.4f} per tiro, "
        f"{accordi[1]['pearson']:.4f} per partita   "
        f"scarto relativo mediano {accordi[0]['scarto_relativo_mediano']:.1%}\n"
    )

    contesto = {**divisione, "scartati": float(scartati)}
    percorso_md, percorso_json = scrivi(incrociato, gruppi, contesto, calibrazione, accordi)
    print(f"\nrisultati in {percorso_md.name} e {percorso_json.name}")
    print(f"durata {time.perf_counter() - inizio:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
