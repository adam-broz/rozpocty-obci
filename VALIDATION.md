# Validace proti portálu Monitor

Cíl: ověřit, že příjmy a výdaje, které počítá pipeline z otevřených dat
(extrakt FIN 2-12 M), odpovídají číslům, která ukazuje portál
[Monitor státní pokladny](https://monitor.statnipokladna.gov.cz).

**Ověřeno:** 24. 11. 2026, ručně na stránkách *Přehled → Základní ukazatele*
(„Příjmy konsolidované“ a „Výdaje konsolidované“, řádek *Skutečnost*,
období 12. daného roku, částky v tisících Kč).

## Výsledek

| Obec | Rok | Obyvatel | Příjmy – Monitor | Příjmy – pipeline | Výdaje – Monitor | Výdaje – pipeline | Shoda |
|---|---|---:|---:|---:|---:|---:|:-:|
| [Hlavní město Praha](https://monitor.statnipokladna.gov.cz/ucetni-jednotka/00064581/prehled?rad=t&obdobi=2512) (IČO 00064581) | 2025 | 1 397 880 | 148 140 568 | 148 140 568 | 123 970 124 | 123 970 124 | ✅ |
| [Kutná Hora](https://monitor.statnipokladna.gov.cz/ucetni-jednotka/00236195/prehled?rad=t&obdobi=2512) (IČO 00236195) | 2025 | 21 642 | 882 083 | 882 083 | 855 502 | 855 502 | ✅ |
| [Kutná Hora](https://monitor.statnipokladna.gov.cz/ucetni-jednotka/00236195/prehled?rad=t&obdobi=2112) | 2021 | 20 367 | 694 956 | 694 956 | 581 885 | 581 885 | ✅ |
| [Vysoká Lhota](https://monitor.statnipokladna.gov.cz/ucetni-jednotka/00511374/prehled?rad=t&obdobi=2512) (okr. Pelhřimov, IČO 00511374) | 2025 | 16 | 971 | 971 | 633 | 633 | ✅ |

Částky v tisících Kč. Hodnoty pipeline jsou zaokrouhlené na tisíce
z přesných částek v `web/public/data/obce/{kód}.json`.

Další kontroly, které sedí:

- **Saldo Kutné Hory 2025** podle API Monitoru (`u6 – Saldo příjmů a výdajů po
  konsolidaci`) je 26 581 225,60 Kč; pipeline: 882 082 968 − 855 501 742 =
  26 581 226 Kč (rozdíl jen zaokrouhlením na celé koruny).
- **Běžné výdaje na obyvatele** Kutné Hory 2025 podle Monitoru 31 962,92 Kč ×
  21 642 obyvatel = 691,74 mil. Kč; pipeline: běžné výdaje 691 741 556 Kč.
- **Počet obyvatel**: Monitor uvádí pro rok 2025 21 642 obyvatel, stejně jako
  ČSÚ k 1. 1. 2025 (datová sada OBY02A), kterou používá pipeline.

## Jak se počítá (a proč to sedí)

1. Z extraktu FIN 2-12 M se berou tabulky příjmů (`ZC_VTAB = 000100`) a výdajů
   (`000200`), sloupec `ZU_ROZKZ` (skutečnost od počátku roku k 31. 12.).
2. Příjmy = položky tříd 1–4, výdaje = třídy 5–6. Třída 8 (financování: úvěry,
   splátky jistin, změna stavu účtů) se nepočítá.
3. Vyloučí se **konsolidační položky** – v číselníku položek mají příznak
   `kon_pol = true`. Jde o převody mezi vlastními účty a fondy obce (4134/5345,
   4133/5344, 4138/5348, 4139/5349, 5342) a převody mezi statutárním městem
   a jeho obvody (4137/5347, 4251/6363).

Bez kroku 3 by Kutná Hora v roce 2025 měla „příjmy“ 2,69 mld. Kč místo
0,88 mld. Kč – převody mezi vlastními účty (4134/5345) tam dosahují 1,7 mld. Kč.

## Jak validaci zopakovat

```bash
uv run python -m pipeline
uv run pytest tests/test_municipalities.py -v
```

Testy porovnávají výstup s hodnotami z tabulky výše. Pro jiný rok nebo obec
otevřete na Monitoru stránku `…/ucetni-jednotka/{IČO}/prehled?rad=t&obdobi={RR}12`
a doplňte řádek do `MONITOR` v `tests/test_municipalities.py`.
