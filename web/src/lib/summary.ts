// Shrnutí „Ve zkratce“ – pár vět běžnou češtinou. Věty jsou formulované
// neosobně („příjmy obce…“), aby fungovaly pro obec, město i městys
// bez skloňování podle rodu.
import type { Meta, Obec, Year } from './data';
import { kc, money, pct, groupLabel, plural } from './format';

export interface Summary {
  lines: string[];
  topCategories: { id: string; name: string; phrase: string; share: number }[];
}

export function yearDiff(a: number | null | undefined, b: number | null | undefined) {
  if (a == null || b == null || a <= 0) return null;
  return b / a - 1;
}

function changeWord(d: number) {
  if (Math.abs(d) < 0.03) return 'zůstaly zhruba stejné';
  return d > 0 ? `vzrostly o ${pct(d)}` : `klesly o ${pct(-d)}`;
}

export function buildSummary(o: Obec, meta: Meta): Summary {
  const y: Year = o.years.at(-1)!;
  const pop = y.population || 0;
  const lines: string[] = [];
  const inc = y.income.total ?? 0;
  const exp = y.expense.total ?? 0;
  const saldo = inc - exp;

  lines.push(
    `V roce ${y.year} činily příjmy ${money(inc)} a výdaje ${money(exp)}. ` +
      (Math.abs(saldo) < Math.max(exp, 1) * 0.01
        ? 'Příjmy a výdaje byly zhruba vyrovnané.'
        : saldo > 0
          ? `Rozpočet tak skončil přebytkem ${money(saldo)}.`
          : `Rozpočet tak skončil schodkem ${money(-saldo)} – rozdíl se kryje z úspor z minulých let nebo z úvěru.`),
  );

  const cats = meta.categories
    .filter((c) => c.id !== 'ostatni')
    .map((c) => ({ id: c.id, name: c.name, phrase: c.phrase, share: exp > 0 ? (y.expense.categories[c.id] ?? 0) / exp : 0 }))
    .sort((a, b) => b.share - a.share);
  const top = cats.slice(0, 3).filter((c) => c.share > 0.02);
  if (pop && exp) {
    lines.push(
      `Na jednoho obyvatele to je ${kc(exp / pop)} výdajů za rok.` +
        (top.length
          ? ` Nejvíc peněz šlo ${top.map((c) => `${c.phrase} (${pct(c.share)})`).join(', ').replace(/, ([^,]*)$/, ' a $1')}.`
          : ''),
    );
  }

  if (exp > 0) {
    const share = y.expense.capital / exp;
    lines.push(
      `Do investic – staveb, rekonstrukcí a nového majetku – šlo ${pct(share)} výdajů (${money(y.expense.capital)}).`,
    );
  }

  const g = y.group;
  if (g && !o.isRegion && pop && g.median.expense_total) {
    const d = exp / pop / g.median.expense_total - 1;
    const how = Math.abs(d) < 0.05 ? 'zhruba stejné jako' : d > 0 ? `o ${pct(d)} vyšší než` : `o ${pct(-d)} nižší než`;
    lines.push(
      `Výdaje na obyvatele jsou ${how} u podobných obcí (${groupLabel(g.band, g.scope, o.kraj)}, ${g.n} ${plural(g.n, 'obec', 'obce', 'obcí')}).`,
    );
  }

  const first = o.years[0];
  if (o.years.length >= 3 && first.year !== y.year) {
    const di = yearDiff(first.income.total, y.income.total);
    const de = yearDiff(first.expense.total, y.expense.total);
    if (di != null && de != null) {
      lines.push(`Od roku ${first.year} příjmy ${changeWord(di)} a výdaje ${changeWord(de)} (bez očištění o inflaci).`);
    }
  }

  return { lines, topCategories: top };
}
