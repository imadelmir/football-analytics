"""Verifiche dell'identita' visiva delle squadre (M6-T3).

Il colore non e' una scelta estetica ma un calcolo, quindi si verifica come un
calcolo: deve essere **stabile**, **distinguibile** e **leggibile**. L'ultima
proprieta' e' quella che si dimentica sempre, ed e' l'unica che rende una
dashboard inutilizzabile per qualcuno.
"""

from __future__ import annotations

import re

import pytest

from football_analytics import squadre


def contrasto_col_bianco(colore: str) -> float:
    """Rapporto di contrasto fra un colore e il bianco, secondo WCAG.

    Args:
        colore: Il colore in forma ``#rrggbb``.

    Returns:
        Il rapporto, fra 1 e 21.
    """
    canali = [int(colore[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineari = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canali]
    luminanza = 0.2126 * lineari[0] + 0.7152 * lineari[1] + 0.0722 * lineari[2]
    return 1.05 / (luminanza + 0.05)


# ---------------------------------------------------------------------------
# Le sigle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "atteso"),
    [
        ("Paris Saint-Germain", "PSG"),
        ("Olympique de Marseille", "OM"),
        ("AS Monaco", "ASM"),
        ("OGC Nice", "OGCN"),
        ("Stade Rennais FC", "SRFC"),
        ("Lyon", "LYO"),
        ("Angers", "ANG"),
        ("Real Madrid", "RM"),
    ],
)
def test_le_sigle_sono_quelle_riconoscibili(nome: str, atteso: str) -> None:
    assert squadre.sigla(nome) == atteso


def test_le_parole_brevi_restano_intere() -> None:
    # Sono quasi sempre gia' acronimi: senza questa regola meta' delle squadre
    # francesi e italiane perderebbe la parte riconoscibile del nome.
    assert squadre.sigla("AS Roma") == "ASR"
    assert squadre.sigla("FC Barcelona") == "FCB"


def test_le_congiunzioni_non_entrano_nella_sigla() -> None:
    assert squadre.sigla("Olympique de Marseille") == "OM"
    assert squadre.sigla("Deportivo de La Coruña") == "DC"


def test_gli_accenti_non_cambiano_la_sigla() -> None:
    assert squadre.sigla("Gazélec Ajaccio") == squadre.sigla("Gazelec Ajaccio")


def test_una_sigla_non_supera_le_quattro_lettere() -> None:
    lunghissimo = "Associazione Sportiva Dilettantistica Calcio Nuova Squadra"

    assert len(squadre.sigla(lunghissimo)) <= squadre.LETTERE


def test_un_nome_vuoto_non_rompe_la_vista() -> None:
    # Meglio un punto interrogativo che una riga mancante in classifica.
    assert squadre.sigla("") == "?"
    assert squadre.sigla("   ") == "?"


# ---------------------------------------------------------------------------
# I colori
# ---------------------------------------------------------------------------


def test_lo_stesso_nome_da_sempre_lo_stesso_colore() -> None:
    """Il colore non deve cambiare fra un riavvio e l'altro.

    Con ``hash()`` cambierebbe: Python lo randomizza a ogni processo, e la
    dashboard cambierebbe colori a ogni riavvio senza che nessuno capisca
    perche'. Per questo il modulo usa ``sha256``.
    """
    assert squadre.colore("Lyon") == squadre.colore("Lyon")
    assert squadre.colore("Lyon") == "#6f2034"


def test_squadre_diverse_hanno_colori_diversi() -> None:
    nomi = ["Paris Saint-Germain", "Olympique de Marseille", "AS Monaco", "Lyon", "Angers"]

    assert len({squadre.colore(n) for n in nomi}) == len(nomi)


def test_i_colori_sono_esadecimali_validi() -> None:
    for nome in ("Lyon", "Angers", "AS Monaco", ""):
        assert re.fullmatch(r"#[0-9a-f]{6}", squadre.colore(nome))


def test_il_testo_bianco_si_legge_su_qualunque_colore() -> None:
    """La proprieta' che si dimentica sempre, verificata su tutte le tonalita'.

    Non basta provare qualche nome: la tonalita' viene da un'impronta e puo'
    cadere ovunque. Il test copre l'intero cerchio cromatico, che e' l'unico
    modo di sapere che **nessuna** squadra futura prendera' un colore
    illeggibile.

    Con luminosita' 0,32 il caso peggiore era 4,29, sotto la soglia WCAG AA, e
    capitava davvero su una delle 152 squadre del magazzino.
    """
    peggiore = min(contrasto_col_bianco(squadre._da_hsl(i / 360)) for i in range(360))

    assert peggiore >= 4.5


def test_il_colore_non_dipende_da_accenti_o_maiuscole() -> None:
    assert squadre.colore("Gazélec Ajaccio") == squadre.colore("GAZELEC AJACCIO")
