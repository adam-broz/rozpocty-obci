"""Ručně ověřené obce: výstup pipeline musí sedět s hodnotami, které ukazuje
portál Monitor (sekce Přehled → Příjmy/Výdaje konsolidované, skutečnost).
Podrobnosti a datum ověření viz VALIDATION.md.

Testy potřebují vygenerovaná data (`uv run python -m pipeline`); jinak se přeskočí.
"""

import json

import pytest

from pipeline import config as C

OBCE = C.OUTPUT / "obce"

# (kód obce, rok, příjmy v tis. Kč, výdaje v tis. Kč) – opsáno z webu Monitoru
MONITOR = [
    ("554782", 2025, 148_140_568, 123_970_124),  # Hlavní město Praha
    ("533955", 2025, 882_083, 855_502),  # Kutná Hora
    ("533955", 2021, 694_956, 581_885),  # Kutná Hora, starší rok
    ("561771", 2025, 971, 633),  # Vysoká Lhota (okr. Pelhřimov), 16 obyvatel
]

pytestmark = pytest.mark.skipif(not OBCE.exists(), reason="chybí výstup pipeline")


def load(zuj):
    with open(OBCE / f"{zuj}.json", encoding="utf-8") as f:
        return json.load(f)


def year(doc, y):
    return next(x for x in doc["years"] if x["year"] == y)


@pytest.mark.parametrize("zuj, rok, prijmy, vydaje", MONITOR)
def test_totals_match_monitor(zuj, rok, prijmy, vydaje):
    if rok not in processed_years():
        pytest.skip(f"rok {rok} není ve zpracovaném rozsahu")
    y = year(load(zuj), rok)
    assert round(y["income"]["total"] / 1000) == prijmy
    assert round(y["expense"]["total"] / 1000) == vydaje


def processed_years():
    with open(C.OUTPUT / "meta.json", encoding="utf-8") as f:
        return json.load(f)["years"]


@pytest.mark.parametrize("zuj", ["554782", "533955", "561771"])
def test_parts_sum_to_totals(zuj):
    for y in load(zuj)["years"]:
        inc, exp = y["income"], y["expense"]
        assert abs(inc["tax"] + inc["nontax"] + inc["capital"] + inc["grants"] - inc["total"]) <= 4
        assert abs(exp["current"] + exp["capital"] - exp["total"]) <= 2
        assert abs(sum(exp["categories"].values()) - exp["total"]) <= len(exp["categories"])


def test_kutna_hora_metadata():
    d = load("533955")
    assert d["name"] == "Kutná Hora"
    assert d["ico"] == "00236195"
    assert d["kraj"] == "CZ020"
    y = year(d, 2025)
    assert y["population"] == 21642  # ČSÚ, k 1. 1. 2025 (stejné číslo uvádí Monitor)
    g = y["group"]
    assert g["band"] == 8  # 20 001–50 000 obyvatel
    assert g["n"] >= C.MIN_GROUP_SIZE


def test_index_complete():
    with open(C.OUTPUT / "index.json", encoding="utf-8") as f:
        idx = json.load(f)
    assert len(idx) > 6200  # v ČR je přes 6 250 obcí
    assert idx[0][1] == "Praha"
    assert len({r[0] for r in idx}) == len(idx)
