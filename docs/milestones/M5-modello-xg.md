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
| `src/football_analytics/metriche.py` | Log loss, Brier, AUC e il riferimento — mai l'accuratezza |
| `tests/test_features.py` | 42 test, molti su casi geometrici calcolabili a mano |
| `tests/test_divisione.py` | 19 test, compreso uno che dimostra il difetto evitato |
| `tests/test_modello.py` | Proprietà che nessun messaggio d'errore segnalerebbe |
| `tests/test_metriche.py` | Due test dimostrano le trappole invece di dichiararle |

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

Tutti i punteggi sono calcolati da `metriche.py` sullo stesso insieme di
verifica, e riportati qui **copiando l'uscita del programma**.

| | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sempre la frequenza media | 0,31429 | 0,08610 | 0,500 | 0,0 % | 0,0951 |
| **Modello base** | **0,26214** | **0,07387** | **0,7893** | **14,2 %** | 0,0950 |
| xG di StatsBomb | 0,24515 | 0,06858 | 0,8199 | 20,3 % | 0,0929 |

> **Correzione.** La prima stesura riportava 0,31703 come log loss del
> riferimento. L'avevo stimato a mente invece di calcolarlo, e scritto con
> cinque decimali come se l'avessi misurato. Il valore calcolato è **0,31429**.
> Il numero sbagliato resta nel messaggio del commit `fbb48bb`, che non si
> riscrive. Da M5-T5 il riferimento esce da `metriche.riferimento()` e non è
> più scrivibile a mano.

**Il Brier score va letto rispetto a un riferimento.** Un modello che risponde
sempre «0,0951» ottiene 0,08610 senza aver imparato niente: è lo zero della
scala. Su quella scala il modello base cattura il **69,8 %** di quello che
cattura StatsBomb, usando sei variabili e nessuna informazione spaziale.

| Cosa | Valore |
| --- | --- |
| Calibrazione, xG medio contro gol reali | 0,0950 contro 0,0951 |
| Tiri modellabili | 43.179 su 43.849 |
| Copertura del fotogramma sui tiri modellabili | 100 % |

### Il modello ad alberi (M5-T5) — **risultato negativo**

Gradient boosting a istogrammi sulle **stesse identiche variabili**, stessa
divisione, stesso preprocessore. Il confronto cambia una cosa sola: la classe
di modello.

Iperparametri scelti in validazione incrociata a 5 pieghe **raggruppate per
partita**, senza mai guardare l'insieme di verifica:

| Configurazione | Iterazioni | Tasso | Foglie | Log loss in CV |
| --- | ---: | ---: | ---: | ---: |
| **compatto** | 200 | 0,10 | 15 | **0,26574** |
| prudente | 300 | 0,05 | 31 | 0,26779 |
| lento | 600 | 0,03 | 31 | 0,26905 |

Poi il vincitore, misurato una volta sulla verifica:

| | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Modello base, logistica | **0,26214** | **0,07387** | **0,7893** | **14,2 %** | 0,0950 |
| Gradient boosting | 0,26374 | 0,07456 | 0,7845 | 13,4 % | 0,0943 |

**Il gradient boosting perde su tutte e tre le metriche:** +0,93 % di Brier,
+0,61 % di log loss, −0,0048 di AUC. Non è una questione di calibrazione —
*ordina* peggio.

**Perché.** Le variabili base sono due continue e quattro categoriche, e
l'`angolo` **è già una trasformazione non lineare**, calcolata con il teorema
del coseno a partire dalle coordinate. Il lavoro non lineare l'ha fatto la
costruzione delle variabili; al modello non resta distorsione da correggere,
solo varianza da pagare. La validazione incrociata lo dice per conto suo: fra
le tre configurazioni vince **la più piccola** e perde quella con 600
iterazioni. Un modello che migliora rimpicciolendosi sta dicendo che non c'è
struttura da trovare.

**Perché era il risultato utile.** La previsione registrata in `NOTES.md`
diceva che il gradient boosting avrebbe vinto grazie alla variabile del
portiere, che è spaziale e qui non c'è. Il risultato va oltre: senza quella
variabile gli alberi non pareggiano, peggiorano. Questo rende M5-T6
interpretabile — la classe di modello su queste variabili vale meno di zero,
quindi un eventuale salto aggiungendo le variabili spaziali sarà attribuibile
all'**informazione**, non all'algoritmo.

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
- **Il confronto fra le due classi di modello è avvenuto sull'insieme di
  verifica**, che è il secondo sguardo dopo M5-T4. Il posto giusto per
  scegliere fra modelli è la validazione incrociata; il test si guarda alla
  fine. Gli iperparametri sono stati scelti correttamente in CV, ma il
  punteggio in CV della regressione logistica non è stato registrato, quindi il
  confronto fra classi è dichiarato come misurato: sul test. Da colmare prima
  di M5-T12.
- **`models/xg_base.pkl` contiene oggi il gradient boosting**, non il modello
  che ha vinto. La scelta di quale classe finisce in produzione è rinviata a
  M5-T6, dove le variabili spaziali potrebbero ribaltare il confronto: gli
  alberi trattano i valori mancanti da soli, cosa che alla regressione logistica
  non riesce senza imputazione.
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
