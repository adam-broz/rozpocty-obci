"""Načtení a použití mapování paragrafů na kategorie (categories.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from . import config as C

DEFAULT_CATEGORY = "ostatni"


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    description: str
    phrase: str
    prefixes: tuple[str, ...]


@lru_cache
def load(path: Path = C.CATEGORIES_FILE) -> tuple[Category, ...]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cats = tuple(
        Category(c["id"], c["name"], c.get("description", ""), c.get("phrase", ""), tuple(str(p) for p in c.get("prefixes", [])))
        for c in raw["categories"]
    )
    ids = [c.id for c in cats]
    if len(ids) != len(set(ids)):
        raise ValueError("categories.yaml: duplicitní id kategorie")
    if DEFAULT_CATEGORY not in ids:
        raise ValueError(f"categories.yaml: chybí výchozí kategorie '{DEFAULT_CATEGORY}'")
    seen: dict[str, str] = {}
    for c in cats:
        for p in c.prefixes:
            if not p.isdigit() or not 1 <= len(p) <= 4:
                raise ValueError(f"categories.yaml: neplatný prefix '{p}' u {c.id}")
            if p in seen:
                raise ValueError(f"categories.yaml: prefix '{p}' je u '{seen[p]}' i '{c.id}'")
            seen[p] = c.id
    return cats


def prefix_table() -> list[tuple[str, str]]:
    """Seznam (prefix, id_kategorie) pro SQL join."""
    return [(p, c.id) for c in load() for p in c.prefixes]


def categorize(paragraf: str) -> str:
    """Kategorie pro čtyřmístný paragraf (nejdelší shodný prefix vyhrává)."""
    best, best_len = DEFAULT_CATEGORY, 0
    for prefix, cat in prefix_table():
        if paragraf.startswith(prefix) and len(prefix) > best_len:
            best, best_len = cat, len(prefix)
    return best
