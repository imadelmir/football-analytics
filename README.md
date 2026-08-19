# Football Analytics

[![CI](https://github.com/imadelmir/football-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/imadelmir/football-analytics/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Licenza MIT](https://img.shields.io/badge/licenza-MIT-green.svg)](LICENSE)
[![Dashboard online](https://img.shields.io/badge/dashboard-online-15803d.svg)](https://football-analytics-imadelmir.streamlit.app)

### → **[Apri la dashboard](https://football-analytics-imadelmir.streamlit.app)**

**Quanto vale, davvero, sapere dove sono i difensori quando parte un tiro?**
Questo progetto risponde misurando: 43.849 tiri di StatsBomb, due modelli di
expected goals addestrati sulle stesse identiche partite — uno che vede il
fotogramma del tiro e uno no — e una dashboard per guardarci dentro.

> **In English.** An end-to-end football analytics project built on StatsBomb
> Open Data: ingestion of 1,753 matches, reduction to six compact Parquet
> tables, two expected-goals models, and a seven-view Streamlit dashboard. The
> question it answers, measured: how much is it worth to know where the
> defenders are? **+2.9 Brier points, +18 % relative — 62 % of the gap to
> StatsBomb's own xG model.** Everything below is in Italian.

![La Home della dashboard](docs/immagini/m6/home.png)

| | |
| --- | --- |
| **La risposta** | Vedere difensori e portiere vale **+2,9 punti di Brier score** (16,3 % → 19,2 % di guadagno sul riferimento), e colma il **62 %** del divario dall'xG ufficiale di StatsBomb |
| **I dati** | 9 competizioni, 1.753 partite, **43.849 tiri**, 4.578 gol — 6,25 GB di JSON ridotti a **6,3 MB** di Parquet |
| **La dashboard** | 7 viste Streamlit, tema che cambia con la competizione, nessuna lettura dei dati grezzi |
| **Il codice** | Tipizzato in `mypy --strict`, lint `ruff`, **oltre 700 test** con copertura del 94 %, CI su ogni push |

## Provalo

Serve **Python 3.12** e **[uv](https://docs.astral.sh/uv/)**.

```bash
git clone https://github.com/imadelmir/football-analytics.git
cd football-analytics

uv sync --all-extras
uv run streamlit run app/Panoramica.py
```

**Non serve scaricare niente.** Le sei tabelle Parquet che la dashboard legge
sono nel repository: pesano 6,3 MB in tutto e l'app parte da un clone pulito.
I 6,25 GB di JSON grezzi servono solo a rigenerarle.

---

## Le tre domande, e le risposte

Scelte dopo aver guardato i dati, non prima. Il ragionamento è nel
[notebook di esplorazione](notebooks/esplorazione.ipynb) e in
[`docs/milestones/M4-esplorazione.md`](docs/milestones/M4-esplorazione.md).

### 1. Quanto vale sapere dove sono i difensori?

Sui 41.179 tiri su azione, la conversione passa dal **38,9 %** con due
avversari inquadrati al **7,2 %** con otto o più — un fattore cinque **a
distanza di tiro quasi costante**, fra i 16 e i 18 metri. Non è che con pochi
difensori si tira da più vicino: si tira da lontano uguale e si segna molto
di più.

Quello è il segnale nei dati. La domanda vera è quanto un modello riesca a
catturarne, e per rispondere se ne addestrano **due sulle stesse partite**:
uno con le variabili ricavate dal fotogramma del tiro — difensori nel cono,
distanza del portiere — e uno senza.

| Modello | Brier | AUC | Guadagno sul riferimento |
| --- | ---: | ---: | ---: |
| Riferimento (risponde sempre la media) | 0,08728 | 0,500 | 0,0 % |
| Base — posizione, angolo, parte del corpo | 0,07305 | 0,799 | 16,3 % |
| **Spaziale — in più il fotogramma del tiro** | **0,07050** | **0,819** | **19,2 %** |
| xG ufficiale di StatsBomb | 0,06894 | 0,823 | 21,0 % |

**+2,9 punti**, cioè **+18 % di capacità esplicativa** — e il **62 %** della
distanza che separava il modello base dall'xG di StatsBomb.

**Regge fuori dal campione.** Applicato alle 18 partite delle finali di
Champions, escluse dall'addestramento *e* dalla verifica, il modello spaziale
tiene il **18,2 %** contro il 19,2 % della verifica, mentre il base scende dal
16,3 % al 13,0 %: fuori campione il fotogramma conta di più, non di meno.

I numeri escono da `scripts/train_model.py` e stanno in
[`docs/milestones/M5-risultati.md`](docs/milestones/M5-risultati.md), che il
comando riscrive. **Non sono ricopiati a mano da nessuna parte.**

### 2. Chi segna più di quanto dovrebbe, e per quanto tempo?

La differenza fra gol e xG è la misura più fraintesa del calcio analitico: su
un giocatore e mezza stagione è quasi solo rumore. Su 43.849 tiri si può
guardare quanto quello scarto persista davvero — e la dashboard lo mostra
senza chiamarlo mai né bravura né fortuna.

La soglia dei 500 minuti non è cosmetica: senza, il miglior marcatore per
novanta minuti è sempre uno entrato al 90°.

### 3. Le leghe giocano davvero in modo diverso?

Si somigliano nei gol — da 2,52 a 2,74 per partita — ma non nel modo di
arrivarci: **Serie A e Premier tirano di più della Liga e producono meno xG.**
Si tira di più da posizioni peggiori.

Quattro campionati della **stessa stagione** permettono di dirlo senza che
l'epoca faccia da variabile nascosta.

---

## Com'è fatto

Quattro strati, e una regola che li tiene separati.

| Strato | Dove | Cosa fa |
| --- | --- | --- |
| 1. Ingestione | `src/football_analytics/ingest.py` | Scarica i JSON in `data/raw/`, in modo incrementale e ripartibile |
| 2. Trasformazione | `src/football_analytics/transform.py` | Riduce gli eventi a sei Parquet compatti in `data/processed/` |
| 3. Modello | `src/football_analytics/model.py` | I due modelli xG, base e spaziale, con divisione per partita |
| 4. Dashboard | `app/` | Sette viste Streamlit, tema che cambia con la competizione |

**La regola: l'app non legge mai i dati grezzi.** Streamlit Community Cloud dà
1 GB di RAM, e caricare i JSON a ogni visita significherebbe un'app che muore
al primo utente. La lettura dal disco avviene in un solo file (`app/dati.py`),
è in cache, e un test conta le letture per dimostrarlo invece di dedurlo.

```
football-analytics/
├── src/football_analytics/   config, ingest, transform, features, model, metriche, viz…
├── scripts/                  scarica_dati.py, build_dataset.py, train_model.py
├── app/                      la dashboard: Panoramica.py + pages/
├── tests/                    oltre 700 test, senza rete
├── notebooks/                esplorazione (M4), fuori dal pacchetto
├── data/raw/                 JSON scaricati — fuori da git, 6,25 GB
├── data/processed/           sei Parquet, 6,3 MB — versionati, sono ciò che l'app legge
├── models/                   xg_base e xg_360, .pkl e scheda .json
└── docs/milestones/          una relazione per ogni milestone conclusa
```

### La divisione dei dati

Train e test sono separati **per partita**, mai per tiro: due tiri della stessa
partita condividono avversario, campo e arbitro, e finire uno di qua e uno di
là gonfierebbe il punteggio senza che nessuna metrica se ne accorga.

- **Addestramento:** 34.160 tiri su 1.388 partite
- **Verifica:** 8.425 tiri su 347 partite, mai viste
- **Applicazione:** 560 tiri su 18 partite di Champions, fuori da entrambi

La scelta fra classi di modello si fa in validazione incrociata raggruppata,
dove l'insieme di verifica non entra. Il test si guarda **una volta sola**,
alla fine. E l'accuratezza non compare mai: su un evento che accade nel 9,7 %
dei casi, rispondere sempre «no gol» dà il 90 % di accuratezza e zero
informazione.

---

## Le competizioni

Nove competizioni, 1.753 partite. I conteggi sono **misurati** con
`scripts/esplora_open_data.py`, non stimati: il piano iniziale ne assumeva
altri e si è rivelato sbagliato su metà delle fonti — il racconto è in
[`docs/milestones/M2-ingestione.md`](docs/milestones/M2-ingestione.md).

**Quattro campionati, stagione 2015/16** — la stessa stagione per tutti, così
il confronto fra leghe non scambia la differenza fra i campionati con quella
fra le epoche.

| Competizione | Partite | File 360 |
| --- | ---: | ---: |
| La Liga 2015/16 | 380 | 0 |
| Premier League 2015/16 | 380 | 0 |
| Serie A 2015/16 | 380 | 0 |
| Ligue 1 2015/16 | 377 | 0 |

**Tornei per nazionali** — competizioni complete, con in più i file 360 di
contesto su quasi tutte le partite.

| Competizione | Partite | File 360 |
| --- | ---: | ---: |
| Coppa del Mondo 2022 | 64 | 64 |
| Campionato Europeo 2024 | 51 | 51 |
| Campionato Europeo 2020 | 51 | 51 |
| Coppa d'Africa 2023 | 52 | 1 |

**Finali di Champions League** — 18 partite dal 1971 al 2019, di cui **17
finali vere**: la diciottesima è Fiorentina–Manchester United del 1999, una
partita di girone che l'Open Data tiene nella stessa competizione ed è filtrata
per fase in tutte le viste.

### 360 e fotogramma del tiro sono due cose diverse

Vale la pena dirlo, perché è la distinzione su cui questo progetto ha sbagliato
una volta e l'errore è arrivato fino a `main`.

I file `three-sixty/` coprono **tutti gli eventi** della partita e nei
campionati non ci sono. Il `shot.freeze_frame` è **dentro l'evento del tiro**,
dà la posizione di ogni giocatore in quell'istante, e c'è sul **99 %** dei
tiri di tutte le competizioni, campionati del 2015/16 compresi.

Il modello spaziale legge il **secondo**, non il primo. È per questo che il
confronto gira su circa 44.000 tiri invece che su 5.500. Il dettaglio è in
[`docs/milestones/M3-trasformazione.md`](docs/milestones/M3-trasformazione.md).

---

## Le schermate

Sette viste, tutte raggiungibili dal menu. Le immagini a piena risoluzione sono
in [`docs/immagini/m6/`](docs/immagini/m6/).

| | |
| --- | --- |
| **Squadre** — classifica, xG, scarto | **Giocatori** — radar per reparto |
| ![Squadre](docs/immagini/m6/squadre.png) | ![Giocatori](docs/immagini/m6/giocatori.png) |
| **Modello xG** — calibrazione e pesi | **Metodologia** — la catena del dato |
| ![Modello](docs/immagini/m6/modello.png) | ![Metodologia](docs/immagini/m6/metodologia.png) |

Il tema cambia con la competizione: verde per i campionati, blu per le finali
di Champions. Non è decorazione — è il segnale che i dati sotto sono cambiati.

| Serie A | Finali di Champions |
| --- | --- |
| ![Tema campionato](docs/immagini/m6/tema-serie-a.png) | ![Tema Champions](docs/immagini/m6/tema-champions.png) |

---

## I limiti

La dashboard ne dichiara **undici** nella pagina Metodologia, scritti in
`src/football_analytics/metodo.py`. I quattro che cambiano come si leggono i
numeri:

- **L'xG mostrato nelle viste è quello di StatsBomb, non il nostro.** I due
  modelli servono a capire come si costruisce un xG e quanto vale il
  fotogramma, non a sostituire quello ufficiale, addestrato su molti più dati.
  Solo la vista «Modello xG» mostra i nostri.
- **L'albo d'oro non è quello della Champions League.** Diciassette finali su
  oltre settanta edizioni: qui il Liverpool risulta con due coppe invece di
  sei.
- **Le finali non sono una serie storica.** Tre sono del 1971-73 e quattordici
  del 2004-2019; fra il 1974 e il 2003 non c'è niente. Nessun confronto fra
  epoche, in nessuna vista.
- **Un xG non prevede una partita.** Dice quanto valevano le occasioni create,
  a cose fatte. Una squadra con più xG non era destinata a vincere: aveva
  tirato da posizioni migliori.

---

## Attribuzione dei dati

Questo progetto usa **[StatsBomb Open Data](https://github.com/statsbomb/open-data)**,
resi disponibili gratuitamente da StatsBomb. La citazione della fonte è una
**condizione d'uso**, non una cortesia: compare qui, nel piede di ogni pagina
della dashboard e nella pagina Metodologia.

I dati sono soggetti alla licenza pubblicata nel repository di StatsBomb.

**Nessuno stemma di club e nessuna fotografia di agenzia è usato in questo
progetto:** al posto degli stemmi c'è la sigla della squadra in un cerchio,
generata dal nome.

I **loghi delle competizioni** in `app/assets/loghi/` sono invece presenti, e
sono marchi registrati dei rispettivi titolari — UEFA, FIFA, CAF, LaLiga, Lega
Serie A, Premier League, LFP. Compaiono a titolo puramente descrittivo, per
identificare la competizione di cui si stanno mostrando i dati; questo progetto
non è affiliato né sponsorizzato da nessuno di loro, e i marchi restano dei
rispettivi proprietari.

---

## Sviluppo

```bash
uv run ruff format .        # formatta
uv run ruff check --fix .   # lint, con le correzioni automatiche
uv run mypy                 # tipi, in modalità strict
uv run pytest               # test, con misura della copertura
```

Gli stessi comandi girano in CI a ogni push e a ogni pull request, in due job
separati: **Lint e tipi** e **Test**. Il file `uv.lock` blocca l'intero albero
delle dipendenze, non solo quelle dirette: è ciò che rende l'installazione
identica su una macchina diversa.

Per rigenerare i dati da zero — dieci minuti e 6,25 GB di spazio libero:

```bash
uv run python scripts/scarica_dati.py --tutte   # i JSON in data/raw/
uv run python scripts/build_dataset.py          # i sei Parquet
uv run python scripts/train_model.py            # i modelli e M5-risultati.md
```

Su Windows con Smart App Control attivo alcuni comandi vengono bloccati:
la spiegazione e la soluzione sono in [`docs/windows.md`](docs/windows.md).

## Come è stato costruito

Otto milestone, ognuna chiusa con la sua relazione — quanto è stato misurato,
cosa si è rotto e perché, cosa è stato deciso di non fare. L'indice con tutti i
numeri chiave è in
[`docs/milestones/README.md`](docs/milestones/README.md).

| | | |
| --- | --- | --- |
| [M1 — Fondamenta](docs/milestones/M1-fondamenta.md) | [M2 — Ingestione](docs/milestones/M2-ingestione.md) | [M3 — Trasformazione](docs/milestones/M3-trasformazione.md) |
| [M4 — Esplorazione](docs/milestones/M4-esplorazione.md) | [M5 — Modello xG](docs/milestones/M5-modello-xg.md) | [M6 — Dashboard](docs/milestones/M6-dashboard.md) |
| [M7 — Pubblicazione](docs/milestones/M7-pubblicazione.md) | [M8 — Portfolio](docs/milestones/M8-portfolio.md) | |

Il diario degli inciampi è in [`NOTES.md`](NOTES.md): cinquantatré annotazioni
su cosa si è rotto, come si è capito e cosa ha insegnato. È la parte che un
lettore tecnico guarda per capire come si è lavorato, non solo cosa è uscito.

> **Stato:** M8 conclusa. Tutte e otto le milestone sono chiuse.

## Licenza

Codice sotto licenza MIT. I dati appartengono a StatsBomb e sono soggetti alle
loro condizioni d'uso.
