# Risultati misurati di M5

> **File generato da `scripts/train_model.py`. Non modificare a mano.**
> Rigenerabile con `uv run python scripts/train_model.py`.

Addestramento: 34.553 tiri su 1.402 partite. Verifica: 8.592 tiri su 351 partite, mai viste.

Scartati 34 tiri senza il portiere avversario nel fotogramma, da tutti i modelli.

Ambiente: scikit-learn 1.9.0, pandas 3.0.5.


### Confronto fra classi di modello e insiemi di variabili

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,31389 | 0,08595 | 0,5000 | 0,0 % | 0,0950 |
| logistica base | 0,26151 | 0,07371 | 0,7903 | 14,2 % | 0,0948 |
| alberi base | 0,26280 | 0,07436 | 0,7862 | 13,5 % | 0,0943 |
| logistica spaziale | 0,24882 | 0,07037 | 0,8158 | 18,1 % | 0,0963 |
| alberi spaziale | 0,24924 | 0,07069 | 0,8134 | 17,8 % | 0,0959 |
| StatsBomb | 0,24476 | 0,06846 | 0,8203 | 20,4 % | 0,0929 |

### Da dove viene il guadagno (regressione logistica)

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,31389 | 0,08595 | 0,5000 | 0,0 % | 0,0950 |
| base | 0,26151 | 0,07371 | 0,7903 | 14,2 % | 0,0948 |
| + solo portiere | 0,25346 | 0,07174 | 0,8086 | 16,5 % | 0,0958 |
| + solo difensori | 0,25505 | 0,07194 | 0,8029 | 16,3 % | 0,0956 |
| + solo cono | 0,25798 | 0,07281 | 0,7973 | 15,3 % | 0,0948 |
| + tutto | 0,24882 | 0,07037 | 0,8158 | 18,1 % | 0,0963 |
