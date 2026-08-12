# Risultati misurati di M5

> **File generato da `scripts/train_model.py`. Non modificare a mano.**
> Rigenerabile con `uv run python scripts/train_model.py`.

Addestramento: 34.160 tiri su 1.388 partite. Verifica: 8.425 tiri su 347 partite, mai viste.

Applicazione: 560 tiri su 18 finali di Champions, escluse dall'addestramento **e** dalla verifica.

Scartati 34 tiri senza il portiere avversario nel fotogramma, da tutti i modelli.

Riproducibilita': due addestramenti con lo stesso seed danno previsioni che differiscono al massimo di 0.0e+00.

Ambiente: scikit-learn 1.9.0, pandas 3.0.5.


### Confronto fra classi di modello e insiemi di variabili

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,31759 | 0,08728 | 0,5000 | 0,0 % | 0,0966 |
| logistica base | 0,25872 | 0,07305 | 0,7985 | 16,3 % | 0,0968 |
| alberi base | 0,26078 | 0,07374 | 0,7955 | 15,5 % | 0,0963 |
| logistica spaziale | 0,24933 | 0,07050 | 0,8186 | 19,2 % | 0,0973 |
| alberi spaziale | 0,24866 | 0,07075 | 0,8192 | 18,9 % | 0,0963 |
| StatsBomb | 0,24575 | 0,06894 | 0,8231 | 21,0 % | 0,0939 |

### Da dove viene il guadagno (regressione logistica)

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,31759 | 0,08728 | 0,5000 | 0,0 % | 0,0966 |
| base | 0,25872 | 0,07305 | 0,7985 | 16,3 % | 0,0968 |
| + solo portiere | 0,25410 | 0,07190 | 0,8109 | 17,6 % | 0,0970 |
| + solo difensori | 0,25260 | 0,07135 | 0,8108 | 18,2 % | 0,0971 |
| + solo cono | 0,25579 | 0,07227 | 0,8047 | 17,2 % | 0,0968 |
| + tutto | 0,24933 | 0,07050 | 0,8186 | 19,2 % | 0,0973 |

### Applicazione alle finali di Champions, mai viste

| Modello | Log loss | Brier | AUC | Guadagno | xG medio |
| --- | ---: | ---: | ---: | ---: | ---: |
| riferimento | 0,30501 | 0,08278 | 0,5000 | 0,0 % | 0,0911 |
| logistica base | 0,25680 | 0,07202 | 0,7832 | 13,0 % | 0,0905 |
| logistica spaziale | 0,24136 | 0,06771 | 0,8174 | 18,2 % | 0,0830 |
| StatsBomb | 0,23254 | 0,06499 | 0,8362 | 21,5 % | 0,0851 |

### Scelta fra le classi, in validazione incrociata

Le pieghe sono raggruppate per partita e **l'insieme di verifica non entra**.
E' il posto dove si sceglie fra modelli; il test si guarda una volta alla fine.

| Modello | Log loss in CV |
| --- | ---: |
| logistica spaziale | 0,25409 |
| alberi spaziale | 0,25507 |
| logistica base | 0,26532 |
| alberi base | 0,26673 |

### Come legge i tiri il modello spaziale (M5-T10)

Ordinate per peso. Il coefficiente e' sulla scala standardizzata, quindi
confrontabile fra variabili; il rapporto di probabilita' e' per **unita'**
naturale, quindi leggibile in una frase.

| Variabile | Tipo | Coefficiente | Odds ratio per unita | Effetto |
| --- | --- | ---: | ---: | --- |
| `tipo_Open Play` | categoria | -1,556 | 0,211 | riduce |
| `distanza` | numerica | -1,391 | 0,853 | riduce |
| `parte_corpo_Head` | categoria | -0,800 | 0,449 | riduce |
| `portiere_avanzato` | numerica | 0,430 | 1,231 | aumenta |
| `angolo` | numerica | 0,411 | 4,699 | aumenta |
| `tipo_Free Kick` | categoria | 0,406 | 1,501 | aumenta |
| `parte_corpo_Other` | categoria | -0,386 | 0,680 | riduce |
| `distanza_portiere` | numerica | 0,357 | 1,041 | aumenta |
| `difensori_nel_cono` | numerica | -0,329 | 0,713 | riduce |
| `avversari_vicini` | numerica | -0,250 | 0,755 | riduce |
| `schema_From Corner` | categoria | -0,223 | 0,800 | riduce |
| `schema_From Throw In` | categoria | -0,189 | 0,828 | riduce |

### Accordo con l'xG di StatsBomb

Non e' una misura di *quale* modello sia migliore — quella e' la tabella
sopra — ma di **quanto i due si somiglino**.

| | Per tiro | Per partita |
| --- | ---: | ---: |
| Correlazione di Pearson | 0,9088 | 0,9522 |
| Correlazione di Spearman | 0,8861 | 0,9522 |
| Scarto medio, con segno | 0,00336 | 0,08152 |
| Scarto assoluto medio | 0,02909 | 0,21853 |
| Scarto assoluto mediano | 0,01387 | 0,17071 |
| Scarto relativo mediano | 0,2902 | 0,0827 |

### Curva di calibrazione — logistica base

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 843 | 0,0120 | 0,0178 | -0,0058 | -1,3 |
| 2 | 842 | 0,0223 | 0,0178 | 0,0045 | 1,0 |
| 3 | 843 | 0,0319 | 0,0285 | 0,0034 | 0,6 |
| 4 | 842 | 0,0429 | 0,0356 | 0,0073 | 1,1 |
| 5 | 843 | 0,0552 | 0,0391 | 0,0161 | 2,4 |
| 6 | 842 | 0,0701 | 0,0534 | 0,0166 | 2,1 |
| 7 | 842 | 0,0891 | 0,0843 | 0,0048 | 0,5 |
| 8 | 843 | 0,1156 | 0,1151 | 0,0005 | 0,0 |
| 9 | 842 | 0,1647 | 0,1960 | -0,0313 | -2,3 |
| 10 | 843 | 0,3642 | 0,3784 | -0,0142 | -0,9 |

### Curva di calibrazione — logistica spaziale

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 843 | 0,0091 | 0,0071 | 0,0020 | 0,7 |
| 2 | 842 | 0,0180 | 0,0238 | -0,0058 | -1,1 |
| 3 | 843 | 0,0267 | 0,0297 | -0,0030 | -0,5 |
| 4 | 842 | 0,0364 | 0,0309 | 0,0055 | 0,9 |
| 5 | 843 | 0,0475 | 0,0297 | 0,0179 | 3,1 |
| 6 | 842 | 0,0613 | 0,0570 | 0,0043 | 0,5 |
| 7 | 842 | 0,0812 | 0,0677 | 0,0135 | 1,6 |
| 8 | 843 | 0,1127 | 0,1044 | 0,0083 | 0,8 |
| 9 | 842 | 0,1760 | 0,1876 | -0,0117 | -0,9 |
| 10 | 843 | 0,4037 | 0,4282 | -0,0246 | -1,4 |

### Curva di calibrazione — StatsBomb

| Gruppo | Tiri | xG previsto | Gol osservati | Scarto | In errori standard |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 843 | 0,0088 | 0,0261 | -0,0173 | -3,2 |
| 2 | 842 | 0,0192 | 0,0119 | 0,0073 | 2,0 |
| 3 | 843 | 0,0270 | 0,0166 | 0,0104 | 2,4 |
| 4 | 842 | 0,0352 | 0,0309 | 0,0043 | 0,7 |
| 5 | 843 | 0,0450 | 0,0332 | 0,0118 | 1,9 |
| 6 | 842 | 0,0573 | 0,0451 | 0,0121 | 1,7 |
| 7 | 842 | 0,0738 | 0,0831 | -0,0093 | -1,0 |
| 8 | 843 | 0,1007 | 0,0807 | 0,0200 | 2,1 |
| 9 | 842 | 0,1627 | 0,1995 | -0,0368 | -2,7 |
| 10 | 843 | 0,4091 | 0,4389 | -0,0298 | -1,7 |
