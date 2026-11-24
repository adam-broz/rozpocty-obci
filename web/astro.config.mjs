// @ts-check
import { defineConfig } from 'astro/config';

// Na GitHub Pages běží web pod https://<uživatel>.github.io/<repo>/.
// SITE_URL a BASE_PATH nastavuje GitHub Action; lokálně platí výchozí hodnoty.
export default defineConfig({
  site: process.env.SITE_URL || 'http://localhost:4321',
  base: process.env.BASE_PATH || '/rozpocty-obci',
  trailingSlash: 'ignore',
  build: { format: 'directory', concurrency: 4 },
  compressHTML: true,
  scopedStyleStrategy: 'class',
});
