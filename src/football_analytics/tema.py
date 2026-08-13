"""I colori della dashboard, in un posto solo.

**Nessun altro modulo del pacchetto contiene un colore letterale**, e c'e' un
test che lo verifica leggendo il sorgente. Non e' pedanteria: un `#1b7f4f`
scritto dentro un grafico e' invisibile finche' non serve cambiarlo, e allora
va cercato in venti file. Peggio, sopravvive al cambio di tema — la vista
resterebbe verde anche quando tutto il resto e' diventato blu.

Il progetto usa **un tema per competizione**, su due livelli:

- **il neutro e' chiaro.** Senza una competizione scelta la dashboard e'
  bianca: e' lo stato in cui non si sta guardando niente in particolare, e non
  ha senso che indossi i colori di qualcuno.
- **ogni competizione e' scura e porta i propri colori.** La Serie A verde,
  bianco e rosso; La Liga rosso e oro; la Premier due azzurri; le finali blu
  notte e azzurro. Quei colori compaiono in tre punti — la fascia in cima,
  l'accento e il fondo, dove sono spenti fino a diventare notte — e vengono
  tutti da :attr:`Tema.striscia`, quindi cambiarne uno li cambia insieme.

**Il buio non e' piu' il segnale delle finali.** Lo era, e diceva «qui il
modello viene applicato a partite mai viste» invece che addestrato. Ora tutte
le competizioni sono scure, quindi quel significato e' stato speso per
l'identita' visiva: cio' che **deve** restare e' la dichiarazione scritta
nella vista delle finali, perche' da un colore nessuno puo' dedurre che quei
diciotto match sono fuori campione.

Il tema si sceglie dalla competizione, quindi dai dati, e non da un
interruttore che qualcuno puo' dimenticare in una posizione sbagliata. La
scelta passa per il ``competition_id`` di StatsBomb e non per la chiave della
stagione: una nuova annata di Premier League resta azzurra senza che qui
cambi una riga.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from football_analytics import config
from football_analytics.config import Gruppo

#: Il campo da gioco, **uguale in tutte le competizioni**.
#:
#: Prima ogni tema aveva la propria erba, e il campo diventava viola nella
#: Liga e blu notte in Ligue 1. Il risultato era che la stessa mappa dei tiri
#: sembrava dire cose diverse a seconda del campionato: una zona calda su erba
#: scura si legge piu' intensa della stessa zona su erba chiara, e il confronto
#: fra due competizioni diventava un confronto fra due fondi.
#:
#: L'identita' della competizione resta dove non falsa niente: la fascia in
#: cima, l'accento, il fondo della pagina. Il campo e' uno strumento di misura,
#: e uno strumento di misura non cambia unita' con l'occasione.
#:
#: **Le linee vanno scelte insieme all'erba, non dopo.**
#:
#: Rendendo il prato piu' verde le vecchie linee ``#7d8f85`` scendevano a 2,70
#: a 1 sulla striscia chiara, sotto il 3 a 1 che WCAG chiede a un elemento
#: grafico: sarebbero rimaste visibili a chi ha vista buona e sparite agli
#: altri. Con ``#64796c`` il contrasto risale a 3,69 sulla striscia chiara e
#: 3,39 su quella scura.
ERBA_CHIARA: Final[str] = "#d5ead7"
ERBA_SCURA: Final[str] = "#c9e2cc"
LINEE_CAMPO: Final[str] = "#64796c"


@dataclass(frozen=True, slots=True)
class Tema:
    """Una palette completa, sufficiente a disegnare qualunque vista.

    I nomi descrivono **il ruolo**, non il colore: ``primario`` resta
    ``primario`` quando diventa blu. E' cio' che permette di scrivere un grafico
    una volta sola e vederlo cambiare tema senza toccarlo.

    Attributes:
        nome: Identificativo del tema, usato nei test e nei log.
        sfondo: Il fondo della pagina.
        superficie: Il fondo di schede e riquadri, un gradino sopra lo sfondo.
        bordo: Le separazioni fra riquadri.
        testo: Il colore del testo principale.
        testo_tenue: Didascalie, unita' di misura, note.
        primario: Il colore d'accento: pulsanti, selezioni, serie principale.
        primario_tenue: Riempimenti e aree sotto le curve.
        erba_chiara: La striscia chiara del campo. **Uguale in tutti i temi**,
            vedi :data:`ERBA_CHIARA`: resta un campo del tema perche' i
            grafici lo leggono da li', non perche' vari.
        erba_scura: La striscia scura del campo, anch'essa condivisa.
        linee: Le linee del campo, condivise per lo stesso motivo. Le griglie
            dei grafici usano invece ``bordo``, che segue il tema.
        gol: Serie che rappresentano gol realizzati.
        atteso: Serie che rappresentano valori attesi, cioe' l'xG.
        pericolo: Scarti negativi e avvisi.
        barra: Il fondo della barra laterale. **Bianco in tutti i temi**: la
            navigazione non appartiene a una competizione, e vederla cambiare
            colore a ogni scelta la faceva sembrare parte del contenuto.
        barra_testo: Il testo sulla barra laterale, scuro perche' il fondo e'
            chiaro ovunque.
        barra_accento: La voce selezionata. E' il **primo colore della
            striscia** e non l'accento del tema: quello e' schiarito per
            leggersi sul fondo scuro delle pagine, e su una barra bianca
            sparirebbe.
        barra_tenue: Le voci spente del menu. Stesso motivo di
            ``barra_accento``: ``testo_tenue`` e' tarato sul fondo scuro delle
            pagine e sulla barra bianca diventa illeggibile.
        bordo_barra: Lo sfondo di una voce al passaggio del mouse.
        striscia: I colori della fascia d'identita' in cima alla pagina, da
            sinistra a destra. **Tre colori diventano bande nette**, cioe' una
            bandiera; **due diventano una sfumatura**, cioe' un marchio. La
            regola sta nella lunghezza della tupla perche' un tricolore
            sfumato non e' un tricolore, e un marchio a bande sembra rotto.
    """

    nome: str
    sfondo: str
    superficie: str
    bordo: str
    testo: str
    testo_tenue: str
    primario: str
    primario_tenue: str
    erba_chiara: str
    erba_scura: str
    linee: str
    gol: str
    atteso: str
    pericolo: str
    barra: str
    barra_testo: str
    barra_accento: str
    barra_tenue: str
    bordo_barra: str
    striscia: tuple[str, ...]


#: Il tema di campionati e tornei.
#:
#: I colori strutturali sono **gli stessi** di ``.streamlit/config.toml``, e un
#: test verifica che non divergano. Tutti i contrasti sono misurati: il testo
#: sta a 15,2 a 1 sullo sfondo, la barra laterale a 9,7, dove lo standard WCAG
#: AA ne chiede 4,5.
VERDE: Final[Tema] = Tema(
    nome="verde",
    sfondo="#f6f8f7",
    superficie="#ffffff",
    bordo="#d5dedb",
    testo="#111827",
    testo_tenue="#6b7280",
    primario="#15803d",
    primario_tenue="#dcfce7",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#15803d",
    atteso="#2f6fed",
    pericolo="#dc2626",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#15803d",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#15803d", "#4ade80"),
)

#: Premier League: azzurro.
#:
#: Non e' il viola del marchio ufficiale, che su fondo chiaro diventa cupo e
#: che comunque non si puo' riprodurre senza usare l'identita' visiva della
#: lega. L'azzurro e' la lettura comune del campionato inglese e resta a
#: 5,93 a 1 sul bianco, dove per un elemento grafico ne bastano 3.
PREMIER: Final[Tema] = Tema(
    nome="premier",
    sfondo="#091f35",
    superficie="#0f263d",
    bordo="#0c3654",
    testo="#e8eef8",
    testo_tenue="#95c0d8",
    primario="#6da8c8",
    primario_tenue="#082b47",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#6da8c8",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#0369a1",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#0369a1", "#38bdf8"),
)

#: La Liga: rosso e oro.
#:
#: Con l'accento rosso, ``pericolo`` non puo' restare rosso: due rossi vicini
#: nella stessa vista si leggono come la stessa cosa. Diventa ambra, che resta
#: un colore d'allarme senza confondersi con l'accento.
LIGA: Final[Tema] = Tema(
    nome="liga",
    sfondo="#26131f",
    superficie="#291b2b",
    bordo="#4a1b27",
    testo="#e8eef8",
    testo_tenue="#e2a0a0",
    primario="#d67b7b",
    primario_tenue="#3e141f",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#d67b7b",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#b91c1c",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#b91c1c", "#f2b705", "#b91c1c"),
)

#: Serie A: il tricolore.
#:
#: Il verde e' quello della bandiera, piu' acceso del verde neutro del
#: progetto, ma resta il tema che si distingue meno dal neutro: a fare il
#: lavoro e' la fascia tricolore in cima, non l'accento.
SERIE_A: Final[Tema] = Tema(
    nome="serie_a",
    sfondo="#082526",
    superficie="#0f2b30",
    bordo="#0b4135",
    testo="#e8eef8",
    testo_tenue="#94cfb1",
    primario="#6bbc93",
    primario_tenue="#07362b",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#6bbc93",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#008c45",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#008c45", "#ffffff", "#ce2b37"),
)

#: Ligue 1: blu di Francia.
#:
#: Blu scuro contro l'azzurro chiaro della Premier: sono due blu, ma a
#: luminosita' opposte, e le due fasce d'identita' non si somigliano.
LIGUE1: Final[Tema] = Tema(
    nome="ligue1",
    sfondo="#0d1831",
    superficie="#131f3a",
    bordo="#15264d",
    testo="#e8eef8",
    testo_tenue="#a0acce",
    primario="#7c8dbb",
    primario_tenue="#101d40",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#7c8dbb",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#1e3a8a",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#1e3a8a", "#ffffff", "#ce2b37"),
)

#: Coppa d'Africa: verde scuro e oro.
COPPA_AFRICA: Final[Tema] = Tema(
    nome="coppa_africa",
    sfondo="#192f32",
    superficie="#293e40",
    bordo="#47595b",
    testo="#e8eef8",
    testo_tenue="#9cb7a7",
    primario="#779b85",
    primario_tenue="#2e4744",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#779b85",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#14532d",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#14532d", "#c99a2e", "#14532d"),
)

#: Campionato Europeo: rosso e blu.
#:
#: Il rosso e' piu' rosato di quello de La Liga, che e' mattone: due tornei che
#: non si incontrano mai nella stessa vista possono somigliarsi, ma non fino a
#: rendere inutile il colore.
EUROPEI: Final[Tema] = Tema(
    nome="europei",
    sfondo="#1b2a52",
    superficie="#2b395e",
    bordo="#495575",
    testo="#e8eef8",
    testo_tenue="#e49bad",
    primario="#d9768e",
    primario_tenue="#453b5f",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#d9768e",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#1e40af",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#1e40af", "#be123c"),
)

#: Coppa del Mondo: oro.
#:
#: L'oro puro non si puo' usare per il testo — su bianco sta sotto il 3 a 1 —
#: quindi l'accento e' il bronzo dorato che regge 4,92, e il giallo pieno resta
#: nella fascia d'identita', dove non deve essere letto ma visto.
MONDIALI: Final[Tema] = Tema(
    nome="mondiali",
    sfondo="#37312a",
    superficie="#453f39",
    bordo="#5f5a55",
    testo="#e8eef8",
    testo_tenue="#d8bd97",
    primario="#c8a46f",
    primario_tenue="#574a39",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#c8a46f",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#a16207",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#a16207", "#e8c766"),
)

#: Le finali di Champions League: nero, blu notte, azzurro.
#:
#: **L'unico tema scuro del progetto**, e il buio e' il segnale: qui il
#: modello viene applicato a partite che non ha mai visto.
#:
#: ``atteso`` e' un grigio acciaio e non un secondo colore acceso. Non e' una
#: rinuncia: l'xG e' il valore *previsto*, i gol sono quello *accaduto*, e
#: farli spiccare sul valore atteso rende il grafico leggibile nel verso
#: giusto.
BLU: Final[Tema] = Tema(
    nome="blu",
    sfondo="#162438",
    superficie="#263346",
    bordo="#455060",
    testo="#e6edf8",
    testo_tenue="#93a6c4",
    primario="#38bdf8",
    primario_tenue="#1d4662",
    erba_chiara=ERBA_CHIARA,
    erba_scura=ERBA_SCURA,
    linee=LINEE_CAMPO,
    gol="#38bdf8",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#0b2545",
    barra_tenue="#6b7280",
    bordo_barra="#eef1f0",
    striscia=("#0b2545", "#38bdf8"),
)

#: Tutti i temi, per nome.
TEMI: Final[dict[str, Tema]] = {
    t.nome: t for t in (VERDE, PREMIER, LIGA, SERIE_A, LIGUE1, COPPA_AFRICA, EUROPEI, MONDIALI, BLU)
}

#: Da quale competizione di StatsBomb viene ciascun tema.
#:
#: La chiave e' il ``competition_id``, non la chiave della stagione: aggiungere
#: la Premier 2016/17 non richiede di toccare questa tabella, e i due Europei
#: del magazzino — 2020 e 2024 — condividono il tema perche' condividono
#: l'identificativo, che e' il comportamento giusto: sono la stessa
#: competizione in due edizioni.
#:
#: Il neutro resta per le selezioni senza competizione, non per i tornei:
#: quelli hanno il proprio colore come i campionati.
PER_COMPETIZIONE: Final[dict[int, Tema]] = {
    config.PREMIER_2015_16.competition_id: PREMIER,
    config.LA_LIGA_2015_16.competition_id: LIGA,
    config.SERIE_A_2015_16.competition_id: SERIE_A,
    config.LIGUE_1_2015_16.competition_id: LIGUE1,
    config.COPPA_AFRICA_2023.competition_id: COPPA_AFRICA,
    config.EURO_2024.competition_id: EUROPEI,
    config.MONDIALI_2022.competition_id: MONDIALI,
}

#: La scala di colori dei tiri, dal meno pericoloso al piu' pericoloso.
#:
#: Cinque gradini e non una sfumatura continua: l'occhio non distingue un
#: gradiente su pallini piccoli e sovrapposti, mentre cinque classi si leggono
#: dalla legenda e si contano. I confini — 0,05 · 0,10 · 0,30 · 0,50 — non sono
#: arbitrari: separano il tiro da fuori dal tiro in area, e l'occasione dalla
#: quasi-rete.
#:
#: **Ogni fascia porta anche la propria opacita', e questa e' la parte che
#: decide se la mappa si legge.** I tiri da niente sono la meta' del totale: a
#: piena opacita' formano una massa che copre le occasioni vere, cioe' proprio
#: quello che si vuole guardare. Facendoli sbiadire diventano il contesto —
#: «da qui si tira tanto» — e le occasioni restano in primo piano.
#:
#: Il colore va dal grigio freddo all'ambra: freddo per il tiro della
#: disperazione, caldo per la quasi-rete. E' la convenzione delle mappe di
#: calore, e non richiede di consultare la legenda per capire il verso.
SCALA_XG: Final[tuple[tuple[str, float, str, float], ...]] = (
    ("< 0,05", 0.05, "#b8c4cc", 0.16),
    ("0,05 – 0,10", 0.10, "#5b93b8", 0.30),
    ("0,10 – 0,30", 0.30, "#1e9e7e", 0.55),
    ("0,30 – 0,50", 0.50, "#16a34a", 0.85),
    ("> 0,50", 1.01, "#ea580c", 1.0),
)

#: La stessa scala in tonalita' fredde, per il tema notturno delle finali.
SCALA_XG_NOTTE: Final[tuple[tuple[str, float, str, float], ...]] = (
    ("< 0,05", 0.05, "#3d4a63", 0.20),
    ("0,05 – 0,10", 0.10, "#4f7fc0", 0.34),
    ("0,10 – 0,30", 0.30, "#38bdf8", 0.58),
    ("0,30 – 0,50", 0.50, "#a78bfa", 0.86),
    ("> 0,50", 1.01, "#fb923c", 1.0),
)


#: La soglia sotto cui la formula WCAG usa il ramo lineare invece della potenza.
GINOCCHIO: Final[float] = 0.03928

#: Il punto di mezzo fra chiaro e scuro, in luminanza.
MEZZO: Final[float] = 0.5


def luminanza(colore: str) -> float:
    """La luminanza relativa di un colore, secondo la formula WCAG.

    Args:
        colore: Un colore esadecimale a sei cifre.

    Returns:
        Un valore fra 0 (nero) e 1 (bianco).
    """
    canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [v / 12.92 if v <= GINOCCHIO else ((v + 0.055) / 1.055) ** 2.4 for v in canali]
    return 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]


def e_scuro(tema: Tema) -> bool:
    """Se il tema ha il fondo scuro.

    **Si misura, non si elenca.** Un tema e' scuro perche' il suo fondo lo e',
    non perche' si chiama in un certo modo: cosi' le regole che valgono «sui
    temi scuri» continuano a valere se domani ne nasce un altro, e non c'e' un
    elenco di nomi da tenere aggiornato in due posti.

    Args:
        tema: La palette.

    Returns:
        Vero se il fondo e' piu' scuro del punto di mezzo.
    """
    return luminanza(tema.sfondo) < MEZZO


#: Il fondo notte con cui si smorzano i colori d'identita'.
#:
#: Non e' nero puro: il nero spegne la tinta e tutti i fondi verrebbero uguali.
#: E' anche piu' chiaro di un blu notte pieno, perche' il fondo deve restare un
#: ambiente e non un pozzo — a 0a1120 le schede sembravano illuminate da un
#: faro.
NOTTE: Final[str] = "#1a2334"

#: Quanto resta del colore d'identita' nel fondo. Il resto e' notte.
QUANTO_TINGE: Final[float] = 0.26


def _mescola(primo: str, secondo: str, quota: float) -> str:
    """Fonde due colori.

    Args:
        primo: Il colore di partenza.
        secondo: Quello verso cui andare.
        quota: Quanto del secondo, fra 0 e 1.

    Returns:
        Il colore risultante, esadecimale.
    """
    canali = (
        round(int(primo[i : i + 2], 16) * (1 - quota) + int(secondo[i : i + 2], 16) * quota)
        for i in (1, 3, 5)
    )
    return "#" + "".join(f"{min(255, max(0, c)):02x}" for c in canali)


def fondo_sfumato(tema: Tema) -> tuple[str, ...]:
    """I colori del fondo della pagina, dai colori d'identita' della competizione.

    **Il fondo e' la bandiera, spenta fino a diventare notte.** La Serie A ha
    verde, bianco e rosso; il fondo li porta tutti e tre, ognuno scurito al
    punto da restare un'atmosfera invece che un colore. Cosi' la pagina si
    riconosce prima ancora di leggere il titolo, e non serve inventare una
    seconda tavolozza accanto a quella che gia' definisce la competizione.

    **Quanto un colore tinge dipende da quanto e' chiaro.** Il bianco della
    Serie A e della Ligue 1 con una quota fissa schiariva il fondo fino a
    portare il testo sotto la soglia di leggibilita': moltiplicando la quota
    per ``1 - luminanza`` il bianco tinge quasi nulla e resta la banda neutra
    fra le due colorate, che e' il ruolo che ha nella bandiera, mentre un
    verde o un rosso scuri tingono pieno.

    Args:
        tema: La palette.

    Returns:
        I colori del fondo, nell'ordine della fascia d'identita'.
    """
    return tuple(
        _mescola(NOTTE, colore, QUANTO_TINGE * (1 - luminanza(colore))) for colore in tema.striscia
    )


def _senza_opacita(colore: str) -> str:
    """Lo stesso colore, completamente trasparente.

    Serve al primo gradino delle mappe di calore. Partire da
    :data:`TRASPARENTE` — che e' un nero trasparente — non e' equivalente:
    Plotly interpola fra i gradini **anche sul canale del colore**, quindi le
    zone quasi vuote passerebbero per un grigio sporco prima di prendere la
    tinta giusta. Partendo dalla stessa tinta a opacita' zero la sfumatura
    resta pulita.

    Args:
        colore: Un colore esadecimale a sei cifre.

    Returns:
        Lo stesso colore in notazione ``rgba`` con opacita' zero.
    """
    rosso, verde, blu = (int(colore[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({rosso},{verde},{blu},0)"


#: La scala delle mappe di calore, uguale per tutti i temi chiari.
#:
#: **Non deriva dall'accento della lega**, e la prima versione lo faceva: la
#: mappa de La Liga veniva tutta rossa, dal quasi-vuoto al punto piu' battuto,
#: perche' una sola tinta ha pochi gradini distinguibili. Con cinque tinte i
#: gradini si contano a occhio senza consultare la barra.
#:
#: **La luminanza scende a ogni gradino** — 0,86 · 0,67 · 0,62 · 0,34 · 0,14 ·
#: 0,05 — quindi la mappa resta leggibile anche stampata in bianco e nero, e
#: soprattutto non crea bordi finti: una scala arcobaleno che risale di
#: luminosita' disegna confini dove il dato e' liscio, ed e' il difetto per cui
#: la scala «jet» e' sconsigliata da trent'anni.
#:
#: Non finisce in blu o viola, che pure sarebbero belli: dal rosso al viola il
#: salto percettivo misura ΔE 79-87 contro i 34-45 di ogni altro passo, e
#: quello si vedrebbe come un anello netto attorno al punto piu' caldo.
SCALA_CALORE: Final[tuple[tuple[float, str], ...]] = (
    (0.00, "rgba(205,235,180,0)"),
    (0.06, "#cdebb4"),
    (0.26, "#96e673"),
    (0.46, "#f2cc25"),
    (0.64, "#ef8118"),
    (0.84, "#cf1f2d"),
    (1.00, "#7a1020"),
)


def scala_calore(tema: Tema, sotto: float = 0.0) -> tuple[tuple[float, str], ...]:
    """La scala continua delle mappe di calore.

    Le finali di Champions tengono la propria, costruita dal tema: sul fondo
    nero la scala chiara sbianca il campo, mentre quella derivata parte dal
    blu notte e sale all'azzurro, che e' esattamente il contrasto che il tema
    scuro puo' permettersi.

    **Sotto una soglia la mappa e' del tutto trasparente**, cosi' l'erba resta
    erba. Senza, Plotly interpola l'opacita' dal primo gradino e le zone dove
    non si tira quasi mai prendono un velo biancastro: il campo sembra coperto
    di nebbia e non si capisce piu' dove finisce il dato e dove comincia il
    disegno. La soglia arriva da chi chiama perche' dipende dal massimo di
    *quella* mappa — vedi :func:`football_analytics.viz.mappa_di_calore`.

    Args:
        tema: La palette attiva.
        sotto: La posizione sulla scala, fra 0 e 1, fino alla quale la mappa
            resta invisibile. A zero la scala e' quella piena di sempre.

    Returns:
        I gradini della scala, come coppie posizione-colore.
    """
    gradini = SCALA_CALORE
    if tema.nome == BLU.nome:
        gradini = (
            (0.0, _senza_opacita(tema.primario_tenue)),
            (0.15, tema.primario_tenue),
            (0.55, tema.primario),
            (1.0, scala_di(tema)[-1][2]),
        )
    if sotto <= 0.0:
        return gradini

    # Due gradini con la stessa tinta trasparente, non uno: con un gradino solo
    # Plotly comincerebbe a far salire l'opacita' subito dopo lo zero, che e'
    # il difetto che questa soglia esiste per togliere.
    invisibile = _senza_opacita(gradini[1][1])
    coda = tuple((sotto + posizione * (1.0 - sotto), colore) for posizione, colore in gradini[1:])
    return ((0.0, invisibile), (sotto, invisibile), *coda)


def scala_di(tema: Tema) -> tuple[tuple[str, float, str, float], ...]:
    """La scala dei tiri adatta al tema attivo.

    Args:
        tema: La palette attiva.

    Returns:
        Le cinque fasce: etichetta, limite superiore, colore e opacita'.
    """
    return SCALA_XG_NOTTE if tema.nome == BLU.nome else SCALA_XG


#: Riempimento trasparente, per le forme che devono avere solo il contorno.
#:
#: Sta qui e non in ``viz.py`` perche' e' comunque un valore di colore, e il
#: test che vieta i colori letterali fuori da questo file lo ha giustamente
#: segnalato la prima volta che l'ho scritto altrove.
TRASPARENTE: Final[str] = "rgba(0,0,0,0)"


def per_gruppo(gruppo: str | Gruppo) -> Tema:
    """Sceglie il tema dal gruppo della competizione.

    Il tema viene **dai dati**, non da un interruttore: e' impossibile trovarsi
    la vista delle finali colorata di verde perche' qualcuno ha dimenticato di
    cambiare uno stato.

    Args:
        gruppo: Il gruppo della competizione mostrata.

    Returns:
        Il tema blu per le finali, quello verde per tutto il resto.
    """
    return BLU if str(gruppo) == str(Gruppo.FINALI) else VERDE


def per_competizione(chiave: str | None) -> Tema:
    """Sceglie il tema dalla competizione selezionata.

    Le finali di Champions restano l'unica vista scura; i quattro campionati
    hanno il proprio accento; tornei per nazionali, selezione vuota e chiavi
    sconosciute stanno sul tema neutro.

    **Una chiave sconosciuta non solleva.** :func:`config.competizione` lo fa,
    ed e' giusto la' — un errore di battitura in una pipeline va visto subito.
    Qui no: e' il tema di una dashboard, e restare senza colore e' preferibile
    a una pagina che non si apre.

    Args:
        chiave: La chiave della competizione, per esempio
            ``"premier_2015_16"``, oppure ``None`` per la selezione completa.

    Returns:
        Il tema della competizione, oppure quello verde.
    """
    if not chiave:
        return VERDE
    try:
        voce = config.competizione(chiave)
    except ValueError:
        return VERDE
    if voce.gruppo == Gruppo.FINALI:
        return BLU
    return PER_COMPETIZIONE.get(voce.competition_id, VERDE)
