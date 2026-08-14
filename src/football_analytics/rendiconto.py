"""I numeri gia' misurati del modello xG, letti e non ricalcolati (M6-T9).

**Questo modulo non addestra niente e non carica nessun modello.** Legge tre
file JSON che M5 ha prodotto e che stanno in git:

- ``docs/milestones/M5-risultati.json`` — calibrazione, coefficienti,
  ablazione, accordo con StatsBomb, applicazione alle finali;
- ``models/xg_base.json`` e ``models/xg_360.json`` — le schede delle due
  varianti che vanno in produzione.

**Il motivo e' una regola del progetto, non una comodita'.** Un numero non si
cambia senza rigenerarlo dal codice: se la dashboard ricalcolasse la
calibrazione al volo, prima o poi mostrerebbe un valore diverso da quello
scritto in ``M5-risultati.md``, e nessuno saprebbe quale dei due credere. Cosi'
invece i due non possono divergere, perche' sono lo stesso file.

**Un secondo motivo, piu' concreto.** I ``.pkl`` sono ancora fuori da git fino
a M7-T1, e caricarne uno significa eseguire codice serializzato: una pagina che
si limita a leggere JSON funziona su Streamlit Cloud il giorno del deploy senza
aprire quella superficie.

Le tre avvertenze sulla lettura dei coefficienti — categorie identificate a
meno di una costante, «a parita' di tutto il resto», il segno e' una direzione
e non una causa — stanno in :func:`~football_analytics.model.coefficienti` e la
pagina le ripete a chi guarda.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final

import pandas as pd

from football_analytics import config
from football_analytics.features import VARIABILI_SPAZIALI

if TYPE_CHECKING:
    from pathlib import Path

#: Il rendiconto completo di M5.
#:
#: Il percorso e' lo stesso che ``scripts/train_model.py`` usa per scrivere.
#: Sono due costanti distinte in due file distinti, quindi possono divergere:
#: un test verifica che il file esista qui e sia leggibile, cosi' se un giorno
#: lo script cambiasse cartella la suite se ne accorge invece che la pagina.
RISULTATI: Final[Path] = config.PROJECT_ROOT / "docs" / "milestones" / "M5-risultati.json"

#: Le due varianti che vanno in produzione: chiave del file, nome in pagina,
#: e la frase che dice cosa le distingue.
#:
#: **I nomi in pagina sono «Base» e «360», ovunque.** Nel rendiconto di M5 le
#: stesse due cose si chiamano «logistica base» e «logistica spaziale», perche'
#: li' andavano distinte anche dalle varianti ad alberi. Portarsi dietro due
#: nomi per lo stesso modello e' il modo piu' rapido per far credere a chi
#: guarda che i modelli siano quattro.
VARIANTI: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "xg_base",
        "Base",
        "Sei variabili: da dove parte il tiro, con quale parte del corpo, "
        "da quale tipo di giocata e se il tiratore era sotto pressione.",
    ),
    (
        "xg_360",
        "360",
        "Le sei di prima piu' cinque che descrivono chi c'era intorno, "
        "ricavate dai fotogrammi 360 di StatsBomb.",
    ),
)

#: Come si chiamano in pagina i modelli del rendiconto di M5.
NOMI: Final[dict[str, str]] = {
    "riferimento": "Riferimento",
    "logistica base": "Base",
    "alberi base": "Alberi (base)",
    "logistica spaziale": "360",
    "alberi spaziale": "Alberi (360)",
    "StatsBomb": "StatsBomb",
}

#: I tre modelli di cui M5 ha salvato la curva di calibrazione.
CALIBRATI: Final[tuple[str, ...]] = ("logistica base", "logistica spaziale", "StatsBomb")

#: Come si chiamano in pagina i passi dell'ablazione.
#:
#: Le chiavi arrivano da ``GRUPPI`` in ``scripts/train_model.py`` e sono scritte
#: per chi legge un terminale. In pagina servono nomi che dicano *cosa* si sta
#: aggiungendo, non la sigla del gruppo.
PASSI: Final[dict[str, str]] = {
    "riferimento": "Nessun modello",
    "base": "Modello base",
    "+ solo portiere": "+ posizione del portiere",
    "+ solo difensori": "+ difensori e compagni attorno",
    "+ solo cono": "+ difensori nel cono di tiro",
    "+ tutto": "Modello 360",
}

#: I nomi leggibili delle variabili numeriche e booleane.
ETICHETTE: Final[dict[str, str]] = {
    "distanza": "Distanza dalla porta",
    "angolo": "Ampiezza della porta vista dal tiratore",
    "sotto_pressione": "Tiratore sotto pressione",
    "difensori_nel_cono": "Difensori nel cono di tiro",
    "distanza_portiere": "Distanza del portiere",
    "portiere_avanzato": "Portiere fuori dai pali",
    "avversari_vicini": "Avversari a ridosso",
    "compagni_in_area": "Compagni in area",
}

#: I valori delle variabili categoriche, tradotti.
#:
#: Il prefisso resta nell'etichetta finale — «Parte del corpo · testa» — perche'
#: senza, ``tipo_Corner`` e ``schema_From Corner`` diventerebbero due righe
#: chiamate entrambe «Da corner»: due cose diverse con lo stesso nome nella
#: stessa tabella.
VALORI: Final[dict[str, dict[str, str]]] = {
    "parte_corpo": {
        "Head": "testa",
        "Right Foot": "piede destro",
        "Left Foot": "piede sinistro",
        "Other": "altro",
    },
    "tipo": {
        "Open Play": "su azione",
        "Free Kick": "punizione diretta",
        "Corner": "direttamente da corner",
        "Penalty": "rigore",
        "Kick Off": "calcio d'inizio",
    },
    "schema": {
        "Regular Play": "azione manovrata",
        "From Corner": "corner",
        "From Free Kick": "punizione",
        "From Throw In": "rimessa laterale",
        "From Goal Kick": "rinvio dal fondo",
        "From Counter": "contropiede",
        "From Keeper": "rilancio del portiere",
        "From Kick Off": "calcio d'inizio",
        "From Kick": "calcio piazzato",
        "Other": "altro",
    },
}

#: Il prefisso di ciascuna variabile categorica e come si legge in pagina.
PREFISSI: Final[tuple[tuple[str, str], ...]] = (
    ("parte_corpo_", "Parte del corpo"),
    ("tipo_", "Tipo di tiro"),
    ("schema_", "Origine dell'azione"),
)


@dataclass(frozen=True)
class Variante:
    """Una delle due varianti del modello, come sta nel suo file JSON.

    Attributes:
        chiave: Il nome del file in ``models/``, senza estensione.
        etichetta: Come si chiama in pagina.
        descrizione: Cosa la distingue dall'altra, in una frase.
        classe: La classe scikit-learn del passo finale della pipeline.
        variabili: Le variabili in ingresso.
        log_loss: Log loss sul test.
        brier: Brier score sul test.
        auc: Area sotto la curva ROC sul test.
        errore_calibrazione: Scarto medio assoluto fra xG previsto e gol
            osservati, decile per decile.
        guadagno_brier: Quanto il Brier migliora rispetto al riferimento, in
            quota sul riferimento stesso.
    """

    chiave: str
    etichetta: str
    descrizione: str
    classe: str
    variabili: tuple[str, ...]
    log_loss: float
    brier: float
    auc: float
    errore_calibrazione: float
    guadagno_brier: float


@dataclass(frozen=True)
class Contesto:
    """Su quanti dati il modello e' stato addestrato e verificato.

    Attributes:
        tiri_train: Tiri di addestramento.
        tiri_test: Tiri di verifica.
        partite_train: Partite di addestramento.
        partite_test: Partite di verifica.
        tiri_applicazione: Tiri delle finali di Champions, mai visti.
        finali_applicazione: Quante finali.
        quota_gol: La quota di gol nel test, cioe' il tasso base.
        scartati: Tiri esclusi per fotogramma 360 incompleto.
        scikit_learn: La versione usata per addestrare.
        pandas: La versione usata per addestrare.
        addestrato_il: Quando, in ISO 8601.
    """

    tiri_train: int
    tiri_test: int
    partite_train: int
    partite_test: int
    tiri_applicazione: int
    finali_applicazione: int
    quota_gol: float
    scartati: int
    scikit_learn: str
    pandas: str
    addestrato_il: str


@dataclass(frozen=True)
class Accordo:
    """Quanto il nostro xG somiglia a quello ufficiale di StatsBomb.

    Attributes:
        pearson_tiro: Correlazione lineare sul singolo tiro.
        pearson_partita: Correlazione lineare sull'xG totale di una partita.
        scarto_assoluto_mediano: Scarto tipico sul singolo tiro, in xG.
        scarto_partita: Scarto tipico sull'xG di una partita, in xG.
        totale_nostro: xG totale sul test, secondo noi.
        totale_altrui: xG totale sul test, secondo StatsBomb.
    """

    pearson_tiro: float
    pearson_partita: float
    scarto_assoluto_mediano: float
    scarto_partita: float
    totale_nostro: float
    totale_altrui: float


@lru_cache(maxsize=1)
def _misure() -> dict[str, Any]:
    """Legge il rendiconto di M5, una volta sola per processo.

    Returns:
        Il JSON completo.
    """
    with RISULTATI.open(encoding="utf-8") as flusso:
        letto: dict[str, Any] = json.load(flusso)
    return letto


@lru_cache(maxsize=len(VARIANTI))
def _scheda(chiave: str) -> dict[str, Any]:
    """Legge la scheda di un modello addestrato.

    Args:
        chiave: Il nome del file in ``models/``, senza estensione.

    Returns:
        Il JSON della scheda.
    """
    with (config.MODELS_DIR / f"{chiave}.json").open(encoding="utf-8") as flusso:
        letto: dict[str, Any] = json.load(flusso)
    return letto


def disponibile() -> bool:
    """Dice se i numeri congelati sono tutti al loro posto.

    Serve alla pagina per dichiarare l'assenza invece di esplodere: i tre file
    stanno in git, quindi in condizioni normali e' sempre vero, ma su una copia
    di lavoro incompleta la vista deve dirlo e non morire.

    Returns:
        Vero se il rendiconto e le due schede esistono.
    """
    return RISULTATI.exists() and all(
        (config.MODELS_DIR / f"{chiave}.json").exists() for chiave, _, _ in VARIANTI
    )


def varianti() -> list[Variante]:
    """Le due varianti di produzione, dalle rispettive schede.

    Returns:
        Base e 360, in quest'ordine.
    """
    elenco = []
    for chiave, etichetta, descrizione in VARIANTI:
        scheda = _scheda(chiave)
        metriche: dict[str, float] = scheda["metriche"]
        elenco.append(
            Variante(
                chiave=chiave,
                etichetta=etichetta,
                descrizione=descrizione,
                classe=str(scheda["classe"]),
                variabili=tuple(str(voce) for voce in scheda["variabili"]),
                log_loss=float(metriche["log_loss"]),
                brier=float(metriche["brier"]),
                auc=float(metriche["auc"]),
                errore_calibrazione=float(metriche["errore_calibrazione"]),
                guadagno_brier=float(metriche["guadagno_brier"]),
            )
        )
    return elenco


def contesto() -> Contesto:
    """Su quanti dati sono stati misurati i numeri della pagina.

    Returns:
        Il contesto dell'addestramento.
    """
    misure = _misure()
    dati: dict[str, float] = misure["contesto"]
    ambiente: dict[str, str] = misure["ambiente"]
    return Contesto(
        tiri_train=int(dati["tiri_train"]),
        tiri_test=int(dati["tiri_test"]),
        partite_train=int(dati["partite_train"]),
        partite_test=int(dati["partite_test"]),
        tiri_applicazione=int(dati["tiri_applicazione"]),
        finali_applicazione=int(dati["finali_applicazione"]),
        quota_gol=float(dati["gol_test"]),
        scartati=int(dati["scartati"]),
        scikit_learn=str(ambiente["scikit_learn"]),
        pandas=str(ambiente["pandas"]),
        addestrato_il=str(_scheda(VARIANTI[0][0])["addestrato_il"]),
    )


def calibrazione() -> pd.DataFrame:
    """Le curve di calibrazione dei tre modelli, in forma lunga.

    **Decili e non fasce di larghezza fissa.** Con fasce fisse l'ultima
    conterrebbe una manciata di tiri e il suo punto ballerebbe di dieci punti
    percentuali per due gol in piu': i decili tengono ~842 tiri per punto, e
    l'errore standard riportato dice quanto ciascuno e' affidabile.

    Returns:
        Una riga per modello e decile, con ``modello``, ``gruppo``, ``tiri``,
        ``xg_previsto``, ``gol_osservati``, ``errore_standard``, ``scarto`` e
        ``scarto_in_se`` — lo scarto misurato in errori standard, che e' il
        numero da guardare per sapere se un punto fuori dalla retta e' un
        difetto o rumore. Vuota se il rendiconto non contiene la sezione.
    """
    curve: dict[str, list[dict[str, float]]] = _misure().get("calibrazione", {})
    righe = [
        {
            "modello": NOMI.get(nome, nome),
            "gruppo": int(punto["gruppo"]),
            "tiri": int(punto["tiri"]),
            "xg_previsto": float(punto["xg_previsto"]),
            "gol_osservati": float(punto["gol_osservati"]),
            "errore_standard": float(punto["errore_standard"]),
            "scarto": float(punto["scarto"]),
            "scarto_in_se": float(punto["scarto_in_se"]),
        }
        for nome in CALIBRATI
        if nome in curve
        for punto in curve[nome]
    ]
    return pd.DataFrame(righe)


def etichetta_variabile(nome: str) -> str:
    """Traduce il nome tecnico di una variabile in una voce leggibile.

    Args:
        nome: Il nome prodotto dal preprocessore, per esempio
            ``"schema_From Corner"``.

    Returns:
        L'etichetta da mostrare.
    """
    if nome in ETICHETTE:
        return ETICHETTE[nome]
    for prefisso, testa in PREFISSI:
        if nome.startswith(prefisso):
            grezzo = nome[len(prefisso) :]
            colonna = prefisso.rstrip("_")
            return f"{testa} · {VALORI[colonna].get(grezzo, grezzo.lower())}"
    return nome


def pesi() -> pd.DataFrame:
    """Le variabili continue e booleane, ordinate per quanto pesano.

    **Solo queste, e le categoriche stanno in :func:`categorie`.** Metterle
    nella stessa classifica sarebbe la lettura sbagliata di cui avverte
    :func:`~football_analytics.model.coefficienti`: le categorie sono
    codificate senza scartarne un livello, quindi i loro coefficienti sono
    identificati solo a meno di una costante. Nel rendiconto la costante si
    vede a occhio nudo — la somma dei coefficienti vale −1,0389 identica per
    tutte e tre le variabili categoriche — e trascinerebbe «tipo di tiro» in
    cima a una classifica dove non ha titolo di comparire.

    **La scala e' l'odds ratio per deviazione standard**, cioe' la risposta a
    «quale variabile pesa di piu'»: mette sullo stesso metro variabili con
    unita' incompatibili, metri contro conteggi di giocatori.

    La colonna ``peso`` e' il logaritmo in base due dell'odds ratio, ed e'
    l'unica scala onesta per un grafico a barre divergenti: dimezzare e
    raddoppiare la probabilita' relativa devono dare barre lunghe uguali e di
    verso opposto, e con l'odds ratio grezzo non succede — 0,5 disterebbe 0,5
    dall'unita' e 2,0 ne disterebbe 1,0.

    Returns:
        Una riga per variabile con ``variabile``, ``odds_ratio``, ``peso``,
        ``per_unita``, ``unita``, ``direzione`` e ``spaziale`` — vero se la
        variabile viene dai fotogrammi 360. Vuota se il rendiconto non
        contiene la sezione.
    """
    righe = [
        {
            "variabile": etichetta_variabile(str(voce["variabile"])),
            "grezzo": str(voce["variabile"]),
            "odds_ratio": float(voce["odds_ratio_per_deviazione_standard"]),
            "peso": math.log2(float(voce["odds_ratio_per_deviazione_standard"])),
            "per_unita": float(voce["odds_ratio_per_unita"]),
            "unita": float(voce["unita_per_deviazione_standard"]),
            "direzione": str(voce["direzione"]),
            "spaziale": str(voce["variabile"]) in VARIABILI_SPAZIALI,
        }
        for voce in _misure().get("coefficienti", [])
        if str(voce["tipo"]) != "categoria"
        and float(voce["odds_ratio_per_deviazione_standard"]) > 0
    ]
    if not righe:
        return pd.DataFrame()
    tabella = pd.DataFrame(righe)
    return tabella.reindex(tabella["peso"].abs().sort_values(ascending=False).index).reset_index(
        drop=True
    )


def categorie() -> pd.DataFrame:
    """I livelli di ciascuna variabile categorica, centrati dentro la variabile.

    **Il centraggio non e' cosmesi, e' la correzione dell'unico difetto che
    rende quei coefficienti illeggibili.** Con una codifica che non scarta
    nessun livello, ogni variabile categorica e' definita a meno di una
    costante: nel rendiconto quella costante e' visibile — la somma dei
    coefficienti e' −1,0389 per tutte e tre — e sposta in blocco tutti i
    livelli verso il basso. Togliendo la media dentro la variabile, la costante
    sparisce e restano le differenze, che sono la parte identificata.

    Dopo il centraggio la lettura torna quella che un tecnico si aspetta: a
    parita' di distanza e angolo, il colpo di testa vale circa la meta' di un
    tiro di piede.

    Returns:
        Una riga per livello con ``gruppo`` (il nome della variabile),
        ``livello``, ``odds_ratio`` centrato e ``peso`` in base due. Vuota se
        il rendiconto non contiene la sezione.
    """
    per_gruppo: dict[str, list[tuple[str, float]]] = {}
    for voce in _misure().get("coefficienti", []):
        grezzo = str(voce["variabile"])
        if str(voce["tipo"]) != "categoria":
            continue
        for prefisso, testa in PREFISSI:
            if grezzo.startswith(prefisso):
                per_gruppo.setdefault(testa, []).append((grezzo, float(voce["coefficiente"])))
                break

    righe: list[dict[str, str | float]] = []
    for testa, voci in per_gruppo.items():
        media = sum(valore for _, valore in voci) / len(voci)
        righe.extend(
            {
                "gruppo": testa,
                "livello": etichetta_variabile(grezzo).split(" · ")[-1],
                "odds_ratio": math.exp(valore - media),
                "peso": (valore - media) / math.log(2),
            }
            for grezzo, valore in voci
        )
    if not righe:
        return pd.DataFrame()
    return (
        pd.DataFrame(righe)
        .sort_values(["gruppo", "peso"], ascending=[True, False])
        .reset_index(drop=True)
    )


def per_nome(tabella: pd.DataFrame, chiave: str, colonna: str) -> dict[str, float]:
    """Estrae una colonna numerica indicizzata dal nome della riga.

    **Esiste per un problema di tipi, ed e' onesto dirlo.** Il modo naturale di
    leggere una cella e' ``tabella.loc["Modello base", "brier"]``, ma per
    pandas-stubs quel valore ha un tipo unione che comprende date, stringhe e
    numeri complessi: ``float()`` non lo accetta, e mypy si ferma. Le
    alternative erano un ``cast`` in ogni punto di lettura — sei nel progetto,
    fra pagina e test — oppure questa funzione, che fa la conversione una volta
    sola e restituisce un dizionario con un tipo vero.

    Ne guadagna anche la lettura: chi chiama scrive ``brier["Modello 360"]``
    invece di una doppia indicizzazione con un ``float`` attorno.

    Args:
        tabella: Una delle tabelle di questo modulo.
        chiave: La colonna da cui prendere i nomi, per esempio ``"passo"``.
        colonna: La colonna numerica da estrarre.

    Returns:
        Il valore di ``colonna`` per ogni nome. Vuoto se la tabella lo e'.
    """
    if tabella.empty:
        return {}
    nomi = tabella[chiave].astype(str).to_numpy()
    numeri = tabella[colonna].to_numpy(dtype=float)
    return {str(nome): float(valore) for nome, valore in zip(nomi, numeri, strict=True)}


def _metriche(sezione: str, ordine: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Estrae una sezione di confronto fra modelli come tabella.

    Args:
        sezione: La chiave del rendiconto: ``confronto``, ``ablazione`` o
            ``fuori_campione``.
        ordine: Le chiavi da tenere, nell'ordine voluto. Senza, si tiene
            l'ordine del file.

    Returns:
        Una riga per modello con ``modello``, ``log_loss``, ``brier``, ``auc``
        ed ``errore_calibrazione``.
    """
    blocco: dict[str, dict[str, float]] = _misure().get(sezione, {})
    chiavi = ordine if ordine is not None else tuple(blocco)
    righe = [
        {
            "chiave": chiave,
            "log_loss": float(blocco[chiave]["log_loss"]),
            "brier": float(blocco[chiave]["brier"]),
            "auc": float(blocco[chiave]["auc"]),
            "errore_calibrazione": float(blocco[chiave]["errore_calibrazione"]),
        }
        for chiave in chiavi
        if chiave in blocco
    ]
    return pd.DataFrame(righe)


def confronto() -> pd.DataFrame:
    """Tutti i modelli provati a M5, sullo stesso test.

    Returns:
        Una riga per modello con ``modello`` leggibile e le quattro metriche.
    """
    tabella = _metriche("confronto")
    if tabella.empty:
        return tabella
    tabella.insert(0, "modello", [NOMI.get(chiave, chiave) for chiave in tabella["chiave"]])
    return tabella.drop(columns="chiave")


def ablazione() -> pd.DataFrame:
    """Quanto vale ciascun gruppo di variabili 360, aggiunto da solo.

    **Aggiunto da solo, non tolto dal totale.** Le variabili spaziali sono
    correlate fra loro: togliendone una dal modello completo il suo contributo
    viene assorbito dalle altre e sembra nullo. Aggiungendola alla base si vede
    quanto porta davvero.

    Returns:
        Una riga per passo con ``passo`` leggibile e le quattro metriche, nel
        proprio ordine di lettura.
    """
    tabella = _metriche("ablazione", tuple(PASSI))
    if tabella.empty:
        return tabella
    tabella.insert(0, "passo", [PASSI.get(chiave, chiave) for chiave in tabella["chiave"]])
    return tabella.drop(columns="chiave")


def fuori_campione() -> pd.DataFrame:
    """I punteggi sulle finali di Champions, mai entrate nell'addestramento.

    Returns:
        Una riga per modello con ``modello`` leggibile e le quattro metriche.
    """
    tabella = _metriche("fuori_campione")
    if tabella.empty:
        return tabella
    tabella.insert(0, "modello", [NOMI.get(chiave, chiave) for chiave in tabella["chiave"]])
    return tabella.drop(columns="chiave")


def accordo() -> Accordo | None:
    """Quanto il nostro xG somiglia a quello ufficiale di StatsBomb.

    Returns:
        L'accordo, o ``None`` se il rendiconto non contiene la sezione.
    """
    blocco: dict[str, dict[str, float]] = _misure().get("accordo", {})
    if "per_tiro" not in blocco or "per_partita" not in blocco:
        return None
    per_tiro = blocco["per_tiro"]
    per_partita = blocco["per_partita"]
    return Accordo(
        pearson_tiro=float(per_tiro["pearson"]),
        pearson_partita=float(per_partita["pearson"]),
        scarto_assoluto_mediano=float(per_tiro["scarto_assoluto_mediano"]),
        scarto_partita=float(per_partita["scarto_assoluto_mediano"]),
        totale_nostro=float(per_tiro["xg_totale_nostro"]),
        totale_altrui=float(per_tiro["xg_totale_altrui"]),
    )
