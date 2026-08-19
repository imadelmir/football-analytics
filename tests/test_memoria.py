"""Il magazzino sta in memoria (M7-T5).

Il criterio della task e' che **con tutte le viste aperte l'app resti sotto il
gigabyte**. Streamlit Cloud non espone un contatore: se lo si supera il
processo viene ucciso e nei log resta una disconnessione, senza spiegazione.

Un test non puo' riprodurre l'app in esecuzione su Cloud, e non prova a farlo.
Quello che puo' fare, ed e' la parte che invecchia, e' sorvegliare **il costo
fisso**: le sei tabelle che ``dati.leggi`` tiene in cache per tutta la sessione
sono l'unica cosa che resta in memoria fra un'interazione e l'altra. Le
aggregazioni delle viste sono transitorie — Streamlit riesegue lo script da
capo a ogni click — e infatti misurate spostano il processo di due megabyte.

**Le soglie sono derivate da una misura, non scelte tonde.** A M7-T5 il
magazzino occupava 49,6 MB, con ``freeze_frames`` a 33,8 MB. I tetti qui sotto
stanno a circa il doppio: abbastanza larghi da non fallire per una riga in piu'
o per una versione diversa di pandas, abbastanza stretti da accorgersi di una
colonna nuova su una tabella da mezzo milione di righe.

Il numero completo — base, magazzino, picco, margine — si rigenera con::

    uv run python scripts/misura_memoria.py
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics.config import DATA_PROCESSED
from misura_memoria import TABELLE, in_memoria_mb, residente_mb

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "shots.parquet").exists(),
    reason="il magazzino non e' costruito",
)

#: Quanto puo' occupare l'intero magazzino letto in memoria, in megabyte.
TETTO_MAGAZZINO_MB: float = 100.0

#: Quanto puo' occupare la piu' grande delle sei tabelle.
#:
#: E' `freeze_frames`, e a M7-T5 vale il 68 % del totale: 562.105 righe con le
#: posizioni dei giocatori al momento di ogni tiro. Se il margine su Cloud si
#: stringesse un giorno, e' da questa tabella che si comincia.
TETTO_TABELLA_MB: float = 70.0


@senza_magazzino
def test_il_magazzino_letto_sta_nel_suo_budget() -> None:
    """Le sei tabelle insieme, che sono il costo fisso di una sessione.

    Il confronto e' con i megabyte in memoria e non con quelli su disco: i
    Parquet pesano 6,3 MB e ne occupano 49,6 una volta letti, un fattore quasi
    otto. Guardare il peso dei file darebbe una tranquillita' non giustificata.
    """
    pesi = {
        nome: in_memoria_mb(pd.read_parquet(DATA_PROCESSED / f"{nome}.parquet")) for nome in TABELLE
    }
    totale = sum(pesi.values())

    dettaglio = ", ".join(f"{nome} {peso:.1f} MB" for nome, peso in pesi.items())
    assert totale < TETTO_MAGAZZINO_MB, (
        f"il magazzino occupa {totale:.1f} MB in memoria, oltre il tetto di "
        f"{TETTO_MAGAZZINO_MB:.0f} MB. Dettaglio: {dettaglio}"
    )


@senza_magazzino
def test_nessuna_tabella_da_sola_domina_la_memoria() -> None:
    """Una sola tabella non deve mangiarsi il budget delle altre cinque.

    Il tetto per tabella esiste perche' il totale da solo nasconderebbe il caso
    che conta: una tabella che raddoppia mentre le altre calano lascerebbe la
    somma quasi ferma, e sarebbe comunque il momento in cui una lettura
    comincia a costare secondi invece che millisecondi.
    """
    sforati = {
        nome: peso
        for nome in TABELLE
        if (peso := in_memoria_mb(pd.read_parquet(DATA_PROCESSED / f"{nome}.parquet")))
        > TETTO_TABELLA_MB
    }

    assert sforati == {}, f"tabelle oltre {TETTO_TABELLA_MB:.0f} MB: {sforati}"


def test_il_peso_in_memoria_guarda_dentro_le_colonne_object() -> None:
    """``deep=True`` conta, ma non piu' dove ci si aspetterebbe.

    La prima versione di questo test costruiva una colonna di testo normale e
    pretendeva che la misura profonda fosse molto piu' grande di quella
    superficiale. **Ha fallito con i due numeri identici**, ed e' stato
    istruttivo: da pandas 3.0 il tipo predefinito delle stringhe non e' piu'
    ``object`` con puntatori a oggetti Python sparsi, ma una colonna nativa
    supportata da Arrow, contigua. Non c'e' niente da inseguire fuori
    dall'array, quindi le due misure coincidono.

    Il secondo tentativo e' fallito a sua volta, e vale la pena registrarlo:
    passare ``dtype=object`` al costruttore **non basta**. Con dentro delle
    stringhe, pandas 3 riconverte comunque al tipo nativo e il tipo richiesto
    viene ignorato. Per ottenere una colonna davvero ``object`` servono oggetti
    che non sappia rappresentare altrimenti.

    Qui sono liste, che e' la forma in cui i fotogrammi dei tiri arrivano nei
    JSON grezzi — ed e' anche il motivo per cui ``transform.py`` li appiattisce
    invece di conservarli: una colonna di liste da mezzo milione di righe
    costerebbe in memoria molto piu' delle colonne numeriche che la
    sostituiscono.

    Vale anche come nota sul magazzino: se i suoi 49,6 MB fossero misurati
    male, sarebbero misurati **in eccesso**, non in difetto.
    """
    posizioni = pd.DataFrame({"fotogramma": [[1.0, 2.0, 3.0] for _ in range(5_000)]})

    profondo = in_memoria_mb(posizioni)
    superficiale = float(posizioni.memory_usage(deep=False).sum()) / 1024**2

    assert posizioni["fotogramma"].dtype == object, "il test non guarda una colonna object"
    assert profondo > superficiale * 2, (
        f"su una colonna object la misura profonda deve essere molto maggiore: "
        f"{profondo:.3f} MB contro {superficiale:.3f} MB"
    )


def test_le_stringhe_native_di_pandas_3_non_hanno_peso_nascosto() -> None:
    """L'altra meta' del comportamento, fissata perche' non si perda.

    Le colonne di testo normali pesano uguale misurate in profondita' o in
    superficie. E' una buona notizia — meno memoria e nessuna sorpresa — ma va
    scritta: il giorno in cui il progetto girasse su una versione di pandas
    precedente, questo test fallirebbe e direbbe subito che le stime di memoria
    del magazzino vanno rifatte.
    """
    testi = pd.DataFrame({"nome": ["Gonzalo Higuaín con un nome molto lungo"] * 5_000})

    profondo = in_memoria_mb(testi)
    superficiale = float(testi.memory_usage(deep=False).sum()) / 1024**2

    assert testi["nome"].dtype != object, f"atteso il tipo nativo, trovato {testi['nome'].dtype}"
    assert profondo == pytest.approx(superficiale), (
        f"le stringhe native non dovrebbero avere peso nascosto: {profondo:.3f} MB "
        f"contro {superficiale:.3f} MB"
    )


def test_la_memoria_del_processo_si_legge_o_si_dichiara_assente() -> None:
    """Il misuratore non deve mai restituire un numero inventato.

    Su Linux legge ``/proc/self/status``, su Windows chiama ``psapi``. Se una
    delle due strade si rompesse, la risposta giusta e' ``None`` — che lo
    script stampa come «non leggibile» — e non uno zero che verrebbe
    interpretato come «l'app non occupa memoria».

    Alla prima esecuzione su Windows la funzione restituiva ``None`` per un
    difetto vero: ``GetCurrentProcess`` senza ``restype`` dichiarato consegna
    un handle troncato a 32 bit, e l'API rispondeva zero. La conclusione
    sbagliata sarebbe stata «Windows non offre la misura».
    """
    misura = residente_mb()

    assert misura is None or misura > 0.0, f"memoria residente non plausibile: {misura}"
    if misura is not None:
        assert misura > 10.0, (
            f"{misura:.1f} MB e' meno di quanto occupi un interprete Python "
            "con pandas importato: la lettura non sta misurando questo processo"
        )
