"""La scheda di una singola squadra (M6-T4).

**E' una pagina a se' e non un pannello in fondo alla classifica.** Stava
sotto la tabella, e con venti squadre significava scorrere mezzo schermo per
vedere i propri numeri e altrettanto per tornare a confrontarli con gli altri.
Separandola, la classifica resta un elenco e la scheda un ritratto.

La squadra arriva dalla pagina Squadre attraverso le chiavi di consegna: senza
una squadra scelta, questa pagina non ha niente da dire e riporta indietro.

Una cosa del disegno non c'e' ed e' voluto — **il numero di maglia**: non
esiste nei dati, e inventarlo per far somigliare la rete a una formazione
sarebbe l'unica cosa falsa della pagina. Al suo posto c'e' il nome.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import classifica, panoramica, passaggi, viz
from football_analytics.config import ATTRIBUZIONE
from guscio import SENZA_BARRA, barre, distintivo, foglio, numero

if TYPE_CHECKING:
    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Scheda squadra", layout="wide")

#: Le voci della scheda: etichetta, chiave e decimali.
VOCI: tuple[tuple[str, str, int], ...] = (
    ("Gol fatti", "gol_fatti", 0),
    ("xG generato", "xg_fatti", 1),
    ("Gol subiti", "gol_subiti", 0),
    ("xG concesso", "xg_subiti", 1),
    ("Differenza reti", "differenza", 0),
    ("Tiri totali", "tiri_fatti", 0),
    ("Tiri per partita", "tiri_per_partita", 1),
    ("Tiri concessi per partita", "tiri_subiti_per_partita", 1),
    ("xG per partita", "xg_per_partita", 2),
    ("xG per tiro", "xg_per_tiro", 3),
)

#: Le voci in percentuale, che non passano da :func:`numero`.
QUOTE: tuple[tuple[str, str], ...] = (("Conversione", "conversione"),)

#: Quante squadre nel confronto.
CONFRONTO: int = 5

#: Quanti realizzatori mostrare.
QUANTE: int = 5


def anagrafica(squadra: str, numeri: dict[str, float], *, con_punti: bool) -> None:
    """Il riquadro con nome, posizione e i sei valori della squadra.

    Args:
        squadra: Il nome della squadra.
        numeri: Il risultato di :func:`classifica.scheda`.
        con_punti: Se la selezione ha una classifica, quindi una posizione.
    """
    posto = ""
    if con_punti:
        posto = (
            f"{numero(numeri['posizione'])}° posto · "
            f"{numero(numeri['punti'])} punti · {numero(numeri['giocate'])} partite · "
            f"{numero(numeri['vinte'])}V {numero(numeri['pari'])}N {numero(numeri['perse'])}P"
        )
    else:
        posto = (
            f"{numero(numeri['giocate'])} partite · "
            f"{numero(numeri['vinte'])}V {numero(numeri['pari'])}N {numero(numeri['perse'])}P"
        )

    righe = "".join(
        f'<div class="voce-scheda"><span>{etichetta}</span>'
        f"<b>{numero(numeri[chiave], decimali)}</b></div>"
        for etichetta, chiave, decimali in VOCI
    ) + "".join(
        f'<div class="voce-scheda"><span>{etichetta}</span>'
        f"<b>{f'{numeri[chiave]:.1%}'.replace('.', ',')}</b></div>"
        for etichetta, chiave in QUOTE
    )
    st.markdown(
        f'<div class="capo">{distintivo(squadra)}'
        f'<div><div class="nome-squadra">{squadra}</div>'
        f'<div class="posto">{posto}</div></div></div>'
        f'<div class="voci">{righe}</div>',
        unsafe_allow_html=True,
    )


def evidenza(numeri: dict[str, float]) -> None:
    """Lo scarto fra gol e occasioni, in chiusura di pagina.

    E' una conclusione, non un dato dell'elenco: fra le voci dell'anagrafica
    sembrava la settima riga di una tabella.

    **Sta in fondo, sopra l'attribuzione**, ed e' la terza posizione provata.
    In fondo alla colonna di sinistra si incastrava nella scheda della riga
    successiva; dentro quella del confronto la stringeva contro le barre. In
    coda alla pagina non ha nessuna scheda accanto a cui appiccicarsi, e la
    riga che chiude una scheda e' anche il posto giusto per una conclusione.

    Args:
        numeri: Il risultato di :func:`classifica.scheda`.
    """
    scarto = numeri["scarto_xg"]
    verso = "sopra" if scarto >= 0 else "sotto"
    st.markdown(
        f'<div class="evidenza">{"+" if scarto >= 0 else "−"}{numero(abs(scarto), 1)} '
        f"gol {verso} l'xG</div>",
        unsafe_allow_html=True,
    )


def scheda(
    squadra: str,
    tavole: dict[str, pd.DataFrame],
    tema: Tema,
    *,
    con_punti: bool,
) -> None:
    """Il dettaglio della squadra scelta, sotto la classifica.

    Args:
        squadra: Il nome della squadra.
        tavole: Le tabelle gia' filtrate: ``tiri``, ``giocatori``, ``passi``
            della sola squadra, piu' ``partite`` e ``tabella`` dell'intera
            competizione, che servono per il confronto e per la curva.
        tema: La palette attiva.
        con_punti: Se la selezione ha una classifica.
    """
    tiri = tavole["tiri"]
    giocatori = tavole["giocatori"]
    passi = tavole["passi"]
    partite = tavole["partite"]
    tabella = tavole["tabella"]
    numeri = classifica.scheda(tabella, squadra)
    if not numeri:
        st.info("Questa squadra non compare nella selezione.")
        return

    sinistra, centro, destra = st.columns([1.15, 1.5, 1.35])
    with sinistra, st.container(border=True):
        anagrafica(squadra, numeri, con_punti=con_punti)

    with centro, st.container(border=True):
        st.markdown("##### Rete dei passaggi")
        nodi = passaggi.titolari(giocatori)
        archi = passaggi.rete(passi, nodi)
        st.plotly_chart(
            viz.rete_passaggi(nodi, archi, passaggi.coinvolgimento(archi, nodi), tema),
            width="stretch",
            config=SENZA_BARRA,
        )
        st.caption("Posizione media in campo · spessore della linea = numero di passaggi")

    with destra, st.container(border=True):
        st.markdown("##### Mappa dei tiri")
        st.plotly_chart(
            viz.per_esito(panoramica.tiri_di_gioco(tiri), tema),
            width="stretch",
            config=SENZA_BARRA,
        )
        st.caption("Area del cerchio = xG")

    sotto_sinistra, sotto_destra = st.columns(2)
    with sotto_sinistra, st.container(border=True):
        st.markdown("##### Confronto con le prime del campionato")
        migliori = tabella.nlargest(CONFRONTO, "xg_fatti")
        if squadra not in set(migliori["squadra"]):
            migliori = pd.concat([migliori, tabella[tabella["squadra"] == squadra]])
        st.markdown(
            barre(migliori, "xg_fatti", "squadra", tema, decimali=1),
            unsafe_allow_html=True,
        )

    with sotto_destra, st.container(border=True):
        st.markdown("##### Gol contro xG, partita dopo partita")
        curva = classifica.andamento_squadra(partite, squadra)
        if curva.empty:
            st.markdown('<p class="vuoto">Nessun dato nella selezione.</p>', unsafe_allow_html=True)
        else:
            st.plotly_chart(
                viz.linee(
                    list(curva["data"]),
                    {"gol": list(curva["gol"]), "xG cumulato": list(curva["xg"])},
                    tema,
                    altezza=300,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )

    evidenza(numeri)


def main() -> None:
    """Disegna la pagina."""
    guscio.ritira_consegna()
    guscio.barra_laterale("Squadre")

    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    squadra: str | None = st.session_state.get(guscio.CHIAVE_SQUADRA)
    # Le due chiavi sono state di un widget, e Streamlit scarta lo stato dei
    # widget che non vengono piu' disegnati: qui non ce ne sono, quindi vanno
    # riscritte a ogni giro o la pagina si svuota al secondo rerun.
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione
    st.session_state[guscio.CHIAVE_SQUADRA] = squadra

    tema = theme.applica(dati.gruppo_di(competizione, dati.leggi("matches")), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    if squadra is None:
        st.info("Scegli una squadra dalla classifica per vederne la scheda.")
        if st.button("← Torna alle squadre", key="torna_vuoto"):
            st.switch_page("pages/Squadre.py")
        return

    st.markdown(
        f'<div class="testata"><h1 class="titolo">{squadra}</h1>'
        f'<p class="sottotitolo">{dati.nome_di(competizione) if competizione else ""}</p></div>',
        unsafe_allow_html=True,
    )
    if st.button("← Torna alla classifica", key="torna_classifica"):
        st.switch_page("pages/Squadre.py")

    partite = dati.filtra(dati.leggi("matches"), competizione)
    tiri = dati.filtra(dati.leggi("shots"), competizione)
    giocatori = dati.filtra(dati.leggi("player_stats"), competizione)
    passi = dati.filtra(dati.leggi("passes"), competizione)
    if partite.empty:
        st.info("Nessuna partita in questa selezione.")
        return

    suoi_tiri = tiri[tiri["squadra"] == squadra]
    sue_partite = partite[(partite["casa"] == squadra) | (partite["ospite"] == squadra)]
    guscio.indicatori(
        panoramica.kpi(suoi_tiri, sue_partite),
        panoramica.realizzazione(suoi_tiri),
        squadra,
    )

    scheda(
        squadra,
        {
            "tiri": suoi_tiri,
            "giocatori": giocatori[giocatori["squadra"] == squadra],
            "passi": passi[passi["squadra"] == squadra],
            "partite": partite,
            "tabella": classifica.tabella(partite, tiri),
        },
        tema,
        con_punti=classifica.ha_classifica(partite),
    )

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
