# M7 — Pubblicazione

> Il progetto ha un indirizzo pubblico. Chi clona il repository ottiene i dati
> insieme al codice e l'app parte senza scaricare niente; chi non vuole clonare
> apre un link e la dashboard è lì.

**Periodo:** 19 agosto 2026 · **Task:** 7 · **Pull request:** #101, #102, #103,
#104, #105, #106

**Indirizzo:** <https://football-analytics-imadelmir.streamlit.app>

---

## 1. Cosa è stato costruito

Fino a M6 il progetto era un repository che qualcuno doveva saper eseguire: uv,
il download di 6,25 GB di JSON, la costruzione del magazzino, l'addestramento.
Tre comandi e venti minuti, prima di vedere qualcosa.

M7 ha rimosso tutto questo da entrambi i lati. **I sei Parquet e i due modelli
sono in git** — 6,3 MB in tutto, contro i gigabyte da cui nascono — quindi un
clone pulito parte con `uv sync` e `streamlit run`. E **l'app è pubblicata**,
quindi nella maggior parte dei casi non serve nemmeno clonare.

La milestone ha anche corretto un difetto di M6 che nessun test copriva, e ha
prodotto quattro sorprese fra ambiente locale e Streamlit Cloud che sono, come
il backlog prevedeva, la parte più utile di questo file.

### L'ordine reale dei task

Non è quello del backlog, e vale la pena dirlo perché il grafo dei commit non
lo racconta:

| Ordine | Task | Pull request |
| --- | --- | --- |
| 1 | **T1 e T2 insieme** — magazzino in git, `requirements.txt` | #101 |
| 2 | T4 — README completo | #102 |
| 3 | T3 — deploy, in tre parti | #103, #104 |
| 4 | T5 — verifica della memoria | #105 |
| 5 | T6 — `NOTES.md` | #106 |
| 6 | T7 — questa relazione | — |

**T1 e T2 sono usciti in un commit solo, e il titolo nomina solo T1.** Nel
grafo di `main` T2 non compare: chi guarda la cronologia vede il magazzino
entrare in git e non vede `requirements.txt` nascere. È un mio errore di
confezionamento, non di contenuto — entrambi i criteri erano soddisfatti e
verificati — e sta scritto qui perché la cronologia non si riscrive: `main` è
protetto contro il force push per scelta, e cancellare l'errore costerebbe più
di quanto valga.

**T4 è stato fatto prima di T3** perché il README andava sistemato comunque, e
il difetto che conteneva — il badge della CI puntava a un repository che non è
questo — era più urgente di un deploy.

---

## 2. La procedura di deploy, passo per passo

È il criterio della task: *un'altra persona deve poter ripetere il deploy
seguendo solo questo file*. Quindi qui c'è tutto, comprese le cose che sembrano
ovvie e che non lo sono state.

### Prerequisiti

Il repository deve essere **pubblico** — il piano gratuito di Streamlit
Community Cloud non pubblica app da repository privati — e `main` deve
contenere i Parquet e i modelli. Se `data/processed/` è vuota l'app parte e
muore alla prima lettura, perché su Cloud non c'è modo di eseguire
`build_dataset.py`.

### I passi

1. Andare su <https://share.streamlit.io> ed entrare con GitHub, autorizzando
   l'accesso ai repository.
2. *Create app* → *Deploy a public app from GitHub*.
3. Compilare:

   | Campo | Valore |
   | --- | --- |
   | Repository | `imadelmir/football-analytics` |
   | Branch | `main` |
   | Main file path | `app/Panoramica.py` |
   | Python version *(in Advanced settings)* | **3.12** |

4. *Deploy*. Il primo avvio richiede circa cinque minuti: la piattaforma clona
   il repository e installa 52 pacchetti.
5. **Scegliere un sottodominio leggibile.** Dalla lista delle app, i tre
   puntini `⋮` a destra della riga → *Settings* → *General* → *App URL*.
   L'indirizzo predefinito è generato a caso —
   `football-analytics-cfdh2f8wceqyphbuosy9mv.streamlit.app` — e non è una cosa
   che si mette in un portfolio. Va fatto **prima** di scrivere il link da
   qualche parte: cambiarlo dopo lascia link morti in giro.

### La versione di Python va messa a mano

Streamlit Cloud **non legge `.python-version`**. Con la versione predefinita,
`pandas 3.0.5` e `pyarrow 24` potrebbero non avere ruote precompilate,
l'installazione proverebbe a costruirle e andrebbe in timeout. Il campo è in
*Advanced settings* al momento della creazione, ed è modificabile dopo dallo
stesso pannello delle impostazioni.

### Quale file di dipendenze viene usato

Questa è la prima sorpresa, e cambia cosa ha senso mantenere. Dai log del
primo avvio:

```
WARN: More than one requirements file detected in the repository.
Available options: uv-sync uv.lock, uv requirements.txt, poetry pyproject.toml.
Used: uv-sync with /mount/src/football-analytics/uv.lock
```

**La piattaforma trova tre file e sceglie `uv.lock`.** `requirements.txt` non
viene letto. Il progetto lo mantiene comunque, perché serve a chi installa con
`pip` senza `uv`, ma non governa il deploy — e il pacchetto stesso risulta
installato dalla riga:

```
+ football-analytics==0.1.0 (from file:///mount/src/football-analytics)
```

---

## 3. File creati e modificati

| File | Cosa |
| --- | --- |
| `.gitignore` | Tolte le esclusioni di `data/processed/` e `models/`; i commenti riscritti al passato spiegano perché entrano solo adesso |
| `requirements.txt` | Rigenerato senza `--no-emit-project`, quindi con `-e .` |
| `README.md` | Riscritto: primo schermo con la risposta misurata, le schermate, i comandi |
| `docs/windows.md` | **Nuovo.** Le 46 righe su Smart App Control, uscite dal README |
| `pyproject.toml` | URL del repository corretto; `scripts` aggiunta al percorso dei test |
| `scripts/misura_memoria.py` | **Nuovo.** Misura base, magazzino e picco senza dipendenze aggiuntive |
| `src/football_analytics/panoramica.py` | `kpi()` restituisce due totali di gol invece di uno |
| `app/Panoramica.py` | La didascalia della ciambella usa `gol_da_tiro` |
| `NOTES.md` | Cinque voci per M6, sette per M7; sedici titoli riportati al livello giusto |
| `tests/test_readme.py` | **Nuovo.** Quattordici test perché il README non menta |
| `tests/test_memoria.py` | **Nuovo.** Quattro test sul costo fisso in memoria |
| `tests/test_impalcatura.py` | Il magazzino in un clone pulito, `requirements.txt`, il diario per milestone |
| `tests/test_panoramica.py` | Tre test sui due totali di gol |

---

## 4. Decisioni tecniche

### Scelta: i Parquet entrano in git a prodotto finito, non prima

**Alternativa scartata:** versionarli da M3, quando sono nati.

**Perché:** git non sa fare diff dei binari, quindi ogni versione è una copia
intera. I Parquet si sono rigenerati **otto volte** fra M3 e M6 — all'arrivo di
`passes` e `touches`, allo scaricamento delle altre competizioni, all'aggiunta
dell'xG a M5. Versionarli da subito avrebbe lasciato decine di megabyte di
cronologia che nessuno può più togliere, perché `main` è protetto contro il
force push di proposito.

La regola per il futuro è scritta nel `.gitignore`: rigenerarli solo quando
cambia davvero qualcosa, e guardare `git show --stat` prima di committare.

### Scelta: i pickle sono in git, ma la dashboard non li carica

**Alternativa scartata:** tenerli fuori, o farli caricare alla vista Modello.

**Perché:** un `.pkl` è Python serializzato, e caricarlo **esegue codice**. In
un'app pubblica quella superficie non si apre per comodità. La vista Modello
legge due schede JSON generate insieme ai modelli; i pickle stanno nel
repository perché chi clona possa ispezionarli e riusarli, non perché servano
a far girare l'app.

### Scelta: il primo schermo del README è la risposta, non l'attribuzione

**Alternativa scartata:** lasciare l'attribuzione a StatsBomb in cima, dov'era.

**Perché:** il criterio di T4 è che chi arriva dal portfolio capisca il
progetto in trenta secondi, e trenta secondi bastano a guardare, non a leggere.
Adesso il primo schermo ha la domanda, una schermata della dashboard e quattro
numeri. L'attribuzione è scesa sotto **integra**: è una condizione di licenza,
e un test lo verifica.

### Scelta: `kpi()` restituisce due totali di gol

**Alternativa scartata:** sceglierne uno, come faceva prima.

**Perché:** i gol dai tabellini comprendono i 156 autogol e rispondono a
«quanti gol si sono visti». I gol dai tiri sono gli unici che si possono
mettere sopra un denominatore ricavato dai tiri. Una sola definizione costringe
a sbagliare una delle due domande. Il dettaglio è nella sezione 6.

### Scelta: la memoria si misura senza `psutil`

**Alternativa scartata:** aggiungere `psutil` alle dipendenze.

**Perché:** sarebbe un pacchetto in più nell'ambiente di produzione per uno
script che gira tre volte l'anno. La memoria residente si legge da
`/proc/self/status` su Linux — che è il sistema di Streamlit Cloud — e dalle
API di sistema via `ctypes` su Windows, dove il progetto viene sviluppato.

---

## 5. Numeri misurati

| Cosa | Valore | Come è stato ottenuto |
| --- | --- | --- |
| Peso del magazzino su disco | 6,3 MB su sei file | `scripts/misura_memoria.py` |
| Peso del magazzino in memoria | **49,6 MB** | idem, `memory_usage(deep=True)` |
| Fattore di espansione | **7,9×** | idem |
| La tabella più grande in memoria | `freeze_frames`, 33,8 MB — il 68 % | idem |
| Il rapporto peggiore | `touches`, 12,6× | idem |
| Processo con le sole librerie | 80 MB | idem, memoria residente |
| Processo con il magazzino letto | **231 MB** | idem |
| Processo durante le aggregazioni | **233 MB** | idem |
| Tetto di Streamlit Community Cloud | 1.024 MB | dichiarato dalla piattaforma |
| **Margine** | **791 MB** | 1.024 − 233 |
| Pacchetti installati al deploy | 52 | log del primo avvio |
| Durata del primo avvio | circa 5 minuti | log, dalle 10:33:15 alle 10:33:24 più la clonazione |
| Test automatici | **703**, copertura 94 % | `uv run python -m pytest -m "not rete" -q` |
| Annotazioni in `NOTES.md` | 50 su sette milestone | `tests/test_impalcatura.py` |
| Rigori delle serie finali | 190 | query sul magazzino |
| Autogol | 156 | 4.601 − 4.445 |

**I 231 MB del processo contro i 49,6 MB delle tabelle non sono un errore.** La
differenza sono i buffer di lettura di pyarrow e le allocazioni intermedie che
il sistema non restituisce subito. E questo script non importa Streamlit,
Plotly e scikit-learn, che nell'app ci sono: il valore reale su Cloud è più
alto. Resta comunque una frazione del tetto, ma **è una stima, non una misura**,
ed è per questo che il criterio di T5 chiede anche la prova empirica.

---

## 6. Problemi incontrati

Il backlog dava per certa almeno una sorpresa fra locale e Cloud. Ne sono
uscite quattro, più un difetto di M6 e due errori di procedura. Le annotazioni
complete sono in [`NOTES.md`](../../NOTES.md); qui le conseguenze operative.

### Un `git push` fa *rerun*, non *restart* — ed è la cosa più utile del file

Dopo aver corretto `panoramica.kpi()`, l'app pubblica mostrava
`KeyError: 'gol_da_tiro'` proprio alla riga che quella chiave la chiedeva.

Dai log: alle 10:33 installazione completa, alle 10:43
`Pulling code changes` → `Processing dependencies` → `Processed dependencies!`
**nello stesso secondo**, poi `Updated app!`. Streamlit aveva rieseguito lo
script — `Panoramica.py`, versione nuova — ma `football_analytics.panoramica`
era già in `sys.modules` dal primo avvio, e Python non reimporta un modulo già
importato.

> **Regola: ogni modifica dentro `src/` richiede un Reboot dell'app su Cloud.
> Il push da solo non basta.** *Manage app* → `⋮` → *Reboot app*.

Senza saperlo si conclude che la correzione non abbia funzionato e si va a
cercare un difetto che non esiste.

### Due definizioni di «gol» nello stesso riquadro

Il difetto di M6, trovato confrontando i numeri della dashboard con quelli del
README. La ciambella «xG realizzato» mostrava **102,7 %** con la didascalia
«4.601 gol / 4.328 xG» — che fa 106,3 %.

`kpi()` prendeva i gol dai tabellini, autogol compresi, e tiri e xG dalla
tabella dei tiri; la percentuale veniva da `realizzazione()`, che i gol li
prende dai tiri. Lo stesso difetto colpiva la conversione: 10,5 % invece di
10,2 %, sotto l'etichetta «dei tiri finisce in gol».

La scelta di contare i gol dai tabellini era **giusta e documentata da M6**.
Il difetto è nato dall'applicarla anche dove il denominatore veniva da
un'altra fonte: una regola corretta smette di esserlo quando esce dal suo
dominio, e la sua stessa documentazione la fa sembrare deliberata ovunque
compaia.

### Una diagnosi giusta su una premessa mai verificata

`requirements.txt` davvero non installava il pacchetto, e su una piattaforma
che lo leggesse l'app sarebbe morta all'avvio. Ho corretto, aperto una PR e
fuso — e solo dopo, leggendo i log, ho scoperto che quel file **non viene mai
letto**. Il ragionamento era corretto e la premessa sbagliata.

### «La piattaforma non lo permette» era un mio errore di due righe

`scripts/misura_memoria.py` dichiarava la memoria residente non leggibile su
Windows. La causa: `GetCurrentProcess` restituisce un `HANDLE` a 64 bit e senza
`restype` dichiarato ctypes lo tratta come intero a 32 bit, quindi l'API riceve
un handle troncato e risponde zero. Sarebbe finito in questa relazione come un
limite della piattaforma.

### pandas 3 ha cambiato il peso delle stringhe

Un test pretendeva che `memory_usage(deep=True)` desse molto più di
`deep=False` su una colonna di testo: ha fallito con i due numeri **identici**.
Da pandas 3.0 le stringhe non sono più `object` con puntatori sparsi ma una
colonna nativa contigua. E passare `dtype=object` al costruttore non basta:
con dentro delle stringhe, pandas riconverte comunque.

La conseguenza che conta: l'espansione 7,9× dal Parquet alla memoria **non**
viene dalle colonne di testo, come avevo scritto in un commento, ma dalla
codifica a dizionario di Parquet sulle colonne numeriche. Il consiglio che ne
avevo tratto — convertire il testo in `category` — non avrebbe recuperato
quasi nulla.

### Due modi di rompersi con `gh`

`gh pr merge --auto` seguito subito da `git pull` fa credere di aver perso il
lavoro: `main` risulta aggiornato e `git branch -d` avvisa che il ramo non è
fuso. Il merge stava solo aspettando la CI. **Controllare
`gh pr list --state open` prima di ogni `git pull`.**

`gh pr create --fill` prende il **nome del ramo** come titolo quando i commit
sono più d'uno, e con lo squash quel titolo diventa il messaggio su `main`:
sarebbe finito `m7 t3 gol da tiro (#104)` in mezzo a tutti gli altri
`M7 - Tx : ...`. **Passare sempre `--title` esplicito.**

### Una pull request fantasma con l'auto-merge armato

La #85, di M5-T9, aperta da sei giorni con il contenuto già su `main`. Non era
un residuo: aveva `Auto-merge: enabled` e nessun controllo obbligatorio, quindi
aspettava un'approvazione che non sarebbe mai arrivata — ma il giorno in cui
qualcuno l'avesse data, GitHub avrebbe fuso un ramo vecchio **riportando
indietro tredici file**. Chiusa con la motivazione scritta nel commento.

---

## 7. Cosa resta aperto

**Il tempo di risveglio non è stato misurato.** Il backlog lo chiede, e non
compare fra i numeri della sezione 5 perché in questo repository non si
scrivono valori non misurati. Streamlit Community Cloud sospende un'app dopo
circa dodici ore senza visite, e l'app è stata pubblicata oggi. Si misura così,
dopo almeno un giorno di inattività:

```bash
# Da un dispositivo che non ha mai aperto l'app, per evitare la cache
curl -o /dev/null -s -w "%{time_total}\n" https://football-analytics-imadelmir.streamlit.app
```

Il numero atteso è nell'ordine delle decine di secondi, perché il risveglio
comporta la ricostruzione dell'ambiente. Chi legge questa relazione e trova
ancora questa riga sa che il dato manca.

**`requirements.txt` è mantenuto ma non usato dal deploy.** Serve a chi
installa con `pip`, e un test lo tiene allineato a `pyproject.toml`. Non è
debito: è un file con un pubblico diverso da quello che credevo avesse.

**`touches` espande 12,6 volte.** Con 791 MB di margine non c'è ragione di
intervenire, e ottimizzare senza un problema misurato è ciò che questo progetto
evita. Se un giorno il margine si stringesse, si comincia da `freeze_frames`,
che da solo vale il 68 % del magazzino in memoria.

**T2 non compare nel grafo di `main`.** Registrato nella sezione 1; non si
corregge riscrivendo la cronologia.

---

## 8. Come verificarlo

I quattro controlli, dal repository:

```bash
uv run ruff format .
uv run ruff check .
uv run python -m mypy
uv run python -m pytest -m "not rete"
```

Il criterio di T1, su un clone davvero pulito:

```bash
git clone https://github.com/imadelmir/football-analytics.git /tmp/prova
cd /tmp/prova
uv sync --all-extras
uv run streamlit run app/Panoramica.py    # senza scaricare niente
```

Il criterio di T5:

```bash
uv run python scripts/misura_memoria.py
```

Il criterio di T3 e la metà empirica di T5 si verificano **sull'indirizzo
pubblico**, non in locale: aprire
<https://football-analytics-imadelmir.streamlit.app> da un telefono, passare
per tutte e sette le viste nella stessa sessione senza ricaricare la pagina, e
cambiare competizione due o tre volte. Se il gigabyte si superasse, l'app si
disconnetterebbe e nei log comparirebbe la morte del processo.
