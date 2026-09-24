// Headless renders of tools/charkit/preview.html.
// usage: NODE_PATH=$(npm root -g) node tools/charkit/render.js out1.png "query1" [out2.png "query2" ...]
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.glb': 'model/gltf-binary',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.css': 'text/css', '.woff2': 'font/woff2' };

function serve() {
  const server = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
    fs.readFile(p, (err, data) => {
      if (err) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' });
      res.end(data);
    });
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r(server)));
}

(async () => {
  const args = process.argv.slice(2);
  const server = await serve();
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (let i = 0; i < args.length; i += 2) {
    const out = args[i];
    const query = args[i + 1];
    const qs = new URLSearchParams(query);
    const W = +(qs.get('w') || 1600), H = +(qs.get('h') || 900);
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) console.log('[page]', m.type(), m.text().slice(0, 300)); });
    page.on('pageerror', (e) => console.log('[pageerror]', e.message));
    const t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}/tools/charkit/preview.html?${query}`);
    await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 240000 });
    const err = await page.evaluate(() => window.__error);
    if (err) console.log('[error]', err);
    await page.screenshot({ path: out });
    console.log(out, ((Date.now() - t0) / 1000).toFixed(1) + 's');
    await page.close();
  }
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
