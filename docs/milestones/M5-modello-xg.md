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

> **Tutti i numeri di questa sezione sono stati rigenerati a M5-T9**, quando le
> 18 finali di Champions sono uscite da addestramento e verifica. La fonte
> autorevole è [`M5-risultati.md`](M5-risultati.md), prodotto da
> `scripts/train_model.py`: qui si citano, non si ricopiano.
>
> I punteggi si sono alzati di circa due punti rispetto alle prime stesure — il
> modello base da 14,2 % a 16,3 %, quello spaziale da 18,1 % a 19,2 % — **non
> perché il modello sia migliorato**, ma perché è cambiato l'insieme su cui si
> misura: senza le finali la frequenza dei gol passa da 0,0950 a 0,0966 e con
> essa il riferimento. È il motivo per cui un guadagno va sempre letto insieme
> al riferimento da cui parte.

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

### Il modello spaziale (M5-T6) — la risposta alla domanda del progetto

> **Quanto vale, davvero, sapere dove sono i difensori?**

I numeri sono in [`M5-risultati.md`](M5-risultati.md), generato da
`scripts/train_model.py`. Questa sezione li **cita**, non li ricopia.

Quattro modelli, due classi per due insiemi di variabili, sulle stesse
identiche righe e sullo stesso identico insieme di verifica:

| | Log loss | Brier | AUC | Guadagno |
| --- | ---: | ---: | ---: | ---: |
| Riferimento | 0,31759 | 0,08728 | 0,5000 | 0,0 % |
| Logistica base | 0,25872 | 0,07305 | 0,7985 | 16,3 % |
| Alberi base | 0,25953 | 0,07351 | 0,7976 | 15,8 % |
| **Logistica spaziale** | **0,24933** | **0,07050** | **0,8186** | **19,2 %** |
| Alberi spaziale | 0,24950 | 0,07079 | 0,8168 | 18,9 % |
| xG di StatsBomb | 0,24575 | 0,06894 | 0,8231 | 21,0 % |

**La risposta: +2,9 punti di guadagno**, da 16,3 % a 19,2 %. In termini
relativi è **+18 % di capacità esplicativa**, con l'AUC che sale di 0,020.

Detto nel modo più utile: il divario che ci separava dall'xG di StatsBomb era
di 4,7 punti. **Il fotogramma ne chiude 2,9, cioè il 62 %.** Si passa dal
catturare il 77,6 % del loro segnale al 91,4 %.

#### Da dove viene il guadagno

| Aggiunta al modello base | Variabili | Guadagno | Δ |
| --- | ---: | ---: | ---: |
| — | 0 | 16,3 % | |
| Solo il portiere | 2 | 17,6 % | +1,3 |
| Solo i difensori | 3 | 18,2 % | +1,9 |
| Solo i difensori nel cono | 1 | 17,2 % | +0,9 |
| Tutto | 5 | 19,2 % | +2,9 |

I due gruppi contribuiscono in modo **confrontabile**, e presi da soli sommano
3,2 punti contro i 2,9 che danno insieme: si sovrappongono poco.

> **Correzione.** La prima stesura affermava che «il portiere vale almeno
> quanto i difensori, con una variabile in meno», sulla base di +2,3 contro
> +2,1. Rigenerando i numeri senza le finali l'ordine si **inverte**: +1,3
> contro +1,9. Togliendo 437 tiri su 34.000 una conclusione cambiava verso —
> quindi non era una conclusione, era rumore raccontato come scoperta.
>
> Quello che regge è che entrambi i gruppi contribuiscono, e che il totale è
> minore della somma delle parti. **Quale dei due pesi di più, questi dati non
> lo dicono.**

#### Perché in produzione va la regressione logistica

Vince sulle variabili base, vince su quelle spaziali, e in più:

- pesa **4 KB contro 368 KB**, cosa che conta su Streamlit Cloud con meno di
  1 GB di RAM;
- ha la calibrazione **garantita dalla forma del modello** — massimizzare la
  verosimiglianza con un'intercetta impone che la media prevista uguagli la
  frequenza osservata — invece che verificata a posteriori;
- **è riproducibile fra versioni delle librerie.** Le due regressioni
  logistiche danno gli stessi identici cinque decimali con scikit-learn 1.7.2 e
  1.9.0; i due modelli ad alberi no, e con 1.9.0 l'AUC del modello spaziale
  scende di 0,003. Per un progetto che deve restare in piedi anche fra un anno
  non è un dettaglio.

### L'applicazione alle finali (M5-T9) — la prova su un'altra epoca

Le 18 finali di Champions vanno dal 1971 al 2019 e sono state **escluse da
addestramento e verifica**, non solo dall'addestramento. Il modello le incontra
per la prima volta qui.

| | Log loss | Brier | AUC | Guadagno |
| --- | ---: | ---: | ---: | ---: |
| Riferimento | 0,30501 | 0,08278 | 0,5000 | 0,0 % |
| Logistica base | 0,25680 | 0,07202 | 0,7832 | 13,0 % |
| **Logistica spaziale** | **0,24136** | **0,06771** | **0,8174** | **18,2 %** |
| xG di StatsBomb | 0,23254 | 0,06499 | 0,8362 | 21,5 % |

**Il modello non crolla:** 18,2 % sulle finali contro 19,2 % sulla verifica,
AUC 0,8174 contro 0,8186. Un modello addestrato su partite dal 2015 al 2024
funziona su finali che partono dal 1971.

Prevede 0,0830 di xG medio contro 0,0911 di gol reali — sembra una
sottostima, ma su 560 tiri l'errore standard della frequenza è 0,0121: lo
scarto vale **0,67 deviazioni standard** ed è compatibile con il caso. Anche
l'xG di StatsBomb sottostima allo stesso modo (0,0851).

**Il difetto trovato prima.** La divisione casuale per partita aveva messo 437
dei 561 tiri delle finali **dentro l'addestramento**, mentre README e
`config.Gruppo` dichiaravano da M2 che quelle partite servivano come prova
fuori campione. Non era leakage in senso stretto, ma il progetto diceva una
cosa e ne faceva un'altra. La separazione ora avviene in
`features.separa_applicazione`, prima della divisione e quindi prima che
qualunque numero venga misurato.

### L'accordo con StatsBomb (M5-T8)

Domanda diversa dalle precedenti: non *quale* modello sia migliore, ma **quanto
i due si somiglino**.

| | Per tiro | Per partita |
| --- | ---: | ---: |
| Correlazione di Pearson | 0,9076 | **0,9529** |
| Correlazione di Spearman | 0,8863 | |
| Scarto medio, con segno | +0,0034 | +0,082 xG |
| Scarto assoluto mediano | 0,0142 | 0,176 xG |
| **Scarto relativo mediano** | **29,5 %** | |

**Su un singolo tiro i due modelli discordano tipicamente del 30 %**, e sui
totali di partita concordano a 0,95. È il numero da dichiarare nella pagina di
metodologia: l'xG di un tiro va letto come una stima grezza, quello di una
partita regge.

Lo scarto assoluto medio **non va letto da solo**: uno scarto grande è possibile
solo dove l'xG è grande, e l'xG è grande sotto porta. Guardandolo senza
normalizzare si conclude che i modelli discordano di più sui tiri ravvicinati,
quando discordano esattamente uguale. C'è un test che lo dimostra.

**Perché l'aggregazione aiuta, e quando non aiuterebbe.** Sommando tiri con
errori indipendenti crescono di pari passo segnale e rumore, e la correlazione
non si muove: verificato su dati sintetici, 0,9472 → 0,9464. Migliora solo se
esiste una componente **condivisa dentro la partita**: 0,9551 → 0,9916. I dati
veri si comportano come il secondo caso, quindi **le partite differiscono
davvero fra loro** nel tipo di occasioni che producono, e i due modelli lo
vedono allo stesso modo anche dove discordano tiro per tiro.

### La curva di calibrazione (M5-T7)

Le metriche riassuntive dicono **quanto** un modello sbaglia; la curva dice
**dove**. I gruppi sono quantili, non intervalli di ampiezza uguale: su un xG la
mediana sta a 0,05 e dieci intervalli larghi 0,1 metterebbero il 61 % dei tiri
nel primo, lasciando vuoti gli ultimi cinque. Le tabelle complete sono in
[`M5-risultati.md`](M5-risultati.md).

| Modello | Errore di calibrazione | Gruppi oltre 2 SE |
| --- | ---: | ---: |
| Logistica base | 0,01284 | 4 su 10 |
| Logistica spaziale | 0,01185 | 3 su 10 |
| xG di StatsBomb | 0,01142 | 3 su 10 |

**Il modello spaziale ha uno scarto medio con segno di +0,0013 — quasi
perfetto — e una curva che sbaglia sistematicamente.** Gli scarti si
compensano: sovrastima la fascia centrale, sottostima quella alta.

| Gruppo | Logistica base | Logistica spaziale | StatsBomb |
| ---: | ---: | ---: | ---: |
| 4 | +3,2 | +0,1 | +2,6 |
| 5 | +2,6 | **+4,6** | +1,4 |
| 6 | +2,2 | +2,3 | +1,4 |
| 9 | −2,3 | −0,8 | −1,2 |
| 10 | −0,6 | −1,3 | −1,5 |

*(scarto fra xG previsto e gol osservati, in errori standard)*

**Il difetto è condiviso con l'xG di StatsBomb**, che non è stato addestrato
sulla nostra divisione. Dieci celle su trenta superano le 2 deviazioni standard,
dove per caso ne aspetteremmo una e mezza. Non è quindi un difetto del nostro
modello: è una proprietà dei dati o della fascia. **Resta aperto** e va
verificato a M5-T9, che applica il modello a competizioni diverse ed è il posto
naturale per capire se dipende dal campionato.

È anche il motivo per cui `errore_di_calibrazione` esiste accanto allo scarto
medio: il secondo vale zero anche per un modello sbagliato ovunque, purché lo
sia in modo simmetrico.

## 5. Problemi incontrati

Il racconto a caldo è in [`NOTES.md`](../../NOTES.md).

## 6. Cosa resta aperto

- **La curva di calibrazione mostra un difetto sistematico condiviso con
  StatsBomb**: tutti i modelli sovrastimano la fascia centrale e sottostimano
  quella alta. Da verificare a M5-T9, dove il modello viene applicato a
  competizioni diverse.
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
