"""Le graduatorie dei giocatori (M6-T5).

Il test che conta di piu' in questo file non guarda il codice: confronta i
capocannonieri calcolati dal magazzino con quelli veri del 2015/16. Chi ha
vinto la classifica marcatori in Liga non e' una questione di implementazione,
e un errore nella catena — dal download alla trasformazione all'aggregazione —
si vedrebbe li' e da nessun'altra parte.
"""

from __future__ import annotations

import pandas as pd
import pytest

from football_analytics import giocatori
from football_analytics.config import DATA_PROCESSED, SOGLIA_MINUTI

senza_magazzino = pytest.mark.skipif(
    not (DATA_PROCESSED / "player_stats.parquet").exists(),
    reason="il magazzino non e' costruito; i Parquet entrano in git a M7-T1",
)


def finti() -> pd.DataFrame:
    """Una manciata di giocatori, con la soglia gia' decisa.

    Returns:
        La tabella di prova.
    """
    return pd.DataFrame(
        [
            {
                "giocatore": "Punta Titolare",
                "squadra": "Alfa",
                "ruolo": "Center Forward",
                "minuti": 2000,
                "partite": 30,
                "tiri": 80,
                "gol": 20,
                "xg": 14.0,
                "gol_meno_xg": 6.0,
                "gol_90": 0.9,
                "xg_90": 0.63,
                "sopra_soglia": True,
            },
            {
                "giocatore": "Punta Riserva",
                "squadra": "Beta",
                "ruolo": "Center Forward",
                "minuti": 90,
                "partite": 3,
                "tiri": 4,
                "gol": 3,
                "xg": 0.6,
                "gol_meno_xg": 2.4,
                "gol_90": 3.0,
                "xg_90": 0.6,
                "sopra_soglia": False,
            },
            {
                "giocatore": "Mediano Solido",
                "squadra": "Alfa",
                "ruolo": "Center Defensive Midfield",
                "minuti": 2500,
                "partite": 32,
                "tiri": 30,
                "gol": 3,
                "xg": 5.5,
                "gol_meno_xg": -2.5,
                "gol_90": 0.11,
                "xg_90": 0.2,
                "sopra_soglia": True,
            },
            {
                "giocatore": "Terzino Corsaro",
                "squadra": "Beta",
                "ruolo": "Left Wing Back",
                "minuti": 2400,
                "partite": 30,
                "tiri": 12,
                "gol": 1,
                "xg": 1.2,
                "gol_meno_xg": -0.2,
                "gol_90": 0.04,
                "xg_90": 0.05,
                "sopra_soglia": True,
            },
        ]
    )


def test_la_riserva_prolifica_resta_fuori_dalle_graduatorie() -> None:
    """E' il motivo per cui la soglia esiste.

    «Punta Riserva» ha 3,00 gol per novanta minuti contro gli 0,90 del
    titolare: senza soglia guiderebbe qualunque classifica per novanta, e la
    vista sarebbe una lista di chi ha giocato poco e segnato una volta.
    """
    tavola = finti()

    per_novanta = giocatori.graduatoria(tavola, "gol_90", 5)

    assert "Punta Riserva" not in set(per_novanta["giocatore"])
    assert next(iter(per_novanta["giocatore"])) == "Punta Titolare"


def test_i_totali_contano_anche_chi_sta_sotto_la_soglia() -> None:
    """I gol di chi ha giocato poco sono comunque gol della competizione.

    Se i totali escludessero i non qualificati, il numero mostrato qui non
    tornerebbe con quello della Home, che li conta tutti — e due schermate
    della stessa app direbbero due verita' diverse sullo stesso campionato.
    """
    totali = giocatori.numeri(finti())

    assert totali["gol"] == 27.0
    assert totali["giocatori"] == 4.0
    assert totali["qualificati"] == 3.0


def test_le_ali_stanno_in_attacco_e_i_wing_back_in_difesa() -> None:
    """Il raggruppamento e' una scelta, quindi va fissata.

    Sono i due casi in cui una lettura diversa sarebbe difendibile, ed e' per
    questo che vanno scritti: se qualcuno li spostasse, le quote di gol per
    reparto cambierebbero senza che nessun numero sembri sbagliato.
    """
    assert giocatori.reparto("Left Wing") == "Attacco"
    assert giocatori.reparto("Right Wing") == "Attacco"
    assert giocatori.reparto("Left Wing Back") == "Difesa"
    assert giocatori.reparto("Center Attacking Midfield") == "Centrocampo"
    assert giocatori.reparto("Center Defensive Midfield") == "Centrocampo"


def test_le_quote_per_reparto_sommano_a_uno() -> None:
    """Una quota che non chiude e' una quota sbagliata."""
    riassunto = giocatori.per_reparto(finti())

    assert riassunto["quota_gol"].sum() == pytest.approx(1.0)
    assert list(riassunto["reparto"]) == ["Difesa", "Centrocampo", "Attacco"]


def test_la_graduatoria_al_contrario_parte_dal_peggiore() -> None:
    """Serve alla vista «gol sotto le attese», che senza questo mostrerebbe i migliori."""
    peggiori = giocatori.graduatoria(finti(), "gol_meno_xg", 2, crescente=True)

    assert list(peggiori["giocatore"]) == ["Mediano Solido", "Terzino Corsaro"]


def test_una_colonna_che_non_esiste_non_fa_esplodere_la_pagina() -> None:
    """Una vista in piu' che chiede una metrica sbagliata deve restare vuota, non rompersi."""
    assert giocatori.graduatoria(finti(), "assist", 5).empty
    assert giocatori.graduatoria(pd.DataFrame(columns=["gol"]), "gol", 5).empty
    assert giocatori.per_reparto(pd.DataFrame()).empty
    assert giocatori.scheda(finti(), "Chi Non Esiste") == {}


@senza_magazzino
def test_ogni_posizione_del_magazzino_ha_un_reparto() -> None:
    """Se StatsBomb aggiungesse una posizione, deve dirlo un test.

    Senza questo controllo una posizione nuova finirebbe in ``Altro``, che nel
    filtro non compare: quei giocatori sparirebbero dalle viste per reparto
    senza che nulla sembri rotto.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")

    ignote = set(tabella["ruolo"].astype(str)) - set(giocatori.DA_POSIZIONE)

    assert ignote == set(), f"posizioni senza reparto: {sorted(ignote)}"


@senza_magazzino
@pytest.mark.parametrize(
    ("chiave", "cognome", "gol"),
    [
        ("la_liga_2015_16", "Suárez", 40),
        ("premier_2015_16", "Kane", 25),
        ("serie_a_2015_16", "Higuaín", 36),
    ],
)
def test_i_capocannonieri_sono_quelli_veri(chiave: str, cognome: str, gol: int) -> None:
    """Il controllo contro la realta', non contro un'altra funzione del progetto.

    La Ligue 1 non e' in elenco apposta: Ibrahimović risulta a 36 invece di 38
    perche' all'Open Data mancano tre partite di quel campionato, la stessa
    lacuna che la vista Squadre dichiara. Metterlo qui vorrebbe dire scrivere
    un numero sbagliato in un test e chiamarlo atteso.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")
    competizione = tabella[tabella["competizione"] == chiave]

    primo = giocatori.graduatoria(competizione, "gol", 1).iloc[0]

    assert cognome in str(primo["giocatore"]), primo["giocatore"]
    assert int(primo["gol"]) == gol


@senza_magazzino
def test_la_soglia_e_quella_dichiarata_e_non_una_copia() -> None:
    """La colonna del magazzino e il confronto sui minuti devono dire lo stesso.

    Se qualcuno riscrivesse la soglia dentro questo modulo, i due numeri
    divergerebbero al primo ritocco e la pagina mostrerebbe una selezione che
    non corrisponde a cio' che la didascalia promette.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")

    dalla_colonna = giocatori.qualificati(tabella)
    dai_minuti = tabella[tabella["minuti"] >= SOGLIA_MINUTI]

    assert len(dalla_colonna) == len(dai_minuti)


@senza_magazzino
def test_nelle_finali_nessuno_raggiunge_la_soglia() -> None:
    """Il caso che rende la soglia fissa scomoda, e che la pagina deve dichiarare.

    Le finali di Champions sono diciassette partite sparse su cinquant'anni: il
    massimo giocato da un singolo e' 432 minuti, quindi la soglia dei 500 non la
    supera nessuno. Non e' un difetto da nascondere abbassando il limite solo
    li' — sarebbero due regole diverse a seconda della vista — ma un fatto che
    la vista deve spiegare, e questo test lo tiene misurato.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")
    finali = tabella[tabella["competizione"] == "champions_finali"]

    assert giocatori.qualificati(finali).empty
    assert int(finali["minuti"].max()) < SOGLIA_MINUTI


def trasferito() -> pd.DataFrame:
    """Lo stesso giocatore in due squadre, come sta nel magazzino.

    Returns:
        Due righe con lo stesso ``giocatore_id``.
    """
    return pd.DataFrame(
        [
            {
                "giocatore_id": 7000,
                "giocatore": "Eder Citadin Martins",
                "giocatore_breve": "Éder",
                "squadra": "Sampdoria",
                "ruolo": "Center Forward",
                "partite": 19,
                "minuti": 1700,
                "tiri": 60,
                "gol": 12,
                "xg": 7.6,
                "gol_meno_xg": 4.4,
            },
            {
                "giocatore_id": 7000,
                "giocatore": "Eder Citadin Martins",
                "giocatore_breve": "Éder",
                "squadra": "Inter Milan",
                "ruolo": "Center Forward",
                "partite": 14,
                "minuti": 787,
                "tiri": 20,
                "gol": 1,
                "xg": 2.1,
                "gol_meno_xg": -1.1,
            },
        ]
    )


def test_chi_cambia_squadra_conta_una_volta_sola() -> None:
    """Il difetto che rendeva quasi giusta la classifica marcatori.

    Nel magazzino la chiave e' (competizione, giocatore, squadra), che per la
    scheda di una squadra e' corretto. Per una classifica di competizione no:
    senza la somma, Éder nel 2015/16 risulterebbe a 12 gol invece di 13, e il
    numero non sembrerebbe sbagliato a nessuno.
    """
    unito = giocatori.per_giocatore(trasferito())

    assert len(unito) == 1
    riga = unito.iloc[0]
    assert riga["gol"] == 13
    assert riga["minuti"] == 2487
    assert riga["partite"] == 33


def test_le_due_squadre_restano_scritte() -> None:
    """Nasconderne una renderebbe la riga incomprensibile a chi ricorda la stagione."""
    unito = giocatori.per_giocatore(trasferito())

    assert unito.iloc[0]["squadra"] == "Sampdoria, Inter Milan"


def test_i_valori_per_novanta_si_ricalcolano_sui_minuti_totali() -> None:
    """Il valore per novanta di una somma non e' la somma dei valori per novanta.

    Sommare 0,64 e 0,11 darebbe 0,75 gol/90, che e' assurdo per un giocatore
    da 13 gol in 2.487 minuti. Il conto giusto e' 13 / 2.487 x 90 = 0,47.
    """
    unito = giocatori.per_giocatore(trasferito())

    assert unito.iloc[0]["gol_90"] == pytest.approx(13 / 2487 * 90, rel=1e-6)


def test_la_soglia_si_applica_ai_minuti_sommati() -> None:
    """Due spezzoni sotto soglia che insieme la superano devono qualificare.

    E' il caso opposto e altrettanto silenzioso: chi ha giocato 300 minuti in
    una squadra e 300 nell'altra ha giocato 600 minuti, e per la stagione e'
    un giocatore qualificato.
    """
    meta = SOGLIA_MINUTI // 2 + 50
    mezzi = trasferito()
    mezzi["minuti"] = [meta, meta]

    unito = giocatori.per_giocatore(mezzi)

    assert int(unito.iloc[0]["minuti"]) >= SOGLIA_MINUTI
    assert bool(unito.iloc[0]["sopra_soglia"])
    assert not giocatori.qualificati(unito).empty


@senza_magazzino
def test_le_graduatorie_usano_i_nomi_con_cui_i_giocatori_sono_noti() -> None:
    """«Aveiro» e «Cuccittini» sono i cognomi anagrafici di Ronaldo e Messi.

    Prendere l'ultima parola del nome completo sembrava ragionevole e produceva
    un tabellone illeggibile. Il magazzino ha gia' la colonna giusta.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")
    liga = giocatori.per_giocatore(tabella[tabella["competizione"] == "la_liga_2015_16"])

    primi = list(giocatori.graduatoria(liga, "gol", 5)["giocatore_breve"])

    assert primi == [
        "Luis Suárez",
        "Cristiano Ronaldo",
        "Lionel Messi",
        "Neymar",
        "Karim Benzema",
    ]


@senza_magazzino
def test_la_somma_per_giocatore_non_perde_ne_inventa_gol() -> None:
    """Il totale della competizione deve restare identico dopo l'aggregazione.

    E' il controllo che accorgerebbe di un ``groupby`` su una chiave sbagliata:
    raggruppare per nome invece che per identificativo unirebbe due omonimi, e
    il totale non se ne accorgerebbe — ma il conteggio dei giocatori si'.
    """
    tabella = pd.read_parquet(DATA_PROCESSED / "player_stats.parquet")
    serie_a = tabella[tabella["competizione"] == "serie_a_2015_16"]

    unito = giocatori.per_giocatore(serie_a)

    assert unito["gol"].sum() == serie_a["gol"].sum()
    assert unito["minuti"].sum() == serie_a["minuti"].sum()
    assert len(unito) == serie_a["giocatore_id"].nunique()


def reparto_finto(quanti: int, reparto_ruolo: str, *, gol_extra: int = 0) -> pd.DataFrame:
    """Un reparto popolato quanto basta a calcolare percentili.

    Args:
        quanti: Quanti giocatori generare.
        reparto_ruolo: La posizione StatsBomb da assegnare a tutti.
        gol_extra: Gol in piu' dati all'ultimo, per creare un fuoriclasse.

    Returns:
        La tabella di prova.
    """
    righe = []
    for i in range(quanti):
        gol = i + (gol_extra if i == quanti - 1 else 0)
        righe.append(
            {
                "giocatore_id": 1000 + i,
                "giocatore": f"Tale {i}",
                "giocatore_breve": f"Tale {i}",
                "squadra": "Alfa",
                "ruolo": reparto_ruolo,
                "partite": 30,
                "minuti": 2700,
                "tiri": 20 + i,
                "gol": gol,
                "xg": 5.0 + i * 0.1,
                "gol_meno_xg": gol - (5.0 + i * 0.1),
                "tiri_90": (20 + i) / 30,
                "gol_90": gol / 30,
                "xg_90": (5.0 + i * 0.1) / 30,
                "sopra_soglia": True,
            }
        )
    return pd.DataFrame(righe)


def test_il_percentile_confronta_dentro_il_reparto() -> None:
    """Un attaccante misurato contro i portieri risulta fenomenale su tutto.

    E' il difetto che il criterio di M6-T6 esiste per impedire: il radar deve
    dire «meglio dell'85 % degli attaccanti», non «meglio dell'85 % di chiunque
    giochi a calcio».
    """
    attacco = reparto_finto(25, "Center Forward")
    difesa = reparto_finto(25, "Left Back")
    difesa["giocatore_id"] += 100
    difesa["gol"] = 0
    difesa["gol_90"] = 0.0
    insieme = pd.concat([attacco, difesa], ignore_index=True)

    ultimo_attaccante = int(attacco.iloc[-1]["giocatore_id"])
    posizioni = giocatori.percentili(insieme, ultimo_attaccante)

    # Il confronto e' sui 25 attaccanti, non sui 50 giocatori.
    assert posizioni["confronto"] == 25.0
    assert posizioni["gol_90"] > 90


def test_il_percentile_di_chi_sta_in_mezzo_e_cinquanta() -> None:
    """Chi vale quanto la mediana deve stare a 50, non a 0 o a 100.

    Contare solo i valori strettamente minori manderebbe al percentile zero
    tutti i difensori con zero gol, che sono la maggioranza del reparto: la
    meta' dei pari conta meta'.
    """
    pari = reparto_finto(24, "Left Back")
    pari["gol"] = 0
    pari["gol_90"] = 0.0

    posizioni = giocatori.percentili(pari, 1000)

    assert posizioni["gol_90"] == pytest.approx(50.0)


def test_senza_abbastanza_pari_il_radar_non_si_disegna() -> None:
    """Un percentile su quattro persone e' una posizione in una fila corta.

    «Meglio del 66 %» su quattro giocatori vuol dire «terzo su quattro», che e'
    un'informazione diversa e molto piu' debole. Meglio non disegnare niente
    che disegnare un radar che sembra dire qualcosa.
    """
    pochi = reparto_finto(giocatori.MINIMO_CONFRONTO - 1, "Center Forward")

    assert giocatori.percentili(pochi, 1000) == {}


def test_chi_non_ha_tirato_non_ha_un_xg_per_tiro_indefinito() -> None:
    """Zero e non ``NaN``: sul radar un buco e un valore basso si leggono uguali."""
    senza_tiri = reparto_finto(21, "Goalkeeper")
    senza_tiri["tiri"] = 0
    senza_tiri["xg"] = 0.0

    completa = giocatori.con_xg_per_tiro(senza_tiri)

    assert completa["xg_per_tiro"].notna().all()
    assert (completa["xg_per_tiro"] == 0.0).all()


def test_l_andamento_cumula_e_salta_i_rigori_dei_tiebreak() -> None:
    """La cumulata di un giocatore e' per partita, e i tiebreak non sono partita."""
    tiri = pd.DataFrame(
        [
            {
                "match_id": 1,
                "giocatore_id": 7,
                "gol": True,
                "xg_statsbomb": 0.4,
                "rigori_finali": False,
            },
            {
                "match_id": 2,
                "giocatore_id": 7,
                "gol": False,
                "xg_statsbomb": 0.2,
                "rigori_finali": False,
            },
            {
                "match_id": 3,
                "giocatore_id": 7,
                "gol": True,
                "xg_statsbomb": 0.76,
                "rigori_finali": True,
            },
            {
                "match_id": 1,
                "giocatore_id": 9,
                "gol": True,
                "xg_statsbomb": 0.9,
                "rigori_finali": False,
            },
        ]
    )

    curva = giocatori.andamento(tiri, 7)

    assert len(curva) == 2
    assert list(curva["gol"]) == [1, 1]
    assert curva.iloc[-1]["xg"] == pytest.approx(0.6)
