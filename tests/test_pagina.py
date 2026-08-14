"""La pagina Streamlit viene **eseguita**, non solo importata (M6-T3).

Questo test esiste per un errore preciso: la Panoramica e' stata scritta,
riscritta tre volte e mostrata all'utente **senza essere mai eseguita**. I test
coprivano le funzioni sotto — aggregazioni, grafici, tema — ma nessuno faceva
girare la pagina, e un difetto nel modo in cui quelle funzioni vengono messe
insieme non sarebbe emerso finche' qualcuno non apriva il browser.

``AppTest`` esegue lo script Streamlit senza browser e senza server, e riporta
qualunque eccezione. Non verifica come appare la pagina — quello resta un
lavoro per gli occhi — ma verifica che appaia.

Il test si salta se il magazzino non e' stato costruito: i Parquet entrano in
git solo a M7-T1, quindi in CI non ci sono ancora.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from football_analytics.config import DATA_PROCESSED

#: La pagina da eseguire.
PAGINA: Path = Path(__file__).parents[1] / "app" / "Panoramica.py"

#: Quanti secondi concedere: la prima esecuzione legge tutti i Parquet.
ATTESA: int = 120

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "shots.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


@pytest.fixture(scope="module")
def eseguita() -> object:
    """Esegue la Panoramica una volta sola per tutto il modulo.

    Returns:
        L'applicazione dopo l'esecuzione.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    return app


@senza_magazzino
def test_la_pagina_gira_senza_eccezioni(eseguita: object) -> None:
    """Il test che sarebbe servito tre riscritture fa."""
    errori = [str(e.value) for e in eseguita.exception]  # type: ignore[attr-defined]

    assert not errori, f"la pagina ha sollevato: {errori}"


@senza_magazzino
def test_i_due_filtri_ci_sono_e_nascono_dal_magazzino(eseguita: object) -> None:
    """Due filtri, non tre: la stagione e' sparita perche' non poteva scegliere.

    Ogni competizione del magazzino ha una sola stagione, quindi il menu aveva
    sempre una voce sola. Il test controlla anche che le opzioni vengano dai
    dati e non da un elenco scritto a mano: aggiungere una competizione deve
    farla comparire da sola.
    """
    filtri = eseguita.selectbox  # type: ignore[attr-defined]

    assert [s.label for s in filtri] == ["Competizione", "Squadra"]
    assert len(filtri[0].options) == len(dati_competizioni())
    assert len(filtri[1].options) > 1


def dati_competizioni() -> list[str]:
    """Le competizioni del magazzino, lette senza passare per l'app.

    Returns:
        Le chiavi delle competizioni.
    """
    import pandas as pd  # noqa: PLC0415

    return sorted(pd.read_parquet(DATA_PROCESSED / "matches.parquet")["competizione"].unique())


@senza_magazzino
def test_ci_sono_i_quattro_grafici_previsti(eseguita: object) -> None:
    # Mappa dei tiri, andamento, anello dell'xG realizzato, distribuzione.
    assert len(eseguita.get("plotly_chart")) == 4  # type: ignore[attr-defined]


@senza_magazzino
def test_cambiare_competizione_non_rompe_la_pagina(eseguita: object) -> None:
    """Il filtro si muove davvero, e la pagina regge il rerun.

    E' il momento in cui Streamlit riesegue tutto lo script da capo: se una
    funzione dipendesse da uno stato lasciato dal giro precedente, e' qui che
    salterebbe fuori.
    """
    app = eseguita
    filtro = app.selectbox[0]  # type: ignore[attr-defined]
    seconda = filtro.options[1]

    filtro.set_value(seconda).run()

    assert not app.exception, f"cambiando competizione: {[str(e.value) for e in app.exception]}"  # type: ignore[attr-defined]


def test_la_pagina_non_usa_piu_use_container_width() -> None:
    """``use_container_width`` e' scaduto il 31 dicembre 2025.

    Legge il sorgente, quindi gira anche senza magazzino: e' un controllo sul
    codice, non sul comportamento.

    Streamlit lo accetta ancora per compatibilita' ma lo segnala a ogni
    chiamata. Un avviso ignorato e' un errore rimandato: il test lo trasforma
    in un fallimento adesso, invece che in una pagina rotta al prossimo
    aggiornamento.
    """
    sorgente = PAGINA.read_text(encoding="utf-8")

    assert "use_container_width" not in sorgente


@senza_magazzino
def test_scegliere_un_campionato_ricolora_la_pagina() -> None:
    """Il tema segue davvero il filtro, fino al foglio di stile iniettato.

    E' la verifica che manca a :mod:`tests.test_tema`: li' si controlla che
    ``per_competizione`` restituisca il tema giusto, che e' vero anche se
    nessuno chiama quella funzione. Qui si muove il filtro vero e si legge il
    CSS che finisce nella pagina.

    Il confronto e' sul fondo, non sull'accento: il fondo e' l'unica cosa che
    cambia in **tutta** la finestra, ed e' quello che si nota.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    from football_analytics import tema  # noqa: PLC0415

    attesi = {
        "premier_2015_16": tema.PREMIER,
        "la_liga_2015_16": tema.LIGA,
        "serie_a_2015_16": tema.SERIE_A,
        "ligue1_2015_16": tema.LIGUE1,
        "champions_finali": tema.BLU,
        "euro_2024": tema.EUROPEI,
        "mondiali_2022": tema.MONDIALI,
        "coppa_africa_2023": tema.COPPA_AFRICA,
    }

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()

    # ``options`` restituisce le etichette gia' passate per ``format_func``,
    # mentre ``set_value`` vuole il valore grezzo. Iterare sulle opzioni
    # sembrava naturale e non selezionava niente: il ciclo girava, nessun
    # confronto veniva eseguito e il test passava. Le chiavi stanno qui sotto
    # proprio per non ripescarle da li'.
    for chiave, scelto in attesi.items():
        app.selectbox[0].set_value(chiave).run()

        assert not app.exception, f"{chiave}: {[str(e.value) for e in app.exception]}"
        fogli = [str(m.value) for m in app.markdown if "--st-sfondo" in str(m.value)]
        assert len(fogli) == 1, f"{chiave}: fogli di stile trovati {len(fogli)}"
        assert f"--st-sfondo: {scelto.sfondo};" in fogli[0], chiave
        assert scelto.striscia[0] in fogli[0], f"fascia mancante: {chiave}"


@senza_magazzino
def test_cambiare_competizione_azzera_una_squadra_che_non_esiste_piu() -> None:
    """Il caso che rompe i filtri a cascata.

    Si sceglie il Real Madrid nella Liga e poi si passa alla Premier: la
    squadra selezionata non e' piu' fra le opzioni. Streamlit riporta il
    filtro a vuoto invece di sollevare, e la pagina mostra tutta la Premier —
    ma e' un comportamento su cui il codice fa affidamento senza dirlo, quindi
    vale la pena inchiodarlo.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.selectbox[0].set_value("la_liga_2015_16").run()
    app.selectbox[1].set_value("Real Madrid").run()
    assert app.selectbox[1].value == "Real Madrid"

    app.selectbox[0].set_value("premier_2015_16").run()

    assert not app.exception, [str(e.value) for e in app.exception]
    assert app.selectbox[1].value is None
    assert "Real Madrid" not in app.selectbox[1].options


# ---------------------------------------------------------------------------
# La vista Squadre (M6-T4)
# ---------------------------------------------------------------------------


def squadre_aperta() -> object:
    """Apre la Panoramica e passa alla vista Squadre.

    **Non si puo' aprire ``pages/Squadre.py`` direttamente.** ``st.page_link``
    ha bisogno del contesto multipagina, che esiste solo se l'app parte dallo
    script principale: eseguendo la pagina da sola solleva ``KeyError:
    'url_pathname'``, che non e' un difetto della pagina ma del modo di
    provarla.

    Returns:
        L'applicazione sulla vista Squadre.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Squadre.py")
    app.run()
    return app


def scegli_competizione(app: object, chiave: str) -> None:
    """Apre una competizione dai riquadri della vista Squadre.

    Senza una competizione scelta la pagina mostra solo i riquadri: le squadre
    di tutto il magazzino in una tabella sola non sono la classifica di niente,
    e le prime righe metterebbero a confronto la Liga e i Mondiali.

    Args:
        app: L'applicazione sulla vista Squadre.
        chiave: La chiave della competizione.
    """
    app.button(key=f"apri_{chiave}").click().run()  # type: ignore[attr-defined]


@senza_magazzino
def test_la_vista_squadre_si_apre_sui_riquadri() -> None:
    """All'apertura ci sono le competizioni, non una tabella.

    La tabella stava in cima e mostrava tutto il magazzino mescolato: una
    classifica in cui il Barcellona e la nazionale del Qatar stanno nella
    stessa colonna non e' la classifica di niente.
    """
    app = squadre_aperta()

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.dataframe) == 0  # type: ignore[attr-defined]
    for chiave in dati_competizioni():
        assert app.button(key=f"apri_{chiave}") is not None, chiave  # type: ignore[attr-defined]


@senza_magazzino
def test_la_classifica_della_liga_e_quella_vera() -> None:
    """Gli stessi numeri di ``test_classifica``, ma passando dall'interfaccia.

    Serve a coprire il tratto che i test del modulo non toccano: il filtro che
    seleziona la competizione, il passaggio della tabella a ``st.dataframe`` e
    la scelta delle colonne. Un errore li' darebbe una classifica giusta
    calcolata e sbagliata mostrata.
    """
    app = squadre_aperta()

    scegli_competizione(app, "la_liga_2015_16")

    tavola = app.dataframe[0].value  # type: ignore[attr-defined]
    prima = tavola.iloc[0]
    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(tavola) == 20
    assert prima["squadra"] == "Barcelona"
    assert int(prima["punti"]) == 91
    assert "punti" in tavola.columns


@senza_magazzino
def test_le_finali_non_mostrano_una_classifica() -> None:
    # Diciotto partite in quarantotto anni non fanno un girone: i punti
    # sparirebbero dentro una tabella dall'aria autorevole.
    app = squadre_aperta()

    scegli_competizione(app, "champions_finali")

    colonne = list(app.dataframe[0].value.columns)  # type: ignore[attr-defined]
    assert "punti" not in colonne
    assert "differenza_xg" in colonne


@senza_magazzino
def test_la_ligue_1_avvisa_che_mancano_partite() -> None:
    """Il buco nei dati arriva fino a chi guarda.

    Il modulo sa che sei squadre hanno giocato meno delle altre; questo test
    verifica che la pagina lo dica invece di mostrare 93 punti come se fossero
    quelli ufficiali.
    """
    app = squadre_aperta()

    scegli_competizione(app, "ligue1_2015_16")

    # L'avviso e' un pannello richiudibile in fondo, non piu' un riquadro
    # giallo in cima: con «Tutte le competizioni» elencava centocinquanta
    # nomi e occupava mezzo schermo prima ancora della tabella.
    testi = [str(e.label) for e in app.expander]  # type: ignore[attr-defined]
    assert testi, "nessun avviso sulle partite mancanti"
    assert "6 squadre" in testi[0]


@senza_magazzino
def test_la_scheda_della_squadra_mostra_tutti_i_riquadri() -> None:
    """I riquadri del disegno ci sono, e i numeri sono quelli veri.

    La scheda e' una pagina a se': sotto la classifica costringeva a scorrere
    mezzo schermo per leggerla e altrettanto per tornare al confronto.
    """
    app = squadre_aperta()
    scegli_competizione(app, "ligue1_2015_16")
    app.selectbox[0].set_value("Paris Saint-Germain").run()  # type: ignore[attr-defined]

    app.switch_page("pages/Scheda.py")  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.get("plotly_chart")) == 3  # type: ignore[attr-defined]
    scheda = [
        str(m.value)
        for m in app.markdown  # type: ignore[attr-defined]
        if "nome-squadra" in str(m.value) and "<style>" not in str(m.value)
    ]
    assert scheda, "la scheda della squadra non compare"
    testo = scheda[0]
    assert "Paris Saint-Germain" in testo
    assert "1° posto" in testo
    assert "93 punti" in testo
    assert "Gol fatti" in testo
    assert "xG concesso" in testo


@senza_magazzino
def test_la_classifica_non_disegna_grafici() -> None:
    """La vista Squadre e' un elenco, non un ritratto.

    I grafici stanno tutti nella scheda: se ne comparisse uno qui vorrebbe
    dire che la separazione fra le due pagine e' saltata.
    """
    app = squadre_aperta()
    scegli_competizione(app, "la_liga_2015_16")

    app.selectbox[0].set_value("Barcelona").run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.get("plotly_chart")) == 0  # type: ignore[attr-defined]
    assert len(app.dataframe) == 1  # type: ignore[attr-defined]
    etichetta = app.button(key="apri_scheda").label  # type: ignore[attr-defined]
    assert etichetta == "Apri la scheda completa · Barcelona"


@senza_magazzino
def test_dalla_home_si_salta_alla_scheda() -> None:
    """Il pulsante porta alla scheda con competizione e squadra gia' scelte.

    E' il primo stato condiviso fra due pagine del progetto, e ha due modi di
    rompersi che sembrano funzionare: il salto avviene ma la selezione non
    arriva, oppure arriva e non se ne va piu'. Il test copre entrambi.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.selectbox[0].set_value("la_liga_2015_16").run()
    app.selectbox[1].set_value("Barcelona").run()
    salto = app.button(key="vai_a_squadre")
    assert salto.label == "Apri la scheda di Barcelona"

    salto.click().run()

    assert not app.exception, [str(e.value) for e in app.exception]
    testo = " ".join(voce.value for voce in app.markdown)
    assert "Rete dei passaggi" in testo, "non siamo arrivati alla scheda"
    assert "Barcelona" in testo


@senza_magazzino
def test_la_consegna_si_consuma_dopo_il_salto() -> None:
    """La consegna sparisce appena usata, o resterebbe una scheda fantasma.

    Se restasse nello stato, ogni rerun della vista Squadre riaprirebbe la
    stessa squadra e il filtro sembrerebbe non rispondere.

    Il test si ferma qui e non prova a togliere la squadra dopo il salto:
    ``AppTest`` non segue uno ``switch_page`` fatto dallo script — il rerun
    successivo riesegue lo script principale — quindi quella verifica
    misurerebbe il simulatore invece dell'app. Che togliendo la squadra la
    scheda sparisca e' gia' coperto da
    :func:`test_la_scheda_sparisce_togliendo_la_squadra`.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    import guscio  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.selectbox[0].set_value("la_liga_2015_16").run()
    app.selectbox[1].set_value("Barcelona").run()
    app.button[0].click().run()

    rimaste = [
        chiave
        for chiave in (guscio.CONSEGNA_COMPETIZIONE, guscio.CONSEGNA_SQUADRA)
        if chiave in app.session_state
    ]
    assert rimaste == [], f"consegne non consumate: {rimaste}"


@senza_magazzino
def test_la_competizione_sopravvive_ai_rerun() -> None:
    """La classifica non torna ai riquadri mentre la si sta guardando.

    ``CHIAVE_COMPETIZIONE`` e' stata la chiave di un widget — il menu della
    Home — e Streamlit scarta lo stato dei widget che non vengono piu'
    disegnati. Senza la riscrittura a ogni giro, la competizione sopravviveva
    a un rerun e spariva al successivo: si sceglieva la Liga, si sceglieva una
    squadra, e la pagina tornava alla scelta del campionato.
    """
    app = squadre_aperta()
    scegli_competizione(app, "la_liga_2015_16")

    for passo in ("Barcelona", None, "Real Madrid"):
        app.selectbox[0].set_value(passo).run()  # type: ignore[attr-defined]
        assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
        assert len(app.dataframe) == 1, f"la tabella e' sparita dopo {passo!r}"  # type: ignore[attr-defined]


@senza_magazzino
@pytest.mark.parametrize("pagina", ["Panoramica.py", "pages/Squadre.py", "pages/Giocatori.py"])
def test_il_menu_e_fatto_di_voci_tutte_uguali(pagina: str) -> None:
    """Otto pulsanti identici, in ogni pagina.

    La distanza fra due voci non puo' dipendere da quale sia quella attiva:
    prima la voce corrente era un ``div`` e le altre ``st.page_link``, e il
    menu risultava spaziato in modo diverso su ogni pagina. Il test guarda la
    cosa che lo garantisce — che siano tutte lo stesso componente — invece del
    CSS, che da qui non si puo' vedere.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    import guscio  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    if pagina != "Panoramica.py":
        app.switch_page(pagina)
        app.run()

    menu = [app.button(key=f"menu_{etichetta}") for etichetta, _, _ in guscio.MENU]

    assert all(voce is not None for voce in menu), "una voce del menu non e' un pulsante"
    assert len(menu) == len(guscio.MENU)
    # Spente devono essere due cose e solo due: la vista corrente, perche' un
    # collegamento a se stessi non serve, e le viste non ancora costruite.
    # Il conto si ricava da `MENU`, non da un numero fisso: cosi' il test non
    # va aggiornato ogni volta che una task chiude, ma continua ad accorgersi
    # se una pagina esistente resta irraggiungibile.
    spente = {voce.label for voce in menu if voce.disabled}
    da_costruire = {
        f"{etichetta}  ·  {task}" for etichetta, task, percorso in guscio.MENU if not percorso
    }
    corrente = {etichetta for etichetta, _, percorso in guscio.MENU if percorso == pagina}
    attesa = da_costruire | corrente

    assert spente == attesa, "spente devono essere solo la vista corrente e quelle da costruire"


@senza_magazzino
def test_ogni_competizione_del_magazzino_ha_il_suo_logo() -> None:
    """Nessuna competizione resta senza marchio.

    I loghi sono decorazione e non dati, quindi ``logo_di`` restituisce
    ``None`` invece di sollevare — ma se **tutte** le competizioni ne hanno
    uno tranne una, quella stona in mezzo alle altre. Il test lo dice adesso
    invece di lasciarlo scoprire guardando la pagina.

    Euro 2020 ed Euro 2024 hanno file diversi: condividono il tema, che e'
    della competizione, non il marchio, che e' dell'edizione.
    """
    import dati  # noqa: PLC0415

    senza = [chiave for chiave in dati_competizioni() if dati.logo_di(chiave) is None]

    assert senza == [], f"competizioni senza logo: {senza}"
    assert dati.logo_di("euro_2020") != dati.logo_di("euro_2024")
    assert dati.logo_di("competizione_inventata") is None


@senza_magazzino
def test_il_marchio_si_comporta_come_la_voce_home() -> None:
    """Il marchio e la voce del menu devono portare allo stesso posto.

    Prima il marchio riportava alla Home conservando la selezione fatta su
    Squadre: era il comportamento chiesto allora, ed e' stato cambiato. Il
    rischio ora e' che le due strade divergano — il menu azzera e il marchio
    no — quindi il test le confronta invece di fidarsi.
    """
    import guscio  # noqa: PLC0415

    app = squadre_aperta()
    scegli_competizione(app, "serie_a_2015_16")
    assert app.session_state[guscio.CHIAVE_COMPETIZIONE] == "serie_a_2015_16"  # type: ignore[attr-defined]

    app.button(key="menu_marchio").click().run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert app.selectbox(key="filtro_competizione").value is None  # type: ignore[attr-defined]
    voci = {voce.label: voce.disabled for voce in app.button}  # type: ignore[attr-defined]
    assert voci["Home"]


def test_il_marchio_punta_alla_voce_home_del_menu() -> None:
    """Il percorso non e' riscritto a mano da nessuna parte.

    Due copie dello stesso percorso divergono al primo spostamento di file, e
    il marchio porterebbe a una pagina che non esiste piu' — un errore che si
    vede solo cliccando.
    """
    import guscio  # noqa: PLC0415

    etichetta, _, pagina = next(voce for voce in guscio.MENU if voce[0] == "Home")

    assert pagina == guscio.CASA
    assert etichetta == "Home"


def test_il_logo_entra_nel_foglio_di_stile() -> None:
    """Il marchio arriva come dato in linea, non come file da servire.

    Streamlit non espone una cartella statica senza ``enableStaticServing``:
    se il logo fosse un percorso, in locale funzionerebbe — perche' il file
    c'e' — e in produzione comparirebbe un pulsante senza logo.
    """
    import guscio  # noqa: PLC0415
    from football_analytics import tema as palette  # noqa: PLC0415

    foglio = guscio.foglio(palette.VERDE)

    assert "data:image/png;base64," in foglio
    assert "st-key-marchio" in foglio
    assert "assets/marchio.png" not in foglio


def test_il_marchio_resta_leggero() -> None:
    """Un logo da un mega dentro il CSS di ogni pagina.

    Il file originale pesava 967 KB: incorporato in base64 sarebbe cresciuto di
    un terzo e viaggerebbe a ogni ridisegno, su un'app che gira in meno di un
    gigabyte di RAM. Ridimensionato a 96 px ne pesa sedici.
    """
    import dati  # noqa: PLC0415

    assert dati.MARCHIO.exists()
    assert dati.MARCHIO.stat().st_size < 40_000


def test_l_import_del_font_e_la_prima_regola_del_foglio() -> None:
    """Una regola prima dell'``@import`` e i browser lo ignorano.

    E' un difetto che non da' nessun segnale: nessun errore, nessun avviso, solo
    il marchio nel font di sistema. Sarebbe passato inosservato fino a una
    schermata a caso.
    """
    import guscio  # noqa: PLC0415
    from football_analytics import tema as palette  # noqa: PLC0415

    corpo = guscio.foglio(palette.VERDE).split("<style>", 1)[1]
    prima_regola = corpo.index("{")
    posizione = corpo.index("@import")

    assert posizione < prima_regola


def test_il_marchio_ha_un_font_di_riserva() -> None:
    """Se Google Fonts non risponde il marchio deve restare leggibile.

    Un ``font-family`` con un nome solo, e la scritta cade su un ripiego
    qualunque del browser: su Windows spesso Times New Roman, che accanto a un
    logo geometrico stona in modo evidente.
    """
    import guscio  # noqa: PLC0415
    from football_analytics import tema as palette  # noqa: PLC0415

    riga = next(
        linea
        for linea in guscio.foglio(palette.VERDE).splitlines()
        if "font-family" in linea and "Space Grotesk" in linea
    )

    assert riga.count(",") >= 2
    assert riga.rstrip().endswith("sans-serif !important;")


def test_nessuna_scorciatoia_background_sui_pulsanti_della_barra() -> None:
    """La scorciatoia ``background`` azzera anche ``background-image``.

    E' il difetto che faceva sparire il logo del marchio al passaggio del
    mouse: la regola generale dell'hover usava ``background: colore !important``
    e vinceva in specificita' su quella del marchio, cancellandogli l'immagine.
    Il test guarda solo le regole che riguardano i pulsanti della barra, perche'
    altrove la scorciatoia e' legittima.
    """
    import re  # noqa: PLC0415

    import guscio  # noqa: PLC0415
    from football_analytics import tema as palette  # noqa: PLC0415

    foglio = guscio.foglio(palette.VERDE)
    colpevoli = [
        selettore.strip()
        for selettore, corpo in re.findall(r"([^{}]+)\{([^{}]*)\}", foglio)
        if "stSidebar" in selettore
        and "button" in selettore
        and re.search(r"(^|[;\s])background\s*:", corpo)
    ]

    assert colpevoli == []


def test_il_logo_resta_al_passaggio_del_mouse_e_al_clic() -> None:
    """Il marchio ridichiara l'immagine negli stati interattivi.

    Non basta averla nella regola base: qualunque regola di ``:hover`` o
    ``:active`` che tocchi lo sfondo puo' portarsela via, e il difetto si vede
    solo tenendo premuto il pulsante — cioe' quasi mai, provando.
    """
    import guscio  # noqa: PLC0415
    from football_analytics import tema as palette  # noqa: PLC0415

    foglio = guscio.foglio(palette.VERDE)

    for stato in (":hover", ":focus", ":active"):
        assert f".st-key-marchio button{stato}" in foglio


def scheda_di(chiave: str, squadra: str) -> object:
    """La scheda di una squadra, raggiunta come la raggiunge chi usa l'app.

    Args:
        chiave: La chiave della competizione.
        squadra: Il nome della squadra.

    Returns:
        L'applicazione sulla scheda.
    """
    import guscio  # noqa: PLC0415

    app = squadre_aperta()
    scegli_competizione(app, chiave)
    app.session_state[guscio.CONSEGNA_SQUADRA] = squadra  # type: ignore[attr-defined]
    app.switch_page("pages/Scheda.py")  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]
    return app


@senza_magazzino
def test_la_scheda_mostra_gli_indicatori_della_home() -> None:
    """Gli stessi riquadri, non una versione ridotta.

    Era la differenza che si vedeva a occhio: la Home diceva partite, tiri, gol
    e conversione, e la scheda partiva dalle sole voci della classifica.
    """
    app = scheda_di("serie_a_2015_16", "Juventus")

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    for etichetta in ("Partite", "Tiri totali", "Gol", "xG totale", "Conversione", "xG per tiro"):
        assert etichetta in testo, etichetta


@senza_magazzino
def test_gli_indicatori_della_scheda_contano_anche_le_trasferte() -> None:
    """Filtrare per la sola colonna «casa» darebbe meta' campionato.

    Diciannove partite invece di trentotto e' un errore che passa: il numero
    resta plausibile e nessuno lo verifica a mente.
    """
    import guscio  # noqa: PLC0415

    app = scheda_di("serie_a_2015_16", "Juventus")

    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]

    assert f'<span class="numero">{guscio.numero(38)}</span>' in testo


@senza_magazzino
def test_il_riquadro_trofei_distingue_tre_casi_diversi() -> None:
    """Lo zero c'e' per tutti, ma tre situazioni non sono la stessa cosa.

    Il Barcellona ha vinto tre delle finali nel magazzino; la Juventus ne ha
    giocate tre senza vincerne nessuna; il Getafe non compare fra le finaliste.
    Con il solo numero, gli ultimi due casi sarebbero identici — e leggere «0»
    per il Getafe come «non ha mai vinto» sarebbe un'affermazione che questi
    dati non permettono. La nota sotto il numero e' cio' che li separa.
    """
    import re  # noqa: PLC0415

    atteso = {
        ("la_liga_2015_16", "Barcelona"): ("3", "2009, 2011, 2015"),
        ("serie_a_2015_16", "Juventus"): ("0", "0 su 3 finali giocate"),
        ("la_liga_2015_16", "Getafe"): ("0", "nessuna finale nei dati"),
    }

    for (chiave, squadra), (numero_atteso, nota_attesa) in atteso.items():
        app = scheda_di(chiave, squadra)

        blocco = next(
            voce.value
            for voce in app.markdown  # type: ignore[attr-defined]
            if "Trofei" in voce.value
        )
        trovato = re.search(r'numero">(.*?)</span>\s*<span class="nota">(.*?)</span>', blocco, re.S)

        assert trovato is not None, squadra
        assert trovato.group(1) == numero_atteso, squadra
        assert trovato.group(2) == nota_attesa, squadra


@senza_magazzino
def test_la_classifica_non_mostra_la_striscia_degli_indicatori() -> None:
    """La vista Squadre e' il confronto fra squadre, non il ritratto di una.

    La striscia c'era stata per un giro e rispondeva a una domanda che chi
    guarda una graduatoria non sta facendo. Il pulsante per la scheda resta.
    """
    app = squadre_aperta()
    scegli_competizione(app, "la_liga_2015_16")

    app.selectbox(key="filtro_squadra").set_value("Real Madrid").run()  # type: ignore[attr-defined]

    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    assert "Tiri totali" not in testo
    assert "Trofei" not in testo
    assert app.button(key="apri_scheda") is not None  # type: ignore[attr-defined]


@senza_magazzino
def test_i_trofei_non_si_mostrano_senza_la_cautela() -> None:
    """«Trofei 4» per il Real Madrid si legge come un fatto, e i titoli sono 15.

    La nota sta attaccata al riquadro dentro :func:`guscio.indicatori`, non
    nella pagina: cosi' non si puo' riusare la striscia altrove dimenticandola.
    """
    app = scheda_di("la_liga_2015_16", "Real Madrid")

    note = " ".join(voce.value for voce in app.caption)  # type: ignore[attr-defined]

    assert "non è l'albo d'oro completo" in note


def home_nuova() -> object:
    """Una Home appena avviata, tutta sua.

    Non riusa la fixture ``eseguita``, che ha scope di modulo: i test di
    navigazione scrivono nello stato della sessione, e condividerlo vorrebbe
    dire far dipendere l'esito di un test dall'ordine in cui girano gli altri.

    Returns:
        L'applicazione sulla Home.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    return app


def torna_a_home(app: object) -> tuple[object, object]:
    """Preme Home nella barra laterale e legge i filtri che trova.

    L'ultimo salto passa dal pulsante vero e non da ``AppTest.switch_page``:
    e' proprio la barra laterale a decidere se la Home vada ripristinata, e
    saltandola il test proverebbe qualcos'altro.

    Args:
        app: L'applicazione, ovunque si trovi.

    Returns:
        La competizione e la squadra che la Home mostra.
    """
    app.button(key="menu_Home").click().run()  # type: ignore[attr-defined]
    return (
        app.selectbox(key="filtro_competizione").value,  # type: ignore[attr-defined]
        app.selectbox(key="filtro_squadra").value,  # type: ignore[attr-defined]
    )


@senza_magazzino
def test_tornando_da_squadre_la_home_riparte_pulita() -> None:
    """Una scelta fatta altrove non deve comparire fra i filtri della Home.

    Chi entra da Squadre, apre la Serie A e la Juventus e poi preme Home, non
    ha mai scelto niente **sulla Home**: trovarsela filtrata su quella squadra
    e' uno stato che l'utente non ha chiesto e non sa come togliere.
    """
    app = squadre_aperta()
    scegli_competizione(app, "serie_a_2015_16")
    app.selectbox(key="filtro_squadra").set_value("Juventus").run()  # type: ignore[attr-defined]
    app.switch_page("pages/Scheda.py")  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]

    assert torna_a_home(app) == (None, None)
    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]


@senza_magazzino
def test_tornando_da_una_scheda_aperta_dalla_home_i_filtri_restano() -> None:
    """L'altra meta' della regola, e senza questa la prima sarebbe solo «azzera».

    Chi ha scelto La Liga e il Barcellona **sulla Home**, e' andato a vedere la
    scheda e torna indietro, si aspetta di ritrovare la Home dove l'aveva
    lasciata.
    """
    app = home_nuova()
    app.selectbox(key="filtro_competizione").set_value("la_liga_2015_16").run()  # type: ignore[attr-defined]
    app.selectbox(key="filtro_squadra").set_value("Barcelona").run()  # type: ignore[attr-defined]
    app.button(key="vai_a_squadre").click().run()  # type: ignore[attr-defined]

    assert torna_a_home(app) == ("la_liga_2015_16", "Barcelona")
    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]


@senza_magazzino
def test_il_ripristino_non_blocca_i_filtri_della_home() -> None:
    """Il modo in cui questo meccanismo puo' rompersi senza sembrare rotto.

    Se il ripristino girasse a ogni rerun invece che al solo arrivo, riscrivrebbe
    i filtri con i valori del giro precedente: cambiare competizione dal menu
    non avrebbe effetto, e la pagina tornerebbe indietro da sola.
    """
    app = home_nuova()

    app.selectbox(key="filtro_competizione").set_value("la_liga_2015_16").run()  # type: ignore[attr-defined]
    app.selectbox(key="filtro_competizione").set_value("serie_a_2015_16").run()  # type: ignore[attr-defined]

    assert app.selectbox(key="filtro_competizione").value == "serie_a_2015_16"  # type: ignore[attr-defined]


@senza_magazzino
def test_dalla_home_la_barra_porta_a_squadre_con_la_competizione() -> None:
    """La consegna verso le altre viste non deve essere saltata.

    Il ritorno alla Home e la partenza dalla Home passano dalla stessa
    funzione: se il ramo sbagliato prendesse anche l'altro caso, Squadre si
    aprirebbe sui riquadri invece che sulla classifica gia' scelta.
    """
    app = home_nuova()
    app.selectbox(key="filtro_competizione").set_value("la_liga_2015_16").run()  # type: ignore[attr-defined]

    app.button(key="menu_Squadre").click().run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.dataframe) == 1, "Squadre non si e' aperta sulla classifica"  # type: ignore[attr-defined]


@senza_magazzino
def test_lo_scarto_chiude_la_pagina_sopra_l_attribuzione() -> None:
    """La posizione e' la terza provata, e questo test e' il motivo.

    In fondo alla colonna di sinistra il riquadro si incastrava nella scheda
    della riga successiva; dentro quella del confronto restava stretto contro
    le barre. In coda alla pagina non ha nessuna scheda accanto — ma e' una
    posizione che un ritocco distratto puo' spostare senza accorgersene,
    quindi l'ordine degli ultimi due blocchi va fissato.
    """
    for chiave, squadra in (("serie_a_2015_16", "Juventus"), ("la_liga_2015_16", "Getafe")):
        app = scheda_di(chiave, squadra)

        ultimi = [voce.value for voce in app.markdown][-2:]  # type: ignore[attr-defined]

        assert 'class="evidenza"' in ultimi[0], squadra
        assert 'class="attribuzione"' in ultimi[1], squadra


def su_giocatori(chiave: str) -> object:
    """La vista Giocatori con una competizione aperta.

    Args:
        chiave: La chiave della competizione.

    Returns:
        L'applicazione.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Giocatori.py")
    app.run()
    app.button(key=f"apri_{chiave}").click().run()
    return app


@senza_magazzino
def test_i_giocatori_si_aprono_sui_riquadri_e_non_su_una_classifica() -> None:
    """Senza una competizione scelta non c'e' una graduatoria sensata.

    Mettere in colonna un attaccante di Ligue 1 con trentaquattro presenze e
    uno visto per tre partite a un Mondiale produce un ordinamento che sembra
    significativo e non lo e'.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Giocatori.py")
    app.run()

    assert not app.exception, [str(e.value) for e in app.exception]
    assert len(app.dataframe) == 0
    assert app.button(key="apri_serie_a_2015_16") is not None


@senza_magazzino
def test_la_vista_giocatori_mostra_le_quattro_graduatorie() -> None:
    """Le quattro ci sono tutte, e il capocannoniere e' quello vero."""
    app = su_giocatori("serie_a_2015_16")

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    for titolo in ("Marcatori", "xG generato", "Gol sopra le attese", "Gol sotto le attese"):
        assert titolo in testo, titolo
    assert "Higuaín" in testo


@senza_magazzino
def test_il_filtro_reparto_restringe_le_graduatorie() -> None:
    """Con i soli portieri le graduatorie non devono piu' mostrare attaccanti.

    E' il modo in cui un filtro puo' rompersi restando plausibile: se non
    venisse applicato, la pagina mostrerebbe le stesse classifiche di prima e
    nessuno se ne accorgerebbe.

    Il riquadro «Capocannoniere» resta su Higuaín ed e' voluto: la striscia in
    cima descrive la competizione e sta **sopra** il filtro. Il test guarda
    quindi i soli blocchi delle graduatorie, non tutto il testo della pagina.
    """
    import dati  # noqa: PLC0415
    from football_analytics import giocatori as logica  # noqa: PLC0415

    app = su_giocatori("serie_a_2015_16")
    graduatorie = " ".join(
        voce.value
        for voce in app.markdown  # type: ignore[attr-defined]
        if 'class="classifica"' in voce.value
    )
    assert "Higuaín" in graduatorie

    app.session_state["filtro_reparto"] = ["Portiere"]  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    dopo = " ".join(
        voce.value
        for voce in app.markdown  # type: ignore[attr-defined]
        if 'class="classifica"' in voce.value
    )
    assert "Higuaín" not in dopo

    # Il conto passa dalla stessa somma per giocatore che usa la pagina: un
    # portiere trasferito a gennaio ha due righe nel magazzino e una sola qui,
    # e confrontare con le righe grezze farebbe fallire il test per il motivo
    # sbagliato.
    portieri = logica.con_reparto(
        logica.per_giocatore(dati.filtra(dati.leggi("player_stats"), "serie_a_2015_16"))
    )
    attesi = len(portieri[portieri["reparto"] == "Portiere"])
    assert len(app.dataframe[0].value) == attesi  # type: ignore[attr-defined]


@senza_magazzino
def test_la_tabella_dei_giocatori_tiene_anche_chi_sta_sotto_la_soglia() -> None:
    """Escluderli anche dalla tabella li farebbe sparire senza spiegazione."""
    import dati  # noqa: PLC0415
    from football_analytics import giocatori as logica  # noqa: PLC0415

    app = su_giocatori("serie_a_2015_16")

    mostrati = len(app.dataframe[0].value)  # type: ignore[attr-defined]
    tutti = logica.per_giocatore(dati.filtra(dati.leggi("player_stats"), "serie_a_2015_16"))

    assert mostrati == len(tutti)
    assert mostrati > len(logica.qualificati(tutti))


def su_partite(chiave: str) -> object:
    """La vista Partite con una competizione aperta.

    Args:
        chiave: La chiave della competizione.

    Returns:
        L'applicazione.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Partite.py")
    app.run()
    app.button(key=f"apri_{chiave}").click().run()
    return app


@senza_magazzino
def test_la_vista_partite_elenca_tutto_il_campionato() -> None:
    """Trecentottanta partite, e le due liste dei casi notevoli."""
    app = su_partite("serie_a_2015_16")

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.dataframe[0].value) == 380  # type: ignore[attr-defined]
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    assert "Vinte da chi aveva creato meno" in testo
    assert "Le più aperte" in testo


@senza_magazzino
def test_la_scheda_di_una_partita_si_apre_con_i_suoi_tre_grafici() -> None:
    """Due mappe dei tiri e la corsa dell'xG.

    La scheda e' l'unico posto della dashboard dove due valori di xG stanno
    accanto senza cautele: stesso campo, stesso arbitro, stessi novanta minuti.
    """
    import guscio  # noqa: PLC0415

    app = su_partite("serie_a_2015_16")
    import dati  # noqa: PLC0415
    from football_analytics import partite as logica  # noqa: PLC0415

    tutte = dati.filtra(dati.leggi("matches"), "serie_a_2015_16")
    scelta = int(logica.elenco(tutte).iloc[0]["match_id"])
    app.session_state[guscio.CONSEGNA_PARTITA] = scelta  # type: ignore[attr-defined]
    app.switch_page("pages/Incontro.py")  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert len(app.get("plotly_chart")) == 3  # type: ignore[attr-defined]
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    assert 'class="tabellone"' in testo
    assert 'class="evidenza"' in testo


def scheda_giocatore(chiave: str, nome_breve: str) -> object:
    """La scheda di un giocatore, raggiunta come la raggiunge chi usa l'app.

    Args:
        chiave: La chiave della competizione.
        nome_breve: Il nome con cui il giocatore e' noto.

    Returns:
        L'applicazione sulla scheda.
    """
    import dati  # noqa: PLC0415
    import guscio  # noqa: PLC0415
    from football_analytics import giocatori as logica  # noqa: PLC0415

    tutti = logica.per_giocatore(dati.filtra(dati.leggi("player_stats"), chiave))
    suo = tutti[tutti["giocatore_breve"] == nome_breve]
    assert not suo.empty, nome_breve

    app = su_giocatori(chiave)
    app.session_state[guscio.CONSEGNA_GIOCATORE] = int(  # type: ignore[attr-defined]
        suo.iloc[0]["giocatore_id"]
    )
    app.switch_page("pages/Giocatore.py")  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]
    return app


@senza_magazzino
def test_il_clic_su_una_riga_apre_la_scheda_del_giocatore() -> None:
    """E' il criterio di chiusura di M6-T5, e per due task non era soddisfatto.

    La tabella era un tabellone da leggere; il backlog chiede che sia il modo
    di scegliere un giocatore. Il test riconosce la scheda dal radar, che
    esiste solo la'.
    """
    app = scheda_giocatore("serie_a_2015_16", "Gonzalo Higuaín")

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    assert "Confronto con il reparto Attacco" in testo
    assert "Higuaín" in testo


@senza_magazzino
def test_la_tabella_dei_giocatori_ha_reparto_e_posizione() -> None:
    """Il backlog chiede «ruolo»: il reparto filtra, la posizione informa.

    Con il solo reparto due attaccanti sono indistinguibili anche quando uno
    e' un centravanti e l'altro un'ala.
    """
    app = su_giocatori("serie_a_2015_16")

    colonne = list(app.dataframe[0].value.columns)  # type: ignore[attr-defined]

    assert "reparto" in colonne
    assert "ruolo" in colonne
    assert "giocatore_id" not in colonne, "l'identificativo non va mostrato"


@senza_magazzino
def test_la_scheda_del_portiere_e_ridotta_e_lo_dichiara() -> None:
    """Senza parate ne' clean sheet, un radar direbbe solo che non segna.

    Il limite e' dei dati, non della vista: la pagina lo scrive invece di
    mostrare grafici vuoti che sembrano un difetto.
    """
    import dati  # noqa: PLC0415
    from football_analytics import giocatori as logica  # noqa: PLC0415

    tutti = logica.con_reparto(
        logica.per_giocatore(dati.filtra(dati.leggi("player_stats"), "serie_a_2015_16"))
    )
    portiere = logica.qualificati(tutti[tutti["reparto"] == "Portiere"]).nlargest(1, "minuti")

    app = scheda_giocatore("serie_a_2015_16", str(portiere.iloc[0]["giocatore_breve"]))

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    avvisi = " ".join(voce.value for voce in app.info)  # type: ignore[attr-defined]
    assert "parate" in avvisi
    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]
    assert "Confronto con il reparto" not in testo
    # Resta la mappa dei tocchi: e' l'unica cosa che i dati sanno dirci.
    assert len(app.get("plotly_chart")) == 1  # type: ignore[attr-defined]


@senza_magazzino
def test_dalla_scheda_squadra_si_arriva_alle_sue_partite() -> None:
    """Il criterio di chiusura di M6-T7, che la prima stesura non soddisfaceva.

    Non basta arrivare alla vista Partite: chi ci arriva dalla Juventus deve
    trovarci la Juventus, non tutta la Serie A.
    """
    app = scheda_di("serie_a_2015_16", "Juventus")

    app.button(key="vai_a_partite").click().run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    assert app.selectbox(key="filtro_squadra").value == "Juventus"  # type: ignore[attr-defined]
    assert len(app.dataframe[0].value) == 38  # type: ignore[attr-defined]


@senza_magazzino
def test_la_scheda_squadra_confronta_con_una_squadra_scelta() -> None:
    """Il criterio di chiusura di M6-T4, mancato dalla prima stesura.

    Le prime cinque per xG sono un confronto utile, ma non rispondono a «come
    siamo messi rispetto a chi ci sta davanti»: per quello serve scegliere.
    """
    import re  # noqa: PLC0415

    app = scheda_di("serie_a_2015_16", "Juventus")

    app.selectbox(key="confronta_con").set_value("Napoli").run()  # type: ignore[attr-defined]

    assert not app.exception, [str(e.value) for e in app.exception]  # type: ignore[attr-defined]
    blocco = next(
        voce.value
        for voce in app.markdown  # type: ignore[attr-defined]
        if 'class="classifica"' in voce.value
    )
    assert re.findall(r'class="nome">([^<]+)<', blocco) == ["Juventus", "Napoli"]


@senza_magazzino
def test_senza_scelta_la_scheda_mostra_ancora_le_prime() -> None:
    """Il comportamento precedente resta quello predefinito.

    Chi non chiede un confronto preciso deve trovare quello sensato, non un
    riquadro vuoto in attesa di una scelta.
    """
    app = scheda_di("serie_a_2015_16", "Juventus")

    testo = " ".join(voce.value for voce in app.markdown)  # type: ignore[attr-defined]

    assert "Confronto con le prime del campionato" in testo


@senza_magazzino
def test_il_confronto_leghe_mostra_le_quattro_schede() -> None:
    """Quattro campionati, la frase calcolata e le curve di densita'."""
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Confronto.py")
    app.run()

    assert not app.exception, [str(e.value) for e in app.exception]
    testo = " ".join(voce.value for voce in app.markdown)
    assert testo.count('class="targa"') == 4
    assert 'class="evidenza"' in testo
    assert len(app.get("plotly_chart")) == 1


@senza_magazzino
def test_il_confronto_leghe_avverte_sul_limite_vero() -> None:
    """E' il criterio di chiusura di M6-T8, e la nota e' stata riscritta due volte.

    La prima stesura seguiva il backlog e nominava la Serie A. La seconda
    diceva che senza i dati 360 non si sa dove fossero difensori e portiere: e'
    falso, quelle posizioni stanno nel fotogramma del tiro, che nei campionati
    c'e' sul 99 % dei tiri. Il limite misurabile e' uno solo, ed e' la Ligue 1
    a 377 partite invece di 380.

    Il test pretende quel numero e **vieta** la frase sbagliata, cosi' non puo'
    rientrare da una riscrittura distratta.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Confronto.py")
    app.run()

    avvisi = " ".join(voce.value for voce in app.warning)

    assert "377" in avvisi, "il buco della Ligue 1 va dichiarato dove i numeri si confrontano"
    assert "senza sapere dove" not in avvisi, "e' la frase falsa: le posizioni si conoscono"


@senza_magazzino
def test_la_frase_del_confronto_nasce_dai_numeri() -> None:
    """Nessun testo fisso: la frase nomina la metrica piu' distante e la misura.

    Con i dati veri la distanza maggiore e' sulla conversione, il 16 % fra il
    primo e l'ultimo. Se qualcuno cambiasse il calcolo, una frase scritta a
    mano resterebbe li' a dire il falso.
    """
    import dati  # noqa: PLC0415
    from football_analytics import leghe as logica  # noqa: PLC0415
    from football_analytics import panoramica as base  # noqa: PLC0415

    riassunto = logica.riassunto(dati.leggi("matches"), base.tiri_di_gioco(dati.leggi("shots")))
    rapporti = logica.scarti(riassunto)

    peggiore = max(rapporti, key=lambda chiave: rapporti[chiave])
    assert peggiore == "conversione"
    assert rapporti[peggiore] == pytest.approx(1.16, abs=0.01)


@senza_magazzino
def test_la_vista_modello_risponde_alle_quattro_domande() -> None:
    """Il criterio di M6-T9: un tecnico deve capire il modello senza il codice.

    Le quattro intestazioni sono le quattro domande che si fa chi valuta un
    modello, e stanno in pagina in quell'ordine. Se una sparisse, la pagina
    resterebbe bella e smetterebbe di soddisfare il criterio.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Modello.py")
    app.run()

    assert not app.exception, [str(e.value) for e in app.exception]
    testo = " ".join(voce.value for voce in app.markdown)
    for domanda in ("È calibrato?", "Cosa guarda", "variabili spaziali servono", "Regge fuori"):
        assert domanda in testo, f"manca il blocco «{domanda}»"


@senza_magazzino
def test_la_vista_modello_nomina_le_metriche_e_le_spiega() -> None:
    """Registro tecnico, con una riga in chiaro sotto ogni blocco.

    Le metriche restano con il loro nome — un tecnico deve poterle leggere — ma
    la pagina dice anche cosa vogliono dire, o chi non fa ML non ricava niente.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Modello.py")
    app.run()

    testo = " ".join(voce.value for voce in [*app.markdown, *app.caption])

    for metrica in ("Brier", "Log loss", "AUC"):
        assert metrica in testo
    assert "calibrato" in testo
    assert "deviazione standard" in testo, "la metrica va nominata e anche spiegata"


@senza_magazzino
def test_la_vista_modello_dichiara_la_divisione_per_partita() -> None:
    """E' la regola che protegge tutti i numeri della pagina.

    Dividere per tiro invece che per partita farebbe filtrare informazione fra
    addestramento e verifica, e ogni punteggio della pagina sarebbe gonfiato.
    Chi valuta il progetto cerca proprio questa frase.
    """
    from streamlit.testing.v1 import AppTest  # noqa: PLC0415

    app = AppTest.from_file(str(PAGINA), default_timeout=ATTESA)
    app.run()
    app.switch_page("pages/Modello.py")
    app.run()

    testo = " ".join(voce.value for voce in [*app.markdown, *app.caption])

    assert "per partita intera" in testo
    assert "mai visti dal modello" in testo, "le finali fuori campione vanno dichiarate"


def test_le_frasi_della_vista_modello_nascono_dai_numeri() -> None:
    """Nessun testo fisso: le conclusioni si ricalcolano dal rendiconto.

    Con i numeri di M5 le variabili spaziali valgono un 3,5 % di Brier. Una
    frase scritta a mano resterebbe li' a dire il falso se il modello venisse
    riaddestrato.

    Non serve il magazzino: il rendiconto e' un JSON, ed e' in git. Questo
    controllo gira anche in CI.
    """
    from football_analytics import rendiconto  # noqa: PLC0415

    brier = rendiconto.per_nome(rendiconto.ablazione(), "passo", "brier")
    base = brier["Modello base"]
    completo = brier["Modello spaziale"]

    assert (base - completo) / base * 100 == pytest.approx(3.5, abs=0.3)


def test_la_vista_modello_e_agganciata_al_menu() -> None:
    """Una pagina che esiste e non compare nel menu non esiste per chi guarda."""
    import guscio  # noqa: PLC0415

    voci = {etichetta: pagina for etichetta, _, pagina in guscio.MENU}

    assert voci["Modello xG"] == "pages/Modello.py"
    assert (Path(__file__).parents[1] / "app" / voci["Modello xG"]).exists()
