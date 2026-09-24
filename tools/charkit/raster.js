// Rasterize charkit SVG textures to PNG (transparent background) with headless Chromium.
// usage: NODE_PATH=$(npm root -g) node tools/charkit/raster.js [file.svg ...]   (default: all in textures/)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = path.join(__dirname, 'textures');
  const files = process.argv.slice(2).length ? process.argv.slice(2) : fs.readdirSync(dir).filter((f) => f.endsWith('.svg')).map((f) => path.join(dir, f));
  const browser = await chromium.launch();
  for (const f of files) {
    const svg = fs.readFileSync(f, 'utf8');
    const w = +(svg.match(/width="(\d+)"/) || [])[1] || 1024;
    const h = +(svg.match(/height="(\d+)"/) || [])[1] || 1024;
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    await page.evaluate(() => document.fonts.ready);
    const out = f.replace(/\.svg$/, '.png');
    await page.screenshot({ path: out, omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
    console.log(out, `${w}x${h}`, Math.round(fs.statSync(out).size / 1024) + 'KB');
    await page.close();
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
