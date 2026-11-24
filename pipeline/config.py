"""Společná konfigurace pipeline: cesty, URL zdrojů a parametry."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"  # stažené soubory (cache, nic se nestahuje dvakrát)
INTERIM = DATA / "interim"  # rozbalené / převedené mezivýsledky (parquet)
OUTPUT = ROOT / "web" / "public" / "data"  # výsledné JSONy pro web

CATEGORIES_FILE = Path(__file__).resolve().parent / "categories.yaml"

# --- Zdroje -----------------------------------------------------------------
MONITOR = "https://monitor.statnipokladna.gov.cz"
# Extrakt výkazu FIN 2-12 M za daný rok a měsíc (12 = celý rok).
FINM_URL = MONITOR + "/data/extrakty/csv/FinM/{year}_{month:02d}_Data_CSUIS_FINM.zip"
# Číselníky Monitoru (XML).
CODELIST_URL = MONITOR + "/data/xml/{name}.xml"
CODELISTS = ["ucjed", "polozka", "paragraf"]
# ČSÚ: Počet obyvatel podle pohlaví (OBY02A), územní členění až do obcí.
CSU_POP_URL = "https://data.csu.gov.cz/opendata/sady/OBY02A/distribuce/csv"

# Odkazy pro web
MONITOR_UNIT_URL = MONITOR + "/ucetni-jednotka/{ico}/prehled?rad=t&obdobi={yy}12"
MONITOR_LICENSE_URL = MONITOR + "/datovy-katalog/licence"

# --- Parametry ----------------------------------------------------------------
N_YEARS = 5  # kolik uzavřených let zpracovat (trend)
FIRST_POSSIBLE_YEAR = 2010
# Číselníky se mění (nové obce, změny názvů) – po kolika dnech je stáhnout znovu.
CODELIST_MAX_AGE_DAYS = 25
# Mezi požadavky na stejný server čekáme, ať nikoho nezahltíme.
REQUEST_PAUSE_S = 2.0
# Minimální velikost srovnávací skupiny v kraji; jinak se srovnává celostátně.
MIN_GROUP_SIZE = 5

USER_AGENT = "rozpocty-obci (open-source; https://github.com/adam-broz/rozpocty-obci) python-urllib"

KRAJE = {
    "CZ010": "Hlavní město Praha",
    "CZ020": "Středočeský kraj",
    "CZ031": "Jihočeský kraj",
    "CZ032": "Plzeňský kraj",
    "CZ041": "Karlovarský kraj",
    "CZ042": "Ústecký kraj",
    "CZ051": "Liberecký kraj",
    "CZ052": "Královéhradecký kraj",
    "CZ053": "Pardubický kraj",
    "CZ063": "Kraj Vysočina",
    "CZ064": "Jihomoravský kraj",
    "CZ071": "Olomoucký kraj",
    "CZ072": "Zlínský kraj",
    "CZ080": "Moravskoslezský kraj",
}

# Velikostní kategorie obcí (dolní mez včetně). Odpovídají číselníku KATOBYV
# Monitoru, jen dvě největší (100 tis.–1 mil. a nad 1 mil.) jsou sloučené,
# protože Praha by jinak neměla s kým se srovnávat.
SIZE_BANDS = [
    (0, "do 100 obyvatel"),
    (101, "101–200 obyvatel"),
    (201, "201–500 obyvatel"),
    (501, "501–1 000 obyvatel"),
    (1001, "1 001–2 000 obyvatel"),
    (2001, "2 001–5 000 obyvatel"),
    (5001, "5 001–10 000 obyvatel"),
    (10001, "10 001–20 000 obyvatel"),
    (20001, "20 001–50 000 obyvatel"),
    (50001, "50 001–100 000 obyvatel"),
    (100001, "nad 100 000 obyvatel"),
]


def size_band(population: int | None) -> int | None:
    """Index velikostní kategorie podle počtu obyvatel."""
    if population is None:
        return None
    idx = 0
    for i, (low, _) in enumerate(SIZE_BANDS):
        if population >= low:
            idx = i
    return idx


def today() -> dt.date:
    return dt.date.today()
