"""Verifiche del tema della dashboard (M6-T1).

Il criterio del backlog e' che **un test verifichi che `viz.py` non contenga
colori letterali**. Qui la verifica e' piu' larga: cerca in **tutto il
pacchetto** tranne `tema.py`, perche' la regola non riguarda un file ma
un'architettura — i colori stanno in un posto solo, e chiunque ne scriva uno
altrove rompe la build invece di scoprirlo fra sei mesi.
"""

from __future__ import annotations

import math
import re
from itertools import pairwise
from pathlib import Path

import pytest

from football_analytics import config, tema
from football_analytics.config import Gruppo

#: Il sorgente del pacchetto, che il test legge come testo.
PACCHETTO: Path = Path(tema.__file__).parent

#: Le forme in cui un colore puo' nascondersi in un sorgente Python.
#:
#: Il ``\b`` davanti a ``rgb`` e ``hsl`` non e' decorativo: senza, la regex
#: trovava ``hsl(`` dentro il **nome** della funzione ``_da_hsl(`` e segnalava
#: un colore letterale che non esisteva. Un test troppo largo e' inutile quanto
#: uno troppo stretto — smette di indicare il difetto e comincia a indicare se
#: stesso.
COLORI_LETTERALI: re.Pattern[str] = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\(",
)

#: I nomi di colore CSS che capita di scrivere per distrazione.
NOMI_COLORE: frozenset[str] = frozenset(
    {"white", "black", "green", "blue", "red", "yellow", "grey", "gray", "orange"}
)


def moduli() -> list[Path]:
    """Elenca i moduli del pacchetto in cui i colori sono vietati.

    Returns:
        Tutti i ``.py`` del pacchetto tranne ``tema.py``, che e' il posto dove
        i colori devono stare.
    """
    return sorted(p for p in PACCHETTO.glob("*.py") if p.name != "tema.py")


# ---------------------------------------------------------------------------
# Il criterio del backlog
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("modulo", moduli(), ids=lambda p: p.name)
def test_nessun_colore_letterale_fuori_da_tema(modulo: Path) -> None:
    """Nessun modulo del pacchetto contiene un colore scritto a mano.

    Un colore dentro un grafico e' invisibile finche' non serve cambiarlo, e
    sopravvive al cambio di tema: la vista resterebbe verde anche quando tutto
    il resto e' diventato blu.
    """
    sorgente = modulo.read_text(encoding="utf-8")

    trovati = COLORI_LETTERALI.findall(sorgente)

    assert not trovati, f"{modulo.name} contiene colori letterali: {trovati}"


@pytest.mark.parametrize("modulo", moduli(), ids=lambda p: p.name)
def test_nessun_nome_di_colore_css_fuori_da_tema(modulo: Path) -> None:
    parole = set(re.findall(r"[a-z]+", modulo.read_text(encoding="utf-8").lower()))

    sospette = parole & NOMI_COLORE

    assert not sospette, f"{modulo.name} usa nomi di colore: {sorted(sospette)}"


def test_il_test_saprebbe_riconoscere_un_colore() -> None:
    # Un test che cerca qualcosa deve dimostrare di saperlo trovare, o non
    # distingue «nessun colore» da «espressione regolare sbagliata».
    assert COLORI_LETTERALI.search('colore = "#1b7f4f"')
    assert COLORI_LETTERALI.search("colore = 'rgb(27, 127, 79)'")
    assert COLORI_LETTERALI.search('sfondo = "rgba(0,0,0,.5)"')
    assert COLORI_LETTERALI.search('bordo = "hsl(140, 55%, 28%)"')
    assert not COLORI_LETTERALI.search("distanza = 120.0")
    # I falsi positivi contano quanto i mancati: `_da_hsl(` e' un nome di
    # funzione, non un colore, e la prima stesura lo segnalava.
    assert not COLORI_LETTERALI.search("return _da_hsl(tonalita)")
    assert not COLORI_LETTERALI.search("def converti_in_srgb(valore):")


# ---------------------------------------------------------------------------
# La scelta del tema
# ---------------------------------------------------------------------------


def test_le_finali_sono_blu() -> None:
    assert tema.per_gruppo(Gruppo.FINALI) is tema.BLU
    assert tema.per_gruppo("finali") is tema.BLU


def test_campionati_e_tornei_sono_verdi() -> None:
    assert tema.per_gruppo(Gruppo.CAMPIONATO) is tema.VERDE
    assert tema.per_gruppo(Gruppo.TORNEO) is tema.VERDE


def test_un_gruppo_sconosciuto_non_rompe_la_dashboard() -> None:
    # Meglio una vista verde che una pagina bianca: se domani nasce un gruppo
    # nuovo, l'app deve continuare a disegnare.
    assert tema.per_gruppo("gruppo_inventato") is tema.VERDE


# ---------------------------------------------------------------------------
# Le palette
# ---------------------------------------------------------------------------


def colori_di(scelto: tema.Tema) -> list[tuple[str, str]]:
    """Tutti i colori di un tema, coppia per coppia, tuple appiattite.

    ``striscia`` e' l'unico campo che non e' una stringa. Appiattirlo qui
    invece di saltarlo tiene i suoi colori dentro i controlli su formato e
    validita': un tricolore con un ``#gggggg`` dentro passerebbe inosservato
    fino al momento in cui il browser lo ignora silenziosamente.

    Args:
        scelto: La palette da scorrere.

    Returns:
        Coppie nome-del-campo e colore, esclusi i campi che non sono colori.
    """
    trovati: list[tuple[str, str]] = []
    for campo in scelto.__slots__:
        if campo == "nome":
            continue
        valore = getattr(scelto, campo)
        if isinstance(valore, str):
            trovati.append((campo, valore))
        else:
            trovati.extend((f"{campo}[{i}]", c) for i, c in enumerate(valore))
    return trovati


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_ogni_tema_definisce_tutti_i_ruoli(scelto: tema.Tema) -> None:
    # Se un tema dimenticasse un campo, la vista che lo usa fallirebbe solo
    # quando qualcuno la apre con quel tema attivo.
    for campo in scelto.__slots__:
        valore = getattr(scelto, campo)
        assert valore
    assert len(scelto.striscia) >= 2, "una fascia di un colore solo non e' una fascia"


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_i_colori_sono_esadecimali_validi(scelto: tema.Tema) -> None:
    for campo, valore in colori_di(scelto):
        assert re.fullmatch(r"#[0-9a-f]{6}", valore), f"{campo} = {valore}"


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_il_testo_si_legge_sullo_sfondo(scelto: tema.Tema) -> None:
    """Il contrasto fra testo e sfondo rispetta lo standard WCAG AA.

    Non e' un dettaglio estetico: sotto 4,5 a 1 il testo diventa faticoso da
    leggere per chiunque e illeggibile per qualcuno. La soglia e' quella
    ufficiale per il testo normale.
    """
    assert contrasto(scelto.testo, scelto.sfondo) >= 4.5
    assert contrasto(scelto.testo, scelto.superficie) >= 4.5
    assert contrasto(scelto.testo_tenue, scelto.sfondo) >= 3.0


def test_il_tema_statico_di_streamlit_non_diverge_da_quello_dinamico() -> None:
    """L'unica duplicazione di colori del progetto resta allineata.

    ``.streamlit/config.toml`` deve ripetere i colori del tema verde, perche'
    Streamlit lo legge prima che Python parta e non puo' importare niente. Un
    commento non impedisce che i due si separino; questo test si'.

    Se divergessero, l'app mostrerebbe per una frazione di secondo i colori
    vecchi a ogni caricamento — il tipo di difetto che nessuno segnala e tutti
    notano.
    """
    percorso = PACCHETTO.parents[1] / ".streamlit" / "config.toml"
    # Il confronto ignora le maiuscole: in un file TOML `#0F6E56` e `#0f6e56`
    # sono lo stesso colore, e far fallire un test su quello sarebbe rumore.
    configurazione = percorso.read_text(encoding="utf-8").lower()

    for campo in ("primario", "sfondo", "superficie", "bordo", "testo", "barra", "barra_testo"):
        colore = str(getattr(tema.VERDE, campo)).lower()
        assert colore in configurazione, f"config.toml non contiene {campo} = {colore}"


def luminanza(colore: str) -> float:
    """Calcola la luminanza relativa di un colore esadecimale.

    Args:
        colore: Il colore in forma ``#rrggbb``.

    Returns:
        La luminanza secondo la formula WCAG, fra 0 e 1.
    """
    canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def contrasto(primo: str, secondo: str) -> float:
    """Rapporto di contrasto fra due colori, secondo WCAG.

    Args:
        primo: Il primo colore, in forma ``#rrggbb``.
        secondo: Il secondo colore.

    Returns:
        Il rapporto, fra 1 (identici) e 21 (nero su bianco).
    """
    a, b = sorted((luminanza(primo), luminanza(secondo)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# ---------------------------------------------------------------------------
# Un tema per competizione
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("chiave", "atteso"),
    [
        ("premier_2015_16", "premier"),
        ("la_liga_2015_16", "liga"),
        ("serie_a_2015_16", "serie_a"),
        ("ligue1_2015_16", "ligue1"),
        ("champions_finali", "blu"),
    ],
)
def test_ogni_campionato_ha_il_proprio_tema(chiave: str, atteso: str) -> None:
    assert tema.per_competizione(chiave).nome == atteso


@pytest.mark.parametrize(
    ("chiave", "atteso"),
    [
        ("mondiali_2022", "mondiali"),
        ("coppa_africa_2023", "coppa_africa"),
        ("euro_2020", "europei"),
        ("euro_2024", "europei"),
    ],
)
def test_anche_i_tornei_hanno_il_proprio_tema(chiave: str, atteso: str) -> None:
    """Ogni competizione ha il suo colore, tornei compresi.

    All'inizio i tornei restavano sul tema neutro, con la motivazione che un
    Mondiale non ha un'identita' visiva stabile come una lega. La motivazione
    non regge dal lato di chi guarda: nella pagina Squadre le nove competizioni
    stanno una accanto all'altra, e sei riquadri identici non aiutano a
    distinguerle.

    **I due Europei condividono il tema perche' condividono l'identificativo**
    — ``competition_id`` 55 — ed e' giusto: sono la stessa competizione in due
    edizioni, e due colori suggerirebbero due tornei distinti.

    Il neutro resta solo per la selezione senza competizione, dove vuol dire
    «nessuna in particolare».
    """
    assert tema.per_competizione(chiave).nome == atteso


def test_una_competizione_sconosciuta_non_rompe_la_dashboard() -> None:
    """La chiave sbagliata non solleva, a differenza di ``config.competizione``.

    Il comportamento diverso e' voluto: in una pipeline un nome sbagliato deve
    fermare tutto, in una dashboard deve solo togliere il colore. Il test
    verifica prima che la funzione severa sia davvero severa, altrimenti
    starebbe misurando due volte la stessa indulgenza.
    """
    with pytest.raises(ValueError, match="sconosciuta"):
        config.competizione("liga_inventata")

    assert tema.per_competizione("liga_inventata") is tema.VERDE
    assert tema.per_competizione(None) is tema.VERDE
    assert tema.per_competizione("") is tema.VERDE


def test_solo_il_neutro_e_chiaro() -> None:
    """Il fondo scuro dice «stai guardando una competizione precisa».

    Il neutro e' lo stato in cui non si sta guardando niente in particolare, e
    non ha senso che indossi i colori di qualcuno: resta bianco. Tutte le
    competizioni sono scure e portano la propria bandiera.

    **Il buio non e' piu' il segnale delle finali**, che era il suo primo
    significato: diceva «qui il modello viene applicato invece che
    addestrato». Quel significato e' stato speso per l'identita' visiva, e a
    M6-T10 va sostituito da una dichiarazione scritta nella vista — da un
    colore nessuno puo' dedurre che quei diciotto match sono fuori campione.
    """
    chiari = [t.nome for t in tema.TEMI.values() if not tema.e_scuro(t)]

    assert chiari == ["verde"]


def test_i_temi_non_si_somigliano() -> None:
    """Due leghe non possono avere lo stesso accento.

    Senza questo, aggiungere un campionato copiando il tema accanto e
    dimenticando di cambiarne il colore darebbe una pagina che sembra
    funzionare e non distingue piu' niente.
    """
    accenti = [t.primario for t in tema.TEMI.values()]

    assert len(set(accenti)) == len(accenti)


def distanza_percettiva(primo: str, secondo: str) -> float:
    """La distanza fra due colori in CIELAB, cioe' quanto si vede la differenza.

    La distanza euclidea in RGB non serve: due colori a pari distanza in RGB
    possono essere indistinguibili o ovvi a seconda di dove si trovano. CIELAB
    e' costruito perche' distanze uguali si vedano uguali, ed e' l'unico modo
    di dire «questo salto e' il doppio di quello» senza inventare.

    Args:
        primo: Un colore esadecimale.
        secondo: L'altro.

    Returns:
        La distanza ΔE fra i due.
    """

    def a_lab(colore: str) -> tuple[float, float, float]:
        canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        rosso, verde, blu = (
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in canali
        )
        x = (0.4124 * rosso + 0.3576 * verde + 0.1805 * blu) / 0.95047
        y = 0.2126 * rosso + 0.7152 * verde + 0.0722 * blu
        z = (0.0193 * rosso + 0.1192 * verde + 0.9505 * blu) / 1.08883

        def piega(t: float) -> float:
            return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

        fx, fy, fz = piega(x), piega(y), piega(z)
        return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

    quadrati = sum((p - q) ** 2 for p, q in zip(a_lab(primo), a_lab(secondo), strict=True))
    return math.sqrt(quadrati)


def test_la_scala_di_calore_non_risale_mai_di_luminosita() -> None:
    """Il difetto per cui la scala «jet» e' sconsigliata da trent'anni.

    Una scala arcobaleno che risale di luminosita' disegna un bordo netto
    dove il dato e' liscio: l'occhio legge il salto di chiarezza come un
    confine e vede una zona che non esiste. Con la luminanza che scende a ogni
    gradino il problema non si pone, e in piu' la mappa resta leggibile in
    scala di grigi.

    Il test copre solo la scala condivisa dai temi chiari: quella delle finali
    e' costruita dal tema e ha tre gradini, dove il rischio non si pone.
    """
    chiarezze = [luminanza(colore) for _, colore in tema.SCALA_CALORE[1:]]

    discese = [prima > dopo for prima, dopo in pairwise(chiarezze)]
    assert all(discese), [f"{v:.2f}" for v in chiarezze]


def test_i_gradini_della_scala_sono_percettivamente_regolari() -> None:
    """Nessun salto di colore molto piu' largo degli altri.

    E' la ragione per cui la scala non finisce in blu o viola, che pure
    sarebbero stati piu' belli: dal rosso al viola il salto misura ΔE 79-87
    contro i 34-45 di ogni altro passo, e si vedrebbe come un anello attorno
    al punto piu' caldo. La soglia di 2 sul rapporto e' larga di proposito —
    serve a fermare un salto doppio, non a inseguire l'uniformita' perfetta.
    """
    colori = [colore for _, colore in tema.SCALA_CALORE[1:]]
    passi = [distanza_percettiva(prima, dopo) for prima, dopo in pairwise(colori)]

    assert max(passi) / min(passi) < 2.0, [f"{p:.0f}" for p in passi]


def test_il_menu_automatico_e_spento_dalla_configurazione() -> None:
    """Il menu delle pagine di Streamlit non deve mai comparire, nemmeno per un attimo.

    Nasconderlo con il CSS non basta: la regola viaggia con lo script, e fra il
    disegno della pagina e l'esecuzione del codice c'e' un istante in cui la
    barra nativa e' gia' visibile. A ogni cambio pagina si vedeva comparire e
    sparire un secondo menu con i nomi dei file — «Panoramica, Scheda,
    Squadre». ``config.toml`` Streamlit lo legge prima di disegnare qualunque
    cosa, quindi li' la barra non nasce proprio.

    Il test guarda il file di configurazione e non il CSS, perche' e' il file
    che risolve il difetto; la regola CSS resta come rete di sicurezza.
    """
    percorso = PACCHETTO.parents[1] / ".streamlit" / "config.toml"
    configurazione = percorso.read_text(encoding="utf-8")

    assert "[client]" in configurazione
    assert "showSidebarNavigation = false" in configurazione


def test_ogni_competizione_del_magazzino_ha_un_tema_distinto() -> None:
    """Nove competizioni, nove identita' riconoscibili.

    Nella pagina Squadre i riquadri stanno tutti nella stessa schermata: due
    competizioni con lo stesso accento sarebbero indistinguibili proprio dove
    il colore serve. L'unica coppia che condivide il tema sono i due Europei,
    che sono la stessa competizione.
    """
    accenti: dict[str, list[str]] = {}
    for voce in config.COMPETIZIONI:
        accenti.setdefault(tema.per_competizione(voce.chiave).primario, []).append(voce.chiave)

    doppioni = {colore: chiavi for colore, chiavi in accenti.items() if len(chiavi) > 1}

    assert list(doppioni.values()) == [["euro_2024", "euro_2020"]], doppioni


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_l_accento_si_vede_sulla_propria_superficie(scelto: tema.Tema) -> None:
    """L'accento regge la soglia WCAG per gli elementi grafici.

    Tre a uno e' la soglia per cio' che non e' testo — bordi, barre, pallini —
    ed e' il ruolo dell'accento: se scendesse sotto, i riquadri della pagina
    Squadre avrebbero un colore che non si distingue dal fondo.
    """
    assert contrasto(scelto.primario, scelto.superficie) >= 3.0
    assert contrasto(scelto.primario, scelto.sfondo) >= 3.0


def test_il_fondo_di_ogni_tema_e_la_sua_bandiera() -> None:
    """Il fondo nasce dai colori d'identita', non da una seconda tavolozza.

    La Serie A ha verde, bianco e rosso: il fondo li porta tutti e tre, spenti
    fino a diventare notte. Se il fondo fosse scritto a mano, cambiare la
    fascia lascerebbe le due cose scollegate.

    Serie A e Ligue 1 condividono due dei tre colori — bianco e rosso stanno
    in entrambe le bandiere — e infatti i loro fondi differiscono solo nella
    prima banda. E' una conseguenza dei dati, non un difetto.
    """
    import theme  # noqa: PLC0415

    for scelto in tema.TEMI.values():
        if not tema.e_scuro(scelto):
            continue
        fondo = tema.fondo_sfumato(scelto)
        assert len(fondo) == len(scelto.striscia)
        for spento, acceso in zip(fondo, scelto.striscia, strict=True):
            assert luminanza(spento) < luminanza(acceso), scelto.nome
        assert all(colore in theme.sfondo_di(scelto) for colore in fondo)


@pytest.mark.parametrize("scelto", list(tema.TEMI.values()), ids=lambda t: t.nome)
def test_il_testo_si_legge_su_tutto_il_fondo(scelto: tema.Tema) -> None:
    """Nessun punto della sfumatura schiarisce fino a mangiarsi il testo.

    Il fondo non e' una tinta unita: e' un gradiente fra due o tre colori, e la
    soglia va rispettata in **tutti**, non solo in ``sfondo``.
    """
    if not tema.e_scuro(scelto):
        # Il neutro e' una tinta unita, gia' coperta da
        # `test_il_testo_si_legge_sullo_sfondo`.
        return
    for colore in tema.fondo_sfumato(scelto):
        assert contrasto(scelto.testo, colore) >= 4.5, colore
        assert contrasto(scelto.testo_tenue, colore) >= 3.0, colore
