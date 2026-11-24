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
    con.execute(
        f"""
        CREATE OR REPLACE TABLE skupiny AS
        WITH kraj_g AS (
          SELECT rok, kraj, band, metric, median(pc) AS med, count(*) AS n
          FROM pc_long GROUP BY ALL
        ), cr_g AS (
          SELECT rok, band, metric, median(pc) AS med, count(*) AS n
          FROM pc_long GROUP BY ALL
        )
        , picked AS (
          SELECT o.zuj, o.rok, o.band, k.metric,
                 k.n >= {C.MIN_GROUP_SIZE} AS in_kraj,
                 CASE WHEN k.n >= {C.MIN_GROUP_SIZE} THEN k.n ELSE c.n END AS group_n,
                 CASE WHEN k.n >= {C.MIN_GROUP_SIZE} THEN k.med ELSE c.med END AS med
          FROM (SELECT DISTINCT zuj, rok, kraj, band FROM pc_long) o
          JOIN kraj_g k ON k.rok = o.rok AND k.kraj = o.kraj AND k.band = o.band
          JOIN cr_g c ON c.rok = o.rok AND c.band = o.band AND c.metric = k.metric
        )
        SELECT zuj, rok, band,
               CASE WHEN bool_and(in_kraj) THEN 'kraj' ELSE 'cr' END AS scope,
               max(group_n) AS n,
               map_from_entries(list(struct_pack(k := metric, v := med))) AS med
        FROM picked GROUP BY zuj, rok, band
        """
    )
