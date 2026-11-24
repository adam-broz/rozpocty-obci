// Věta se „zajímavým číslem“ pro stránku obce a OG obrázek.
import type { Meta, Obec } from './data';
import { kc, diffText } from './format';

export interface HighlightParts {
  /** hlavní číslo, např. „o 85 % víc“ nebo „12 345 Kč“ */
  big: string;
  /** celá věta */
  sentence: string;
}

export function highlightParts(o: Obec, meta: Meta): HighlightParts | null {
  const h = o.highlight;
  if (!h) return null;
  if (h.kind === 'pcOnly') {
    return {
      big: kc(h.pc),
      sentence: `Na jednoho obyvatele připadlo v roce ${meta.latestYear} ${kc(h.pc)} výdajů.`,
    };
  }
  if (h.diff == null || h.median == null) return null;
  const verb = h.kind === 'category'
    ? `dává ${meta.categories.find((c) => c.id === h.id)?.phrase ?? ''}`
    : 'utrácí celkem';
  const cmp = diffText(h.diff);
  const big = cmp.replace(/ než$/, '').replace(/ jako$/, '');
  return {
    big,
    sentence: `${o.name} ${verb} ${kc(h.pc)} na obyvatele – ${cmp} podobné obce (${kc(h.median)}).`,
  };
}

export const highlightSentence = (o: Obec, meta: Meta) => highlightParts(o, meta)?.sentence ?? null;
