// tableau: a "frozen moment" 3D hook — mannequin figures hold one pose (an animation clip frozen at a
// fixed time), only the camera drifts. Style target: VN history-explainer openers (desaturated night
// plaza, heavy DOF, dust, one colored hero in a monochrome crowd).
// Pure function of the frame number: all motion is camera lerp + f-driven particle drift.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { BokehPass } from 'three/examples/jsm/postprocessing/BokehPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

const $ = id => document.getElementById(id);
const deg = d => d * Math.PI / 180;
const lerp = (a, b, u) => a + (b - a) * u;
const ease = u => u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;   // gentle inout for camera drift

let renderer, scene, camera, composer, bokeh, W, H, FPS;
let baseModel, clips;           // UBC gltf scene + UAL1 animation clips
let particles;
const mixers = [];              // kept only so GC doesn't eat them; never updated after init

// deterministic pseudo-random (same scene every run)
let seed = 7;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;

// ---------- materials ----------
const MAT = {
  crowd: () => new THREE.MeshStandardMaterial({ color: 0xbfa89a, roughness: .62, metalness: .02 }),
  soldier: () => new THREE.MeshStandardMaterial({ color: 0xd6d9df, roughness: .55, metalness: .04 }),
  hero: () => new THREE.MeshStandardMaterial({ color: 0x5a74a8, roughness: .5, metalness: .03 }),
  black: () => new THREE.MeshStandardMaterial({ color: 0x0a0b0d, roughness: .85 }),
  redGlow: () => new THREE.MeshStandardMaterial({ color: 0x300000, emissive: 0xff2412, emissiveIntensity: 2.4, roughness: .4 }),
  gun: () => new THREE.MeshStandardMaterial({ color: 0xd9dce2, roughness: .45, metalness: .1 }),
  helmet: () => new THREE.MeshStandardMaterial({ color: 0xb9bdc4, roughness: .5, metalness: .06 }),
};

// ---------- actors ----------
function spawn({ clip, time, at, yaw, mat, scale = 1 }) {
  const clone = SkeletonUtils.clone(baseModel);
  clone.traverse(o => { if (o.isMesh || o.isSkinnedMesh) { o.material = mat(); o.frustumCulled = false; } });
  const root = new THREE.Group();
  root.add(clone);
  root.position.set(...at);
  root.rotation.y = deg(yaw);
  root.scale.setScalar(scale);
  const c = clips.find(c => c.name === clip);
  if (!c) throw new Error(`no clip ${clip}`);
  const mixer = new THREE.AnimationMixer(clone);
  mixer.clipAction(c).play();
  mixer.setTime(time % c.duration);         // freeze the pose here; never updated again
  mixers.push(mixer);
  scene.add(root);
  root.updateMatrixWorld(true);
  return root;
}

const bone = (root, re) => { let hit = null; root.traverse(o => { if (!hit && o.isBone && re.test(o.name)) hit = o; }); return hit; };

// boxy AK-style rifle, muzzle toward +z of its own frame
function rifle(mat) {
  const g = new THREE.Group();
  const add = (geo, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); g.add(m); return m; };
  add(new THREE.BoxGeometry(.055, .085, .52), 0, 0, .05);                       // receiver
  add(new THREE.CylinderGeometry(.016, .016, .34, 10).rotateX(Math.PI / 2), 0, .012, .46); // barrel
  add(new THREE.BoxGeometry(.04, .05, .12), 0, .048, .34);                      // front sight block
  add(new THREE.BoxGeometry(.045, .14, .07), 0, -.1, .12).rotation.x = deg(18); // magazine
  add(new THREE.BoxGeometry(.05, .09, .26), 0, -.02, -.26).rotation.x = deg(-6);// stock
  add(new THREE.BoxGeometry(.03, .09, .05), 0, -.075, -.03);                    // grip
  return g;
}

function helmetFor(figure, mat) {
  const h = bone(figure, /head/i);
  if (!h) return;
  const p = new THREE.Vector3(); h.getWorldPosition(p);
  const q = new THREE.Quaternion(); h.getWorldQuaternion(q);
  const g = new THREE.Group();
  const dome = new THREE.Mesh(new THREE.SphereGeometry(.125, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), mat);
  dome.scale.set(1, .82, 1.1);
  const brim = new THREE.Mesh(new THREE.CylinderGeometry(.128, .138, .035, 20), mat);
  brim.position.y = -.005;
  g.add(dome, brim);
  g.position.copy(p); g.quaternion.copy(q);
  g.translateY(.085);
  scene.add(g);
}

// place a rifle between the two hands of a frozen aiming pose
function rifleInHands(figure, mat) {
  const l = bone(figure, /hand_l/i), r = bone(figure, /hand_r/i);
  if (!l || !r) return null;
  const pl = new THREE.Vector3(), pr = new THREE.Vector3();
  l.getWorldPosition(pl); r.getWorldPosition(pr);
  const g = rifle(mat);
  g.position.copy(pl).add(pr).multiplyScalar(.5);
  g.position.y -= .02;
  const fwd = new THREE.Vector3(); figure.getWorldDirection(fwd);       // root yaw direction
  g.lookAt(g.position.clone().add(fwd));
  scene.add(g);
  return g;
}

// ---------- shots ----------
// from/to: camera path (eased); look: fixed target; focus: metres; ap: bokeh aperture; set: group to show
let SHOTS;
const shotAt = f => {
  let acc = 0;
  for (const s of SHOTS) { if (f <= acc + s.frames) return [s, (f - acc - 1) / s.frames]; acc += s.frames; }
  return [SHOTS[SHOTS.length - 1], 1];
};

// ---------- scene ----------
async function build(base) {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d12);
  scene.fog = new THREE.FogExp2(0x0b0d12, 0.055);

  scene.add(new THREE.HemisphereLight(0x45577a, 0x16161a, 2.4));
  const key = new THREE.DirectionalLight(0xbcc9e4, 3.4); key.position.set(-6, 9, 8); scene.add(key);
  const rim = new THREE.DirectionalLight(0x6d84b5, 2.6); rim.position.set(2, 6, -10); scene.add(rim);

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(90, 90),
    new THREE.MeshStandardMaterial({ color: 0x1d2027, roughness: .82 }));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);

  const loader = new GLTFLoader();
  const ubc = await loader.loadAsync(base + 'quaternius_ubc_ual/Superhero_Male_FullBody.gltf');
  baseModel = ubc.scene;
  const ual = await loader.loadAsync(base + 'quaternius_ubc_ual/UAL1_Standard.glb');
  clips = ual.animations;

  // --- set 1: the plaza (crowd flees toward +z, hero up front, soldiers behind) ---
  const hero = spawn({ clip: 'Sprint_Loop', time: .38, at: [0.3, 0, 10], yaw: 8, mat: MAT.hero });
  for (let i = 0; i < 26; i++) {
    const run = rnd() < .7;
    spawn({
      clip: run ? 'Sprint_Loop' : 'Jog_Fwd_Loop', time: rnd() * 2,
      at: [lerp(-9, 9, rnd()), 0, lerp(1.5, 8.6, rnd())],
      yaw: lerp(-28, 28, rnd()), mat: MAT.crowd, scale: lerp(.96, 1.03, rnd()),
    });
  }
  const soldiers = [];
  for (let i = 0; i < 6; i++) {
    const s = spawn({ clip: 'Pistol_Aim_Neutral', time: .5, at: [-6.5 + i * 2.5, 0, -4.5 - (i % 2) * .7], yaw: lerp(-6, 6, rnd()), mat: MAT.soldier });
    helmetFor(s, MAT.helmet());
    rifleInHands(s, MAT.gun());
    soldiers.push(s);
  }

  // --- set 2 (far away): silhouette soldier, red glowing rifle ---
  const sil = spawn({ clip: 'Pistol_Aim_Neutral', time: .5, at: [200, 0, 0], yaw: 24, mat: MAT.black });
  helmetFor(sil, MAT.black());
  const silGun = rifleInHands(sil, MAT.redGlow());
  const silRim = new THREE.DirectionalLight(0x58688f, 6); silRim.position.set(197, 4, -6);
  silRim.target = sil; scene.add(silRim, silRim.target);
  const glow = new THREE.PointLight(0xff2a14, 4.5, 2.6); glow.position.copy(silGun.position).add(new THREE.Vector3(0, .1, .2)); scene.add(glow);

  // --- dust / bokeh particles drifting through the plaza ---
  const N = 420, pos = new Float32Array(N * 3), seedv = new Float32Array(N);
  for (let i = 0; i < N; i++) { pos[3 * i] = lerp(-10, 10, rnd()); pos[3 * i + 1] = lerp(0, 5, rnd()); pos[3 * i + 2] = lerp(-6, 13, rnd()); seedv[i] = rnd(); }
  const pg = new THREE.BufferGeometry();
  pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  pg.userData = { base: pos.slice(), seedv };
  const pc = document.createElement('canvas'); pc.width = pc.height = 64;
  const pctx = pc.getContext('2d'), grad = pctx.createRadialGradient(32, 32, 2, 32, 32, 30);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(.4, 'rgba(255,255,255,.4)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  pctx.fillStyle = grad; pctx.fillRect(0, 0, 64, 64);
  particles = new THREE.Points(pg, new THREE.PointsMaterial({
    color: 0xaebfe2, size: .07, map: new THREE.CanvasTexture(pc), transparent: true, opacity: .5,
    depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  scene.add(particles);

  SHOTS = [
    { name: 'hero', frames: 140, from: [1.3, 1.52, 12.9], to: [0.9, 1.46, 12.15], look: [0.25, 1.15, 10.2], focus: 2.4, ap: 8e-4 },
    { name: 'line', frames: 130, from: [-9.4, 1.52, -3.3], to: [-8.5, 1.48, -3.55], look: [0.5, 1.2, -4.9], focus: 4.3, ap: 4.5e-4 },
    { name: 'gun', frames: 110, from: [-5.15, 1.34, -3.85], to: [-5.35, 1.31, -3.95], look: [-6.5, 1.28, -3.95], focus: 1.2, ap: 1.3e-3 },
    { name: 'sil', frames: 100, from: [200.9, 1.32, 2.4], to: [200.7, 1.28, 2.1], look: [199.9, 1.25, 0.1], focus: 2.2, ap: 3e-4 },
    { name: 'title', frames: 100, from: [400, 1.5, 5], to: [400, 1.5, 4.9], look: [400, 1.5, 0], focus: 5, ap: 1e-5, title: true },
  ];
  return SHOTS.reduce((a, s) => a + s.frames, 0);
}

function renderAt(f) {
  const [s, u0] = shotAt(f);
  const u = ease(Math.min(1, Math.max(0, u0)));
  camera.position.set(lerp(s.from[0], s.to[0], u), lerp(s.from[1], s.to[1], u), lerp(s.from[2], s.to[2], u));
  camera.lookAt(...s.look);
  bokeh.uniforms.focus.value = s.focus;
  bokeh.uniforms.aperture.value = s.ap;

  // dust drifts up-left very slowly; wraps inside its volume
  const pg = particles.geometry, base = pg.userData.base, sv = pg.userData.seedv, arr = pg.attributes.position.array;
  const t = f / FPS;
  for (let i = 0; i < sv.length; i++) {
    arr[3 * i] = base[3 * i] + Math.sin(t * .22 + sv[i] * 9) * .25;
    arr[3 * i + 1] = ((base[3 * i + 1] + t * (.06 + sv[i] * .05)) % 5 + 5) % 5;
    arr[3 * i + 2] = base[3 * i + 2] + Math.cos(t * .17 + sv[i] * 7) * .2;
  }
  pg.attributes.position.needsUpdate = true;

  $('title').style.display = s.title ? 'flex' : 'none';
  if (s.title) $('title').style.opacity = Math.min(1, u0 * 3).toFixed(3);

  const t0 = performance.now();
  composer.render();
  return { ms: performance.now() - t0, shot: s.name };
}

// ---------- public API ----------
window.init = async function (cfg, base) {
  [W, H] = cfg.size; FPS = cfg.fps;
  const stage = $('stage'); stage.style.width = W + 'px'; stage.style.height = H + 'px';
  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H); renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;    // filmic rolloff suits the moody grade
  renderer.toneMappingExposure = 1.05;
  stage.insertBefore(renderer.domElement, stage.firstChild);
  camera = new THREE.PerspectiveCamera(42, W / H, .05, 400);
  const frames = await build(base);
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  bokeh = new BokehPass(scene, camera, { focus: 3, aperture: 2e-4, maxblur: .018 });
  composer.addPass(bokeh);
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), .5, .45, .72));
  return { frames };
};
window.renderFrame = f => renderAt(f);
window.gpu = () => { const gl = renderer.getContext(), i = gl.getExtension('WEBGL_debug_renderer_info'); return i ? gl.getParameter(i.UNMASKED_RENDERER_WEBGL) : 'n/a'; };
window.ready = true;
