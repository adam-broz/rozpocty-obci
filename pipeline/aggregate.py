"""Agregace FIN 2-12 M na souhrnná čísla za obec a rok + srovnávací mediány.

Klíčová pravidla (podrobně v DECISIONS.md):
- Bere se SKUTEČNOST (sloupec ZU_ROZKZ = výsledek od počátku roku k 31. 12.).
- Vylučují se konsolidační položky (v číselníku položek příznak kon_pol = true),
  tj. převody mezi vlastními účty a fondy obce (4134/5345, 4133/5344, 4139/5349,
  4138/5348, 5342) a převody mezi statutárním městem a jeho obvody
  (4137/5347, 4251/6363). Výsledek odpovídá „konsolidovaným“ příjmům a výdajům
  na portálu Monitor.
- Financování (třída 8: úvěry, splátky, změna stavu účtů) se do příjmů ani
  výdajů nepočítá.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from . import categories
from . import config as C

INCOME_CLASSES = {"1": "tax", "2": "nontax", "3": "capital", "4": "grants"}
EXPENSE_CLASSES = {"5": "current", "6": "capital"}
# Převody statutárního města jeho obvodům/městským částem (výdaje).
DISTRICT_TRANSFER_ITEMS = ("5347", "6363")


def build(con: duckdb.DuckDBPyConnection, years: list[int]) -> None:
    """Vytvoří v `con` tabulky: obce, rows, obec_rok, obec_kat, skupiny."""
    I = C.INTERIM
    last = max(years)
    finm = ", ".join(f"'{I / f'finm_{y}.parquet'}'" for y in years)

    # --- Seznam obcí (stav k 31. 12. posledního roku) ---------------------------
    con.execute(
        f"""
        CREATE OR REPLACE TABLE obce AS
        WITH u AS (
          SELECT *, row_number() OVER (PARTITION BY zuj_id ORDER BY end_date DESC, start_date DESC) rn
          FROM '{I / 'ucjed_obce.parquet'}'
          WHERE start_date <= '{last}-12-31' AND end_date >= '{last}-12-31'
        ), csu AS (
          SELECT zuj, any_value(nazev_csu) FILTER (WHERE rok = (SELECT max(rok) FROM '{I / 'obyvatele.parquet'}')) nazev_csu
          FROM '{I / 'obyvatele.parquet'}' GROUP BY zuj
        )
        SELECT u.zuj_id AS zuj, u.ico, u.nazev AS nazev_uj, u.obec AS nazev_obec,
               csu.nazev_csu, u.kraj, u.poddruhuj_id AS poddruh
        FROM u LEFT JOIN csu ON csu.zuj = u.zuj_id
        WHERE rn = 1
        """
    )

    # --- Řádky výkazu s klasifikací --------------------------------------------
    con.execute("CREATE OR REPLACE TEMP TABLE cat_prefix (prefix VARCHAR, kat VARCHAR)")
    con.executemany("INSERT INTO cat_prefix VALUES (?, ?)", categories.prefix_table())
    con.execute(
        f"""
        CREATE OR REPLACE TABLE rows AS
        WITH f AS (SELECT * FROM read_parquet([{finm}])),
        pol AS (
          SELECT polozka, start_date, end_date, kon_pol FROM '{I / 'polozka.parquet'}'
        ),
        f2 AS (
          SELECT f.*, o.zuj,
                 coalesce((SELECT any_value(p.kon_pol = 'true') FROM pol p
                           WHERE p.polozka = f.polozka
                             AND p.start_date <= f.rok || '-12-31' AND p.end_date >= f.rok || '-12-31'),
                          false) AS konsolidace
          FROM f JOIN obce o ON o.ico = f.ico
        )
        SELECT f2.*, substr(polozka, 1, 1) AS trida,
               (SELECT kat FROM cat_prefix c WHERE f2.paragraf LIKE c.prefix || '%'
                ORDER BY length(c.prefix) DESC LIMIT 1) AS kat
        FROM f2
        """
    )
    con.execute(f"UPDATE rows SET kat = '{categories.DEFAULT_CATEGORY}' WHERE kat IS NULL")

    # --- Součty za obec a rok -----------------------------------------------------
    inc = ",\n".join(
        f"sum(skutecnost) FILTER (WHERE vtab='000100' AND trida='{t}' AND NOT konsolidace) AS income_{n}"
        for t, n in INCOME_CLASSES.items()
    )
    exp = ",\n".join(
        f"sum(skutecnost) FILTER (WHERE vtab='000200' AND trida='{t}' AND NOT konsolidace) AS expense_{n}"
        for t, n in EXPENSE_CLASSES.items()
    )
    is_inc = "vtab='000100' AND trida IN ('1','2','3','4') AND NOT konsolidace"
    is_exp = "vtab='000200' AND trida IN ('5','6') AND NOT konsolidace"
    items = ", ".join(f"'{p}'" for p in DISTRICT_TRANSFER_ITEMS)
    con.execute(
        f"""
        CREATE OR REPLACE TABLE obec_rok AS
        WITH s AS (
          SELECT zuj, rok,
            {inc},
            {exp},
            sum(skutecnost) FILTER (WHERE {is_inc}) AS income_total,
            sum(skutecnost) FILTER (WHERE {is_exp}) AS expense_total,
            sum(schvaleny) FILTER (WHERE {is_inc}) AS income_approved,
            sum(po_zmenach) FILTER (WHERE {is_inc}) AS income_amended,
            sum(schvaleny) FILTER (WHERE {is_exp}) AS expense_approved,
            sum(po_zmenach) FILTER (WHERE {is_exp}) AS expense_amended,
            sum(skutecnost) FILTER (WHERE vtab='000200' AND polozka IN ({items})) AS district_transfers
          FROM rows GROUP BY zuj, rok
        )
        SELECT s.*, p.obyvatel AS population
        FROM s LEFT JOIN '{I / 'obyvatele.parquet'}' p ON p.zuj = s.zuj AND p.rok = s.rok
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE obec_kat AS
        SELECT zuj, rok, kat, sum(skutecnost) AS amount
        FROM rows WHERE {is_exp}
        GROUP BY ALL
        """
    )

    # --- Srovnávací skupiny a mediány --------------------------------------------
    band_case = " ".join(
        f"WHEN r.population >= {low} THEN {i}" for i, (low, _) in reversed(list(enumerate(C.SIZE_BANDS)))
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE obec_rok AS
        SELECT r.*, o.kraj,
               CASE {band_case} END AS band
        FROM obec_rok r JOIN obce o USING (zuj)
        """
    )
    # Hodnoty na obyvatele v „dlouhém“ tvaru: (zuj, rok, metrika, hodnota)
    metrics = [
        "income_total", "income_tax", "income_nontax", "income_capital", "income_grants",
        "expense_total", "expense_current", "expense_capital",
    ]
    union = " UNION ALL ".join(
        f"SELECT zuj, rok, kraj, band, '{m}' AS metric, coalesce({m}, 0) / population AS pc FROM obec_rok"
        for m in metrics
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE pc_long AS
        WITH base AS (
          SELECT * FROM obec_rok WHERE population > 0 AND expense_total IS NOT NULL
        ), allcats AS (
          SELECT b.zuj, b.rok, b.kraj, b.band, b.population, c.id AS kat
          FROM base b CROSS JOIN (SELECT unnest(?) AS id) c
        )
        SELECT * FROM ({union.replace('FROM obec_rok', 'FROM base')})
        UNION ALL
        SELECT a.zuj, a.rok, a.kraj, a.band, 'cat_' || a.kat, coalesce(k.amount, 0) / a.population
        FROM allcats a LEFT JOIN obec_kat k ON k.zuj = a.zuj AND k.rok = a.rok AND k.kat = a.kat
        """,
        [[c.id for c in categories.load()]],
    )
    _group_medians(con)


def median_without(values: list[float], k: int) -> float:
    """Medián seřazeného seznamu `values` bez prvku na pozici `k`."""
    m = len(values) - 1
    get = lambda j: values[j] if j < k else values[j + 1]  # noqa: E731
    if m % 2:
        return get(m // 2)
    return (get(m // 2 - 1) + get(m // 2)) / 2


def _group_medians(con: duckdb.DuckDBPyConnection) -> None:
    """Medián podobných obcí – BEZ obce samotné (srovnáváme s ostatními).

    Skupina = stejný rok, velikostní kategorie a kraj. Má-li skupina v kraji
    méně než MIN_GROUP_SIZE dalších obcí, použije se stejná kategorie v celé ČR.
    """
    from collections import defaultdict

    rows = con.execute("SELECT zuj, rok, kraj, band, metric, pc FROM pc_long").fetchall()
    kraj_g: dict[tuple, list] = defaultdict(list)
    cr_g: dict[tuple, list] = defaultdict(list)
    for zuj, rok, kraj, band, metric, pc in rows:
        kraj_g[(rok, kraj, band, metric)].append((pc, zuj))
        cr_g[(rok, band, metric)].append((pc, zuj))
    pos: dict[tuple, tuple[list[float], dict[str, int]]] = {}

    def lookup(key, groups):
        if key not in pos:
            items = sorted(groups[key])
            pos[key] = ([v for v, _ in items], {z: i for i, (_, z) in enumerate(items)})
        return pos[key]

    out: dict[tuple, dict] = {}
    for zuj, rok, kraj, band, metric, _ in rows:
        vals, idx = lookup((rok, kraj, band, metric), kraj_g)
        scope = "kraj"
        if len(vals) - 1 < C.MIN_GROUP_SIZE:
            vals, idx = lookup((rok, band, metric), cr_g)
            scope = "cr"
        if len(vals) < 2:
            continue
        rec = out.setdefault((zuj, rok), {"band": band, "scope": scope, "n": len(vals) - 1, "med": {}})
        rec["med"][metric] = median_without(vals, idx[zuj])

    import csv
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        w = csv.writer(f)
        w.writerow(["zuj", "rok", "band", "scope", "n", "metric", "med"])
        for (z, r), g in out.items():
            for metric, med in g["med"].items():
                w.writerow([z, r, g["band"], g["scope"], g["n"], metric, med])
        tmp = f.name
    con.execute(
        f"""
        CREATE OR REPLACE TABLE skupiny AS
        SELECT zuj, rok, band, scope, n, map(list(metric), list(med)) AS med
        FROM read_csv('{tmp}', header=true, types={{'zuj': 'VARCHAR', 'med': 'DOUBLE'}})
        GROUP BY zuj, rok, band, scope, n
        """
    )
    Path(tmp).unlink()
