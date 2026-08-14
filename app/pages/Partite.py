"""La vista Partite (M6-T7).

**Si entra scegliendo una competizione**, come in Squadre e Giocatori: la stessa
schermata presa dal guscio, non copiata.

L'elenco esiste per essere ordinato — per xG, per differenza, per giornata — e
per aprire una partita. Le due liste sopra rispondono invece a una domanda che
l'elenco da solo non fa venire in mente: quali partite ha vinto la squadra
sbagliata.

Questa pagina non calcola niente: filtra, chiama
:mod:`football_analytics.partite` e disegna.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import partite
from football_analytics.config import ATTRIBUZIONE
from guscio import foglio, numero

st.set_page_config(page_title="Football Analytics — Partite", layout="wide")

#: Altezza di una riga e della testata della tabella, in pixel.
ALTEZZA_RIGA: int = 35
ALTEZZA_TESTA: int = 38
ALTEZZA_MASSIMA: int = 520


def indicatori(totali: dict[str, float]) -> None:
    """La striscia con i totali della competizione.

    Args:
        totali: Il risultato di :func:`partite.numeri`.
    """
    per_partita = totali["gol"] / totali["partite"] if totali["partite"] else 0.0
    voci = (
        ("Partite", numero(totali["partite"]), "nella competizione"),
        ("Gol", numero(totali["gol"]), f"{numero(per_partita, 2)} a partita"),
        ("xG totale", numero(totali["xg"], 1), "occasioni create"),
        (
            "Vinte dalla sfavorita",
            numero(totali["ribaltate"]),
            f"{totali['quota_ribaltate']:.0%} delle partite".replace(".", ","),
        ),
    )
    for colonna, (etichetta, valore, nota) in zip(st.columns(len(voci)), voci, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="scheda"><div class="cima">'
                f'<span class="etichetta">{etichetta}</span></div>'
                f'<span class="numero">{valore}</span>'
                f'<span class="nota">{nota}</span></div>',
                unsafe_allow_html=True,
            )


def riga_partita(riga: pd.Series) -> str:
    """Una partita in una riga di testo, per le liste dei casi notevoli.

    Args:
        riga: La partita.

    Returns:
        Il frammento HTML.
    """
    incontro = f"{riga['casa']} {riga['risultato']} {riga['ospite']}"
    xg = f"{numero(float(riga['xg_casa']), 2)} – {numero(float(riga['xg_ospite']), 2)} xG"
    return f'<div class="voce-scheda"><span>{incontro}</span><b>{xg}</b></div>'


def notevoli(selezione: pd.DataFrame) -> None:
    """Le due liste che l'elenco da solo non farebbe venire in mente.

    Args:
        selezione: Le partite della competizione.
    """
    sinistra, destra = st.columns(2)
    with sinistra, st.container(border=True):
        st.markdown("##### Vinte da chi aveva creato meno")
        contrarie = partite.ribaltate(selezione)
        if contrarie.empty:
            st.markdown(
                '<p class="vuoto">Nessuna, in questa selezione.</p>', unsafe_allow_html=True
            )
        else:
            righe = "".join(riga_partita(r) for _, r in contrarie.iterrows())
            st.markdown(f'<div class="voci">{righe}</div>', unsafe_allow_html=True)
        st.caption(
            f"Solo quando lo scarto di xG supera {numero(partite.SCARTO_MINIMO, 1)}: sotto, "
            "le due squadre hanno creato la stessa cosa."
        )
    with destra, st.container(border=True):
        st.markdown("##### Le più aperte")
        aperte = partite.piu_aperte(selezione)
        righe = "".join(riga_partita(r) for _, r in aperte.iterrows())
        st.markdown(f'<div class="voci">{righe}</div>', unsafe_allow_html=True)
        st.caption("Per xG complessivo delle due squadre, non per gol segnati.")


def tavola(elenco: pd.DataFrame) -> int | None:
    """L'elenco delle partite, ordinabile e con le righe cliccabili.

    Args:
        elenco: Il risultato di :func:`partite.elenco`.

    Returns:
        L'identificativo della partita su cui si e' premuto, oppure ``None``.
    """
    mostrate = elenco.drop(columns=["match_id"])
    scelta = st.dataframe(
        mostrate,
        width="stretch",
        hide_index=True,
        height=min(ALTEZZA_RIGA * len(elenco) + ALTEZZA_TESTA, ALTEZZA_MASSIMA),
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "giornata": st.column_config.NumberColumn("G", format="%d"),
            "casa": st.column_config.TextColumn("Casa"),
            "risultato": st.column_config.TextColumn("Risultato"),
            "ospite": st.column_config.TextColumn("Ospite"),
            "xg_casa": st.column_config.NumberColumn("xG casa", format="%.2f"),
            "xg_ospite": st.column_config.NumberColumn("xG ospite", format="%.2f"),
            "differenza_xg": st.column_config.NumberColumn("Δ xG", format="%+.2f"),
            "tiri_casa": st.column_config.NumberColumn("Tiri casa", format="%d"),
            "tiri_ospite": st.column_config.NumberColumn("Tiri ospite", format="%d"),
            "ribaltata": st.column_config.CheckboxColumn("Sfavorita"),
        },
        key="riga_partita",
    )
    # L'accesso e' per chiave e non per attributo, come nella vista Squadre:
    # `DataframeState` non espone `.selection` nei tipi di Streamlit.
    righe = scelta["selection"]["rows"]
    if not righe:
        return None
    # L'indice della riga scelta e' posizionale e si riferisce alla tabella
    # **mostrata**: va riportato su `elenco`, che ha ancora `match_id`.
    return int(elenco.iloc[righe[0]]["match_id"])


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Partite")
    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    guscio.ritira_consegna()
    competizione = st.session_state.get(guscio.CHIAVE_COMPETIZIONE, competizione)
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione

    tema = theme.applica(dati.gruppo_di(competizione, dati.leggi("matches")), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    # Tutto il corpo in un solo `st.empty()`, come nelle altre viste: Streamlit
    # sostituisce un elemento alla volta, e passando dai riquadri all'elenco si
    # vedrebbe per un istante la testata nuova sopra e i riquadri vecchi sotto.
    corpo = st.empty()
    with corpo.container():
        _corpo(competizione)


def _corpo(competizione: str | None) -> None:
    """Il contenuto della pagina, qualunque sia lo stato della scelta.

    Args:
        competizione: La competizione scelta, oppure ``None``.
    """
    sotto = "Scegli una competizione per vederne le partite"
    if competizione is not None:
        sotto = dati.nome_di(competizione)
    marchio = dati.insegna(competizione, guscio.LOGO_TESTATA) if competizione else ""
    st.markdown(
        f'<div class="testata con-insegna">{marchio}'
        f'<div><h1 class="titolo">Partite</h1>'
        f'<p class="sottotitolo">{sotto}</p></div></div>',
        unsafe_allow_html=True,
    )

    if competizione is None:
        guscio.riquadri_competizioni()
        st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)
        return

    if st.button("← Cambia competizione", key="cambia_competizione_partite"):
        st.session_state[guscio.CONSEGNA_COMPETIZIONE] = None
        st.rerun()

    tutte = dati.filtra(dati.leggi("matches"), competizione)
    if tutte.empty:
        st.info("Nessuna partita in questa selezione.")
        return

    # Il filtro usa la chiave condivisa: chi arriva dalla scheda di una squadra
    # la trova gia' impostata, ed e' il criterio di chiusura di M6-T7.
    _, squadra = guscio.filtri(tutte, [st.container()], con_competizione=False)
    selezione = partite.di_squadra(tutte, squadra)
    if selezione.empty:
        st.info("Nessuna partita per questa squadra.")
        return

    indicatori(partite.numeri(selezione))
    notevoli(selezione)

    with st.container(border=True):
        st.markdown("##### Tutte le partite")
        premuta = tavola(partite.elenco(selezione))
    st.caption("Premi una riga per aprire la partita.")

    if premuta is not None:
        st.session_state[guscio.CONSEGNA_PARTITA] = premuta
        st.switch_page("pages/Incontro.py")

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
