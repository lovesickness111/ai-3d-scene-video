// Turn a conversation + its TTS audio into frames with the three.js scene, headless.
// Schedules the turns like qa_scene.py (camera moves in the silence between turns),
// derives the mouth levels from the wavs, hands everything to the page and screenshots
// every frame into <out>/frames; make_video.py then lays the voices under them.
//
//   npm run build
//   node shoot.mjs --conversation ../../conversation_decision_apps.json --out ../../output/decision_apps --frames 40,300,700
//   node shoot.mjs --conversation ../../conversation_decision_apps.json --out ../../output/decision_apps
import { chromium } from 'playwright-core';
import { mkdirSync, readFileSync, writeFileSync, readdirSync, unlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1] ?? true] : null).filter(Boolean));
const fps = +(args.fps ?? 12), move = +(args.move ?? .65);
const out = path.resolve(here, args.out ?? '../../output/decision_apps');
const conversation = JSON.parse(readFileSync(path.resolve(here, args.conversation ?? '../../conversation_decision_apps.json'), 'utf8'));
const audio = JSON.parse(readFileSync(path.join(out, 'audio', 'audio.json'), 'utf8'));

// ---- mouth levels, as qa_scene.mouth_levels: closed in silence, open on frames louder than the half second around them ----
function wavSamples(file) {
  const buf = readFileSync(file);
  let pos = 12, rate = 44100, data = null;
  while (pos + 8 <= buf.length) {
    const id = buf.toString('ascii', pos, pos + 4), size = buf.readUInt32LE(pos + 4);
    if (id === 'fmt ') rate = buf.readUInt32LE(pos + 12);
    if (id === 'data') { data = buf.subarray(pos + 8, pos + 8 + size); break; }
    pos += 8 + size + (size & 1);
  }
  const n = data.length >> 1, samples = new Float32Array(n);
  for (let i = 0; i < n; i++) samples[i] = Math.abs(data.readInt16LE(i * 2));
  return { samples, rate };
}
function mouthLevels(file) {
  const { samples, rate } = wavSamples(file);
  const hop = Math.floor(rate / 100), count = Math.floor(samples.length / hop);
  const level = new Float32Array(count);
  for (let i = 0; i < count; i++) { let s = 0; for (let j = 0; j < hop; j++) s += samples[i * hop + j]; level[i] = s / hop; }
  const sorted = Float32Array.from(level).sort(), p95 = sorted[Math.min(count - 1, Math.floor(.95 * (count - 1)))] || 1;
  for (let i = 0; i < count; i++) level[i] /= p95;
  const mean = (a, b) => { const i0 = Math.max(0, Math.round(a * 100)), i1 = Math.max(i0 + 1, Math.round(b * 100)); if (i0 >= count) return 0; let s = 0, n = 0; for (let i = i0; i < Math.min(i1, count); i++) { s += level[i]; n++; } return n ? s / n : 0; };
  const levels = [];
  for (let k = 0; k < Math.ceil(count / 100 * fps); k++) {
    const now = mean(k / fps, (k + 1) / fps), around = mean(k / fps - .17, k / fps + .25);
    levels.push(now < .08 ? 'closed' : now >= around ? 'open' : 'half');
  }
  return levels;
}

// ---- schedule, as qa_scene.schedule ----
let frame = 1, prev = null;
const turns = conversation.map((turn, i) => {
  const a = audio[String(i)];
  if (!a) throw new Error(`audio.json has no turn ${i}: run tts.py first`);
  const shot = `${turn.speaker}_${turn.illustration ? 'explain' : 'talk'}`;
  const frame_start = frame;
  const voice_frame = frame + (prev && prev !== shot ? Math.round(move * fps) : 0);
  const frame_end = voice_frame + Math.ceil((a.seconds + .25) * fps) - 1;
  frame = frame_end + 1; prev = shot;
  return { ...turn, shot, frame_start, voice_frame, frame_end, seconds: a.seconds, cues: a.cues, beats: a.beats,
           mouth: mouthLevels(path.join(out, 'audio', `turn_${String(i).padStart(2, '0')}.wav`)) };
});
const last = turns[turns.length - 1].frame_end;
writeFileSync(path.join(out, 'timeline.json'), JSON.stringify(turns.map(({ mouth, ...t }) => t), null, 2));
console.log(`${turns.length} turns, ${last} frames = ${(last / fps).toFixed(1)} s`);

const only = args.frames ? String(args.frames).split(',').map(Number) : null;
const framesDir = path.join(out, 'frames');
mkdirSync(framesDir, { recursive: true });
if (!only) for (const f of readdirSync(framesDir)) if (/^frame_\d{4}\.png$/.test(f) && +f.slice(6, 10) > last) unlinkSync(path.join(framesDir, f));

const browser = await chromium.launch({ channel: 'chrome', headless: true,
  args: ['--allow-file-access-from-files',  // GLTFLoader fetches the .glb files next to index.html
         ...(args.gpu ? ['--ignore-gpu-blocklist', '--enable-gpu'] : ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.log('[pageerror]', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('[page]', m.text()); });
await page.goto('file://' + path.join(here, 'index.html').replace(/\\/g, '/'));
await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
console.log('WebGL:', await page.evaluate(() => window.gpu()));
// --assets <json>: ready-made glTF models to place in the room (paths relative to assets/).
// Default: assets/dev_casual.json, the Quaternius character who plays the dev; --assets none for the built dev.
const assetsSpec = args.assets ?? 'assets/dev_casual.json';
if (assetsSpec !== 'none') {
  const spec = JSON.parse(readFileSync(path.resolve(here, assetsSpec), 'utf8'));
  for (const a of spec) { a.url = 'assets/' + a.file; if (a.animations) a.animations = 'assets/' + a.animations; }
  for (const r of await page.evaluate(s => window.loadAssets(s), spec)) console.log('asset', JSON.stringify(r));
}
const info = await page.evaluate(t => window.init(t), { fps, move, turns });
console.log('shots:', JSON.stringify(info.shots));

if (args.title) {  // --title [json opts]: the title card (characters on the 2D backdrop + text) into <out>/thumbnail.png
  await page.evaluate(o => window.renderTitle(o), args.title === true ? {} : JSON.parse(args.title));
  await page.screenshot({ path: path.join(out, 'thumbnail.png') });
  await browser.close();
  console.log('wrote', path.join(out, 'thumbnail.png'));
  process.exit(0);
}
if (args.still) {  // --still wide[,dev_side...]: one still per named shot into <out>/still_<shot>.png, nothing else
  const f = +(args.frame ?? 1);
  for (const shot of String(args.still).split(',')) {
    const name = `still_${shot}${args.frame ? '_' + f : ''}.png`;
    await page.evaluate(([s, f, l]) => window.renderStill(s, f, l), [shot, f, +(args.look ?? 0)]);  // --look 1: the dev faces the boss
    await page.screenshot({ path: path.join(out, name) });
    console.log('wrote', path.join(out, name));
  }
  await browser.close();
  process.exit(0);
}
const started = Date.now();
let n = 0, renderMs = 0;
for (const f of only ?? Array.from({ length: last }, (_, i) => i + 1)) {
  const r = await page.evaluate(f => window.renderFrame(f), f);
  await page.screenshot({ path: path.join(framesDir, `frame_${String(f).padStart(4, '0')}.png`) });
  n++; renderMs += r.ms;
  if (only || n % 100 === 0 || n === last) {
    const el = (Date.now() - started) / 1000;
    console.log(`frame ${f}/${last}  ${el.toFixed(0)}s elapsed, ${(el / n).toFixed(2)} s/frame (render ${(renderMs / n).toFixed(1)} ms)`);
  }
}
await browser.close();
console.log('wrote', framesDir);
