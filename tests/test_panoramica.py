"""Verifiche delle aggregazioni della Panoramica (M6-T3).

Il criterio del backlog e' che **i numeri coincidano con quelli calcolati a
mano su dieci partite**. Qui «a mano» significa: ricalcolati con un secondo
metodo, elementare e volutamente lento, che non condivide nemmeno una riga di
codice con quello sotto esame. Se i due concordano su dieci partite scelte a
caso, l'aggregazione fa quello che dice.

Un test che riusasse le stesse funzioni verificherebbe solo che il codice sia
d'accordo con se stesso.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from football_analytics import panoramica
from football_analytics.config import SOGLIA_MINUTI

if TYPE_CHECKING:
    from collections.abc import Sequence

#: Dieci partite inventate, con numeri scelti perche' si sommino a mente.
PARTITE: list[dict[str, object]] = [
    {"match_id": i, "casa": f"Casa {i}", "ospite": f"Ospite {i}", "data": f"2016-01-{i + 1:02d}"}
    for i in range(10)
]


def partite_finte() -> pd.DataFrame:
    """Dieci partite con risultati e xG noti.

    I gol in casa vanno da 0 a 9, quelli fuori sono sempre 1: il totale fa
    45 + 10 = **55**, un numero che si controlla senza calcolatrice.

    Returns:
        La tabella delle partite.
    """
    righe = []
    for i, base in enumerate(PARTITE):
        righe.append(
            {
                **base,
                "gol_casa": i,
                "gol_ospite": 1,
                "xg_casa": 1.5,
                "xg_ospite": 0.5,
            }
        )
    return pd.DataFrame(righe)


def tiri_finti() -> pd.DataFrame:
    """I tiri delle dieci partite, coerenti con i loro risultati.

    Ogni partita ha ``i`` tiri della squadra di casa che finiscono in gol e due
    dell'ospite di cui uno solo entra: i totali si ricavano a mente e non da
    un'esecuzione del codice.

    Returns:
        La tabella dei tiri.
    """
    righe = []
    for i, base in enumerate(PARTITE):
        for _ in range(i):
            righe.append(
                {
                    "match_id": base["match_id"],
                    "squadra": base["casa"],
                    "gol": True,
                    "xg_statsbomb": 0.5,
                }
            )
        for k in range(2):
            righe.append(
                {
                    "match_id": base["match_id"],
                    "squadra": base["ospite"],
                    "gol": k == 0,
                    "xg_statsbomb": 0.25,
                }
            )
    return pd.DataFrame(righe)


# ---------------------------------------------------------------------------
# I KPI, contro un conteggio elementare
# ---------------------------------------------------------------------------


def test_i_gol_totali_sono_quelli_delle_dieci_partite() -> None:
    # 0+1+2+...+9 in casa fa 45, piu' un gol per ospite fa 55.
    risultato = panoramica.kpi(tiri_finti(), partite_finte())

    assert risultato["gol"] == 55.0
    assert risultato["partite"] == 10.0


def test_i_kpi_coincidono_con_il_conteggio_riga_per_riga() -> None:
    """Il criterio del backlog, verificato con un secondo metodo.

    Il conteggio di controllo scorre le righe una per una con Python puro:
    lento, banale, e senza una riga in comune con le aggregazioni di pandas
    che sta verificando.
    """
    tiri, partite = tiri_finti(), partite_finte()

    gol_a_mano = 0
    for riga in partite.to_dict("records"):
        gol_a_mano += int(riga["gol_casa"]) + int(riga["gol_ospite"])
    xg_a_mano = 0.0
    tiri_a_mano = 0
    for riga in tiri.to_dict("records"):
        xg_a_mano += float(riga["xg_statsbomb"])
        tiri_a_mano += 1

    risultato = panoramica.kpi(tiri, partite)

    assert risultato["gol"] == pytest.approx(gol_a_mano)
    assert risultato["xg"] == pytest.approx(xg_a_mano)
    assert risultato["tiri"] == pytest.approx(tiri_a_mano)
    assert risultato["gol_per_partita"] == pytest.approx(gol_a_mano / len(partite))
    assert risultato["conversione"] == pytest.approx(gol_a_mano / tiri_a_mano)


def test_una_selezione_vuota_non_produce_nan() -> None:
    # Una dashboard non deve mostrare «nan» a chi filtra troppo: e' il momento
    # in cui l'utente pensa che l'app sia rotta.
    vuoti = tiri_finti().iloc[0:0]
    nessuna = partite_finte().iloc[0:0]

    risultato = panoramica.kpi(vuoti, nessuna)

    assert all(valore == 0.0 for valore in risultato.values())


def test_i_gol_dei_kpi_comprendono_gli_autogol() -> None:
    """La ragione per cui i gol si contano dalle partite e non dai tiri.

    Un autogol entra nel risultato ma non nei tiri della squadra che ne
    beneficia. Contandoli dai tiri il totale sarebbe piu' basso del risultato
    reale, e nessuno se ne accorgerebbe guardando la dashboard.
    """
    partite = partite_finte()
    tiri = tiri_finti()

    dai_kpi = panoramica.kpi(tiri, partite)["gol"]
    dai_tiri = float(tiri["gol"].sum())

    # Nei dati finti ogni gol nasce da un tiro, quindi i due coincidono: il
    # test serve a fissare la relazione, non a trovare una differenza.
    assert dai_kpi == pytest.approx(dai_tiri)

    # Con un autogol la relazione si rompe, ed e' esattamente il caso che il
    # conteggio dai tiri sbaglierebbe. La modifica passa per numpy perche'
    # `.loc[riga, colonna]` non e' tipizzabile con pandas-stubs.
    con_autogol = partite.copy()
    aumentati = con_autogol["gol_casa"].to_numpy().copy()
    aumentati[0] += 1
    con_autogol["gol_casa"] = aumentati

    assert panoramica.kpi(tiri, con_autogol)["gol"] == pytest.approx(dai_tiri + 1)


# ---------------------------------------------------------------------------
# Due totali di gol, e il difetto nato dall'averne uno solo (M7-T3)
# ---------------------------------------------------------------------------


def test_un_autogol_entra_nei_gol_ma_non_nella_conversione() -> None:
    """La correzione di M7-T3, sul caso minimo che la rende necessaria.

    ``gol`` risponde a «quanti gol si sono visti» e l'autogol ci sta dentro.
    ``conversione`` risponde a «quanti tiri finiscono in gol», e l'autogol non
    e' un tiro di quella squadra: al numeratore va ``gol_da_tiro``.

    Prima di M7-T3 la conversione usava il primo dei due, e su tutte le
    competizioni dichiarava 10,5 % invece di 10,2 %.
    """
    partite = partite_finte()
    tiri = tiri_finti()
    dai_tiri = float(tiri["gol"].sum())

    con_autogol = partite.copy()
    aumentati = con_autogol["gol_casa"].to_numpy().copy()
    aumentati[0] += 1
    con_autogol["gol_casa"] = aumentati

    numeri = panoramica.kpi(tiri, con_autogol)

    assert numeri["gol"] == pytest.approx(dai_tiri + 1), "l'autogol deve contare fra i gol"
    assert numeri["gol_da_tiro"] == pytest.approx(dai_tiri), "ma non fra i gol dei tiri"
    assert numeri["conversione"] == pytest.approx(dai_tiri / numeri["tiri"])


def test_la_ciambella_e_la_sua_didascalia_escono_dallo_stesso_numeratore() -> None:
    """L'invariante che mancava, e il motivo per cui il difetto si e' visto.

    La vista disegna la percentuale con :func:`panoramica.realizzazione` e le
    scrive sotto «N gol / M xG» prendendo N da :func:`panoramica.kpi`. Finche'
    nessuno pretende che N diviso M faccia la percentuale, le due possono
    divergere senza che nulla protesti — ed e' successo: 102,7 % con sotto
    «4.601 gol / 4.328 xG», che fa 106,3 %.

    Il difetto e' stato trovato **guardando una schermata**, non eseguendo un
    test. Questo test esiste perche' non serva piu' guardare.
    """
    partite = partite_finte()
    tiri = tiri_finti()

    con_autogol = partite.copy()
    aumentati = con_autogol["gol_casa"].to_numpy().copy()
    aumentati[0] += 1
    con_autogol["gol_casa"] = aumentati

    numeri = panoramica.kpi(tiri, con_autogol)
    quota = panoramica.realizzazione(tiri)

    assert numeri["gol_da_tiro"] / numeri["xg"] == pytest.approx(quota), (
        "la didascalia della ciambella non ricostruisce la percentuale che le sta sopra"
    )


def test_lo_scarto_dai_kpi_confronta_due_grandezze_omogenee() -> None:
    """``gol_meno_xg`` sottrae dall'xG dei tiri i gol degli stessi tiri.

    L'xG esiste solo per i tiri: un autogol non ne ha, quindi metterlo al
    minuendo produce uno scarto positivo che nessuna occasione ha generato.
    Sui dati veri valeva 156 gol di troppo, e la frase calcolata della Home lo
    raccontava come se le squadre avessero segnato piu' del previsto.
    """
    partite = partite_finte()
    tiri = tiri_finti()

    con_autogol = partite.copy()
    aumentati = con_autogol["gol_casa"].to_numpy().copy()
    aumentati[0] += 1
    con_autogol["gol_casa"] = aumentati

    numeri = panoramica.kpi(tiri, con_autogol)

    assert numeri["gol_meno_xg"] == pytest.approx(numeri["gol_da_tiro"] - numeri["xg"])
    assert numeri["gol_meno_xg"] != pytest.approx(numeri["gol"] - numeri["xg"])


# ---------------------------------------------------------------------------
# I rigori della serie finale, il difetto trovato sui dati veri
# ---------------------------------------------------------------------------


def test_i_rigori_della_serie_finale_non_contano_come_gol() -> None:
    """Il difetto che il campione sintetico non poteva mostrare.

    Su dieci partite vere ne sono comparsi diciannove, e contarli gonfiava i
    gol da 33 a 48. Hanno ``gol = True`` ma non entrano nel risultato: si
    giocano dopo che la partita e' finita.
    """
    tiri = tiri_finti()
    tiri["rigori_finali"] = False
    serie = pd.DataFrame(
        [
            {
                "match_id": 0,
                "squadra": "Casa 0",
                "gol": True,
                "xg_statsbomb": 0.78,
                "rigori_finali": True,
            }
            for _ in range(5)
        ]
    )
    con_serie = pd.concat([tiri, serie], ignore_index=True)

    assert len(panoramica.tiri_di_gioco(con_serie)) == len(tiri)
    assert panoramica.kpi(con_serie, partite_finte()) == panoramica.kpi(tiri, partite_finte())
    assert panoramica.per_squadra(con_serie).equals(panoramica.per_squadra(tiri))


def test_senza_la_colonna_il_filtro_non_rompe() -> None:
    # Le tabelle dei test e quelle di viste future potrebbero non averla: e'
    # meglio passare oltre che far fallire una vista intera.
    assert len(panoramica.tiri_di_gioco(tiri_finti())) == len(tiri_finti())


@pytest.mark.skipif(
    not (Path("data/processed/shots.parquet").exists()),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)
def test_su_dieci_partite_vere_i_conti_tornano() -> None:
    """Il criterio del backlog, sui dati veri invece che su un campione finto.

    L'identita' verificata e':

        gol dai tiri giocati + autogol = gol del risultato

    E' la relazione che il difetto dei rigori finali violava, e che nessuna
    metrica riassuntiva avrebbe segnalato.
    """
    tiri = pd.read_parquet("data/processed/shots.parquet")
    partite = pd.read_parquet("data/processed/matches.parquet")
    dieci = partite.sort_values("match_id").head(10)
    suoi = tiri[tiri["match_id"].isin(set(dieci["match_id"]))]

    risultato = panoramica.kpi(suoi, dieci)
    dai_tiri = int(panoramica.tiri_di_gioco(suoi)["gol"].sum())
    autogol = int(dieci["autogol_casa"].sum() + dieci["autogol_ospite"].sum())

    assert dai_tiri + autogol == int(risultato["gol"])
    assert risultato["tiri"] == len(panoramica.tiri_di_gioco(suoi))
    assert risultato["xg"] == pytest.approx(
        float(panoramica.tiri_di_gioco(suoi)["xg_statsbomb"].sum())
    )


# ---------------------------------------------------------------------------
# Le squadre
# ---------------------------------------------------------------------------


def test_ogni_squadra_compare_una_volta_sola() -> None:
    tabella = panoramica.per_squadra(tiri_finti())

    assert tabella["squadra"].is_unique
    assert len(tabella) == 19  # nove squadre di casa con tiri, piu' dieci ospiti


def test_i_totali_per_squadra_sommano_a_quelli_generali() -> None:
    # Se una riga finisse in due gruppi, o nessuno, la somma non tornerebbe.
    tiri = tiri_finti()

    tabella = panoramica.per_squadra(tiri)

    assert tabella["tiri"].sum() == len(tiri)
    assert tabella["xg"].sum() == pytest.approx(tiri["xg_statsbomb"].sum())
    assert tabella["gol"].sum() == tiri["gol"].sum()


def test_le_squadre_sono_ordinate_per_xg() -> None:
    valori = panoramica.per_squadra(tiri_finti())["xg"].to_numpy()

    assert list(valori) == sorted(valori, reverse=True)


def test_si_possono_chiedere_solo_le_prime() -> None:
    assert len(panoramica.per_squadra(tiri_finti(), quante=5)) == 5


def test_nessun_tiro_nessuna_squadra() -> None:
    vuota = panoramica.per_squadra(tiri_finti().iloc[0:0])

    assert vuota.empty
    assert "squadra" in vuota.columns


# ---------------------------------------------------------------------------
# La classifica dei giocatori, e la soglia dei minuti
# ---------------------------------------------------------------------------


def giocatori_finti() -> pd.DataFrame:
    """Tre giocatori, di cui uno entrato pochi minuti.

    Returns:
        Una tabella nella forma di ``player_stats``.
    """
    return pd.DataFrame(
        [
            {"giocatore": "Regolare", "minuti": 2000, "gol": 12, "xg": 10.0},
            {"giocatore": "Titolare", "minuti": 1500, "gol": 9, "xg": 9.5},
            {"giocatore": "Subentrato", "minuti": 40, "gol": 2, "xg": 0.3},
        ]
    )


def test_chi_sta_sotto_la_soglia_resta_fuori_dalla_classifica() -> None:
    # Senza soglia il miglior marcatore per novanta minuti e' sempre qualcuno
    # entrato al 90esimo: due gol in quaranta minuti fanno 4,5 gol per novanta.
    classifica = panoramica.top_giocatori(giocatori_finti())

    assert "Subentrato" not in set(classifica["giocatore"])
    assert len(classifica) == 2


def test_la_soglia_e_quella_dichiarata_nel_progetto() -> None:
    sotto = giocatori_finti().assign(minuti=SOGLIA_MINUTI - 1)
    esatta = giocatori_finti().assign(minuti=SOGLIA_MINUTI)

    assert panoramica.top_giocatori(sotto).empty
    assert len(panoramica.top_giocatori(esatta)) == 3


def test_la_classifica_e_ordinata_per_gol() -> None:
    valori = panoramica.top_giocatori(giocatori_finti())["gol"].to_numpy()

    assert list(valori) == sorted(valori, reverse=True)


# ---------------------------------------------------------------------------
# L'andamento
# ---------------------------------------------------------------------------


def test_l_andamento_ha_una_riga_per_data() -> None:
    curva = panoramica.andamento(partite_finte())

    assert len(curva) == 10
    assert curva["data"].is_unique


def test_l_andamento_e_ordinato_nel_tempo() -> None:
    date = list(panoramica.andamento(partite_finte())["data"])

    assert date == sorted(date)


def test_l_andamento_somma_le_partite_dello_stesso_giorno() -> None:
    partite = partite_finte()
    partite.loc[1, "data"] = partite.loc[0, "data"]

    curva = panoramica.andamento(partite)

    assert len(curva) == 9
    assert curva["gol"].sum() == float(partite["gol_casa"].sum() + partite["gol_ospite"].sum())


@pytest.mark.parametrize("colonne", [("gol",), ("xg",), ("gol", "xg")])
def test_si_possono_chiedere_solo_alcune_serie(colonne: Sequence[str]) -> None:
    curva = panoramica.andamento(partite_finte(), colonne)

    assert set(curva.columns) == {"data", *colonne}


def test_una_tabella_vuota_e_senza_tipi_conserva_le_colonne() -> None:
    """Una trappola di pandas che produce un errore lontano dalla causa.

    Se ``rigori_finali`` ha tipo ``object`` — cosa che accade costruendo una
    tabella vuota senza dichiarare i tipi — allora ``~colonna`` non e' una
    maschera booleana, e ``tabella[serie]`` viene letto come **selezione di
    colonne per nome** invece che come filtro di righe. Il risultato e' una
    tabella senza colonne, e l'errore esplode molto dopo, quando qualcuno
    cerca ``xg_statsbomb`` e non la trova piu'.

    **C'era gia' un test sulla selezione vuota e non l'aveva preso**, perche'
    costruisce il vuoto con ``.iloc[0:0]`` su una tabella tipizzata: cosi' i
    tipi sopravvivono e il caso non si presenta. La differenza e' fra «vuota» e
    «vuota e senza tipi», e il difetto viveva esattamente li' in mezzo. Il
    fallimento e' arrivato dai test delle frasi calcolate di M6-T12.
    """
    colonne = ["competizione", "xg_statsbomb", "gol", "x", "minuto", "rigori_finali"]
    vuoti = pd.DataFrame(columns=colonne)
    nessuna = pd.DataFrame(columns=["gol_casa", "gol_ospite"])

    giocati = panoramica.tiri_di_gioco(vuoti)

    assert list(giocati.columns) == colonne, "il filtro ha perso le colonne"
    assert giocati.empty
    assert all(valore == 0.0 for valore in panoramica.kpi(vuoti, nessuna).values())
