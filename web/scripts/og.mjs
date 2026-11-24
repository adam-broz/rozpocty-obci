// Generuje obrázky ke sdílení (Open Graph, 1200×630) pro každou obec
// do public/og/{kód}.png. Spouští se před `astro build` (npm run build).
// Obrázek se přegeneruje jen tehdy, když je JSON obce novější než PNG.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import sharp from 'sharp';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const DATA = path.join(ROOT, 'public', 'data');
const OUT = path.join(ROOT, 'public', 'og');
fs.mkdirSync(OUT, { recursive: true });

const font = (w, sub) =>
  fs.readFileSync(require.resolve(`@fontsource/source-sans-3/files/source-sans-3-${sub}-${w}-normal.woff`));
const fonts = [
  { name: 'S', data: font(400, 'latin'), weight: 400 },
  { name: 'SX', data: font(400, 'latin-ext'), weight: 400 },
  { name: 'S', data: font(700, 'latin'), weight: 700 },
  { name: 'SX', data: font(700, 'latin-ext'), weight: 700 },
];

const C = { bg: '#f7f6f2', ink: '#1c1d1f', muted: '#5a5f66', accent: '#0f5c8c', soft: '#d6e6f1', line: '#dcdad3' };
const nf0 = new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('cs-CZ', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const kc = (x) => `${nf0.format(x)} Kč`;
const pct = (x) => `${nf0.format(Math.round(x * 100))} %`;
function diffText(diff) {
  if (Math.abs(diff) < 0.05) return 'přibližně stejně jako';
  if (diff >= 1) return `${nf1.format(diff + 1).replace(',0', '')}× víc než`;
  return diff > 0 ? `o ${pct(diff)} víc než` : `o ${pct(-diff)} méně než`;
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

const meta = JSON.parse(fs.readFileSync(path.join(DATA, 'meta.json'), 'utf-8'));
const index = JSON.parse(fs.readFileSync(path.join(DATA, 'index.json'), 'utf-8'));
const catById = Object.fromEntries(meta.categories.map((c) => [c.id, c]));

// Minimalistický „h()“ pro satori (bez Reactu)
const h = (type, style, ...children) => ({ type, props: { style: { display: 'flex', ...style }, children: children.flat().filter((c) => c != null && c !== false) } });

function frame(body, footerNote) {
  return h('div', { width: 1200, height: 630, boxSizing: 'border-box', background: C.bg, color: C.ink, fontFamily: 'S, SX', flexDirection: 'column', padding: '48px 64px 40px' },
    h('div', { alignItems: 'center', gap: 14, fontSize: 30, fontWeight: 700, color: C.accent },
      h('div', { width: 36, height: 36, background: C.accent, borderRadius: 8, alignItems: 'flex-end', justifyContent: 'center', gap: 4, padding: 7 },
        h('div', { width: 5, height: 10, background: '#fff', borderRadius: 1 }),
        h('div', { width: 5, height: 16, background: '#fff', borderRadius: 1 }),
        h('div', { width: 5, height: 22, background: '#fff', borderRadius: 1 })),
      'Rozpočty obcí'),
    h('div', { flexDirection: 'column', flexGrow: 1, justifyContent: 'center' }, body),
    h('div', { fontSize: 22, color: C.muted, borderTop: `2px solid ${C.line}`, paddingTop: 18 },
      footerNote ?? 'Zdroj dat: Ministerstvo financí ČR, Monitor státní pokladny; Český statistický úřad (upraveno)'),
  );
}

function bars(value, median) {
  const max = Math.max(value, median, 1);
  const row = (label, v, color) =>
    h('div', { alignItems: 'center', gap: 16, fontSize: 24, color: C.muted },
      h('div', { width: 210 }, label),
      h('div', { width: Math.max(6, Math.round((v / max) * 620)), height: 26, background: color, borderRadius: 5 }),
      h('div', { color: C.ink, fontWeight: 700 }, kc(v)));
  return h('div', { flexDirection: 'column', gap: 10, marginTop: 20 }, row('tato obec', value, C.accent), row('podobné obce', median, '#8a9099'));
}

function obecTree(o, row) {
  const y = o.years.at(-1);
  const hl = o.highlight;
  const sub = [o.okres && o.okres !== 'Praha' ? `okres ${o.okres}` : meta.kraje[o.kraj], `${nf0.format(y.population ?? 0)} obyvatel`].join(' · ');
  const nameSize = o.name.length > 28 ? 48 : o.name.length > 18 ? 58 : 68;
  let body;
  if (!hl) {
    body = [h('div', { fontSize: 36, marginTop: 20 }, `Příjmy a výdaje obce za rok ${y.year}`)];
  } else if (hl.kind === 'pcOnly') {
    body = [
      h('div', { fontSize: 32, color: C.muted, marginTop: 26 }, `Výdaje na jednoho obyvatele v roce ${y.year}`),
      h('div', { fontSize: 84, fontWeight: 700, color: C.accent, lineHeight: 1.05 }, kc(hl.pc)),
    ];
  } else {
    const label = hl.kind === 'category' ? `${cap(catById[hl.id]?.phrase ?? '')} dává` : 'Celkové výdaje';
    body = [
      h('div', { fontSize: 30, color: C.muted, marginTop: 22 }, `${label} na obyvatele v roce ${y.year}`),
      h('div', { alignItems: 'baseline', gap: 22 },
        h('div', { fontSize: 72, fontWeight: 700, color: C.accent, lineHeight: 1.1 }, diffText(hl.diff).replace(/ (než|jako)$/, '')),
        h('div', { fontSize: 34, color: C.ink }, 'než podobné obce')),
      bars(hl.pc, hl.median),
    ];
  }
  return frame([
    h('div', { fontSize: nameSize, fontWeight: 700, lineHeight: 1.05, letterSpacing: -1 }, o.name),
    h('div', { fontSize: 28, color: C.muted, marginTop: 8 }, sub),
    ...body,
  ]);
}

async function render(tree, file) {
  const svg = await satori(tree, { width: 1200, height: 630, fonts });
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: 1200 } }).render().asPng();
  // Paletové PNG (kvantizace na 64 barev) je ~4× menší a na jednoduché grafice nepoznat.
  await sharp(png).png({ palette: true, colours: 64, effort: 4 }).toFile(file);
}

// Obrázek se přegeneruje jen tehdy, když se změnilo to, co na něm je
// (název, okres, obyvatelé, zajímavé číslo) nebo tento skript. Otisky se
// ukládají do og/.manifest.json – v GitHub Action se složka og/ cachuje.
//
// Paralelizace: hlavní proces spustí N podprocesů, každý zpracuje svůj díl
// seznamu (OG_SHARD=i/N). OG_ONLY=kód,kód vygeneruje jen vybrané obce (ladění).
const t0 = Date.now();
const shard = process.env.OG_SHARD;
const only = process.env.OG_ONLY?.split(',');
const MANIFEST = path.join(OUT, '.manifest.json');
const TODO = path.join(OUT, '.todo.json');
const { createHash } = await import('node:crypto');
const selfHash = createHash('sha1').update(fs.readFileSync(new URL(import.meta.url))).digest('hex');

function fingerprint(o) {
  const y = o.years.at(-1);
  const payload = JSON.stringify([selfHash, o.name, o.okres, o.kraj, y?.year, y?.population, o.highlight]);
  return createHash('sha1').update(payload).digest('hex').slice(0, 16);
}

if (!shard && !only) {
  await render(
    frame([
      h('div', { fontSize: 76, fontWeight: 700, lineHeight: 1.05, letterSpacing: -1 }, 'Kam jdou peníze vaší obce?'),
      h('div', { fontSize: 34, color: C.muted, marginTop: 24, maxWidth: 1000 },
        `Příjmy a výdaje všech ${nf0.format(index.length)} obcí v Česku, na obyvatele a ve srovnání s podobnými obcemi.`),
    ]),
    path.join(OUT, 'index.png'),
  );
  let manifest = {};
  try { manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf-8')); } catch {}
  const next = {};
  const todo = [];
  for (const row of index) {
    const o = JSON.parse(fs.readFileSync(path.join(DATA, 'obce', `${row[0]}.json`), 'utf-8'));
    if (!o.years.length) continue;
    const fp = fingerprint(o);
    next[row[0]] = fp;
    if (manifest[row[0]] !== fp || !fs.existsSync(path.join(OUT, `${row[0]}.png`))) todo.push(row[0]);
  }
  fs.writeFileSync(TODO, JSON.stringify(todo));
  const n = todo.length < 50 ? 1 : Math.min(8, (await import('node:os')).availableParallelism());
  const { spawn } = await import('node:child_process');
  const codes = todo.length ? await Promise.all(
    Array.from({ length: n }, (_, i) =>
      new Promise((resolve) => {
        const p = spawn(process.execPath, [new URL(import.meta.url).pathname], {
          env: { ...process.env, OG_SHARD: `${i}/${n}` },
          stdio: 'inherit',
        });
        p.on('exit', resolve);
      }),
    ),
  ) : [];
  fs.rmSync(TODO, { force: true });
  if (codes.some((c) => c !== 0)) process.exit(1);
  fs.writeFileSync(MANIFEST, JSON.stringify(next));
  console.log(`og: ${todo.length} nových/změněných obrázků, hotovo za ${((Date.now() - t0) / 1000).toFixed(0)} s`);
} else {
  const [i, n] = shard ? shard.split('/').map(Number) : [0, 1];
  const ids = only ?? JSON.parse(fs.readFileSync(TODO, 'utf-8')).filter((_, k) => k % n === i);
  const rowById = new Map(index.map((r) => [r[0], r]));
  for (const id of ids) {
    const o = JSON.parse(fs.readFileSync(path.join(DATA, 'obce', `${id}.json`), 'utf-8'));
    if (!o.years.length) continue;
    await render(obecTree(o, rowById.get(id)), path.join(OUT, `${id}.png`));
  }
}
