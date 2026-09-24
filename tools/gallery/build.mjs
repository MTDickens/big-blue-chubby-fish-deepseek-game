// Bundles gallery/app.js (+ vendored three.js and MToon) into gallery/dist/app.js for GitHub Pages.
// `--artifact <out.html>` also writes a single-file page (CSS and JS inlined) for a claude.ai artifact.
import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const VENDOR = {
  three: 'vendor/three/build/three.module.js',
  'three/addons/': 'vendor/three/examples/jsm/',
  '@pixiv/three-vrm-materials-mtoon': 'vendor/three-vrm-materials-mtoon/three-vrm-materials-mtoon.module.js',
};

const vendorPlugin = {
  name: 'vendor',
  setup(build) {
    build.onResolve({ filter: /^(three|@pixiv\/three-vrm-materials-mtoon)(\/.*)?$/ }, (args) => {
      for (const [spec, target] of Object.entries(VENDOR)) {
        if (spec.endsWith('/') ? args.path.startsWith(spec) : args.path === spec) {
          return { path: path.join(ROOT, target + (spec.endsWith('/') ? args.path.slice(spec.length) : '')) };
        }
      }
      return undefined;
    });
  },
};

const out = path.join(ROOT, 'gallery/dist/app.js');
await esbuild.build({
  entryPoints: [path.join(ROOT, 'gallery/app.js')],
  bundle: true,
  format: 'esm',
  minify: true,
  target: 'es2022',
  legalComments: 'eof',
  outfile: out,
  plugins: [vendorPlugin],
});
console.log('wrote', path.relative(ROOT, out), (fs.statSync(out).size / 1024).toFixed(0) + ' KB');

const i = process.argv.indexOf('--artifact');
if (i > 0) {
  const dest = process.argv[i + 1];
  let html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const css = fs.readFileSync(path.join(ROOT, 'gallery/style.css'), 'utf8');
  const js = fs.readFileSync(out, 'utf8').replace(/<\/script/gi, '<\\/script');
  html = html
    .replace('<link rel="stylesheet" href="gallery/style.css">', () => `<style>\n${css}</style>`)
    .replace('<script type="module" src="gallery/dist/app.js"></script>', () => `<script type="module">\n${js}</script>`);
  fs.writeFileSync(dest, html);
  console.log('wrote', dest, (fs.statSync(dest).size / 1024).toFixed(0) + ' KB');
}
