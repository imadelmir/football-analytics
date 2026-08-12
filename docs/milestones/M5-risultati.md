# Risultati misurati di M5

> **File generato da `scripts/train_model.py`. Non modificare a mano.**
> Rigenerabile con `uv run python scripts/train_model.py`.

Addestramento: 34.553 tiri su 1.402 partite. Verifica: 8.592 tiri su 351 partite, mai viste.

Scartati 34 tiri senza il portiere avversario nel fotogramma, da tutti i modelli.

Ambiente: scikit-learn 1.7.2, pandas 2.3.3.


### Confronto fra classi di modello e insiemi di variabili

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,31389 | 0,08595 | 0,5000 | 0,0 % | 0,0950 |
| logistica base | 0,26151 | 0,07371 | 0,7903 | 14,2 % | 0,0948 |
| alberi base | 0,26276 | 0,07434 | 0,7862 | 13,5 % | 0,0943 |
| logistica spaziale | 0,24882 | 0,07037 | 0,8158 | 18,1 % | 0,0963 |
| alberi spaziale | 0,24792 | 0,07047 | 0,8167 | 18,0 % | 0,0957 |
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

### Curva di calibrazione — logistica base

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 860 | 0,0119 | 0,0198 | -0,0079 | -1,7 |
| 2 | 859 | 0,0230 | 0,0186 | 0,0044 | 0,9 |
| 3 | 859 | 0,0324 | 0,0349 | -0,0025 | -0,4 |
| 4 | 859 | 0,0430 | 0,0256 | 0,0174 | 3,2 |
| 5 | 859 | 0,0552 | 0,0384 | 0,0168 | 2,6 |
| 6 | 859 | 0,0703 | 0,0536 | 0,0167 | 2,2 |
| 7 | 859 | 0,0898 | 0,0815 | 0,0083 | 0,9 |
| 8 | 859 | 0,1168 | 0,1304 | -0,0136 | -1,2 |
| 9 | 859 | 0,1627 | 0,1944 | -0,0317 | -2,3 |
| 10 | 860 | 0,3432 | 0,3523 | -0,0092 | -0,6 |

### Curva di calibrazione — logistica spaziale

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 860 | 0,0095 | 0,0128 | -0,0032 | -0,8 |
| 2 | 859 | 0,0185 | 0,0244 | -0,0059 | -1,1 |
| 3 | 859 | 0,0270 | 0,0233 | 0,0037 | 0,7 |
| 4 | 859 | 0,0368 | 0,0361 | 0,0007 | 0,1 |
| 5 | 859 | 0,0488 | 0,0244 | 0,0244 | 4,6 |
| 6 | 859 | 0,0633 | 0,0466 | 0,0167 | 2,3 |
| 7 | 859 | 0,0830 | 0,0629 | 0,0202 | 2,4 |
| 8 | 859 | 0,1143 | 0,1257 | -0,0115 | -1,0 |
| 9 | 859 | 0,1735 | 0,1839 | -0,0104 | -0,8 |
| 10 | 860 | 0,3876 | 0,4093 | -0,0217 | -1,3 |

### Curva di calibrazione — StatsBomb

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 860 | 0,0086 | 0,0221 | -0,0134 | -2,7 |
| 2 | 859 | 0,0189 | 0,0151 | 0,0038 | 0,9 |
| 3 | 859 | 0,0270 | 0,0163 | 0,0107 | 2,5 |
| 4 | 859 | 0,0354 | 0,0221 | 0,0132 | 2,6 |
| 5 | 859 | 0,0451 | 0,0361 | 0,0090 | 1,4 |
| 6 | 859 | 0,0577 | 0,0477 | 0,0099 | 1,4 |
| 7 | 859 | 0,0753 | 0,0838 | -0,0086 | -0,9 |
| 8 | 859 | 0,1022 | 0,1059 | -0,0038 | -0,4 |
| 9 | 859 | 0,1621 | 0,1781 | -0,0160 | -1,2 |
| 10 | 860 | 0,3964 | 0,4221 | -0,0257 | -1,5 |
