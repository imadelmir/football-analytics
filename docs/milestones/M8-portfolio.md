# M8 — Portfolio

> Il progetto ha un case study nel portfolio, in italiano e in inglese, al posto
> del segnaposto che occupava quel posto da mesi.

**Periodo:** 19 agosto 2026 · **Task:** 6 · **Repository toccato:**
`AVENA50/Portfolio-imad-el-mir`

---

## 1. Cosa è stato costruito

Fino a M7 il progetto esisteva e funzionava, ma nel portfolio era una scheda che
diceva «progetto pianificato: il case study comparirà qui quando sarà
costruito». M8 ha sostituito quella scheda con il primo case study completo del
portfolio — nessuno degli altri sette progetti ne aveva uno.

Il contenuto non è una descrizione del progetto: è **la domanda, l'esperimento e
la risposta**. Quanto vale sapere dove sono i difensori, come lo si misura, e i
+2,9 punti di Brier score che ne escono, con la tabella dei quattro modelli a
confronto.

Il frontmatter usa quasi tutto lo schema del portfolio, che finora nessun
progetto aveva riempito: quattro metriche per i badge dell'intestazione, cinque
punti salienti, sei funzionalità, quattro lezioni apprese, e la sezione
architettura con i quattro strati e quattro decisioni tecniche con il loro
perché.

---

## 2. File creati e modificati

Tutti nel repository del portfolio.

| File | Cosa |
| --- | --- |
| `src/content/projects/it/football-analytics.mdx` | Case study italiano, dal segnaposto di 24 righe a un documento completo |
| `src/content/projects/en/football-analytics.mdx` | Lo stesso in inglese, con i sette campi condivisi identici |
| `public/images/projects/football-analytics/*.webp` | Dieci schermate convertite dalla documentazione di M6 |
| `public/images/projects/football-analytics/cover.png` | Copertina 16:9 ricavata dalla Home reale, al posto del segnaposto |

---

## 3. Decisioni tecniche

### Scelta: categoria `ai-ml` invece di `data-bi`

**Alternativa scartata:** lasciare `data-bi`, che il segnaposto dichiarava.

**Perché:** il cuore del progetto sono due modelli addestrati e confrontati con
Brier score, AUC e curve di calibrazione; la dashboard è il modo in cui li si
guarda, non il risultato. La categoria è un campo condiviso fra le due lingue,
quindi è stata cambiata in entrambe insieme.

### Scelta: sei schermate referenziate, dieci committate

**Alternativa scartata:** committare solo le sei che compaiono in pagina.

**Perché:** le quattro non usate — `partite`, `confronto`, `tema-serie-a`,
`metodologia-verifiche` — costano 250 KB e servono se un giorno la galleria si
allunga o se il progetto va raccontato altrove. Sotto i 250 KB il costo di
tenerle è inferiore a quello di rigenerarle.

### Scelta: il case study nomina tre difetti del progetto

**Alternativa scartata:** una sezione «cosa ho imparato» in positivo, come si
usa nei portfolio.

**Perché:** i tre difetti raccontati — una vista che dichiarava il falso,
un'etichetta che attribuiva al campionato i numeri di una squadra, due
definizioni della stessa parola nello stesso riquadro — appartengono tutti alla
stessa famiglia: **il codice funzionava e il significato no**. È la cosa più
difficile da imparare in questo mestiere, e mostrarla dice più di un elenco di
tecnologie.

### Scelta: niente video

**Alternativa scartata:** registrare la dimostrazione che M8-T2 prevede.

**Perché:** il progetto ha un indirizzo pubblico funzionante. Chi vuole vedere
la dashboard in movimento ci clicca, e un video di trenta secondi costerebbe
5 MB per mostrare meno di quanto mostri l'app. Il campo `video` dello schema
resta libero per il giorno in cui servisse.

---

## 4. Numeri misurati

| Cosa | Valore | Come è stato ottenuto |
| --- | --- | --- |
| Schermate convertite | 10, da PNG a WebP | `PIL`, qualità 88, nessun passaggio più basso necessario |
| Peso delle schermate | da 1.662 KB a **677 KB**, −59 % | somma dei file |
| La più pesante | `metodologia-verifiche`, 88 KB | tetto del criterio: 200 KB |
| Copertina | 1600×900, **125 KB** | ritaglio 16:9 della Home, quantizzato a 256 colori |
| Campi condivisi verificati | 7 su 7 identici | confronto fra i due frontmatter |
| Lunghezza delle tagline | 135 e 128 caratteri | limite dello schema: 180 |
| Metriche, punti salienti, funzionalità, lezioni | 4, 5, 6, 4 | frontmatter |
| Strati e decisioni in `architecture` | 4 e 4 | frontmatter |

**I numeri del case study non sono stati ricopiati a mano da questi file: sono
stati presi da `M5-risultati.json` e dalle relazioni di milestone mentre il
documento veniva scritto.** Il criterio di M8-T6 chiede che coincidano, e la
verifica è stata fatta confrontandoli uno per uno — non da un test, perché i due
repository sono separati e nessuno dei due può leggere l'altro. È l'unico
criterio di tutto il progetto verificato a mano e non da un comando, e vale la
pena saperlo.

---

## 5. Problemi incontrati

### Ho sovrascritto un file funzionante per una ricerca troncata

**Cosa:** ho concluso che la pagina di dettaglio dei progetti non esistesse, ho
proposto di costruirla, e l'ho scritta sovrascrivendo quella vera.

**Come si è capito:** da `git status`, che mostrava ` M` — modificato — invece
di `??` — non tracciato. Un file non tracciato è un file nuovo; un file
modificato è un file che c'era.

**La causa:** avevo cercato le rotte con
`find src/app -maxdepth 4 -name "page.tsx"`, e il percorso vero —
`[locale]/(site)/projects/[slug]/page.tsx` — sta a profondità **cinque**. Non è
comparso nell'elenco, e ho preso l'assenza dal risultato di una ricerca per
assenza dal progetto.

**Risolto:** `git checkout --` sul file. Non si è perso niente, ma solo perché
era committato.

**Cosa insegna:** l'errore non è stato il `maxdepth` sbagliato — quello è un
refuso. È aver trattato «non l'ho trovato» come «non c'è», e aver poi costruito
tre paragrafi di diagnosi convincente sopra quella conclusione, fino a proporre
un lavoro intero che non serviva. **Una ricerca che non trova qualcosa è
un'informazione sulla ricerca, non sul progetto.** E prima di sovrascrivere un
file bisogna sapere se esiste: `git status` lo diceva in due caratteri.

Il file originale, oltretutto, era migliore di quello che avevo scritto: non
dichiara `image` nei metadati, perché accanto c'è un `opengraph-image.tsx` che
verrebbe sovrascritto da quella dichiarazione. Un dettaglio della piattaforma
che io non conoscevo.

### Il portfolio e il progetto stanno su due account diversi

Il portfolio è su `AVENA50/Portfolio-imad-el-mir`, football-analytics su
`imadelmir/football-analytics`. Chi arriva al case study e clicca sul link
GitHub del sito finisce su un account dove questo progetto non c'è. Non è un
difetto del lavoro fatto, ma è una cosa che chi visita il portfolio nota.

---

## 6. Cosa resta aperto

**Il video di M8-T2.** Il campo `video` dello schema è libero e la sezione della
pagina lo aspetta. Costa una registrazione dello schermo e una compressione
sotto i 5 MB.

**Il tempo di risveglio dell'app**, che M7 aveva già dichiarato non misurato.
Il comando per farlo è nella sezione 7 di
[`M7-pubblicazione.md`](M7-pubblicazione.md).

**Le altre sette schede del portfolio sono ancora segnaposto.** Football
Analytics è il primo case study vero, e lo schema che ora sappiamo riempire vale
per tutti.

---

## 7. Come verificarlo

Dal repository del portfolio:

```bash
npm run check    # typecheck, lint, test
npm run build    # valida il frontmatter contro lo schema zod
```

Un frontmatter non valido ferma la build indicando file e campo. Poi le due
pagine, che è il criterio di M8-T5:

```bash
npm run dev
```

- `http://localhost:3000/it/projects/football-analytics`
- `http://localhost:3000/en/projects/football-analytics`

Le sezioni compaiono solo se il frontmatter le dichiara: qui ci sono
intestazione con le quattro metriche, stack, architettura, funzionalità,
galleria, corpo del case study con l'indice, lezioni e navigazione fra progetti.
La sezione video non c'è, ed è corretto.
