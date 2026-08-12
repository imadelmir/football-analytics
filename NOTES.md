# NOTES — il diario degli inciampi

Ogni volta che qualcosa si rompe, una riga qui. Non e' un changelog: e' il
posto dove finisce cio' che non funzionava e perche'.

Questo file diventa la sezione `learnings` del case study nel portfolio, ed e'
la parte che distingue un case study da una brochure. Scritto a caldo vale;
ricostruito alla fine, no.

**Formato:** data, milestone-task, cosa si e' rotto, come si e' capito, come si
e' risolto.

---

## M1 — Fondamenta

### 2026-08-07 · M1-T3 · streamlit 1.61 e pyarrow 25 non stanno insieme

**Cosa:** risolvendo le dipendenze, chiedere sia `streamlit` sia `pyarrow`
all'ultima versione dava `streamlit==1.59.1` invece di `1.61.1`.

**Come si e' capito:** `uv pip compile` con `streamlit==1.61.1` fissato ha
mostrato che la 1.61.1 vincola `pyarrow<25`, quindi il risolutore stava
retrocedendo streamlit per tenere pyarrow 25.

**Risolto:** scelto `streamlit==1.61.1` + `pyarrow==24.0.0`. Fra le due,
streamlit e' la dipendenza che decide cosa la dashboard puo' fare
(`st.navigation`, `on_select` sulle tabelle); pyarrow 24 legge e scrive Parquet
esattamente come la 25.

### 2026-08-07 · M1-T2 · Windows blocca il Python scaricato da uv

**Cosa:** `uv python install 3.12` va a buon fine, ma il primo `uv sync` muore
mentre costruisce il pacchetto, con
`ImportError: DLL load failed while importing _socket: Un criterio di controllo
dell'applicazione ha bloccato il file`.

**Come si e' capito:** il percorso nella traccia dell'errore
(`AppData\Roaming\uv\python\cpython-3.12-...`) dice che il file bloccato non e'
del progetto, ma dell'interprete stesso. Il messaggio «criterio di controllo
dell'applicazione» e' Smart App Control / WDAC: impedisce l'esecuzione di
binari non firmati che compaiono nelle cartelle utente, e le distribuzioni
python-build-standalone usate da uv non sono firmate da Microsoft.

**Risolto:** installato il Python 3.12 ufficiale
(`winget install --id Python.Python.3.12 -e`), che e' firmato, poi
`uv python uninstall 3.12` per togliere di mezzo quello bloccato. Senza un
interprete gestito da usare, uv ripiega su quello di sistema. Il `.venv`
risultante gira su CPython 3.12.10.

**Perche' non si e' disattivato Smart App Control:** su Windows 11 e' una
scelta irreversibile — una volta spento non si riaccende senza reinstallare il
sistema. Cambiare interprete costa due comandi.

**Da ricordare per M7:** questo vincolo e' locale alla macchina di sviluppo.
Streamlit Community Cloud e i runner di GitHub Actions girano su Linux e non
hanno il problema; il `ci.yml` continua a usare il Python gestito da uv.

### 2026-08-07 · M1-T4 · lo stesso blocco colpisce mypy e coverage

**Cosa:** risolto il problema dell'interprete, `uv run mypy` falliva con
`ImportError: DLL load failed while importing internal`, e `pytest` emetteva
`CoverageWarning: Couldn't import C tracer`.

**Come si e' capito:** stesso criterio di controllo di prima, applicato pero'
ai binari delle librerie invece che a quelli di Python. `mypy` viene
distribuito compilato con mypyc e `coverage` include un tracciatore in C:
entrambi sono file `.pyd` non firmati, quindi entrambi bloccati. `ruff` invece
passa, perche' e' un singolo eseguibile Rust senza DLL da caricare.

**Il falso allarme:** il primo sospetto era che fossero bloccate anche pandas,
numpy e pyarrow — nel qual caso il progetto non sarebbe girato affatto su
questa macchina. Un `import` esplicito di tutte e sei le librerie pesanti ha
risposto `TUTTO OK`. Il comando sembrava bloccato ma era solo lento: `streamlit`
e `sklearn` al primo import impiegano diversi secondi, e l'antivirus che
ispeziona ogni DLL peggiora l'attesa. **Lezione: prima di dichiarare un blocco,
verificare che non sia solo lentezza.**

**Risolto:** `mypy` installato da sorgente, in versione pura Python, tramite la
variabile d'ambiente utente `UV_NO_BINARY_PACKAGE=mypy` piu'
`uv sync --reinstall-package mypy`. Costruzione in 18.9s, poi
`Success: no issues found in 3 source files`. Per `coverage` e' bastato
`disable_warnings = ["no-ctracer"]`: la libreria ripiega gia' da sola sul
tracciatore Python e i numeri sono identici.

**Perche' una variabile d'ambiente e non una riga in `pyproject.toml`:** il
blocco e' un fatto di questa macchina, non del progetto. Su Linux — dove girano
sia GitHub Actions sia Streamlit Cloud — mypy compilato funziona, e rallentare
la CI per un vincolo locale sarebbe la scelta sbagliata. Il repository resta
pulito; il rimedio vive sul computer che ha il problema.

---

## M2 — Ingestione

### 2026-08-07 · M2-T1 · il piano si sbagliava su meta' delle competizioni

**Cosa:** il test di rete di M2-T1 e' fallito su due competizioni su quattro.
Ligue 1 2021/22: attese 380 partite, trovate **26**. Bundesliga 2023/24:
attese 306, trovate **34**. Serie A 2015/16 e finali di Champions tornavano.

**Come si e' capito:** 26 e 34 non sono numeri casuali. 34 e' una stagione
intera di Bundesliga **per una squadra sola**; 26 sono le presenze di un
giocatore in un campionato. StatsBomb non pubblica sempre stagioni complete:
a volte rilascia il sottoinsieme legato a un tema — la biografia di Messi, la
stagione imbattuta del Leverkusen.

**Perche' era grave:** quelle due erano le uniche fonti di dati 360 del piano.
Insieme dovevano dare 686 partite e ne danno 60. L'intero confronto fra
modello base e modello 360 — la parte piu' raccontabile del progetto — si
sarebbe addestrato su un decimo dei dati previsti, e i 27.000 tiri stimati
sarebbero stati circa 1.500.

**Risolto:** scritto `scripts/esplora_open_data.py`, che conta le partite di
ogni stagione dell'Open Data e ne riporta la disponibilita' dei freeze frame.
Da li' e' emerso il quadro reale e le fonti sono state riscelte.

**Cosa insegna:** il piano si basava su numeri plausibili — 380 partite sono
un campionato a venti squadre, 306 uno a diciotto — ma nessuno li aveva
verificati. Un numero che *sembra* giusto e' il tipo peggiore di errore,
perche' non attira controlli. Il task che li ha verificati esisteva apposta, ed
e' l'unico motivo per cui il problema e' emerso al secondo task di M2 invece
che a M5.

### 2026-08-07 · M2-T1 · `bool(NaN)` vale True

**Cosa:** la prima versione di `esplora_open_data.py` dichiarava i dati 360
disponibili per tutte e quaranta le stagioni, comprese quelle che il piano
sapeva non averli.

**Come si e' capito:** il risultato era troppo bello. Se *tutto* ha i 360, la
domanda centrale del progetto non ha senso — e un controllo che risponde
sempre si' non e' un controllo.

**La causa:**

```python
ha_360 = bool(voce.get("match_available_360"))  # sbagliato
```

Quando il campo manca, pandas restituisce `NaN`. E `bool(NaN)` in Python vale
`True`, perche' NaN e' un float diverso da zero. La correzione e'
`bool(pd.notna(...))`.

**Cosa insegna:** con pandas, il valore mancante non e' `None` e non e' falso.
Ogni controllo di verita' su una cella che puo' essere vuota va scritto con
`pd.notna` o `pd.isna`, mai con `if valore:`. Vale per tutto M3, dove i campi
opzionali degli eventi StatsBomb sono la norma.

### 2026-08-07 · M2-T2 · una stima sbagliata del 50 %, e il modo di accorgersene

**Cosa:** avevo stimato circa 4,5 GB per lo scaricamento completo. Misurando i
file veri di Euro 2020 — 516,9 MB per 51 partite — l'estrapolazione dice **7 GB**.

**Come si e' capito:** guardando il disco invece dei propri calcoli. La stima
veniva da un'ipotesi sulla dimensione media di un file di eventi; il numero
reale e' 3,1 MB per gli eventi e 7,1 MB per i freeze frame.

**Cosa insegna:** la stima non era irragionevole, era solo non misurata — e
nessuno l'avrebbe controllata, perche' «circa 4,5 GB» non ha l'aria di un
numero da verificare. E' lo stesso meccanismo che aveva reso invisibile
l'errore del piano sulle 380 partite di Ligue 1. Un numero plausibile e non
misurato e' il posto dove gli errori si nascondono meglio.

---

## M3 — Trasformazione

### 2026-08-07 · M3-T1 · i freeze frame erano ovunque, e non me n'ero accorto

**Cosa:** aprendo un evento di tiro per capire come costruire `shots.parquet`,
`shot.freeze_frame` era li' dentro — posizione, nome e ruolo di ogni giocatore
al momento del tiro. Non nei file `three-sixty/`: **dentro l'evento**.

**Come si e' capito:** contando. Un campione di tre partite di Serie A 2015/16
e tre finali di Champions, competizioni che il piano dava per prive di dati
spaziali:

| Competizione | Tiri | Con `shot.freeze_frame` |
| --- | ---: | ---: |
| Serie A 2015/16 | 66 | 64 (97 %) |
| Euro 2020 | 1.289 | 1.247 (97 %) |
| Finali Champions 2017-2019 | 85 | 84 (99 %) |

**Perche' e' la scoperta piu' grossa finora:** l'intera architettura si reggeva
sull'idea che solo alcune competizioni permettessero il modello con le
variabili spaziali. Era falso. La domanda centrale del progetto — quanto vale
sapere dove sono i difensori — passa da ~5.500 tiri a ~44.000, e con quel
volume la differenza fra i due modelli diventa misurabile invece che
indicativa.

**I due freeze frame, per non confonderli mai piu':**

| | `shot.freeze_frame` | file `three-sixty/` |
| --- | --- | --- |
| Dove | dentro l'evento di tiro | file separato, 6,5 MB a partita |
| Quando | solo al momento del tiro | tutti i 3.400 eventi |
| Contiene | posizione, **nome**, **ruolo**, compagno si/no | posizione, compagno, portiere, attore |
| In piu' | — | area inquadrata dalla telecamera |
| Disponibile | ~97 % dei tiri, ovunque | solo alcune competizioni |

Per il modello xG serve il primo, ed e' anche il piu' ricco: sapere che il
difensore piu' vicino e' un centrale invece di un terzino e' informazione che
i file 360 non hanno.

**Cosa insegna:** avevo verificato *quali competizioni hanno i file 360* e mi
ero fermato li', perche' la risposta confermava il piano. Non avevo verificato
*cosa serve davvero al modello*. Confermare l'ipotesi che si aveva in testa e'
il momento in cui si smette di guardare — ed e' esattamente quando bisognerebbe
guardare meglio.

### 2026-08-07 · M3-T1 · la fixture sbagliata, smascherata dal suo stesso test

**Cosa:** avevo scritto una fixture dichiarando che la partita finiva 2 a 2. Il
test e' fallito: gli eventi dicevano 2 a 1.

**Chi aveva ragione:** il codice. Contando a mano — un gol su azione della
Casalinga, un autogol a suo favore, un gol dell'Ospite nei supplementari, due
rigori finali che non contano — fa 2 a 1. Il numero nei metadati era mio, e
sbagliato.

**Cosa insegna:** e' esattamente il meccanismo che dovra' proteggere il
progetto quando i dati saranno 1.753 partite invece di una inventata. Se un
test scritto apposta per verificare i risultati smaschera chi l'ha scritto,
funziona. E la fixture corretta e' finita per essere migliore: i modi
plausibili di sbagliare quel conteggio sono **tre** — ignorare l'autogol
(1 a 1), includere i rigori finali (3 a 1), contare l'autogol per entrambe le
squadre (2 a 2) — e ora c'e' un test per ciascuno.

### 2026-08-07 · M3-T2 · i minuti non si sommano

**Cosa:** calcolando i minuti giocati come somma delle durate degli spezzoni di
`positions`, alcuni giocatori risultavano con valori negativi.

**Come si e' capito:** guardando uno spezzone di Federico Chiesa in
Italia-Austria:

```
da 108:54 (p4) a  83:34 (p2)   inizio "Tactical Shift"    fine "Substitution - On"
da  83:34 (p2) a  None         inizio "Substitution - On" fine "Final Whistle"
```

Il primo ha `to` **precedente** a `from`. Non e' un caso isolato: succede
nell'1,3 % degli spezzoni, 30 volte su 2.320 nelle sole 57 partite scaricate.

**Risolto:** non sommando. Un giocatore entra in campo una volta ed esce una
volta; gli spezzoni intermedi esistono solo per registrare i cambi di
posizione. Il tempo in campo e' quindi `max(to) - min(from)`, e con quella
formula l'anomalia diventa innocua — nel caso di Chiesa da' i 61 minuti
corretti invece dei 31 che darebbe la somma.

**Cosa insegna:** quando un dato ha una struttura ridondante — spezzoni che
insieme ricostruiscono un intervallo — conviene calcolare sull'**invariante**
(l'intervallo complessivo) invece che sui pezzi. I pezzi possono essere
incoerenti fra loro; l'invariante no.

### 2026-08-07 · M3-T2 · 129 minuti in campo

**Cosa:** cinque giocatori francesi risultavano aver giocato 129 minuti.

**Come si e' capito:** il massimo teorico e' 120, supplementari compresi. La
partita era Francia-Svizzera, finita ai rigori: prendendo `max(Half End)` su
tutti i periodi si prendeva anche la fine del **quinto**, cioe' dei rigori, che
cade al 128'.

**Risolto:** la durata della partita considera solo i periodi fino al quarto.
Quattro partite di Euro 2020 ne erano affette.

**Cosa insegna:** e' la terza volta che il periodo 5 si intrufola dove non
dovrebbe — prima nei gol, poi nei tiri delle statistiche giocatore, ora nella
durata. I rigori finali sono eventi a tutti gli effetti ma non sono gioco, e
ogni aggregazione va scritta chiedendosi se li vuole dentro. Ora c'e' una
costante, `ULTIMO_PERIODO_DI_GIOCO`, invece di un `5` sparso nel codice.

### 2026-08-07 · M3-T2 · la prima verifica contro il mondo esterno

**Cosa:** la classifica marcatori calcolata da `player_stats.parquet` su Euro
2020 e' Ronaldo 5, Schick 5, poi Lukaku, Forsberg, Kane e Benzema a 4.

**Perche' conta:** e' la classifica ufficiale del torneo — Ronaldo e Schick
vinsero la Scarpa d'Oro a pari merito. Tutte le verifiche fino a qui erano
**interne**: i gol tornano con i risultati scritti nello stesso file. Questa e'
la prima che si confronta con un fatto pubblico, verificabile da chiunque.

Una pipeline puo' essere internamente coerente e sbagliata: basta un errore
sistematico che si propaga ovunque. Il confronto con l'esterno e' l'unico che
lo smaschera, e vale la pena cercarne uno per ogni tabella prodotta.

### 2026-08-07 · M3-T4 · un test che guastava la tabella con lo stesso valore

**Cosa:** `test_un_gol_incoerente_con_l_esito_viene_segnalato` falliva con
`DID NOT RAISE`.

**Come si e' capito:** il test scriveva `gol = True` sulla prima riga di
`shots` per creare un'incoerenza. Ma la prima riga e' il gol del 12': aveva
gia' `gol` vero. Il controllo non scattava perche' non c'era niente da trovare.

**Risolto:** `gol = False`, piu' un'asserzione che verifica il valore di
partenza prima di guastarlo — cosi' l'errore non puo' ripetersi in silenzio.

**Cosa insegna:** e' esattamente cio' contro cui metteva in guardia la
docstring del file, «un controllo mai visto fallire non e' un controllo». Vale
anche per il test stesso: un test negativo che passa perche' non ha davvero
introdotto l'anomalia e' peggio di nessun test, perche' da' fiducia
ingiustificata. Quando si scrive un test che si aspetta un fallimento, va
verificato **anche** che la condizione di partenza fosse sana.

### 2026-08-07 · M2-T4 · l'indice competizioni mente per omissione

**Cosa:** avevo dichiarato la Coppa d'Africa 2023 coperta dai dati 360.
Scaricandola, il manifest ha riportato **1 partita su 52**.

**Come si e' capito:** dal peso. 134 MB contro i ~530 delle altre competizioni
con i 360. Un numero che non torna con gli altri numeri.

**La causa:** il campo `match_available_360` dell'indice competizioni e'
**a livello di competizione**, e diventa non nullo anche se una sola partita ha
i file. Il dato affidabile e' `match_status_360` nel file delle partite, che ha
quattro valori:

| valore | significato |
| --- | --- |
| `available` | il file esiste |
| `processing` | StatsBomb lo sta producendo |
| `scheduled` | ha in programma di produrlo |
| `unscheduled` | non e' previsto |

Solo il primo e' un file. Gli altri sono promesse — e la Premier League 2015/16
ne ha 200 in `processing` e 180 in `scheduled`, cioe' zero file e 380 promesse.

**Risolto:** Coppa d'Africa portata a `PARZIALE`, e il test di rete riscritto
per contare gli stati partita per partita invece di leggere l'indice.
Rinominato anche `TORNEI_360` in `TORNEI`: il nome vecchio affermava una cosa
falsa.

**Il modello non ne risente:** nella Coppa d'Africa `shot.freeze_frame` c'e'
nel 95 % dei tiri. E' la conferma pratica di quanto contasse distinguere i due
tipi di fotogramma.

**Cosa insegna, ed e' il filo di tutta M2:** ogni volta che mi sono sbagliato,
la fonte sbagliata era **quella piu' comoda da leggere**. Un numero scritto nel
piano invece di contare le partite. Un campo aggregato invece di scorrere le
righe. Una cella che sembra falsa invece di chiedere a `pd.notna`. La fonte
giusta costava sempre un passo in piu', e quel passo e' esattamente il lavoro.

### 2026-08-07 · M3-T3 · lo stesso errore due volte, con un'altra maschera

**Cosa:** la costruzione del magazzino su 1.753 partite si e' fermata su
Lorient-Marsiglia: risultato calcolato 1-0, ufficiale 1-1.

**Come si e' capito:** guardando gli eventi. Il gol c'era, al 45' del secondo
tempo. Ma:

```
evento:    team = "Marseille"
metadati:  ospite = "Olympique de Marseille"
```

Lo stesso club con due nomi. Contavo i gol per **nome squadra**, e il nome
negli eventi non e' quello nel file delle partite: il Marsiglia risultava a
zero. Succede a due squadre su 152, Marsiglia e Caen, entrambe di Ligue 1.

**Risolto:** confronto per identificativo, e i nomi presi sempre dal file
partite cosi' che il magazzino ne abbia una grafia sola. Aggiunta
`nome_squadra(meta, id)`, che e' l'unico punto in cui un identificativo diventa
un nome.

**Cosa insegna, e questa e' la parte che conta:** e' **lo stesso errore** dei
giocatori sdoppiati di poche ore prima — «Danny Ward» e «Daniel Ward» — con
un'altra maschera. Li' avevo scritto nel commit *«l'identita' e'
l'identificativo, il nome e' un attributo»*, l'avevo applicato ai giocatori, e
non mi era venuto in mente di applicarlo alle squadre.

Imparare una lezione su un caso non basta: va cercato **dove altro vale lo
stesso principio**. Ogni volta che una chiave e' una stringa leggibile invece
di un identificativo, il difetto e' gia' li' e aspetta solo il dato giusto per
manifestarsi. Nel magazzino restano da controllare le competizioni, che pero'
usano una chiave scelta da noi e non da StatsBomb.

**Nota di merito al controllo:** questo non l'ha trovato una lettura del
codice. L'ha trovato `verifica_risultato`, su una partita fra 1.753, mesi prima
che qualcuno guardasse una dashboard.

### 2026-08-07 · M3-T4 · due tiri fuori dal campo, e non era un errore

**Cosa:** sul dataset completo il controllo delle coordinate ha segnalato due
tiri con `x` oltre la linea di porta: 120,2 e 120,1 su un campo lungo 120.

**Come si e' capito:** guardandoli. Entrambi hanno `y` vicino a 1, cioe' sono
calciati dalla linea di fondo all'altezza della bandierina, ed entrambi hanno
l'xG **minimo** possibile, 0,00018. Un pallone calciato sulla linea puo' avere
il centro qualche centimetro oltre: e' rumore di misura del tracciamento, non
un dato sbagliato.

**Risolto:** una tolleranza esplicita di un metro, con il perche' scritto
accanto alla costante.

**Cosa insegna:** il primo istinto e' stato «il controllo ha trovato qualcosa,
quindi i dati sono sbagliati». Ma un controllo puo' essere **troppo severo**, e
quello e' un difetto peggiore di uno troppo permissivo: un controllo che
segnala falsi allarmi viene disattivato, e da quel momento non trova piu'
nemmeno i problemi veri. Due tiri su 44.000 non giustificano di bloccare la
pipeline; una tolleranza documentata si'.

La differenza fra questo caso e quello del Marsiglia e' tutta qui: li' il
controllo aveva ragione e ho corretto il codice, qui aveva torto e ho corretto
il controllo. Distinguere i due casi e' il lavoro — allentare sempre e'
comodo, irrigidire sempre e' inutile.

### 2026-08-07 · M3 · la verifica esterna che vale piu' di tutte le altre

**Cosa:** le classifiche marcatori calcolate dal magazzino, confrontate con i
fatti pubblici:

| Giocatore | Competizione | Calcolati | Ufficiali |
| --- | --- | ---: | ---: |
| Luis Suarez | La Liga 2015/16 | 40 | 40 (Pichichi) |
| Gonzalo Higuain | Serie A 2015/16 | 36 | 36 (record) |
| Cristiano Ronaldo | La Liga 2015/16 | 35 | 35 |
| Lionel Messi | La Liga 2015/16 | 26 | 26 |
| Zlatan Ibrahimovic | Ligue 1 2015/16 | 36 | **38** |

**Lo scarto e' la parte interessante.** Non e' un difetto della pipeline: alla
Ligue 1 2015/16 mancano 3 partite su 380 — le giornate 14, 23 e 36 ne hanno
nove invece di dieci — e il PSG e' fra le sei squadre a cui ne manca una.

**Cosa insegna:** sapere **quale** partita manca e' cio' che separa un dato
incompleto da un dato sbagliato. Un totale che non torna, da solo, e' inutile;
un totale che non torna **e di cui si conosce la ragione esatta** e' una
dichiarazione onesta che si puo' mettere in una pagina Metodologia.

Ed e' la ragione per cui vale la pena cercare una verifica esterna per ogni
tabella prodotta: quella interna dice che i numeri sono coerenti fra loro, non
che sono veri.

---

## M4 — Esplorazione

### 2026-08-07 · M4-T1 · un numero che non tornava con un altro numero

**Cosa:** guardando la conversione per numero di avversari nel fotogramma, il
gruppo con zero o un avversario aveva conversione **12,7 %** e xG medio
**0,788**. Un xG da rigore con una conversione da tiro da trenta metri.

**Come si e' capito:** non era un errore, era una **contraddizione interna**.
Ogni altro gruppo aveva conversione e xG allineati; solo quello no. Un numero
che non torna con un altro numero e' un invito a guardare, non un'anomalia da
annotare.

Erano rigori. E allora:

| Rigori | Numero | Conversione |
| --- | ---: | ---: |
| **senza** fotogramma | 426 | **81,9 %** |
| **con** fotogramma | 54 | **11,1 %** |

Il fotogramma di un rigore contiene **solo il portiere**, e StatsBomb lo allega
quasi esclusivamente quando il rigore non entra: serve a registrare la
posizione del portiere per analizzare la parata.

**Perche' e' grave:** la presenza del dato dipende dal risultato. E'
distorsione da selezione, e un modello la impara volentieri — imparerebbe
«fotogramma presente, quindi sbagliato», che non e' calcio ma un artefatto di
raccolta. Sarebbe entrata in M5 senza che niente segnalasse un problema,
perche' non c'e' nessun errore da intercettare: i dati sono corretti, e' il
**modo in cui esistono** a essere informativo nel modo sbagliato.

**Risolto:** i rigori restano fuori dal modello — che e' comunque la prassi,
hanno xG fisso — e `ha_fotogramma` non sara' mai una variabile.

**La verifica che salva il progetto:** sui tiri su azione la copertura del
fotogramma e' **100 %**, 41.179 su 41.179. La distorsione e' confinata ai
rigori, quindi il confronto fra modello base e modello spaziale si puo' fare
su tutti i tiri di gioco senza correzioni. Se la copertura fosse stata parziale
anche li', M5 sarebbe stato un problema molto diverso.

**Cosa insegna:** e' il primo difetto della giornata che **nessun controllo
automatico avrebbe potuto trovare**. Non c'e' un `NaN`, un duplicato, un totale
che non torna: i dati sono tutti validi. Emerge solo guardando le distribuzioni
e chiedendosi perche' due numeri non stiano insieme. E' esattamente il lavoro
per cui M4 esiste, ed e' il motivo per cui saltarla per arrivare prima al
modello sarebbe stato un pessimo affare.

### 2026-08-07 · M4-T1 · la regola generale su Smart App Control

**Cosa:** `uv run jupyter nbconvert` bloccato con
`[WinError 4551] Un criterio di controllo dell'applicazione ha bloccato il
file`. Terza manifestazione dello stesso vincolo dopo l'interprete Python di uv
(M1-T2) e i binari mypyc di mypy (M1-T4).

**Come si e' capito:** il blocco non riguardava `jupyter` ma
`jupyter-nbconvert.exe`, il piccolo eseguibile che uv genera in
`.venv\Scripts\` per ogni comando dichiarato da un pacchetto. Sono binari non
firmati creati in una cartella utente: il profilo esatto che la policy blocca.

**Risolto, e vale come regola generale su questa macchina:**

> Invocare il **modulo** Python, non l'eseguibile generato.
> `uv run python -m nbconvert` invece di `uv run jupyter nbconvert`.

Cosi' gira `python.exe`, che e' una copia del Python 3.12 ufficiale ed e'
firmato — ed e' il motivo per cui `uv run python` ha sempre funzionato mentre
`uv run mypy` no. Il modulo viene importato, non eseguito come binario a se'.

**Cosa insegna:** i primi due casi li avevo risolti uno per uno, con due
rimedi diversi — cambiare interprete, ricompilare mypy da sorgente. Solo al
terzo ho visto che erano **la stessa cosa**, e che esiste un rimedio unico che
li copre tutti. E' lo stesso schema del gol del Marsiglia: la lezione
imparata su un caso non era stata cercata altrove. Tre occorrenze sono il
momento in cui conviene fermarsi e chiedersi qual e' la regola, invece di
applicare la terza toppa.

---

## M5 — Modello xG

### 2026-08-07 · M5-T2 · il cono e' piu' stretto di come lo si immagina

**Cosa:** scrivendo i test di `nel_cono` mi aspettavo che un difensore a
`(112, 38)`, con il tiro da `(110, 40)`, fosse davanti al pallone. E' a 2,8
metri, sembra addosso.

**Non lo e'.** A `x = 112` il triangolo fra il tiro e i due pali e' largo
appena 1,6 metri, da `y = 39,2` a `y = 40,8`. Quel difensore e' di **fianco**,
non davanti.

**Cosa insegna:** la geometria vicino alla porta e' controintuitiva perche' il
cono si stringe rapidamente man mano che ci si avvicina. Un test scritto «a
occhio» avrebbe sancito il comportamento sbagliato, e da quel momento sarebbe
stato il codice a doversi adeguare al test. C'e' un test apposta, con il
calcolo nel commento.

### 2026-08-07 · M5-T2 · il portiere e una relazione a U

**Cosa:** la conversione in funzione di quanto il portiere e' uscito dalla
linea, su 43.179 tiri:

| Portiere uscito di | Tiri | Conversione |
| --- | ---: | ---: |
| ≤ 0,5 m — sulla linea | 855 | 14,3 % |
| 0,5-1,5 m | 12.237 | 8,3 % |
| 1,5-3 m | 18.359 | **7,1 %** |
| 3-6 m | 9.564 | 11,1 % |
| oltre 6 m | 2.128 | **26,7 %** |

**Non e' monotona: e' a U.** Un portiere incollato alla linea concede il doppio
del punto migliore; uno uscito troppo concede quasi il quadruplo. Il minimo sta
fra 1,5 e 3 metri.

**Perche' conta piu' del calcio:** una **regressione logistica non puo'
rappresentare una U**. E' monotona nei predittori per costruzione, quindi su
questa variabile vedra' una retta dove c'e' una parabola, e ne ricavera' un
coefficiente vicino a zero — cioe' concludera' che la posizione del portiere
non conta. Un gradient boosting la cattura senza sforzo.

E' esattamente il motivo per cui M5-T4 e M5-T5 chiedono due modelli. La
differenza: adesso sappiamo **in anticipo dove** il secondo dovrebbe vincere,
quindi il confronto diventa una previsione da verificare invece di un numero
da commentare a posteriori.

### 2026-08-07 · M5-T2 · StatsBomb usa gia' i difensori nel cono

**Cosa:** raggruppando per difensori nel cono, l'xG medio di StatsBomb segue la
conversione reale quasi perfettamente — 0,129 · 0,060 · 0,051 · 0,045 contro
0,137 · 0,059 · 0,046 · 0,045.

**Cosa significa:** il loro modello vede gia' il fotogramma. Il nostro modello
spaziale **non li battera'**, e sarebbe ingenuo aspettarselo.

**Conseguenza sul racconto del progetto:** il confronto che ha senso non e'
«noi contro StatsBomb» ma «base contro spaziale», dove misuriamo quanto vale
un'informazione che loro hanno gia'. Il confronto con StatsBomb (M5-T8) resta,
ma come **prova di onesta'**: dichiarare di quanto si e' peggiori di un
fornitore professionale e' piu' credibile che scegliere una metrica su cui si
vince.

### 2026-08-07 · M5-T3 · una soglia tarata sull'intuizione invece che sulla statistica

**Cosa:** il test che verifica che la divisione train/test non sbilanci la
classe positiva chiedeva che le due frequenze di gol differissero di meno di
0,02. Sul campione sintetico dava 0,0984 contro 0,1212 — differenza 0,0228,
fallito.

**Come si e' capito:** invece di alzare la soglia, ho misurato sui dati veri.
Li' la differenza e' **0,0005**, cioe' 0,2 deviazioni standard, e su dieci seed
diversi il massimo e' 0,0079. La divisione funziona benissimo: era il test a
essere sbagliato.

**La causa:** il campione sintetico ha 12.500 tiri, i dati veri 43.179. Lo
scarto atteso per puro caso e' tre volte piu' grande sul primo. Una soglia
**fissa** e' implicitamente tarata sulla dimensione del campione con cui e'
stata scritta, e trasferirla altrove non ha senso.

**Risolto:** soglia espressa in **deviazioni standard** invece che in punti
percentuali:

```python
errore_standard = math.sqrt(p * (1 - p) * (1 / len(train) + 1 / len(test)))
assert abs(gol_train - gol_test) < 4 * errore_standard
```

Cosi' vale a qualunque dimensione del campione, e dice una cosa precisa —
«questa differenza e' compatibile con il caso» — invece di una arbitraria.

**Cosa insegna:** e' il caso gemello dei due tiri a venti centimetri oltre la
linea. Li' il controllo era troppo severo e i dati erano sani; qui la soglia
era arbitraria e i dati erano sani. In entrambi i casi la tentazione era
allentare il numero finche' passava, e in entrambi la risposta giusta e' stata
**capire da dove doveva venire il numero**. Una soglia che non si sa derivare
e' una soglia che prima o poi verra' allentata a caso.

---

## M5-T4 — Avevo silenziato mypy invece di ascoltarlo

**Il sintomo:** sette errori tutti uguali, `Unused "type: ignore" comment`, in
`tests/test_modello.py`.

**La causa:** avevo dichiarato la fixture `addestrato` come
`tuple[object, ...]`, perche' importare `Pipeline` in un file di test mi
sembrava una complicazione. Ma un `object` non ha `.predict_proba`, quindi ogni
uso della fixture diventava un errore di tipo, e avevo messo un
`# type: ignore[arg-type]` su ognuno. Poi ho corretto un'altra cosa, mypy ha
smesso di aver bisogno di quei commenti, e me li ha segnalati tutti e sette.

**Risolto:** il tipo vero, `tuple[Pipeline, pd.DataFrame, pd.DataFrame]`, con
l'import sotto `TYPE_CHECKING`. Zero `type: ignore` rimasti.

**Cosa insegna:** avevo scritto sette silenziatori per evitare un import. Un
`type: ignore` non e' mai una correzione — e' una nota che dice «so meglio io»,
e va scritta solo quando e' vero. Le sette righe erano il segnale che il tipo
dichiarato era sbagliato, non che mypy fosse pedante. Il fatto che sia stato
mypy stesso a farmele notare, quando sono diventate inutili, e' il motivo per
cui `warn_unused_ignores` va tenuto acceso.

## M5-T4 — Il numero che dice se il modello e' calibrato

**Non e' un problema, e' il primo risultato del progetto**, ma vale la pena
annotarlo perche' conferma una scelta fatta al buio settimane fa.

```
xG medio previsto  0,0950
gol reali          0,0951
```

Su 8.597 tiri mai visti. Uno scarto di **un decimillesimo**.

Quel numero e' il pagamento diretto della decisione di **non** usare
`class_weight="balanced"`. Con un gol ogni dieci tiri, bilanciare le classi e'
la prima cosa che qualunque tutorial suggerisce: migliora l'AUC e fa sentire il
modello «piu' bravo». Avrebbe anche spinto le probabilita' verso il 50 %,
producendo un xG che dice 0,4 dove la realta' e' 0,1 — un modello che ordina
bene i tiri e mente su quanto valgono. Per un classificatore sarebbe un
dettaglio; per un xG e' il prodotto.

C'era gia' un test che avrebbe fallito se avessi cambiato idea. Adesso c'e'
anche la misura sui dati veri.

**Cosa insegna:** il consiglio piu' diffuso su un problema sbilanciato e'
sbagliato **per questo problema specifico**, e non perche' sia sbagliato in
generale. Dipende da cosa deve produrre il modello: un'etichetta o un numero.
La domanda «cosa mi serve in uscita» va fatta prima di scegliere gli
iperparametri, non dopo aver guardato le metriche.

## M5-T4 — Un Brier score da solo non vuol dire niente

**Il sintomo:** il modello dava Brier 0,0739 e StatsBomb 0,0686. Stavo per
scrivere «siamo vicini» senza sapere cosa volesse dire vicini.

**La causa:** il Brier score non ha uno zero naturale. Su un problema dove si
segna il 9,5 % delle volte, un modello che risponde **sempre 0,0951** ottiene
gia' 0,0861 senza aver imparato nulla. Confrontare 0,0739 con 0,0686 senza
sapere che si parte da 0,0861 e' come confrontare due tempi sui 100 metri senza
sapere dov'e' la partenza.

**Risolto:** riportare entrambi come miglioramento rispetto al riferimento.

| | Brier | Miglioramento |
| --- | ---: | ---: |
| Sempre la media | 0,08606 | 0 % |
| Modello base | 0,07387 | 14,2 % |
| StatsBomb | 0,06858 | 20,3 % |

Detto cosi' il divario si legge: il modello base cattura **il 70 % di quello
che cattura StatsBomb**, con sei variabili e nessuna informazione spaziale.

**Cosa insegna:** ogni metrica va accompagnata dal punteggio del modello piu'
stupido possibile. E' l'unica cosa che trasforma un numero in
un'informazione — e nel caso del Brier score il modello stupido e' bravissimo,
perche' rispondere sempre «quasi mai» su un evento raro e' quasi sempre giusto.

## M5-T5 — Ho scritto un numero che non avevo calcolato

**Il sintomo:** nella tabella di M5-T4 il log loss del modello di riferimento
era **0,31703**. Il valore vero e' **0,31418**.

**La causa:** il Brier del riferimento ha una formula chiusa che conosco a
memoria, `p(1-p)`, e quello era giusto. Il log loss ha anch'esso una formula
chiusa — `-(p·ln p + (1-p)·ln(1-p))` — ma invece di calcolarla l'ho **stimata a
mente**, e poi l'ho scritta con cinque decimali. La precisione tipografica ha
fatto passare per misura quella che era un'approssimazione.

E' finito anche nel messaggio del commit `fbb48bb`, dove resta: `main` e'
protetto contro la riscrittura, e va bene cosi'. Una correzione visibile vale
piu' di una cronologia ripulita.

**Risolto:** il riferimento smette di essere un numero e diventa una funzione,
`metriche.riferimento()`, con due test che confrontano ciascuna formula chiusa
con il calcolo diretto sui dati. Non c'e' piu' nessun punto del progetto in cui
quel numero si possa scrivere a mano.

**Cosa insegna:** il numero di decimali e' un'affermazione. Cinque decimali
dicono «ho misurato»; se non e' vero, e' un'affermazione falsa messa li' senza
accorgersene. La regola operativa e' piu' semplice del principio: **se un
numero ha una formula, la formula va nel codice**, anche quando e' cosi'
elementare che sembra piu' veloce farla a mente. Soprattutto allora.

## M5-T5 — La terza soglia scritta senza derivarla

**Il sintomo:** il test che verifica la previsione registrata — «gli alberi
battono la logistica su una relazione a U» — chiedeva agli alberi un guadagno
sul Brier superiore al **20 %**. Misurato: **2,3 %**. Il test sarebbe fallito
accusando il codice.

**La causa:** su quei dati sintetici il guadagno massimo **possibile** e' circa
l'**8 %**. Con probabilita' vere fra 0,05 e 0,40, quasi tutto l'errore
quadratico e' rumore che nessun modello puo' togliere: anche conoscendo la
probabilita' esatta di ogni tiro si scende solo da 0,1389 a 0,1280. Avevo
chiesto piu' del massimo teorico.

**Risolto:** il generatore restituisce anche `probabilita_vera`, cioe' la
probabilita' che ha prodotto l'esito, e il test costruisce l'**oracolo** — il
modello imbattibile. Le soglie sono frazioni dell'ottenibile, non punti di
Brier. Misurato su sei semi: la logistica cattura da -6 % a -1 % dell'oracolo,
gli alberi dal 25 % al 71 %.

**Cosa insegna:** e' la **terza** volta in questo progetto che scrivo una soglia
senza saperla derivare — dopo il 2 % sulla frequenza dei gol e dopo lo 0,31703
qui sopra. Il denominatore giusto non e' mai zero: la domanda non e' «quanto
guadagna il modello», e' «quanto **si puo'** guadagnare, e quanta parte ne
prende». Quando i dati sono sintetici quel massimo si puo' calcolare
esattamente, quindi non c'e' nessuna scusa per indovinarlo.

Vale anche per i dati veri: il 14,2 % del modello base non e' su 100, e' su un
massimo che non conosciamo. Il numero utile e' il 70 % di StatsBomb, che e' il
miglior tetto misurabile che abbiamo.

## M5-T5 — Misurare la calibrazione nel posto sbagliato

**Il sintomo:** `test_gli_alberi_restano_calibrati` falliva con uno scarto di
**-0,056**, dieci volte la soglia. Sembrava che il gradient boosting fosse
gravemente scalibrato.

**La causa:** non era del modello. Era della divisione.

```
gol nell'addestramento  0,1998
gol nella verifica      0,2470     <- 4,7 punti di differenza

              addestramento    verifica
logistica          -0,00000     -0,0521
alberi             +0,00035     -0,0557
```

Entrambi i modelli sono calibrati **quasi esattamente** su cio' su cui hanno
imparato, e sbagliano **insieme** sulla verifica. Con quel seme la divisione
per partita ha prodotto un insieme di verifica che segna piu' dell'altro, a 3,3
deviazioni standard: raro, non impossibile, e su 40 partite del tutto normale
che capiti prima o poi.

Un modello calibrato riproduce la distribuzione **da cui ha imparato**. Se
l'insieme di verifica ne ha un'altra, lo scarto misura la differenza fra i due
insiemi, non l'onesta' del modello.

**Risolto:** due test al posto di uno. Il primo misura la calibrazione
sull'addestramento — ed e' quello che smaschera `class_weight="balanced"`, che
resta il difetto da sorvegliare. Il secondo **dimostra** che lo scarto sulla
verifica e' della divisione, verificando che i due modelli non si allontanano
mai piu' di 0,0058 l'uno dall'altro mentre lo scarto comune arriva a 0,056.

**Cosa insegna:** il test di M5-T4 si chiamava
`test_il_modello_e_calibrato_sul_suo_addestramento`, con l'insieme scritto nel
nome. Scrivendo la versione per gli alberi ho tenuto l'idea e perso il
complemento — e il nome che avevo scelto quando ci ragionavo era piu' preciso
del codice che ho scritto dopo. **Quando un nome contiene una condizione,
quella condizione e' parte dell'affermazione**: cambiarla senza cambiare il
nome e' un modo silenzioso di verificare un'altra cosa.

C'e' anche una conseguenza pratica per M5-T6: il confronto fra modello base e
modello 360 deve avvenire **sullo stesso identico insieme di verifica**, o la
differenza misurata sara' in parte quella fra due divisioni.

## M5-T5 — La previsione registrata era giusta, ma per difetto

**Non e' un problema: e' il risultato del task**, e vale la pena scriverlo
perche' e' negativo.

In `NOTES.md`, prima di misurare, avevo scritto che il gradient boosting
avrebbe vinto **grazie alla variabile del portiere**, dove la relazione ha una
U che una regressione logistica non puo' rappresentare. Quella variabile e'
spaziale e a M5-T5 non c'era. Previsione implicita: sulle sole variabili base
il guadagno sarebbe stato piccolo.

Misurato:

```
                Brier    guadagno     AUC
logistica     0.07387      14.2 %   0.7893
alberi        0.07456      13.4 %   0.7845
```

**Non piccolo: negativo.** Gli alberi perdono su tutte e tre le metriche.

**Perche':** l'`angolo` e' gia' una trasformazione non lineare delle
coordinate, calcolata con il teorema del coseno. La non linearita' l'ha messa
la costruzione delle variabili, non serve che la ritrovi il modello. Agli
alberi resta la varianza da pagare senza distorsione da correggere.

La validazione incrociata lo diceva gia' da sola, e me ne sono accorto solo
dopo: fra le tre configurazioni ha vinto **la piu' piccola** (200 iterazioni,
15 foglie) e ha perso quella da 600 iterazioni. **Un modello che migliora
rimpicciolendosi sta dicendo che non c'e' struttura da trovare.** Quel segnale
era leggibile prima di guardare il test, e vale la pena imparare a leggerlo:
l'andamento del punteggio al variare della capacita' e' un'informazione, non
solo un mezzo per scegliere un numero.

**Cosa insegna:** un risultato negativo con una causa chiara vale piu' di un
guadagno marginale raccontato bene. E soprattutto **rende leggibile il task
successivo**: adesso sappiamo che su queste variabili la classe di modello vale
meno di zero, quindi se M5-T6 mostra un salto, il salto e' dell'informazione.
Se avessi trovato un guadagno del 2 % qui, a M5-T6 non avrei saputo dire quale
parte venisse dagli alberi e quale dai difensori.

**Debito aperto, dichiarato:** il confronto fra le due classi l'ho fatto sul
test, che e' il secondo sguardo dopo M5-T4. Gli iperparametri li ho scelti
correttamente in validazione incrociata, ma il punteggio in CV della logistica
non l'ho registrato — quindi la conclusione e' giusta ma dimostrata nel posto
sbagliato. Va colmato prima della relazione finale di M5.

## M5-T6 — La previsione registrata era sbagliata, e l'ho scoperto perche' era scritta

**Scritto prima di addestrare qualunque modello spaziale.**

In `NOTES.md`, a M5-T5, avevo registrato che la distanza del portiere ha una
**U**: si segna di piu' quando il portiere e' addosso — perche' vuol dire che si
tira da vicino — e quando e' molto avanzato, perche' la porta e' sguarnita.

Ho controllato la forma **sulle sole partite di addestramento**, tenendo la
distanza di tiro quasi costante per non misurare un'altra cosa:

```
distanza di tiro 12-18        conv     scarto dal precedente
  portiere  0-4   n= 247    19,4 %
  portiere  4-6   n= 319    27,3 %     +7,8 pt = 2,2 SE
  portiere  6-8   n= 467    28,1 %     +0,8 pt = 0,2 SE
  portiere  8-10  n=1239    15,1 %    -13,0 pt = 5,6 SE
  portiere 10-14  n=4551     8,6 %     -6,5 pt = 5,9 SE
```

**E' una ∩, non una U.** Si segna di piu' nel mezzo, con il portiere uscito dai
pali ma non ancora addosso. Avevo previsto il contrario.

E la parte non monotona e' **debole**: la salita iniziale vale 2,2 deviazioni
standard nella banda 12-18, ma **1,0** nella banda 13-16 e **0,8** nella banda
18-24. Su tre finestre indipendenti non regge. La discesa dopo il picco invece
e' schiacciante ovunque, da 4 a 6 SE.

C'e' anche un confondimento da dichiarare: la distanza tiratore-portiere
**ricodifica in parte la distanza dalla porta**, perche' quando il portiere e'
sulla linea le due quasi coincidono. Senza condizionare sulla distanza di tiro
la relazione sembra monotona, ed e' un artefatto.

**Conseguenza:** il meccanismo che avevo pre-registrato — «una logistica non
puo' rappresentare una U, un albero si'» — **non e' supportato**. Quello che i
dati mostrano con certezza e' una relazione in gran parte decrescente, che una
regressione logistica rappresenta benissimo.

**Previsione corretta, registrata ora, prima di misurare:**

> Il guadagno delle variabili spaziali arrivera' soprattutto dai **difensori
> nel cono di tiro**, non dal portiere, e sara' catturabile anche da una
> regressione logistica. Il gradient boosting non dovrebbe recuperare il
> divario che ha perso a M5-T5.

**Cosa insegna:** la pre-registrazione ha fatto esattamente il lavoro per cui
serve. Se avessi guardato i dati a M5-T6 senza aver scritto niente prima, avrei
visto una relazione non monotona, avrei detto «come previsto», e non mi sarei
accorto di aver sbagliato **il verso**. Una previsione vaga si conferma sempre;
una precisa si puo' rompere, e questa si e' rotta su un dettaglio che cambia la
spiegazione.

## M5-T6 — Ho scambiato «non serve un albero» per «non serve»

**Il sintomo:** la previsione registrata poche ore prima diceva che il guadagno
delle variabili spaziali sarebbe venuto **dai difensori nel cono, non dal
portiere**. Misurato:

```
base                14.2 %
+ solo portiere     16.5 %    +2,3 punti, con 2 variabili
+ solo difensori    16.3 %    +2,1 punti, con 3 variabili
+ tutto             18.1 %    +3,9 punti
```

Il portiere vale **di piu'**, con una variabile in meno.

**La causa dell'errore, che e' la parte interessante.** A M5-T5 avevo previsto
che il gradient boosting avrebbe vinto **grazie** alla U nella distanza del
portiere. Ho controllato la forma sui dati di addestramento, la U non c'era — e
da li' ho concluso che allora il portiere contasse poco.

Non segue. **L'assenza di non linearita' non e' assenza di segnale.** La
distanza del portiere e' la variabile spaziale piu' informativa del gruppo;
semplicemente lo e' in modo che una retta rappresenta benissimo. Avevo confuso
«non serve un albero per usarla» con «non serve».

E' anche il motivo per cui la previsione a M5-T5 era sbagliata due volte nello
stesso punto: prima ho attribuito al portiere una forma che non ha, poi gli ho
tolto un'importanza che ha.

**Cosa insegna:** quando si cerca la giustificazione per un modello piu'
complesso si finisce per misurare **la forma** di una relazione invece della
**forza**. Sono due domande diverse e la seconda viene prima: quanto informa, e
solo dopo, in che forma. Avevo invertito l'ordine perche' stavo cercando un
argomento per il gradient boosting, non una descrizione dei dati.

## M5-T6 — La logistica e' identica fra le versioni, gli alberi no

**Non e' un problema, e' un'osservazione** emersa confrontando la mia
esecuzione di prova con quella nell'ambiente coi pin del progetto.

```
                      scikit-learn 1.9.0   scikit-learn 1.7.2
logistica base                   0,07371              0,07371
logistica spaziale               0,07037              0,07037
alberi base                      0,07436              0,07434
alberi spaziale                  0,07069              0,07047
```

Le due regressioni logistiche coincidono a **cinque decimali**. I due modelli
ad alberi no, e con la versione piu' recente l'AUC del modello spaziale scende
di 0,003 — abbastanza da farlo passare da «pareggia con la logistica» a «perde
anche sulle variabili spaziali».

**Perche':** una regressione logistica converge a un ottimo unico, definito dal
problema e non dall'implementazione. Un gradient boosting a istogrammi dipende
da come vengono scelti i confini dei bin, da come si gestiscono i pareggi nei
tagli e da altri dettagli che cambiano legittimamente fra release.

**Cosa insegna:** e' un argomento in piu' per mettere la logistica in
produzione, e non era nella lista quando ho scritto il confronto. Un modello i
cui numeri cambiano quando si aggiorna una libreria costringe a rieseguire e
riscrivere la relazione a ogni `uv lock`. E' il motivo per cui questo file di
risultati **registra le versioni** con cui e' stato prodotto: senza, una
differenza fra due esecuzioni sarebbe un mistero invece di un'informazione.

## M5-T7 — La curva di calibrazione si rompeva sul modello di riferimento

**Il sintomo:** quattro test gia' esistenti passati da giorni hanno iniziato a
fallire tutti insieme con `ZeroDivisionError: Weights sum to zero`. Nessuno dei
quattro riguardava la calibrazione.

**La causa:** avevo aggiunto `errore_calibrazione` fra i valori restituiti da
`metriche()`, quindi la nuova funzione veniva chiamata **su ogni modello
valutato** — compreso quello che risponde sempre la frequenza media. Con
previsioni tutte identiche non esistono quantili da tagliare: `pd.qcut`
restituisce solo NaN, il raggruppamento resta vuoto, e la media pesata degli
scarti divide per zero.

**Risolto:** se le etichette sono tutte NaN, tutto finisce in un gruppo solo.
Che e' la risposta giusta e non un ripiego: con una previsione sola c'e' un
gruppo solo, e l'errore di calibrazione e' la distanza fra quel numero e la
frequenza osservata. Verificato su tre casi degeneri — costante, sempre zero,
sempre uno — che ora danno rispettivamente 0,000, 0,097 e 0,903.

**Cosa insegna:** avevo provato la funzione nuova solo su previsioni
realistiche, cioe' su una distribuzione continua. **Il caso limite non era
esotico: era il riferimento**, l'oggetto che il modulo costruisce da solo a ogni
confronto e su cui si regge tutta la scala del guadagno. Quando si aggiunge un
campo a una struttura restituita ovunque, il costo non e' scrivere la funzione:
e' che quella funzione viene chiamata su tutti gli ingressi che la struttura
gia' riceveva, compresi quelli che nessuno aveva in mente.

I quattro test che hanno segnalato il difetto non erano test della
calibrazione. Sono i test del riferimento e delle due trappole, scritti a
M5-T5 per ragioni completamente diverse. E' il motivo per cui vale la pena
scrivere test su casi banali che «ovviamente funzionano».

## M5-T8 — Un test scritto su un'intuizione che non regge

**Il sintomo:** avevo scritto `test_sommare_per_partita_riduce_il_disaccordo_
casuale`, dando per scontato che aggregando i tiri per partita la correlazione
fra due modelli salga. Misurato sui dati sintetici: **da 0,9472 a 0,9464**. Non
sale.

**La causa:** sommando `n` termini indipendenti crescono **sia** la varianza del
segnale **sia** quella del rumore, entrambe proporzionalmente a `n`. Il rapporto
fra le due resta identico, e la correlazione con lui. «Gli errori si
compensano» e' vero in valore assoluto ma non in **rapporto**, e la
correlazione guarda il rapporto.

L'aggregazione aiuta solo se esiste una componente **condivisa dentro il
gruppo**: allora la varianza dei totali cresce con `n²` mentre quella del rumore
resta lineare. Verificato: 0,9551 → 0,9916.

**Cosa dicono i dati veri:** il nostro modello e quello di StatsBomb passano da
0,9076 per tiro a 0,9529 per partita. Si comportano come il secondo caso.
Quindi **le partite differiscono sistematicamente fra loro** nel tipo di
occasioni che producono, e i due modelli concordano su quella differenza anche
dove discordano tiro per tiro. Non lo sapevo prima di misurarlo, e non l'avrei
scoperto se il test fosse passato.

**Risolto:** due test al posto di uno. Il primo verifica che l'aggregazione
**non** migliori l'accordo quando il rumore e' indipendente — cosi' nessuno
«corregge» il codice inseguendo un miglioramento che non deve esserci. Il
secondo verifica che migliori quando la componente condivisa c'e'.

**Cosa insegna:** il test era sbagliato perche' avevo scritto l'affermazione
prima di saperla dimostrare. Ma il fallimento ha prodotto **piu' informazione
del successo**: mi ha costretto a distinguere due situazioni che confondevo, e a
scoprire in quale delle due stanno i dati.

## M5-T8 — Un modello salvato e' legato alla versione che l'ha scritto

**Il sintomo:** caricando `xg_360.pkl` con scikit-learn 1.7.2, dopo che era
stato scritto con la 1.9.0:

```
AttributeError: 'LogisticRegression' object has no attribute 'multi_class'
```

**La causa:** un pickle non salva la classe, salva **lo stato di un'istanza**.
Alla rilettura scikit-learn ricostruisce l'oggetto con il codice della versione
installata, e se quel codice si aspetta attributi che la versione precedente non
scriveva, si rompe. Vale in entrambe le direzioni.

**Perche' conta oltre l'episodio:** e' un rischio diretto per M7. Se
Streamlit Cloud installasse una versione di scikit-learn diversa da quella con
cui il modello e' stato addestrato, la dashboard fallirebbe **al caricamento
del modello**, cioe' all'avvio e non durante lo sviluppo. Il progetto e' gia'
protetto — `uv.lock` blocca l'intero albero e il deploy deve usare
`uv sync --locked` — ma la protezione era nata per la riproducibilita' dei
numeri, non per questo. Adesso e' anche un requisito di funzionamento, e come
tale va scritto nella relazione di M7.

E' anche il secondo argomento, arrivato per caso, a favore della regressione
logistica in produzione: quattro chilobyte di coefficienti si potrebbero
riscrivere in un formato neutro il giorno in cui servisse. I 368 KB di alberi
del gradient boosting no.

## M5-T9 — Il progetto dichiarava una cosa e ne faceva un'altra

**Il sintomo:** il README e il docstring di `config.Gruppo` dicevano da M2 che
le finali di Champions servono come **prova fuori campione**, «dati che il
modello non ha mai visto». Contati: **437 tiri delle finali su 561 erano
nell'addestramento**.

**La causa:** `dividi_per_partita` mescola le partite a caso e non sa nulla dei
gruppi. Nessuno le aveva mai detto che quelle 18 partite dovevano restare
fuori. Non era leakage in senso stretto — nessun tiro stava da entrambe le
parti — ma la prova fuori campione non era una prova.

Nella stessa verifica e' emerso che il README diceva anche «senza freeze
frame»: falso, il **99,8 %** di quei tiri ce l'ha. Due affermazioni sbagliate
nella stessa riga, sopravvissute a tre milestone perche' nessuno le aveva mai
contate.

**Risolto:** `features.separa_applicazione` toglie il gruppo `finali` **prima**
della divisione, e quindi prima che qualunque numero venga misurato.

**Il risultato:** il modello tiene. 18,2 % di guadagno sulle finali contro
19,2 % sulla verifica, AUC 0,8174 contro 0,8186. Addestrato su calcio dal 2015
al 2024, funziona su finali che partono dal 1971.

**Cosa insegna:** una regola scritta nella documentazione non e' una regola
finche' non c'e' una funzione che la applica. Era scritta in tre punti — README,
docstring del gruppo, piano di progetto — e in nessuno di quei tre posti
qualcosa la faceva rispettare. **La documentazione descrive le intenzioni, il
codice descrive i fatti**, e quando divergono ha ragione il codice.

## M5-T9 — Una conclusione che si e' ribaltata togliendo l'1,3 % dei dati

**Il sintomo:** rigenerando i numeri senza le finali, l'ablazione di M5-T6 si
inverte.

```
                  con le finali    senza
+ solo portiere        +2,3         +1,3
+ solo difensori       +2,1         +1,9
```

A M5-T6 avevo scritto, in relazione e nel README, che **il portiere vale piu'
dei difensori**. Bastano 437 tiri su 34.000 per invertire l'ordine.

**La causa:** la differenza era 0,2 punti. Non avevo mai chiesto se 0,2 punti
fossero distinguibili dal rumore — avevo solo notato che uno dei due numeri era
piu' grande, e ci avevo costruito sopra una spiegazione con tanto di «con una
variabile in meno».

**Risolto:** la relazione adesso dice che i due gruppi contribuiscono in modo
confrontabile e che **quale pesi di piu' questi dati non lo dicono**.

**Cosa insegna:** e' lo stesso errore delle soglie scritte senza derivarle, in
un'altra forma. Li' inventavo il numero a cui confrontare; qui confrontavo due
numeri veri senza chiedermi se la loro differenza significasse qualcosa. La
domanda «e' piu' grande?» e' quasi sempre la domanda sbagliata: quella giusta e'
«e' piu' grande di quanto ci si aspetterebbe per caso?».

La cosa che mi ha salvato non e' stata la prudenza, e' stato **aver dovuto
rigenerare i numeri per un altro motivo**. Se M5-T9 non avesse toccato la
divisione, quella frase sarebbe finita nel case study.

---

<!--
Le milestone successive aggiungono qui la loro sezione.
Almeno un'annotazione per milestone: e' il criterio di M7-T6.
-->
