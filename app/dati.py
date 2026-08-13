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

import pandas as pd
import streamlit as st

from football_analytics import config
from football_analytics.config import DATA_PROCESSED


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
