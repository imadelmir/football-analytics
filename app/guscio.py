"""Il guscio condiviso da tutte le viste (M6-T4).

Fino a M6-T3 la dashboard era una pagina sola e questa roba stava dentro
``Panoramica.py``. Con la seconda vista sarebbe diventata roba **copiata**, e
due copie di un menu divergono al primo ritocco: la voce attiva evidenziata in
una pagina e non nell'altra, il filtro competizione che in una accetta «Tutte»
e nell'altra no.

**Il menu e' fatto di otto pulsanti identici**, non di componenti diversi a
seconda dello stato: quelli delle viste costruite cambiano pagina, gli altri
sono spenti con la sigla della task. Il menu automatico che Streamlit disegna
da solo sopra la barra e' nascosto — mostrerebbe gli stessi nomi una seconda
volta, con un altro stile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

import dati
import theme
from football_analytics import albo, squadre
from football_analytics.tema import per_competizione

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pandas as pd
    from streamlit.delta_generator import DeltaGenerator

    from football_analytics.tema import Tema

#: La configurazione predefinita dei grafici: nessun comando, nessuno zoom.
#:
#: In un notebook la barra di Plotly serve; su un anello o su un istogramma
#: alto duecento pixel e' arredamento che invita a toccare cose che non
#: cambiano niente, e con ``dragmode`` attivo bastava un movimento del mouse
#: per ritrovarsi ingranditi su un angolo.
SENZA_BARRA: dict[str, object] = {"displayModeBar": False, "scrollZoom": False}

#: La configurazione delle sole viste dove ingrandire ha senso.
#:
#: La mappa dei tiri e' l'unico grafico del progetto in cui guardare da vicino
#: una zona significa qualcosa. Restano i comandi di zoom e il ritorno alla
#: vista iniziale; selezione, righelli e confronti spariscono. ``scrollZoom``
#: e' spento anche qui perche' la pagina scorre: la rotella deve far scendere
#: la pagina, non ingrandire il grafico che passa sotto il puntatore.
CON_ZOOM: dict[str, object] = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "select2d",
        "lasso2d",
        "autoScale2d",
        "toggleSpikelines",
        "hoverClosestCartesian",
        "hoverCompareCartesian",
        "pan2d",
        "toImage",
    ],
}

#: Quante righe nelle classifiche laterali.
QUANTE: int = 5

#: Quante competizioni per riga nei riquadri di scelta.
PER_RIGA: int = 3

#: Altezza del logo nei riquadri di scelta e nella testata, in pixel.
LOGO: int = 44
LOGO_TESTATA: int = 58

#: Le chiavi con cui i filtri vivono in ``st.session_state``.
#:
#: **Fisse e condivise fra le pagine, ed e' il punto.** Streamlit tiene lo
#: stato per chiave, non per pagina: dando lo stesso nome al filtro squadra
#: della Home e a quello di Squadre, passando dall'una all'altra la selezione
#: resta dov'era invece di azzerarsi. E' anche cio' che permette a un pulsante
#: di preparare la scelta e poi cambiare pagina.
CHIAVE_COMPETIZIONE: str = "filtro_competizione"
CHIAVE_SQUADRA: str = "filtro_squadra"

#: Le chiavi del passaggio di consegne fra una pagina e l'altra.
#:
#: Servono perche' lo stato dei widget **non sopravvive al cambio pagina**: la
#: Home sceglie la competizione con un menu a tendina e Squadre con dei
#: pulsanti, e due widget di tipo diverso con la stessa chiave si azzerano a
#: vicenda. Queste chiavi non appartengono a nessun widget, quindi si possono
#: scrivere prima del salto e leggere dopo.
CONSEGNA_COMPETIZIONE: str = "apri_competizione"
CONSEGNA_SQUADRA: str = "apri_squadra"
CONSEGNA_PARTITA: str = "apri_partita"
CONSEGNA_GIOCATORE: str = "apri_giocatore"

#: Cosa e' aperto nelle due schede di dettaglio.
CHIAVE_PARTITA: str = "partita_scelta"
CHIAVE_GIOCATORE: str = "giocatore_scelto"

#: La memoria della sola Home, e il segnale che la sta richiamando.
#:
#: **La Home ricorda cio' che aveva scelto lei**, non cio' che hanno scelto le
#: altre pagine. Le chiavi dei filtri sono condivise apposta — passando fra
#: Squadre e Scheda la selezione resta dov'era — ma quella condivisione, letta
#: dalla Home, dava un risultato sbagliato: chi entrava da Squadre, sceglieva
#: la Serie A e la Juventus, e poi premeva Home, si trovava la Home filtrata
#: su una scelta che non aveva mai fatto li'.
#:
#: Con una memoria separata le due strade restano distinte: chi ha filtrato
#: **sulla Home** la ritrova come l'aveva lasciata, chi non l'ha mai toccata la
#: trova pulita.
MEMORIA_COMPETIZIONE: str = "home_competizione"
MEMORIA_SQUADRA: str = "home_squadra"
RICHIAMO_HOME: str = "torna_alla_home"


#: Le viste previste dal backlog: etichetta, task, percorso della pagina.
#:
#: Il percorso vuoto significa «non ancora costruita»: la voce compare spenta
#: con la sigla della task accanto. Un menu che porta a pagine vuote e' peggio
#: di un menu che dichiara cosa manca, e tenere l'elenco completo fin da subito
#: mostra dove sta andando il progetto invece di far comparire voci a sorpresa.
#:
#: I percorsi sono relativi allo script principale, come vuole
#: ``st.switch_page``.
MENU: tuple[tuple[str, str, str], ...] = (
    ("Home", "M6-T3", "Panoramica.py"),
    ("Squadre", "M6-T4", "pages/Squadre.py"),
    ("Giocatori", "M6-T5", "pages/Giocatori.py"),
    ("Partite", "M6-T7", "pages/Partite.py"),
    ("Confronto leghe", "M6-T8", ""),
    ("Modello xG", "M6-T9", ""),
    ("Finali Champions", "M6-T10", ""),
    ("Metodologia", "M6-T11", ""),
)

#: La pagina a cui torna il marchio.
#:
#: Presa da :data:`MENU` invece che riscritta: due copie dello stesso percorso
#: sono due cose che possono divergere, e il giorno in cui la home cambiasse
#: file il marchio porterebbe a una pagina che non c'e' piu'.
CASA: str = MENU[0][2]

#: Le coppie consegna-filtro, in un posto solo.
#:
#: Erano ripetute in due funzioni, e aggiungendo la partita ne avrei dovute
#: toccare due: prima o poi una delle due resta indietro e una selezione
#: sopravvive al salto mentre un'altra no.
COPPIE_DI_CONSEGNA: tuple[tuple[str, str], ...] = (
    (CONSEGNA_COMPETIZIONE, CHIAVE_COMPETIZIONE),
    (CONSEGNA_SQUADRA, CHIAVE_SQUADRA),
    (CONSEGNA_PARTITA, CHIAVE_PARTITA),
    (CONSEGNA_GIOCATORE, CHIAVE_GIOCATORE),
)


#: Le icone dei sei indicatori, disegnate in linea.
#:
#: SVG scritti a mano e non una libreria di icone: sono sei simboli, pesano
#: nulla, ereditano il colore dal CSS e non aggiungono una dipendenza a un
#: progetto che gira dentro un gigabyte di RAM. ``currentColor`` fa il resto —
#: diventano viola nel tema delle finali senza che qui cambi niente.
ICONE: dict[str, str] = {
    "Partite": (
        '<path d="M3 4h18v16H3z"/><path d="M3 9h18"/><path d="M8 2v4"/><path d="M16 2v4"/>'
    ),
    "Tiri totali": (
        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>'
        '<circle cx="12" cy="12" r="1.5" fill="currentColor"/>'
    ),
    "Gol": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 7.5l3.5 2.6-1.3 4.1h-4.4L8.5 10.1z"/>'
        '<path d="M12 3v4.5M4.2 9.4l4.3.7M19.8 9.4l-4.3.7M7.3 19.6l2.5-5.4M16.7 19.6l-2.5-5.4"/>'
    ),
    "xG totale": ('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    "Conversione": ('<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
    "xG per tiro": (
        '<circle cx="12" cy="12" r="8"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>'
        '<circle cx="12" cy="12" r="2.5" fill="currentColor"/>'
    ),
    "Trofei": (
        '<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 5H5v2a3 3 0 0 0 3 3"/>'
        '<path d="M16 5h3v2a3 3 0 0 1-3 3"/><path d="M12 13v4M9 20h6M10 17h4v3h-4z"/>'
    ),
}


def fascia_di(tema: Tema) -> str:
    """La sfumatura d'identita' di un tema, per chi la vuole fuori dalla testata.

    Rimanda a :func:`theme.fascia`: la regola su bandiere e sfumature sta li' e
    non va riscritta, o due fasce degli stessi colori finirebbero disegnate in
    due modi diversi.

    Args:
        tema: La palette.

    Returns:
        Il valore CSS di ``background``.
    """
    return theme.fascia(tema)


def icona(nome: str) -> str:
    """Il markup dell'icona di un indicatore.

    Args:
        nome: L'etichetta dell'indicatore.

    Returns:
        Il tag ``svg``, oppure stringa vuota se non c'e' un'icona.
    """
    tracciato = ICONE.get(nome)
    if tracciato is None:
        return ""
    return (
        '<svg class="icona" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{tracciato}</svg>'
    )


def numero(valore: float, decimali: int = 0) -> str:
    """Formatta un numero all'italiana: punto per le migliaia, virgola decimale.

    Args:
        valore: Il numero.
        decimali: Quante cifre dopo la virgola.

    Returns:
        Il numero formattato.
    """
    return f"{valore:,.{decimali}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def distintivo(nome: str) -> str:
    """Il cerchio con la sigla della squadra.

    Args:
        nome: Il nome della squadra.

    Returns:
        Il frammento HTML.
    """
    return (
        f'<span class="sigla" style="background:{squadre.colore(nome)}">'
        f"{squadre.sigla(nome)}</span>"
    )


def barra_laterale(attiva: str) -> None:
    """Marchio e navigazione.

    **Tutte le voci sono lo stesso componente**, e non e' un dettaglio di
    gusto. Prima la voce attiva era un ``div`` e le altre ``st.page_link``:
    due elementi con margini propri diversi, quindi la distanza fra due voci
    cambiava a seconda di quale delle due fosse quella attiva — il menu
    sembrava storto in un modo diverso su ogni pagina. Tre tentativi di
    allineare i margini a colpi di CSS non hanno risolto niente, perche' il
    difetto non era nei valori ma nell'avere due scatole diverse.

    Con otto pulsanti identici la distanza e' necessariamente la stessa: non
    c'e' piu' niente da tenere allineato. Quelli delle viste da costruire sono
    disattivati e portano la sigla della task; quello della vista corrente e'
    disattivato pure lui, perche' un collegamento a se stessi non serve.

    Args:
        attiva: L'etichetta della vista corrente.
    """
    with st.sidebar, st.container(key="marchio"):
        # Il marchio e' un pulsante, non un'immagine dentro un collegamento:
        # un `<a href="/">` ricaricherebbe la pagina da capo e la competizione
        # scelta andrebbe persa, mentre `st.switch_page` la conserva. Il logo
        # arriva dal CSS come sfondo, perche' l'etichetta di un pulsante
        # accetta solo testo.
        if st.button("Football **Analytics**", key="menu_marchio", width="stretch"):
            vai_a(CASA)

    with st.sidebar:
        for etichetta, task, pagina in MENU:
            corrente = etichetta == attiva
            premuto = st.button(
                etichetta if pagina else f"{etichetta}  ·  {task}",
                key=f"menu_{etichetta}",
                width="stretch",
                disabled=corrente or not pagina,
                type="primary" if corrente else "secondary",
            )
            if premuto and pagina:
                vai_a(pagina)


def riquadri_competizioni() -> None:
    """I rettangoli con cui si sceglie il campionato.

    **Sostituiscono la fila di pulsantini e la tabella sempre aperta.** Con
    nove competizioni tutte uguali in una riga non si capiva quale fosse un
    campionato e quale un torneo, e la tabella compariva prima ancora che si
    fosse scelto qualcosa — mostrando le squadre di tutto il magazzino
    mescolate, che non e' una classifica di niente.

    **Ogni riquadro porta i colori della propria competizione**, presi dallo
    stesso tema che vestira' la pagina una volta aperta: la scelta e' anche
    un'anteprima, e nove riquadri identici non aiutavano a distinguere la Liga
    dai Mondiali.

    Ogni riquadro scrive la scelta e fa ripartire lo script: al giro dopo la
    pagina mostra i dati di quella competizione.

    **Sta nel guscio e non in una pagina**, perche' la usano sia Squadre sia
    Giocatori: due copie divergerebbero al primo ritocco, e la schermata con
    cui si entra in una vista sarebbe diversa a seconda di quale vista.
    """
    # Tutto dentro un contenitore **con chiave**, e non e' decorazione.
    #
    # Scegliendo una competizione la pagina passa da questi riquadri alla
    # striscia degli indicatori, e le due cose hanno la stessa forma: colonne
    # di contenitori con bordo. Streamlit riconcilia gli elementi per
    # posizione, quindi riusava i riquadri come schede e per un istante i
    # pulsanti «Apri» comparivano dentro gli indicatori. Con una chiave i due
    # blocchi hanno identita' diverse e vengono sostituiti invece che riusati.
    with st.container(key="scelta_competizione"):
        _riquadri()


def _riquadri() -> None:
    """Disegna i riquadri veri e propri."""
    st.markdown('<p class="sezione-scelta">Scegli una competizione</p>', unsafe_allow_html=True)
    chiavi = dati.competizioni()
    for riga in range(0, len(chiavi), PER_RIGA):
        gruppo = chiavi[riga : riga + PER_RIGA]
        for colonna, chiave in zip(st.columns(PER_RIGA), gruppo, strict=False):
            suo = per_competizione(chiave)
            with colonna, st.container(border=True):
                st.markdown(
                    f'<div class="targa" style="border-left:4px solid {suo.primario}">'
                    f"{dati.insegna(chiave, LOGO)}"
                    f'<div><span class="nome-competizione" style="color:{suo.primario}">'
                    f"{dati.nome_di(chiave)}</span>"
                    f'<span class="stagione">{dati.stagione_di(chiave)}</span></div></div>'
                    f'<div class="fascetta" style="background:{fascia_di(suo)}"></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Apri", key=f"apri_{chiave}", width="stretch"):
                    st.session_state[CONSEGNA_COMPETIZIONE] = chiave
                    st.rerun()


def indicatori(numeri: dict[str, float], quota: float, squadra: str | None = None) -> None:
    """La striscia dei riquadri con i numeri principali.

    Stava in ``Panoramica.py`` finche' l'ha usata una pagina sola. Con Squadre
    che mostra gli stessi valori, copiarla avrebbe significato due strisce
    destinate a divergere: la Home con l'xG a tre decimali e Squadre a due, e
    nessuno se ne accorge finche' non si guardano affiancate.

    Il settimo riquadro — i trofei — **compare solo se la squadra ha finali nel
    magazzino**. Non e' un riquadro a zero: una squadra che non ha mai giocato
    una finale di Champions e una di cui il progetto non conosce il palmares
    sono due cose diverse, e mostrare «0» le confonderebbe.

    Args:
        numeri: Il risultato di :func:`football_analytics.panoramica.kpi`.
        quota: L'xG realizzato, da
            :func:`football_analytics.panoramica.realizzazione`.
        squadra: La squadra scelta, se ce n'e' una. Serve solo ai trofei.
    """
    xg_per_tiro = numeri["xg"] / numeri["tiri"] if numeri["tiri"] else 0.0
    voci = [
        ("Partite", numero(numeri["partite"]), "nella selezione"),
        (
            "Tiri totali",
            numero(numeri["tiri"]),
            f"{numero(numeri['tiri_per_partita'], 1)} a partita",
        ),
        ("Gol", numero(numeri["gol"]), f"{numero(numeri['gol_per_partita'], 2)} a partita"),
        ("xG totale", numero(numeri["xg"]), f"{numero(numeri['xg_per_partita'], 2)} a partita"),
        (
            "Conversione",
            f"{numeri['conversione']:.1%}".replace(".", ","),
            "dei tiri finisce in gol",
        ),
        ("xG per tiro", numero(xg_per_tiro, 3), f"realizzato al {quota:.0%}".replace(".", ",")),
    ]

    coppe = albo.di_squadra(dati.albo_champions(), squadra) if squadra else None
    if squadra is not None:
        anni = ", ".join(str(anno) for anno in coppe.anni_vinti) if coppe else ""
        if anni:
            nota = anni
        elif coppe is not None:
            nota = f"0 su {numero(coppe.giocate)} finali giocate"
        else:
            # Non «non ha mai vinto»: non ha mai giocato una delle finali che
            # stanno nel magazzino. Lo zero c'e' perche' e' stato chiesto, la
            # nota dice di che zero si tratta.
            nota = "nessuna finale nei dati"
        voci.append(("Trofei", numero(coppe.vinte if coppe else 0), nota))

    for colonna, (etichetta, valore, nota) in zip(st.columns(len(voci)), voci, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="scheda"><div class="cima">'
                f'<span class="etichetta">{etichetta}</span>{icona(etichetta)}</div>'
                f'<span class="numero">{valore}</span>'
                f'<span class="nota">{nota}</span></div>',
                unsafe_allow_html=True,
            )

    if squadra is not None:
        # La cautela sta qui e non nella pagina: attaccata al riquadro non si
        # puo' dimenticare quando la striscia verra' riusata altrove. Senza,
        # «Trofei 4» per il Real Madrid si legge come un fatto — i suoi titoli
        # veri sono quindici — e uno zero si leggerebbe come «non ha mai
        # vinto», che e' un'affermazione che questi dati non permettono.
        st.caption(
            "Trofei ricostruiti dalle 17 finali di Champions presenti nell'Open Data, "
            "rigori compresi: non è l'albo d'oro completo della competizione."
        )


def filtri(
    partite: pd.DataFrame,
    colonne: Sequence[DeltaGenerator],
    *,
    con_competizione: bool = True,
) -> tuple[str | None, str | None]:
    """I due filtri della pagina, da disegnare accanto al titolo.

    **La stagione non c'e' piu'.** Ogni competizione del magazzino ne ha una
    sola, quindi era un menu con una voce: occupava spazio, sembrava utile e
    non poteva cambiare niente.

    **Nessuno dei due parte da una voce «Tutte».** Con ``index=None`` Streamlit
    mostra il testo guida e la lente di ricerca, e con centocinquanta squadre
    scrivere tre lettere e' l'unico modo ragionevole di trovarne una. La
    crocetta riporta alla selezione completa.

    Args:
        partite: La tabella delle partite, da cui nascono le scelte.
        colonne: Le colonne in cui disegnare. Una sola se la competizione la
            sceglie qualcun altro, due altrimenti.
        con_competizione: Se disegnare anche il menu delle competizioni. La
            vista Squadre lo spegne perche' la' la competizione si sceglie a
            pulsanti, e due comandi per la stessa cosa finiscono per dire
            valori diversi.

    Returns:
        La competizione e la squadra scelte, oppure ``None`` per tutte.
    """
    scelta: str | None = st.session_state.get(CHIAVE_COMPETIZIONE)
    if con_competizione:
        dove_competizione, dove_squadra = colonne
        with dove_competizione:
            competizione = st.selectbox(
                "Competizione",
                dati.competizioni(),
                index=None,
                format_func=dati.etichetta_di,
                placeholder="Tutte le competizioni",
                key=CHIAVE_COMPETIZIONE,
            )
        scelta = None if competizione is None else str(competizione)
    else:
        (dove_squadra,) = colonne

    with dove_squadra:
        squadra = st.selectbox(
            "Squadra",
            dati.squadre_di(partite, scelta),
            index=None,
            placeholder="Cerca una squadra",
            key=CHIAVE_SQUADRA,
        )
    return scelta, None if squadra is None else str(squadra)


def apri_scheda(competizione: str | None, squadra: str) -> None:
    """Porta **direttamente** alla scheda di una squadra.

    Portava alla vista Squadre, cioe' alla classifica, da cui bisognava ancora
    trovare la riga giusta e premerla: il pulsante prometteva «apri la scheda»
    e ne apriva un'altra.

    La selezione passa dalle chiavi di consegna e non da quelle dei widget:
    le chiavi dei widget non si possono riscrivere dopo che il widget e' stato
    disegnato, e comunque non sopravvivrebbero al cambio pagina.

    Va chiamata dal corpo dello script, **non da un ``on_click``**: le
    callback girano prima che Streamlit prepari il contesto multipagina, e li'
    ``switch_page`` solleva «Could not find page».

    Args:
        competizione: La competizione da preselezionare, se c'e'.
        squadra: La squadra di cui aprire la scheda.
    """
    st.session_state[CONSEGNA_COMPETIZIONE] = competizione
    st.session_state[CONSEGNA_SQUADRA] = squadra
    st.switch_page("pages/Scheda.py")


def vai_a(pagina: str) -> None:
    """Cambia pagina dalla barra laterale, portandosi dietro cio' che serve.

    Le due destinazioni vogliono cose diverse, e tenerlo in un posto solo evita
    che il marchio e le voci del menu si comportino in modo diverso: verso la
    Home si chiede il ripristino della sua memoria, verso le altre viste si
    consegnano i filtri correnti.

    Args:
        pagina: Il percorso della pagina, relativo allo script principale.
    """
    if pagina == CASA:
        st.session_state[RICHIAMO_HOME] = True
    else:
        consegna_i_filtri()
    st.switch_page(pagina)


def consegna_i_filtri() -> None:
    """Mette la selezione corrente nelle chiavi di consegna, prima di cambiare pagina.

    Serve perche' **lo stato di un widget non sopravvive al cambio pagina**:
    Streamlit butta via il valore dei widget che non ha ridisegnato, quindi il
    menu a tendina della Home si ritrova vuoto appena si passa da un'altra
    vista. Le chiavi di consegna non appartengono a nessun widget e attraversano
    il salto intatte; la pagina di arrivo le ritira con
    :func:`ritira_consegna`.

    Va chiamata prima di ogni ``switch_page`` della barra laterale, non solo di
    quello del marchio: il difetto non e' del marchio, e' di ogni voce che porta
    a una pagina con dei filtri.
    """
    for consegna, filtro in COPPIE_DI_CONSEGNA:
        st.session_state[consegna] = st.session_state.get(filtro)


def ricorda_home(competizione: str | None, squadra: str | None) -> None:
    """Salva cio' che la Home sta mostrando, per quando ci si tornera'.

    Va chiamata **dopo** i filtri, con i valori che hanno restituito: prima
    salverebbe quelli del giro precedente.

    Args:
        competizione: La competizione scelta sulla Home, o ``None``.
        squadra: La squadra scelta sulla Home, o ``None``.
    """
    st.session_state[MEMORIA_COMPETIZIONE] = competizione
    st.session_state[MEMORIA_SQUADRA] = squadra


def ripristina_home() -> None:
    """Rimette sulla Home la sua ultima selezione, **solo quando ci si arriva**.

    Il segnale viene dalla barra laterale e si consuma con ``pop``. Senza, la
    funzione girerebbe a ogni rerun della Home e riscriverebbe i filtri con i
    valori del giro precedente: cambiare competizione dal menu a tendina non
    avrebbe effetto, perche' la scelta appena fatta verrebbe sovrascritta
    dalla memoria un istante dopo.

    Va chiamata prima di disegnare i filtri: la chiave di un widget gia'
    disegnato non si puo' riscrivere.
    """
    if not st.session_state.pop(RICHIAMO_HOME, False):
        return
    st.session_state[CHIAVE_COMPETIZIONE] = st.session_state.get(MEMORIA_COMPETIZIONE)
    st.session_state[CHIAVE_SQUADRA] = st.session_state.get(MEMORIA_SQUADRA)


def ritira_consegna() -> None:
    """Trasferisce la selezione consegnata nei filtri, una volta sola.

    Va chiamata **prima** di disegnare i filtri: scrivere la chiave di un
    widget e' permesso solo finche' il widget non esiste. Il consumo con
    ``pop`` e' la parte che evita la selezione fantasma — senza, tornando alla
    vista a mano ci si ritroverebbe la stessa squadra riaperta per sempre.
    """
    for consegna, filtro in COPPIE_DI_CONSEGNA:
        if consegna in st.session_state:
            st.session_state[filtro] = st.session_state.pop(consegna)


def barre(righe: pd.DataFrame, chiave: str, nome: str, tema: Tema, *, decimali: int) -> str:
    """Compone una classifica a barre, con distintivo e barra proporzionale.

    Si chiama ``barre`` e non ``classifica`` perche' non ha niente a che vedere
    con :mod:`football_analytics.classifica`, che calcola punti e posizioni:
    questa disegna, e disegna qualunque graduatoria le si passi.

    Args:
        righe: Le righe gia' ordinate e tagliate.
        chiave: La colonna del valore da mostrare.
        nome: La colonna del nome da mostrare.
        tema: La palette attiva.
        decimali: Quante cifre decimali nel valore.

    Returns:
        Il markup della classifica.
    """
    if righe.empty:
        return '<p class="vuoto">Nessun dato nella selezione.</p>'

    massimo = float(righe[chiave].max())
    pezzi = []
    for posizione, riga in enumerate(righe.to_dict("records"), start=1):
        larghezza = float(riga[chiave]) / massimo if massimo else 0.0
        scarto = float(riga.get("gol_meno_xg", 0.0))
        segno = "positivo" if scarto >= 0 else "negativo"
        pezzi.append(
            f'<div class="riga"><span class="posto">{posizione}</span>'
            f"{distintivo(str(riga['squadra']))}"
            f'<span class="nome">{riga[nome]}</span>'
            f'<div class="traccia"><div class="riempimento" '
            f'style="width:{larghezza:.1%};background:{tema.primario}"></div></div>'
            f'<span class="valore">{numero(float(riga[chiave]), decimali)}</span>'
            f'<span class="scarto {segno}">{"+" if scarto >= 0 else "−"}'
            f"{numero(abs(scarto), 1)}</span></div>"
        )
    return f'<div class="classifica">{"".join(pezzi)}</div>'


#: Lo stile della pagina. Usa solo i campi del tema, mai colori scritti a mano.
def foglio(tema: Tema) -> str:
    """Il foglio di stile delle pagine, gia' vestito del tema.

    Sta qui e non in tre `format` sparsi per le pagine perche' il modello ha
    piu' di un segnaposto: con la formattazione a carico di chi chiama, la
    prima pagina che ne dimenticasse uno morirebbe con un ``KeyError`` a
    schermo. Con una funzione sola, o li ha tutti o non compila mai.

    Args:
        tema: La palette attiva.

    Returns:
        Il blocco ``<style>`` pronto per ``st.markdown``.
    """
    return MODELLO.format(tema=tema, marchio=dati.marchio())


#: Il modello del foglio di stile. Passa sempre da :func:`foglio`.
MODELLO: str = """<style>
/* Il font del marchio. `@import` deve stare in cima al blocco: una regola
   prima, e i browser lo ignorano in silenzio — il marchio resterebbe nel font
   di sistema senza che niente segnali il difetto. Un test lo verifica.

   Space Grotesk sta solo sul marchio, non su tutta l'app: i corpi di testo
   restano sul font di Streamlit, gia' misurato per contrasto e leggibilita' in
   tutti e nove i temi. Cambiare font ovunque per una scritta di due parole
   vorrebbe dire rifare quelle misure. */
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap");

.testata {{ margin: 0 0 .2rem 0; }}
.titolo {{
  font-size: 2.6rem; font-weight: 800; margin: 0; letter-spacing: -.03em;
  color: {tema.primario}; line-height: 1.05;
}}
.sottotitolo {{ color: {tema.testo_tenue}; margin: 0; font-size: .95rem; }}
.periodo.sola {{ margin-left: 0; padding-left: 0; border-left: none; }}
.periodo {{
  margin-left: 12px; padding-left: 12px; border-left: 1px solid {tema.bordo};
  color: {tema.testo_tenue}; font-variant-numeric: tabular-nums;
}}

/* Il marchio: un pulsante con il logo per sfondo.

   Il selettore parte da `.st-key-marchio`, la classe che Streamlit mette sul
   contenitore quando gli si passa una `key`. Serve la doppia classe piu'
   l'elemento per battere in specificita' la regola generale dei pulsanti della
   barra laterale, che sta qui sotto e usa `!important`.

   Il logo sta nel `background-image` e non in un `<img>` perche' l'etichetta di
   un pulsante Streamlit accetta solo testo: e' l'unico modo per avere il
   marchio e la scritta dentro la stessa area cliccabile. */
section[data-testid="stSidebar"] .st-key-marchio {{ margin-bottom: 14px; }}
section[data-testid="stSidebar"] .st-key-marchio button {{
  background-image: url("{marchio}") !important;
  background-repeat: no-repeat !important;
  background-position: left 0 center !important;
  background-size: 48px 48px !important;
  min-height: 56px !important;
  padding: 4px 10px 4px 50px !important;
  color: {tema.barra_testo} !important;
}}
section[data-testid="stSidebar"] .st-key-marchio button:hover,
section[data-testid="stSidebar"] .st-key-marchio button:focus,
section[data-testid="stSidebar"] .st-key-marchio button:active {{
  background-color: {tema.bordo_barra} !important;
  background-image: url("{marchio}") !important;
}}
/* Il font va messo sul `<p>` e non sul pulsante: Streamlit scrive l'etichetta
   dentro un paragrafo con le proprie regole, che vincono su quelle ereditate.
   La riserva finisce sul font di sistema, cosi' il marchio resta leggibile
   anche se Google Fonts non risponde. */
section[data-testid="stSidebar"] .st-key-marchio button p {{
  font-family: "Space Grotesk", "Segoe UI", system-ui, sans-serif !important;
  font-size: 1.24rem !important;
  font-weight: 400 !important;
  letter-spacing: -.02em !important;
  line-height: 1.1 !important;
}}
section[data-testid="stSidebar"] .st-key-marchio button p strong {{
  font-weight: 700 !important;
}}
/* Il menu: otto pulsanti uguali, con l'aspetto di voci di elenco invece che
   di pulsanti.

   Il selettore parte da `section[data-testid="stSidebar"] button` e non dal
   testid del singolo pulsante: quello cambia da una versione di Streamlit
   all'altra, mentre «un bottone dentro la barra laterale» resta vero. Gli
   `!important` battono le regole che Streamlit applica ai propri componenti,
   che non passano da qui e che altrimenti rimettono cornice e sfondo. */
section[data-testid="stSidebar"] button {{
  justify-content: flex-start !important;
  padding: 9px 12px !important;
  border-radius: 9px !important;
  border: none !important;
  box-shadow: none !important;
  background-color: transparent !important;
  font-size: .93rem;
  font-weight: 400;
  line-height: 1.5;
  min-height: 0 !important;
  transition: background-color .18s ease, color .18s ease;
}}
section[data-testid="stSidebar"] button p {{
  color: {tema.barra_testo}; margin: 0; transition: color .18s ease;
}}
/* `background-color` e non la scorciatoia `background`: quest'ultima azzera
   anche `background-image`, e siccome questa regola vince in specificita' su
   quella del marchio, al passaggio del mouse il logo spariva. Il difetto era
   qui, non in Streamlit. */
section[data-testid="stSidebar"] button:hover:not(:disabled) {{
  background-color: {tema.bordo_barra} !important;
}}
section[data-testid="stSidebar"] button:disabled {{ opacity: 1; cursor: default; }}

/* La vista corrente: pieno colore, come una voce selezionata. */
section[data-testid="stSidebar"] button[kind="primary"] {{
  background-color: {tema.barra_accento} !important;
}}
section[data-testid="stSidebar"] button[kind="primary"] p {{
  color: #fff; font-weight: 600;
}}
/* Le viste da costruire: spente, ma con un grigio che vive sulla barra.
   Usavano `testo_tenue`, che e' schiarito per il fondo scuro delle pagine: su
   una barra bianca diventava un verde slavato illeggibile. */
section[data-testid="stSidebar"] button[kind="secondary"]:disabled p {{
  color: {tema.barra_tenue};
}}

.palmares {{
  display: flex; flex-direction: column; gap: 2px; margin-top: 10px;
  padding: 12px 14px; border-radius: 12px;
  background: {tema.primario_tenue}; border: 1px solid {tema.bordo};
}}
.palmares .etichetta {{
  color: {tema.primario}; font-size: .72rem; text-transform: uppercase;
  letter-spacing: .09em; font-weight: 700;
}}
.palmares .grande {{ font-size: 1.35rem; font-weight: 800; color: {tema.testo}; }}
.palmares .nota {{ color: {tema.testo_tenue}; font-size: .82rem; }}

/* Il tabellone della scheda partita: due lati e un trattino. */
.tabellone {{
  display: flex; align-items: center; justify-content: center; gap: 28px;
  padding: 18px 14px; margin-bottom: 4px; border-radius: 12px;
  background: {tema.superficie}; border: 1px solid {tema.bordo};
}}
.tabellone .lato {{ display: flex; flex-direction: column; align-items: center; gap: 2px; }}
.tabellone .squadra {{ color: {tema.testo_tenue}; font-size: .9rem; }}
.tabellone .gol {{
  font-size: 3rem; font-weight: 800; line-height: 1; color: {tema.testo};
  font-variant-numeric: tabular-nums;
}}
.tabellone .xg {{ color: {tema.primario}; font-size: .86rem; font-weight: 700; }}
.tabellone .separatore {{ color: {tema.testo_tenue}; font-size: 2rem; }}

.scheda {{ display: flex; flex-direction: column; gap: 2px; }}
.scheda .cima {{ display: flex; align-items: center; justify-content: space-between; }}
.scheda .icona {{ width: 22px; height: 22px; color: {tema.primario}; opacity: .85; }}
.scheda .etichetta {{
  color: {tema.primario}; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .09em; font-weight: 700;
}}
.scheda .numero {{
  font-size: 2.15rem; font-weight: 800; line-height: 1.12;
  font-variant-numeric: tabular-nums; color: {tema.testo};
  letter-spacing: -.02em;
}}
.scheda .nota {{ color: {tema.testo_tenue}; font-size: .8rem; }}

.classifica {{ display: flex; flex-direction: column; gap: 13px; padding-bottom: 6px; }}
.classifica .riga {{ display: flex; align-items: center; gap: 9px; }}
.classifica .posto {{ width: 14px; color: {tema.testo_tenue}; font-size: .82rem; }}
/* Il distintivo: la regola sta sulla classe, non sul contesto. Era annidata
   sotto `.classifica`, e lo stesso distintivo nella scheda della squadra
   veniva fuori quadrato — la forma dipendeva da dove lo si metteva. */
.sigla {{
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 700;
  line-height: 1;
}}
.classifica .nome {{ min-width: 170px; font-size: 1rem; font-weight: 500; }}
.classifica .traccia {{ flex: 1; height: 9px; border-radius: 5px; background: {tema.sfondo}; }}
.classifica .riempimento {{ height: 100%; border-radius: 4px; }}
.classifica .valore {{
  min-width: 58px; text-align: right; font-weight: 700; font-size: 1.05rem;
  font-variant-numeric: tabular-nums;
}}
.classifica .scarto {{ min-width: 46px; text-align: right; font-size: .82rem; }}
.classifica .scarto.positivo {{ color: {tema.primario}; }}
.classifica .scarto.negativo {{ color: {tema.pericolo}; }}
.vuoto {{ color: {tema.testo_tenue}; }}

/* Il riempimento interno delle schede: lo stile del bordo sta in theme.py,
   qui solo l'aria attorno al contenuto. */
[data-testid="stVerticalBlockBorderWrapper"] {{ padding: .35rem .6rem; }}
h5 {{ font-size: .95rem !important; font-weight: 700; margin-bottom: .1rem; }}
[data-testid="stCaptionContainer"] {{ margin-top: -.35rem; }}

.insight {{ display: flex; flex-direction: column; gap: 1px; }}
.insight .etichetta {{ color: {tema.testo_tenue}; font-size: .78rem; }}
.insight .grande {{ font-size: 1.3rem; font-weight: 700; color: {tema.primario}; }}
.insight .nota {{ color: {tema.testo_tenue}; font-size: .76rem; }}

/* I riquadri con cui si sceglie la competizione. */
.sezione-scelta {{
  color: {tema.testo_tenue}; font-size: .8rem; text-transform: uppercase;
  letter-spacing: .07em; margin: .2rem 0 .6rem 0;
}}
.targa {{
  display: flex; align-items: center; gap: 12px;
  padding-left: 10px; margin-bottom: 8px;
}}
.targa > div {{ display: flex; flex-direction: column; gap: 2px; }}
.insegna {{ width: auto; flex: none; object-fit: contain; }}
/* Il logo accanto al titolo: la testata diventa una riga, e il marchio non
   spinge il testo perche' ha larghezza automatica sull'altezza fissata. */
.testata.con-insegna {{ display: flex; align-items: center; gap: 16px; }}
.nome-competizione {{ font-size: 1.1rem; font-weight: 700; }}
.targa .stagione {{ color: {tema.testo_tenue}; font-size: .82rem; }}
/* La fascia della competizione, sotto il nome: la stessa che comparira' in
   cima alla pagina una volta aperta. */
.fascetta {{ height: 4px; border-radius: 3px; margin-bottom: 10px; }}

/* La scheda della squadra: intestazione, elenco di valori, evidenza. */
.capo {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
.capo .sigla {{ width: 46px; height: 46px; font-size: 13px; }}
.nome-squadra {{ font-size: 1.35rem; font-weight: 700; color: {tema.testo}; line-height: 1.15; }}
.posto {{ color: {tema.testo_tenue}; font-size: .82rem; }}
.voci {{ display: flex; flex-direction: column; }}
.voce-scheda {{
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 7px 0; border-bottom: 1px solid {tema.bordo};
  color: {tema.testo_tenue}; font-size: .9rem;
}}
.voce-scheda:last-child {{ border-bottom: none; }}
.voce-scheda b {{ color: {tema.testo}; font-size: 1.02rem; font-variant-numeric: tabular-nums; }}
/* Il riquadro sta in fondo alla pagina, fuori da ogni colonna: qui un margine
   verticale e' innocuo, perche' non c'e' nessuna scheda accanto la cui altezza
   possa essere calcolata senza tenerne conto. */
.evidenza {{
  margin: 6px 0 4px; padding: 12px 14px; border-radius: 10px;
  text-align: center;
  background: {tema.primario_tenue}; color: {tema.primario};
  font-size: .92rem; font-weight: 600;
}}
</style>"""
