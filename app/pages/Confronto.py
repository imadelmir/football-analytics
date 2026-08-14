"""Il confronto fra i quattro campionati (M6-T8).

**Questa e' l'unica vista senza scelta della competizione**, ed e' voluto: il
confronto fra campionati e' il contenuto della pagina, non un filtro. Il tema
resta quello neutro, perche' indossare i colori di uno dei quattro mentre li si
mette a paragone sarebbe una presa di posizione grafica su una domanda che la
pagina lascia aperta.

**L'avvertenza del criterio e' stata riscritta due volte.** Il backlog chiedeva
di segnalare che «la Serie A usa il modello base»; la copertura misurata dice
che nessuno dei quattro campionati ha i dati 360, quindi la Serie A non e'
l'eccezione. La seconda stesura pero' ne traeva una conseguenza falsa — che
senza i 360 non si sappia dove fossero difensori e portiere — confondendo due
prodotti diversi. Il dettaglio sta in :func:`avvertenza`.

Questa pagina non calcola niente: legge, chiama
:mod:`football_analytics.leghe` e disegna.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import dati
import guscio
import theme
from football_analytics import leghe, panoramica, viz
from football_analytics.config import ATTRIBUZIONE
from football_analytics.tema import per_competizione
from guscio import SENZA_BARRA, foglio, numero

st.set_page_config(page_title="Football Analytics — Confronto leghe", layout="wide")

#: Quanto due campionati devono differire perche' valga la pena dirlo.
#:
#: Un rapporto di 1,05 fra il massimo e il minimo e' il cinque per cento: su
#: trentotto giornate e' dentro il rumore, e chiamarlo «differenza fra
#: campionati» sarebbe leggere una fluttuazione.
SCARTO_NOTEVOLE: float = 1.10


def schede(riassunto: pd.DataFrame) -> None:
    """Una scheda per campionato, con i cinque numeri normalizzati.

    Args:
        riassunto: Il risultato di :func:`leghe.riassunto`.
    """
    for colonna, (_, riga) in zip(st.columns(len(riassunto)), riassunto.iterrows(), strict=True):
        chiave = str(riga["competizione"])
        suo = per_competizione(chiave)
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="targa" style="border-left:4px solid {suo.striscia[0]}">'
                f"{dati.insegna(chiave, guscio.LOGO)}"
                f'<div><span class="nome-competizione" style="color:{suo.striscia[0]}">'
                f"{dati.nome_di(chiave)}</span>"
                f'<span class="stagione">{numero(float(riga["partite"]))} partite</span>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
            voci = "".join(
                f'<div class="voce-scheda"><span>{etichetta}</span>'
                f"<b>{numero(float(riga[campo]), decimali)}</b></div>"
                for etichetta, campo, decimali in leghe.VOCI
            )
            st.markdown(f'<div class="voci">{voci}</div>', unsafe_allow_html=True)


def quanto_si_somigliano(rapporti: dict[str, float]) -> str:
    """La frase che dice se i campionati si distinguono davvero.

    **Nasce dai numeri**, quindi non puo' diventare falsa se il magazzino
    cambia: nomina la metrica su cui la distanza e' maggiore e la misura.

    Args:
        rapporti: Il risultato di :func:`leghe.scarti`.

    Returns:
        La frase.
    """
    if not rapporti:
        return "Non ci sono abbastanza campionati per un confronto."

    etichette = {campo: etichetta for etichetta, campo, _ in leghe.VOCI}
    campo = max(rapporti, key=lambda chiave: rapporti[chiave])
    distanza = rapporti[campo]
    scarto = f"{(distanza - 1) * 100:.0f} %".replace(".", ",")

    if distanza < SCARTO_NOTEVOLE:
        return (
            f"I quattro campionati si somigliano: anche dove differiscono di più — "
            f"{etichette[campo].lower()} — fra il primo e l'ultimo passa il {scarto}."
        )
    return (
        f"La differenza maggiore è su {etichette[campo].lower()}: fra il primo e "
        f"l'ultimo passa il {scarto}."
    )


def avvertenza() -> None:
    """La nota che chiude M6-T8, corretta dopo un errore.

    **La prima stesura diceva una cosa falsa**, e vale la pena lasciarla
    scritta qui invece di far sparire la traccia. Diceva: «nessuno dei quattro
    campionati ha i dati 360, quindi l'xG di ogni tiro e' stimato senza sapere
    dove fossero difensori e portiere». La prima meta' e' vera, la seconda no.

    Sono **due prodotti diversi di StatsBomb**. I *dati 360* sono i fotogrammi
    di ogni evento e nel magazzino sono al 100 % nei tornei recenti e a zero in
    tutti e quattro i campionati — **e a zero anche nelle finali di Champions**,
    che era l'indizio. Il *fotogramma del tiro* e' invece allegato agli eventi
    di tiro ovunque, e copre il 99,3 % dei tiri di Premier, il 99,1 % di Liga e
    Ligue 1, il 98,8 % di Serie A. Le posizioni di difensori e portiere al
    momento del tiro si conoscono, nei campionati come nei tornei.

    Restava allora da capire cosa **davvero** limiti il confronto, e i dati
    dicono che non e' il modello: la dashboard mostra l'xG di StatsBomb, non il
    nostro. Il limite vero e' l'unico misurabile — la Ligue 1 ha 377 partite
    invece di 380 — ed e' la ragione per cui ogni numero qui e' normalizzato.
    Un test verifica entrambe le coperture, cosi' la nota non puo' tornare
    falsa in silenzio.
    """
    st.warning(
        "**I quattro numeri sono confrontabili fra loro, e nessuno è un totale.** "
        "La Ligue 1 ha 377 partite invece di 380, perché all'Open Data ne mancano tre: "
        "un totale grezzo direbbe che in Francia si segna meno, quando semplicemente si "
        "è giocato tre volte in meno. Per questo ogni voce è per partita o per tiro. "
        "L'xG mostrato è quello ufficiale di StatsBomb, lo stesso in tutte le viste."
    )


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Confronto leghe")
    # Nessuna competizione scelta: il tema resta il neutro. Vestire la pagina
    # con i colori di uno dei quattro mentre li si confronta sarebbe una presa
    # di posizione grafica su una domanda che la pagina lascia aperta.
    tema = theme.applica("campionato", None)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    st.markdown(
        '<div class="testata"><h1 class="titolo">Confronto leghe</h1>'
        '<p class="sottotitolo">I quattro campionati 2015/16, '
        "gli unici davvero confrontabili nel magazzino</p></div>",
        unsafe_allow_html=True,
    )

    partite = dati.leggi("matches")
    tiri = panoramica.tiri_di_gioco(dati.leggi("shots"))
    riassunto = leghe.riassunto(partite, tiri)
    if riassunto.empty:
        st.info("Nessun campionato nel magazzino.")
        return

    schede(riassunto)
    st.markdown(
        f'<div class="evidenza">{quanto_si_somigliano(leghe.scarti(riassunto))}</div>',
        unsafe_allow_html=True,
    )

    sinistra, destra = st.columns([1.4, 1])
    with sinistra, st.container(border=True):
        st.markdown("##### Da dove si tira, campionato per campionato")
        colori = {chiave: per_competizione(chiave).striscia[0] for chiave in leghe.campionati()}
        nomi = {chiave: dati.nome_di(chiave) for chiave in leghe.campionati()}
        st.plotly_chart(
            viz.densita(leghe.distribuzione(tiri), colori, tema, etichette=nomi),
            width="stretch",
            config=SENZA_BARRA,
        )
        st.caption(
            "Densità dell'xG del singolo tiro, normalizzata: ogni curva somma a uno, "
            "quindi si confrontano le forme e non quanti tiri si battono. Una curva "
            "spostata a destra vuol dire occasioni mediamente migliori."
        )
    with destra, st.container(border=True):
        st.markdown("##### Gol contro xG")
        st.markdown(
            guscio.barre(
                riassunto.assign(nome=[dati.nome_di(str(k)) for k in riassunto["competizione"]]),
                "gol_per_partita",
                "nome",
                tema,
                decimali=2,
                con_distintivo=False,
            ),
            unsafe_allow_html=True,
        )
        st.caption(
            "Gol per partita. L'xG per partita sta nelle schede sopra: dove i due "
            "numeri divergono, il campionato ha segnato più o meno di quanto creava."
        )

    avvertenza()
    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
