"""La scheda di una singola partita (M6-T7).

**E' l'unico posto della dashboard dove due valori di xG si possono affiancare
senza cautele**: stesso campo, stesso arbitro, stessi novanta minuti. Le
graduatorie dei giocatori devono restare dentro una competizione perche' i
contesti non sono confrontabili; qui il contesto e' identico per definizione.

La corsa dell'xG e' **a gradini**, non a linee: l'xG salta a ogni tiro e resta
fermo in mezzo. Una diagonale fra il minuto 12 e il 34 direbbe che in quei
ventidue minuti e' successo qualcosa.
"""

from __future__ import annotations

import streamlit as st

import dati
import guscio
import theme
from football_analytics import partite, viz
from football_analytics.config import ATTRIBUZIONE
from guscio import SENZA_BARRA, foglio, numero

st.set_page_config(page_title="Football Analytics — Partita", layout="wide")


def tabellone(numeri: partite.Scheda) -> None:
    """Il risultato grande, con l'xG sotto.

    Args:
        numeri: Il risultato di :func:`partite.scheda`.
    """
    st.markdown(
        f'<div class="tabellone">'
        f'<div class="lato"><span class="squadra">{numeri.casa}</span>'
        f'<span class="gol">{numeri.gol_casa}</span>'
        f'<span class="xg">{numero(numeri.xg_casa, 2)} xG</span></div>'
        f'<span class="separatore">–</span>'
        f'<div class="lato"><span class="squadra">{numeri.ospite}</span>'
        f'<span class="gol">{numeri.gol_ospite}</span>'
        f'<span class="xg">{numero(numeri.xg_ospite, 2)} xG</span></div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def giudizio(numeri: partite.Scheda) -> None:
    """Cosa dice l'xG del risultato, in una frase.

    **Nessun testo fisso**: la frase nasce dal confronto, quindi non puo'
    diventare falsa cambiando partita.

    Args:
        numeri: Il risultato di :func:`partite.scheda`.
    """
    favorita = numeri.favorita_xg
    vincitrice = numeri.vincitrice
    if not favorita:
        frase = "Le due squadre hanno creato le stesse occasioni."
    elif not vincitrice:
        frase = f"Ha creato di più il {favorita}, ma è finita in parità."
    elif numeri.ribaltata:
        frase = f"Ha vinto il {vincitrice}, ma le occasioni dicevano {favorita}."
    else:
        frase = f"Ha vinto il {vincitrice}, che aveva anche creato di più."
    st.markdown(f'<div class="evidenza">{frase}</div>', unsafe_allow_html=True)


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Partite")
    competizione: str | None = st.session_state.get(guscio.CHIAVE_COMPETIZIONE)
    guscio.ritira_consegna()
    competizione = st.session_state.get(guscio.CHIAVE_COMPETIZIONE, competizione)
    scelta: int | None = st.session_state.get(guscio.CHIAVE_PARTITA)
    # Le chiavi vanno riscritte a ogni giro: Streamlit scarta lo stato dei
    # widget non ridisegnati, e qui non ce ne sono.
    st.session_state[guscio.CHIAVE_COMPETIZIONE] = competizione
    st.session_state[guscio.CHIAVE_PARTITA] = scelta

    tema = theme.applica(dati.gruppo_di(competizione, dati.leggi("matches")), competizione)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    if scelta is None:
        st.info("Scegli una partita dall'elenco per vederne la scheda.")
        if st.button("← Torna alle partite", key="torna_partite_vuoto"):
            st.switch_page("pages/Partite.py")
        return

    tutte = dati.filtra(dati.leggi("matches"), competizione)
    numeri = partite.scheda(tutte, scelta)
    if numeri is None:
        st.info("Questa partita non compare nella selezione.")
        if st.button("← Torna alle partite", key="torna_partite_assente"):
            st.switch_page("pages/Partite.py")
        return

    st.markdown(
        f'<div class="testata"><h1 class="titolo">{numeri.casa} — {numeri.ospite}</h1>'
        f'<p class="sottotitolo">{dati.nome_di(competizione) if competizione else ""}'
        f'<span class="periodo">giornata {numeri.giornata} · '
        f"{numeri.data:%d/%m/%Y}</span></p></div>",
        unsafe_allow_html=True,
    )
    if st.button("← Torna alle partite", key="torna_partite"):
        st.switch_page("pages/Partite.py")

    tabellone(numeri)

    tiri = dati.filtra(dati.leggi("shots"), competizione)
    suoi = tiri[tiri["match_id"] == scelta]

    sinistra, destra = st.columns(2)
    for colonna, lato in zip((sinistra, destra), ("casa", "ospite"), strict=True):
        squadra = getattr(numeri, lato)
        with colonna, st.container(border=True):
            st.markdown(f"##### Tiri del {squadra}")
            st.plotly_chart(
                viz.shot_map(suoi[suoi["squadra"] == squadra], tema, altezza=460),
                width="stretch",
                config=SENZA_BARRA,
            )

    with st.container(border=True):
        st.markdown("##### La corsa dell'xG")
        corsa = partite.corsa_xg(suoi, scelta, [numeri.casa, numeri.ospite])
        if corsa.empty:
            st.markdown(
                '<p class="vuoto">Nessun tiro registrato in questa partita.</p>',
                unsafe_allow_html=True,
            )
        else:
            st.plotly_chart(
                viz.linee(
                    list(corsa["minuto"]),
                    {
                        numeri.casa: list(corsa[numeri.casa]),
                        numeri.ospite: list(corsa[numeri.ospite]),
                    },
                    tema,
                    altezza=320,
                    a_gradini=True,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )
            st.caption(
                "L'xG accumulato minuto per minuto. Sale a scatti perché cresce solo "
                "quando qualcuno tira: fra un tiro e l'altro resta fermo."
            )

    giudizio(numeri)

    if numeri.autogol_casa or numeri.autogol_ospite:
        st.caption(
            "In questa partita ci sono autogol: contano nel risultato ma non nell'xG, "
            "perché non nascono da un tiro di chi li subisce."
        )

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
