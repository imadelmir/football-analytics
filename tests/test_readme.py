"""Il README non mente (M7-T4).

Il criterio della task e' che **chi arriva dal portfolio capisca il progetto in
trenta secondi**, e un criterio del genere non si verifica con un test: si
verifica facendolo leggere a qualcuno. Quello che invece un test puo' fare, ed
e' il motivo per cui questo file esiste, e' impedire che il README diventi
falso senza che nessuno se ne accorga.

Un documento e' l'unica parte di un progetto che non smette mai di compilare.
Il codice che dice una bugia si rompe; il README che dice «nove viste» quando
sono sette resta li' per mesi, ed e' la prima cosa che un lettore vede. Quando
questa riscrittura e' cominciata il README ne aveva cinque, di bugie — il
badge della CI puntava a **un altro repository**, i campionati erano contati
tre invece di quattro, lo stato era fermo a M5 e le viste erano nove.

Ognuno di quei cinque difetti ha qui il suo test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

import pytest

from football_analytics import config

#: Il documento sotto esame.
README: Final[Path] = config.PROJECT_ROOT / "README.md"

#: Il proprietario e il nome del repository, come stanno su GitHub.
#:
#: Scritti qui una volta e confrontati ovunque: il difetto originale era che
#: README e `pyproject.toml` contenevano lo stesso URL sbagliato in tre punti,
#: rimasto da un repository di prova dopo il cambio di nome dell'account.
PROPRIETARIO: Final[str] = "imadelmir"
REPOSITORY: Final[str] = f"https://github.com/{PROPRIETARIO}/football-analytics"

#: I file di testo che possono contenere l'URL del repository.
DOVE_COMPARE: Final[tuple[str, ...]] = ("README.md", "pyproject.toml")

#: I numeri scritti in lettere, per i confronti sulle quantita' dichiarate.
IN_LETTERE: Final[dict[int, str]] = {
    4: "Quattro",
    6: "Sei",
    7: "Sette",
    8: "Otto",
    9: "Nove",
    11: "Undici",
}


@pytest.fixture(scope="module")
def testo() -> str:
    """Il README, letto una volta sola.

    Returns:
        Il contenuto del file.
    """
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def misurati() -> dict[str, Any]:
    """I risultati generati da ``scripts/train_model.py``.

    Returns:
        Il contenuto di ``docs/milestones/M5-risultati.json``.
    """
    percorso = config.PROJECT_ROOT / "docs" / "milestones" / "M5-risultati.json"
    dati: dict[str, Any] = json.loads(percorso.read_text(encoding="utf-8"))
    return dati


def all_italiana(valore: float, cifre: int) -> str:
    """Formatta un numero come lo scrive il README.

    Args:
        valore: Il numero.
        cifre: Quante cifre dopo la virgola.

    Returns:
        Il numero con la virgola decimale.
    """
    return f"{valore:.{cifre}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 1. Il repository
# ---------------------------------------------------------------------------


def test_nessun_file_rimanda_a_un_altro_repository() -> None:
    """Il difetto piu' grave dei cinque, e il piu' facile da non vedere.

    Il badge della CI e' la **prima riga** che si vede aprendo il progetto da
    un portfolio, e puntava a `AVENA50/football-analytics`: un repository che
    non e' questo. Il badge mostrava quindi lo stato dei test di qualcun altro
    — o, piu' probabilmente, un'immagine spezzata.

    Il controllo e' su un URL costruito, non sul nome vecchio: cercare
    «AVENA50» proteggerebbe da un solo errore gia' commesso, mentre cosi'
    qualunque altro proprietario fa fallire il test.
    """
    sbagliati: list[str] = []
    for nome in DOVE_COMPARE:
        testo = (config.PROJECT_ROOT / nome).read_text(encoding="utf-8")
        for url in re.findall(r"https://github\.com/([\w.-]+)/football-analytics", testo):
            if url != PROPRIETARIO:
                sbagliati.append(f"{nome} → github.com/{url}/football-analytics")

    assert sbagliati == [], "rimandi a un altro repository:\n  " + "\n  ".join(sbagliati)


def test_il_readme_e_pyproject_dicono_lo_stesso_repository(testo: str) -> None:
    """I metadati del pacchetto e la pagina pubblica non possono divergere.

    Chi installa il pacchetto vede l'URL di `pyproject.toml`; chi apre GitHub
    vede quello del README. Se si separano, uno dei due porta nel posto
    sbagliato e nessuno se ne accorge finche' qualcuno non ci clicca.
    """
    pyproject = (config.PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert f'Repository = "{REPOSITORY}"' in pyproject
    assert f"{REPOSITORY}.git" in testo, "il comando di clone non nomina il repository giusto"
    assert f"{REPOSITORY}/actions" in testo, "il badge della CI non punta a questo repository"


# ---------------------------------------------------------------------------
# 2. I collegamenti
# ---------------------------------------------------------------------------


def test_ogni_collegamento_relativo_del_readme_esiste(testo: str) -> None:
    """Immagini e link a file, tutti insieme.

    `tests/test_impalcatura.py` fa la stessa cosa per le immagini dentro
    `docs/`, ma il README sta nella radice e restava fuori — e nella radice ci
    sono i rimandi che contano di piu', perche' li segue chi non conosce il
    progetto.

    Qui i link a file sono compresi, non solo le immagini: un rimando a una
    relazione di milestone che non esiste e' un vicolo cieco esattamente come
    un'immagine spezzata.
    """
    riferimenti = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", testo)
    rotti = [
        riferimento
        for riferimento in riferimenti
        if not riferimento.startswith(("http://", "https://", "#"))
        and not (README.parent / riferimento.split("#")[0]).exists()
    ]

    assert rotti == [], "collegamenti che non portano da nessuna parte:\n  " + "\n  ".join(rotti)


def test_il_readme_mostra_almeno_una_schermata(testo: str) -> None:
    """Il criterio nomina le schermate, e una sola non basta a rappresentarlo.

    Trenta secondi non bastano a leggere: bastano a **guardare**. Una vista
    della dashboard nella prima schermata dice cos'e' questo progetto piu' in
    fretta di qualunque paragrafo, e per questo il controllo pretende che
    l'immagine principale stia in alto e non in fondo alla pagina.
    """
    immagini = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", testo)
    schermate = [percorso for percorso in immagini if percorso.startswith("docs/immagini/")]

    assert len(schermate) >= 4, f"solo {len(schermate)} schermate: {schermate}"

    prima = testo.index(f"]({schermate[0]})")
    assert prima < len(testo) // 4, "la prima schermata arriva troppo in basso per servire"


# ---------------------------------------------------------------------------
# 3. Le quantita' dichiarate
# ---------------------------------------------------------------------------


def test_il_numero_di_viste_dichiarato_e_quello_del_menu(testo: str) -> None:
    """«Nove viste Streamlit» era falso da quando il menu ne ha sette.

    Il numero non si controlla a memoria: si prende da :data:`guscio.MENU`, che
    e' la sola definizione del menu. Aggiungere una vista fa fallire questo
    test, che e' il comportamento voluto — il README va aggiornato insieme.
    """
    import guscio  # noqa: PLC0415

    quante = len(guscio.MENU)

    assert f"{quante} viste" in testo, f"il menu ha {quante} viste e il README non lo dice"
    assert f"{IN_LETTERE[quante]} viste" in testo, "manca la forma in lettere"


def test_il_numero_di_competizioni_e_di_partite_e_quello_misurato(testo: str) -> None:
    """«Tre campionati» era falso: sono quattro, e le competizioni nove.

    I campionati e i tornei stanno in :mod:`football_analytics.config`, e le
    partite attese sono dichiarate una per competizione. Il totale del README
    deve essere la loro somma, non un numero ricordato.
    """
    from football_analytics.config import CAMPIONATI, COMPETIZIONI  # noqa: PLC0415

    partite = sum(voce.partite_attese for voce in COMPETIZIONI)

    assert f"{len(COMPETIZIONI)} competizioni" in testo
    assert f"{partite:,}".replace(",", ".") in testo, f"il totale delle partite e' {partite}"
    assert f"{IN_LETTERE[len(CAMPIONATI)]} campionati" in testo


def test_il_numero_di_limiti_e_quello_dichiarato_in_pagina(testo: str) -> None:
    """Gli undici limiti sono scritti in un posto solo, e il README li conta.

    Il criterio della task nomina i limiti fra le sei cose che devono esserci.
    Dichiararne un numero diverso da quello che la dashboard mostra sarebbe il
    modo piu' silenzioso di renderne alcuni invisibili.
    """
    from football_analytics import metodo  # noqa: PLC0415

    quanti = len(metodo.LIMITI)
    assert IN_LETTERE[quanti].lower() in testo.lower(), f"i limiti dichiarati sono {quanti}"


# ---------------------------------------------------------------------------
# 4. I numeri del modello
# ---------------------------------------------------------------------------


def test_i_punteggi_del_modello_vengono_dal_file_generato(
    testo: str, misurati: dict[str, Any]
) -> None:
    """Ogni cifra della tabella si ritrova in ``M5-risultati.json``.

    E' il test che nessun altro sostituisce. La tabella del README e' scritta a
    mano — Markdown non si genera da solo — e un Brier score ricopiato male, o
    rimasto da prima che le finali uscissero dal campione, sarebbe invisibile a
    qualunque controllo sulla forma.
    """
    confronto = misurati["confronto"]

    mancanti: list[str] = []
    for chiave in ("riferimento", "logistica base", "logistica spaziale", "StatsBomb"):
        voce = confronto[chiave]
        for atteso in (
            all_italiana(voce["brier"], 5),
            all_italiana(voce["auc"], 3),
            f"{all_italiana(voce['guadagno_brier'] * 100, 1)} %",
        ):
            if atteso not in testo:
                mancanti.append(f"{chiave}: {atteso}")

    assert mancanti == [], "numeri non presenti o diversi da quelli misurati:\n  " + "\n  ".join(
        mancanti
    )


def test_il_guadagno_dichiarato_e_una_sottrazione_vera(
    testo: str, misurati: dict[str, Any]
) -> None:
    """«+2,9 punti» e «62 %» sono numeri derivati, e i derivati si sbagliano.

    Nessuno script li stampa: nascono da una sottrazione e da una divisione
    fatte a mano fra i punteggi della tabella. Rifarle qui costa tre righe e
    toglie l'unico posto del README dove un errore di aritmetica potrebbe
    passare inosservato.
    """
    confronto = misurati["confronto"]
    base = confronto["logistica base"]["guadagno_brier"] * 100
    spaziale = confronto["logistica spaziale"]["guadagno_brier"] * 100
    altrui = confronto["StatsBomb"]["guadagno_brier"] * 100

    punti = spaziale - base
    quota = (spaziale - base) / (altrui - base) * 100

    assert f"+{all_italiana(punti, 1)} punti" in testo
    assert f"{quota:.0f} %" in testo, f"la quota del divario colmata e' {quota:.1f} %"


def test_i_numeri_fuori_campione_sono_quelli_delle_finali(
    testo: str, misurati: dict[str, Any]
) -> None:
    """La tenuta fuori campione e' meta' della risposta, e va misurata.

    Un guadagno che vale solo sull'insieme di verifica non dimostra niente: le
    partite di verifica vengono dalle stesse competizioni dell'addestramento.
    Le finali di Champions sono di altre epoche e altre squadre, e sono escluse
    da entrambi — il numero che ne esce e' l'unico che parla di generalizzazione.
    """
    fuori = misurati["fuori_campione"]

    for chiave in ("logistica base", "logistica spaziale"):
        atteso = f"{all_italiana(fuori[chiave]['guadagno_brier'] * 100, 1)} %"
        assert atteso in testo, f"{chiave} fuori campione: manca {atteso}"


def test_la_divisione_dei_dati_e_dichiarata_con_i_numeri_giusti(
    testo: str, misurati: dict[str, Any]
) -> None:
    """Quante partite in addestramento, quante in verifica, quante fuori.

    E' la parte del README che un lettore tecnico guarda per prima, perche'
    dice se il progetto ha evitato la trappola: dividere per tiro invece che
    per partita. I tre numeri vengono dal file generato.
    """
    contesto = misurati["contesto"]

    for chiave in ("tiri_train", "partite_train", "tiri_test", "partite_test"):
        atteso = f"{int(contesto[chiave]):,}".replace(",", ".")
        assert atteso in testo, f"{chiave} = {atteso} non compare"

    assert "per partita" in testo
    assert "accuratezza" in testo.lower(), "il README non dice perche' l'accuratezza non si usa"


# ---------------------------------------------------------------------------
# 5. Le sei cose che il criterio chiede
# ---------------------------------------------------------------------------


def test_il_readme_contiene_le_sei_cose_del_criterio(testo: str) -> None:
    """Il criterio di M7-T4, elencato e controllato voce per voce.

    «Cosa fa, come si esegue, i numeri del modello, le schermate,
    l'attribuzione, i limiti.» Sono sei, e questo test le cerca una a una.

    Non dimostra che si capisca in trenta secondi — quello lo dice solo chi
    legge. Dimostra che **nessuna delle sei e' stata persa** in una riscrittura
    successiva, che e' il modo tipico in cui un documento buono si guasta.
    """
    mancanti = [
        nome
        for nome, segno in (
            ("cosa fa", "expected goals"),
            ("come si esegue", "uv run streamlit run app/Panoramica.py"),
            ("i numeri del modello", "Brier"),
            ("le schermate", "docs/immagini/m6/"),
            ("l'attribuzione", "StatsBomb Open Data"),
            ("i limiti", "## I limiti"),
        )
        if segno not in testo
    ]

    assert mancanti == [], f"il criterio chiede anche: {', '.join(mancanti)}"


def test_lo_stato_dichiarato_e_quello_dell_indice_delle_milestone(testo: str) -> None:
    """«Stato: M5» e' rimasto scritto per due milestone intere.

    Lo stato del README si scrive a mano e nessuno lo rilegge: e' il campo che
    invecchia per primo. L'indice delle milestone, invece, si aggiorna a ogni
    chiusura perche' e' l'ultimo task di ogni milestone — quindi e' lui il
    riferimento, e il README deve concordarci.
    """
    indice = (config.PROJECT_ROOT / "docs" / "milestones" / "README.md").read_text(encoding="utf-8")
    concluse = re.findall(r"\| (M\d) \|[^|]*\|[^|]*\| 🟢", indice)
    assert concluse, "l'indice delle milestone non segna nessuna milestone conclusa"

    ultima = concluse[-1]
    assert f"{ultima} conclusa" in testo, f"l'indice dice che {ultima} e' chiusa, il README no"


def test_l_attribuzione_a_statsbomb_non_e_stata_alleggerita(testo: str) -> None:
    """La citazione della fonte e' una condizione di licenza.

    E' l'unica sezione del README che non si puo' accorciare per far posto ad
    altro: sta qui, nel piede di ogni pagina della dashboard e nella vista
    Metodologia, e a M7-T4 e' scesa sotto le schermate solo perche' il criterio
    chiede che il primo schermo spieghi il progetto. Scendere di posizione e'
    concesso; sparire no.
    """
    for obbligatorio in (
        "StatsBomb Open Data",
        "https://github.com/statsbomb/open-data",
        "condizione d'uso",
    ):
        assert obbligatorio in testo, f"manca dall'attribuzione: {obbligatorio}"
