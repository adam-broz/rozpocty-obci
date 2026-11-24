# Licence a podmínky užití dat

Kód projektu je pod licencí MIT (viz [LICENSE](LICENSE)). Data, se kterými
pracuje, mají vlastní podmínky užití od svých poskytovatelů. Ověřeno 24. 11. 2026.

## Ministerstvo financí ČR – Monitor státní pokladny

| Datová sada | Použitý soubor |
|---|---|
| FIN 2-12 M – Plnění rozpočtu ÚSC (`…/api/opendata/monitor/FinM`) | `https://monitor.statnipokladna.gov.cz/data/extrakty/csv/FinM/{rok}_12_Data_CSUIS_FINM.zip` |
| Číselník Účetní jednotka (`…/ciselnik-ucetni-jednotka`) | `https://monitor.statnipokladna.gov.cz/data/xml/ucjed.xml` |
| Číselník Rozpočtová položka (`…/ciselnik-rozpoctova-polozka`) | `https://monitor.statnipokladna.gov.cz/data/xml/polozka.xml` |
| Číselník Paragraf (`…/ciselnik-paragraf`) | `https://monitor.statnipokladna.gov.cz/data/xml/paragraf.xml` |

**Národní katalog otevřených dat:** datové sady Monitoru v NKOD (data.gov.cz)
**zaregistrované nejsou**. SPARQL dotaz na data.gov.cz pro poskytovatele
Ministerstvo financí (IČO 00006947) vrací jen „podněty na data k otevření“
(např. R163, R168 – Integrovaný informační systém Státní pokladny), ne samotné
datové sady.

**Podmínky užití** proto bereme z DCAT katalogu, který Monitor publikuje podle
otevřené formální normy (`https://monitor.statnipokladna.gov.cz/api/opendata/monitor`).
U distribucí jsou uvedeny tyto podmínky užití:

| Položka | Hodnota |
|---|---|
| Autorské dílo | [neobsahuje autorská díla](https://data.gov.cz/podmínky-užití/neobsahuje-autorská-díla/) |
| Databáze jako autorské dílo | [licenční podmínky Monitoru](https://monitor.statnipokladna.gov.cz/datovy-katalog/licence) |
| Databáze chráněná zvláštními právy | [licenční podmínky Monitoru](https://monitor.statnipokladna.gov.cz/datovy-katalog/licence) |
| Osobní údaje | [neobsahuje osobní údaje](https://data.gov.cz/podmínky-užití/neobsahuje-osobní-údaje/) |

[Podmínky užívání dat portálu MONITOR](https://monitor.statnipokladna.gov.cz/datovy-katalog/licence)
povolují data užívat, šířit a zpracovávat i v dalších dílech, komerčně
i nekomerčně, za těchto podmínek:

1. **Uvést zřetelně, že zdrojem dat je MF ČR**, a nesmí vzniknout dojem, že MF ČR
   uživatele nebo způsob užití podporuje. → Na webu i v README uvádíme
   „Zdroj dat: Ministerstvo financí ČR, Monitor státní pokladny; Český statistický
   úřad“ a výslovně píšeme, že jde o nezávislý projekt.
2. **Odkázat na podmínky užívání** při šíření dat nebo děl z nich. → Odkaz je
   v patičce každé stránky webu, na stránce „Jak to počítáme“ a v README.
3. Podmínky dále uvádějí, že uživatel **„není oprávněn Data jakkoliv upravovat či
   pozměňovat ani užívat způsobem … který by mohl působit … klamavě“**.

> ⚠️ **K bodu 3:** projekt data agreguje (sčítá do kategorií), vylučuje
> konsolidační položky a přepočítává je na obyvatele. Výslovně je přitom povoleno
> data „zpracovávat a začleňovat do děl“. Hodnoty samotné neměníme – součty jsou
> ověřené proti portálu Monitor (VALIDATION.md) – a všude uvádíme, že jde
> o upravená data, s odkazem na původní data obce na Monitoru. Výklad podmínky
> o „upravování“ ale není jednoznačný; před veřejným spuštěním doporučujeme
> zvážit dotaz na MF ČR.

## Český statistický úřad – počet obyvatel

| Datová sada | Použitý soubor |
|---|---|
| [Počet obyvatel podle pohlaví (OBY02A)](https://data.csu.gov.cz/opendata/sady/OBY02A) – k 1. 1., 1. 7. a 31. 12., až do úrovně obcí | `https://data.csu.gov.cz/opendata/sady/OBY02A/distribuce/csv` |

Podmínky užití uvedené v katalogovém záznamu distribuce (formát NKOD):

| Položka | Hodnota |
|---|---|
| Autorské dílo | [neobsahuje autorská díla](https://data.gov.cz/podmínky-užití/neobsahuje-autorská-díla/) |
| Databáze jako autorské dílo | [není autorskoprávně chráněnou databází](https://data.gov.cz/podmínky-užití/není-autorskoprávně-chráněnou-databází/) |
| Databáze chráněná zvláštními právy | [není chráněna zvláštním právem pořizovatele databáze](https://data.gov.cz/podmínky-užití/není-chráněna-zvláštním-právem-pořizovatele-databáze/) |
| Osobní údaje | [neobsahuje osobní údaje](https://data.gov.cz/podmínky-užití/neobsahuje-osobní-údaje/) |

Data ČSÚ jsou tedy volně použitelná bez dalších podmínek; zdroj přesto uvádíme.

## Výstupy projektu

JSON soubory a obrázky, které projekt generuje (`web/public/data`, `web/public/og`),
jsou odvozené z výše uvedených dat a platí pro ně podmínky jejich zdrojů – zejména
povinnost uvést MF ČR jako zdroj a odkázat na podmínky užívání Monitoru.
