# Schermate della milestone M6

Sette immagini, una per vista. Il criterio di M6-T14 non si chiude senza.

| File | Vista | Stato |
| --- | --- | --- |
| `home.png` | Home | ✅ tutte le competizioni, mappa di calore e indicatori |
| `squadre.png` | Squadre | ✅ Serie A, la classifica con gli xG e la frase calcolata |
| `giocatori.png` | Giocatori | ✅ Serie A, con Higuaín in cima e i quattro reparti |
| `partite.png` | Partite | ✅ Europei, l'Italia con lo scarto di xG partita per partita |
| `confronto.png` | Confronto leghe | ✅ le quattro schede e le curve di densità |
| `modello.png` | Modello xG | ✅ le due varianti e l'inizio della calibrazione |
| `metodologia.png` | Metodologia | ✅ la catena del dato e il magazzino |

Più due che non sono viste ma servono alla spiegazione del cambio tema, che è
la seconda metà del criterio:

| File | Cosa mostra |
| --- | --- |
| `tema-serie-a.png` | La Home in Serie A: fondo scuro, accenti verdi |
| `tema-champions.png` | La scheda del Real Madrid nelle finali: tutto blu |
| `metodologia-verifiche.png` | Le dieci verifiche, ognuna con il proprio test |

## Come catturarle

Finestra del browser larga almeno **1600 px** — sotto, le colonne si accavallano
e le schede vanno a capo. Cattura la pagina intera dove ci sta, o la parte alta
fino al primo grafico dove la pagina è lunga.

**Le immagini vanno preparate prima di committarle.** A schermo intero pesano
2-3 MB, un terzo dell'intero magazzino. Il trattamento applicato a quelle
presenti — ridimensionamento a 1600 px e riduzione a 256 colori — le porta a
1,3 MB in tutto senza perdita visibile: le schermate di un'interfaccia hanno
poche tinte piatte, e la palette ridotta le rappresenta quasi esattamente.

```python
from PIL import Image

im = Image.open("originale.png")
im.thumbnail((1600, 1600), Image.LANCZOS)
im.convert("RGB").quantize(colors=256).save("finale.png", "PNG", optimize=True)
```

Misurato sulle prime sette: PNG diretto 3,8 MB, JPEG di qualità 85 circa 0,9 MB ma
con aloni attorno al testo, **PNG a 256 colori 1,3 MB e testo intatto**.

## Una scelta consapevole

Le schermate **invecchiano**: la prima modifica a una vista le rende obsolete, e
nessun test se ne accorge. Restano perché il criterio della task le chiede e
perché un documento di milestone racconta com'era il progetto **in quel
momento** — non è documentazione di riferimento, è un rapporto datato. Chi vuole
vedere la dashboard di oggi la esegue.
