// Video frame tool for turning a 蓝色大肥鱼 video into references.
// Decodes with the Playwright-bundled Chromium (handles AV1/H.264 video), so no ffmpeg is needed.
//
// Usage (NODE_PATH must point at a global playwright install, e.g. NODE_PATH=$(npm root -g)):
//   node tools/video/frames.js sheet  <video> <outDir> [step=2] [cols=3] [rows=4] [cellW=640]
//   node tools/video/frames.js frames <video> <outDir> <t1,t2,...>
//   node tools/video/frames.js crop   <video> <outDir> <t1,t2,...> <x> <y> <w> <h> [scale=1]
//   node tools/video/frames.js sample <video> <t> <x,y,w,h;x,y,w,h;...>   -> prints average colors as hex
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

function serve(file) {
  const dir = path.dirname(path.resolve(file));
  const server = http.createServer((req, res) => {
    const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]));
    if (req.url === '/' || req.url === '/index.html') {
      res.writeHead(200, { 'content-type': 'text/html' });
      res.end(`<!doctype html><body style="margin:0;background:#111"><video id="v" muted preload="auto" src="/${encodeURIComponent(path.basename(file))}" style="display:none"></video><div id="g"></div></body>`);
      return;
    }
    fs.stat(p, (err, st) => {
      if (err) { res.writeHead(404); res.end(); return; }
      const range = req.headers.range;
      if (range) {
        const [s, e] = range.replace('bytes=', '').split('-');
        const start = +s, end = e ? +e : st.size - 1;
        res.writeHead(206, { 'content-range': `bytes ${start}-${end}/${st.size}`, 'accept-ranges': 'bytes', 'content-length': end - start + 1, 'content-type': 'video/mp4' });
        fs.createReadStream(p, { start, end }).pipe(res);
      } else {
        res.writeHead(200, { 'content-length': st.size, 'content-type': 'video/mp4', 'accept-ranges': 'bytes' });
        fs.createReadStream(p).pipe(res);
      }
    });
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r(server)));
}

async function open(video, viewport) {
  const server = await serve(video);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport });
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  const duration = await page.evaluate(() => new Promise(r => {
    const v = document.getElementById('v');
    if (v.readyState >= 1) r(v.duration); else v.onloadedmetadata = () => r(v.duration);
  }));
  return { server, browser, page, duration, close: async () => { await browser.close(); server.close(); } };
}

// Draws frames at the given times into canvases (optionally cropped/scaled) laid out in a grid.
async function drawFrames(page, times, { x = 0, y = 0, w = 1920, h = 1080, outW = 1920, cols = 1, label = true }) {
  const outH = Math.round(outW * h / w);
  await page.evaluate(async ({ times, x, y, w, h, outW, outH, cols, label }) => {
    const v = document.getElementById('v'), g = document.getElementById('g');
    g.innerHTML = '';
    g.style.cssText = `display:grid;grid-template-columns:repeat(${cols},${outW}px)`;
    for (const t of times) {
      await new Promise(r => { v.onseeked = r; v.currentTime = t; });
      await new Promise(r => { v.requestVideoFrameCallback(() => r()); setTimeout(r, 400); });
      const d = document.createElement('div');
      if (label) {
        const l = document.createElement('div');
        l.textContent = t.toFixed(1) + 's';
        l.style.cssText = 'color:#ff0;font:bold 16px monospace;height:22px;line-height:22px;padding-left:4px';
        d.appendChild(l);
      }
      const c = document.createElement('canvas');
      c.width = outW; c.height = outH; c.style.display = 'block';
      const ctx = c.getContext('2d');
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(v, x, y, w, h, 0, 0, outW, outH);
      d.appendChild(c); g.appendChild(d);
    }
  }, { times, x, y, w, h, outW, outH, cols, label });
}

(async () => {
  const [mode, video, ...rest] = process.argv.slice(2);
  if (!mode || !video) { console.log(fs.readFileSync(__filename, 'utf8').split('\n').slice(0, 10).join('\n')); process.exit(1); }
  if (mode === 'sheet') {
    const [outDir, step = 2, cols = 3, rows = 4, cellW = 640] = rest;
    const cw = +cellW, ch = Math.round(cw * 9 / 16) + 22;
    const s = await open(video, { width: cols * cw, height: rows * ch });
    const times = [];
    for (let t = 0.2; t <= s.duration - 0.05; t += +step) times.push(+t.toFixed(2));
    fs.mkdirSync(outDir, { recursive: true });
    const per = cols * rows, base = path.basename(video, path.extname(video));
    for (let i = 0; i * per < times.length; i++) {
      await drawFrames(s.page, times.slice(i * per, (i + 1) * per), { outW: cw, cols: +cols });
      const out = path.join(outDir, `${base}_sheet${String(i).padStart(2, '0')}.png`);
      await s.page.screenshot({ path: out, fullPage: true });
      console.log(out);
    }
    await s.close();
  } else if (mode === 'frames' || mode === 'crop') {
    const [outDir, ts, x = 0, y = 0, w = 1920, h = 1080, scale = 1] = rest;
    const outW = Math.round(+w * +scale);
    const s = await open(video, { width: outW, height: 400 });
    fs.mkdirSync(outDir, { recursive: true });
    const base = path.basename(video, path.extname(video));
    for (const t of ts.split(',').map(Number)) {
      await drawFrames(s.page, [t], { x: +x, y: +y, w: +w, h: +h, outW, label: false });
      const out = path.join(outDir, `${base}_${t.toFixed(1)}s${mode === 'crop' ? `_${x}_${y}_${w}x${h}` : ''}.png`);
      await (await s.page.$('canvas')).screenshot({ path: out });
      console.log(out);
    }
    await s.close();
  } else if (mode === 'sample') {
    const [t, regions] = rest;
    const s = await open(video, { width: 200, height: 200 });
    const rs = regions.split(';').map(r => r.split(',').map(Number));
    const out = await s.page.evaluate(async ({ t, rs }) => {
      const v = document.getElementById('v');
      await new Promise(r => { v.onseeked = r; v.currentTime = t; });
      await new Promise(r => { v.requestVideoFrameCallback(() => r()); setTimeout(r, 400); });
      const c = document.createElement('canvas'); c.width = 1920; c.height = 1080;
      const ctx = c.getContext('2d'); ctx.drawImage(v, 0, 0);
      const hex = n => Math.round(n).toString(16).padStart(2, '0');
      return rs.map(([x, y, w = 4, h = 4]) => {
        const d = ctx.getImageData(x, y, w, h).data; let r = 0, g = 0, b = 0;
        for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
        const n = d.length / 4;
        return { at: [x, y, w, h], hex: '#' + hex(r / n) + hex(g / n) + hex(b / n) };
      });
    }, { t: +t, rs });
    console.log(JSON.stringify(out));
    await s.close();
  } else {
    console.error('unknown mode', mode); process.exit(1);
  }
})().catch(e => { console.error(e); process.exit(1); });
