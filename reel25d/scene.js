// reel25d: a 2.5D cut-out meme reel in three.js. One photo as a far background plane, PNG cut-outs as
// upright billboards and blocky "Roblox-style" characters built from rounded boxes, all placed in metres on
// a floor at y = 0. The camera cuts between named shots (optionally drifting for parallax); every frame is a
// pure function of the frame number: window.init(director) then window.renderFrame(f).
//
// Director format: see ../director/*.json and README.md next to this file.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

const $ = id => document.getElementById(id);
const deg = d => d * Math.PI / 180;
const lerp = (a, b, u) => a + (b - a) * u;
const lerp3 = (a, b, u) => [lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
const clamp01 = x => Math.min(1, Math.max(0, x));
const EASE = {
  linear: u => u,
  inout: u => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2,
  out: u => 1 - Math.pow(1 - u, 3),
  in: u => u * u * u,
  back: u => { const c = 1.7, d = c + 1; return 1 + d * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); },  // overshoot
};

let renderer, scene, camera, D, W, H, FPS, BASE, bgPlane;
const actors = {};        // name -> { spec, kind, obj, parts, w, h }
const textures = {};      // url -> Texture
let beats = [];           // resolved by shoot.mjs: [{t, shot, caption, set, anim, overlay, ...}]
let shadowTex;

// ---------- loading ----------
const loader = new THREE.TextureLoader();
async function tex(file) {
  const url = BASE + file;
  if (!textures[url]) {
    const t = await loader.loadAsync(url);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    textures[url] = t;
  }
  return textures[url];
}

function shadowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'), r = g.createRadialGradient(64, 64, 10, 64, 64, 64);
  r.addColorStop(0, 'rgba(0,0,0,.55)'); r.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
function contactShadow(width) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(width, width * .45),
    new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = .01; m.renderOrder = -1;
  return m;
}

// ---------- actors ----------
// sprite: a PNG cut-out standing on the floor (bottom-centre pivot), always turned to face the camera
async function makeSprite(spec) {
  const t = await tex(spec.file);
  const h = spec.height ?? 1, w = h * t.image.width / t.image.height;
  const mat = new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: .06, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  mesh.position.y = h / 2;
  const pivot = new THREE.Group(); pivot.add(mesh);  // roll/scale happen here, about the sprite centre
  pivot.position.y = 0;
  const obj = new THREE.Group(); obj.add(pivot);
  if (spec.shadow !== false && !spec.attachOnly) obj.add(contactShadow(w * .9));
  return { kind: 'sprite', obj, parts: { pivot, mesh, mat }, w, h };
}

// blocky: R6-style figure, 5 units tall (legs 2, torso 2, head 1); unit = height / 5. Faces +z at yaw 0.
async function makeBlocky(spec) {
  const u = (spec.height ?? 1.75) / 5;
  const col = c => new THREE.Color(c);
  const mat = (c, r = .5) => new THREE.MeshStandardMaterial({ color: col(c), roughness: r, metalness: .05 });
  const body = mat(spec.color ?? '#f2c21b', .45), limb = mat(spec.limbColor ?? spec.color ?? '#f2c21b', .5);
  const box = (w, h, d, m, r = .09) => new THREE.Mesh(new RoundedBoxGeometry(w * u, h * u, d * u, 3, r * u), m);
  const obj = new THREE.Group();
  const parts = {};
  // legs hang from hip pivots at y = 2u
  for (const [name, x] of [['legL', -.5], ['legR', .5]]) {
    const p = new THREE.Group(); p.position.set(x * u, 2 * u, 0);
    const m = box(.96, 2, .96, limb); m.position.y = -1 * u; p.add(m); obj.add(p); parts[name] = p;
  }
  const upper = new THREE.Group(); upper.position.y = 2 * u; obj.add(upper); parts.upper = upper;
  const torso = box(2, 2, 1, body); torso.position.y = 1 * u; upper.add(torso); parts.torso = torso;
  for (const [name, x] of [['armL', -1.5], ['armR', 1.5]]) {
    const p = new THREE.Group(); p.position.set(x * u, 2 * u, 0);
    const m = box(.96, 2, .96, limb); m.position.y = -1 * u; p.add(m); upper.add(p); parts[name] = p;
  }
  const headG = new THREE.Group(); headG.position.y = 2.5 * u + .05 * u; upper.add(headG); parts.head = headG;
  const head = box(1.2, 1.05, 1.1, body, .22); headG.add(head);
  // face: a texture on the front of the head, switchable. spec.faces = {key: file | {file, size:[w,h], y}}
  // (size in head units; default fills the part of the head below a hat brim)
  if (spec.faces) {
    const fm = new THREE.MeshBasicMaterial({ transparent: true, alphaTest: .05 });
    const face = new THREE.Mesh(new THREE.PlaneGeometry(u, u), fm);
    face.position.set(0, 0, .56 * u); headG.add(face);
    parts.face = face; parts.faceMaps = {}; parts.faceGeo = {};
    for (const [k, f] of Object.entries(spec.faces)) {
      const o = typeof f === 'string' ? { file: f } : f;
      parts.faceMaps[k] = await tex(o.file);
      parts.faceGeo[k] = { size: o.size ?? spec.faceSize ?? [1.1, .62], y: o.y ?? spec.faceY ?? -.18, z: o.z ?? 0 };
    }
    fm.map = parts.faceMaps[spec.face ?? Object.keys(spec.faces)[0]]; fm.needsUpdate = true;
  }
  if (spec.hat === 'bucket') {  // crown + sloping brim, charcoal
    const hm = mat('#2a2a2e', .7);
    const crown = new THREE.Mesh(new THREE.CylinderGeometry(.62 * u, .68 * u, .55 * u, 28), hm); crown.position.y = .72 * u;
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(.70 * u, 1.05 * u, .22 * u, 28), hm); brim.position.y = .40 * u;
    headG.add(crown, brim);
  } else if (spec.hat === 'beanie') {
    const hm = mat(spec.hatColor ?? '#1b1b1f', .8);
    const dome = new THREE.Mesh(new THREE.SphereGeometry(.72 * u, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2), hm); dome.position.y = .35 * u;
    const band = new THREE.Mesh(new THREE.CylinderGeometry(.74 * u, .74 * u, .28 * u, 28), hm); band.position.y = .32 * u;
    headG.add(dome, band);
  } else if (spec.hat === 'bandana') {  // red cap over a block of black hair
    const hair = box(1.3, .9, 1.25, mat('#111114', .9), .12); hair.position.y = .22 * u; headG.add(hair);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(.74 * u, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2.2), mat(spec.hatColor ?? '#d62828', .6));
    cap.position.y = .32 * u; headG.add(cap);
    const knot = box(.5, .25, .35, mat(spec.hatColor ?? '#d62828', .6), .08); knot.position.set(.55 * u, .55 * u, -.55 * u); headG.add(knot);
  }
  obj.add(contactShadow(2.6 * u));
  return { kind: 'blocky', obj, parts, w: 4 * u, h: 5 * u, u };
}

// pack: a soft rounded block with straps — parachute bag or school backpack. Pivot at the bottom.
async function makePack(spec) {
  const w = spec.width ?? .55, h = spec.height ?? .7, d = spec.depth ?? .4;
  const g = new THREE.Group();
  const main = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, Math.min(w, h, d) * .28),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(spec.color ?? '#5b6b3a'), roughness: .85 }));
  main.position.y = h / 2; g.add(main);
  const pocket = new THREE.Mesh(new RoundedBoxGeometry(w * .62, h * .42, d * .35, 3, d * .1),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(spec.color ?? '#5b6b3a').multiplyScalar(.8), roughness: .85 }));
  pocket.position.set(0, h * .38, d / 2 + d * .1); g.add(pocket);
  const sm = new THREE.MeshStandardMaterial({ color: new THREE.Color(spec.strapColor ?? '#e3c23a'), roughness: .7 });
  for (const x of [-w * .28, w * .28]) {
    const s = new THREE.Mesh(new THREE.BoxGeometry(w * .12, h * .92, d * 1.08), sm); s.position.set(x, h / 2, 0); g.add(s);
  }
  const obj = new THREE.Group(); obj.add(g);
  if (spec.shadow !== false) obj.add(contactShadow(w * 1.6));
  return { kind: 'pack', obj, parts: { g }, w, h };
}

const BUILD = { sprite: makeSprite, blocky: makeBlocky, pack: makePack };

// ---------- scene ----------
async function buildScene() {
  scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x8a8678, D.light?.hemi ?? 1.1));
  const sun = new THREE.DirectionalLight(0xffffff, D.light?.sun ?? 1.7);
  sun.position.set(...(D.light?.sunPos ?? [4, 9, 7])); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, D.light?.fill ?? .5); fill.position.set(-5, 3, 6); scene.add(fill);

  // background: a 2D layer riding on the camera, always covering the frame; each shot crops it with
  // bg.zoom / bg.pan, and a drifting camera slides it a little (parallax) — the cut-out collage look
  const bt = await tex(D.background.file);
  bgPlane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: bt, depthWrite: false }));
  bgPlane.renderOrder = -10;
  bgPlane.userData.aspect = bt.image.width / bt.image.height;
  camera.add(bgPlane);
  scene.add(camera);

  shadowTex = shadowTexture();
  for (const [name, spec] of Object.entries(D.actors)) {
    const a = await BUILD[spec.type](spec);
    a.spec = spec; a.name = name; a.obj.visible = false;
    scene.add(a.obj); actors[name] = a;
  }
}

// ---------- state per frame ----------
function defaultState(name) {
  const s = actors[name].spec;
  return { at: s.at ? [...s.at] : [0, 0, 0], yaw: s.yaw ?? 0, roll: 0, pitch: 0, scale: 1, visible: !!s.at,
           attach: null, face: s.face ?? null, faceScale: 1, lean: 0, arms: [0, 0], legs: [0, 0], opacity: 1, flip: false };
}

function stateAt(time) {
  const st = {}; for (const n in actors) st[n] = defaultState(n);
  let shot = null, shotStart = 0, caption = null, overlay = 0, watermark = D.watermark ?? null;
  for (const b of beats) {
    if (b.t > time) break;
    if (b.shot) { shot = b.shot; shotStart = b.t; }
    if ('caption' in b) caption = b.caption;
    if ('overlay' in b) overlay = b.overlay;
    if ('watermark' in b) watermark = b.watermark;
    for (const [n, props] of Object.entries(b.set ?? {})) {
      const s = st[n]; if (!s) throw new Error(`set: unknown actor ${n}`);
      if ('at' in props) { s.at = [...props.at]; s.visible = true; }
      if ('visible' in props) s.visible = props.visible;
      for (const k of ['yaw', 'roll', 'pitch', 'scale', 'face', 'faceScale', 'lean', 'opacity', 'flip']) if (k in props) s[k] = props[k];
      if ('arms' in props) s.arms = Array.isArray(props.arms) ? props.arms : [props.arms, props.arms];
      if ('attach' in props) s.attach = props.attach;   // {to, offset:[x,y,z], yaw?} or null
    }
    for (const an of b.anim ?? []) applyAnim(st, an, time - (b.t + (an.delay ?? 0)));
  }
  return { st, shot, shotStart, caption, overlay, watermark };
}

function applyAnim(st, an, local) {
  if (local < 0) return;
  const dur = an.dur ?? 1, u = clamp01(local / dur), e = EASE[an.ease ?? 'inout'](u);
  const s = st[an.actor]; if (!s) throw new Error(`anim: unknown actor ${an.actor}`);
  switch (an.type) {
    case 'move': {
      s.visible = true;
      s.at = lerp3(s.at, an.to, e);
      if (an.walk && u < 1) { const w = Math.sin(local * 2 * Math.PI * (an.stride ?? 2.2)); s.legs = [w * 28, -w * 28]; s.arms = [-w * 22, w * 22]; }
      break;
    }
    case 'turn': s.yaw = lerp(s.yaw, an.to, e); break;
    case 'jump': {  // ballistic flight from the current spot; v in m/s, spins while flying, hidden at the end
      const t = Math.min(local, dur), v = an.v ?? [0, 3, -5], g = an.g ?? 9.8;
      s.at = [s.at[0] + v[0] * t, s.at[1] + v[1] * t - .5 * g * t * t, s.at[2] + v[2] * t];
      if (an.spin) s[an.axis === 'x' ? 'pitch' : 'roll'] += an.spin * t;
      if (an.lean) s.lean = an.lean * Math.min(1, t / .25);
      if (u >= 1 && an.hide !== false) s.visible = false;
      break;
    }
    case 'pop': { s.visible = true; s.scale = lerp(an.from ?? 2.5, an.to ?? 1, EASE[an.ease ?? 'back'](u)); break; }
    case 'facepop': s.faceScale = lerp(an.from ?? 2.5, an.to ?? 1, EASE[an.ease ?? 'back'](u)); break;
    case 'scale': s.scale = lerp(s.scale, an.to ?? 1, e); break;
    case 'bend': s.lean = an.back ? an.to * Math.sin(Math.PI * u) : lerp(s.lean, an.to, e); break;
    case 'arms': { const v = an.back ? an.to * Math.sin(Math.PI * u) : lerp(s.arms[0], an.to, e); s.arms = [an.left === false ? s.arms[0] : v, an.right === false ? s.arms[1] : v]; break; }
    case 'shake': { const k = an.amp ?? .04, f = an.freq ?? 9; s.at = [s.at[0] + k * Math.sin(local * 2 * Math.PI * f) * (1 - u), s.at[1], s.at[2]]; break; }
    case 'nod': s.pitch = (an.amp ?? 12) * Math.sin(Math.PI * u); break;
    case 'fade': s.opacity = lerp(an.from ?? 1, an.to ?? 0, e); if (u >= 1 && an.to === 0) s.visible = false; break;
    case 'hide': if (u >= 1) s.visible = false; break;
    case 'show': s.visible = true; break;
    default: throw new Error(`anim: unknown type ${an.type}`);
  }
}

// ---------- apply state to the scene graph ----------
const _v = new THREE.Vector3();
function placeActor(name, s, st, cam) {
  const a = actors[name], o = a.obj;
  o.visible = s.visible;
  if (!s.visible) return;
  let yaw = s.yaw;
  if (s.attach) {  // ride on another actor: world position of an offset in the parent's frame
    const p = actors[s.attach.to], ps = st[s.attach.to];
    o.visible = ps.visible; if (!o.visible) return;
    _v.set(...(s.attach.offset ?? [0, 0, 0]));
    p.obj.updateMatrixWorld(true);
    (s.attach.part && p.parts[s.attach.part] ? p.parts[s.attach.part] : p.obj).localToWorld(_v);
    o.position.copy(_v);
    yaw = ps.yaw + (s.attach.yaw ?? 0);
    o.rotation.set(deg(ps.pitch), deg(yaw), deg(ps.roll), 'YXZ');
  } else {
    o.position.set(...s.at);
    if (a.kind === 'sprite') yaw = Math.atan2(cam.position.x - s.at[0], cam.position.z - s.at[2]) * 180 / Math.PI;  // billboard
    o.rotation.set(deg(s.pitch), deg(yaw), deg(s.roll), 'YXZ');
  }
  o.scale.setScalar(s.scale * (s.flip ? 1 : 1));
  if (a.kind === 'sprite') {
    a.parts.mesh.scale.x = s.flip ? -1 : 1;
    a.parts.mat.opacity = s.opacity; a.parts.mat.transparent = true;
  }
  if (a.kind === 'blocky') {
    const P = a.parts;
    P.upper.rotation.x = deg(s.lean);
    P.armL.rotation.x = deg(-s.arms[0]); P.armR.rotation.x = deg(-s.arms[1]);
    P.legL.rotation.x = deg(s.legs[0]); P.legR.rotation.x = deg(s.legs[1]);
    if (P.face && s.face && P.faceMaps[s.face]) {
      if (P.face.material.map !== P.faceMaps[s.face]) { P.face.material.map = P.faceMaps[s.face]; P.face.material.needsUpdate = true; }
      const g = P.faceGeo[s.face], k = s.faceScale;
      P.face.scale.set(g.size[0] * k, g.size[1] * k, 1);
      P.face.position.set(0, g.y * a.u * k, (.56 + g.z) * a.u + (k - 1) * .3 * a.u);  // a popped face floats in front of the head
    }
  }
  // the ground shadow only when standing on the floor
  const sh = o.children.find(c => c.material && c.material.map === shadowTex);
  if (sh) sh.visible = Math.abs(s.at[1]) < .05 && !s.attach;
}

function placeCamera(shotName, elapsed) {
  const sh = D.shots[shotName]; if (!sh) throw new Error(`unknown shot ${shotName}`);
  const drift = sh.drift ?? [0, 0, 0];
  const pos = [sh.pos[0] + drift[0] * elapsed, sh.pos[1] + drift[1] * elapsed, sh.pos[2] + drift[2] * elapsed];
  const look = sh.look ?? [0, 1, 0];
  camera.position.set(...pos);
  camera.lookAt(look[0] + (sh.lookDrift ? sh.lookDrift[0] * elapsed : 0), look[1] + (sh.lookDrift ? sh.lookDrift[1] * elapsed : 0), look[2] + (sh.lookDrift ? sh.lookDrift[2] * elapsed : 0));
  if (sh.roll) camera.rotateZ(deg(sh.roll));
  camera.fov = (sh.fov ?? D.camera?.fov ?? 45) + (sh.zoom ?? 0) * elapsed;
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld(true);
  fitBackground(sh, drift, elapsed);
}

// cover-fit the photo to the frame at a fixed distance in front of the camera, then crop per shot.
// bg.zoom > 1 enlarges, bg.pan = [right, up] in fractions of the frame. Camera drift pans/zooms it a
// little (D.background.parallax per metre) so near things move more than the photo.
function fitBackground(sh, drift, elapsed) {
  const dist = 60, bg = sh.bg ?? {}, px = D.background.parallax ?? .12;
  const fh = 2 * dist * Math.tan(deg(camera.fov) / 2), fw = fh * camera.aspect;
  const ia = bgPlane.userData.aspect;
  let w = fw, h = fw / ia; if (h < fh) { h = fh; w = fh * ia; }
  const zoom = (bg.zoom ?? 1) * (1 - drift[2] * elapsed * px);   // dolly in (drift z < 0) zooms the photo a bit
  bgPlane.scale.set(w * zoom, h * zoom, 1);
  const pan = bg.pan ?? [0, 0];
  bgPlane.position.set((pan[0] - drift[0] * elapsed * px) * fw, (pan[1] - drift[1] * elapsed * px) * fh, -dist);
}

function renderAt(time) {
  const { st, shot, shotStart, caption, overlay, watermark } = stateAt(time);
  placeCamera(shot ?? Object.keys(D.shots)[0], time - shotStart);
  // parents first so attached actors read an up-to-date world matrix
  for (const n in actors) if (!st[n].attach) placeActor(n, st[n], st, camera);
  for (const n in actors) if (st[n].attach) placeActor(n, st[n], st, camera);
  const cap = $('caption');
  if (caption) { cap.textContent = caption; cap.style.display = 'block'; } else cap.style.display = 'none';
  const wm = $('watermark');
  if (watermark) { wm.textContent = watermark; wm.style.display = 'block'; } else wm.style.display = 'none';
  $('overlay').style.opacity = typeof overlay === 'number' ? overlay : (overlay?.opacity ?? 0);
  if (overlay && overlay.color) $('overlay').style.background = overlay.color;
  const t0 = performance.now();
  renderer.render(scene, camera);
  return { ms: performance.now() - t0, shot, caption };
}

// ---------- public API ----------
window.init = async function (director, base, resolvedBeats) {
  D = director; BASE = base; beats = resolvedBeats;
  [W, H] = D.size; FPS = D.fps;
  const stage = $('stage'); stage.style.width = W + 'px'; stage.style.height = H + 'px';
  $('caption').style.fontSize = Math.round((D.caption?.size ?? .059) * W) + 'px';
  if (D.caption?.top) $('caption').style.top = D.caption.top;
  if (D.caption?.font) $('caption').style.fontFamily = D.caption.font;
  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H); renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;  // photos and cut-outs keep their exact colours
  stage.insertBefore(renderer.domElement, stage.firstChild);
  camera = new THREE.PerspectiveCamera(D.camera?.fov ?? 45, W / H, .05, 300);
  await buildScene();
  return { actors: Object.fromEntries(Object.entries(actors).map(([n, a]) => [n, { kind: a.kind, w: +a.w.toFixed(2), h: +a.h.toFixed(2) }])) };
};
window.renderFrame = f => renderAt((f - 1) / FPS);
window.renderTime = t => renderAt(t);
window.gpu = () => { const gl = renderer.getContext(), i = gl.getExtension('WEBGL_debug_renderer_info'); return i ? gl.getParameter(i.UNMASKED_RENDERER_WEBGL) : 'n/a'; };
window.ready = true;
