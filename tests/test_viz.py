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

import numpy as np
import pandas as pd
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


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_i_grafici_non_disegnano_il_proprio_fondo(scelto: tema.Tema) -> None:
    """Il fondo delle figure e' trasparente, non del colore della scheda.

    Prima ``paper_bgcolor`` valeva ``tema.superficie``, che e' lo stesso colore
    della scheda che contiene il grafico: sulla carta identico, in pagina no.
    Il rettangolo di Plotly ha angoli vivi dentro una scheda con angoli
    arrotondati, e non arriva mai fino al bordo — si vedeva un riquadro bianco
    stampato sopra la scheda bianca, visibile proprio agli angoli.

    Trasparente non e' equivalente: e' l'unico valore che continua a funzionare
    se un giorno la scheda cambia fondo, o ne ha uno sfumato.
    """
    for figura in (
        viz.campo(scelto),
        viz.ciambella(0.42, "42%", "xG realizzato", scelto),
    ):
        assert figura.layout.paper_bgcolor == tema.TRASPARENTE


def test_il_campo_e_lo_stesso_in_ogni_competizione() -> None:
    """Regola cambiata, e il test cambia con lei invece di sparire.

    In M6-T1 il campo prendeva i colori del tema: verde nei campionati, blu
    nelle finali. Era vistoso e sbagliato — la stessa mappa di calore su erba
    scura si legge piu' intensa che su erba chiara, quindi il confronto fra
    due competizioni diventava un confronto fra due fondi. Ora il campo e' uno
    strumento di misura e non cambia unita' con l'occasione.

    L'identita' della competizione resta dove non falsa niente: i colori dei
    tiri, che questo test verifica restino diversi.
    """
    verde = viz.campo(tema.per_gruppo("campionato"))
    blu = viz.campo(tema.per_gruppo("finali"))

    assert verde.layout.plot_bgcolor == blu.layout.plot_bgcolor == tema.ERBA_SCURA
    riempimenti = {f.fillcolor for f in forme(blu) if f.fillcolor}
    assert tema.ERBA_CHIARA in riempimenti
    # Cio' che distingue le finali sono le tracce, non il prato.
    assert {voce[2] for voce in tema.SCALA_XG_NOTTE} != {voce[2] for voce in tema.SCALA_XG}


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


# ---------------------------------------------------------------------------
# La shot map (M6-T3)
# ---------------------------------------------------------------------------


def tiri_di_prova() -> pd.DataFrame:
    """Sei tiri, due dei quali gol, con xG noti.

    Returns:
        Una tabella nella forma di ``shots.parquet``.
    """
    return pd.DataFrame(
        {
            "x": [110.0, 100.0, 95.0, 112.0, 105.0, 90.0],
            "y": [40.0, 30.0, 50.0, 44.0, 36.0, 40.0],
            "gol": [True, False, False, True, False, False],
            "xg_statsbomb": [0.40, 0.10, 0.05, 0.60, 0.08, 0.02],
            "giocatore": ["A", "B", "C", "D", "E", "F"],
            "squadra": ["Uno"] * 6,
            "minuto": [10, 20, 30, 40, 50, 60],
        }
    )


def test_la_shot_map_divide_i_tiri_in_fasce_di_xg() -> None:
    """Cinque classi invece di una scala continua.

    Su migliaia di pallini piccoli e sovrapposti un gradiente non si legge:
    nessuno distingue 0,18 da 0,24 guardando una sfumatura. Cinque classi si
    leggono dalla legenda e si contano.
    """
    mappa = viz.shot_map(tiri_di_prova(), tema.VERDE)

    nomi = [traccia.name for traccia in mappa.data]
    attese = [voce[0] for voce in tema.scala_di(tema.VERDE)]

    assert set(nomi) <= set(attese)
    assert len(nomi) >= 2


def test_le_fasce_sono_in_ordine_di_pericolosita() -> None:
    # La legenda deve leggersi dal meno al piu' pericoloso: al contrario
    # sarebbe corretta e faticosa.
    mappa = viz.shot_map(tiri_di_prova(), tema.VERDE)
    ordine = [voce[0] for voce in tema.scala_di(tema.VERDE)]
    disegnate = [t.name for t in mappa.data]

    assert disegnate == sorted(disegnate, key=ordine.index)


def test_ogni_tiro_finisce_in_una_fascia_e_una_sola() -> None:
    # Se i confini si sovrapponessero o lasciassero un buco, qualche tiro
    # sparirebbe dalla mappa senza che niente lo segnali.
    tiri = tiri_di_prova()

    mappa = viz.shot_map(tiri, tema.VERDE)

    disegnati = sum(len(traccia.x) for traccia in mappa.data)
    assert disegnati == len(tiri)


def test_i_gol_hanno_un_contorno_e_non_un_colore_diverso() -> None:
    """Distinguere l'esito col colore toglierebbe la lettura dell'xG.

    E succederebbe proprio sui tiri piu' interessanti: i gol sono quasi tutti
    ad alto xG, cioe' i pallini che uno guarda per primi.
    """
    tiri = tiri_di_prova()

    mappa = viz.shot_map(tiri, tema.VERDE)

    spessori = [larghezza for traccia in mappa.data for larghezza in traccia.marker.line.width]
    assert sum(1 for s in spessori if s > 0) == int(tiri["gol"].sum())


def test_le_fasce_basse_sono_piu_trasparenti() -> None:
    """L'opacita' e' cio' che decide se la mappa si legge.

    I tiri da niente sono meta' del totale: a piena opacita' formano una massa
    che copre le occasioni vere, cioe' proprio quello che si vuole guardare.
    E' stato il primo difetto visibile della mappa, e non era il colore.
    """
    trasparenze = [voce[3] for voce in tema.scala_di(tema.VERDE)]

    assert trasparenze == sorted(trasparenze)
    assert trasparenze[0] < 0.4
    assert trasparenze[-1] > 0.9


def test_l_opacita_arriva_fino_al_disegno() -> None:
    mappa = viz.shot_map(tiri_di_prova(), tema.VERDE)
    per_fascia = {voce[0]: voce[3] for voce in tema.scala_di(tema.VERDE)}

    for traccia in mappa.data:
        assert traccia.marker.opacity == pytest.approx(per_fascia[traccia.name])


def test_la_legenda_e_accesa() -> None:
    # Senza legenda le fasce di colore sono decorazione.
    assert viz.shot_map(tiri_di_prova(), tema.VERDE).layout.showlegend is True


def test_la_dimensione_cresce_con_la_radice_dell_xg() -> None:
    """L'occhio confronta le aree, non i raggi.

    Con il raggio proporzionale all'xG, un tiro da 0,40 sembrerebbe quattro
    volte uno da 0,10 in **larghezza** e sedici volte in **area**. E' il modo
    piu' comune di esagerare un grafico senza volerlo.
    """
    raggi = viz._dimensioni([0.10, 0.40])
    escursione = viz.PALLINO_MASSIMO - viz.PALLINO_MINIMO

    quota_piccolo = (raggi[0] - viz.PALLINO_MINIMO) / escursione
    quota_grande = (raggi[1] - viz.PALLINO_MINIMO) / escursione

    assert quota_grande == pytest.approx(1.0)
    assert quota_piccolo == pytest.approx(0.5)


def test_un_xg_nullo_non_produce_un_pallino_invisibile() -> None:
    raggi = viz._dimensioni([0.0, 0.5])

    assert min(raggi) >= viz.PALLINO_MINIMO


def test_tutti_gli_xg_a_zero_non_dividono_per_zero() -> None:
    raggi = viz._dimensioni([0.0, 0.0, 0.0])

    assert all(r == pytest.approx(viz.PALLINO_MINIMO) for r in raggi)


def test_senza_tiri_resta_solo_il_campo() -> None:
    vuota = viz.shot_map(tiri_di_prova().iloc[0:0], tema.VERDE)

    assert len(vuota.data) == 0
    assert len(forme(vuota)) > 10


def test_la_shot_map_disegna_sul_campo_del_tema_scelto() -> None:
    blu = viz.shot_map(tiri_di_prova(), tema.BLU)
    colori_notte = {voce[2] for voce in tema.SCALA_XG_NOTTE}

    assert blu.layout.plot_bgcolor == tema.ERBA_SCURA
    assert {t.marker.color for t in blu.data} <= colori_notte


def test_le_strisce_si_alternano() -> None:
    strisce = viz.erba(tema.VERDE)
    colori = [s["fillcolor"] for s in strisce]

    assert len(set(colori)) == 2
    assert all(colori[i] != colori[i + 1] for i in range(len(colori) - 1))


def test_la_mappa_non_mostra_nomi_al_passaggio() -> None:
    """Nessun nome di giocatore compare passando il mouse sulla mappa.

    In area i tiri sono decine, sovrapposti a pochi pixel l'uno dall'altro: il
    puntatore pesca quello che sta sopra nell'ordine di disegno, che non e'
    quello che si sta guardando. Il riquadro mostrava quindi un nome
    plausibile e quasi sempre sbagliato — peggio di nessun nome, perche' sembra
    un'informazione.

    Il test guarda ``customdata`` e non il solo ``hoverinfo``: e' il dato a
    dover mancare, altrimenti i nomi viaggiano comunque nell'HTML della pagina
    e basta una riga altrove per rimetterli in vista.
    """
    figura = viz.shot_map(tiri_di_prova(), tema.VERDE)

    for traccia in figura.data:
        assert traccia.customdata is None
        assert traccia.hovertemplate is None


# ---------------------------------------------------------------------------
# La mappa di calore
# ---------------------------------------------------------------------------


def test_la_mappa_di_calore_conserva_tutti_i_tiri() -> None:
    """Nessun tiro si perde e nessuno viene contato due volte.

    Il controllo e' sulla griglia **prima** della sfocatura: quella disegnata
    non conserva la somma, perche' ai bordi la finestra della media sporge dal
    campo. Se i bordi delle celle fossero sfasati di mezza iarda, o l'ultimo
    escludesse i tiri sulla linea di fondo, il totale non tornerebbe e la mappa
    mostrerebbe una densita' sbagliata senza sembrare rotta.
    """
    tiri = tiri_di_prova()

    conteggi, _, _ = viz.griglia_dei_tiri(tiri)

    assert round(float(conteggi.sum())) == len(tiri)


def test_la_barra_dei_colori_mostra_i_conteggi_non_le_radici() -> None:
    """La trasformazione serve all'occhio, non deve arrivare all'etichetta.

    E' la parte in cui una scala non lineare diventa disonesta: se la barra
    riportasse le radici, un lettore che confronta due zone leggerebbe numeri
    che non sono tiri.
    """
    tiri = tiri_di_prova()
    figura = viz.mappa_di_calore(tiri, tema.VERDE)
    barra = figura.data[0].colorbar

    massimo = float(viz.griglia_dei_tiri(tiri)[0].max())

    assert float(barra.ticktext[-1]) == pytest.approx(massimo, abs=0.5)
    assert float(barra.tickvals[-1]) == pytest.approx(massimo**0.5, rel=1e-6)


def test_la_radice_salva_le_celle_rare() -> None:
    """La ragione per cui la scala non e' lineare, misurata invece che asserita.

    I due numeri non sono inventati: sono la forma vera della distribuzione de
    La Liga con celle da quattro iarde — cella piu' battuta 385 tiri, mediana
    delle celle piene 8. La prima stesura di questo test usava 400 e 3 scelti a
    occhio, e falliva: con quel rapporto nemmeno la radice basta. Serviva
    guardare i dati invece di immaginarli.
    """
    conteggi = np.array([385.0, *([8.0] * 40)])

    lineare = conteggi / conteggi.max()
    radice = np.sqrt(conteggi) / np.sqrt(conteggi.max())

    assert (lineare[1:] < 0.10).all(), "la scala lineare dovrebbe spegnere la coda"
    assert (radice[1:] > 0.10).all(), "la radice dovrebbe salvarla"


def test_le_linee_del_campo_stanno_sopra_la_mappa_di_calore() -> None:
    """Una superficie opaca sopra l'area di rigore nasconde l'area di rigore.

    Le linee sono l'unico riferimento per capire dove si stia guardando: sotto
    una mappa di calore devono passare sopra, mentre nella nuvola di punti
    restano sotto perche' li' coprirebbero i tiri.
    """
    calore = viz.mappa_di_calore(tiri_di_prova(), tema.VERDE)
    punti = viz.shot_map(tiri_di_prova(), tema.VERDE)

    def livelli(figura: Any) -> set[str]:
        return {f.layer for f in forme(figura) if f.line and f.line.color == tema.VERDE.linee}

    assert livelli(calore) == {"above"}
    assert livelli(punti) == {"below"}


def test_la_mappa_di_calore_vuota_resta_un_campo() -> None:
    vuota = viz.mappa_di_calore(tiri_di_prova().head(0), tema.VERDE)

    assert len(vuota.data) == 0
    assert len(forme(vuota)) > 0


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_la_scala_di_calore_parte_invisibile(scelto: tema.Tema) -> None:
    """Il primo gradino e' trasparente, o il campo sparisce sotto una patina.

    Deve anche essere la **stessa tinta** del gradino successivo: partendo da
    un nero trasparente, Plotly interpolerebbe verso il grigio e le zone quasi
    vuote prenderebbero una sfumatura sporca che non significa niente.
    """
    scala = tema.scala_calore(scelto)
    primo, secondo = scala[0][1], scala[1][1]

    assert primo.startswith("rgba(") and primo.endswith(",0)")
    canali = primo[len("rgba(") : -len(",0)")]
    atteso = ",".join(str(int(secondo[i : i + 2], 16)) for i in (1, 3, 5))
    assert canali == atteso


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_le_posizioni_della_scala_sono_ordinate(scelto: tema.Tema) -> None:
    posizioni = [posizione for posizione, _ in tema.scala_calore(scelto)]

    assert posizioni == sorted(posizioni)
    assert posizioni[0] == 0.0
    assert posizioni[-1] == 1.0


# ---------------------------------------------------------------------------
# La rete dei passaggi e la mappa per esito
# ---------------------------------------------------------------------------


def rete_di_prova() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Tre giocatori e due legami, con posizioni scelte a mano.

    Returns:
        Nodi, archi e coinvolgimenti.
    """
    nodi = pd.DataFrame(
        {
            "giocatore_id": [1, 2, 3],
            "giocatore_breve": ["Uno", "Due", "Tre"],
            "ruolo": ["Goalkeeper", "Center Back", "Striker"],
            "minuti": [900, 800, 700],
            "x_media": [10.0, 45.0, 90.0],
            "y_media": [40.0, 30.0, 45.0],
        }
    )
    archi = pd.DataFrame(
        {
            "x0": [10.0, 45.0],
            "y0": [40.0, 30.0],
            "x1": [45.0, 90.0],
            "y1": [30.0, 45.0],
            "da": ["Uno", "Due"],
            "a": ["Due", "Tre"],
            "passaggi": [100, 40],
        }
    )
    conteggi = pd.Series([100.0, 140.0, 40.0], index=nodi["giocatore_breve"])
    return nodi, archi, conteggi


def test_la_rete_disegna_un_arco_per_legame() -> None:
    """Gli archi sono forme, i giocatori una traccia sola.

    Plotly non sa variare lo spessore dentro una traccia: venti legami di
    spessore diverso vorrebbero dire venti tracce, e venti voci di legenda da
    nascondere una per una.
    """
    nodi, archi, conteggi = rete_di_prova()
    campo_solo = viz.campo(tema.VERDE, meta_campo=False)

    figura = viz.rete_passaggi(nodi, archi, conteggi, tema.VERDE)

    assert len(figura.data) == 1
    assert len(forme(figura)) == len(forme(campo_solo)) + len(archi)


def test_il_legame_piu_battuto_e_il_piu_spesso() -> None:
    nodi, archi, conteggi = rete_di_prova()

    figura = viz.rete_passaggi(nodi, archi, conteggi, tema.VERDE)

    aggiunte = forme(figura)[-len(archi) :]
    spessori = [f.line.width for f in aggiunte]
    assert spessori[0] > spessori[1]
    assert max(spessori) <= viz.SPESSORE_MASSIMO


def test_i_giocatori_portano_il_nome_e_non_un_numero() -> None:
    """I numeri di maglia non esistono in ``player_stats``.

    Inventarli per far somigliare la rete a una formazione sarebbe l'unica
    cosa falsa della vista.
    """
    nodi, archi, conteggi = rete_di_prova()

    figura = viz.rete_passaggi(nodi, archi, conteggi, tema.VERDE)

    assert list(figura.data[0].text) == ["Uno", "Due", "Tre"]


def test_la_rete_senza_giocatori_resta_un_campo() -> None:
    nodi, archi, conteggi = rete_di_prova()

    vuota = viz.rete_passaggi(nodi.head(0), archi, conteggi, tema.VERDE)

    assert len(vuota.data) == 0
    assert len(forme(vuota)) > 0


def test_la_mappa_per_esito_separa_gol_e_tiri() -> None:
    tiri = tiri_di_prova()

    figura = viz.per_esito(tiri, tema.VERDE)

    per_nome = {traccia.name: traccia for traccia in figura.data}
    assert set(per_nome) == {"tiro", "gol"}
    assert len(per_nome["gol"].x) == int(tiri["gol"].astype(bool).sum())
    assert len(per_nome["tiro"].x) == len(tiri) - len(per_nome["gol"].x)


def test_la_mappa_per_esito_non_mostra_nomi() -> None:
    figura = viz.per_esito(tiri_di_prova(), tema.VERDE)

    for traccia in figura.data:
        assert traccia.customdata is None
        assert traccia.hovertemplate is None


def test_la_sfocatura_rende_la_mappa_piu_liscia() -> None:
    """La misura di cio' che la sfocatura deve ottenere.

    «Piu' liscia» non e' un'opinione: e' il salto medio fra celle vicine. Su
    una griglia a scacchiera — il caso peggiore — la media pesata sui vicini
    deve abbatterlo, o non sta facendo niente.
    """
    scacchiera = (np.indices((20, 20)).sum(axis=0) % 2 * 100.0).astype(np.float64)

    smussata = viz._sfoca(scacchiera)

    prima = np.abs(np.diff(scacchiera, axis=0)).mean()
    dopo = np.abs(np.diff(smussata, axis=0)).mean()
    assert dopo < prima / 10


def test_la_scala_resta_sui_conteggi_veri_dopo_la_sfocatura() -> None:
    """Smussare abbassa il picco: la barra deve continuare a dire il vero.

    Senza il riscalamento, la cella piu' battuta risulterebbe avere meno tiri
    di quanti ne ha — un numero sbagliato, non un'approssimazione grafica.
    """
    tiri = tiri_di_prova()
    figura = viz.mappa_di_calore(tiri, tema.VERDE)

    conteggi = np.square(np.asarray(figura.data[0].z))
    dichiarato = float(figura.data[0].colorbar.ticktext[-1])

    assert conteggi.max() == pytest.approx(dichiarato, rel=1e-6)


def test_dove_non_si_tira_il_campo_resta_scoperto() -> None:
    """Sotto la soglia la mappa non deve disegnare niente.

    Servono **due** gradini trasparenti, non uno: con uno solo Plotly comincia
    a far salire l'opacita' subito dopo lo zero e le zone quasi vuote prendono
    il velo biancastro che la soglia esiste per togliere.
    """
    tiri = tiri_di_prova()
    scala = viz.mappa_di_calore(tiri, tema.VERDE).data[0].colorscale

    assert scala[0][0] == 0.0
    assert scala[0][1].endswith(",0)")
    assert scala[1][1] == scala[0][1]
    assert scala[1][0] > 0.0


def test_la_soglia_e_in_tiri_non_in_posizione_sulla_scala() -> None:
    """La stessa posizione sulla scala vale conteggi diversi.

    E' il motivo per cui la soglia non puo' essere una costante fissa: con la
    radice, la posizione dipende dal massimo della mappa. Due insiemi con
    massimi diversi devono avere il plateau trasparente in punti diversi, ma
    entrambi corrispondenti a :data:`viz.SOGLIA_CALORE` tiri.
    """
    pochi = tiri_di_prova()
    molti = pd.concat([tiri_di_prova()] * 9, ignore_index=True)

    for tiri in (pochi, molti):
        massimo = float(viz.griglia_dei_tiri(tiri)[0].max())
        soglia = viz.mappa_di_calore(tiri, tema.VERDE).data[0].colorscale[1][0]

        assert soglia**2 * massimo == pytest.approx(viz.SOGLIA_CALORE, rel=1e-6)

    scarso = viz.mappa_di_calore(pochi, tema.VERDE).data[0].colorscale[1][0]
    abbondante = viz.mappa_di_calore(molti, tema.VERDE).data[0].colorscale[1][0]
    assert scarso > abbondante


def test_la_corsa_dell_xg_sale_a_gradini() -> None:
    """L'xG salta a ogni tiro e resta fermo in mezzo.

    Con la linea diagonale il grafico direbbe che fra il minuto 12 e il 34 la
    squadra ha creato qualcosa: e' una lettura sbagliata prodotta da una scelta
    di disegno, non dai dati.
    """
    a_gradini = viz.linee([0, 10, 30], {"Alfa": [0.0, 0.3, 0.8]}, tema.VERDE, a_gradini=True)
    normale = viz.linee([0, 10, 30], {"Alfa": [0.0, 0.3, 0.8]}, tema.VERDE)

    assert a_gradini.data[0].line.shape == "hv"
    assert normale.data[0].line.shape == "linear"


def test_il_radar_ha_la_scala_bloccata_da_zero_a_cento() -> None:
    """Un radar che ridimensiona gli assi fa sembrare fenomenale chiunque.

    Con la scala automatica il punto piu' alto tocca sempre il bordo, quindi
    ogni giocatore ha almeno un asse al massimo. Bloccata, la forma dice
    qualcosa: piccola vuol dire piccola.
    """
    figura = viz.radar({"Tiri/90": 90.0, "xG/90": 20.0, "Gol/90": 55.0}, tema.VERDE)

    assert figura.layout.polar.radialaxis.range == (0, 100)


def test_il_radar_disegna_la_mediana_e_chiude_il_poligono() -> None:
    """Due tracce: la mediana del reparto e il giocatore.

    Il primo punto va ripetuto in fondo, o il poligono resta aperto fra
    l'ultimo asse e il primo — e si vede.
    """
    assi = {"a": 10.0, "b": 80.0, "c": 40.0}

    figura = viz.radar(assi, tema.VERDE)

    mediana, giocatore = figura.data
    assert set(mediana.r) == {50.0}
    assert len(giocatore.r) == len(assi) + 1
    assert giocatore.r[0] == giocatore.r[-1]
    assert giocatore.theta[0] == giocatore.theta[-1]


def test_il_radar_senza_assi_non_esplode() -> None:
    assert len(viz.radar({}, tema.VERDE).data) == 0


def test_la_mappa_dei_tocchi_usa_il_campo_intero() -> None:
    """I tocchi di un terzino stanno nella sua meta'.

    Con mezzo campo se ne vedrebbe la meta', e il terzino sembrerebbe un
    attaccante che non tocca mai la palla.
    """
    tocchi = pd.DataFrame(
        [
            {"cella_x": 2, "cella_y": 3, "tocchi": 40},
            {"cella_x": 20, "cella_y": 8, "tocchi": 5},
        ]
    )

    figura = viz.mappa_tocchi(tocchi, tema.VERDE)

    assert figura.layout.xaxis.range == (0.0, viz.LUNGHEZZA)
    assert len(figura.data) == 1


def test_la_mappa_dei_tocchi_vuota_resta_un_campo() -> None:
    vuota = viz.mappa_tocchi(pd.DataFrame(columns=["cella_x", "cella_y", "tocchi"]), tema.VERDE)

    assert len(vuota.data) == 0
    assert len(forme(vuota)) > 10


def test_la_calibrazione_ha_la_bisettrice_e_gli_assi_agganciati() -> None:
    """Senza il quarantacinque gradi la distanza dalla retta inganna l'occhio.

    E' lo stesso difetto silenzioso di :func:`viz.attese_contro_realizzato`: un
    grafico con assi di scala diversa resta plausibile e dice il falso, perche'
    uno scarto di due punti percentuali sembra grande in basso e piccolo in
    alto.
    """
    curve = pd.DataFrame(
        [
            {
                "modello": "Base",
                "gruppo": indice,
                "tiri": 800,
                "xg_previsto": indice / 10,
                "gol_osservati": indice / 10,
                "errore_standard": 0.01,
                "scarto": 0.0,
                "scarto_in_se": 0.0,
            }
            for indice in range(5)
        ]
    )

    figura = viz.calibrazione(curve, {"Base": "#123456"}, tema.VERDE)

    assert figura.layout.yaxis.scaleanchor == "x"
    assert figura.layout.yaxis.scaleratio == 1
    assert [forma for forma in forme(figura) if forma["type"] == "line"], "manca la bisettrice"
    assert figura.data[0].error_y.array is not None, "le barre d'errore sono il senso del grafico"


def test_la_calibrazione_senza_punti_non_esplode() -> None:
    vuota = viz.calibrazione(pd.DataFrame(), {}, tema.VERDE)

    assert len(vuota.data) == 0


def test_le_barre_divergenti_sono_simmetriche_attorno_allo_zero() -> None:
    """Dimezzare e raddoppiare devono dare barre lunghe uguali.

    Chi chiama passa i pesi gia' in logaritmo, quindi il compito del grafico e'
    non rovinarli: l'intervallo deve essere centrato sullo zero, o meta' delle
    barre risulterebbe schiacciata contro il bordo.
    """
    figura = viz.barre_divergenti(
        ["dimezza", "raddoppia"], [-1.0, 1.0], ["#111", "#222"], ["×0,50", "×2,00"], tema.VERDE
    )

    sinistra, destra = figura.layout.xaxis.range
    assert sinistra == pytest.approx(-destra)
    assert figura.layout.yaxis.autorange == "reversed", "la prima barra deve stare in cima"
    assert list(figura.data[0].text) == ["×0,50", "×2,00"]


def test_le_barre_divergenti_senza_dati_non_esplodono() -> None:
    assert len(viz.barre_divergenti([], [], [], [], tema.VERDE).data) == 0
