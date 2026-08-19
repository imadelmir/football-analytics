"""Verifiche minime di M1: il pacchetto si importa e i percorsi sono coerenti.

Questi test non toccano la rete ne' i dati. Servono a dare a `pytest` qualcosa
da eseguire fin dal primo giorno: senza almeno un test, `pytest` esce con
codice 5 e la CI risulterebbe rossa su un repository perfettamente sano.
"""

from __future__ import annotations

import pytest

import football_analytics
from football_analytics import config


def test_il_pacchetto_si_importa() -> None:
    assert football_analytics.__version__ == "0.1.0"


def test_i_percorsi_sono_assoluti() -> None:
    for percorso in (
        config.PROJECT_ROOT,
        config.DATA_RAW,
        config.DATA_PROCESSED,
        config.MODELS_DIR,
    ):
        assert percorso.is_absolute()


def test_la_radice_contiene_pyproject() -> None:
    assert (config.PROJECT_ROOT / "pyproject.toml").is_file()


def test_percorso_tabella_costruisce_il_nome_giusto() -> None:
    atteso = config.DATA_PROCESSED / "shots.parquet"
    assert config.percorso_tabella("shots") == atteso


def test_percorso_tabella_rifiuta_una_tabella_inventata() -> None:
    with pytest.raises(ValueError, match="Tabella sconosciuta"):
        config.percorso_tabella("corner")


def test_assicura_cartelle_e_idempotente() -> None:
    config.assicura_cartelle()
    config.assicura_cartelle()
    assert config.DATA_RAW.is_dir()
    assert config.DATA_PROCESSED.is_dir()
    assert config.MODELS_DIR.is_dir()


def test_nessun_documento_rimanda_a_un_immagine_che_non_esiste() -> None:
    """Un collegamento rotto in una relazione di milestone non lo vede nessuno.

    Su GitHub un'immagine mancante compare come icona spezzata, e chi legge il
    documento pensa che il progetto sia trascurato — o peggio, che la vista
    descritta non esista. Il controllo e' generale e vale per tutte le
    milestone, presenti e future.

    **Per M6 e' anche il criterio della task.** M6-T14 chiede una schermata per
    vista: finche' le sette immagini non sono al loro posto, questo test e'
    rosso e la milestone non e' conclusa. E' voluto — un criterio che si puo'
    dichiarare soddisfatto senza che nulla lo controlli non e' un criterio.
    """
    import re  # noqa: PLC0415

    docs = config.PROJECT_ROOT / "docs"
    mancanti = []
    for documento in sorted(docs.rglob("*.md")):
        testo = documento.read_text(encoding="utf-8")
        for riferimento in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", testo):
            if riferimento.startswith(("http://", "https://")):
                continue
            if not (documento.parent / riferimento).resolve().exists():
                mancanti.append(f"{documento.relative_to(docs)} → {riferimento}")

    assert mancanti == [], "immagini citate e non presenti:\n  " + "\n  ".join(mancanti)


#: Le sei tabelle che un clone deve contenere, e il peso oltre il quale una di
#: esse smette di essere comoda in git.
#:
#: Cinquanta megabyte e' il limite che il progetto si e' dato a M3: sopra, un
#: binario che git non sa confrontare diventa un peso permanente nella
#: cronologia, perche' `main` e' protetto contro il force push.
TABELLE = ("matches", "shots", "passes", "touches", "player_stats", "freeze_frames")
TETTO_MB = 50.0

#: I due modelli che `scripts/train_model.py` produce.
MODELLI = ("xg_base", "xg_360")


def test_un_clone_pulito_contiene_il_magazzino() -> None:
    """Il criterio di M7-T1, e la rete che protegge gli altri ottantacinque test.

    Fino a M6 i Parquet erano fuori da git, e ottantacinque test si saltavano
    da soli con ``skipif``. Adesso i file ci sono e quei test girano — ma il
    marcatore e' rimasto, ed e' un'arma a doppio taglio: se un giorno il
    magazzino sparisse, quegli ottantacinque tornerebbero a **saltare in
    silenzio** e la CI resterebbe verde su un progetto che non funziona.

    Questo test toglie il silenzio. Non si salta mai: se le tabelle non ci
    sono, e' rosso.
    """
    mancanti = [
        nome for nome in TABELLE if not (config.DATA_PROCESSED / f"{nome}.parquet").exists()
    ]

    assert mancanti == [], (
        f"il magazzino e' incompleto: {mancanti}. "
        "Ricostruiscilo con `uv run python scripts/build_dataset.py`."
    )


def test_i_modelli_addestrati_sono_nel_repository() -> None:
    """Le due schede JSON servono alla vista Modello, i pickle a chi riusa.

    La dashboard **non carica nessun pickle** — legge solo i JSON, perche' un
    `.pkl` e' Python serializzato e caricarlo esegue codice. I pickle stanno in
    git perche' chi clona possa ispezionare i modelli, e questo test verifica
    che ci siano entrambe le forme.
    """
    mancanti = [
        f"{nome}{estensione}"
        for nome in MODELLI
        for estensione in (".pkl", ".json")
        if not (config.MODELS_DIR / f"{nome}{estensione}").exists()
    ]

    assert mancanti == [], (
        f"mancano dei modelli: {mancanti}. Rigenerali con `uv run python -m scripts.train_model`."
    )


def test_nessun_file_del_magazzino_sfora_il_tetto() -> None:
    """Sopra i cinquanta megabyte un binario diventa un peso permanente.

    Git non sa fare diff dei binari: ogni versione e' una copia intera, e da
    `main` non si toglie senza riscrivere la cronologia — che questo progetto
    ha deciso di non fare mai.
    """
    pesanti = {
        percorso.name: round(percorso.stat().st_size / 1024**2, 2)
        for percorso in config.DATA_PROCESSED.glob("*.parquet")
        if percorso.stat().st_size / 1024**2 > TETTO_MB
    }

    assert pesanti == {}, f"oltre i {TETTO_MB} MB: {pesanti}"


def dipendenze_dichiarate() -> dict[str, str]:
    """Le dipendenze di produzione lette da ``pyproject.toml``.

    Returns:
        Il nome normalizzato di ogni pacchetto e la versione bloccata.
    """
    import tomllib  # noqa: PLC0415

    with (config.PROJECT_ROOT / "pyproject.toml").open("rb") as flusso:
        progetto = tomllib.load(flusso)

    fissate = {}
    for voce in progetto["project"]["dependencies"]:
        nome, _, versione = str(voce).partition("==")
        fissate[nome.strip().lower().replace("_", "-")] = versione.strip()
    return fissate


def test_requirements_esiste_e_non_diverge_da_pyproject() -> None:
    """Due elenchi di dipendenze sono due cose che possono divergere.

    ``pyproject.toml`` e' la fonte per chi sviluppa con ``uv``;
    ``requirements.txt`` serve a Streamlit Cloud, che ``pyproject.toml`` non lo
    legge, e a chiunque installi con ``pip``. Il secondo si **genera** dal
    primo:

        uv export --no-dev --no-hashes -o requirements.txt

    Rigenerarlo e' un comando; dimenticarsene e' una riga sola, e il risultato
    e' un'app pubblica che gira con una versione di pandas diversa da quella su
    cui i test sono verdi. Questo test lo impedisce.

    Il comando qui sopra e' cambiato a M7-T3: fino ad allora portava anche
    ``--no-emit-project``, e la conseguenza e' raccontata in
    :func:`test_requirements_installa_anche_il_pacchetto`.
    """
    requisiti = config.PROJECT_ROOT / "requirements.txt"

    assert requisiti.exists(), (
        "manca requirements.txt. Generalo con: uv export --no-dev --no-hashes -o requirements.txt"
    )

    esportate = {}
    for riga in requisiti.read_text(encoding="utf-8").splitlines():
        pulita = riga.split("#")[0].strip()
        if not pulita or pulita.startswith("-"):
            continue
        nome, _, resto = pulita.partition("==")
        esportate[nome.strip().lower().replace("_", "-")] = resto.split(";")[0].strip()

    discordanti = {
        nome: (attesa, esportate.get(nome, "assente"))
        for nome, attesa in dipendenze_dichiarate().items()
        if esportate.get(nome) != attesa
    }

    assert discordanti == {}, (
        f"pyproject.toml e requirements.txt non concordano: {discordanti}. "
        "Rigenera con `uv export --no-dev --no-hashes -o requirements.txt`."
    )


def test_requirements_installa_anche_il_pacchetto() -> None:
    """Il difetto che avrebbe fatto fallire il primo avvio pubblico (M7-T3).

    In locale il pacchetto lo installa ``uv sync`` e nessuno ci pensa piu'. Su
    Streamlit Cloud gira **solo** ``pip install -r requirements.txt``: il
    codice sta in ``src/``, e senza una riga che lo dichiari nessuno mette
    ``football_analytics`` su ``sys.path``.

    Il test lega i due fatti invece di controllarne uno solo. Se le pagine
    importano il pacchetto, allora ``requirements.txt`` deve installarlo — e
    finche' l'implicazione e' scritta qui, chi domani rigenerasse il file con
    ``--no-emit-project`` lo scoprirebbe dalla CI e non dalla schermata rossa
    di un'app pubblica.

    A M7-T2 quel flag c'era, con una ragione che sembrava buona: un pacchetto
    che non sta su PyPI non e' una dipendenza. Ma ``pip`` sa installarlo da
    ``.``, e senza quella riga tredici file su tredici non partono.
    """
    app = config.PROJECT_ROOT / "app"
    importano = sorted(
        percorso.relative_to(app).as_posix()
        for percorso in app.rglob("*.py")
        if "football_analytics" in percorso.read_text(encoding="utf-8")
    )
    if not importano:
        pytest.skip("nessuna pagina importa il pacchetto: la riga non servirebbe")

    requisiti = config.PROJECT_ROOT / "requirements.txt"
    righe = [riga.strip() for riga in requisiti.read_text(encoding="utf-8").splitlines()]

    assert "-e ." in righe or "." in righe, (
        f"{len(importano)} file di app/ importano football_analytics, ma requirements.txt "
        "non lo installa. Rigenera con `uv export --no-dev --no-hashes -o requirements.txt`."
    )

    assoluti = [riga for riga in righe if "file:///" in riga]
    assert assoluti == [], f"percorsi della macchina di sviluppo in requirements.txt: {assoluti}"


def test_il_diario_ha_un_annotazione_per_ogni_milestone_conclusa() -> None:
    """Il criterio di M7-T6, verificato invece che dichiarato.

    ``NOTES.md`` diventa la sezione «learnings» del case study, ed e' la parte
    che distingue un case study da una brochure. Una milestone senza
    annotazioni non vuol dire che sia filata liscia: vuol dire che nessuno ha
    scritto cosa e' andato storto, e chi legge non puo' distinguere i due casi.

    La lista delle milestone non e' scritta qui: si ricava dall'indice in
    ``docs/milestones/README.md``, che si aggiorna a ogni chiusura perche' e'
    l'ultimo task di ognuna. Chiudere M8 senza annotarne gli inciampi fara'
    fallire questo test senza che nessuno debba ricordarsene.
    """
    import re  # noqa: PLC0415

    milestone = config.PROJECT_ROOT / "docs" / "milestones" / "README.md"
    concluse = re.findall(r"\| (M\d) \|[^|]*\|[^|]*\| 🟢", milestone.read_text(encoding="utf-8"))
    assert concluse, "l'indice non segna nessuna milestone conclusa"

    diario = (config.PROJECT_ROOT / "NOTES.md").read_text(encoding="utf-8")
    sezioni = re.split(r"^## ", diario, flags=re.MULTILINE)[1:]
    annotazioni = {blocco.split(" ", 1)[0].strip(): blocco.count("\n### ") for blocco in sezioni}

    mute = [nome for nome in [*concluse, "M7"] if annotazioni.get(nome, 0) == 0]

    assert mute == [], f"milestone senza annotazioni in NOTES.md: {mute}. Trovate: {annotazioni}"


def test_requirements_non_porta_dentro_gli_strumenti_di_sviluppo() -> None:
    """Streamlit Cloud non ha bisogno di jupyterlab, mypy e pytest.

    Sono decine di megabyte e minuti di installazione a ogni avvio, per far
    girare un'app che non li usa. L'``--no-dev`` dell'export serve a questo, e
    qui si verifica che ci fosse.
    """
    requisiti = config.PROJECT_ROOT / "requirements.txt"
    if not requisiti.exists():
        pytest.skip("requirements.txt non ancora generato")

    testo = requisiti.read_text(encoding="utf-8").lower()
    intrusi = [nome for nome in ("jupyterlab", "mypy", "pytest", "ruff") if nome in testo]

    assert intrusi == [], f"strumenti di sviluppo in requirements.txt: {intrusi}"
