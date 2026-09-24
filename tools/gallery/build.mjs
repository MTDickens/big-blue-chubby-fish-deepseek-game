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

// The artifact host supplies the document skeleton, so keep only the title, font link, styles and body content.
const i = process.argv.indexOf('--artifact');
if (i > 0) {
  const dest = process.argv[i + 1];
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const css = fs.readFileSync(path.join(ROOT, 'gallery/style.css'), 'utf8');
  const js = fs.readFileSync(out, 'utf8').replace(/<\/script/gi, '<\\/script');
  const title = html.match(/<title>[\s\S]*?<\/title>/)[0];
  const fonts = html.match(/<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/)[0];
  const body = html.match(/<body[^>]*>([\s\S]*)<\/body>/)[1]
    .replace('<script type="module" src="gallery/dist/app.js"></script>',
      () => `<script>window.GALLERY_NO_DOWNLOAD = true; window.GALLERY_GLB_JSON = true;</script>\n<script type="module">\n${js}</script>`);
  fs.writeFileSync(dest, `${title}\n${fonts}\n<style>\n${css}</style>\n${body}`);
  console.log('wrote', dest, (fs.statSync(dest).size / 1024).toFixed(0) + ' KB');
  // artifacts serve JSON but not .glb, so each model travels as {"glb": "<base64>"} next to the page
  const dir = path.join(path.dirname(dest), 'assets/characters');
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(path.join(ROOT, 'assets/characters')).filter((n) => n.endsWith('.glb'))) {
    const b64 = fs.readFileSync(path.join(ROOT, 'assets/characters', f)).toString('base64');
    fs.writeFileSync(path.join(dir, `${f}.json`), JSON.stringify({ glb: b64 }));
  }
  console.log('wrote', dir, '*.glb.json');
}
