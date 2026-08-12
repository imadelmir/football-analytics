"""Applica il tema a Streamlit, a ogni rerun (M6-T1).

**Perche' «a ogni rerun».** Streamlit ricostruisce la pagina da zero a ogni
interazione: un filtro cambiato, un pulsante premuto, e tutto lo script viene
rieseguito. Un foglio di stile iniettato una volta sola sparirebbe al primo
click. :func:`applica` va quindi chiamata **all'inizio di ogni pagina**, non
una volta all'avvio.

Il file ``.streamlit/config.toml`` copre solo il tema **statico**: Streamlit lo
legge all'avvio e non lo rilegge mai piu'. Serve perche' i widget nativi —
pulsanti, selettori, barre laterali — siano gia' del colore giusto al primo
disegno, senza il lampo bianco che si vedrebbe aspettando il CSS. Il cambio
**dinamico** — un tema per competizione, piu' la fascia d'identita' in cima
alla pagina — passa invece da qui.

La separazione con :mod:`football_analytics.tema` e' voluta: li' stanno i
colori e la logica di scelta, che sono verificabili senza aprire un browser;
qui sta solo il modo di consegnarli a Streamlit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from football_analytics.tema import Tema, per_competizione, per_gruppo

if TYPE_CHECKING:
    from football_analytics.config import Gruppo

#: Il prefisso delle variabili CSS iniettate, come da backlog.
PREFISSO: str = "--st-"

#: Oltre questo numero di colori la fascia diventa una bandiera a bande nette
#: invece di una sfumatura continua.
BANDIERA: int = 2


def variabili(tema: Tema) -> str:
    """Traduce un tema in dichiarazioni di variabili CSS.

    Ogni campo del tema diventa una variabile ``--st-<campo>``, quindi
    aggiungerne uno a :class:`~football_analytics.tema.Tema` lo rende
    disponibile ai fogli di stile senza toccare questa funzione.

    Args:
        tema: La palette da tradurre.

    Returns:
        Le dichiarazioni, una per riga, da mettere dentro un blocco ``:root``.
    """
    return "\n".join(
        f"  {PREFISSO}{campo}: {valore};"
        for campo in Tema.__slots__
        if campo != "nome" and isinstance(valore := getattr(tema, campo), str)
    )


def fascia(tema: Tema) -> str:
    """Costruisce la sfumatura della fascia d'identita'.

    Tre colori diventano bande nette, perche' un tricolore sfumato non e' piu'
    un tricolore; due diventano una sfumatura continua, perche' un marchio a
    bande sembra un errore di caricamento.

    Args:
        tema: La palette attiva.

    Returns:
        Il valore CSS di ``background``, pronto da assegnare.
    """
    colori = tema.striscia
    if len(colori) > BANDIERA:
        passo = 100 / len(colori)
        tappe = ", ".join(
            f"{colore} {i * passo:.4g}%, {colore} {(i + 1) * passo:.4g}%"
            for i, colore in enumerate(colori)
        )
        return f"linear-gradient(90deg, {tappe})"
    return f"linear-gradient(90deg, {', '.join(colori)})"


def foglio_di_stile(tema: Tema) -> str:
    """Costruisce il foglio di stile completo per un tema.

    Args:
        tema: La palette attiva.

    Returns:
        Il markup ``<style>`` pronto da iniettare.
    """
    return f"""<style>
:root {{
{variabili(tema)}
}}

.stApp {{
  background-color: var({PREFISSO}sfondo);
  color: var({PREFISSO}testo);
}}

/* La fascia d'identita': una riga sottile in cima alla finestra, con i colori
   della competizione scelta. Dice a colpo d'occhio dove ci si trova senza
   occupare spazio ne' costringere a leggere un'etichetta — ed e' l'unico
   punto in cui i tre colori di una bandiera possono stare tutti insieme senza
   litigare con i dati sotto. */
.stApp::before {{
  content: "";
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 4px;
  z-index: 999;
  background: {fascia(tema)};
}}

/* Streamlit riserva in cima una fascia alta un centinaio di pixel: l'intestazione
   con il menu e il pulsante Deploy, piu' il margine del contenitore. In una
   dashboard che deve stare in una schermata sola e' spazio buttato — il titolo
   finisce a meta' pagina e le classifiche scivolano sotto la piega.

   L'intestazione resta nel documento ma diventa alta zero e trasparente: i
   comandi restano raggiungibili passandoci sopra, mentre lo spazio torna al
   contenuto. Nasconderla del tutto toglierebbe anche il menu delle
   impostazioni, che serve. */
header[data-testid="stHeader"] {{
  background: transparent;
  height: 0;
}}

[data-testid="stToolbar"] {{ right: 8px; top: 4px; }}

/* Streamlit centra il contenuto e gli lascia margini generosi ai lati. Su uno
   schermo largo diventa una colonna stretta in mezzo al nulla, con la barra
   laterale lontana dai dati che filtra. */
.block-container {{
  padding-top: .5rem;
  padding-bottom: 1.5rem;
  padding-left: 1.6rem;
  padding-right: 1.6rem;
  max-width: 100%;
}}

/* La barra laterale ha lo stesso problema del contenuto: Streamlit le lascia
   sopra una fascia vuota per il pulsante che la chiude. Il marchio finisce a
   un quinto dell'altezza e il menu comincia a meta'. */
[data-testid="stSidebarUserContent"] {{ padding-top: .4rem; }}
[data-testid="stSidebarHeader"] {{ height: 0; padding: 0; }}
section[data-testid="stSidebar"] {{ width: 228px !important; }}

/* Le colonne stanno piu' vicine: con lo spazio predefinito sei schede KPI
   occupano una riga e mezza invece di una. */
[data-testid="stHorizontalBlock"] {{ gap: .7rem; }}
[data-testid="stVerticalBlock"] {{ gap: .55rem; }}

/* Le cornici dei pannelli. Il bordo e' piu' marcato dello standard di
   Streamlit: con un contorno appena accennato su fondo quasi bianco le schede
   si confondono fra loro, e una dashboard fatta di riquadri ha bisogno che i
   riquadri si vedano. */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background: var({PREFISSO}superficie);
  border: 1px solid var({PREFISSO}bordo);
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, .06);
}}

h1, h2 {{ margin-bottom: .2rem; }}
h5 {{ margin-bottom: .6rem; }}

/* La barra laterale resta scura anche a tema chiaro: separa la navigazione dal
   contenuto senza bisogno di una linea, e rende immediato quale sia lo spazio
   dei comandi e quale quello dei dati. */
[data-testid="stSidebar"] {{
  background-color: var({PREFISSO}barra);
}}

[data-testid="stSidebar"] * {{
  color: var({PREFISSO}barra_testo);
}}

[data-testid="stSidebar"] a:hover,
[data-testid="stSidebar"] [aria-selected="true"] {{
  color: var({PREFISSO}barra_accento);
}}

[data-testid="stMetric"] {{
  background-color: var({PREFISSO}superficie);
  border: 1px solid var({PREFISSO}bordo);
  border-radius: 10px;
  padding: 14px 16px;
}}

[data-testid="stMetricLabel"] {{
  color: var({PREFISSO}testo_tenue);
}}

[data-testid="stMetricValue"] {{
  color: var({PREFISSO}testo);
  font-variant-numeric: tabular-nums;
}}

/* I due filtri ora stanno nel corpo della pagina, non piu' nella barra
   laterale: senza queste regole ereditavano il tema statico di config.toml —
   che e' sempre chiaro — e nelle finali diventavano due riquadri bianchi su
   fondo nero. */
[data-testid="stWidgetLabel"] p {{
  color: var({PREFISSO}testo_tenue);
  font-size: .78rem; text-transform: uppercase; letter-spacing: .06em;
}}
[data-baseweb="select"] > div {{
  background-color: var({PREFISSO}superficie);
  border-color: var({PREFISSO}bordo);
  color: var({PREFISSO}testo);
}}
[data-baseweb="select"] div, [data-baseweb="select"] input, [data-baseweb="select"] span {{
  color: var({PREFISSO}testo);
}}
[data-baseweb="select"] svg {{ fill: var({PREFISSO}testo_tenue); }}
[data-baseweb="popover"] li {{
  background-color: var({PREFISSO}superficie);
  color: var({PREFISSO}testo);
}}
[data-baseweb="popover"] li:hover {{ background-color: var({PREFISSO}primario_tenue); }}

h1, h2, h3 {{ color: var({PREFISSO}testo); }}
a {{ color: var({PREFISSO}primario); }}
hr {{ border-color: var({PREFISSO}bordo); }}

/* Il piede con l'attribuzione a StatsBomb: e' una condizione della licenza,
   quindi deve restare leggibile e non puo' sparire in un colore troppo tenue. */
.attribuzione {{
  color: var({PREFISSO}testo_tenue);
  border-top: 1px solid var({PREFISSO}bordo);
  padding-top: 12px;
  margin-top: 32px;
  font-size: 0.85rem;
}}
</style>"""


def applica(gruppo: str | Gruppo | None = None, competizione: str | None = None) -> Tema:
    """Inietta il tema nella pagina corrente e lo restituisce.

    Va chiamata **all'inizio di ogni pagina**, perche' Streamlit riesegue lo
    script a ogni interazione e il foglio di stile va riconsegnato ogni volta.

    La competizione ha la precedenza sul gruppo, perche' e' l'informazione piu'
    precisa delle due: sapere che si guarda la Premier implica gia' che sia un
    campionato. Il gruppo resta come ripiego per le viste che filtrano su un
    insieme di competizioni invece che su una sola.

    Args:
        gruppo: Il gruppo della competizione mostrata.
        competizione: La chiave della competizione mostrata, per esempio
            ``"serie_a_2015_16"``.

    Returns:
        Il tema applicato, da passare alle funzioni di disegno: cosi' i grafici
        usano gli stessi colori della pagina senza doverli conoscere.
    """
    tema = per_competizione(competizione) if competizione else per_gruppo(gruppo or "")
    st.markdown(foglio_di_stile(tema), unsafe_allow_html=True)
    return tema
