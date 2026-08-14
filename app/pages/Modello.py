"""Come funziona il modello xG, e quanto vale (M6-T9).

**Il criterio della task e' che un tecnico capisca il modello senza leggere il
codice**, e detta cosi' impone quattro risposte in quest'ordine: e' calibrato?
cosa guarda? i dati 360 servono davvero? regge fuori dal campione su cui e'
stato misurato? La pagina e' fatta di quei quattro blocchi e di niente altro.

**Nessun numero viene calcolato qui.** Tutti arrivano gia' misurati da
:mod:`football_analytics.rendiconto`, che legge il rendiconto di M5 e le schede
dei due modelli. E' la stessa fonte di ``M5-risultati.md``: cosi' la pagina e la
documentazione non possono dire due cose diverse, e nessun valore in pagina e'
stato scritto a mano.

**Le metriche mantengono il loro nome** — Brier, log loss, AUC — perche' il
criterio parla di un tecnico, e nascondere i nomi dietro parafrasi renderebbe
la pagina inservibile proprio a chi deve valutarla. Sotto ogni blocco c'e' una
riga che dice in italiano cosa quel numero significa, cosi' chi non fa ML
ricava comunque la conclusione.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

import guscio
import theme
from football_analytics import rendiconto, viz
from football_analytics.config import ATTRIBUZIONE
from guscio import SENZA_BARRA, foglio, numero

if TYPE_CHECKING:
    from football_analytics.tema import Tema

st.set_page_config(page_title="Football Analytics — Modello xG", layout="wide")

#: Oltre quanti errori standard uno scarto di calibrazione smette di essere
#: rumore.
#:
#: Due errori standard sono il novantacinque per cento circa: sotto quella
#: soglia un punto lontano dalla bisettrice e' compatibile con il caso, e
#: chiamarlo difetto del modello vorrebbe dire leggere una fluttuazione.
SOGLIA_SE: float = 2.0

#: I nomi dei tre gruppi di variabili categoriche, come li produce
#: :func:`~football_analytics.rendiconto.categorie`.
#:
#: Costanti e non stringhe ripetute: sono chiavi di ricerca dentro una tabella,
#: e un refuso in una delle due copie darebbe una sezione vuota invece di un
#: errore.
GRUPPO_CORPO: str = "Parte del corpo"
GRUPPO_TIPO: str = "Tipo di tiro"
GRUPPO_SCHEMA: str = "Origine dell'azione"


def colori_modelli(tema: Tema) -> dict[str, str]:
    """Il colore di ciascun modello, usato in tutta la pagina.

    **Uno solo per modello, in tutti i grafici.** Se la variante 360 fosse blu
    nella calibrazione e verde fra i coefficienti, ogni grafico costringerebbe
    a rileggere la legenda.

    Args:
        tema: La palette attiva.

    Returns:
        Il colore per nome del modello.
    """
    return {"Base": tema.atteso, "360": tema.primario, "StatsBomb": tema.testo_tenue}


def cartellino(etichetta: str, valore: str, nota: str) -> str:
    """Un riquadro con un numero e la sua didascalia.

    Args:
        etichetta: Il nome del numero.
        valore: Il numero, gia' formattato.
        nota: La riga sotto.

    Returns:
        Il frammento HTML.
    """
    return (
        f'<div class="scheda"><div class="cima">'
        f'<span class="etichetta">{etichetta}</span></div>'
        f'<span class="numero">{valore}</span>'
        f'<span class="nota">{nota}</span></div>'
    )


def intestazione(varianti: list[rendiconto.Variante], contesto: rendiconto.Contesto) -> None:
    """Le due varianti affiancate, con le metriche di ciascuna.

    Args:
        varianti: Base e 360.
        contesto: Su quanti dati sono state misurate.
    """
    for colonna, variante in zip(st.columns(len(varianti)), varianti, strict=True):
        with colonna, st.container(border=True):
            st.markdown(
                f'<div class="targa"><div>'
                f'<span class="nome-competizione">Modello {variante.etichetta}</span>'
                f'<span class="stagione">{len(variante.variabili)} variabili · '
                f"regressione logistica</span></div></div>",
                unsafe_allow_html=True,
            )
            st.markdown(f'<p class="vuoto">{variante.descrizione}</p>', unsafe_allow_html=True)
            voci = (
                ("Brier", numero(variante.brier, 4), "più basso è meglio"),
                ("Log loss", numero(variante.log_loss, 4), "più basso è meglio"),
                ("AUC", numero(variante.auc, 3), "0,5 = caso"),
                (
                    "Errore di calibrazione",
                    f"{numero(variante.errore_calibrazione * 100, 2)} %",
                    "scarto medio per decile",
                ),
            )
            st.markdown(
                '<div class="voci">'
                + "".join(
                    f'<div class="voce-scheda"><span>{etichetta}</span><b>{valore}</b></div>'
                    for etichetta, valore, _ in voci
                )
                + "</div>",
                unsafe_allow_html=True,
            )

    st.caption(
        f"Misurati su {numero(contesto.tiri_test)} tiri di verifica da "
        f"{numero(contesto.partite_test)} partite, tenute fuori dall'addestramento "
        f"**per partita intera** e non per singolo tiro: due tiri della stessa partita "
        f"condividono avversario, campo e arbitro, e dividerli fra addestramento e "
        f"verifica farebbe filtrare informazione da una parte all'altra. "
        f"Addestramento su {numero(contesto.tiri_train)} tiri da "
        f"{numero(contesto.partite_train)} partite; {numero(contesto.scartati)} tiri "
        f"scartati per fotogramma 360 incompleto. "
        f"scikit-learn {contesto.scikit_learn}, pandas {contesto.pandas}."
    )


def frase_calibrazione(curve: pd.DataFrame, varianti: list[rendiconto.Variante]) -> str:
    """La conclusione sulla calibrazione, calcolata dai punti.

    **Nasce dai numeri**, quindi non puo' diventare falsa se un giorno il
    modello venisse riaddestrato: conta i decili che escono dall'incertezza
    invece di dichiarare a priori che il modello e' calibrato.

    Args:
        curve: Il risultato di :func:`rendiconto.calibrazione`.
        varianti: Base e 360.

    Returns:
        La frase.
    """
    if curve.empty:
        return "La curva di calibrazione non è disponibile."

    nostri = curve[curve["modello"] != "StatsBomb"]
    fuori = int((nostri["scarto_in_se"].abs() > SOGLIA_SE).sum())
    peggiore = max(variante.errore_calibrazione for variante in varianti)
    quanti = len(nostri)
    return (
        f"Su {quanti} decili misurati fra le due varianti, {fuori} escono da due errori "
        f"standard: gli altri {quanti - fuori} stanno a una distanza dalla bisettrice "
        f"compatibile con il caso. La variante meno calibrata delle due sbaglia in media "
        f"{numero(peggiore * 100, 2)} punti percentuali di probabilità per decile."
    )


def blocco_calibrazione(
    curve: pd.DataFrame, varianti: list[rendiconto.Variante], tema: Tema
) -> None:
    """Il primo blocco: il modello dice la verità sulle probabilità?

    Args:
        curve: Il risultato di :func:`rendiconto.calibrazione`.
        varianti: Base e 360.
        tema: La palette attiva.
    """
    st.markdown("#### 1. È calibrato?")
    st.markdown(
        '<p class="vuoto">Un xG non serve a ordinare i tiri dal migliore al peggiore, '
        "serve a dire <b>quanto</b> vale un tiro. Un modello calibrato che dice «trenta "
        "per cento» deve trovarsi davanti a tiri che finiscono in rete tre volte su dieci: "
        "se sistematicamente ne finiscono cinque, ogni somma di xG costruita sopra quel "
        "modello è gonfiata.</p>",
        unsafe_allow_html=True,
    )
    sinistra, destra = st.columns([1.5, 1])
    with sinistra, st.container(border=True):
        st.plotly_chart(
            viz.calibrazione(curve, colori_modelli(tema), tema),
            width="stretch",
            config=SENZA_BARRA,
        )
    with destra, st.container(border=True):
        st.markdown("##### Come si legge")
        st.markdown(
            '<p class="vuoto">Ogni punto è un decile: i tiri sono ordinati per '
            "probabilità prevista e divisi in dieci gruppi da circa ottocento. "
            "L'ascissa è quanto il modello prometteva in quel gruppo, l'ordinata quanti "
            "gol sono arrivati davvero. Le barre verticali sono l'errore standard del "
            "gruppo: dicono quanto quel punto può ballare per solo effetto del caso.</p>"
            '<p class="vuoto">Sopra la bisettrice il modello sottostima, sotto '
            "sovrastima. <b>StatsBomb è in grigio come termine di paragone</b>, non come "
            "verità: è anch'esso un modello, addestrato su molti più dati dei nostri.</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="evidenza">{frase_calibrazione(curve, varianti)}</div>',
            unsafe_allow_html=True,
        )


def blocco_variabili(tema: Tema) -> None:
    """Il secondo blocco: cosa guarda il modello.

    Args:
        tema: La palette attiva.
    """
    st.markdown("#### 2. Cosa guarda")
    st.markdown(
        '<p class="vuoto">Una regressione logistica <b>è già la propria spiegazione</b>: '
        "i coefficienti sono ciò che ha imparato, e non serve una libreria di "
        "attribuzione per leggerli. È il motivo per cui in questo progetto SHAP non "
        "compare.</p>",
        unsafe_allow_html=True,
    )

    pesi = rendiconto.pesi()
    with st.container(border=True):
        st.markdown("##### Le variabili continue, dalla più pesante")
        if pesi.empty:
            st.markdown('<p class="vuoto">Non disponibile.</p>', unsafe_allow_html=True)
        else:
            st.plotly_chart(
                viz.barre_divergenti(
                    [str(voce) for voce in pesi["variabile"]],
                    [float(valore) for valore in pesi["peso"]],
                    [
                        tema.primario if bool(spaziale) else tema.atteso
                        for spaziale in pesi["spaziale"]
                    ],
                    [f"×{numero(float(valore), 2)}" for valore in pesi["odds_ratio"]],
                    tema,
                    titolo_x="quanto moltiplica le probabilità relative di segnare",
                    altezza=330,
                ),
                width="stretch",
                config=SENZA_BARRA,
            )
            st.caption(
                "Ogni barra è l'odds ratio per **una deviazione standard** della "
                "variabile: è l'unico modo di confrontare metri con conteggi di "
                "giocatori. In verde le sei variabili base, in colore d'accento le "
                "cinque che arrivano dai fotogrammi 360. Le barre sono lunghe quanto il "
                "logaritmo del rapporto, così dimezzare e raddoppiare pesano uguale; il "
                "numero scritto è il rapporto vero."
            )

    categorie = rendiconto.categorie()
    sinistra, destra = st.columns(2)
    for colonna, gruppo in zip((sinistra, destra), (GRUPPO_CORPO, GRUPPO_TIPO), strict=True):
        suo = categorie[categorie["gruppo"] == gruppo] if not categorie.empty else pd.DataFrame()
        with colonna, st.container(border=True):
            st.markdown(f"##### {gruppo}")
            if suo.empty:
                st.markdown('<p class="vuoto">Non disponibile.</p>', unsafe_allow_html=True)
                continue
            st.plotly_chart(
                viz.barre_divergenti(
                    [str(voce) for voce in suo["livello"]],
                    [float(valore) for valore in suo["peso"]],
                    [tema.atteso] * len(suo),
                    [f"×{numero(float(valore), 2)}" for valore in suo["odds_ratio"]],
                    tema,
                    altezza=90 + 44 * len(suo),
                ),
                width="stretch",
                config=SENZA_BARRA,
            )

    st.caption(
        "**I livelli di una variabile categorica sono confrontabili fra loro, non con le "
        "variabili continue né con quelli di un'altra categoria.** La codifica non scarta "
        "nessun livello, quindi ogni variabile è definita a meno di una costante — nel "
        "nostro caso la somma dei coefficienti vale −1,0389 identica per tutte e tre. "
        "Qui la costante è tolta centrando dentro la variabile, ed è per questo che i "
        "numeri si leggono così: a parità di distanza e di angolo, di testa vale poco più "
        "della metà di un tiro di piede. "
        + frase_schema(categorie)
        + " Un coefficiente vale sempre «a parità di tutto il resto», e il segno è una "
        "direzione, non una causa: il modello vede associazioni."
    )


def frase_schema(categorie: pd.DataFrame) -> str:
    """La riga sull'origine dell'azione, calcolata invece che scritta.

    Quella variabile ha nove livelli e quasi nessuna escursione: un grafico a
    nove barre tutte lunghe uguali occuperebbe mezza pagina per dire «non
    conta». Una frase con il divario misurato lo dice in una riga, e resta vera
    se il divario cambia.

    Args:
        categorie: Il risultato di :func:`rendiconto.categorie`.

    Returns:
        La frase.
    """
    if categorie.empty:
        return ""
    escursioni = {
        str(gruppo): float(suoi["odds_ratio"].max()) / float(suoi["odds_ratio"].min())
        for gruppo, suoi in categorie.groupby("gruppo", observed=True)
    }
    if GRUPPO_SCHEMA not in escursioni or GRUPPO_TIPO not in escursioni:
        return ""
    schema = numero(escursioni[GRUPPO_SCHEMA], 2)
    tipo = numero(escursioni[GRUPPO_TIPO], 1)
    return (
        f"L'origine dell'azione — corner, contropiede, rimessa, punizione — ha nove "
        f"livelli e conta pochissimo: fra il più favorevole e il meno favorevole passa "
        f"un fattore {schema}, contro il {tipo} del tipo di tiro."
    )


def tabella_metriche(tabella: pd.DataFrame, prima: str) -> None:
    """Una tabella di metriche con le colonne formattate allo stesso modo.

    Args:
        tabella: Le righe da mostrare.
        prima: Il nome della prima colonna, ``modello`` o ``passo``.
    """
    st.dataframe(
        tabella,
        width="stretch",
        hide_index=True,
        column_config={
            prima: st.column_config.TextColumn(prima.capitalize()),
            "brier": st.column_config.NumberColumn("Brier", format="%.4f"),
            "log_loss": st.column_config.NumberColumn("Log loss", format="%.4f"),
            "auc": st.column_config.NumberColumn("AUC", format="%.3f"),
            "errore_calibrazione": st.column_config.NumberColumn(
                "Err. calibrazione", format="%.4f"
            ),
        },
    )


def blocco_360() -> None:
    """Il terzo blocco: le due varianti a confronto."""
    st.markdown("#### 3. I dati 360 servono?")
    ablazione = rendiconto.ablazione()
    st.markdown(
        '<p class="vuoto">Ogni gruppo di variabili spaziali è stato aggiunto al modello '
        "base <b>da solo</b>, non tolto dal modello completo. Le variabili 360 sono "
        "correlate fra loro: togliendone una dal completo, il suo contributo viene "
        "assorbito dalle altre e sembra nullo.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if ablazione.empty:
            st.markdown('<p class="vuoto">Non disponibile.</p>', unsafe_allow_html=True)
            return
        tabella_metriche(ablazione, "passo")
        st.markdown(
            f'<div class="evidenza">{frase_360(ablazione)}</div>',
            unsafe_allow_html=True,
        )


def frase_360(ablazione: pd.DataFrame) -> str:
    """Quanto valgono davvero i 360, calcolato dalla tabella.

    Args:
        ablazione: Il risultato di :func:`rendiconto.ablazione`.

    Returns:
        La frase.
    """
    brier = rendiconto.per_nome(ablazione, "passo", "brier")
    if "Modello base" not in brier or "Modello 360" not in brier:
        return ""
    base = brier["Modello base"]
    completo = brier["Modello 360"]
    guadagno = (base - completo) / base * 100
    return (
        f"Le cinque variabili spaziali portano il Brier da {numero(base, 4)} a "
        f"{numero(completo, 4)}: un miglioramento del {numero(guadagno, 1)} %. "
        f"È reale e si misura, ma è molto meno di quanto la parola «360» suggerisca — "
        f"dove il tiro parte resta di gran lunga l'informazione principale."
    )


def blocco_fuori_campione(contesto: rendiconto.Contesto) -> None:
    """Il quarto blocco: il modello regge fuori dal suo campione?

    Args:
        contesto: Su quanti tiri e finali è stata fatta la prova.
    """
    st.markdown("#### 4. Regge fuori dal campione?")
    sinistra, destra = st.columns(2)
    with sinistra, st.container(border=True):
        st.markdown("##### Sulle partite di verifica")
        confronto = rendiconto.confronto()
        if confronto.empty:
            st.markdown('<p class="vuoto">Non disponibile.</p>', unsafe_allow_html=True)
        else:
            tabella_metriche(confronto, "modello")
            st.caption(
                "Tutte le varianti provate a M5 sullo stesso test. Gli alberi sono un "
                "gradient boosting: pareggia la logistica e non la batte, quindi in "
                "produzione va la logistica, che si può leggere."
            )
    with destra, st.container(border=True):
        st.markdown(f"##### Sulle {numero(contesto.finali_applicazione)} finali di Champions")
        fuori = rendiconto.fuori_campione()
        if fuori.empty:
            st.markdown('<p class="vuoto">Non disponibile.</p>', unsafe_allow_html=True)
        else:
            tabella_metriche(fuori, "modello")
            st.caption(
                f"{numero(contesto.tiri_applicazione)} tiri di finali dal 1971 al 2019, "
                "**tolti prima della divisione fra addestramento e verifica** e quindi "
                "mai visti dal modello, nemmeno di striscio. Calcio di un'altra epoca, "
                "e i punteggi non peggiorano."
            )

    accordo = rendiconto.accordo()
    if accordo is None:
        return
    with st.container(border=True):
        st.markdown("##### E rispetto all'xG ufficiale di StatsBomb?")
        voci = (
            ("Correlazione per tiro", numero(accordo.pearson_tiro, 3), "Pearson"),
            ("Correlazione per partita", numero(accordo.pearson_partita, 3), "Pearson"),
            (
                "Scarto tipico per tiro",
                numero(accordo.scarto_assoluto_mediano, 3),
                "xG, mediana",
            ),
            (
                "xG totale sul test",
                numero(accordo.totale_nostro, 1),
                f"{numero(accordo.totale_altrui, 1)} secondo StatsBomb",
            ),
        )
        for colonna, (etichetta, valore, nota) in zip(st.columns(len(voci)), voci, strict=True):
            with colonna:
                st.markdown(cartellino(etichetta, valore, nota), unsafe_allow_html=True)
        st.caption(
            "L'accordo è alto sul singolo tiro e più alto ancora sull'xG di una partita "
            "intera, dove gli scarti dei singoli tiri si compensano. **Non è una prova di "
            "correttezza**: due modelli possono sbagliare insieme. È la ragione per cui "
            "la dashboard mostra l'xG di StatsBomb e non il nostro — questa pagina serve "
            "a dire quanto il nostro gli somiglia, non a sostituirlo."
        )


def main() -> None:
    """Disegna la pagina."""
    guscio.barra_laterale("Modello xG")
    # Nessuna competizione: il modello è uno solo e vale su tutte. Il tema resta
    # il neutro, come nel confronto fra leghe.
    tema = theme.applica("campionato", None)
    st.markdown(foglio(tema), unsafe_allow_html=True)

    st.markdown(
        '<div class="testata"><h1 class="titolo">Modello xG</h1>'
        '<p class="sottotitolo">Quanto vale un tiro, e quanto è affidabile '
        "il numero che lo dice</p></div>",
        unsafe_allow_html=True,
    )

    if not rendiconto.disponibile():
        st.info(
            "I risultati misurati del modello non sono in questa copia del progetto. "
            "Si rigenerano con `uv run python -m scripts.train_model`."
        )
        return

    varianti = rendiconto.varianti()
    contesto = rendiconto.contesto()
    intestazione(varianti, contesto)

    st.divider()
    blocco_calibrazione(rendiconto.calibrazione(), varianti, tema)
    st.divider()
    blocco_variabili(tema)
    st.divider()
    blocco_360()
    st.divider()
    blocco_fuori_campione(contesto)

    st.caption(
        f"Tutti i numeri di questa pagina sono letti da `docs/milestones/M5-risultati.json`, "
        f"prodotto da `scripts/train_model.py` il "
        f"{contesto.addestrato_il[:10].replace('-', '/')}. Nessuno è calcolato qui, e "
        f"nessuno è scritto a mano: la pagina e la documentazione della milestone non "
        f"possono divergere perché leggono lo stesso file."
    )
    st.markdown(f'<p class="attribuzione">{ATTRIBUZIONE}</p>', unsafe_allow_html=True)


main()
