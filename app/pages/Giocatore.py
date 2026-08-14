"""La scheda del singolo giocatore (M6-T6).

**Il radar confronta con la media del reparto, non con l'intero campionato.**
E' il criterio di chiusura della task, ed e' anche l'unico modo in cui un radar
dice qualcosa: misurare un terzino contro tutti i giocatori della Serie A lo
mette sotto la mediana su ogni asse offensivo, il che e' vero e inutile.

**Il reparto e non la posizione StatsBomb.** Le ventiquattro posizioni sono
piu' precise, ma otto hanno meno di dieci giocatori qualificati: una «media del
ruolo» calcolata su tre persone non e' una media. I quattro reparti stanno fra
i 96 e i 162, e :data:`~football_analytics.giocatori.MINIMO_CONFRONTO` blocca il
radar quando anche quelli non bastano.

**I portieri hanno una scheda ridotta, e la pagina lo dice.** Nel magazzino non
ci sono parate ne' clean sheet: un radar costruito su tiri e gol li
descriverebbe come attaccanti pessimi, che e' una risposta a una domanda che
nessuno ha fatto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import giocatori, viz
from football_analytics.config import ATTRIBUZIONE, SOGLIA_MINUTI
from guscio import SENZA_BARRA, foglio, numero

if TYPE_CHECKING:
    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Giocatore", layout="wide")

#: Il reparto che non ha una scheda completa.
PORTIERE: str = "Portiere"


def anagrafica(riga: pd.Series) -> None:
    """Nome, squadra, reparto e posizione.

    Args:
        riga: La riga del giocatore.
    """
    st.markdown(
        f'<div class="testata"><h1 class="titolo">{riga["giocatore_breve"]}</h1>'
        f'<p class="sottotitolo">{riga["squadra"]}'
        f'<span class="periodo">{riga["reparto"]} · {riga["ruolo"]}</span></p></div>',
        unsafe_allow_html=True,
    )


def indicatori(riga: pd.Series) -> None:
    """I cinque numeri principali del giocatore.

    Args:
        riga: La riga del giocatore.
    """
    tiri = float(riga["tiri"])
    scarto = float(riga["gol_meno_xg"])
    voci = (
        ("Presenze", numero(float(riga["partite"])), f"{numero(float(riga['minuti']))} minuti"),
        ("Gol", numero(float(riga["gol"])), f"{numero(float(riga['gol_90']), 2)} ogni 90'"),
        ("xG", numero(float(riga["xg"]), 1), f"{numero(float(riga['xg_90']), 2)} ogni 90'"),
        ("Tiri", numero(tiri), f"{numero(float(riga['tiri_90']), 1)} ogni 90'"),
        (
            "Gol − xG",
            f"{'+' if scarto >= 0 else '−'}{numero(abs(scarto), 1)}",
            "sopra le attese" if scarto >= 0 else "sotto le attese",
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


def confronto(tutti: pd.DataFrame, riga: pd.Series, tema: Tema) -> None:
    """Il radar contro la mediana del reparto.

    Args:
        tutti: I giocatori della competizione, gia' sommati per giocatore.
        riga: La riga del giocatore.
        tema: La palette attiva.
    """
    posizioni = giocatori.percentili(tutti, int(riga["giocatore_id"]))
    st.markdown(f"##### Confronto con il reparto {riga['reparto']}")
    if not posizioni:
        st.markdown(
            '<p class="vuoto">Il reparto non ha abbastanza giocatori sopra la soglia '
            "perché un confronto significhi qualcosa.</p>",
            unsafe_allow_html=True,
        )
        return

    assi = {etichetta: posizioni[colonna] for etichetta, colonna, _ in giocatori.ASSI_RADAR}
    st.plotly_chart(viz.radar(assi, tema), width="stretch", config=SENZA_BARRA)
    st.caption(
        f"Ogni asse è un percentile fra i {numero(posizioni['confronto'])} "
        f"{riga['reparto'].lower()} con almeno {numero(SOGLIA_MINUTI)} minuti: il tratteggio "
        "è la mediana del reparto, non del campionato."
    )


def dettaglio_tiri(tiri: pd.DataFrame) -> None:
    """Il tabellone dei tiri, dal più pericoloso.

    Args:
        tiri: Il risultato di :func:`giocatori.tiri_di`.
    """
    st.dataframe(
        tiri,
        width="stretch",
        hide_index=True,
        height=320,
        column_config={
            "minuto": st.column_config.NumberColumn("Min", format="%d"),
            "avversario": st.column_config.TextColumn("Avversario"),
            "esito": st.column_config.TextColumn("Esito"),
            "xg_statsbomb": st.column_config.NumberColumn("xG", format="%.3f"),
            "parte_corpo": st.column_config.TextColumn("Parte del corpo"),
            "tipo": st.column_config.TextColumn("Tipo"),
        },
    )


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Giocatori")
    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    guscio.ritira_consegna()
    competizione = st.session_state.get(guscio.CHIAVE_COMPETIZIONE, competizione)
    scelto: int | None = st.session_state.get(guscio.CHIAVE_GIOCATORE)
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione
    st.session_state[guscio.CHIAVE_GIOCATORE] = scelto

    tema = theme.applica(dati.gruppo_di(competizione, dati.leggi("matches")), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    if scelto is None:
        st.info("Scegli un giocatore dalla tabella per vederne la scheda.")
        if st.button("← Torna ai giocatori", key="torna_giocatori_vuoto"):
            st.switch_page("pages/Giocatori.py")
        return

    tutti = giocatori.con_reparto(
        giocatori.per_giocatore(dati.filtra(dati.leggi("player_stats"), competizione))
    )
    suo = tutti[tutti["giocatore_id"] == scelto]
    if suo.empty:
        st.info("Questo giocatore non compare nella selezione.")
        if st.button("← Torna ai giocatori", key="torna_giocatori_assente"):
            st.switch_page("pages/Giocatori.py")
        return

    riga = suo.iloc[0]
    anagrafica(riga)
    if st.button("← Torna ai giocatori", key="torna_giocatori"):
        st.switch_page("pages/Giocatori.py")

    indicatori(riga)
    _corpo(tutti, riga, scelto, competizione, tema)


def _corpo(
    tutti: pd.DataFrame,
    riga: pd.Series,
    scelto: int,
    competizione: str | None,
    tema: Tema,
) -> None:
    """Il resto della scheda, che cambia a seconda del reparto.

    Args:
        tutti: I giocatori della competizione.
        riga: La riga del giocatore.
        scelto: Il suo identificativo.
        competizione: La competizione scelta.
        tema: La palette attiva.
    """
    tocchi = dati.filtra(dati.leggi("touches"), competizione)
    suoi_tocchi = tocchi[tocchi["giocatore_id"] == scelto]

    if riga["reparto"] == PORTIERE:
        # Scheda ridotta, e dichiarata: senza parate ne' clean sheet nel
        # magazzino, radar e mappa dei tiri direbbero solo che un portiere non
        # segna — una risposta a una domanda che nessuno ha fatto.
        st.info(
            "Scheda ridotta: l'Open Data di StatsBomb non contiene parate né clean sheet, "
            "quindi radar e mappa dei tiri direbbero soltanto che un portiere non tira."
        )
        with st.container(border=True):
            st.markdown("##### Dove tocca il pallone")
            st.plotly_chart(
                viz.mappa_tocchi(suoi_tocchi, tema), width="stretch", config=SENZA_BARRA
            )
        st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)
        return

    tiri = dati.filtra(dati.leggi("shots"), competizione)
    suoi_tiri = tiri[tiri["giocatore_id"] == scelto]

    sinistra, destra = st.columns(2)
    with sinistra, st.container(border=True):
        confronto(tutti, riga, tema)
    with destra, st.container(border=True):
        st.markdown("##### Dove tocca il pallone")
        st.plotly_chart(viz.mappa_tocchi(suoi_tocchi, tema), width="stretch", config=SENZA_BARRA)
        st.caption(
            "Densità dei tocchi sul campo intero: il gioco di un terzino sta nella sua metà."
        )

    sotto_sinistra, sotto_destra = st.columns(2)
    with sotto_sinistra, st.container(border=True):
        st.markdown("##### I suoi tiri")
        st.plotly_chart(
            viz.shot_map(suoi_tiri, tema, altezza=440), width="stretch", config=SENZA_BARRA
        )
    with sotto_destra, st.container(border=True):
        st.markdown("##### Gol contro xG, partita dopo partita")
        curva = giocatori.andamento(tiri, scelto)
        if curva.empty:
            st.markdown('<p class="vuoto">Nessun tiro nella selezione.</p>', unsafe_allow_html=True)
        else:
            st.plotly_chart(
                viz.linee(
                    list(range(1, len(curva) + 1)),
                    {"gol": list(curva["gol"]), "xG cumulato": list(curva["xg"])},
                    tema,
                    altezza=300,
                    a_gradini=True,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )
            st.caption(
                "Le partite in cui ha tirato, in ordine: l'asse conta quelle, non le giornate."
            )

    with st.container(border=True):
        st.markdown("##### Dettaglio dei tiri")
        dettaglio_tiri(giocatori.tiri_di(tiri, scelto))

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
