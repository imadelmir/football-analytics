# Relazioni di milestone

Ogni milestone si chiude con il suo file. Non è documentazione di cortesia:
l'ultimo task di ciascuna milestone è esattamente questo, e **la milestone non
è completa finché il file non esiste**.

Il modello sta in [`_template.md`](_template.md) e si copia **all'inizio** della
milestone, non alla fine. Le note si aggiungono mentre si lavora: un file
scritto a caldo racconta cose che una ricostruzione a posteriori non ricorda
più.

---

## Stato

| # | Milestone | Issue | Stato | Relazione |
| --- | --- | --- | --- | --- |
| M1 | Fondamenta | 7 | 🟢 conclusa | [M1-fondamenta.md](M1-fondamenta.md) |
| M2 | Ingestione | 7 | 🟢 conclusa | [M2-ingestione.md](M2-ingestione.md) |
| M3 | Trasformazione | 8 | 🟢 conclusa | [M3-trasformazione.md](M3-trasformazione.md) |
| M4 | Esplorazione | 3 | 🟢 conclusa | [M4-esplorazione.md](M4-esplorazione.md) |
| M5 | Modello xG | 12 | 🟢 conclusa | [M5-modello-xg.md](M5-modello-xg.md) |
| M6 | Dashboard | 14 | 🟢 conclusa | [M6-dashboard.md](M6-dashboard.md) |
| M7 | Pubblicazione | 7 | 🟢 conclusa | [M7-pubblicazione.md](M7-pubblicazione.md) |
| M8 | Portfolio | 6 | ⚪ da fare | — |

Legenda: ⚪ da fare · 🟡 in corso · 🟢 conclusa

## Numeri chiave

Si compilano man mano, e **solo con valori misurati**. Sono gli stessi che
finiranno nel frontmatter del case study: si prendono da qui, non si
ricalcolano a mano.

| Cosa | Valore | Da quale milestone |
| --- | --- | --- |
| Pacchetti bloccati in `uv.lock` | 68 | M1 |
| Competizioni scelte | 9 | M2 |
| Partite scaricate | 1.753 | M2 |
| Di cui con file 360 | 167 | M2 |
| Peso di `data/raw/` | 6,25 GB | M2 |
| Tiri analizzati | 43.849 | M3 |
| Gol | 4.578 | M3 |
| Tiri con freeze frame | 43.264 — 99 % | M3 |
| Peso di `data/processed/` | 2,87 MB | M3 |
| Test automatici | 131 | M3 |
| xG mediano di un tiro | 0,051 | M4 |
| Distanza mediana di tiro | 19 m | M4 |
| Conversione, 2 avversari inquadrati | 38,9 % | M4 |
| Conversione, 8+ avversari inquadrati | 7,2 % | M4 |
| Brier score, modello base | 0,07305 | M5 |
| Brier score, modello spaziale | 0,07050 | M5 |
| Brier score, xG di StatsBomb | 0,06894 | M5 |
| AUC, modello base → spaziale | 0,7985 → 0,8186 | M5 |
| **Quanto vale vedere i difensori** | **+2,9 punti, +18 % relativo** | M5 |
| Quota del divario da StatsBomb colmata | 62 % | M5 |
| Guadagno sulle finali, mai viste | 18,2 % contro 19,2 % | M5 |
| Accordo con StatsBomb, per partita | Pearson 0,952 | M5 |
| Riproducibilità, due addestramenti | scarto 0,0 | M5 |
| Errore di calibrazione, modello spaziale | 0,00964 — il migliore dei tre | M5 |
| Test automatici | 223 | M5 |
| Viste della dashboard | 7 nel menu, 10 script | M6 |
| Palette del tema | 9, una per competizione | M6 |
| Righe in `app/` | 4.612 | M6 |
| Peso del magazzino letto dalla dashboard | 6,29 MB | M6 |
| Letture dal disco per sessione | 1 per tabella | M6 |
| Limiti dichiarati in pagina | 11 | M6 |
| Verifiche citate con il proprio test | 10 | M6 |
| Test automatici | 703, copertura 94 % | M7 |
| Peso del magazzino in memoria | 49,6 MB — 7,9× il Parquet | M7 |
| Processo con il magazzino letto | 231 MB su 1.024 di tetto | M7 |
| Margine sul tetto di Streamlit Cloud | 791 MB | M7 |
| Annotazioni in `NOTES.md` | 50, su sette milestone | M7 |
| Autogol, che non sono tiri di nessuno | 156 | M7 |

> **Il conteggio dei test è di M7, non di M6.** Alla chiusura di M6 non era
> stato annotato, e ricostruirlo sottraendo i test aggiunti dopo darebbe un
> numero calcolato invece che misurato. Vale la regola di sempre: si scrive
> quando è stato preso.

> I valori vengono da [`M5-risultati.md`](M5-risultati.md), generato da
> `scripts/train_model.py`. Sono stati rigenerati a M5-T9, quando le finali
> sono uscite dal campione: i punteggi si sono alzati di due punti perché è
> cambiato il riferimento, non il modello.
