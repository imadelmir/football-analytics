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


#: Il tema di campionati e tornei.
VERDE: Final[Tema] = Tema(
    nome="verde",
    sfondo="#0d1411",
    superficie="#16211c",
    bordo="#26362e",
    testo="#e8f0ea",
    testo_tenue="#9bb0a4",
    primario="#3fbf7f",
    primario_tenue="#1d5b3f",
    erba_chiara="#1a3d2b",
    erba_scura="#153224",
    linee="#c9d8ce",
    gol="#f5c451",
    atteso="#3fbf7f",
    pericolo="#e8735a",
)

#: Il tema delle finali di Champions League.
BLU: Final[Tema] = Tema(
    nome="blu",
    sfondo="#0b1119",
    superficie="#141d29",
    bordo="#25334a",
    testo="#e7eef8",
    testo_tenue="#9aabc2",
    primario="#4d9fe8",
    primario_tenue="#1e4570",
    erba_chiara="#17304d",
    erba_scura="#122741",
    linee="#ccd9e8",
    gol="#f5c451",
    atteso="#4d9fe8",
    pericolo="#e8735a",
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
