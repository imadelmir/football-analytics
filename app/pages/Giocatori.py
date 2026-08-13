"""La vista Giocatori (M6-T5).

**Si entra scegliendo una competizione, e non e' un passaggio in piu'.** Le
graduatorie su tutto il magazzino metterebbero nella stessa colonna un
attaccante di Ligue 1 con 34 presenze e uno visto per tre partite a un
Mondiale: l'ordinamento sembrerebbe significativo e non lo sarebbe. La stessa
schermata di scelta della vista Squadre, presa dal guscio invece che copiata.

**Le graduatorie si fermano a chi ha giocato almeno 500 minuti**, e la pagina
lo scrive. Sotto quella quota i valori per novanta minuti esplodono — un gol in
un tempo giocato fa 1,00 gol/90 — e la classifica finirebbe piena di nomi che
nessuno ha visto giocare. Chi resta fuori non sparisce: la tabella in fondo li
tiene tutti, con i minuti in chiaro.

Questa pagina non calcola niente: filtra, chiama
:mod:`football_analytics.giocatori` e disegna.
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
from guscio import SENZA_BARRA, barre, foglio, numero

if TYPE_CHECKING:
    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Giocatori", layout="wide")

#: Quante righe nelle graduatorie a barre.
QUANTI: int = 8

#: Quanti nomi per lato nel grafico gol contro xG.
NOMINATI: int = 6

#: Le graduatorie a barre: titolo, colonna, decimali, dal peggiore.
CLASSIFICHE: tuple[tuple[str, str, int, bool], ...] = (
    ("Marcatori", "gol", 0, False),
    ("xG generato", "xg", 1, False),
    ("Gol sopra le attese", "gol_meno_xg", 1, False),
    ("Gol sotto le attese", "gol_meno_xg", 1, True),
)


def indicatori(totali: dict[str, float], migliore: pd.DataFrame) -> None:
    """La striscia con i totali della competizione.

    Args:
        totali: Il risultato di :func:`giocatori.numeri`.
        migliore: La riga del capocannoniere, eventualmente vuota.
    """
    nome, quanti = "—", "nessun gol"
    if not migliore.empty:
        riga = migliore.iloc[0]
        nome, quanti = str(riga["giocatore_breve"]), f"{numero(riga['gol'])} gol"

    voci: tuple[tuple[str, str, str], ...] = (
        ("Giocatori", numero(totali["giocatori"]), "nella competizione"),
        (
            "Sopra i minuti",
            numero(totali["qualificati"]),
            f"almeno {numero(SOGLIA_MINUTI)} minuti",
        ),
        ("Gol", numero(totali["gol"]), "segnati su azione e su rigore"),
        ("xG totale", numero(totali["xg"], 1), "occasioni create"),
        ("Capocannoniere", nome, quanti),
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


def classifiche(tabella: pd.DataFrame, tema: Tema) -> None:
    """Le quattro graduatorie a barre, due per riga.

    Args:
        tabella: I giocatori della selezione, gia' filtrati per reparto.
        tema: La palette attiva.
    """
    for riga in range(0, len(CLASSIFICHE), 2):
        for colonna, (titolo, campo, decimali, crescente) in zip(
            st.columns(2), CLASSIFICHE[riga : riga + 2], strict=False
        ):
            voci = giocatori.graduatoria(tabella, campo, QUANTI, crescente=crescente)
            with colonna, st.container(border=True):
                st.markdown(f"##### {titolo}")
                if voci.empty:
                    st.markdown(
                        '<p class="vuoto">Nessun giocatore sopra la soglia.</p>',
                        unsafe_allow_html=True,
                    )
                    continue
                # `barre` disegna in proporzione al massimo, che con i valori
                # negativi sarebbe il meno peggio: per le graduatorie al
                # contrario si mostra il valore assoluto e il segno resta nel
                # titolo, che dice «sotto le attese».
                da_disegnare = voci.copy()
                if crescente:
                    da_disegnare[campo] = da_disegnare[campo].abs()
                st.markdown(
                    barre(da_disegnare, campo, "giocatore_breve", tema, decimali=decimali),
                    unsafe_allow_html=True,
                )


def reparti(tabella: pd.DataFrame) -> None:
    """Da dove arrivano i gol, reparto per reparto.

    Args:
        tabella: I giocatori della selezione.
    """
    riassunto = giocatori.per_reparto(tabella)
    if riassunto.empty:
        return
    # Le colonne passano da numpy e non da `itertuples`: per pandas-stubs il
    # tipo di un attributo di riga e' un'unione che comprende date e stringhe,
    # e ogni lettura andrebbe silenziata con un `type: ignore`. E' la stessa
    # ragione per cui `Panoramica.riga_massima` restituisce un dizionario.
    righe = "".join(
        f'<div class="voce-scheda"><span>{nome}</span>'
        f"<b>{numero(float(gol))} gol · {quota:.0%}</b></div>"
        for nome, gol, quota in zip(
            riassunto["reparto"].to_numpy(),
            riassunto["gol"].to_numpy(),
            riassunto["quota_gol"].to_numpy(),
            strict=True,
        )
    )
    st.markdown(f'<div class="voci">{righe}</div>', unsafe_allow_html=True)


def tabella_completa(tabella: pd.DataFrame) -> None:
    """Tutti i giocatori, soglia compresa, in una tabella ordinabile.

    **Anche chi sta sotto i 500 minuti.** Le graduatorie lo escludono per una
    ragione statistica, ma escluderlo anche da qui lo farebbe sparire senza
    spiegazione: qui i minuti sono in chiaro e ognuno vede perche' un nome non
    compare piu' in alto.

    Args:
        tabella: I giocatori della selezione.
    """
    colonne = [
        "giocatore_breve",
        "squadra",
        "reparto",
        "partite",
        "minuti",
        "tiri",
        "gol",
        "xg",
        "gol_meno_xg",
        "xg_90",
    ]
    st.dataframe(
        tabella[colonne].sort_values("gol", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "giocatore_breve": st.column_config.TextColumn("Giocatore"),
            "squadra": st.column_config.TextColumn("Squadra"),
            "reparto": st.column_config.TextColumn("Reparto"),
            "partite": st.column_config.NumberColumn("PG", format="%d"),
            "minuti": st.column_config.NumberColumn("Minuti", format="%d"),
            "tiri": st.column_config.NumberColumn("Tiri", format="%d"),
            "gol": st.column_config.NumberColumn("Gol", format="%d"),
            "xg": st.column_config.NumberColumn("xG", format="%.1f"),
            "gol_meno_xg": st.column_config.NumberColumn("Gol − xG", format="%+.1f"),
            "xg_90": st.column_config.NumberColumn("xG/90", format="%.2f"),
        },
    )


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Giocatori")
    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    guscio.ritira_consegna()
    competizione = st.session_state.get(guscio.CHIAVE_COMPETIZIONE, competizione)
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione

    tema = theme.applica(dati.gruppo_di(competizione, dati.leggi("matches")), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    # **Tutto il corpo dentro un solo `st.empty()`.**
    #
    # Streamlit applica le modifiche un elemento alla volta: passando dai
    # riquadri di scelta alle graduatorie si vedeva per un istante la testata
    # nuova sopra e i riquadri vecchi sotto, con i pulsanti «Apri» finiti
    # dentro le schede dei numeri. Un contenitore con chiave non basta, perche'
    # il difetto non e' l'identita' dei singoli elementi ma il fatto che siano
    # tanti: `st.empty()` e' un posto solo, e riempirlo di nuovo cancella tutto
    # quello che c'era prima in una volta.
    corpo = st.empty()
    with corpo.container():
        _corpo(competizione, tema)


def _corpo(competizione: str | None, tema: Tema) -> None:
    """Il contenuto della pagina, qualunque sia lo stato della scelta.

    Args:
        competizione: La competizione scelta, oppure ``None``.
        tema: La palette attiva.
    """
    sotto = "Scegli un campionato per vederne i giocatori"
    if competizione is not None:
        sotto = dati.nome_di(competizione)
    marchio = dati.insegna(competizione, guscio.LOGO_TESTATA) if competizione else ""
    st.markdown(
        f'<div class="testata con-insegna">{marchio}'
        f'<div><h1 class="titolo">Giocatori</h1>'
        f'<p class="sottotitolo">{sotto}</p></div></div>',
        unsafe_allow_html=True,
    )

    if competizione is None:
        guscio.riquadri_competizioni()
        st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)
        return

    if st.button("← Cambia competizione", key="cambia_competizione_giocatori"):
        st.session_state[guscio.CONSEGNA_COMPETIZIONE] = None
        st.rerun()

    # La somma per giocatore viene **prima** del reparto: chi ha cambiato
    # squadra a gennaio ha due righe nel magazzino, e una classifica di
    # competizione che non le unisce mostra meta' dei suoi gol.
    tutti = giocatori.con_reparto(
        giocatori.per_giocatore(dati.filtra(dati.leggi("player_stats"), competizione))
    )
    if tutti.empty:
        st.info("Nessun giocatore in questa selezione.")
        return

    indicatori(giocatori.numeri(tutti), giocatori.graduatoria(tutti, "gol", 1))

    scelti = st.pills(
        "Reparto",
        list(giocatori.REPARTI),
        selection_mode="multi",
        key="filtro_reparto",
    )
    selezione = giocatori.filtra_reparto(tutti, scelti or [])

    conta = giocatori.numeri(selezione)
    if conta["qualificati"] == 0:
        # Succede davvero, e la pagina deve dire perche' invece di mostrare
        # quattro riquadri vuoti: nelle finali di Champions il massimo giocato
        # e' 432 minuti, perche' sono diciassette partite sparse su
        # cinquant'anni. Abbassare la soglia solo li' vorrebbe dire avere due
        # regole diverse a seconda della vista.
        massimo = int(selezione["minuti"].max()) if not selezione.empty else 0
        st.info(
            f"In questa selezione nessuno raggiunge i {numero(SOGLIA_MINUTI)} minuti: "
            f"il massimo giocato è {numero(massimo)}. Le graduatorie per novanta minuti "
            "non sarebbero confrontabili, quindi restano fuori — la tabella qui sotto "
            "tiene comunque tutti."
        )
    else:
        st.caption(
            f"Le graduatorie considerano chi ha giocato almeno {numero(SOGLIA_MINUTI)} "
            f"minuti: {numero(conta['qualificati'])} giocatori su "
            f"{numero(conta['giocatori'])}. "
            "Sotto quella soglia i valori per novanta minuti diventano rumore."
        )

        classifiche(selezione, tema)

        sinistra, destra = st.columns([1.6, 1])
        with sinistra, st.container(border=True):
            st.markdown("##### Gol contro xG")
            st.plotly_chart(
                viz.attese_contro_realizzato(
                    giocatori.qualificati(selezione),
                    tema,
                    nome="giocatore_breve",
                    etichette=NOMINATI,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )
            st.caption(
                "Un punto per giocatore. La diagonale è gol = xG: sopra chi ha realizzato "
                "più di quanto le occasioni promettessero, sotto chi ha sprecato."
            )
        with destra, st.container(border=True):
            st.markdown("##### Da dove arrivano i gol")
            reparti(tutti)
            st.caption(
                "Sui reparti il filtro non si applica: la quota ha senso solo sul totale "
                "della competizione."
            )

    with st.container(border=True):
        st.markdown("##### Tutti i giocatori")
        tabella_completa(selezione)

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
