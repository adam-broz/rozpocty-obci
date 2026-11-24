"""Testy mapování paragrafů na kategorie (pipeline/categories.yaml)."""

from pathlib import Path

import duckdb
import pytest

from pipeline import categories
from pipeline import config as C


@pytest.mark.parametrize(
    "paragraf, expected",
    [
        ("2212", "doprava"),  # Silnice
        ("2219", "doprava"),  # Ostatní záležitosti pozemních komunikací (chodníky)
        ("2292", "doprava"),  # Dopravní obslužnost
        ("3111", "skolstvi"),  # Mateřské školy
        ("3113", "skolstvi"),  # Základní školy
        ("3314", "kultura"),  # Činnosti knihovnické
        ("3399", "kultura"),  # Ostatní záležitosti kultury, církví a sdělovacích prostředků
        ("3412", "sport"),  # Sportovní zařízení ve vlastnictví obce
        ("3421", "sport"),  # Využití volného času dětí a mládeže
        ("3612", "bydleni"),  # Bytové hospodářství
        ("3631", "bydleni"),  # Veřejné osvětlení
        ("3632", "bydleni"),  # Pohřebnictví
        ("2310", "bydleni"),  # Pitná voda
        ("2321", "zivotni_prostredi"),  # Odvádění a čištění odpadních vod
        ("3722", "zivotni_prostredi"),  # Sběr a svoz komunálních odpadů
        ("3745", "zivotni_prostredi"),  # Péče o vzhled obcí a veřejnou zeleň
        ("1031", "zivotni_prostredi"),  # Pěstební činnost (lesy)
        ("1014", "ostatni"),  # Ozdravování hospodářských zvířat
        ("4351", "socialni"),  # Osobní asistence, pečovatelská služba
        ("3511", "zdravotnictvi"),  # Všeobecná ambulantní péče
        ("5311", "bezpecnost"),  # Bezpečnost a veřejný pořádek (obecní policie)
        ("5512", "bezpecnost"),  # Požární ochrana – dobrovolná část
        ("6112", "sprava"),  # Zastupitelstva obcí
        ("6171", "sprava"),  # Činnost místní správy
        ("6310", "ostatni"),  # Obecné příjmy a výdaje z finančních operací
        ("6399", "ostatni"),  # Ostatní finanční operace
        ("6409", "ostatni"),  # Ostatní činnosti jinde nezařazené
        ("2143", "ostatni"),  # Cestovní ruch
        ("9999", "ostatni"),  # neexistující → výchozí kategorie
    ],
)
def test_known_paragraphs(paragraf, expected):
    assert categories.categorize(paragraf) == expected


def test_yaml_is_consistent():
    cats = categories.load()
    assert 10 <= len(cats) <= 12
    assert all(c.name and c.description for c in cats)


def test_longest_prefix_wins():
    # 23 (vodní hospodářství) je rozdělen podle pododdílů
    assert categories.categorize("2310") == "bydleni"
    assert categories.categorize("2321") == "zivotni_prostredi"


PARAGRAF = C.INTERIM / "paragraf.parquet"


@pytest.mark.skipif(not PARAGRAF.exists(), reason="číselník paragrafů není stažený (spusťte pipeline)")
def test_every_valid_paragraph_has_explicit_category():
    """Každý paragraf platný v posledních letech musí mít kategorii explicitně
    z YAML (ne jen přes výchozí „ostatni“), aby nic nepropadlo nepozorovaně."""
    rows = duckdb.sql(
        f"SELECT DISTINCT paragraf, nazev FROM '{PARAGRAF}' "
        "WHERE end_date >= '2021-01-01' AND paragraf <> '0000'"
    ).fetchall()
    assert len(rows) > 500
    prefixes = [p for p, _ in categories.prefix_table()]
    unmapped = [(p, n) for p, n in rows if not any(p.startswith(x) for x in prefixes)]
    assert unmapped == [], f"paragrafy bez kategorie: {unmapped[:20]}"
