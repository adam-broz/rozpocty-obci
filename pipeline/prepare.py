"""Převod surových souborů (ZIP/CSV/XML) na úsporné parquet tabulky.

Výstupy v data/interim/:
- ucjed_obce.parquet   – účetní jednotky typu „obec“ (druhuj 4) se všemi obdobími platnosti
- polozka.parquet      – číselník rozpočtových položek (druhové třídění)
- paragraf.parquet     – číselník paragrafů (odvětvové třídění)
- obyvatele.parquet    – počet obyvatel obcí k 1. 1. podle ČSÚ
- finm_{rok}.parquet   – FIN 2-12 M, tabulky příjmů a výdajů, jen obce, sečtené
                         podle (IČO, paragraf, položka)
"""

from __future__ import annotations

import logging
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import duckdb

from . import config as C
from .download import finm_path

log = logging.getLogger(__name__)

# Druh účetní jednotky 4 = „Obce“ (číselník DRUHUJ). Poddruh 410 = krajský úřad.
DRUHUJ_OBEC = "4"
PODDRUHUJ_KRAJ = "410"

FINM_MEMBER = re.compile(r"^FINM201_\d+\.csv$", re.IGNORECASE)


def _fresh(out: Path, *sources: Path) -> bool:
    return out.exists() and all(out.stat().st_mtime >= s.stat().st_mtime for s in sources)


def _xml_rows(path: Path, keep=None):
    for _, el in ET.iterparse(path):
        if el.tag == "row":
            d = {c.tag: (c.text or "").strip() for c in el}
            el.clear()
            if keep is None or keep(d):
                yield d


def _write_rows(con: duckdb.DuckDBPyConnection, rows: list[dict], out: Path) -> None:
    import csv
    import tempfile

    if not rows:
        raise RuntimeError(f"Žádná data pro {out.name}")
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
        tmp = f.name
    con.execute(
        f"COPY (SELECT * FROM read_csv('{tmp}', all_varchar=true, header=true)) TO '{out}' (FORMAT parquet)"
    )
    Path(tmp).unlink()


def prepare_codelists(con: duckdb.DuckDBPyConnection) -> None:
    src = C.RAW / "cis" / "ucjed.xml"
    out = C.INTERIM / "ucjed_obce.parquet"
    if not _fresh(out, src):
        log.info("převádím číselník účetních jednotek (velký soubor, chvíli to trvá)")
        rows = list(
            _xml_rows(
                src,
                lambda d: d.get("druhuj_id") == DRUHUJ_OBEC
                and d.get("poddruhuj_id") != PODDRUHUJ_KRAJ
                and d.get("zuj_id"),
            )
        )
        _write_rows(con, rows, out)
    for name in ("polozka", "paragraf"):
        src = C.RAW / "cis" / f"{name}.xml"
        out = C.INTERIM / f"{name}.parquet"
        if not _fresh(out, src):
            log.info("převádím číselník %s", name)
            _write_rows(con, list(_xml_rows(src)), out)


def prepare_population(con: duckdb.DuckDBPyConnection) -> None:
    src = C.RAW / "csu" / "OBY02A.csv"
    out = C.INTERIM / "obyvatele.parquet"
    if _fresh(out, src):
        return
    log.info("převádím počty obyvatel ČSÚ")
    # IndicatorType 2406P = počet obyvatel k 1. 1.; POHL2 = 0 = obě pohlaví;
    # šestimístný kód území = kód obce (ZÚJ).
    con.execute(
        f"""
        COPY (
          SELECT UZ01234596C AS zuj, CAST(CasR AS INTEGER) AS rok,
                 CAST(Hodnota AS INTEGER) AS obyvatel,
                 "Všechna území" AS nazev_csu
          FROM read_csv('{src}', all_varchar=true, header=true)
          WHERE IndicatorType = '2406P' AND POHL2 = '0' AND length(UZ01234596C) = 6
        ) TO '{out}' (FORMAT parquet)
        """
    )


def _amount(col: str) -> str:
    # Částky mají znaménko mínus na konci („1551157.54-“) a mezeru za číslem.
    return (
        f"(CASE WHEN trim({col}) LIKE '%-' THEN -CAST(rtrim(trim({col}), '-') AS DOUBLE) "
        f"ELSE CAST(NULLIF(trim({col}), '') AS DOUBLE) END)"
    )


def prepare_finm(con: duckdb.DuckDBPyConnection, year: int) -> Path:
    src = finm_path(year)
    out = C.INTERIM / f"finm_{year}.parquet"
    ucjed = C.INTERIM / "ucjed_obce.parquet"
    if _fresh(out, src, ucjed):
        return out
    log.info("zpracovávám FIN 2-12 M %s", year)
    tmpdir = C.INTERIM / f"_finm_{year}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        members = [n for n in z.namelist() if FINM_MEMBER.match(Path(n).name)]
        if len(members) != 1:
            raise RuntimeError(f"{src.name}: čekal jsem jeden soubor FINM201_*.csv, našel {members}")
        csv_path = Path(z.extract(members[0], tmpdir))
    # Hlavička má tvar `"""Popis"""TECH:ZKRATKA` – použijeme část za poslední dvojtečkou.
    with open(csv_path, encoding="utf-8") as f:
        header = f.readline().rstrip("\r\n").split(";")
    names = [h.rsplit(":", 1)[-1].strip('"') for h in header]
    required = {"ZC_VTAB", "ZC_ICO", "0FUNC_AREA", "ZCMMT_ITM", "ZU_ROZSCH", "ZU_ROZPZM", "ZU_ROZKZ"}
    missing = required - set(names)
    if missing:
        raise RuntimeError(f"{csv_path.name}: chybí sloupce {missing}")
    cols = ", ".join(f"'{n}': 'VARCHAR'" for n in names)
    con.execute(
        f"""
        COPY (
          WITH raw AS (
            SELECT * FROM read_csv('{csv_path}', header=false, skip=1, delim=';', quote='',
                                   columns={{{cols}}}, null_padding=true)
          ), obce AS (
            SELECT DISTINCT ico FROM '{ucjed}'
            WHERE start_date <= '{year}-12-31' AND end_date >= '{year}-12-31'
          )
          SELECT {year} AS rok, r.ZC_ICO AS ico, r.ZC_VTAB AS vtab,
                 r."0FUNC_AREA" AS paragraf, r.ZCMMT_ITM AS polozka,
                 sum({_amount('r.ZU_ROZSCH')}) AS schvaleny,
                 sum({_amount('r.ZU_ROZPZM')}) AS po_zmenach,
                 sum({_amount('r.ZU_ROZKZ')}) AS skutecnost
          FROM raw r JOIN obce o ON r.ZC_ICO = o.ico
          WHERE r.ZC_VTAB IN ('000100', '000200')
          GROUP BY ALL
        ) TO '{out}' (FORMAT parquet)
        """
    )
    shutil.rmtree(tmpdir)
    return out


def prepare_all(years: list[int]) -> None:
    C.INTERIM.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    prepare_codelists(con)
    prepare_population(con)
    for y in years:
        prepare_finm(con, y)
