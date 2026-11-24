// Formátování čísel a české texty. Sdílené webem i generátorem OG obrázků
// (scripts/og.mjs má vlastní kopii několika funkcí, aby nepotřeboval TS).

const nf0 = new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 1, minimumFractionDigits: 1 });

/** 1 234 567 */
export const num = (x: number | null | undefined) => (x == null ? '–' : nf0.format(x));

/** Kč na obyvatele: „12 345 Kč“ */
export const kc = (x: number | null | undefined) => (x == null ? '–' : `${nf0.format(x)} Kč`);

/** Velké částky: „882,1 mil. Kč“, „1,2 mld. Kč“, „950 tis. Kč“ */
export function money(x: number | null | undefined): string {
  if (x == null) return '–';
  const a = Math.abs(x);
  if (a >= 1e9) return `${nf1.format(x / 1e9)} mld. Kč`;
  if (a >= 1e6) return `${nf1.format(x / 1e6)} mil. Kč`;
  if (a >= 1e4) return `${nf0.format(x / 1e3)} tis. Kč`;
  return `${nf0.format(x)} Kč`;
}

/** Krátký popisek osy: „800 mil.“ */
export function moneyShort(x: number): string {
  const a = Math.abs(x);
  if (a >= 1e9) return `${nf1.format(x / 1e9).replace(',0', '')} mld.`;
  if (a >= 1e6) return `${nf0.format(x / 1e6)} mil.`;
  if (a >= 1e3) return `${nf0.format(x / 1e3)} tis.`;
  return nf0.format(x);
}

export const pct = (x: number) => `${nf0.format(Math.round(x * 100))} %`;

/** Rozdíl proti mediánu: „o 85 % víc“, „2,3× víc“, „o 40 % méně“, „přibližně stejně“ */
export function diffText(diff: number): string {
  if (Math.abs(diff) < 0.05) return 'přibližně stejně jako';
  if (diff >= 1) return `${nf1.format(diff + 1).replace(',0', '')}× víc než`;
  return diff > 0 ? `o ${pct(diff)} víc než` : `o ${pct(-diff)} méně než`;
}

/** Totéž bez „než“ – pro tabulky. */
export function diffShort(diff: number | null): string {
  if (diff == null || !isFinite(diff)) return '–';
  if (Math.abs(diff) < 0.05) return 'stejně';
  if (diff >= 1) return `${nf1.format(diff + 1).replace(',0', '')}× víc`;
  return diff > 0 ? `+${pct(diff)}` : `−${pct(-diff)}`;
}

/** Skloňování: 1 obec, 2 obce, 5 obcí */
export function plural(n: number, one: string, few: string, many: string) {
  if (n === 1) return one;
  if (n >= 2 && n <= 4) return few;
  return many;
}

/** Kraj v 6. pádě: „ve Středočeském kraji“ */
export const KRAJ_LOC: Record<string, string> = {
  CZ010: 'v Praze',
  CZ020: 've Středočeském kraji',
  CZ031: 'v Jihočeském kraji',
  CZ032: 'v Plzeňském kraji',
  CZ041: 'v Karlovarském kraji',
  CZ042: 'v Ústeckém kraji',
  CZ051: 'v Libereckém kraji',
  CZ052: 'v Královéhradeckém kraji',
  CZ053: 'v Pardubickém kraji',
  CZ063: 'v Kraji Vysočina',
  CZ064: 'v Jihomoravském kraji',
  CZ071: 'v Olomouckém kraji',
  CZ072: 've Zlínském kraji',
  CZ080: 'v Moravskoslezském kraji',
};

/** Velikostní kategorie jako fráze: „obce s 201–500 obyvateli“ */
export const BAND_PHRASE = [
  'obce do 100 obyvatel',
  'obce se 101–200 obyvateli',
  'obce s 201–500 obyvateli',
  'obce s 501–1 000 obyvateli',
  'obce s 1 001–2 000 obyvateli',
  'obce a města s 2 001–5 000 obyvateli',
  'města s 5 001–10 000 obyvateli',
  'města s 10 001–20 000 obyvateli',
  'města s 20 001–50 000 obyvateli',
  'města s 50 001–100 000 obyvateli',
  'města nad 100 000 obyvatel',
];

export function groupLabel(band: number, scope: 'kraj' | 'cr', kraj: string) {
  return `${BAND_PHRASE[band]} ${scope === 'kraj' ? KRAJ_LOC[kraj] ?? '' : 'v celé ČR'}`.trim();
}

/** Odstraní diakritiku a převede na malá písmena (pro vyhledávání). */
export const fold = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
