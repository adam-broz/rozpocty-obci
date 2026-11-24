"""Šetrné stahování zdrojových dat do lokální cache.

Pravidla:
- co už je na disku, se znovu nestahuje (výjimka: číselníky starší než
  CODELIST_MAX_AGE_DAYS a nejnovější rok, dokud se mohl měnit);
- vše se stahuje postupně, s pauzou mezi požadavky;
- stahuje se do dočasného souboru a teprve po úspěchu se přejmenuje.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config as C

log = logging.getLogger(__name__)
_last_request = 0.0


def _pause() -> None:
    global _last_request
    wait = C.REQUEST_PAUSE_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _request(url: str, method: str = "GET"):
    _pause()
    req = urllib.request.Request(url, method=method, headers={"User-Agent": C.USER_AGENT})
    return urllib.request.urlopen(req, timeout=300)


def exists_remote(url: str) -> bool:
    try:
        with _request(url, "HEAD") as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def fetch(url: str, dest: Path, max_age_days: float | None = None) -> Path:
    """Stáhne `url` do `dest`, pokud tam soubor ještě není (nebo je starý)."""
    if dest.exists() and dest.stat().st_size > 0:
        age_days = (time.time() - dest.stat().st_mtime) / 86400
        if max_age_days is None or age_days < max_age_days:
            log.info("cache: %s", dest.relative_to(C.ROOT))
            return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log.info("stahuji %s", url)
    with _request(url) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)
    return dest


def finm_path(year: int) -> Path:
    return C.RAW / "finm" / f"{year}_12.zip"


def latest_complete_year() -> int:
    """Nejnovější rok, za který už je zveřejněn celoroční (12.) extrakt FIN 2-12 M."""
    year = C.today().year
    for y in range(year, C.FIRST_POSSIBLE_YEAR, -1):
        if finm_path(y).exists() or exists_remote(C.FINM_URL.format(year=y, month=12)):
            return y
    raise RuntimeError("Nepodařilo se najít žádný celoroční extrakt FIN 2-12 M")


def download_all(years: list[int] | None = None) -> list[int]:
    if years is None:
        last = latest_complete_year()
        years = list(range(last - C.N_YEARS + 1, last + 1))
    for y in years:
        # Celoroční data se po zveřejnění ještě mohou opravovat; poslední rok
        # proto obnovujeme jednou za čas, starší roky jsou už stabilní.
        max_age = C.CODELIST_MAX_AGE_DAYS if y == years[-1] else None
        fetch(C.FINM_URL.format(year=y, month=12), finm_path(y), max_age)
    for name in C.CODELISTS:
        fetch(C.CODELIST_URL.format(name=name), C.RAW / "cis" / f"{name}.xml", C.CODELIST_MAX_AGE_DAYS)
    fetch(C.CSU_POP_URL, C.RAW / "csu" / "OBY02A.csv", C.CODELIST_MAX_AGE_DAYS)
    return years
