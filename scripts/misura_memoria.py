"""Quanta memoria occupa il magazzino una volta letto (M7-T5).

Il criterio della task e' che **con tutte le viste aperte l'app resti sotto il
gigabyte**, e Streamlit Cloud non espone un contatore: se lo si supera il
processo viene ucciso e nei log resta solo una disconnessione. Serve quindi
misurare da questa parte.

**Cosa conta davvero.** Le viste sono transitorie — Streamlit riesegue lo
script a ogni interazione e le tabelle derivate vengono ricostruite e buttate.
Cio' che resta in memoria per tutta la sessione sono le sei tabelle in cache
dentro ``dati.leggi``: quelle sono il costo fisso, e sommate al costo
dell'interprete con pandas, numpy, scikit-learn, plotly e streamlit caricati
danno il numero che il criterio chiede.

Per questo lo script misura tre cose separate invece di una sola:

1. **La base**: quanto pesa il processo dopo aver importato le librerie e
   prima di leggere qualunque dato.
2. **Il magazzino**: quanto aggiunge ciascuna tabella, in memoria e non su
   disco — un Parquet e' compresso, e il rapporto fra i due numeri e' la cosa
   piu' facile da sottovalutare.
3. **Il picco**: quanto sale durante l'aggregazione piu' pesante, che e' il
   momento in cui un'app muore.

Uso::

    uv run python scripts/misura_memoria.py

**Nessuna dipendenza in piu'.** ``psutil`` sarebbe la strada comoda, ma
aggiungerebbe un pacchetto all'ambiente di produzione per uno script che gira
tre volte l'anno. La memoria residente si legge da ``/proc/self/status`` su
Linux — che e' il sistema di Streamlit Cloud — e dalle API di sistema via
``ctypes`` su Windows, dove il progetto viene sviluppato.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

from football_analytics import classifica, panoramica
from football_analytics.config import DATA_PROCESSED

#: Il tetto di Streamlit Community Cloud, dichiarato dalla piattaforma.
TETTO_MB: Final[float] = 1024.0

#: Le sei tabelle che la dashboard tiene in cache per tutta la sessione.
TABELLE: Final[tuple[str, ...]] = (
    "matches",
    "shots",
    "passes",
    "touches",
    "player_stats",
    "freeze_frames",
)


class _ContatoriMemoria(ctypes.Structure):
    """La struttura ``PROCESS_MEMORY_COUNTERS`` di Windows.

    Dichiarata qui invece di importare ``psutil``: serve un campo su dieci, e
    il resto va comunque descritto perche' le dimensioni tornino.

    I tipi sono quelli di ``ctypes`` e non quelli di ``ctypes.wintypes``: il
    secondo modulo **solleva un errore al solo import** su Linux, e questo file
    viene analizzato da mypy anche in CI, che gira su Linux. ``DWORD`` e'
    ``c_ulong``, quindi non si perde niente.
    """

    _fields_ = (
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    )


#: Il nome della piattaforma, passato per una variabile e non letto in linea.
#:
#: ``if sys.platform == "win32"`` mypy lo **risolve staticamente**: sulla
#: macchina di sviluppo il ramo Linux diventa irraggiungibile, in CI quello
#: Windows, e ``warn_unreachable`` segnala l'uno o l'altro a seconda di dove
#: gira. Passando per una variabile di tipo ``str`` la scelta torna a essere
#: quello che e': una decisione a tempo d'esecuzione.
SISTEMA: Final[str] = sys.platform


def residente_mb() -> float | None:
    """La memoria fisica occupata da questo processo, in megabyte.

    Returns:
        I megabyte residenti, oppure ``None`` se la piattaforma non offre un
        modo di saperlo senza dipendenze. Chi chiama deve reggere l'assenza:
        una misura mancante va dichiarata, non sostituita con uno zero.
    """
    if SISTEMA.startswith("linux"):
        for riga_stato in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if riga_stato.startswith("VmRSS:"):
                return float(riga_stato.split()[1]) / 1024.0
        return None

    # `getattr` e non `ctypes.windll`: l'attributo non esiste fuori da Windows,
    # e scriverlo direttamente costringerebbe a un `type: ignore` che su
    # Windows diventa inutilizzato — e `warn_unused_ignores` lo segnala.
    windll: Any = getattr(ctypes, "windll", None)
    if windll is None:
        return None

    # I tipi vanno dichiarati, e non e' pignoleria: senza `restype`, ctypes
    # tratta il valore di ritorno di `GetCurrentProcess` come intero a 32 bit,
    # mentre un HANDLE ne occupa 64. L'API riceve un handle troncato, risponde
    # zero, e la misura risulta «non disponibile su questa piattaforma» —
    # esattamente quello che e' successo alla prima esecuzione, con la
    # conclusione sbagliata che Windows non la offrisse.
    processo_corrente = windll.kernel32.GetCurrentProcess
    processo_corrente.restype = ctypes.c_void_p
    processo_corrente.argtypes = []

    leggi_contatori = windll.psapi.GetProcessMemoryInfo
    leggi_contatori.restype = ctypes.c_int
    leggi_contatori.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_ContatoriMemoria),
        ctypes.c_ulong,
    ]

    contatori = _ContatoriMemoria()
    contatori.cb = ctypes.sizeof(_ContatoriMemoria)
    riuscito = leggi_contatori(processo_corrente(), ctypes.byref(contatori), contatori.cb)
    return float(contatori.WorkingSetSize) / 1024**2 if riuscito else None


def in_memoria_mb(tabella: pd.DataFrame) -> float:
    """Quanto occupa una tabella in memoria, stringhe comprese.

    ``deep=True`` non e' un dettaglio: senza, le colonne di testo vengono
    contate come puntatori e una tabella di nomi di giocatori sembra pesare
    dieci volte meno di quanto pesa.

    Args:
        tabella: La tabella da pesare.

    Returns:
        I megabyte occupati.
    """
    return float(tabella.memory_usage(deep=True).sum()) / 1024**2


def su_disco_mb(nome: str) -> float:
    """Quanto occupa il Parquet corrispondente.

    Args:
        nome: Il nome della tabella, senza estensione.

    Returns:
        I megabyte del file.
    """
    return (DATA_PROCESSED / f"{nome}.parquet").stat().st_size / 1024**2


def riga(voci: tuple[str, ...], larghezze: tuple[int, ...]) -> str:
    """Formatta una riga della tabella di uscita.

    Args:
        voci: I valori gia' convertiti in testo.
        larghezze: La larghezza di ogni colonna.

    Returns:
        La riga allineata.
    """
    coppie = list(zip(voci, larghezze, strict=True))
    testa, larga = coppie[0]
    return "  ".join([testa.ljust(larga), *(voce.rjust(largo) for voce, largo in coppie[1:])])


def main() -> int:
    """Misura e stampa, e dice se il criterio di M7-T5 e' soddisfatto.

    Returns:
        Zero se il totale sta sotto il tetto, uno altrimenti — cosi' il
        comando si puo' mettere in uno script senza leggerne l'uscita.
    """
    base = residente_mb()
    if base is None:
        print(f"Memoria residente non leggibile su {sys.platform}: misuro solo le tabelle.\n")
    else:
        print(f"Base: {base:.0f} MB con le librerie importate, prima di leggere i dati.\n")

    larghezze = (16, 10, 12, 12, 8)
    print(riga(("Tabella", "Righe", "Su disco", "In memoria", "Rapporto"), larghezze))
    print("-" * (sum(larghezze) + 8))

    magazzino: dict[str, pd.DataFrame] = {}
    totale_disco = totale_memoria = 0.0
    for nome in TABELLE:
        tabella = pd.read_parquet(DATA_PROCESSED / f"{nome}.parquet")
        magazzino[nome] = tabella
        disco, memoria = su_disco_mb(nome), in_memoria_mb(tabella)
        totale_disco += disco
        totale_memoria += memoria
        print(
            riga(
                (
                    nome,
                    f"{len(tabella):,}".replace(",", "."),
                    f"{disco:.1f} MB",
                    f"{memoria:.1f} MB",
                    f"{memoria / disco:.1f}×" if disco else "—",
                ),
                larghezze,
            )
        )

    print("-" * (sum(larghezze) + 8))
    print(
        riga(
            (
                "totale",
                "",
                f"{totale_disco:.1f} MB",
                f"{totale_memoria:.1f} MB",
                f"{totale_memoria / totale_disco:.1f}×",
            ),
            larghezze,
        )
    )

    dopo_lettura = residente_mb()
    if dopo_lettura is not None:
        print(f"\nCon il magazzino in memoria: {dopo_lettura:.0f} MB.")

    # Il picco: l'aggregazione piu' pesante su tutte le competizioni insieme,
    # che e' la selezione predefinita della Home e quindi il caso peggiore.
    tiri, partite = magazzino["shots"], magazzino["matches"]
    panoramica.per_squadra(tiri)
    panoramica.per_zona(tiri)
    classifica.tabella(partite, tiri)

    picco = residente_mb()
    if picco is not None:
        print(f"Durante le aggregazioni piu' pesanti: {picco:.0f} MB.")
        print(f"Tetto di Streamlit Community Cloud: {TETTO_MB:.0f} MB.")
        margine = TETTO_MB - picco
        print(f"\n{'✓' if margine > 0 else '✗'} Margine: {margine:.0f} MB.")
        return 0 if margine > 0 else 1

    print("\nSenza la memoria residente il criterio va verificato sul processo vero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
