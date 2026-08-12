"""Il campo da gioco in Plotly, disegnato una volta sola (M6-T2).

**Una funzione sola per tutte le viste.** Shot map, rete dei passaggi e heatmap
usano :func:`campo`, e non e' una comodita': se ognuna disegnasse il proprio
campo, prima o poi due viste avrebbero proporzioni diverse, e un tiro alla
stessa coordinata apparirebbe in due punti diversi dell'app. Sarebbe un difetto
invisibile a chi scrive e ovvio a chi guarda.

**Le misure vengono da un posto solo.** Le coordinate condivise con il modello
— porta, pali, area di rigore — sono importate da
:mod:`football_analytics.features`, non ricopiate. Se un giorno StatsBomb
cambiasse sistema di riferimento, il modello e i grafici cambierebbero insieme.
Un test verifica che le due copie non esistano.

**Nessun colore in questo file.** Ogni funzione riceve un
:class:`~football_analytics.tema.Tema` e usa i suoi campi, cosi' il campo
diventa blu nelle finali di Champions senza che qui cambi una riga.

Sistema di riferimento di StatsBomb: campo 120 x 80, origine in alto a
sinistra, **y che cresce verso il basso**. L'asse verticale va quindi
invertito, o le azioni risultano ribaltate — ed e' l'errore piu' comune con
questi dati, perche' produce grafici plausibili e sbagliati.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import plotly.graph_objects as go

from football_analytics.features import (
    AREA_X,
    AREA_Y_MAX,
    AREA_Y_MIN,
    PALO_DESTRO_Y,
    PALO_SINISTRO_Y,
    PORTA_X,
    PORTA_Y,
)
from football_analytics.tema import TRASPARENTE

if TYPE_CHECKING:
    from football_analytics.tema import Tema

#: Le dimensioni del campo nel sistema di StatsBomb.
LUNGHEZZA: Final[float] = 120.0
LARGHEZZA: Final[float] = 80.0

#: Area piccola: sei iarde di profondita', venti di larghezza.
AREA_PICCOLA_X: Final[float] = 114.0
AREA_PICCOLA_Y_MIN: Final[float] = 30.0
AREA_PICCOLA_Y_MAX: Final[float] = 50.0

#: Dischetto del rigore: dodici iarde dalla linea di porta.
DISCHETTO_X: Final[float] = 108.0

#: Raggio del cerchio di centrocampo e dell'arco dell'area, dieci iarde.
RAGGIO: Final[float] = 10.0

#: Quante strisce d'erba disegnare per meta' campo.
STRISCE: Final[int] = 6

#: Spessore delle linee del campo, in pixel.
SPESSORE: Final[float] = 1.6


def _rettangolo(x0: float, y0: float, x1: float, y1: float, colore: str) -> dict[str, Any]:
    """Costruisce una forma rettangolare piena, senza bordo.

    Args:
        x0: Ascissa iniziale.
        y0: Ordinata iniziale.
        x1: Ascissa finale.
        y1: Ordinata finale.
        colore: Il riempimento.

    Returns:
        La forma nel formato che Plotly si aspetta.
    """
    return {
        "type": "rect",
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "fillcolor": colore,
        "line": {"width": 0},
        "layer": "below",
    }


def _linea(x0: float, y0: float, x1: float, y1: float, colore: str) -> dict[str, Any]:
    """Costruisce un segmento delle linee del campo.

    Args:
        x0: Ascissa iniziale.
        y0: Ordinata iniziale.
        x1: Ascissa finale.
        y1: Ordinata finale.
        colore: Il colore della linea.

    Returns:
        La forma nel formato che Plotly si aspetta.
    """
    return {
        "type": "line",
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "line": {"color": colore, "width": SPESSORE},
        "layer": "below",
    }


def _riquadro(x0: float, y0: float, x1: float, y1: float, colore: str) -> dict[str, Any]:
    """Costruisce un rettangolo vuoto, cioe' quattro linee.

    Args:
        x0: Ascissa iniziale.
        y0: Ordinata iniziale.
        x1: Ascissa finale.
        y1: Ordinata finale.
        colore: Il colore del contorno.

    Returns:
        La forma nel formato che Plotly si aspetta.
    """
    return {
        "type": "rect",
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "line": {"color": colore, "width": SPESSORE},
        "fillcolor": TRASPARENTE,
        "layer": "below",
    }


def _cerchio(cx: float, cy: float, raggio: float, colore: str) -> dict[str, Any]:
    """Costruisce una circonferenza vuota.

    Args:
        cx: Ascissa del centro.
        cy: Ordinata del centro.
        raggio: Il raggio.
        colore: Il colore del contorno.

    Returns:
        La forma nel formato che Plotly si aspetta.
    """
    return {
        "type": "circle",
        "x0": cx - raggio,
        "y0": cy - raggio,
        "x1": cx + raggio,
        "y1": cy + raggio,
        "line": {"color": colore, "width": SPESSORE},
        "fillcolor": TRASPARENTE,
        "layer": "below",
    }


def erba(tema: Tema) -> list[dict[str, Any]]:
    """Disegna le strisce del prato.

    Args:
        tema: La palette attiva.

    Returns:
        Le forme delle strisce, dalla sinistra alla destra del campo.
    """
    larghezza = LUNGHEZZA / (STRISCE * 2)
    return [
        _rettangolo(
            i * larghezza,
            0.0,
            (i + 1) * larghezza,
            LARGHEZZA,
            tema.erba_chiara if i % 2 == 0 else tema.erba_scura,
        )
        for i in range(STRISCE * 2)
    ]


def segnature(tema: Tema) -> list[dict[str, Any]]:
    """Disegna le linee regolamentari del campo.

    Solo la meta' offensiva ha le aree: le viste di questo progetto guardano i
    tiri, e un campo intero con due aree sprecherebbe meta' dello spazio su
    una zona dove non succede quasi niente di ciò che interessa.

    Args:
        tema: La palette attiva.

    Returns:
        Le forme delle linee.
    """
    colore = tema.linee
    return [
        _riquadro(0.0, 0.0, LUNGHEZZA, LARGHEZZA, colore),
        _linea(LUNGHEZZA / 2, 0.0, LUNGHEZZA / 2, LARGHEZZA, colore),
        _cerchio(LUNGHEZZA / 2, PORTA_Y, RAGGIO, colore),
        _riquadro(AREA_X, AREA_Y_MIN, PORTA_X, AREA_Y_MAX, colore),
        _riquadro(AREA_PICCOLA_X, AREA_PICCOLA_Y_MIN, PORTA_X, AREA_PICCOLA_Y_MAX, colore),
        _cerchio(DISCHETTO_X, PORTA_Y, 0.4, colore),
        _cerchio(LUNGHEZZA / 2, PORTA_Y, 0.4, colore),
        # La porta, disegnata piu' spessa: e' il riferimento visivo di ogni
        # vista sui tiri, e a questa scala una linea sottile sparisce.
        {
            "type": "line",
            "x0": PORTA_X,
            "y0": PALO_SINISTRO_Y,
            "x1": PORTA_X,
            "y1": PALO_DESTRO_Y,
            "line": {"color": colore, "width": SPESSORE * 3},
            "layer": "below",
        },
    ]


def campo(tema: Tema, *, meta_campo: bool = True, altezza: int = 520) -> go.Figure:
    """Costruisce la figura del campo, pronta per ricevere i dati.

    E' la base di **tutte** le viste spaziali. Chi la usa aggiunge le proprie
    tracce alla figura restituita e non tocca assi, proporzioni ne' colori.

    **L'asse verticale e' invertito** perche' in StatsBomb la y cresce verso il
    basso. Dimenticarlo produce grafici plausibili con le azioni ribaltate, ed
    e' l'errore piu' comune con questi dati proprio perche' non si vede.

    **Le proporzioni sono bloccate** con ``scaleanchor``: un campo 120x80
    disegnato in un riquadro quadrato mostrerebbe distanze sbagliate, e un
    modello che parla di metri finirebbe illustrato da un grafico che mente
    sulle distanze.

    Args:
        tema: La palette attiva, da :func:`football_analytics.tema.per_gruppo`.
        meta_campo: Se vero mostra solo la meta' offensiva, dove avvengono
            praticamente tutti i tiri.
        altezza: Altezza della figura in pixel.

    Returns:
        La figura, con erba, linee, assi configurati e nessun dato.
    """
    figura = go.Figure()
    figura.update_layout(
        shapes=erba(tema) + segnature(tema),
        paper_bgcolor=tema.superficie,
        plot_bgcolor=tema.erba_scura,
        font={"color": tema.testo},
        height=altezza,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        showlegend=False,
        hoverlabel={"bgcolor": tema.superficie, "font": {"color": tema.testo}},
    )
    figura.update_xaxes(
        range=[LUNGHEZZA / 2, LUNGHEZZA] if meta_campo else [0.0, LUNGHEZZA],
        visible=False,
        constrain="domain",
    )
    figura.update_yaxes(
        range=[LARGHEZZA, 0.0],
        visible=False,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    return figura
