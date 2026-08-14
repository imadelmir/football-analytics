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
