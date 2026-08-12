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
**dinamico** fra verde e blu passa invece da qui.

La separazione con :mod:`football_analytics.tema` e' voluta: li' stanno i
colori e la logica di scelta, che sono verificabili senza aprire un browser;
qui sta solo il modo di consegnarli a Streamlit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from football_analytics.tema import Tema, per_gruppo

if TYPE_CHECKING:
    from football_analytics.config import Gruppo

#: Il prefisso delle variabili CSS iniettate, come da backlog.
PREFISSO: str = "--st-"


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
        f"  {PREFISSO}{campo}: {getattr(tema, campo)};"
        for campo in Tema.__slots__
        if campo != "nome"
    )


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

[data-testid="stSidebar"] {{
  background-color: var({PREFISSO}superficie);
  border-right: 1px solid var({PREFISSO}bordo);
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


def applica(gruppo: str | Gruppo | None = None) -> Tema:
    """Inietta il tema nella pagina corrente e lo restituisce.

    Va chiamata **all'inizio di ogni pagina**, perche' Streamlit riesegue lo
    script a ogni interazione e il foglio di stile va riconsegnato ogni volta.

    Args:
        gruppo: Il gruppo della competizione mostrata. Se assente, il tema
            verde.

    Returns:
        Il tema applicato, da passare alle funzioni di disegno: cosi' i grafici
        usano gli stessi colori della pagina senza doverli conoscere.
    """
    tema = per_gruppo(gruppo) if gruppo is not None else per_gruppo("")
    st.markdown(foglio_di_stile(tema), unsafe_allow_html=True)
    return tema
