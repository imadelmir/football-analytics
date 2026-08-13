"""Lettura del magazzino, con la cache di Streamlit (M6-T3, poi M6-T13).

**La cache sta qui e non in `src/`.** ``st.cache_data`` e' un meccanismo
dell'interfaccia: le funzioni del pacchetto devono restare pure e verificabili
senza Streamlit, e chi le usa da uno script o da un test non deve trascinarsi
dietro una cache che non gli serve.

Senza cache la dashboard rileggerebbe i Parquet **a ogni interazione** —
Streamlit riesegue lo script da capo a ogni click — e su Streamlit Cloud, che
concede meno di 1 GB di RAM, sarebbe il modo piu' rapido per far morire l'app
al primo utente che tocca un filtro.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from football_analytics import albo, config
from football_analytics.config import CHAMPIONS_FINALI, DATA_PROCESSED


@st.cache_data(show_spinner="Carico il magazzino…")
def leggi(tabella: str) -> pd.DataFrame:
    """Legge una tabella del magazzino, una volta sola per sessione.

    Args:
        tabella: Il nome senza estensione, per esempio ``"shots"``.

    Returns:
        La tabella.

    Raises:
        FileNotFoundError: Se il magazzino non e' stato costruito.
    """
    percorso = DATA_PROCESSED / f"{tabella}.parquet"
    if not percorso.exists():
        msg = (
            f"Manca {percorso.name}. Costruisci prima il magazzino:\n"
            "    uv run python scripts/build_dataset.py"
        )
        raise FileNotFoundError(msg)
    return pd.read_parquet(percorso)


@st.cache_data(show_spinner=False)
def competizioni() -> list[str]:
    """Le competizioni presenti nel magazzino, in ordine alfabetico.

    Returns:
        I nomi delle competizioni.
    """
    return sorted(leggi("matches")["competizione"].unique())


#: Dove stanno i loghi delle competizioni.
LOGHI: Path = Path(__file__).parent / "assets" / "loghi"

#: Il marchio dell'app, quello nella barra laterale.
MARCHIO: Path = Path(__file__).parent / "assets" / "marchio.png"


def marchio() -> str:
    """Il marchio dell'app come URI incorporabile nel CSS.

    Va in linea e non come file servito perche' il marchio finisce dentro un
    ``background-image``, e Streamlit non espone una cartella statica senza
    attivare ``enableStaticServing``: un interruttore in piu' da ricordare in
    fase di deploy per un file da sedici chilobyte.

    Returns:
        Il marchio come ``data:`` URI, pronto per ``url(...)``.
    """
    codificato = base64.b64encode(MARCHIO.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{codificato}"


def logo_di(chiave: str) -> Path | None:
    """Il logo di una competizione, se c'e'.

    **La mappa e' per chiave e non per ``competition_id``**, a differenza di
    quella dei temi: Euro 2020 ed Euro 2024 condividono l'identificativo ma
    hanno due loghi diversi, uno per edizione. Il colore e' della competizione,
    il marchio dell'edizione.

    Args:
        chiave: La chiave della competizione.

    Returns:
        Il percorso del file, oppure ``None`` se non esiste. Chi chiama deve
        reggere l'assenza: i loghi non sono dati, sono decorazione, e una
        competizione nuova non deve rompere la pagina per un file mancante.
    """
    percorso = LOGHI / f"{NOMI_LOGHI.get(chiave, chiave)}.svg"
    return percorso if percorso.exists() else None


#: Il nome del file per ciascuna competizione del magazzino.
NOMI_LOGHI: dict[str, str] = {
    "la_liga_2015_16": "la_liga",
    "premier_2015_16": "premier",
    "serie_a_2015_16": "serie_a",
    "ligue1_2015_16": "ligue1",
    "champions_finali": "champions",
    "mondiali_2022": "mondiali",
    "coppa_africa_2023": "coppa_africa",
    "euro_2024": "euro_2024",
    "euro_2020": "euro_2020",
}


def insegna(chiave: str, altezza: int) -> str:
    """Il logo di una competizione come immagine in linea, ad altezza fissa.

    **Ad altezza e non a larghezza**, ed e' il punto: i nove loghi hanno
    proporzioni molto diverse — il tondo della Serie A, il fuso dei Mondiali —
    e fissando la larghezza quello stretto diventava alto il doppio degli
    altri. Fissando l'altezza stanno tutti sulla stessa riga.

    Il file viene incorporato invece che servito: sono SVG di pochi kilobyte,
    e cosi' il markup della targa resta un pezzo solo di HTML invece di un
    elemento Streamlit accanto a un altro, che porterebbe i propri margini.

    Args:
        chiave: La chiave della competizione.
        altezza: L'altezza in pixel.

    Returns:
        Il tag ``img``, oppure stringa vuota se il logo non c'e'.
    """
    percorso = logo_di(chiave)
    if percorso is None:
        return ""
    codificato = base64.b64encode(percorso.read_bytes()).decode("ascii")
    return (
        f'<img class="insegna" src="data:image/svg+xml;base64,{codificato}" '
        f'style="height:{altezza}px" alt="" />'
    )


def nome_di(chiave: str) -> str:
    """Il solo nome della competizione, senza la stagione.

    Serve al titolo della pagina, dove «La Liga · 2015/2016» sarebbe una riga
    di intestazione piena di dettagli che stanno gia' sotto, accanto al
    periodo.

    Args:
        chiave: La chiave della competizione.

    Returns:
        Il nome esteso, oppure la chiave immutata se non e' nota.
    """
    try:
        return config.competizione(chiave).nome
    except ValueError:
        return chiave


def stagione_di(chiave: str) -> str:
    """La stagione di una competizione, per i riquadri di scelta.

    Args:
        chiave: La chiave della competizione.

    Returns:
        La stagione, oppure stringa vuota se la chiave non e' nota.
    """
    try:
        return config.competizione(chiave).stagione
    except ValueError:
        return ""


def etichetta_di(chiave: str) -> str:
    """Il nome leggibile di una competizione, per i menu.

    Il filtro mostrava la chiave del magazzino — ``la_liga_2015_16`` — che e'
    un identificativo tecnico: va benissimo nei nomi dei file e nei filtri di
    pandas, non in un menu. Il nome esteso esiste gia' in
    :mod:`football_analytics.config`, quindi non va inventato qui.

    Il **valore** dell'opzione resta la chiave: cambia solo cio' che si legge,
    e nessuna delle funzioni che filtrano o scelgono il tema deve saperlo.

    Args:
        chiave: La chiave della competizione, oppure una voce speciale come
            ``"Tutte"``.

    Returns:
        Il nome esteso con la stagione, oppure la chiave immutata se non
        corrisponde a una competizione nota.
    """
    try:
        voce = config.competizione(chiave)
    except ValueError:
        return chiave
    return f"{nome_di(chiave)} · {voce.stagione}"


def filtra(tabella: pd.DataFrame, competizione: str | None) -> pd.DataFrame:
    """Restringe una tabella a una competizione.

    Args:
        tabella: La tabella da filtrare.
        competizione: Il nome della competizione, oppure ``None`` per tutte.

    Returns:
        Le sole righe della competizione scelta.
    """
    if competizione is None:
        return tabella
    return tabella[tabella["competizione"] == competizione]


def squadre_di(partite: pd.DataFrame, competizione: str | None) -> list[str]:
    """Le squadre presenti in una competizione, in ordine alfabetico.

    Args:
        partite: La tabella delle partite.
        competizione: Il nome della competizione, oppure ``None`` per tutte.

    Returns:
        I nomi delle squadre.
    """
    parte = filtra(partite, competizione)
    return sorted(set(parte["casa"].astype(str)) | set(parte["ospite"].astype(str)))


def gruppo_di(competizione: str | None, partite: pd.DataFrame) -> str:
    """Trova il gruppo di una competizione, per scegliere il tema.

    Args:
        competizione: Il nome della competizione, oppure ``None``.
        partite: La tabella delle partite.

    Returns:
        Il gruppo, oppure stringa vuota se la selezione ne comprende piu' di
        uno — nel qual caso il tema resta quello predefinito.
    """
    if competizione is None:
        return ""
    gruppi = list(partite.loc[partite["competizione"] == competizione, "gruppo"].unique())
    return str(gruppi[0]) if len(gruppi) == 1 else ""


@st.cache_data(show_spinner=False)
def albo_champions() -> pd.DataFrame:
    """L'albo d'oro delle finali di Champions presenti nel magazzino.

    Legge **tutto** il magazzino e non la selezione corrente: le finali sono una
    competizione a se', e le coppe di una squadra non smettono di esistere
    perche' si sta guardando la Serie A.

    Returns:
        Il risultato di :func:`football_analytics.albo.albo`.
    """
    chiave = CHAMPIONS_FINALI.chiave
    partite = leggi("matches")
    tiri = leggi("shots")
    return albo.albo(
        partite[partite["competizione"] == chiave],
        tiri[tiri["competizione"] == chiave],
    )
