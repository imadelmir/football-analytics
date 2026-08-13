"""La vista Squadre (M6-T4).

**La classifica e' ricostruita dai risultati, e si puo' verificare.** I punti
di Barcellona, Leicester e Juventus 2015/16 calcolati da
:mod:`football_analytics.classifica` coincidono con quelli veri — 91, 81, 91 —
e un test lo controlla a ogni esecuzione. E' l'unica pagina del progetto le cui
cifre hanno un riscontro esterno.

**Accanto ai punti ci sono gli xG, ed e' il motivo per cui la pagina esiste.**
Una classifica si trova ovunque; una classifica con di fianco quanti gol una
squadra *avrebbe dovuto* segnare no.

**Premendo una riga si apre la scheda della squadra**, che e' una pagina a se'
(``pages/Scheda.py``): sotto la tabella costringeva a scorrere mezzo schermo
per leggerla e altrettanto per tornare al confronto con le altre.

**Dove non c'e' un girone all'italiana la classifica sparisce.** Sommare i
punti delle diciotto finali di Champions dal 1971 al 2019 darebbe una tabella
dall'aria autorevole e senza significato.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import classifica
from football_analytics.config import ATTRIBUZIONE
from guscio import foglio, numero

if TYPE_CHECKING:
    from collections.abc import Sequence

    from streamlit.delta_generator import DeltaGenerator


st.set_page_config(page_title="Football Analytics — Squadre", layout="wide")

#: Le colonne della classifica, con l'intestazione e il formato.
COLONNE: tuple[tuple[str, str, str], ...] = (
    ("squadra", "Squadra", "%s"),
    ("giocate", "G", "%d"),
    ("vinte", "V", "%d"),
    ("pari", "N", "%d"),
    ("perse", "P", "%d"),
    ("gol_fatti", "GF", "%d"),
    ("gol_subiti", "GS", "%d"),
    ("differenza", "DR", "%+d"),
    ("punti", "Punti", "%d"),
    ("xg_fatti", "xG", "%.1f"),
    ("xg_subiti", "xGA", "%.1f"),
    ("scarto_xg", "Scarto", "%+.1f"),
)

#: Le colonne quando una classifica non ha senso: niente punti, solo xG.
COLONNE_SENZA_PUNTI: tuple[tuple[str, str, str], ...] = (
    ("squadra", "Squadra", "%s"),
    ("giocate", "G", "%d"),
    ("gol_fatti", "GF", "%d"),
    ("xg_fatti", "xG", "%.1f"),
    ("xg_subiti", "xGA", "%.1f"),
    ("differenza_xg", "Differenza xG", "%+.1f"),
    ("scarto_xg", "Scarto", "%+.1f"),
)

#: Le voci della scheda: etichetta, chiave e decimali.
VOCI: tuple[tuple[str, str, int], ...] = (
    ("Gol fatti", "gol_fatti", 0),
    ("xG generato", "xg_fatti", 1),
    ("Gol subiti", "gol_subiti", 0),
    ("xG concesso", "xg_subiti", 1),
    ("Tiri per partita", "tiri_per_partita", 1),
    ("xG per tiro", "xg_per_tiro", 3),
)

#: L'altezza della tabella cresce con le righe fino a un tetto.
ALTEZZA_RIGA: int = 36
ALTEZZA_TESTA: int = 42
ALTEZZA_MASSIMA: int = 780

#: Quante squadre nel confronto.
CONFRONTO: int = 5

#: Quanti riquadri di competizione per riga.
PER_RIGA: int = 3

#: Altezza del logo nei riquadri e nella testata, in pixel.
LOGO: int = 44
LOGO_TESTATA: int = 58


def nota_partite_mancanti(parziali: Sequence[str]) -> None:
    """L'avviso sui buchi dell'Open Data, in fondo e richiudibile.

    **Stava in cima e apriva l'elenco per esteso.** Con «Tutte le
    competizioni» sono centocinquanta nomi, cioe' dieci righe di riquadro
    giallo prima ancora della tabella: un avviso cosi' grande smette di essere
    letto e diventa un ostacolo. Qui il numero resta subito visibile e i nomi
    stanno dentro, per chi li vuole.

    Args:
        parziali: Le squadre con meno partite delle altre.
    """
    if not parziali:
        return
    with st.expander(
        f"Nell'Open Data mancano alcune partite: {len(parziali)} squadre ne hanno giocate "
        f"meno delle altre, quindi punti e totali sono più bassi di quelli ufficiali."
    ):
        st.caption(", ".join(parziali) + ".")


def tavola(tabella: pd.DataFrame, *, con_punti: bool) -> str | None:
    """Disegna la classifica, ordinabile e con le righe cliccabili.

    ``st.dataframe`` e non un markup fatto a mano: ordinare per xG subiti o per
    scarto e' esattamente cio' che si vuole fare guardando questa tabella.

    La configurazione delle colonne e' costruita qui dentro e non da una
    funzione a parte: il tipo che ``st.dataframe`` si aspetta vive in un modulo
    interno di Streamlit, e annotarlo legherebbe il progetto a un dettaglio che
    puo' cambiare in una versione minore.

    Args:
        tabella: Il risultato di :func:`classifica.tabella`.
        con_punti: Se mostrare punti e risultati o i soli aggregati xG.

    Returns:
        La squadra della riga su cui si e' premuto, oppure ``None``.
    """
    colonne = COLONNE if con_punti else COLONNE_SENZA_PUNTI
    chiavi = [chiave for chiave, _, _ in colonne if chiave in tabella.columns]
    scelta = st.dataframe(
        tabella[chiavi],
        width="stretch",
        hide_index=True,
        height=min(ALTEZZA_RIGA * len(tabella) + ALTEZZA_TESTA, ALTEZZA_MASSIMA),
        column_config={
            chiave: (
                st.column_config.TextColumn(intestazione)
                if formato == "%s"
                else st.column_config.NumberColumn(intestazione, format=formato)
            )
            for chiave, intestazione, formato in colonne
        },
        on_select="rerun",
        selection_mode="single-row",
        key="riga_classifica",
    )
    righe = scelta["selection"]["rows"]
    if not righe:
        return None
    return str(tabella.iloc[righe[0]]["squadra"])


def estremi(tabella: pd.DataFrame) -> None:
    """Chi ha segnato piu' e meno di quanto le occasioni dicessero.

    Args:
        tabella: Il risultato di :func:`classifica.tabella`.
    """
    if tabella.empty:
        return
    ordinata = tabella.sort_values("scarto_xg", ascending=False)
    voci = (
        ("Ha segnato più delle occasioni", ordinata.iloc[0]),
        ("Ha segnato meno delle occasioni", ordinata.iloc[-1]),
    )
    for colonna, (etichetta, riga) in zip(st.columns(2), voci, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="insight"><span class="etichetta">{etichetta}</span>'
                f'<span class="grande">{riga["squadra"]}</span>'
                f'<span class="nota">{numero(float(riga["gol_fatti"]))} gol contro '
                f"{numero(float(riga['xg_fatti']), 1)} xG</span></div>",
                unsafe_allow_html=True,
            )


def main() -> None:
    """Disegna la pagina."""
    partite_tutte = dati.leggi("matches")
    guscio.ritira_consegna()
    guscio.barra_laterale("Squadre")

    intestazione = st.columns([3.4, 1.2], vertical_alignment="bottom")
    # La chiave va riscritta a ogni giro. E' stata la chiave di un widget —
    # il menu della Home — e Streamlit scarta lo stato dei widget che non
    # vengono piu' disegnati: senza questa riga la competizione sopravvive a
    # un rerun e sparisce al successivo, riportando la pagina ai riquadri
    # mentre l'utente sta guardando una classifica.
    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione
    _, squadra = guscio.filtri(partite_tutte, intestazione[1:], con_competizione=False)

    tema = theme.applica(dati.gruppo_di(competizione, partite_tutte), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    # Tutto il corpo in un solo `st.empty()`, come in Giocatori: Streamlit
    # sostituisce un elemento alla volta, e passando dai riquadri alla
    # classifica si vedrebbe per un istante la testata nuova sopra e i riquadri
    # vecchi sotto.
    corpo = st.empty()
    with corpo.container():
        _corpo(partite_tutte, competizione, squadra, intestazione)


def _corpo(
    partite_tutte: pd.DataFrame,
    competizione: str | None,
    squadra: str | None,
    intestazione: Sequence[DeltaGenerator],
) -> None:
    """Il contenuto della pagina, qualunque sia lo stato della scelta.

    Args:
        partite_tutte: Tutte le partite del magazzino.
        competizione: La competizione scelta, oppure ``None``.
        squadra: La squadra scelta nel filtro, oppure ``None``.
        intestazione: Le colonne della testata, gia' create.
    """
    sotto = "Scegli un campionato per vederne la classifica"
    if competizione is not None:
        sotto = dati.nome_di(competizione)
    marchio = dati.insegna(competizione, LOGO_TESTATA) if competizione else ""
    with intestazione[0]:
        st.markdown(
            f'<div class="testata con-insegna">{marchio}'
            f'<div><h1 class="titolo">Squadre</h1>'
            f'<p class="sottotitolo">{sotto}</p></div></div>',
            unsafe_allow_html=True,
        )

    # Senza una competizione scelta non c'e' niente di sensato da mostrare: le
    # squadre di tutto il magazzino in una tabella sola non sono la classifica
    # di nulla, e le prime righe sarebbero un confronto fra la Liga e i
    # Mondiali.
    if competizione is None:
        guscio.riquadri_competizioni()
        st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)
        return

    partite = dati.filtra(partite_tutte, competizione)
    tiri = dati.filtra(dati.leggi("shots"), competizione)
    if partite.empty:
        st.info("Nessuna partita in questa selezione.")
        return

    con_punti = classifica.ha_classifica(partite)
    tabella = classifica.tabella(partite, tiri)

    if st.button("← Cambia competizione", key="cambia_competizione"):
        st.session_state[guscio.CONSEGNA_COMPETIZIONE] = None
        st.session_state[guscio.CONSEGNA_SQUADRA] = None
        st.rerun()

    # I numeri della squadra stanno nella scheda, non qui: questa pagina e' il
    # confronto fra squadre, e una striscia di indicatori sopra la classifica
    # rispondeva a una domanda che chi guarda una graduatoria non sta facendo.
    if squadra is not None and st.button(
        f"Apri la scheda completa · {squadra}", key="apri_scheda", width="stretch"
    ):
        st.switch_page("pages/Scheda.py")

    if not con_punti:
        st.caption(
            "Questa selezione non è un girone all'italiana, quindi non ha una "
            "classifica: restano i gol e gli xG, che si possono confrontare comunque."
        )
    with st.container(border=True):
        premuta = tavola(tabella, con_punti=con_punti)
    st.caption("Premi una riga per aprire la scheda della squadra.")
    # La scheda e' una pagina a se': sotto la tabella costringeva a scorrere
    # mezzo schermo per leggerla e altrettanto per tornare al confronto.
    if premuta is not None:
        st.session_state[guscio.CONSEGNA_SQUADRA] = premuta
        st.switch_page("pages/Scheda.py")
    estremi(tabella)
    nota_partite_mancanti(classifica.incomplete(tabella))

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
