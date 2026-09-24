// Headless screenshots of the gallery page (index.html) for QA.
// usage: NODE_PATH=$(npm root -g) node tools/gallery/shot.js out.png "<hash>" [WxH] [out2.png "<hash2>" [WxH]] ...
//   e.g.  node tools/gallery/shot.js solo.png "m=solo&c=bluefish&still=1" 1600x900
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.css': 'text/css' };

function serve() {
  const server = http.createServer((req, res) => {
    let p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (p.endsWith('/')) p += 'index.html';
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
  const jobs = [];
  for (let i = 0; i < args.length;) {
    const job = { out: args[i], hash: args[i + 1], size: '1600x900' };
    i += 2;
    if (args[i] && /^\d+x\d+$/.test(args[i])) job.size = args[i++];
    jobs.push(job);
  }
  const server = await serve();
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  let failures = 0;
  for (const job of jobs) {
    const [W, H] = job.size.split('x').map(Number);
    const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type()) && !m.text().includes('ERR_CERT_AUTHORITY_INVALID')) { failures += m.type() === 'error'; console.log('[page]', m.type(), m.text().slice(0, 300)); } });
    page.on('pageerror', (e) => { failures++; console.log('[pageerror]', e.message); });
    page.on('requestfailed', (r) => { if (!r.url().includes('fonts.g')) console.log('[requestfailed]', r.url()); });
    const t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}/index.html#${job.hash}`);
    await page.waitForFunction(() => window.__ready === true, null, { timeout: 300000 });
    await page.waitForTimeout(400);
    await page.screenshot({ path: job.out });
    console.log(job.out, ((Date.now() - t0) / 1000).toFixed(1) + 's');
    await page.close();
  }
  await browser.close();
  server.close();
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
