"""Export agregovaných dat do JSON souborů pro statický web.

Výstup (web/public/data/):
- meta.json          – roky, kategorie, velikostní skupiny, kraje, zdroje, datum
- index.json         – seznam obcí pro vyhledávání (kompaktní pole)
- obce/{kód}.json    – detail jedné obce (všechny roky, srovnání se skupinou)
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import shutil

import duckdb

from . import categories
from . import config as C

log = logging.getLogger(__name__)

# Minimální hodnoty, aby „zajímavé číslo“ nevznikalo z drobných částek.
HIGHLIGHT_MIN_PC = 300  # Kč na obyvatele (u obce i u mediánu skupiny)
HIGHLIGHT_MIN_SHARE = 0.03  # podíl kategorie na výdajích skupiny (medián)

STATUTORY = {"411", "412"}  # Praha, statutární města
# Praha je obec i kraj zároveň (platí např. střední školy), srovnání
# výdajových kategorií s ostatními velkými městy by bylo zavádějící.
PRAHA = "554782"


def _r(x):
    return None if x is None else int(round(x))


def _split_name(nazev_csu: str | None, fallback: str) -> tuple[str, str | None]:
    """„Kutná Hora (okr. Kutná Hora)“ -> („Kutná Hora“, „Kutná Hora“)."""
    if nazev_csu:
        m = re.match(r"^(.*?)\s*\(okr\. (.*)\)$", nazev_csu)
        if m:
            return m.group(1), m.group(2)
        return nazev_csu, None
    return fallback, None


def _highlight(year: dict) -> dict | None:
    """Najde kategorii výdajů, ve které se obec nejvíc liší od podobných obcí."""
    g = year.get("group")
    pop = year.get("population")
    if not g or not pop:
        return None
    med = g["median"]
    med_total = med.get("expense_total") or 0
    best = None
    for cat_id, amount in year["expense"]["categories"].items():
        if cat_id == categories.DEFAULT_CATEGORY:
            continue
        m = med.get("cat_" + cat_id) or 0
        pc = amount / pop
        if m < HIGHLIGHT_MIN_PC or pc < HIGHLIGHT_MIN_PC or med_total <= 0 or m / med_total < HIGHLIGHT_MIN_SHARE:
            continue
        diff = pc / m - 1
        if best is None or abs(diff) > abs(best["diff"]):
            best = {"kind": "category", "id": cat_id, "pc": _r(pc), "median": _r(m), "diff": round(diff, 4)}
    if best is None and med_total > 0 and year["expense"]["total"] is not None:
        pc = year["expense"]["total"] / pop
        best = {"kind": "total", "id": "expense_total", "pc": _r(pc), "median": _r(med_total), "diff": round(pc / med_total - 1, 4)}
    return best


def export(con: duckdb.DuckDBPyConnection, years: list[int]) -> None:
    # Zapisujeme do dočasné složky a až nakonec ji prohodíme s tou ostrou,
    # aby web (nebo generátor obrázků) nikdy neviděl rozepsaná data.
    final = C.OUTPUT
    out = final.with_name(final.name + ".tmp")
    shutil.rmtree(out, ignore_errors=True)
    (out / "obce").mkdir(parents=True)

    cats = categories.load()
    cat_ids = [c.id for c in cats]

    obce = con.execute("SELECT zuj, ico, nazev_uj, nazev_obec, nazev_csu, kraj, poddruh FROM obce ORDER BY zuj").fetchall()
    cols = [d[0] for d in con.execute("SELECT * FROM obec_rok LIMIT 0").description]
    by_obec: dict[str, list[dict]] = {}
    for rec in con.execute("SELECT * FROM obec_rok ORDER BY zuj, rok").fetchall():
        d = dict(zip(cols, rec))
        by_obec.setdefault(d["zuj"], []).append(d)
    cats_by: dict[tuple[str, int], dict[str, float]] = {}
    for zuj, rok, kat, amount in con.execute("SELECT zuj, rok, kat, amount FROM obec_kat").fetchall():
        cats_by.setdefault((zuj, rok), {})[kat] = amount
    groups: dict[tuple[str, int], dict] = {}
    for zuj, rok, band, scope, n, med in con.execute("SELECT zuj, rok, band, scope, n, med FROM skupiny").fetchall():
        groups[(zuj, rok)] = {"band": band, "scope": scope, "n": n, "median": {k: _r(v) for k, v in med.items()}}

    index = []
    n_written = 0
    for zuj, ico, nazev_uj, nazev_obec, nazev_csu, kraj, poddruh in obce:
        name, okres = _split_name(nazev_csu, nazev_obec or nazev_uj)
        yrs = []
        for d in by_obec.get(zuj, []):
            cat = cats_by.get((zuj, d["rok"]), {})
            y = {
                "year": d["rok"],
                "population": d["population"],
                "income": {
                    "total": _r(d["income_total"]),
                    "tax": _r(d["income_tax"] or 0),
                    "nontax": _r(d["income_nontax"] or 0),
                    "capital": _r(d["income_capital"] or 0),
                    "grants": _r(d["income_grants"] or 0),
                },
                "expense": {
                    "total": _r(d["expense_total"]),
                    "current": _r(d["expense_current"] or 0),
                    "capital": _r(d["expense_capital"] or 0),
                    "categories": {c: _r(cat.get(c, 0)) for c in cat_ids},
                },
                "budget": {
                    "incomeApproved": _r(d["income_approved"]),
                    "incomeAmended": _r(d["income_amended"]),
                    "expenseApproved": _r(d["expense_approved"]),
                    "expenseAmended": _r(d["expense_amended"]),
                },
                "group": groups.get((zuj, d["rok"])),
            }
            if poddruh in STATUTORY and d["district_transfers"]:
                y["districtTransfers"] = _r(d["district_transfers"])
            yrs.append(y)
        latest = yrs[-1] if yrs else None
        doc = {
            "id": zuj,
            "ico": ico,
            "name": name,
            "officialName": nazev_uj,
            "okres": okres,
            "kraj": kraj,
            "statutory": poddruh in STATUTORY,
            "years": yrs,
            "isRegion": zuj == PRAHA,
            "highlight": (
                None if not latest
                else {"kind": "pcOnly", "id": "expense_total", "pc": _r(latest["expense"]["total"] / latest["population"])}
                if zuj == PRAHA else _highlight(latest)
            ),
            "sourceUrl": C.MONITOR_UNIT_URL.format(ico=ico, yy=str(latest["year"])[2:]) if latest else None,
        }
        with open(out / "obce" / f"{zuj}.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
        n_written += 1
        pop = latest["population"] if latest else None
        index.append([zuj, name, okres or "", kraj, pop or 0])

    index.sort(key=lambda r: (-r[4], r[1]))
    with open(out / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    meta = {
        "generated": dt.date.today().isoformat(),
        "years": years,
        "latestYear": max(years),
        "categories": [{"id": c.id, "name": c.name, "description": c.description, "phrase": c.phrase} for c in cats],
        "sizeBands": [label for _, label in C.SIZE_BANDS],
        "kraje": C.KRAJE,
        "minGroupSize": C.MIN_GROUP_SIZE,
        "sources": {
            "monitor": C.MONITOR,
            "monitorLicense": C.MONITOR_LICENSE_URL,
            "csu": "https://data.csu.gov.cz/opendata/sady/OBY02A",
        },
    }
    with open(out / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    old = final.with_name(final.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if final.exists():
        final.rename(old)
    out.rename(final)
    shutil.rmtree(old, ignore_errors=True)
    log.info("zapsáno %d obcí do %s", n_written, final.relative_to(C.ROOT))
