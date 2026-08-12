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

from typing import TYPE_CHECKING, Any

import pandas as pd
import streamlit as st

import dati
import theme
from football_analytics import panoramica, squadre, viz
from football_analytics.config import ATTRIBUZIONE, SOGLIA_MINUTI

if TYPE_CHECKING:
    from collections.abc import Sequence

    import plotly.graph_objects as go
    from streamlit.delta_generator import DeltaGenerator

    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Panoramica", layout="wide")

#: Plotly mostra di suo una barra con macchina fotografica, zoom e righello.
#: In un notebook servono; in una dashboard sono arredamento che invita a
#: toccare cose che non cambiano niente.
SENZA_BARRA: dict[str, object] = {"displayModeBar": False, "scrollZoom": False}

#: Quante righe nelle classifiche laterali.
QUANTE = 5

#: Le viste previste dal backlog, con la task che le costruira'.
MENU: tuple[tuple[str, str, bool], ...] = (
    ("Home", "M6-T3", True),
    ("Partite", "M6-T7", False),
    ("Giocatori", "M6-T5", False),
    ("Squadre", "M6-T4", False),
    ("Modello xG", "M6-T9", False),
    ("Confronto leghe", "M6-T8", False),
    ("Finali Champions", "M6-T10", False),
    ("Metodologia", "M6-T11", False),
)


#: Le icone dei sei indicatori, disegnate in linea.
#:
#: SVG scritti a mano e non una libreria di icone: sono sei simboli, pesano
#: nulla, ereditano il colore dal CSS e non aggiungono una dipendenza a un
#: progetto che gira dentro un gigabyte di RAM. ``currentColor`` fa il resto —
#: diventano viola nel tema delle finali senza che qui cambi niente.
ICONE: dict[str, str] = {
    "Partite": (
        '<path d="M3 4h18v16H3z"/><path d="M3 9h18"/><path d="M8 2v4"/><path d="M16 2v4"/>'
    ),
    "Tiri totali": (
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>'
        '<circle cx="12" cy="12" r="1.5" fill="currentColor"/>'
    ),
    "Gol": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 7.5l3.5 2.6-1.3 4.1h-4.4L8.5 10.1z"/>'
        '<path d="M12 3v4.5M4.2 9.4l4.3.7M19.8 9.4l-4.3.7M7.3 19.6l2.5-5.4M16.7 19.6l-2.5-5.4"/>'
    ),
    "xG totale": ('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    "Conversione": ('<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
    "xG per tiro": (
        '<circle cx="12" cy="12" r="8"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>'
        '<circle cx="12" cy="12" r="2.5" fill="currentColor"/>'
    ),
}


def icona(nome: str) -> str:
    """Il markup dell'icona di un indicatore.

    Args:
        nome: L'etichetta dell'indicatore.

    Returns:
        Il tag ``svg``, oppure stringa vuota se non c'e' un'icona.
    """
    tracciato = ICONE.get(nome)
    if tracciato is None:
        return ""
    return (
        '<svg class="icona" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{tracciato}</svg>'
    )


def numero(valore: float, decimali: int = 0) -> str:
    """Formatta un numero all'italiana: punto per le migliaia, virgola decimale.

    Args:
        valore: Il numero.
        decimali: Quante cifre dopo la virgola.

    Returns:
        Il numero formattato.
    """
    return f"{valore:,.{decimali}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def distintivo(nome: str) -> str:
    """Il cerchio con la sigla della squadra.

    Args:
        nome: Il nome della squadra.

    Returns:
        Il frammento HTML.
    """
    return (
        f'<span class="sigla" style="background:{squadre.colore(nome)}">'
        f"{squadre.sigla(nome)}</span>"
    )


def barra_laterale() -> None:
    """Solo marchio e navigazione: i filtri stanno accanto ai dati che filtrano.

    Stavano qui sotto, e la distanza si notava: si sceglieva una squadra in
    basso a sinistra e il numero cambiava in alto a destra, con mezzo schermo
    in mezzo. Ora la barra fa una cosa sola — dire dove si e' — e il menu
    comincia subito sotto il marchio invece che dopo un'intestazione che
    ripeteva quello che le voci gia' dicono.
    """
    with st.sidebar:
        st.markdown(
            '<div class="marchio"><span class="segno">FA</span>'
            "<span>Football<br><b>Analytics</b></span></div>",
            unsafe_allow_html=True,
        )
        for etichetta, task, attiva in MENU:
            classe = "voce attiva" if attiva else "voce spenta"
            nota = "" if attiva else f'<span class="task">{task}</span>'
            st.markdown(f'<div class="{classe}">{etichetta}{nota}</div>', unsafe_allow_html=True)


def filtri(
    partite: pd.DataFrame, colonne: Sequence[DeltaGenerator]
) -> tuple[str | None, str | None]:
    """I due filtri della pagina, da disegnare accanto al titolo.

    **La stagione non c'e' piu'.** Ogni competizione del magazzino ne ha una
    sola, quindi era un menu con una voce: occupava spazio, sembrava utile e
    non poteva cambiare niente.

    **Nessuno dei due parte da una voce «Tutte».** Con ``index=None`` Streamlit
    mostra il testo guida e la lente di ricerca, e con centocinquanta squadre
    scrivere tre lettere e' l'unico modo ragionevole di trovarne una. La
    crocetta riporta alla selezione completa.

    Args:
        partite: La tabella delle partite, da cui nascono le scelte.
        colonne: Le due colonne in cui disegnare, in ordine.

    Returns:
        La competizione e la squadra scelte, oppure ``None`` per tutte.
    """
    dove_competizione, dove_squadra = colonne
    with dove_competizione:
        competizione = st.selectbox(
            "Competizione",
            dati.competizioni(),
            index=None,
            format_func=dati.etichetta_di,
            placeholder="Tutte le competizioni",
        )
    scelta = None if competizione is None else str(competizione)
    with dove_squadra:
        squadra = st.selectbox(
            "Squadra",
            dati.squadre_di(partite, scelta),
            index=None,
            placeholder="Cerca una squadra",
        )
    return scelta, None if squadra is None else str(squadra)


def schede(numeri: dict[str, float], quota: float) -> None:
    """La riga dei sei indicatori principali.

    Args:
        numeri: Il risultato di :func:`panoramica.kpi`.
        quota: L'xG realizzato, da :func:`panoramica.realizzazione`.
    """
    xg_per_tiro = numeri["xg"] / numeri["tiri"] if numeri["tiri"] else 0.0
    voci = (
        ("Partite", numero(numeri["partite"]), "nella selezione"),
        (
            "Tiri totali",
            numero(numeri["tiri"]),
            f"{numero(numeri['tiri_per_partita'], 1)} a partita",
        ),
        ("Gol", numero(numeri["gol"]), f"{numero(numeri['gol_per_partita'], 2)} a partita"),
        ("xG totale", numero(numeri["xg"]), f"{numero(numeri['xg_per_partita'], 2)} a partita"),
        (
            "Conversione",
            f"{numeri['conversione']:.1%}".replace(".", ","),
            "dei tiri finisce in gol",
        ),
        ("xG per tiro", numero(xg_per_tiro, 3), f"realizzato al {quota:.0%}".replace(".", ",")),
    )
    for colonna, (etichetta, valore, nota) in zip(st.columns(6), voci, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="scheda"><div class="cima">'
                f'<span class="etichetta">{etichetta}</span>{icona(etichetta)}</div>'
                f'<span class="numero">{valore}</span>'
                f'<span class="nota">{nota}</span></div>',
                unsafe_allow_html=True,
            )


def classifica(righe: pd.DataFrame, chiave: str, nome: str, tema: Tema, *, decimali: int) -> str:
    """Compone una classifica con distintivo e barra proporzionale.

    Args:
        righe: Le righe gia' ordinate e tagliate.
        chiave: La colonna del valore da mostrare.
        nome: La colonna del nome da mostrare.
        tema: La palette attiva.
        decimali: Quante cifre decimali nel valore.

    Returns:
        Il markup della classifica.
    """
    if righe.empty:
        return '<p class="vuoto">Nessun dato nella selezione.</p>'

    massimo = float(righe[chiave].max())
    pezzi = []
    for posizione, riga in enumerate(righe.to_dict("records"), start=1):
        larghezza = float(riga[chiave]) / massimo if massimo else 0.0
        scarto = float(riga.get("gol_meno_xg", 0.0))
        segno = "positivo" if scarto >= 0 else "negativo"
        pezzi.append(
            f'<div class="riga"><span class="posto">{posizione}</span>'
            f"{distintivo(str(riga['squadra']))}"
            f'<span class="nome">{riga[nome]}</span>'
            f'<div class="traccia"><div class="riempimento" '
            f'style="width:{larghezza:.1%};background:{tema.primario}"></div></div>'
            f'<span class="valore">{numero(float(riga[chiave]), decimali)}</span>'
            f'<span class="scarto {segno}">{"+" if scarto >= 0 else "−"}'
            f"{numero(abs(scarto), 1)}</span></div>"
        )
    return f'<div class="classifica">{"".join(pezzi)}</div>'


def riga_massima(tabella: pd.DataFrame, colonna: str) -> dict[str, Any] | None:
    """La riga con il valore piu' alto in una colonna, come dizionario.

    Restituisce un dizionario e non una ``Series`` perche' con pandas-stubs il
    tipo di ``.loc[etichetta]`` e' un'unione che comprende date e stringhe: ogni
    lettura andrebbe silenziata con un ``type: ignore``, e un silenziatore non
    e' mai una correzione.

    Args:
        tabella: La tabella da esaminare.
        colonna: La colonna su cui cercare il massimo.

    Returns:
        La riga, oppure ``None`` se la tabella e' vuota.
    """
    if tabella.empty:
        return None
    posizione = int(tabella[colonna].to_numpy().argmax())
    return {nome: tabella[nome].to_numpy()[posizione] for nome in tabella.columns}


def insight(
    numeri: dict[str, float], zone: pd.DataFrame, quarti: pd.DataFrame, quota: float
) -> None:
    """La striscia di conclusioni, tutte **calcolate**.

    Il piano di completamento lo chiede esplicitamente: nessun testo statico
    che possa diventare falso cambiando filtro.

    Args:
        numeri: Il risultato di :func:`panoramica.kpi`.
        zone: Il risultato di :func:`panoramica.per_zona`.
        quarti: Il risultato di :func:`panoramica.per_quarto_dora`.
        quota: L'xG realizzato.
    """
    # L'estrazione passa per numpy: `.loc[etichetta]` per pandas-stubs ha un
    # tipo unione che comprende date e stringhe, e ogni conversione a float
    # andrebbe silenziata con un `type: ignore`.
    migliore_zona = riga_massima(zone, "xg_medio")
    migliore_quarto = riga_massima(quarti, "xg")
    scarto = numeri["gol_meno_xg"]

    voci = [
        ("xG realizzato", f"{quota:.1%}".replace(".", ","), "gol contro occasioni"),
        (
            "Differenza gol − xG",
            f"{'+' if scarto >= 0 else '−'}{numero(abs(scarto), 1)}",
            "sopra le attese" if scarto >= 0 else "sotto le attese",
        ),
    ]
    if migliore_zona is not None:
        voci.append(
            (
                "Zona più redditizia",
                str(migliore_zona["zona"]),
                f"{numero(migliore_zona['xg_medio'], 3)} xG medio",
            )
        )
    if migliore_quarto is not None:
        voci.append(
            (
                "Quarto d'ora migliore",
                str(migliore_quarto["blocco"]),
                f"{numero(migliore_quarto['xg'], 0)} xG accumulati",
            )
        )

    for colonna, (titolo, grande, sotto) in zip(st.columns(len(voci)), voci, strict=True):
        with colonna:
            st.markdown(
                f'<div class="insight"><span class="etichetta">{titolo}</span>'
                f'<span class="grande">{grande}</span>'
                f'<span class="nota">{sotto}</span></div>',
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
    barra_laterale()

    # I filtri decidono il tema, ma il titolo sta alla loro sinistra: le
    # colonne nascono prima, si riempie la destra, si applica il tema, e solo
    # allora si scrive il titolo — che ha bisogno dei colori appena scelti.
    intestazione = st.columns([2.6, 1, 1], vertical_alignment="bottom")
    competizione, squadra = filtri(partite_tutte, intestazione[1:])

    tema = theme.applica(dati.gruppo_di(competizione, partite_tutte), competizione)
    st.markdown(FOGLIO.format(tema=tema), unsafe_allow_html=True)

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
    sotto = "Overview completa delle performance" if squadra is None else squadra
    with intestazione[0]:
        st.markdown(
            f'<div class="testata"><h1 class="titolo">{titolo}</h1>'
            f'<p class="sottotitolo">{sotto}'
            f'<span class="periodo">{date.min():%d/%m/%Y} — {date.max():%d/%m/%Y}</span>'
            "</p></div>",
            unsafe_allow_html=True,
        )

    numeri = panoramica.kpi(tiri, partite)
    quota = panoramica.realizzazione(tiri)
    giocati = panoramica.tiri_di_gioco(tiri)

    schede(numeri, quota)
    st.write("")

    grafici(giocati, partite, numeri, quota, tema)
    classifiche(giocatori, tiri, giocati, tema)

    st.write("")
    with st.container(border=True):
        st.markdown("##### Insight chiave")
        st.caption("Calcolati dai dati filtrati a ogni ricalcolo, mai scritti a mano.")
        insight(numeri, panoramica.per_zona(tiri), panoramica.per_quarto_dora(tiri), quota)

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
            config=SENZA_BARRA,
        )
        st.caption(
            "Densità dei tiri per zona, celle da 4 iarde. "
            "Il colore cresce con la radice del conteggio: la scala riporta i tiri veri."
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
        st.markdown(classifica(ammessi, "xg", nome, tema, decimali=1), unsafe_allow_html=True)
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
        st.markdown(classifica(migliori, "xg", "squadra", tema, decimali=1), unsafe_allow_html=True)


#: Lo stile della pagina. Usa solo i campi del tema, mai colori scritti a mano.
FOGLIO: str = """<style>
.testata {{ margin: 0 0 .2rem 0; }}
.titolo {{
  font-size: 2.6rem; font-weight: 800; margin: 0; letter-spacing: -.03em;
  color: {tema.primario}; line-height: 1.05;
}}
.sottotitolo {{ color: {tema.testo_tenue}; margin: 0; font-size: .95rem; }}
.periodo {{
  margin-left: 12px; padding-left: 12px; border-left: 1px solid {tema.bordo};
  color: {tema.testo_tenue}; font-variant-numeric: tabular-nums;
}}

.marchio {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
.marchio .segno {{
  width: 40px; height: 40px; border-radius: 11px; background: {tema.primario};
  color: #fff; font-weight: 700; display: inline-flex;
  align-items: center; justify-content: center;
}}
/* Le voci del menu usano il colore pieno del testo della barra, non quello
   tenue. Il tenue serve a mettere in secondo piano un'informazione accessoria;
   qui l'informazione e' la navigazione, e una voce che non si legge non e' in
   secondo piano, e' rotta. La differenza fra voce attiva e voce da costruire
   la fanno lo sfondo e la sigla della task, non lo sbiadimento. */
.voce {{
  padding: 9px 12px; border-radius: 9px; font-size: .93rem; margin-bottom: 2px;
  color: {tema.barra_testo};
}}
.voce.attiva {{ background: {tema.primario}; color: #fff; font-weight: 600; }}
.voce.spenta {{ display: flex; justify-content: space-between; align-items: center; }}
.voce .task {{ font-size: .7rem; opacity: .55; }}

.scheda {{ display: flex; flex-direction: column; gap: 2px; }}
.scheda .cima {{ display: flex; align-items: center; justify-content: space-between; }}
.scheda .icona {{ width: 22px; height: 22px; color: {tema.primario}; opacity: .85; }}
.scheda .etichetta {{
  color: {tema.primario}; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .09em; font-weight: 700;
}}
.scheda .numero {{
  font-size: 2.15rem; font-weight: 800; line-height: 1.12;
  font-variant-numeric: tabular-nums; color: {tema.testo};
  letter-spacing: -.02em;
}}
.scheda .nota {{ color: {tema.testo_tenue}; font-size: .8rem; }}

.classifica {{ display: flex; flex-direction: column; gap: 13px; }}
.classifica .riga {{ display: flex; align-items: center; gap: 9px; }}
.classifica .posto {{ width: 14px; color: {tema.testo_tenue}; font-size: .82rem; }}
.classifica .sigla {{
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 700;
}}
.classifica .nome {{ min-width: 170px; font-size: 1rem; font-weight: 500; }}
.classifica .traccia {{ flex: 1; height: 9px; border-radius: 5px; background: {tema.sfondo}; }}
.classifica .riempimento {{ height: 100%; border-radius: 4px; }}
.classifica .valore {{
  min-width: 58px; text-align: right; font-weight: 700; font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
}}
.classifica .scarto {{ min-width: 46px; text-align: right; font-size: .82rem; }}
.classifica .scarto.positivo {{ color: {tema.primario}; }}
.classifica .scarto.negativo {{ color: {tema.pericolo}; }}
.vuoto {{ color: {tema.testo_tenue}; }}

/* Il riempimento interno delle schede: lo stile del bordo sta in theme.py,
   qui solo l'aria attorno al contenuto. */
[data-testid="stVerticalBlockBorderWrapper"] {{ padding: .35rem .6rem; }}
h5 {{ font-size: .95rem !important; font-weight: 700; margin-bottom: .1rem; }}
[data-testid="stCaptionContainer"] {{ margin-top: -.35rem; }}

.insight {{ display: flex; flex-direction: column; gap: 1px; }}
.insight .etichetta {{ color: {tema.testo_tenue}; font-size: .78rem; }}
.insight .grande {{ font-size: 1.3rem; font-weight: 700; color: {tema.primario}; }}
.insight .nota {{ color: {tema.testo_tenue}; font-size: .76rem; }}
</style>"""


main()
