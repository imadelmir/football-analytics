"""Il confronto fra i quattro campionati (M6-T8).

**Questa e' l'unica vista senza scelta della competizione**, ed e' voluto: il
confronto fra campionati e' il contenuto della pagina, non un filtro. Il tema
resta quello neutro, perche' indossare i colori di uno dei quattro mentre li si
mette a paragone sarebbe una presa di posizione grafica su una domanda che la
pagina lascia aperta.

**L'avvertenza del criterio e' scritta al contrario rispetto al backlog**, e la
ragione sta nei dati: il backlog chiedeva di segnalare che «la Serie A usa il
modello base», ma la copertura 360 e' zero in **tutti e quattro** i campionati.
Fra loro il confronto regge; non regge verso i tornei, dove StatsBomb dispone
delle posizioni di difensori e portiere.

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
    """La nota che chiude M6-T8, riscritta su cio' che i dati dicono.

    Il backlog chiedeva di avvertire che «la Serie A usa il modello base». La
    copertura misurata nel magazzino dice altro: e' zero in tutti e quattro i
    campionati, e al 100 % nei tornei recenti. L'avvertenza corretta riguarda
    quindi il confronto **verso i tornei**, non quello fra i campionati.
    """
    st.warning(
        "**Questi quattro numeri sono confrontabili fra loro, non con i tornei.** "
        "Nessuno dei quattro campionati 2015/16 ha i dati 360 di StatsBomb: l'xG di "
        "ogni tiro è stimato senza sapere dove fossero difensori e portiere. Nei "
        "Mondiali 2022 e negli Europei quei dati ci sono su tutte le partite, quindi "
        "l'xG è calcolato con più informazione e i due gruppi non si mettono in fila. "
        "La Ligue 1 ha inoltre 377 partite invece di 380, perché all'Open Data ne "
        "mancano tre: per questo ogni numero qui è per partita o per tiro, mai un totale."
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
