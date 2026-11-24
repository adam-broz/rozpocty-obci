"""Spuštění celé pipeline jedním příkazem:

    uv run python -m pipeline            # stáhne (co chybí), zpracuje, exportuje
    uv run python -m pipeline --offline  # jen z dat, která už jsou na disku
"""

from __future__ import annotations

import argparse
import logging
import re
import time

import duckdb

from . import aggregate, download, export, prepare
from . import config as C


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m pipeline", description=__doc__)
    ap.add_argument("--offline", action="store_true", help="nic nestahovat, použít jen cache")
    ap.add_argument("--years", type=int, nargs="*", help="konkrétní roky (výchozí: posledních N uzavřených)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    t0 = time.time()

    if args.offline:
        years = args.years or sorted(
            int(m.group(1)) for p in (C.RAW / "finm").glob("*_12.zip") if (m := re.match(r"(\d{4})_12", p.name))
        )[-C.N_YEARS :]
    else:
        years = download.download_all(args.years)
    logging.info("roky: %s", years)

    prepare.prepare_all(years)
    con = duckdb.connect()
    aggregate.build(con, years)
    export.export(con, years)
    logging.info("hotovo za %.0f s", time.time() - t0)


if __name__ == "__main__":
    main()
