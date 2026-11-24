// Načítání dat vygenerovaných pipeline (web/public/data) při sestavení webu.
import fs from 'node:fs';
import path from 'node:path';

const DATA_DIR = path.resolve(process.cwd(), 'public', 'data');

export type CategoryId = string;

export interface Category {
  id: CategoryId;
  name: string;
  description: string;
  phrase: string;
}

export interface Meta {
  generated: string;
  years: number[];
  latestYear: number;
  categories: Category[];
  sizeBands: string[];
  kraje: Record<string, string>;
  minGroupSize: number;
  sources: { monitor: string; monitorLicense: string; csu: string };
}

export interface Group {
  band: number;
  scope: 'kraj' | 'cr';
  n: number;
  median: Record<string, number>;
}

export interface Year {
  year: number;
  population: number | null;
  income: { total: number | null; tax: number; nontax: number; capital: number; grants: number };
  expense: {
    total: number | null;
    current: number;
    capital: number;
    categories: Record<CategoryId, number>;
  };
  budget: {
    incomeApproved: number | null;
    incomeAmended: number | null;
    expenseApproved: number | null;
    expenseAmended: number | null;
  };
  group: Group | null;
  districtTransfers?: number;
}

export interface Highlight {
  kind: 'category' | 'total' | 'pcOnly';
  id: string;
  pc: number;
  median?: number;
  diff?: number;
}

export interface Obec {
  id: string;
  ico: string;
  name: string;
  officialName: string;
  okres: string | null;
  kraj: string;
  statutory: boolean;
  isRegion: boolean;
  years: Year[];
  highlight: Highlight | null;
  sourceUrl: string | null;
}

/** [kód, název, okres, kraj, počet obyvatel] */
export type IndexRow = [string, string, string, string, number];

function readJson<T>(rel: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, rel), 'utf-8')) as T;
}

let _meta: Meta | undefined;
export function getMeta(): Meta {
  return (_meta ??= readJson<Meta>('meta.json'));
}

let _index: IndexRow[] | undefined;
export function getIndex(): IndexRow[] {
  return (_index ??= readJson<IndexRow[]>('index.json'));
}

export function getObec(id: string): Obec {
  return readJson<Obec>(`obce/${id}.json`);
}

/** Obce se stejným názvem – pro rozlišení okresem. */
let _dup: Set<string> | undefined;
export function duplicateNames(): Set<string> {
  if (_dup) return _dup;
  const seen = new Map<string, number>();
  for (const r of getIndex()) seen.set(r[1], (seen.get(r[1]) ?? 0) + 1);
  return (_dup = new Set([...seen].filter(([, n]) => n > 1).map(([k]) => k)));
}
