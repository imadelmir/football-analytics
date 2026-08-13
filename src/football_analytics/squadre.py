"""Identita' visiva delle squadre: sigla e colore, senza tabelle da mantenere.

Nelle nove competizioni del progetto ci sono piu' di ottanta squadre. Una
tabella scritta a mano con sigla e colore per ciascuna sarebbe da aggiornare a
ogni competizione nuova, e da correggere ogni volta che StatsBomb scrive un
nome in modo leggermente diverso. **Qui si ricava tutto dal nome**, in modo
deterministico: la stessa squadra ha sempre la stessa sigla e lo stesso colore,
su qualunque macchina e in qualunque esecuzione.

**Il colore non e' un colore letterale**, e' calcolato — per questo il modulo
non viola la regola che vieta i colori scritti a mano fuori da ``tema.py``. La
tonalita' viene da un'impronta del nome, mentre saturazione e luminosita' sono
fisse e scelte perche' il testo bianco sopra resti leggibile: senza vincolarle,
un nome sfortunato produrrebbe un giallo su cui non si legge niente.

Non c'e' nessuno stemma qui dentro. Se in ``app/assets/loghi/`` esiste
l'immagine di una squadra, la vista la usa; altrimenti disegna la sigla. Il
codice funziona in entrambi i casi.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Final

#: Parole che non contribuiscono alla sigla di una squadra.
CONNETTIVI: Final[frozenset[str]] = frozenset(
    {"de", "di", "du", "da", "of", "the", "la", "le", "il", "los", "las", "el", "and", "y"}
)

#: Quante lettere al massimo in una sigla.
LETTERE: Final[int] = 4

#: Una parola lunga fino a tanto e' quasi sempre gia' un acronimo — AS, FC,
#: OGC — e va tenuta intera invece di ridurla alla sua iniziale.
ACRONIMO: Final[int] = 3

#: Saturazione e luminosita' fisse del colore generato.
#:
#: Sono vincolate per garantire il contrasto del testo bianco sopra il cerchio.
#: **Il valore e' misurato, non scelto a occhio**: provando tutte e 360 le
#: tonalita', con luminosita' 0,32 il caso peggiore scendeva a 4,29 — sotto la
#: soglia WCAG AA di 4,5, e succedeva davvero su una delle 152 squadre del
#: magazzino. A 0,28 il peggiore sale a 5,29.
#:
#: Lasciarle libere significherebbe che prima o poi una squadra prende un
#: giallo su cui non si legge niente, e nessuno se ne accorge finche' non
#: capita quella squadra.
SATURAZIONE: Final[float] = 0.55
LUMINOSITA: Final[float] = 0.28


def normalizza(nome: str) -> str:
    """Toglie accenti e punteggiatura, per confronti stabili.

    Args:
        nome: Il nome della squadra.

    Returns:
        Il nome senza segni diacritici, in minuscolo.
    """
    senza_accenti = unicodedata.normalize("NFKD", nome)
    pulito = "".join(c for c in senza_accenti if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", pulito.lower()).strip()


def sigla(nome: str) -> str:
    """Ricava la sigla di una squadra dal suo nome.

    Con piu' parole prende le iniziali, saltando le congiunzioni: «Paris
    Saint-Germain» diventa ``PSG``, «Olympique de Marseille» diventa ``OM``.
    Con una parola sola prende le prime tre lettere: «Angers» diventa ``ANG``.

    **Le parole brevissime restano intere**, perche' sono quasi sempre gia'
    acronimi: «AS Monaco» diventa ``ASM`` e non ``AM``, «OGC Nice» diventa
    ``OGCN``. Senza questa regola meta' delle squadre francesi e italiane
    perderebbe la parte riconoscibile del nome.

    Args:
        nome: Il nome della squadra.

    Returns:
        La sigla, da una a quattro lettere maiuscole.
    """
    parole = [p for p in normalizza(nome).split() if p not in CONNETTIVI]
    if not parole:
        return "?"
    if len(parole) == 1:
        return parole[0][:3].upper()
    pezzi = [p if len(p) <= ACRONIMO else p[0] for p in parole]
    return "".join(pezzi)[:LETTERE].upper()


def _da_hsl(tonalita: float) -> str:
    """Converte una tonalita' in esadecimale, con saturazione e luminosita' fisse.

    Args:
        tonalita: La tonalita', fra 0 e 1.

    Returns:
        Il colore in forma ``#rrggbb``.
    """
    c = (1 - abs(2 * LUMINOSITA - 1)) * SATURAZIONE
    x = c * (1 - abs((tonalita * 6) % 2 - 1))
    m = LUMINOSITA - c / 2
    sestante = int(tonalita * 6) % 6
    combinazioni = ((c, x, 0.0), (x, c, 0.0), (0.0, c, x), (0.0, x, c), (x, 0.0, c), (c, 0.0, x))
    canali = [round((v + m) * 255) for v in combinazioni[sestante]]
    return "#" + "".join(f"{v:02x}" for v in canali)


def colore(nome: str) -> str:
    """Assegna a ogni squadra un colore stabile, ricavato dal nome.

    Deterministico: la stessa squadra ha sempre lo stesso colore, su qualunque
    macchina. Usa ``sha256`` e non ``hash()``, che in Python cambia a ogni
    avvio del processo e produrrebbe una dashboard che cambia colori a ogni
    riavvio.

    Args:
        nome: Il nome della squadra.

    Returns:
        Il colore in forma ``#rrggbb``, con contrasto garantito per il testo
        bianco.
    """
    impronta = hashlib.sha256(normalizza(nome).encode("utf-8")).digest()
    return _da_hsl(int.from_bytes(impronta[:4], "big") / 2**32)
