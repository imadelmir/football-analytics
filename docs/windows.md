# Se Windows blocca i comandi

Questa pagina serve a chi sviluppa su Windows e vede i comandi del progetto
fallire senza una ragione apparente. Non riguarda il progetto: riguarda il
modo in cui `uv` genera gli eseguibili e il modo in cui Windows li giudica.

Stava nel README fino a M7-T4. È uscita da lì perché il README ha un compito
diverso — far capire il progetto a chi lo apre per la prima volta — e
quarantasei righe di risoluzione di un problema di una singola piattaforma
erano la parte più lunga di quel documento.

---

## Il sintomo

Su un sistema con **Smart App Control** o una policy WDAC attiva, comandi come
`uv run mypy` o `uv run pytest` falliscono con:

```
Un criterio di controllo dell'applicazione ha bloccato il file
```

## Perché succede

`uv` genera in `.venv\Scripts\` un piccolo eseguibile per ogni comando
dichiarato da un pacchetto — `mypy.exe`, `pytest.exe`, `streamlit.exe` — e
quei binari non sono firmati.

**Vengono rigenerati a ogni `uv sync`**, quindi il blocco può ripresentarsi
anche dopo essere stato aggirato una volta. Non è un problema che si risolve
una volta sola: è un problema che si evita cambiando modo di invocare.

## La regola che li risolve tutti

Invocare il **modulo**, non l'eseguibile:

```powershell
uv run python -m mypy
uv run python -m pytest -m "not rete"
uv run python -m streamlit run app/Panoramica.py
uv run python -m nbconvert --to notebook --execute --inplace notebooks/esplorazione.ipynb
uv run python -m jupyterlab
```

Funziona perché gira `python.exe`, che è una copia del Python ufficiale ed è
firmato. `ruff` invece va sempre: è un unico binario Rust senza librerie da
caricare, e la policy non ha niente da ridire.

## L'eccezione: mypy

`mypy` viene distribuito compilato con mypyc, e quei binari sono bloccati
**anche quando li si importa** — quindi `python -m mypy` da solo non basta.
Serve costruirlo da sorgente, una volta sola:

```powershell
[System.Environment]::SetEnvironmentVariable('UV_NO_BINARY_PACKAGE','mypy','User')
uv sync --all-extras --reinstall-package mypy
```

Da lì in avanti `uv run python -m mypy` funziona come su Linux.

## Scrivere Python nel terminale

Se scrivi del Python direttamente in PowerShell, usa una **here-string**:
PowerShell non interpreta `\"` come escape e manderebbe all'interprete una
stringa mai chiusa.

```powershell
@'
import pandas as pd
print(pd.read_parquet("data/processed/shots.parquet").shape)
'@ | uv run python -
```

---

Su Linux e macOS niente di tutto questo serve: valgono i comandi del
[README](../README.md) così come sono scritti.
