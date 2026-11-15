// Capture the tableau scene as PNG frames with Chrome headless.
//
//   node shoot.mjs --out ../../output/tableau --frames 10,200,400     (stills: frame_<f>.png in out/)
//   node shoot.mjs --out ../../output/tableau                         (full -> out/frames/)
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1] ?? true] : null).filter(Boolean));
const out = path.resolve(args.out ?? path.join(root, 'output', 'tableau'));
mkdirSync(out, { recursive: true });

const CFG = { size: [1280, 720], fps: 24 };
const assetsBase = 'file://' + path.join(root, 'experiments', 'threejs', 'assets').replace(/\\/g, '/') + '/';

const browser = await chromium.launch({ channel: 'chrome', headless: true,
  args: ['--allow-file-access-from-files', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: CFG.size[0], height: CFG.size[1] }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.log('[pageerror]', e.message));
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
await page.goto('file://' + path.join(here, 'index.html').replace(/\\/g, '/'));
await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
const info = await page.evaluate(([c, b]) => window.init(c, b), [CFG, assetsBase]);
console.log('WebGL:', await page.evaluate(() => window.gpu()));
console.log(`frames: ${info.frames} = ${(info.frames / CFG.fps).toFixed(1)} s @ ${CFG.fps} fps`);

const shoot = async (f, file) => {
  const r = await page.evaluate(f => window.renderFrame(f), f);
  await page.screenshot({ path: file });
  return r;
};

if (args.frames) {
  for (const f of String(args.frames).split(',').map(Number)) {
    const r = await shoot(f, path.join(out, `frame_${f}.png`));
    console.log(`still frame ${f} shot=${r.shot} (render ${r.ms.toFixed(0)} ms)`);
  }
  await browser.close(); process.exit(0);
}

const framesDir = path.join(out, 'frames');
mkdirSync(framesDir, { recursive: true });
const started = Date.now();
let renderMs = 0;
for (let f = 1; f <= info.frames; f++) {
  const r = await shoot(f, path.join(framesDir, `frame_${String(f).padStart(4, '0')}.png`));
  renderMs += r.ms;
  if (f % 60 === 0 || f === info.frames) {
    const el = (Date.now() - started) / 1000;
    console.log(`frame ${f}/${info.frames}  ${el.toFixed(0)}s elapsed, ${(el / f).toFixed(2)} s/frame (render ${(renderMs / f).toFixed(1)} ms)`);
  }
}
await browser.close();
console.log('wrote', framesDir);
