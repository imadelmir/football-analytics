"""I colori della dashboard, in un posto solo.

**Nessun altro modulo del pacchetto contiene un colore letterale**, e c'e' un
test che lo verifica leggendo il sorgente. Non e' pedanteria: un `#1b7f4f`
scritto dentro un grafico e' invisibile finche' non serve cambiarlo, e allora
va cercato in venti file. Peggio, sopravvive al cambio di tema — la vista
resterebbe verde anche quando tutto il resto e' diventato blu.

Il progetto usa **due temi**:

- **verde** per campionati e tornei, che sono la maggior parte dei dati;
- **blu** per le finali di Champions League, che sono un'altra cosa: 18 partite
  dal 1971 al 2019, e soprattutto le uniche su cui il modello viene
  **applicato** invece che addestrato. Il colore diverso e' un promemoria
  visivo di quella distinzione, non una decorazione.

Il tema si sceglie dal gruppo della competizione, quindi dai dati, e non da un
interruttore che qualcuno puo' dimenticare in una posizione sbagliata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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


#: Il tema di campionati e tornei.
#:
#: I colori strutturali sono **gli stessi** di ``.streamlit/config.toml``, e un
#: test verifica che non divergano. Tutti i contrasti sono misurati: il testo
#: sta a 15,2 a 1 sullo sfondo, la barra laterale a 9,7, dove lo standard WCAG
#: AA ne chiede 4,5.
VERDE: Final[Tema] = Tema(
    nome="verde",
    sfondo="#f4f7f4",
    superficie="#ffffff",
    bordo="#e3e8e3",
    testo="#10231b",
    testo_tenue="#4a6157",
    primario="#0f6e56",
    primario_tenue="#d9ece4",
    erba_chiara="#eaf2ec",
    erba_scura="#e2ece5",
    linee="#83a08d",
    gol="#a1580a",
    atteso="#0f6e56",
    pericolo="#b3261e",
    barra="#0b3a2c",
    barra_testo="#c9e8dc",
    barra_accento="#1d9e75",
)

#: Il tema delle finali di Champions League.
BLU: Final[Tema] = Tema(
    nome="blu",
    sfondo="#f4f6fa",
    superficie="#ffffff",
    bordo="#e2e7ef",
    testo="#101a2b",
    testo_tenue="#4d5f78",
    primario="#14538f",
    primario_tenue="#d7e3f2",
    erba_chiara="#eaeff7",
    erba_scura="#e2e9f4",
    linee="#8b9cb5",
    gol="#a1580a",
    atteso="#14538f",
    pericolo="#b3261e",
    barra="#0d2e52",
    barra_testo="#cddff2",
    barra_accento="#3d86d4",
)

#: Tutti i temi, per nome.
TEMI: Final[dict[str, Tema]] = {VERDE.nome: VERDE, BLU.nome: BLU}

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
