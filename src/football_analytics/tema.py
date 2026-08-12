"""I colori della dashboard, in un posto solo.

**Nessun altro modulo del pacchetto contiene un colore letterale**, e c'e' un
test che lo verifica leggendo il sorgente. Non e' pedanteria: un `#1b7f4f`
scritto dentro un grafico e' invisibile finche' non serve cambiarlo, e allora
va cercato in venti file. Peggio, sopravvive al cambio di tema — la vista
resterebbe verde anche quando tutto il resto e' diventato blu.

Il progetto usa **un tema per competizione**, ma su due soli livelli, e la
distinzione fra i due livelli e' la cosa importante:

- **i temi chiari** — verde neutro, piu' uno per ciascuno dei quattro
  campionati — cambiano l'accento, la sfumatura del fondo e la fascia
  d'identita' in cima alla pagina. La struttura resta la stessa: fondo chiaro,
  schede bianche, testo scuro. Servono a far sentire dove si sta guardando.
- **il tema scuro** e' uno solo, ed e' quello delle finali di Champions
  League: 18 partite dal 1971 al 2019, e soprattutto le uniche su cui il
  modello viene **applicato** invece che addestrato.

**Perche' solo le finali diventano scure.** Il buio era il segnale di quella
differenza epistemica, e dare un colore proprio a ogni lega rischiava di
spegnerlo: se tutto cambia colore, cambiare colore non vuol dire piu' niente.
Tenendo il buio per le sole finali il segnale sopravvive — le leghe si
distinguono fra loro, ma restano tutte «dove il modello ha imparato», e una
sola vista dichiara «qui il modello sta indovinando».

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
        erba_chiara: La striscia chiara del campo.
        erba_scura: La striscia scura del campo.
        linee: Le linee del campo, e le griglie dei grafici.
        gol: Serie che rappresentano gol realizzati.
        atteso: Serie che rappresentano valori attesi, cioe' l'xG.
        pericolo: Scarti negativi e avvisi.
        barra: Il fondo della barra laterale, scuro anche a tema chiaro: separa
            la navigazione dal contenuto senza bisogno di una linea.
        barra_testo: Il testo sulla barra laterale.
        barra_accento: La voce selezionata nella barra laterale.
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
    erba_chiara="#eef4f0",
    erba_scura="#e6eeea",
    linee="#7d8f85",
    gol="#15803d",
    atteso="#2f6fed",
    pericolo="#dc2626",
    barra="#ffffff",
    barra_testo="#111827",
    barra_accento="#15803d",
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
    sfondo="#f4f8fc",
    superficie="#ffffff",
    bordo="#d3dfea",
    testo="#0d1b2a",
    testo_tenue="#5b6b7c",
    primario="#0369a1",
    primario_tenue="#dbeafe",
    erba_chiara="#eef4fa",
    erba_scura="#e5eef7",
    linee="#7d94a8",
    gol="#0369a1",
    atteso="#b45309",
    pericolo="#dc2626",
    barra="#ffffff",
    barra_testo="#0d1b2a",
    barra_accento="#0369a1",
    striscia=("#0369a1", "#38bdf8"),
)

#: La Liga: rosso e oro.
#:
#: Con l'accento rosso, ``pericolo`` non puo' restare rosso: due rossi vicini
#: nella stessa vista si leggono come la stessa cosa. Diventa ambra, che resta
#: un colore d'allarme senza confondersi con l'accento.
LIGA: Final[Tema] = Tema(
    nome="liga",
    sfondo="#fcf6f5",
    superficie="#ffffff",
    bordo="#ead9d6",
    testo="#1c1210",
    testo_tenue="#7a6460",
    primario="#b91c1c",
    primario_tenue="#fee2e2",
    erba_chiara="#f8f2f0",
    erba_scura="#f1e9e7",
    linee="#a89490",
    gol="#b91c1c",
    atteso="#1d4ed8",
    pericolo="#b45309",
    barra="#ffffff",
    barra_testo="#1c1210",
    barra_accento="#b91c1c",
    striscia=("#b91c1c", "#f2b705", "#b91c1c"),
)

#: Serie A: il tricolore.
#:
#: Il verde e' quello della bandiera, piu' acceso del verde neutro del
#: progetto, ma resta il tema che si distingue meno dal neutro: a fare il
#: lavoro e' la fascia tricolore in cima, non l'accento.
SERIE_A: Final[Tema] = Tema(
    nome="serie_a",
    sfondo="#f4faf6",
    superficie="#ffffff",
    bordo="#d3e5da",
    testo="#10201a",
    testo_tenue="#5d7268",
    primario="#008c45",
    primario_tenue="#d6f0e0",
    erba_chiara="#eff7f2",
    erba_scura="#e6f1ea",
    linee="#7f9a8c",
    gol="#008c45",
    atteso="#1d4ed8",
    pericolo="#ce2b37",
    barra="#ffffff",
    barra_testo="#10201a",
    barra_accento="#008c45",
    striscia=("#008c45", "#ffffff", "#ce2b37"),
)

#: Ligue 1: blu di Francia.
#:
#: Blu scuro contro l'azzurro chiaro della Premier: sono due blu, ma a
#: luminosita' opposte, e le due fasce d'identita' non si somigliano.
LIGUE1: Final[Tema] = Tema(
    nome="ligue1",
    sfondo="#f5f7fc",
    superficie="#ffffff",
    bordo="#d6dcea",
    testo="#0e1526",
    testo_tenue="#5f6a80",
    primario="#1e3a8a",
    primario_tenue="#dbe3f8",
    erba_chiara="#f0f3fa",
    erba_scura="#e7ecf6",
    linee="#8290a8",
    gol="#1e3a8a",
    atteso="#b45309",
    pericolo="#ce2b37",
    barra="#ffffff",
    barra_testo="#0e1526",
    barra_accento="#1e3a8a",
    striscia=("#1e3a8a", "#ffffff", "#ce2b37"),
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
    sfondo="#05070e",
    superficie="#0d1526",
    bordo="#1e2b45",
    testo="#e6edf8",
    testo_tenue="#8fa0bd",
    primario="#38bdf8",
    primario_tenue="#123049",
    erba_chiara="#101a2e",
    erba_scura="#0c1424",
    linee="#33425f",
    gol="#38bdf8",
    atteso="#94a3b8",
    pericolo="#f97316",
    barra="#05070e",
    barra_testo="#f2f6fc",
    barra_accento="#38bdf8",
    striscia=("#0b2545", "#38bdf8"),
)

#: Tutti i temi, per nome.
TEMI: Final[dict[str, Tema]] = {t.nome: t for t in (VERDE, PREMIER, LIGA, SERIE_A, LIGUE1, BLU)}

#: Da quale competizione di StatsBomb viene ciascun tema di lega.
#:
#: La chiave e' il ``competition_id``, non la chiave della stagione: aggiungere
#: la Premier 2016/17 non richiede di toccare questa tabella. I tornei per
#: nazionali — Mondiali, Europei, Coppa d'Africa — non compaiono di proposito
#: e restano sul tema neutro.
PER_COMPETIZIONE: Final[dict[int, Tema]] = {
    config.PREMIER_2015_16.competition_id: PREMIER,
    config.LA_LIGA_2015_16.competition_id: LIGA,
    config.SERIE_A_2015_16.competition_id: SERIE_A,
    config.LIGUE_1_2015_16.competition_id: LIGUE1,
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
    (0.00, "rgba(226,243,231,0)"),
    (0.06, "#e2f3e7"),
    (0.26, "#b6e39c"),
    (0.46, "#f2cc25"),
    (0.64, "#ef8118"),
    (0.84, "#cf1f2d"),
    (1.00, "#7a1020"),
)


def scala_calore(tema: Tema) -> tuple[tuple[float, str], ...]:
    """La scala continua delle mappe di calore.

    Le finali di Champions tengono la propria, costruita dal tema: sul fondo
    nero la scala chiara sbianca il campo, mentre quella derivata parte dal
    blu notte e sale all'azzurro, che e' esattamente il contrasto che il tema
    scuro puo' permettersi.

    Args:
        tema: La palette attiva.

    Returns:
        I gradini della scala, come coppie posizione-colore.
    """
    if tema.nome == BLU.nome:
        return (
            (0.0, _senza_opacita(tema.primario_tenue)),
            (0.15, tema.primario_tenue),
            (0.55, tema.primario),
            (1.0, scala_di(tema)[-1][2]),
        )
    return SCALA_CALORE


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
