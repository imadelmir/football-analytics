"""La vista Panoramica (M6-T3).

**Questa pagina non calcola niente.** Filtra, chiama le funzioni di
``football_analytics.panoramica``, e disegna. E' la regola del piano di
completamento — logica in ``src/``, interfaccia in ``app/`` — e ha una
conseguenza pratica: ogni numero mostrato qui e' gia' coperto da un test che
gira senza browser, compreso quello che riconcilia i totali con un conteggio a
mano su dieci partite vere.

**Tre cose del disegno non sono state costruite, e la ragione e' la stessa:
non esistono nei dati.**

- «+12,4 % rispetto alla stagione precedente», che nel disegno compare su tutti
  e sei i riquadri: ogni competizione del magazzino ha **una sola stagione**, e
  quel confronto non e' calcolabile. Al suo posto c'e' il valore per partita,
  che e' vero.
- Le voci di menu oltre a Home sono le task M6-T5, T7, T8 e T9: sono
  nella barra ma **disattivate**, perche' un menu che porta a pagine vuote e'
  peggio di un menu che dichiara cosa manca.
- Gli stemmi dei club e le foto dei giocatori: al loro posto la sigla della
  squadra in un cerchio, generata da :mod:`football_analytics.squadre`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import insights, panoramica, viz
from football_analytics.config import ATTRIBUZIONE, SOGLIA_MINUTI
from guscio import CON_ZOOM, QUANTE, SENZA_BARRA, barre, foglio, numero

if TYPE_CHECKING:
    import plotly.graph_objects as go

    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Panoramica", layout="wide")


def etichetta_selezione(competizione: str | None, squadra: str | None) -> str:
    """Come si chiama la selezione corrente, competizione **e** squadra.

    **Nominare solo la competizione era un errore, e si vedeva.** Con il Real
    Madrid scelto dentro la Liga, la frase diceva «La Liga 2015/16 — in 38
    partite si sono visti 144 gol»: quei numeri sono del Real Madrid, ma
    l'etichetta li attribuiva al campionato, che di partite ne ha 380. Un
    lettore non aveva modo di accorgersene.

    Args:
        competizione: La competizione scelta, se ce n'e' una.
        squadra: La squadra scelta, se ce n'e' una.

    Returns:
        L'etichetta, vuota se non c'e' nessun filtro.
    """
    pezzi = [dati.etichetta_di(competizione) if competizione else "", squadra or ""]
    return " · ".join(pezzo for pezzo in pezzi if pezzo)


def conclusioni(
    tiri: pd.DataFrame,
    partite: pd.DataFrame,
    competizione: str | None,
    squadra: str | None = None,
) -> None:
    """Le frasi calcolate sulla selezione corrente (M6-T12).

    **Erano quattro riquadri con dei numeri, e adesso sono frasi.** I numeri
    c'erano gia' nella striscia degli indicatori sopra: ripeterli qui non
    aggiungeva niente, mentre una frase mette in relazione due valori e dice la
    conclusione — che e' cio' che la task chiede.

    Il calcolo sta in :mod:`football_analytics.insights` e non qui: una
    conclusione nasce da un confronto fra numeri, e un confronto e' logica.
    Cosi' si verifica con pytest, ed e' l'unico modo in cui il criterio della
    task — «cambiando competizione la frase cambia da sola con i numeri
    giusti» — si puo' davvero controllare.

    Args:
        tiri: I tiri della selezione.
        partite: Le partite della selezione.
        competizione: La competizione scelta, se ce n'e' una.
        squadra: La squadra scelta, se ce n'e' una. Senza, l'etichetta nomina
            la sola competizione e i numeri sono quelli di tutto il campionato.
    """
    frasi = insights.della_selezione(tiri, partite, etichetta_selezione(competizione, squadra))
    if not frasi:
        st.markdown(
            '<p class="vuoto">La selezione non ha abbastanza partite per una conclusione.</p>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        "".join(f'<div class="conclusione">{frase}</div>' for frase in frasi),
        unsafe_allow_html=True,
    )


def trend(partite: pd.DataFrame, tema: Tema) -> go.Figure:
    """La curva cumulata di xG e gol.

    Args:
        partite: Le partite della selezione.
        tema: La palette attiva.

    Returns:
        La figura.
    """
    curva = panoramica.andamento(partite)
    if curva.empty:
        return viz.linee([], {}, tema, altezza=196)
    return viz.linee(
        list(curva["data"]),
        {"xG": list(curva["xg"].cumsum()), "Gol": list(curva["gol"].cumsum())},
        tema,
        altezza=196,
    )


def main() -> None:
    """Disegna la pagina."""
    partite_tutte = dati.leggi("matches")
    guscio.barra_laterale("Home")
    # Prima dei filtri, o la scrittura sulla chiave di un widget gia' disegnato
    # solleva un'eccezione.
    guscio.ripristina_home()

    # I filtri decidono il tema, ma il titolo sta alla loro sinistra: le
    # colonne nascono prima, si riempie la destra, si applica il tema, e solo
    # allora si scrive il titolo — che ha bisogno dei colori appena scelti.
    intestazione = st.columns([2.6, 1, 1], vertical_alignment="bottom")
    competizione, squadra = guscio.filtri(partite_tutte, intestazione[1:])

    guscio.ricorda_home(competizione, squadra)

    tema = theme.applica(dati.gruppo_di(competizione, partite_tutte), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    partite = dati.filtra(partite_tutte, competizione)
    tiri = dati.filtra(dati.leggi("shots"), competizione)
    giocatori = dati.filtra(dati.leggi("player_stats"), competizione)
    if squadra is not None:
        partite = partite[(partite["casa"] == squadra) | (partite["ospite"] == squadra)]
        tiri = tiri[tiri["squadra"] == squadra]
        giocatori = giocatori[giocatori["squadra"] == squadra]

    # Il titolo dice quale competizione si sta guardando, e lo dice anche col
    # colore: e' la stessa informazione della fascia in cima, ripetuta dove
    # l'occhio va per primo.
    titolo = "Panoramica" if competizione is None else dati.nome_di(competizione)
    if partite.empty:
        with intestazione[0]:
            st.markdown(
                f'<div class="testata"><h1 class="titolo">{titolo}</h1></div>',
                unsafe_allow_html=True,
            )
        st.info("Nessuna partita in questa selezione.")
        return

    date = pd.to_datetime(partite["data"])
    sotto = "" if squadra is None else squadra
    with intestazione[0]:
        st.markdown(
            f'<div class="testata"><h1 class="titolo">{titolo}</h1>'
            f'<p class="sottotitolo">{sotto}'
            f'<span class="periodo{"" if sotto else " sola"}">'
            f"{date.min():%d/%m/%Y} — {date.max():%d/%m/%Y}</span>"
            "</p></div>",
            unsafe_allow_html=True,
        )

    # Con una squadra scelta, la Home mostra i suoi numeri ma non la sua
    # scheda: il pulsante porta di la' con la selezione gia' fatta, invece di
    # costringere a rifare il filtro nell'altra pagina.
    # Il salto sta nel corpo dello script e non in un `on_click`: le callback
    # girano prima che Streamlit prepari il contesto multipagina, e li'
    # `switch_page` non trova le pagine.
    if squadra is not None and st.button(
        f"Apri la scheda di {squadra}", key="vai_a_squadre", width="stretch"
    ):
        guscio.apri_scheda(competizione, squadra)

    numeri = panoramica.kpi(tiri, partite)
    quota = panoramica.realizzazione(tiri)
    giocati = panoramica.tiri_di_gioco(tiri)

    guscio.indicatori(numeri, quota, squadra, filtro=f"{competizione}|{squadra}")
    st.write("")

    grafici(giocati, partite, numeri, quota, tema)
    classifiche(giocatori, tiri, giocati, tema)

    st.write("")
    with st.container(border=True):
        st.markdown("##### Cosa dicono questi numeri")
        conclusioni(tiri, partite, competizione, squadra)
        st.caption(
            "Frasi calcolate sulla selezione a ogni ricalcolo, mai scritte a mano: "
            "cambiando competizione cambiano da sole, numeri compresi."
        )

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


def grafici(
    giocati: pd.DataFrame,
    partite: pd.DataFrame,
    numeri: dict[str, float],
    quota: float,
    tema: Tema,
) -> None:
    """La fascia centrale: mappa, andamento, anello e distribuzione.

    Args:
        giocati: I tiri della selezione, senza i rigori finali.
        partite: Le partite della selezione.
        numeri: Il risultato di :func:`panoramica.kpi`.
        quota: L'xG realizzato.
        tema: La palette attiva.
    """
    mappa, destra = st.columns([3, 2])
    with mappa, st.container(border=True):
        st.markdown("##### Mappa dei tiri")
        # Niente campione: la mappa di calore conta, e contare su un campione
        # da tremila tiri su quarantatremila darebbe una densita' sbagliata di
        # un fattore quattordici. La nuvola di punti aveva bisogno del
        # campione per non impastarsi; un istogramma no.
        st.plotly_chart(
            viz.mappa_di_calore(giocati, tema, altezza=460, meta_campo=False),
            width="stretch",
            config=CON_ZOOM,
        )
        st.caption(
            "Densità dei tiri per zona, celle da 4 iarde. "
            "Il colore cresce con la radice del conteggio: la scala riporta i tiri veri. "
            "Dove il campo resta verde non si è tirato."
        )
    with destra:
        with st.container(border=True):
            st.markdown("##### Andamento di xG e gol")
            st.plotly_chart(trend(partite, tema), width="stretch", config=SENZA_BARRA)
        with st.container(border=True):
            st.markdown("##### xG realizzato")
            st.caption("gol contro occasioni create")
            st.plotly_chart(
                viz.ciambella(
                    quota,
                    f"{quota:.1%}".replace(".", ","),
                    f"{numero(numeri['gol'])} gol / {numero(numeri['xg'])} xG",
                    tema,
                    altezza=165,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )


def classifiche(
    giocatori: pd.DataFrame, tiri: pd.DataFrame, giocati: pd.DataFrame, tema: Tema
) -> None:
    """Le tre schede sotto la mappa: giocatori, distribuzione, squadre.

    L'ordine e' quello del disegno, e non e' indifferente: le due classifiche
    stanno ai lati e l'istogramma in mezzo, cosi' il confronto fra i due elenchi
    resta possibile a colpo d'occhio invece di richiedere di saltare un grafico.

    Args:
        giocatori: La tabella ``player_stats`` filtrata.
        tiri: I tiri della selezione.
        giocati: I tiri senza i rigori finali, per l'istogramma.
        tema: La palette attiva.
    """
    sinistra, destra = st.columns([2, 1.5])
    with sinistra, st.container(border=True):
        st.markdown("##### Top giocatori per xG")
        st.caption(f"minimo {SOGLIA_MINUTI} minuti")
        ammessi = giocatori[giocatori["minuti"] >= SOGLIA_MINUTI].nlargest(QUANTE, "xg")
        nome = "giocatore_breve" if "giocatore_breve" in ammessi.columns else "giocatore"
        st.markdown(barre(ammessi, "xg", nome, tema, decimali=1), unsafe_allow_html=True)
    with destra, st.container(border=True):
        st.markdown("##### Distribuzione dell'xG")
        st.caption("quanti tiri per ogni livello di pericolosita'")
        st.plotly_chart(
            viz.istogramma_xg(giocati, tema, altezza=196), width="stretch", config=SENZA_BARRA
        )

    with st.container(border=True):
        st.markdown("##### Top squadre per xG")
        st.caption("nella selezione corrente")
        migliori = panoramica.per_squadra(tiri, QUANTE)
        st.markdown(barre(migliori, "xg", "squadra", tema, decimali=1), unsafe_allow_html=True)


main()
