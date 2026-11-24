# CLAUDE.md: architektura pro další práci

Statický web o hospodaření všech obcí v ČR. Python pipeline vyrábí JSON, ze kterého
Astro sestaví statické stránky. Nemá žádný backend. Jazyk webu, komentářů i dokumentace je čeština.

## Struktura

```
pipeline/                Python 3.12 (uv, duckdb, pyyaml)
  __main__.py            `uv run python -m pipeline [--offline] [--years 2024 2025]`
  config.py              cesty, URL zdrojů, N_YEARS, velikostní pásma, kraje
  download.py            šetrné stahování s cache v data/raw (HEAD na zjištění posledního roku)
  prepare.py             XML/CSV/ZIP → parquet v data/interim (jen obce, sečteno po IČO×paragraf×položka)
  categories.yaml        paragraf → kategorie (prefixy, nejdelší vyhrává) – komunitou upravovaný soubor
  categories.py          načtení + validace YAML, categorize()
  aggregate.py           DuckDB: tabulky obce, rows, obec_rok, obec_kat, pc_long, skupiny (mediány)
  export.py              JSON do web/public/data (zápis do .tmp a atomické prohození)
tests/                   pytest: mapování, aritmetika mediánů, ručně ověřené obce (VALIDATION.md)
web/                     Astro 5, bez UI frameworku
  scripts/og.mjs         OG obrázky (satori → resvg → sharp palette PNG), paralelně, inkrementálně
  src/lib/data.ts        typy a čtení JSON při buildu (fs)
  src/lib/format.ts      formátování čísel, české fráze (kraj v 6. pádě, velikostní skupiny)
  src/lib/highlight.ts   věta se „zajímavým číslem“
  src/components/        Search (ARIA combobox), CategoryBars (HTML/CSS), TrendChart (SVG)
  src/pages/             index, o-projektu, obec/[id] (getStaticPaths z index.json)
.github/workflows/update.yml   měsíčně: pipeline → pytest → build → GitHub Pages
```

## Datový tok a klíčová pravidla

1. **FIN 2-12 M** `FINM201_*.csv` v ZIPu: oddělovač `;`, mínus za číslem (`123.45-`),
   hlavička `"""Popis"""TECH:KOD`, takže se bere část za poslední `:`. Tabulky `ZC_VTAB`
   000100 (příjmy) a 000200 (výdaje). Soubor `FINM201_MC_*` (městské části) se ignoruje.
2. **Obec** = `ucjed.druhuj_id = 4`, kromě poddruhu 410, s vyplněným `zuj_id`. Páruje se přes IČO
   a záznam platný k 31. 12. daného roku. `zuj_id` je kód obce = klíč k ČSÚ.
3. **Konsolidace** = vyloučit položky s `kon_pol = true` v číselníku položek, platném pro daný rok.
   Neměnit bez nové validace proti Monitoru.
4. Příjmy jsou třídy položek 1–4, výdaje 5–6. Třída 8 (financování) se nepočítá. Kategorie výdajů
   určuje paragraf.
5. **Obyvatelé:** ČSÚ OBY02A, ukazatel `2406P` (k 1. 1.), `POHL2 = 0`, šestimístný kód území.
6. **Skupiny:** stejný rok, velikostní pásmo (`config.SIZE_BANDS`) a kraj. Medián se počítá **bez
   obce samotné**. Je-li v kraji méně než `MIN_GROUP_SIZE` dalších obcí, srovnává se celostátně.
   Počítá to `aggregate._group_medians` v Pythonu.
7. Praha (`554782`) je obec i kraj, proto `isRegion` a žádné srovnání kategorií. Statutární města
   mají `districtTransfers` (5347+6363), které jsou zkonsolidované pryč.

## JSON obce (`web/public/data/obce/{zuj}.json`)

`{id, ico, name, officialName, okres, kraj, statutory, isRegion, years[], highlight, sourceUrl}`.
Každá položka `years[]` obsahuje `{year, population, income{total,tax,nontax,capital,grants},
expense{total,current,capital,categories{…}}, budget{incomeApproved,…}, group{band,scope,n,median{…}}}`.
Částky jsou v celých Kč, mediány v Kč na obyvatele. Klíče mediánů: `income_*`, `expense_*`,
`cat_{id}`. Index `index.json` je `[[zuj, název, okres, kraj, obyvatel], …]`, seřazený podle počtu
obyvatel sestupně.

## Příkazy

```bash
uv run python -m pipeline --offline   # bez stahování, ~10 s
uv run pytest -q
cd web && npm run dev                 # http://localhost:4321/rozpocty-obci/
cd web && OG_ONLY=533955 node scripts/og.mjs   # jeden OG obrázek (ladění)
cd web && npm run build               # OG + 6 256 stránek, ~2 min (+ OG poprvé ~10 min)
```

## Konvence a pasti

- `SITE_URL`, `BASE_PATH` a `PUBLIC_REPO_URL` nastavuje Action. Lokálně se použije base `/rozpocty-obci`.
  Odkazy proto vždy skládejte přes `import.meta.env.BASE_URL`.
- `scopedStyleStrategy: 'class'`: elementy vytvořené v JS (našeptávač) potřebují `:global(...)`.
- Satori potřebuje fonty latin a latin-ext jako **dvě různé rodiny** (`fontFamily: 'S, SX'`),
  jinak chybí diakritika. Rámec má `boxSizing: 'border-box'`.
- OG obrázky se přegenerují podle otisku obsahu v `public/og/.manifest.json`, ne podle času souboru.
- Nové kategorie: upravte `categories.yaml` (včetně `phrase`). Web i OG je načtou z `meta.json`.
- Zdroj dat a upozornění „data jsou upravená“ musí zůstat v patičce, v README i na OG obrázcích
  (licence MF ČR, viz DATA_LICENSE.md). Nikde nesmí vzniknout dojem, že projekt podporuje úřad.
- Neprovádět scraping webového UI Monitoru. Pouze open data (extrakty, číselníky, DCAT).
