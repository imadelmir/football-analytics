"""La pagina Metodologia non può citare prove che non esistono (M6-T11).

**Il primo test di questo file e' il piu' importante di tutto il progetto**, e
non perche' verifichi un calcolo difficile: verifica che le affermazioni della
vista Metodologia siano controllabili. Quella pagina trae la propria
credibilita' dal nominare il test che regge ogni verifica; se uno di quei test
venisse rinominato o cancellato, la pagina continuerebbe a citarlo e nessuno se
ne accorgerebbe guardandola.

Un progetto che si presenta come rigoroso e che pubblicizza prove inesistenti
non e' incompleto: e' peggio di uno che non dichiara niente.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import metodo
from football_analytics.config import DATA_PROCESSED

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "matches.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)

#: Il tetto per file che il progetto si e' dato, in megabyte.
TETTO_MB = 50.0

#: Quante tabelle deve avere il magazzino.
QUANTE_TABELLE = 6


def test_ogni_verifica_citata_esiste_davvero() -> None:
    """Il test del test: nessun riferimento orfano fra quelli mostrati in pagina.

    Gira **senza magazzino**, perche' legge i file della suite e non i dati:
    vale anche in CI, dove i Parquet non ci sono ancora.
    """
    orfane = metodo.verifiche_orfane()

    assert orfane == [], f"la vista Metodologia cita test che non esistono: {orfane}"


def test_i_riferimenti_sono_nella_forma_che_pytest_accetta() -> None:
    """Si devono poter copiare dietro a ``pytest`` senza aggiustarli.

    E' il motivo per cui in pagina sono monospaziati: sono comandi, non
    decorazione. Un riferimento con la barra rovescia di Windows o senza il
    doppio due punti non funzionerebbe incollato.
    """
    for prova in metodo.VERIFICHE:
        percorso, separatore, funzione = prova.test.partition("::")

        assert separatore == "::", prova.test
        assert percorso.startswith("tests/"), prova.test
        assert "\\" not in prova.test, prova.test
        assert funzione.startswith("test_"), prova.test


def test_nessuna_verifica_e_citata_due_volte() -> None:
    """Due voci diverse rette dallo stesso test sono una prova sola travestita."""
    citati = [prova.test for prova in metodo.VERIFICHE]

    assert len(set(citati)) == len(citati), "un test regge piu' di una verifica"


def test_gli_elenchi_non_sono_vuoti_e_hanno_tutti_i_campi() -> None:
    """Una pagina sulla metodologia con un elenco vuoto e' una pagina che mente."""
    assert metodo.ANELLI
    assert metodo.VERIFICHE
    assert metodo.LIMITI

    for anello in metodo.ANELLI:
        assert anello.nome and anello.dove and anello.cosa
    for prova in metodo.VERIFICHE:
        assert prova.cosa and prova.esito and prova.test
    for limite in metodo.LIMITI:
        assert limite.titolo and limite.conseguenza, limite.titolo


def test_ogni_limite_dice_anche_la_conseguenza() -> None:
    """Dichiarare un limite senza dire cosa comporta non serve a chi legge.

    «La Ligue 1 ha 377 partite» e' un fatto; «per questo nessun numero e' un
    totale» e' cio' che permette di leggere la dashboard senza sbagliare.
    """
    minimo = 40
    for limite in metodo.LIMITI:
        assert len(limite.conseguenza) > minimo, limite.titolo


@senza_magazzino
def test_il_magazzino_ha_le_sei_tabelle_e_sta_nel_tetto() -> None:
    """Sei Parquet, tutti sotto il limite che il progetto si e' dato.

    Il tetto non e' un vincolo di Streamlit Cloud ma una regola del piano: git
    dei binari non sa fare diff e ne conserva ogni versione per intero.
    """
    tabelle = metodo.magazzino()

    assert len(tabelle) == QUANTE_TABELLE
    assert set(tabelle["tabella"]) == {
        "matches",
        "shots",
        "passes",
        "touches",
        "player_stats",
        "freeze_frames",
    }
    assert tabelle["megabyte"].max() < TETTO_MB
    assert (tabelle["righe"] > 0).all()


@senza_magazzino
def test_le_righe_dichiarate_sono_quelle_vere() -> None:
    """I metadati Parquet devono dire il vero, o la pagina mostra numeri finti.

    Leggere i metadati invece dei dati e' un'ottimizzazione — evita di aprire
    1,2 milioni di righe a ogni caricamento — e come ogni ottimizzazione va
    verificata almeno una volta contro la strada lenta.
    """
    tabelle = metodo.magazzino()
    vere = pd.read_parquet(DATA_PROCESSED / "matches.parquet")

    # Un dizionario e non `.loc[riga, colonna]`: per pandas-stubs quella cella
    # ha un tipo unione che comprende date e stringhe, e `int()` non la accetta.
    righe = dict(zip(tabelle["tabella"], tabelle["righe"].to_numpy(), strict=True))
    colonne = dict(zip(tabelle["tabella"], tabelle["colonne"].to_numpy(), strict=True))

    assert int(righe["matches"]) == len(vere)
    assert int(colonne["matches"]) == len(vere.columns)


@senza_magazzino
def test_le_partite_del_magazzino_tornano_con_quelle_del_modello() -> None:
    """L'aritmetica che chiude: addestramento + verifica + finali = tutto.

    Se non tornasse, vorrebbe dire che qualche partita e' stata contata due
    volte o persa per strada fra la trasformazione e l'addestramento — e
    nessuna delle due cose si vedrebbe guardando una vista.
    """
    from football_analytics import rendiconto  # noqa: PLC0415

    contesto = rendiconto.contesto()
    partite = pd.read_parquet(DATA_PROCESSED / "matches.parquet")

    somma = contesto.partite_train + contesto.partite_test + contesto.finali_applicazione

    assert somma == len(partite), (
        f"{contesto.partite_train} + {contesto.partite_test} + "
        f"{contesto.finali_applicazione} != {len(partite)}"
    )


def test_senza_magazzino_la_tabella_ha_comunque_le_colonne(tmp_path: object) -> None:
    """Chi disegna la pagina deve trovare le colonne anche su una copia vuota."""
    import football_analytics.config as configurazione  # noqa: PLC0415

    vera = configurazione.DATA_PROCESSED
    try:
        configurazione.DATA_PROCESSED = tmp_path  # type: ignore[misc, assignment]
        tabelle = metodo.magazzino()
    finally:
        configurazione.DATA_PROCESSED = vera  # type: ignore[misc]

    assert tabelle.empty
    assert list(tabelle.columns) == ["tabella", "righe", "colonne", "megabyte"]
