# M5 — Il modello xG

> Due modelli addestrati sulle stesse partite, valutati sullo stesso insieme di
> verifica, con la differenza dichiarata.

**Periodo:** dal 2026-08-07 · **Issue chiuse:** \_\_ / 12 · **Commit:** \_\_

> Questo file viene compilato **mentre** la milestone procede. Le sezioni con
> `__` sono ancora aperte.

---

## 1. Cosa è stato costruito

<!-- Da completare a fine milestone. -->

Finora: le variabili base e spaziali, la divisione train/test per partita, e il
primo modello — una regressione logistica addestrata su 34.582 tiri.

## 2. File creati e modificati

| File | Cosa fa |
| --- | --- |
| `src/football_analytics/features.py` | Distanza, angolo, cono di tiro, posizione del portiere |
| `src/football_analytics/model.py` | Divisione per partita, pipeline, addestramento, salvataggio |
| `tests/test_features.py` | 42 test, molti su casi geometrici calcolabili a mano |
| `tests/test_divisione.py` | 19 test, compreso uno che dimostra il difetto evitato |
| `tests/test_modello.py` | 8 test sulle proprietà che nessun errore segnalerebbe |

## 3. Decisioni tecniche

### Scelta: l'angolo di tiro è quello sotto cui si vede la porta

**Alternativa scartata:** l'angolo fra la direzione del tiro e l'asse della porta, che è la definizione più immediata.

**Perché:** quella scelta rende i casi noti **verificabili a mente**, quindi i test diventano argomenti invece che numeri copiati da un'esecuzione. Dalla bandierina del corner l'angolo vale zero perché i due pali sono allineati con chi tira; da un punto sulla linea fra i pali vale 180 gradi perché la porta occupa tutto il campo visivo. Qualunque errore di segno, di unità o di scambio fra i pali rompe almeno uno dei due test.

### Scelta: i rigori restano fuori dal modello

**Alternativa scartata:** includerli, sono tiri come gli altri.

**Perché:** due ragioni, e la seconda l'ha trovata M4. La prima è nota: un rigore ha xG praticamente fisso, 0,78, e non dipende da dove sono i difensori. La seconda è più insidiosa: su 480 rigori solo 54 hanno il fotogramma, e quei 54 convertono all'11 % contro l'82 % degli altri, perché StatsBomb lo allega quasi solo quando il rigore sbaglia. **La presenza del dato dipende dall'esito.**

### Scelta: la divisione train/test è per partita

**Alternativa scartata:** una divisione casuale a livello di tiro.

**Perché:** i tiri della stessa partita si somigliano — stesso campo, stesse squadre, stessa serata — e dividerli a caso fa valutare il modello su partite di cui ha già visto una parte. Il punteggio risulta migliore di quello vero, e **il difetto è invisibile**: nessun errore, nessun avviso, solo metriche lusinghiere.

C'è un test che lo dimostra: divide gli stessi dati per tiro e verifica che **tutte** le partite finiscano da entrambe le parti.

### Scelta: nessun `class_weight="balanced"`

**Alternativa scartata:** bilanciare le classi, che con un gol ogni dieci tiri è la prima cosa che viene in mente.

**Perché:** bilanciare i pesi migliora l'ordinamento ma spinge le probabilità previste verso il 50 %, e **distrugge la calibrazione**. Un modello xG che dice 0,5 dove la realtà è 0,1 è inutile: l'xG serve a dire *quanto vale* un'occasione, non a classificarla.

Il risultato misurato conferma la scelta: xG medio previsto **0,0950** contro **0,0951** di gol reali sull'insieme di verifica. Uno scarto di un decimillesimo.

## 4. Numeri misurati

### La divisione

| | Tiri | Partite | Frequenza dei gol |
| --- | ---: | ---: | ---: |
| Addestramento | 34.582 | 1.402 | 0,0946 |
| Verifica | 8.597 | 351 | 0,0951 |

Nessuna partita compare da entrambe le parti. Lo scarto fra le due frequenze è
0,2 deviazioni standard.

### Il modello base (M5-T4)

Regressione logistica su distanza, angolo, parte del corpo, tipo di tiro,
schema di gioco e sotto pressione.

| | Log loss | Brier | AUC |
| --- | ---: | ---: | ---: |
| Sempre la frequenza media | 0,31703 | 0,08606 | 0,500 |
| **Modello base** | **0,26214** | **0,07387** | **0,7893** |
| xG di StatsBomb | 0,24515 | 0,06858 | 0,8199 |

**Il Brier score va letto rispetto a un riferimento.** Un modello che risponde
sempre «0,0951» ottiene 0,08606: è il punto di partenza. Su quella scala:

| | Miglioramento sul riferimento |
| --- | ---: |
| Modello base | **14,2 %** |
| xG di StatsBomb | 20,3 % |

Il modello base cattura circa il **70 %** del miglioramento che StatsBomb
ottiene, usando sei variabili e nessuna informazione spaziale.

| Cosa | Valore |
| --- | --- |
| Calibrazione, xG medio contro gol reali | 0,0950 contro 0,0951 |
| Tiri modellabili | 43.179 su 43.849 |
| Copertura del fotogramma sui tiri modellabili | 100 % |

## 5. Problemi incontrati

Il racconto a caldo è in [`NOTES.md`](../../NOTES.md).

## 6. Cosa resta aperto

- **Il modello base usa le variabili grezze**, senza trasformazioni come il
  logaritmo della distanza. È deliberato: un riferimento deve restare un
  riferimento, e aggiungere non linearità a mano confonderebbe il confronto con
  il gradient boosting di M5-T5.
- **`joblib` emette un avviso di deprecazione con NumPy 2.5** al caricamento dei
  modelli. È interno alla libreria e verrà risolto a monte; silenziarlo
  nasconderebbe una futura rottura.
- **I modelli non sono versionati fino a M7-T1**, come i Parquet. Oltre al
  motivo comune — si rigenerano spesso e git conserva ogni versione dei binari
  — ce n'è uno specifico: un file `.pkl` è Python serializzato, e **caricarlo
  esegue codice**. Un modello nel repository è una superficie di attacco, e va
  committato quando è il prodotto finito e rigenerabile con un comando.

## 7. Come verificarlo

```bash
uv run python -m pytest -m "not rete"
uv run python scripts/train_model.py
```
