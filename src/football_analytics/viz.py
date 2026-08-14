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

import math
from typing import TYPE_CHECKING, Any, Final

import numpy as np
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
from football_analytics.tema import TRASPARENTE, scala_calore, scala_di

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import numpy.typing as npt
    import pandas as pd

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


def _linea(
    x0: float, y0: float, x1: float, y1: float, colore: str, *, livello: str = "below"
) -> dict[str, Any]:
    """Costruisce un segmento delle linee del campo.

    Args:
        x0: Ascissa iniziale.
        y0: Ordinata iniziale.
        x1: Ascissa finale.
        y1: Ordinata finale.
        colore: Il colore della linea.
        livello: ``"below"`` o ``"above"``, rispetto alle tracce.

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
        "layer": livello,
    }


def _riquadro(
    x0: float, y0: float, x1: float, y1: float, colore: str, *, livello: str = "below"
) -> dict[str, Any]:
    """Costruisce un rettangolo vuoto, cioe' quattro linee.

    Args:
        x0: Ascissa iniziale.
        y0: Ordinata iniziale.
        x1: Ascissa finale.
        y1: Ordinata finale.
        colore: Il colore del contorno.
        livello: ``"below"`` o ``"above"``, rispetto alle tracce.

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
        "layer": livello,
    }


def _cerchio(
    cx: float, cy: float, raggio: float, colore: str, *, livello: str = "below"
) -> dict[str, Any]:
    """Costruisce una circonferenza vuota.

    Args:
        cx: Ascissa del centro.
        cy: Ordinata del centro.
        raggio: Il raggio.
        colore: Il colore del contorno.
        livello: ``"below"`` o ``"above"``, rispetto alle tracce.

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
        "layer": livello,
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


def segnature(tema: Tema, *, sopra: bool = False) -> list[dict[str, Any]]:
    """Disegna le linee regolamentari del campo.

    Solo la meta' offensiva ha le aree: le viste di questo progetto guardano i
    tiri, e un campo intero con due aree sprecherebbe meta' dello spazio su
    una zona dove non succede quasi niente di ciò che interessa.

    Args:
        tema: La palette attiva.
        sopra: Se vero le linee stanno **sopra** le tracce invece che sotto.
            Serve alle mappe di calore, che coprono il campo: linee sotto una
            superficie opaca sono linee che non ci sono.

    Returns:
        Le forme delle linee.
    """
    colore = tema.linee
    livello = "above" if sopra else "below"
    return [
        _riquadro(0.0, 0.0, LUNGHEZZA, LARGHEZZA, colore, livello=livello),
        _linea(LUNGHEZZA / 2, 0.0, LUNGHEZZA / 2, LARGHEZZA, colore, livello=livello),
        _cerchio(LUNGHEZZA / 2, PORTA_Y, RAGGIO, colore, livello=livello),
        _riquadro(AREA_X, AREA_Y_MIN, PORTA_X, AREA_Y_MAX, colore, livello=livello),
        _riquadro(
            AREA_PICCOLA_X, AREA_PICCOLA_Y_MIN, PORTA_X, AREA_PICCOLA_Y_MAX, colore, livello=livello
        ),
        _cerchio(DISCHETTO_X, PORTA_Y, 0.4, colore, livello=livello),
        _cerchio(LUNGHEZZA / 2, PORTA_Y, 0.4, colore, livello=livello),
        # La porta, disegnata piu' spessa: e' il riferimento visivo di ogni
        # vista sui tiri, e a questa scala una linea sottile sparisce.
        {
            "type": "line",
            "x0": PORTA_X,
            "y0": PALO_SINISTRO_Y,
            "x1": PORTA_X,
            "y1": PALO_DESTRO_Y,
            "line": {"color": colore, "width": SPESSORE * 3},
            "layer": livello,
        },
    ]


#: Raggio minimo e massimo di un tiro sulla mappa, in pixel.
PALLINO_MINIMO: Final[float] = 3.5
PALLINO_MASSIMO: Final[float] = 22.0

#: Spessore minimo e massimo di un legame nella rete dei passaggi.
SPESSORE_MINIMO: Final[float] = 1.0
SPESSORE_MASSIMO: Final[float] = 9.0


def _dimensioni(xg: npt.ArrayLike) -> list[float]:
    """Traduce l'xG in raggi visibili.

    **La dimensione e' proporzionale alla radice dell'xG, non all'xG.** L'occhio
    confronta le **aree**, e un'area proporzionale al valore e' la traduzione
    onesta: usando il raggio, un tiro da 0,4 sembrerebbe quattro volte uno da
    0,1 invece di quattro volte in area, cioe' il doppio in larghezza. E' lo
    stesso errore delle mappe con i cerchi proporzionali al raggio, ed e' il
    modo piu' comune di esagerare un grafico senza volerlo.

    Args:
        xg: I valori di xG dei tiri.

    Returns:
        I raggi, uno per tiro.

    """
    valori = np.asarray(xg, dtype=float)
    if valori.size == 0:
        return []
    massimo = float(valori.max())
    quota = np.sqrt(valori / massimo) if massimo > 0 else np.zeros_like(valori)
    return list(PALLINO_MINIMO + quota * (PALLINO_MASSIMO - PALLINO_MINIMO))


def _sfondo(figura: go.Figure, tema: Tema, altezza: int) -> go.Figure:
    """Applica a una figura lo sfondo e i caratteri del tema.

    **Il carattere e' quello del testo pieno, non quello tenue.** Il colore
    generale della figura vale anche per la legenda, e una legenda e' il nome
    delle serie: senza, un grafico a due linee non si legge. Sul tema scuro la
    differenza era netta — «xG» e «Gol» sparivano nel fondo. Le tacche degli
    assi restano tenui perche' hanno il proprio ``tickfont``: la' lo
    sbiadimento e' voluto, e' contesto.

    Args:
        figura: La figura da vestire.
        tema: La palette attiva.
        altezza: Altezza in pixel.

    Returns:
        La stessa figura.
    """
    figura.update_layout(
        height=altezza,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor=TRASPARENTE,
        plot_bgcolor=TRASPARENTE,
        dragmode=False,
        font={"color": tema.testo, "size": 12},
        hoverlabel={"bgcolor": tema.superficie, "font": {"color": tema.testo}},
    )
    figura.update_xaxes(tickfont={"color": tema.testo_tenue, "size": 11})
    figura.update_yaxes(tickfont={"color": tema.testo_tenue, "size": 11})
    return figura


def ciambella(
    quota: float, etichetta: str, sotto: str, tema: Tema, altezza: int = 200
) -> go.Figure:
    """Un anello con la percentuale al centro.

    **Un anello e non una torta.** Una torta con due fette si legge peggio di
    un numero scritto, e il buco al centro serve proprio a ospitare quel
    numero: la forma diventa un contorno del dato invece che il dato stesso.

    Args:
        quota: Il valore da rappresentare, fra 0 e oltre 1.
        etichetta: Il numero grande al centro.
        sotto: La riga piccola sotto il numero.
        tema: La palette attiva.
        altezza: Altezza in pixel.

    Returns:
        La figura.
    """
    pieno = min(max(quota, 0.0), 1.0)
    figura = go.Figure(
        go.Pie(
            values=[pieno, 1 - pieno],
            hole=0.74,
            sort=False,
            direction="clockwise",
            rotation=0,
            marker={"colors": [tema.primario, tema.bordo], "line": {"width": 0}},
            textinfo="none",
            hoverinfo="skip",
        )
    )
    figura.add_annotation(
        text=(
            f"<span style='font-size:26px;color:{tema.testo}'><b>{etichetta}</b></span>"
            f"<br><span style='font-size:11px;color:{tema.testo_tenue}'>{sotto}</span>"
        ),
        showarrow=False,
        x=0.5,
        y=0.5,
    )
    figura.update_layout(showlegend=False)
    return _sfondo(figura, tema, altezza)


def istogramma_xg(tiri: pd.DataFrame, tema: Tema, altezza: int = 240) -> go.Figure:
    """La distribuzione dell'xG per tiro.

    E' il grafico che spiega il progetto meglio di qualunque frase: la maggior
    parte dei tiri vale pochissimo, e la coda a destra e' fatta di pochi tiri
    che valgono quasi mezza rete. Chi guarda capisce da solo perche' contare i
    tiri non basta.

    Args:
        tiri: I tiri della selezione, con ``xg_statsbomb``.
        tema: La palette attiva.
        altezza: Altezza in pixel.

    Returns:
        La figura.
    """
    figura = go.Figure()
    if not tiri.empty:
        figura.add_trace(
            go.Histogram(
                x=tiri["xg_statsbomb"],
                nbinsx=40,
                marker={"color": tema.primario, "line": {"width": 0}},
                hovertemplate="xG %{x:.2f}<br>%{y} tiri<extra></extra>",
            )
        )
    figura.update_layout(bargap=0.05, showlegend=False)
    figura.update_xaxes(title_text="xG per tiro", gridcolor=tema.bordo, zeroline=False)
    figura.update_yaxes(gridcolor=tema.bordo, zeroline=False)
    return _sfondo(figura, tema, altezza)


def linee(
    x: Sequence[object],
    serie: Mapping[str, Sequence[float]],
    tema: Tema,
    altezza: int = 240,
    *,
    a_gradini: bool = False,
) -> go.Figure:
    """Un grafico a linee con i colori del tema.

    Args:
        x: I valori dell'asse orizzontale, condivisi da tutte le serie.
        serie: Nome della serie e i suoi valori.
        tema: La palette attiva.
        altezza: Altezza in pixel.
        a_gradini: Se vero la linea sale di scatto invece che in diagonale.
            Serve all'xG accumulato durante una partita: **l'xG non cresce di
            continuo, salta a ogni tiro**. Una diagonale fra due tiri
            suggerirebbe che fra il minuto 12 e il 34 la squadra abbia creato
            qualcosa, e in quei ventidue minuti non e' successo niente.

    Returns:
        La figura.
    """
    colori = (tema.primario, tema.testo, tema.atteso)
    figura = go.Figure()
    for (nome, valori), colore in zip(serie.items(), colori, strict=False):
        figura.add_trace(
            go.Scatter(
                x=list(x),
                y=list(valori),
                mode="lines",
                name=nome,
                line={"color": colore, "width": 2.2, "shape": "hv" if a_gradini else "linear"},
            )
        )
    figura.update_layout(
        legend={"orientation": "h", "y": 1.15, "x": 1, "xanchor": "right"},
        hovermode="x unified",
    )
    figura.update_xaxes(gridcolor=tema.bordo, showgrid=False)
    figura.update_yaxes(gridcolor=tema.bordo, zeroline=False)
    return _sfondo(figura, tema, altezza)


def attese_contro_realizzato(
    tabella: pd.DataFrame,
    tema: Tema,
    *,
    nome: str = "giocatore",
    etichette: int = 6,
    altezza: int = 380,
) -> go.Figure:
    """Gol contro xG, un punto per giocatore, con la bisettrice.

    **La diagonale e' il grafico.** Senza, due nuvole di punti dicono soltanto
    che chi tira di piu' segna di piu'; con la retta ``gol = xG`` la distanza
    verticale da essa diventa leggibile a occhio: sopra sta chi ha realizzato
    piu' di quanto le occasioni promettessero, sotto chi ha sprecato.

    **Gli assi hanno la stessa scala e la stessa lunghezza.** Se non lo fossero
    la bisettrice non sarebbe a quarantacinque gradi, e la distanza da essa
    ingannerebbe l'occhio: e' il modo silenzioso in cui questo grafico mente.

    Solo i punti piu' lontani dalla retta portano il nome: con quattrocento
    giocatori le etichette diventano un muro di testo che copre i punti.

    Args:
        tabella: Le statistiche dei giocatori, con ``xg``, ``gol`` e
            ``gol_meno_xg``.
        tema: La palette attiva.
        nome: La colonna da cui prendere l'etichetta. Il magazzino ha sia il
            nome completo sia quello con cui il giocatore e' conosciuto, e su
            un grafico serve il secondo: l'ultima parola del nome anagrafico
            di Cristiano Ronaldo e' «Aveiro».
        etichette: Quanti nomi mostrare per lato, sopra e sotto la retta.
        altezza: Altezza in pixel.

    Returns:
        La figura.
    """
    figura = go.Figure()
    if tabella.empty:
        return _sfondo(figura, tema, altezza)

    limite = float(max(tabella["xg"].max(), tabella["gol"].max())) * 1.08
    figura.add_shape(
        type="line",
        x0=0.0,
        y0=0.0,
        x1=limite,
        y1=limite,
        line={"color": tema.linee, "width": 1.4, "dash": "dash"},
        layer="below",
    )

    scarto = tabella["gol_meno_xg"]
    colonna = nome if nome in tabella.columns else "giocatore"
    da_nominare = set(tabella.nlargest(etichette, "gol_meno_xg")[colonna]) | set(
        tabella.nsmallest(etichette, "gol_meno_xg")[colonna]
    )
    nomi = [
        str(etichetta) if etichetta in da_nominare else ""
        for etichetta in tabella[colonna].to_numpy()
    ]

    figura.add_trace(
        go.Scatter(
            x=tabella["xg"].to_numpy(),
            y=tabella["gol"].to_numpy(),
            mode="markers+text",
            text=nomi,
            textposition="top center",
            textfont={"size": 10, "color": tema.testo_tenue},
            marker={
                "size": 9,
                "color": [tema.gol if valore >= 0 else tema.pericolo for valore in scarto],
                "line": {"color": tema.superficie, "width": 1},
                "opacity": 0.85,
            },
            customdata=tabella[colonna].to_numpy(),
            hovertemplate="%{customdata}<br>xG %{x:.1f} · gol %{y:.0f}<extra></extra>",
            showlegend=False,
        )
    )

    figura.update_xaxes(
        title={"text": "xG generato", "font": {"size": 11}},
        range=[0, limite],
        gridcolor=tema.bordo,
        zeroline=False,
    )
    figura.update_yaxes(
        title={"text": "gol", "font": {"size": 11}},
        range=[0, limite],
        gridcolor=tema.bordo,
        zeroline=False,
        scaleanchor="x",
        scaleratio=1,
    )
    return _sfondo(figura, tema, altezza)


def radar(
    valori: Mapping[str, float],
    tema: Tema,
    *,
    altezza: int = 340,
) -> go.Figure:
    """Un radar su scala 0-100, con la mediana del reparto segnata.

    **La scala e' fissa da 0 a 100 e non si adatta ai dati.** Un radar che
    ridimensiona gli assi fa sembrare fenomenale chiunque, perche' il punto
    piu' alto tocca sempre il bordo. Con la scala bloccata la forma dice
    qualcosa: piccola vuol dire piccola.

    **Il cerchio a 50 e' la mediana del reparto**, disegnato come seconda
    traccia invece che come griglia: cosi' si vede *dove* il giocatore sta
    sopra e dove sotto, che e' l'unica lettura per cui un radar serve.

    Args:
        valori: Etichetta dell'asse e percentile, da 0 a 100.
        tema: La palette attiva.
        altezza: Altezza in pixel.

    Returns:
        La figura.
    """
    etichette = list(valori)
    figura = go.Figure()
    if not etichette:
        return _sfondo(figura, tema, altezza)

    # Il primo punto va ripetuto in fondo, o il poligono resta aperto fra
    # l'ultimo asse e il primo.
    chiuse = [*etichette, etichette[0]]
    figura.add_trace(
        go.Scatterpolar(
            r=[50.0] * len(chiuse),
            theta=chiuse,
            mode="lines",
            line={"color": tema.linee, "width": 1.2, "dash": "dot"},
            name="mediana del reparto",
            hoverinfo="skip",
        )
    )
    punti = [float(valori[nome]) for nome in etichette]
    figura.add_trace(
        go.Scatterpolar(
            r=[*punti, punti[0]],
            theta=chiuse,
            mode="lines+markers",
            fill="toself",
            fillcolor=tema.primario_tenue,
            line={"color": tema.primario, "width": 2.2},
            marker={"size": 7, "color": tema.primario},
            name="giocatore",
            hovertemplate="%{theta}<br>percentile %{r:.0f}<extra></extra>",
        )
    )
    figura.update_layout(
        polar={
            "bgcolor": TRASPARENTE,
            "radialaxis": {
                "range": [0, 100],
                "showticklabels": False,
                "gridcolor": tema.bordo,
                "linecolor": tema.bordo,
            },
            "angularaxis": {
                "gridcolor": tema.bordo,
                "linecolor": tema.bordo,
                "tickfont": {"size": 11, "color": tema.testo_tenue},
            },
        },
        showlegend=False,
    )
    return _sfondo(figura, tema, altezza)


def mappa_tocchi(tocchi: pd.DataFrame, tema: Tema, *, altezza: int = 420) -> go.Figure:
    """Dove un giocatore tocca il pallone, dalla griglia gia' aggregata.

    **Non riusa** :func:`mappa_di_calore`: quella parte dai tiri e li conta in
    celle, questa riceve celle gia' contate. Costringere le due cose nella
    stessa funzione vorrebbe dire un parametro che cambia il significato del
    primo argomento, e nessuno se ne ricorderebbe.

    **Il campo e' intero.** I tocchi di un terzino stanno nella propria meta',
    e mezzo campo ne mostrerebbe la meta' facendolo sembrare un attaccante
    che non tocca mai la palla.

    Args:
        tocchi: Le celle con ``cella_x``, ``cella_y`` e ``tocchi``.
        tema: La palette attiva.
        altezza: Altezza in pixel.

    Returns:
        Il campo con sopra la densita' dei tocchi.
    """
    figura = campo(tema, altezza=altezza, meta_campo=False, linee_sopra=True)
    if tocchi.empty:
        return figura

    lato_x = LUNGHEZZA / (int(tocchi["cella_x"].max()) + 1)
    lato_y = LARGHEZZA / (int(tocchi["cella_y"].max()) + 1)
    # `fill_value` intero e non ``0.0``: la colonna dei tocchi e' un conteggio,
    # e pandas avvisa che riempire un intero con un float e' deprecato.
    griglia = tocchi.pivot_table(
        index="cella_y", columns="cella_x", values="tocchi", aggfunc="sum", fill_value=0
    )
    conteggi = _sfoca(griglia.to_numpy().astype(np.float64))
    massimo = float(conteggi.max())
    if massimo <= 0:
        return figura

    # Gli indici passano da `int()`: per pandas-stubs le etichette di colonna
    # sono stringhe, e `i + 0.5` non compila anche se a runtime sono numeri.
    figura.add_trace(
        go.Heatmap(
            x=[(int(i) + 0.5) * lato_x for i in griglia.columns],
            y=[(int(j) + 0.5) * lato_y for j in griglia.index],
            z=np.sqrt(conteggi),
            zmin=0.0,
            zmax=float(np.sqrt(massimo)),
            colorscale=[
                list(gradino)
                for gradino in scala_calore(tema, math.sqrt(min(SOGLIA_CALORE / massimo, 1.0)))
            ],
            zsmooth="best",
            showscale=False,
            hoverinfo="skip",
        )
    )
    return figura


def per_esito(tiri: pd.DataFrame, tema: Tema, *, altezza: int = 420) -> go.Figure:
    """I tiri di una squadra, distinti solo fra gol e non gol.

    **Due colori invece di cinque fasce.** Sulla selezione di una squadra i
    tiri sono qualche centinaio invece di decine di migliaia: le fasce di xG
    diventano una legenda inutilmente fitta, mentre la domanda che si fa
    guardando una singola squadra e' «da dove ha segnato». L'xG resta, ma
    nell'area del cerchio.

    Args:
        tiri: I tiri della squadra.
        tema: La palette attiva.
        altezza: Altezza della figura in pixel.

    Returns:
        Il campo con i tiri sopra.
    """
    figura = campo(tema, altezza=altezza, meta_campo=True)
    if tiri.empty:
        return figura

    for etichetta, riempimento, gol in (
        ("tiro", tema.primario_tenue, False),
        ("gol", tema.gol, True),
    ):
        parte = tiri[tiri["gol"].astype(bool) == gol]
        if parte.empty:
            continue
        figura.add_trace(
            go.Scatter(
                x=parte["x"],
                y=parte["y"],
                mode="markers",
                name=etichetta,
                marker={
                    "size": _dimensioni(parte["xg_statsbomb"].to_numpy()),
                    "color": riempimento,
                    "opacity": 0.9 if gol else 0.75,
                    "line": {"width": 1.0, "color": tema.gol if gol else tema.linee},
                },
                hoverinfo="skip",
            )
        )
    figura.update_layout(
        showlegend=True,
        legend={
            "orientation": "h",
            "y": -0.02,
            "x": 0,
            "bgcolor": TRASPARENTE,
            "font": {"size": 11},
            "itemsizing": "constant",
        },
    )
    return figura


def rete_passaggi(
    nodi: pd.DataFrame,
    archi: pd.DataFrame,
    dimensioni: pd.Series,
    tema: Tema,
    *,
    altezza: int = 420,
) -> go.Figure:
    """La rete dei passaggi sopra il campo intero.

    **I giocatori portano il nome, non il numero di maglia.** I numeri non
    esistono in ``player_stats``, e inventarli per far somigliare il grafico a
    una formazione sarebbe l'unica cosa falsa di tutta la pagina.

    Gli archi sono forme e non tracce: Plotly non sa variare lo spessore
    **dentro** una traccia, quindi venti legami di spessore diverso
    vorrebbero dire venti tracce e venti voci di legenda da nascondere.

    Args:
        nodi: Il risultato di :func:`passaggi.titolari`.
        archi: Il risultato di :func:`passaggi.rete`.
        dimensioni: Il risultato di :func:`passaggi.coinvolgimento`.
        tema: La palette attiva.
        altezza: Altezza della figura in pixel.

    Returns:
        Il campo con la rete sopra.
    """
    figura = campo(tema, altezza=altezza, meta_campo=False)
    if nodi.empty:
        return figura

    if not archi.empty:
        massimo = float(archi["passaggi"].max())
        linee_arco = [
            {
                "type": "line",
                "x0": riga["x0"],
                "y0": riga["y0"],
                "x1": riga["x1"],
                "y1": riga["y1"],
                "line": {
                    "color": tema.primario,
                    "width": SPESSORE_MINIMO
                    + (SPESSORE_MASSIMO - SPESSORE_MINIMO) * riga["passaggi"] / massimo,
                },
                "opacity": 0.35,
                "layer": "below",
            }
            for riga in archi.to_dict("records")
        ]
        figura.update_layout(shapes=[*figura.layout.shapes, *linee_arco])

    coinvolti = dimensioni.reindex(nodi["giocatore_breve"]).fillna(0.0).to_numpy()
    figura.add_trace(
        go.Scatter(
            x=nodi["x_media"],
            y=nodi["y_media"],
            mode="markers+text",
            text=nodi["giocatore_breve"],
            textposition="bottom center",
            textfont={"size": 10, "color": tema.testo},
            marker={
                "size": _dimensioni(coinvolti / max(coinvolti.max(), 1.0)),
                "color": tema.primario,
                "line": {"width": 1.4, "color": tema.superficie},
            },
            hoverinfo="skip",
        )
    )
    return figura


def shot_map(
    tiri: pd.DataFrame,
    tema: Tema,
    *,
    altezza: int = 520,
    meta_campo: bool = True,
) -> go.Figure:
    """Disegna i tiri sul campo, per fascia di xG e con i gol in evidenza.

    **Cinque fasce di colore invece di una scala continua.** Su migliaia di
    pallini piccoli e sovrapposti un gradiente non si legge: nessuno distingue
    0,18 da 0,24 guardando una sfumatura. Cinque classi si leggono dalla
    legenda, si contano, e i confini — 0,05 · 0,10 · 0,30 · 0,50 — separano il
    tiro da fuori dal tiro in area e l'occasione dalla quasi-rete.

    **I gol hanno un anello, non un colore diverso.** Cambiare colore per
    l'esito toglierebbe la lettura dell'xG proprio ai tiri piu' interessanti.
    Il contorno li distingue senza rubare il posto all'informazione.

    Args:
        tiri: I tiri da mostrare, con ``x``, ``y``, ``gol`` e ``xg_statsbomb``.
        tema: La palette attiva.
        altezza: Altezza della figura in pixel.
        meta_campo: Se falso mostra il campo intero, che e' orizzontale. Mezzo
            campo e' piu' grande ma **verticale**, perche' sessanta unita' di
            lunghezza contro ottanta di larghezza danno un riquadro piu' alto
            che largo.

    Returns:
        Il campo con i tiri sopra.
    """
    figura = campo(tema, altezza=altezza, meta_campo=meta_campo)
    if tiri.empty:
        return figura

    valori = tiri["xg_statsbomb"].to_numpy()
    inferiore = 0.0
    for etichetta, superiore, colore, trasparenza in scala_di(tema):
        dentro = (valori >= inferiore) & (valori < superiore)
        inferiore = superiore
        if not dentro.any():
            continue
        parte = tiri[dentro]
        figura.add_trace(
            go.Scatter(
                x=parte["x"],
                y=parte["y"],
                mode="markers",
                name=etichetta,
                legendgroup=etichetta,
                marker={
                    "size": _dimensioni(parte["xg_statsbomb"].to_numpy()),
                    "color": colore,
                    "opacity": trasparenza,
                    "line": {
                        "width": [1.6 if g else 0.0 for g in parte["gol"]],
                        "color": tema.testo,
                    },
                },
                hoverinfo="skip",
            )
        )

    figura.update_layout(
        showlegend=True,
        legend={
            "title": {"text": "xG", "font": {"size": 11}},
            "orientation": "v",
            "x": 1.01,
            "y": 1,
            "bgcolor": TRASPARENTE,
            "font": {"size": 11},
            "itemsizing": "constant",
        },
    )
    return figura


def campo(
    tema: Tema, *, meta_campo: bool = True, altezza: int = 520, linee_sopra: bool = False
) -> go.Figure:
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
        linee_sopra: Se vero le linee del campo stanno sopra le tracce.

    Returns:
        La figura, con erba, linee, assi configurati e nessun dato.
    """
    figura = go.Figure()
    figura.update_layout(
        shapes=erba(tema) + segnature(tema, sopra=linee_sopra),
        paper_bgcolor=TRASPARENTE,
        plot_bgcolor=tema.erba_scura,
        font={"color": tema.testo},
        height=altezza,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        showlegend=False,
        # Nessun trascinamento finche' non si preme il pulsante dello zoom: su
        # un campo il movimento del mouse e' esplorazione, non un comando.
        dragmode=False,
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


#: Lato della cella della mappa di calore, in iarde.
#:
#: Quattro e non due: a due iarde meta' delle celle piene contiene un tiro solo
#: e la mappa diventa una spruzzata di puntini, cioe' la nuvola di punti che si
#: voleva sostituire. A otto l'area di rigore starebbe in due celle e mezza.
PASSO_CALORE: Final[float] = 4.0

#: Quanti gradini nella barra dei colori.
GRADINI: Final[int] = 5

#: Ampiezza della sfocatura della mappa di calore, in celle.
#:
#: ``zsmooth`` di Plotly interpola fra celle vicine ma non toglie il rumore:
#: una cella con due tiri accanto a una vuota resta una macchia quadrata, e su
#: quarantamila tiri il campo si riempiva di quadretti staccati. Una media
#: pesata sui vicini li fonde in una nuvola continua, che e' quello che una
#: mappa di densita' dovrebbe essere.
SFOCATURA: Final[int] = 2

#: Sotto quanti tiri per cella la mappa di calore non disegna niente.
#:
#: Una cella dove si e' tirato meno di una volta non ha niente da mostrare, e
#: lasciarla verde e' piu' onesto che velarla di bianco. La soglia e' in
#: **tiri veri**, non in posizione sulla scala: la stessa posizione vale 1,6
#: tiri in Serie A (cella piu' battuta 441) e 0,09 nelle finali di Champions
#: (cella piu' battuta 26), quindi una soglia fissa sulla scala coprirebbe due
#: cose diverse. Cosi' com'e', sulla Serie A resta scoperto il 67 % del campo —
#: esattamente le celle dove nessuno ha mai tirato.
SOGLIA_CALORE: Final[float] = 1.0


def _sfoca(griglia: npt.NDArray[np.float64], raggio: int = SFOCATURA) -> npt.NDArray[np.float64]:
    """Smussa una griglia con una media pesata sui vicini.

    E' una gaussiana separabile applicata due volte, una per asse: costa due
    passate invece di una convoluzione bidimensionale, e non serve scipy —
    che il progetto non ha fra le dipendenze e non vale la pena aggiungere per
    quindici righe.

    **La somma non si conserva**, e va detto: ai bordi la finestra sporge dal
    campo e i pesi che cadono fuori vengono persi. Non e' un problema qui
    perche' il colore e' relativo al massimo, ma vorrebbe dire che questa
    funzione non si puo' riusare dove i conteggi devono tornare.

    Args:
        griglia: I conteggi per cella.
        raggio: Quante celle per lato entrano nella media.

    Returns:
        La griglia smussata, della stessa forma.
    """
    distanze = np.arange(-raggio, raggio + 1, dtype=np.float64)
    pesi = np.exp(-((distanze / raggio) ** 2) * 2.0)
    pesi /= pesi.sum()

    smussata = np.apply_along_axis(lambda riga: np.convolve(riga, pesi, mode="same"), 0, griglia)
    return np.apply_along_axis(lambda riga: np.convolve(riga, pesi, mode="same"), 1, smussata)


def griglia_dei_tiri(
    tiri: pd.DataFrame, passo: float = PASSO_CALORE
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Conta i tiri per cella, senza smussare niente.

    Sta fuori da :func:`mappa_di_calore` perche' e' l'unico punto in cui i
    conteggi sono ancora esatti: la sfocatura che viene dopo **non conserva la
    somma** — ai bordi la finestra sporge dal campo e i pesi che cadono fuori
    si perdono — quindi «nessun tiro e' andato perso» si puo' verificare solo
    qui.

    Args:
        tiri: I tiri da contare, con ``x`` e ``y``.
        passo: Il lato della cella, in iarde.

    Returns:
        I conteggi, i bordi in x e i bordi in y.
    """
    bordi_x: npt.NDArray[np.float64] = np.arange(0.0, LUNGHEZZA + passo, passo, dtype=np.float64)
    bordi_y: npt.NDArray[np.float64] = np.arange(0.0, LARGHEZZA + passo, passo, dtype=np.float64)
    # ``histogram2d`` restituisce ``Any`` per i conteggi: senza l'annotazione
    # esplicita il tipo si perderebbe qui e ricomparirebbe come ``Any`` in ogni
    # chiamante, che e' il modo silenzioso in cui mypy smette di servire.
    conteggi: npt.NDArray[np.float64]
    conteggi, _, _ = np.histogram2d(
        tiri["x"].to_numpy(), tiri["y"].to_numpy(), bins=[bordi_x, bordi_y]
    )
    return conteggi, bordi_x, bordi_y


def mappa_di_calore(
    tiri: pd.DataFrame,
    tema: Tema,
    *,
    altezza: int = 520,
    meta_campo: bool = True,
    passo: float = PASSO_CALORE,
) -> go.Figure:
    """Disegna da dove si tira, come densita' invece che come singoli tiri.

    **Il colore cresce con la radice del conteggio, non con il conteggio.**
    La distribuzione e' molto sbilanciata: nel magazzino la cella piu' battuta
    ne ha 1.863 e la mediana delle celle piene ne ha 5. Con una scala lineare
    fra il 26 % e il 74 % delle celle piene resta sotto il 10 % di intensita',
    cioe' invisibile, e la mappa mostra un solo punto caldo su un campo vuoto.
    Con la radice quella quota scende fra lo 0 % e il 62 %, e sulla selezione
    di una singola squadra nessuna cella sparisce.

    **La barra dei colori riporta i conteggi veri**, non le radici: la
    trasformazione serve all'occhio, e nasconderla nell'etichetta la
    trasformerebbe in un numero sbagliato.

    **Le linee del campo passano sopra.** Una superficie colorata che copre
    l'area di rigore rende impossibile capire dove sia l'area di rigore, che e'
    l'unico riferimento per leggere la mappa.

    **Dove non si tira il campo resta verde**: sotto :data:`SOGLIA_CALORE` tiri
    per cella la mappa e' trasparente. La soglia e' convertita in posizione
    sulla scala qui, perche' dipende dal massimo di questa mappa.

    Args:
        tiri: I tiri da contare, con le colonne ``x`` e ``y``.
        tema: La palette attiva.
        altezza: Altezza della figura in pixel.
        meta_campo: Se falso mostra il campo intero.
        passo: Il lato della cella, in iarde.

    Returns:
        Il campo con sopra la densita' dei tiri.
    """
    figura = campo(tema, altezza=altezza, meta_campo=meta_campo, linee_sopra=True)
    if tiri.empty:
        return figura

    conteggi, bordi_x, bordi_y = griglia_dei_tiri(tiri, passo)
    massimo = float(conteggi.max())
    if massimo <= 0:
        return figura
    # La barra dei colori riporta i conteggi veri, quindi la scala resta legata
    # al massimo **prima** della sfocatura: smussando, il picco si abbassa, e
    # leggere la scala su quello ridotto direbbe che la cella piu' battuta ha
    # meno tiri di quanti ne ha.
    smussati = _sfoca(conteggi)
    conteggi = smussati * (massimo / max(float(smussati.max()), 1e-9))

    centri_x = (bordi_x[:-1] + bordi_x[1:]) / 2
    centri_y = (bordi_y[:-1] + bordi_y[1:]) / 2
    tacche = np.linspace(0.0, massimo, GRADINI)

    figura.add_trace(
        go.Heatmap(
            x=centri_x,
            y=centri_y,
            z=np.sqrt(conteggi).T,
            colorscale=[
                list(gradino)
                for gradino in scala_calore(tema, math.sqrt(min(SOGLIA_CALORE / massimo, 1.0)))
            ],
            zmin=0.0,
            zmax=float(np.sqrt(massimo)),
            zsmooth="best",
            hoverinfo="skip",
            colorbar={
                "title": {"text": "tiri", "font": {"size": 11}},
                "thickness": 10,
                "len": 0.75,
                "outlinewidth": 0,
                "tickfont": {"size": 11, "color": tema.testo_tenue},
                "tickvals": np.sqrt(tacche),
                "ticktext": [f"{valore:.0f}" for valore in tacche],
            },
        )
    )
    return figura
