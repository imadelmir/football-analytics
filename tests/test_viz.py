"""Verifiche del campo in Plotly (M6-T2).

Un grafico non si verifica guardandolo — o meglio, si guarda **anche**, ma
quello che si vede a occhio non distingue un campo con le proporzioni sbagliate
da uno giusto, ne' un asse invertito da uno corretto. Entrambi gli errori
producono immagini plausibili.

Quello che si puo' verificare a macchina e' che le misure siano quelle
regolamentari, che gli assi siano configurati come devono, e che il campo non
contenga una seconda copia delle coordinate gia' definite per il modello.
"""

from __future__ import annotations

from typing import Any

import pytest

from football_analytics import features, tema, viz


@pytest.fixture
def figura() -> Any:
    """Un campo disegnato con il tema verde.

    Returns:
        La figura di Plotly.
    """
    return viz.campo(tema.VERDE)


def forme(figura: Any) -> list[Any]:
    """Estrae le forme dal layout della figura.

    Args:
        figura: La figura di Plotly.

    Returns:
        L'elenco delle forme.
    """
    return list(figura.layout.shapes)


# ---------------------------------------------------------------------------
# Le misure sono quelle regolamentari
# ---------------------------------------------------------------------------


def test_il_campo_disegna_le_coordinate_del_modello() -> None:
    """Le linee disegnate cadono sulle coordinate che il modello usa.

    La prima stesura confrontava gli oggetti importati — `viz.AREA_X is
    features.AREA_X` — e verificava un import invece di un comportamento.
    Passava anche se `campo` avesse disegnato l'area da tutt'altra parte.

    Questa versione guarda le forme prodotte: se un giorno il campo avesse una
    sua copia delle coordinate, la vista mostrerebbe un'area e il modello ne
    userebbe un'altra, senza che niente segnali il disaccordo.
    """
    segni = viz.segnature(tema.VERDE)
    ascisse = {float(s["x0"]) for s in segni} | {float(s["x1"]) for s in segni}
    ordinate = {float(s["y0"]) for s in segni} | {float(s["y1"]) for s in segni}

    assert features.AREA_X in ascisse
    assert features.PORTA_X in ascisse
    assert features.AREA_Y_MIN in ordinate
    assert features.AREA_Y_MAX in ordinate
    assert features.PALO_SINISTRO_Y in ordinate
    assert features.PALO_DESTRO_Y in ordinate


def test_le_misure_regolamentari_sono_rispettate() -> None:
    # Il campo StatsBomb e' in iarde: 18 di area grande, 6 di area piccola,
    # 12 per il dischetto, 8 di porta. Sono numeri controllabili sul
    # regolamento, non su un'esecuzione del codice.
    assert pytest.approx(18.0) == features.PORTA_X - features.AREA_X
    assert pytest.approx(6.0) == features.PORTA_X - viz.AREA_PICCOLA_X
    assert pytest.approx(12.0) == features.PORTA_X - viz.DISCHETTO_X
    assert pytest.approx(8.0) == features.PALO_DESTRO_Y - features.PALO_SINISTRO_Y
    assert pytest.approx(44.0) == features.AREA_Y_MAX - features.AREA_Y_MIN
    assert pytest.approx(20.0) == viz.AREA_PICCOLA_Y_MAX - viz.AREA_PICCOLA_Y_MIN


def test_le_aree_sono_centrate_sulla_porta() -> None:
    centro_area = (features.AREA_Y_MIN + features.AREA_Y_MAX) / 2
    centro_piccola = (viz.AREA_PICCOLA_Y_MIN + viz.AREA_PICCOLA_Y_MAX) / 2

    assert centro_area == pytest.approx(features.PORTA_Y)
    assert centro_piccola == pytest.approx(features.PORTA_Y)


def test_l_area_piccola_sta_dentro_quella_grande() -> None:
    assert viz.AREA_PICCOLA_X > features.AREA_X
    assert viz.AREA_PICCOLA_Y_MIN > features.AREA_Y_MIN
    assert viz.AREA_PICCOLA_Y_MAX < features.AREA_Y_MAX


def test_il_dischetto_sta_dentro_l_area() -> None:
    assert features.AREA_X < viz.DISCHETTO_X < features.PORTA_X


# ---------------------------------------------------------------------------
# Gli assi, dove si nascondono gli errori invisibili
# ---------------------------------------------------------------------------


def test_l_asse_verticale_e_invertito(figura: Any) -> None:
    """In StatsBomb la y cresce verso il basso.

    Senza inversione le azioni risultano ribaltate, e il grafico resta
    plausibile: e' l'errore piu' comune con questi dati proprio perche' non si
    vede.
    """
    inizio, fine = figura.layout.yaxis.range

    assert inizio > fine


def test_le_proporzioni_sono_bloccate(figura: Any) -> None:
    # Un campo 120x80 disegnato in un riquadro quadrato mostra distanze
    # sbagliate, e un modello che parla di metri finirebbe illustrato da un
    # grafico che mente sulle distanze.
    assert figura.layout.yaxis.scaleanchor == "x"
    assert figura.layout.yaxis.scaleratio == 1


def test_meta_campo_mostra_la_meta_offensiva(figura: Any) -> None:
    inizio, fine = figura.layout.xaxis.range

    assert inizio == pytest.approx(viz.LUNGHEZZA / 2)
    assert fine == pytest.approx(viz.LUNGHEZZA)


def test_il_campo_intero_si_puo_chiedere() -> None:
    intero = viz.campo(tema.VERDE, meta_campo=False)

    assert intero.layout.xaxis.range == (0.0, viz.LUNGHEZZA)


def test_gli_assi_non_hanno_numeri(figura: Any) -> None:
    # Le coordinate StatsBomb non significano niente per chi guarda: mostrarle
    # aggiungerebbe rumore e suggerirebbe una precisione che non serve.
    assert figura.layout.xaxis.visible is False
    assert figura.layout.yaxis.visible is False


# ---------------------------------------------------------------------------
# Il tema arriva davvero fino al disegno
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_il_campo_usa_i_colori_del_tema(scelto: tema.Tema) -> None:
    disegnato = viz.campo(scelto)
    usati = {f.fillcolor for f in forme(disegnato) if f.fillcolor}

    assert scelto.erba_chiara in usati
    assert scelto.erba_scura in usati
    assert disegnato.layout.paper_bgcolor == scelto.superficie


def test_le_finali_disegnano_un_campo_blu() -> None:
    """Il criterio di M6-T1: le finali rendono l'app blu, campo compreso.

    La prima stesura confrontava ``paper_bgcolor``, cioe' il fondo della
    scheda. Con il tema chiaro quello e' bianco in **entrambi** i temi — ed e'
    giusto che lo sia — quindi il test falliva pur essendo tutto a posto.
    Cio' che distingue davvero i due campi e' l'erba.
    """
    verde = viz.campo(tema.per_gruppo("campionato"))
    blu = viz.campo(tema.per_gruppo("finali"))

    assert verde.layout.plot_bgcolor != blu.layout.plot_bgcolor
    assert blu.layout.plot_bgcolor == tema.BLU.erba_scura
    assert tema.BLU.erba_chiara in {f.fillcolor for f in forme(blu) if f.fillcolor}
    assert tema.VERDE.erba_chiara not in {f.fillcolor for f in forme(blu) if f.fillcolor}


def test_la_figura_nasce_senza_dati(figura: Any) -> None:
    # `campo` e' una base: chi la usa aggiunge le proprie tracce. Se
    # contenesse gia' qualcosa, ogni vista dovrebbe sapere cosa toglierne.
    assert len(figura.data) == 0
    assert len(forme(figura)) > 10


def test_l_erba_copre_tutto_il_campo() -> None:
    strisce = viz.erba(tema.VERDE)

    assert min(float(s["x0"]) for s in strisce) == pytest.approx(0.0)
    assert max(float(s["x1"]) for s in strisce) == pytest.approx(viz.LUNGHEZZA)
    assert all(float(s["y1"]) == pytest.approx(viz.LARGHEZZA) for s in strisce)


def test_le_strisce_si_alternano() -> None:
    strisce = viz.erba(tema.VERDE)
    colori = [s["fillcolor"] for s in strisce]

    assert len(set(colori)) == 2
    assert all(colori[i] != colori[i + 1] for i in range(len(colori) - 1))
