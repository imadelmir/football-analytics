"""Da dove vengono i numeri e cosa non dicono (M6-T11).

**Il criterio della task e' che questa pagina esista prima del deploy, non
dopo.** Scritta dopo sarebbe un riassunto di cio' che si e' fatto; scritta
prima e' un impegno da mantenere. Le due cose si leggono uguali e valgono
diverso — e questa e' stata scritta con M7 ancora da fare.

**Nessun numero e' scritto a mano.** Le righe e i megabyte delle tabelle
arrivano dai metadati dei Parquet, i conteggi di verifiche e limiti dalla
lunghezza degli elenchi in :mod:`football_analytics.metodo`. Una pagina sulla
metodologia che contenesse un numero copiato sarebbe la smentita di se stessa.

**Le verifiche citano il test che le tiene oneste.** Un elenco senza prove e'
una dichiarazione di buone intenzioni: chiunque puo' scrivere «validato». I
riferimenti sono in forma ``file::funzione``, si copiano dietro a ``pytest``, e
un test della suite controlla che esistano tutti — cosi' una prova cancellata
non puo' restare pubblicizzata qui.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import guscio
import theme
from football_analytics import metodo
from football_analytics.config import ATTRIBUZIONE, SOGLIA_MINUTI
from guscio import foglio, numero

st.set_page_config(page_title="Football Analytics — Metodologia", layout="wide")

#: Il limite per file che il progetto si e' dato, in megabyte.
#:
#: Non e' un vincolo di Streamlit Cloud ma una regola del piano: sopra questa
#: soglia un Parquet diventa scomodo in git, che dei binari non sa fare diff e
#: ne conserva ogni versione per intero.
TETTO_MB: float = 50.0

#: Dove sta il codice, per chi vuole controllare invece di fidarsi.
REPOSITORY: str = "https://github.com/imadelmir/football-analytics"


def catena() -> None:
    """Il diagramma dei cinque stadi, dai JSON di StatsBomb alla dashboard."""
    st.markdown("#### La catena del dato")
    st.markdown(
        '<p class="vuoto">Quattro strati e nessuna scorciatoia: <b>la dashboard non '
        "legge mai i dati grezzi</b>, e i moduli di <code>src/</code> non sanno che "
        "Streamlit esista. È la ragione per cui la stessa logica si verifica con pytest "
        "senza aprire un browser, e per cui una vista rotta non può corrompere il "
        "magazzino.</p>",
        unsafe_allow_html=True,
    )
    pezzi = []
    for indice, anello in enumerate(metodo.ANELLI):
        if indice:
            pezzi.append('<span class="freccia">→</span>')
        pezzi.append(
            f'<div class="anello"><span class="nome">{anello.nome}</span>'
            f'<span class="dove">{anello.dove}</span>'
            f'<span class="cosa">{anello.cosa}</span></div>'
        )
    st.markdown(f'<div class="catena">{"".join(pezzi)}</div>', unsafe_allow_html=True)


def magazzino(tabelle: pd.DataFrame) -> None:
    """Le sei tabelle Parquet, con righe e peso letti dai metadati.

    Args:
        tabelle: Il risultato di :func:`metodo.magazzino`.
    """
    st.markdown("#### Il magazzino")
    if tabelle.empty:
        st.info("Il magazzino non è stato costruito in questa copia del progetto.")
        return

    peso = float(tabelle["megabyte"].sum())
    piu_grande = float(tabelle["megabyte"].max())
    sinistra, destra = st.columns([1.3, 1])
    with sinistra, st.container(border=True):
        st.dataframe(
            tabelle,
            width="stretch",
            hide_index=True,
            column_config={
                "tabella": st.column_config.TextColumn("Tabella"),
                "righe": st.column_config.NumberColumn("Righe", format="%d"),
                "colonne": st.column_config.NumberColumn("Colonne", format="%d"),
                "megabyte": st.column_config.NumberColumn("MB", format="%.2f"),
            },
        )
    with destra, st.container(border=True):
        st.markdown(
            f'<div class="voci">'
            f'<div class="voce-scheda"><span>Peso totale</span>'
            f"<b>{numero(peso, 2)} MB</b></div>"
            f'<div class="voce-scheda"><span>File più grande</span>'
            f"<b>{numero(piu_grande, 2)} MB</b></div>"
            f'<div class="voce-scheda"><span>Tetto che ci siamo dati</span>'
            f"<b>{numero(TETTO_MB)} MB</b></div>"
            f'<div class="voce-scheda"><span>Righe in tutto</span>'
            f"<b>{numero(float(tabelle['righe'].sum()))}</b></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Il magazzino sta in git perché è quello che Streamlit Cloud trova quando "
            "clona il repository. Ci sta perché contiene **solo le colonne che le viste "
            "usano**: salvare tutti gli eventi avrebbe voluto dire gigabyte, e una "
            "cronologia git che nessuno può più ripulire."
        )


def verifiche() -> None:
    """Cosa e' stato controllato, contro cosa, e con quale test."""
    st.markdown(f"#### Cosa è stato verificato — {numero(float(len(metodo.VERIFICHE)))} controlli")
    st.markdown(
        '<p class="vuoto"><b>Contro la realtà dove possibile, non contro un\'altra '
        "funzione del progetto.</b> Un test che confronta due funzioni scritte dalla "
        "stessa persona nello stesso pomeriggio verifica la coerenza, non la "
        "correttezza: possono sbagliare entrambe allo stesso modo. I controlli più utili "
        "qui sotto sono quelli che guardano fuori — classifiche e capocannonieri veri "
        "del 2015/16, esiti reali delle finali.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            "".join(
                f'<div class="prova"><span class="cosa">{prova.cosa}</span>'
                f'<span class="esito">{prova.esito}</span>'
                f'<span class="test">{prova.test}</span></div>'
                for prova in metodo.VERIFICHE
            ),
            unsafe_allow_html=True,
        )
    st.caption(
        "I riferimenti si copiano dietro a `pytest` e si controllano in dieci secondi. "
        "Un test della suite verifica che esistano tutti: se una di queste prove venisse "
        "cancellata, la pagina non potrebbe continuare a citarla."
    )


def limiti() -> None:
    """Cosa i numeri non dicono, con la conseguenza pratica."""
    st.markdown(f"#### Cosa i numeri non dicono — {numero(float(len(metodo.LIMITI)))} limiti")
    st.markdown(
        '<p class="vuoto">Tutti, non i più comodi. Una pagina che si chiama Metodologia '
        "e ne nasconde metà è peggio di nessuna pagina: chi se ne accorge smette di "
        "credere anche al resto.</p>",
        unsafe_allow_html=True,
    )
    sinistra, destra = st.columns(2)
    meta = (len(metodo.LIMITI) + 1) // 2
    for colonna, fetta in ((sinistra, metodo.LIMITI[:meta]), (destra, metodo.LIMITI[meta:])):
        with colonna:
            st.markdown(
                "".join(
                    f'<div class="limite"><span class="titolo-limite">{limite.titolo}</span>'
                    f'<span class="conseguenza">{limite.conseguenza}</span></div>'
                    for limite in fetta
                ),
                unsafe_allow_html=True,
            )


def scelte() -> None:
    """Le tre decisioni di metodo che reggono tutti i numeri della dashboard."""
    st.markdown("#### Tre scelte che reggono tutto il resto")
    voci = (
        (
            "Divisione per partita, non per tiro",
            "Due tiri della stessa partita condividono avversario, campo e arbitro. "
            "Dividerli fra addestramento e verifica farebbe filtrare informazione da "
            "una parte all'altra, e ogni punteggio del modello sarebbe gonfiato.",
        ),
        (
            "Mai l'accuratezza come metrica",
            "Con un gol ogni dieci tiri, un modello che risponde sempre «no» è accurato "
            "al 90 % e inutile. Si misurano Brier, log loss, AUC e la calibrazione, che "
            "guardano la probabilità e non la risposta secca.",
        ),
        (
            f"La soglia dei {numero(SOGLIA_MINUTI)} minuti",
            "Chi sta sotto resta nelle tabelle e nei totali ma fuori dalle graduatorie "
            "per novanta minuti: tre gol in duecento minuti darebbero un primato che non "
            "descrive niente.",
        ),
    )
    for colonna, (titolo, corpo) in zip(st.columns(len(voci)), voci, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="scheda"><div class="cima">'
                f'<span class="etichetta">{titolo}</span></div>'
                f'<span class="nota">{corpo}</span></div>',
                unsafe_allow_html=True,
            )


def fonte() -> None:
    """L'attribuzione a StatsBomb e il rimando al codice.

    **L'attribuzione e' una condizione della licenza**, non una cortesia: sta
    in fondo a ogni vista e qui per esteso, con il collegamento al repository
    per chi preferisce controllare invece di fidarsi.
    """
    st.markdown("#### Fonte e codice")
    sinistra, destra = st.columns(2)
    with sinistra, st.container(border=True):
        st.markdown("##### I dati")
        st.markdown(
            '<p class="vuoto">Tutti i dati di questo progetto vengono dallo '
            "<b>StatsBomb Open Data</b>, pubblicato gratuitamente da StatsBomb per "
            "ricerca e formazione. Nessun dato è stato acquistato, inventato o "
            "integrato da altre fonti: quello che non c'è nell'Open Data non c'è "
            "nemmeno qui, ed è dichiarato sopra.</p>",
            unsafe_allow_html=True,
        )
        st.caption(ATTRIBUZIONE)
    with destra, st.container(border=True):
        st.markdown("##### Il codice")
        st.markdown(
            f'<p class="vuoto">Tutto il progetto è pubblico: ingestione, '
            f"trasformazione, modelli, dashboard e la suite di test che tiene onesta "
            f"questa pagina. Ogni numero mostrato si può rigenerare da zero con i "
            f"comandi descritti nel README.</p>"
            f'<p class="vuoto"><a href="{REPOSITORY}" target="_blank">{REPOSITORY}</a></p>',
            unsafe_allow_html=True,
        )


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Metodologia")
    # Nessuna competizione: la metodologia non appartiene a un campionato.
    tema = theme.applica("campionato", None)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    st.markdown(
        '<div class="testata"><h1 class="titolo">Metodologia</h1>'
        '<p class="sottotitolo">Da dove vengono i numeri, cosa è stato verificato '
        "e cosa i numeri non dicono</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="evidenza">Questa pagina è stata scritta <b>prima</b> del deploy, '
        "non dopo: è un impegno, non un riassunto.</div>",
        unsafe_allow_html=True,
    )

    catena()
    st.divider()
    magazzino(metodo.magazzino())
    st.divider()
    scelte()
    st.divider()
    verifiche()
    st.divider()
    limiti()
    st.divider()
    fonte()

    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
