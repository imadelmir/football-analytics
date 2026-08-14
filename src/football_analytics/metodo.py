"""Da dove vengono i numeri e cosa non dicono (M6-T11).

**Il criterio della task e' che questa pagina esista prima del deploy, non
dopo**, e la ragione e' che una metodologia scritta dopo e' un riassunto di
cio' che si e' fatto, mentre scritta prima e' un impegno. Le due cose si
leggono uguali e valgono diverso.

Questo modulo tiene tre elenchi e un conteggio:

- :data:`ANELLI` — la catena del dato, dai JSON di StatsBomb alla dashboard;
- :data:`VERIFICHE` — cosa e' stato controllato **e contro cosa**, con il nome
  del test che tiene onesta ogni affermazione;
- :data:`LIMITI` — cosa i numeri non dicono, con la conseguenza pratica;
- :func:`magazzino` — quanto pesa e quante righe ha ogni tabella, letto dai
  metadati dei Parquet e non da un elenco scritto a mano.

**I riferimenti ai test non sono decorazione.** Un elenco di verifiche senza
prove e' una dichiarazione di buone intenzioni: chiunque puo' scrivere «la
classifica e' stata validata». Citare il test lo rende controllabile in dieci
secondi da chi legge — e :func:`verifiche_orfane` lo rende controllabile a ogni
esecuzione della suite, cosi' una verifica cancellata non puo' restare
pubblicizzata in pagina.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd
import pyarrow.parquet as pq

from football_analytics import config


@dataclass(frozen=True, slots=True)
class Anello:
    """Uno stadio della catena del dato.

    Attributes:
        nome: Come si chiama lo stadio.
        dove: La cartella o il modulo che lo realizza.
        cosa: Che cosa succede qui, in una frase.
    """

    nome: str
    dove: str
    cosa: str


@dataclass(frozen=True, slots=True)
class Verifica:
    """Un controllo fatto sui dati, con la prova che lo tiene onesto.

    Attributes:
        cosa: Che cosa e' stato verificato.
        esito: Il risultato, con i numeri.
        test: Il riferimento pytest, nella forma ``file::funzione``.
    """

    cosa: str
    esito: str
    test: str


@dataclass(frozen=True, slots=True)
class Limite:
    """Qualcosa che i numeri non dicono, e cosa comporta.

    Attributes:
        titolo: Il limite, in poche parole.
        conseguenza: Cosa cambia per chi legge la dashboard.
    """

    titolo: str
    conseguenza: str


#: La catena del dato, dallo scaricamento alla pagina.
#:
#: **Quattro strati rigidi e nessuna scorciatoia**: la dashboard non legge mai
#: i dati grezzi, e i moduli di ``src/`` non sanno che Streamlit esista. E' la
#: ragione per cui la stessa logica si puo' verificare con pytest senza aprire
#: un browser, e per cui una vista rotta non puo' corrompere il magazzino.
ANELLI: Final[tuple[Anello, ...]] = (
    Anello(
        "Sorgente",
        "StatsBomb Open Data",
        "I JSON pubblici degli eventi, uno per partita. Gigabyte di dati grezzi "
        "che non entrano mai in questo repository.",
    ),
    Anello(
        "Ingestione",
        "data/raw/ · ingest.py",
        "Scaricamento incrementale e ripartibile: quello che c'e' gia' non si "
        "riscarica, e un'interruzione non obbliga a ricominciare.",
    ),
    Anello(
        "Trasformazione",
        "data/processed/ · transform.py",
        "Da eventi a sei tabelle Parquet con le sole colonne che le viste usano. "
        "Ogni risultato ricalcolato dagli eventi viene confrontato con quello "
        "ufficiale: se non torna, la costruzione si ferma.",
    ),
    Anello(
        "Modellazione",
        "models/ · model.py",
        "Due modelli xG addestrati su una divisione per partita intera. Le finali "
        "di Champions escono prima della divisione e restano una prova pulita.",
    ),
    Anello(
        "Dashboard",
        "app/ · Streamlit",
        "Sette viste che leggono i Parquet e non calcolano niente di proprio: "
        "la logica sta in src/, l'interfaccia qui.",
    ),
)

#: Cosa e' stato verificato, contro cosa, e con quale test.
#:
#: **Contro la realta' dove possibile, non contro un'altra funzione del
#: progetto.** Un test che confronta due funzioni scritte dalla stessa persona
#: nello stesso pomeriggio verifica la coerenza, non la correttezza: entrambe
#: possono sbagliare allo stesso modo. I controlli piu' utili di questo elenco
#: sono quelli che guardano fuori — classifiche e capocannonieri veri del
#: 2015/16, esiti reali delle finali.
VERIFICHE: Final[tuple[Verifica, ...]] = (
    Verifica(
        "Le classifiche finali dei quattro campionati",
        "Ricostruite dagli eventi e confrontate con quelle vere del 2015/16: "
        "coincidono squadra per squadra, punti compresi.",
        "tests/test_classifica.py::test_le_classifiche_riproducono_quelle_vere",
    ),
    Verifica(
        "I capocannonieri",
        "Suárez 40 nella Liga, Kane 25 in Premier, Higuaín 36 in Serie A. La "
        "Ligue 1 è esclusa apposta: mancano tre partite e il numero sarebbe sbagliato.",
        "tests/test_giocatori.py::test_i_capocannonieri_sono_quelli_veri",
    ),
    Verifica(
        "Ogni risultato ricalcolato dagli eventi",
        "Somma dei gol per partita confrontata con il tabellino ufficiale, "
        "autogol inclusi e rigori dei tiebreak esclusi. Se non torna, la "
        "trasformazione si ferma invece di scrivere un Parquet sbagliato.",
        "tests/test_transform.py::test_il_risultato_calcolato_e_quello_ufficiale",
    ),
    Verifica(
        "La divisione fra addestramento e verifica",
        "Nessuna partita sta da entrambe le parti, con qualunque seed. Un test "
        "mostra anche cosa succederebbe dividendo per tiro: la separazione si perde.",
        "tests/test_divisione.py::test_dividere_per_tiro_invece_che_per_partita_perde_la_separazione",
    ),
    Verifica(
        "Chi ha vinto le finali di Champions",
        "Diciassette esiti confrontati con la storia, comprese le tre decise ai "
        "rigori, che nel tabellino restano in pareggio.",
        "tests/test_albo.py::test_la_finale_ai_rigori_ha_un_vincitore",
    ),
    Verifica(
        "I giocatori trasferiti a metà stagione",
        "Il magazzino ha una riga per squadra: sommate per giocatore, o Éder "
        "comparirebbe due volte con metà dei suoi gol ciascuna.",
        "tests/test_giocatori.py::test_chi_cambia_squadra_conta_una_volta_sola",
    ),
    Verifica(
        "La calibrazione del modello",
        "Verificata sui decili con l'errore standard di ciascuno, non a occhio: "
        "l'errore medio è dell'1,0 % di probabilità per decile.",
        "tests/test_rendiconto.py::test_lo_scarto_e_l_errore_standard_sono_coerenti",
    ),
    Verifica(
        "Che i coefficienti si possano leggere",
        "Le variabili categoriche portano una costante non identificata — la "
        "somma è la stessa per tutte e tre — quindi non entrano nella classifica "
        "delle continue.",
        "tests/test_rendiconto.py::test_le_categoriche_portano_una_costante_non_identificata",
    ),
    Verifica(
        "Che il fotogramma del tiro non sia il dato 360",
        "Due prodotti diversi di StatsBomb: il fotogramma copre il 99 % dei tiri "
        "dei campionati, i dati 360 sono a zero. Un'affermazione sbagliata su "
        "questo punto è già finita in pagina una volta.",
        "tests/test_leghe.py::test_il_fotogramma_del_tiro_invece_c_e_quasi_sempre",
    ),
    Verifica(
        "Che le viste si aprano davvero",
        "Ogni pagina viene eseguita nella suite, non solo importata: un difetto "
        "nel modo in cui le funzioni sono messe insieme non aspetta il browser.",
        "tests/test_pagina.py::test_la_pagina_gira_senza_eccezioni",
    ),
)

#: Cosa i numeri non dicono.
#:
#: **Tutti, non i piu' comodi.** Una pagina che si chiama Metodologia e ne
#: nasconde meta' e' peggio di nessuna pagina: chi se ne accorge smette di
#: credere anche al resto.
LIMITI: Final[tuple[Limite, ...]] = (
    Limite(
        "L'xG mostrato è quello di StatsBomb, non il nostro",
        "In tutte le viste tranne quella del modello. I nostri due modelli "
        "servono a capire come si costruisce un xG e quanto vale, non a "
        "sostituire quello ufficiale, che è addestrato su molti più dati.",
    ),
    Limite(
        "La Ligue 1 ha 377 partite invece di 380",
        "All'Open Data ne mancano tre. Per questo nessun numero di confronto fra "
        "campionati è un totale: sono tutti per partita o per tiro.",
    ),
    Limite(
        "L'albo d'oro non è quello della Champions League",
        "L'Open Data contiene diciassette finali su oltre settanta edizioni: qui "
        "il Liverpool risulta con due coppe invece di sei. Vale solo per le "
        "finali presenti.",
    ),
    Limite(
        "Non ci sono parate né clean sheet",
        "I portieri hanno una scheda ridotta, e la pagina lo dichiara: un radar "
        "costruito su tiri e gol li descriverebbe come attaccanti pessimi.",
    ),
    Limite(
        "La soglia dei minuti esclude dalle graduatorie",
        "Chi sta sotto resta nelle tabelle e nei totali, ma fuori dalle "
        "classifiche per novanta minuti: tre gol in duecento minuti darebbero un "
        "primato che non descrive niente.",
    ),
    Limite(
        "Un giocatore trasferito a metà stagione ha due righe nel magazzino",
        "Sommate per giocatore in tutte le viste. Le squadre restano scritte "
        "entrambe, perché è un'informazione vera.",
    ),
    Limite(
        "I dati 360 non ci sono nei campionati",
        "Ma il fotogramma del tiro sì, sul 99 % dei tiri: le posizioni di "
        "difensori e portiere si conoscono, ed è da lì che il modello spaziale "
        "le prende. I due prodotti sono diversi e vanno tenuti distinti.",
    ),
    Limite(
        "I coefficienti categorici sono definiti a meno di una costante",
        "Confrontabili fra livelli della stessa variabile, non con le variabili "
        "continue né con un'altra categoria. La vista del modello li centra "
        "dentro la variabile invece di metterli in classifica.",
    ),
    Limite(
        "Le finali di Champions non sono una serie storica",
        "Tre sono del 1971-73 e quattordici del 2004-2019: fra il 1974 e il 2003 "
        "non c'è niente. Nessun confronto fra epoche in tutta la dashboard.",
    ),
    Limite(
        "La competizione delle finali contiene una partita di girone",
        "Fiorentina — Manchester United del 1999. È filtrata per fase, o "
        "comparirebbe fra le finaliste di Champions League.",
    ),
    Limite(
        "Un xG non prevede una partita",
        "Dice quanto valevano le occasioni create, a cose fatte. Una squadra con "
        "più xG non era destinata a vincere: aveva tirato da posizioni migliori.",
    ),
)


def magazzino() -> pd.DataFrame:
    """Quanto pesa e quante righe ha ogni tabella del magazzino.

    **Letto dai metadati dei Parquet, non caricando i dati.** Le tabelle dei
    tocchi e dei fotogrammi hanno centinaia di migliaia di righe: aprirle per
    contarle costerebbe secondi a ogni caricamento della pagina, e il conteggio
    e' scritto nel file.

    Returns:
        Una riga per tabella con ``tabella``, ``righe``, ``colonne`` e
        ``megabyte``, dalla piu' pesante. Vuota se il magazzino non e'
        costruito.
    """
    righe = []
    for percorso in sorted(config.DATA_PROCESSED.glob("*.parquet")):
        meta = pq.ParquetFile(percorso).metadata
        righe.append(
            {
                "tabella": percorso.stem,
                "righe": int(meta.num_rows),
                "colonne": int(meta.num_columns),
                "megabyte": percorso.stat().st_size / 1024**2,
            }
        )
    if not righe:
        return pd.DataFrame(columns=["tabella", "righe", "colonne", "megabyte"])
    return pd.DataFrame(righe).sort_values("megabyte", ascending=False).reset_index(drop=True)


def verifiche_orfane(radice: Path | None = None) -> list[str]:
    """I test citati in :data:`VERIFICHE` che nella suite non esistono.

    **E' il test del test.** La pagina Metodologia trae la propria credibilita'
    dal fatto di nominare le prove: se una di quelle prove venisse rinominata o
    cancellata, la pagina continuerebbe a citarla e nessuno se ne accorgerebbe
    guardandola. Questa funzione lo rende un fallimento della suite.

    Args:
        radice: La cartella del progetto. Senza, si usa quella del pacchetto.

    Returns:
        I riferimenti che non trovano riscontro, vuoto se tornano tutti.
    """
    base = radice if radice is not None else config.PROJECT_ROOT
    mancanti = []
    for verifica in VERIFICHE:
        percorso, _, funzione = verifica.test.partition("::")
        file = base / percorso
        if not file.exists() or f"def {funzione}(" not in file.read_text(encoding="utf-8"):
            mancanti.append(verifica.test)
    return mancanti
