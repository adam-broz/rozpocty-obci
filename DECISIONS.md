# Rozhodnutí

Záznam rozhodnutí, která padla při stavbě projektu, a jejich důvodů.
Nejnovější dole.

## Data

**D1. Zdroj účetních dat: extrakt FIN 2-12 M z open data Monitoru.**
Stahuje se `…/data/extrakty/csv/FinM/{rok}_12_Data_CSUIS_FINM.zip` (celoroční
stav k prosinci). Ze ZIPu se používá jen `FINM201_*.csv` (příjmy a výdaje podle
paragrafů a položek). Soubory `FINM201_MC_*` (městské části, od r. 2023) se
ignorují. Formát: oddělovač `;`, UTF-8 (starší roky čisté ASCII), částky
s tečkou a **znaménkem mínus za číslem** (`1551157.54-`), hlavička ve tvaru
`"""Popis"""TECH:ZKRATKA` – parser bere část za poslední dvojtečkou.

**D2. Jak poznám obec.** Číselník účetních jednotek (`ucjed.xml`): `druhuj_id = 4`
(Obce), kromě `poddruhuj_id = 410` (krajský úřad), a s vyplněným `zuj_id`
(kód obce). Dobrovolné svazky obcí mají `druhuj_id = 5`, příspěvkové organizace 7,
kraje mají vlastní poddruh – tím jsou vyloučené. Městské části Prahy a obvody
statutárních měst jsou v číselníku vedené jako jiný druh (30) a nezobrazujeme je.
Na konci roku 2025 je takto 6 254 obcí.

**D3. Propojení: IČO → kód obce → počet obyvatel.** Řádky výkazu se párují
s číselníkem přes IČO (`ZC_ICO`) a záznam platný k 31. 12. daného roku. Z něj se
bere `zuj_id` (šestimístný kód obce), kraj (`kraj`, NUTS3) a typ (statutární
město). Kód obce je klíčem k ČSÚ.

**D4. Počet obyvatel z ČSÚ, k 1. 1. daného roku.** Datová sada OBY02A
„Počet obyvatel podle pohlaví“, ukazatel `2406P` (k 1. 1.), obě pohlaví,
šestimístný kód území = obec. Stav k 1. 1. je stejný údaj, jaký k danému roku
uvádí Monitor (Kutná Hora 2025: 21 642 v obou). Pozor: ČSÚ údaje za 2021 zpětně
upravil podle sčítání, proto se mohou lišit od starších čísel v Monitoru.

**D5. Zobrazujeme skutečnost za uzavřené roky.** Sloupec `ZU_ROZKZ`
(výsledek od počátku roku) z prosincového výkazu. Schválený rozpočet
(`ZU_ROZSCH`) a rozpočet po změnách (`ZU_ROZPZM`) se ukládají jen do souhrnu
„jak se plnil rozpočet“ – nikdy se nemíchají se skutečností. Rozpracovaný rok
se nezobrazuje (měsíční data nejsou srovnatelná s celoročními).

**D6. Konsolidace podle příznaku v číselníku, ne podle ručního seznamu.**
Vyloučené jsou všechny položky s `kon_pol = true` v číselníku položek platném
pro daný rok (4133, 4134, 4137, 4138, 4139, 4251, 5342, 5344, 5345, 5347, 5348,
5349, 6363). Výsledek přesně odpovídá „konsolidovaným“ číslům Monitoru
(viz VALIDATION.md). Bez toho by např. Kutná Hora měla trojnásobné příjmy.

**D7. Převody statutárních měst obvodům.** Položky 5347/6363 (převody městským
částem/obvodům) jsou konsolidační, takže se v souladu s Monitorem do výdajů
města nepočítají. U Prahy jde o ~15 mld. Kč ročně, které pak utrácejí městské
části (ty nezobrazujeme). Na stránce statutárního města proto zvlášť ukazujeme
„převody obvodům/městským částem“ jako vysvětlivku.

**D8. Financování (třída 8) se nepočítá** do příjmů ani výdajů (úvěry a jejich
splácení nejsou hospodaření v pravém smyslu), stejně jako v Monitoru.

**D9. Pět let pro trend (výchozí `N_YEARS = 5`).** Poslední rok se zjistí
automaticky (existuje-li prosincový extrakt). V listopadu 2026 je to 2021–2025.

**D10. Licence MF.** Datové sady Monitoru nejsou v Národním katalogu otevřených
dat (NKOD) registrované (ověřeno SPARQL dotazem na data.gov.cz – od MF jsou tam
jen „podněty k otevření“). Podmínky užití jsou uvedené v DCAT záznamu katalogu
Monitoru a odkazují na stránku licenčních podmínek Monitoru. Viz DATA_LICENSE.md.

## Kategorie a srovnání

**D11. 11 kategorií výdajů podle paragrafů, nejdelší prefix vyhrává.**
Mapování je v `pipeline/categories.yaml` s komentáři. Sporné případy:
- Pitná voda (231x) → *Bydlení a komunální služby*; odpadní vody (232x),
  vodní toky a nádrže → *Životní prostředí* (podle COFOG 06.3 vs. 05.2).
- Lesy (103x) → *Životní prostředí*; ostatní zemědělství → *Ostatní*.
- Finanční operace (63xx) → *Ostatní*. Patří sem i daň z příjmů právnických osob,
  kterou obec platí sama sobě (6399/5365) – v příjmech i výdajích se objeví
  stejně jako v Monitoru.
- Hasiči i obecní policie → *Bezpečnost*.

**D12. Příjmy podle druhu (třídy položek):** 1 daňové, 2 nedaňové,
3 kapitálové, 4 přijaté transfery (= „dotace“). Výdaje: 5 běžné, 6 kapitálové
(= investice).

**D13. Srovnávací skupina = stejná velikostní kategorie ve stejném kraji,
medián.** Velikostní kategorie odpovídají číselníku KATOBYV (0–100, 101–200, …),
jen dvě největší jsou sloučené do „nad 100 000“. Pokud má skupina v kraji
méně než 5 obcí (velká města), srovnává se se stejnou kategorií v celé ČR.
Medián se počítá z hodnot na obyvatele a obec sama je v něm zahrnutá.
Skupina se počítá pro každý rok zvlášť (obec může mezi kategoriemi přecházet).

**D14. Praha je obec i kraj.** Hradí např. střední školy, takže srovnání
kategorií s ostatními velkými městy by bylo zavádějící. U Prahy se „zajímavé
číslo“ nesrovnává a stránka na to upozorňuje.

**D15. „Zajímavé číslo“ pro sdílení.** Kategorie výdajů (bez „Ostatní“),
ve které se obec nejvíc liší od mediánu skupiny. Aby nevznikaly nesmysly
z drobných částek, musí mít obec i medián aspoň 300 Kč/obyv. a kategorie musí
tvořit aspoň 3 % výdajů typické obce. Když nic nevyhoví, použije se rozdíl
v celkových výdajích na obyvatele.
