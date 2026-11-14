// The Q&A room, dev and mascot in three.js, animated as a pure function of the frame number.
// Same numbers as scripts/_scene_lib.py + qa_scene.py: every helper takes Blender coordinates
// (x, y, z up) and converts to three (x, z, -y). shoot.mjs calls window.init(timeline) once,
// then window.renderFrame(f) per frame and screenshots the page: the WebGL canvas plus the
// HTML speech bubble text and illustration cards laid over it.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';

// Quaternius "Modular Men/Women" bone -> Universal Animation Library (UE mannequin) bone, for retargeting its clips
const QUATERNIUS_TO_UAL = { Hips: 'pelvis', Abdomen: 'spine_01', Torso: 'spine_02', Chest: 'spine_03', Neck: 'neck_01', Head: 'Head' };
for (const [s, u] of [['L', 'l'], ['R', 'r']]) {
  Object.assign(QUATERNIUS_TO_UAL, { [`Shoulder${s}`]: `clavicle_${u}`, [`UpperArm${s}`]: `upperarm_${u}`, [`LowerArm${s}`]: `lowerarm_${u}`,
    [`Hand${s}`]: `hand_${u}`, [`UpperLeg${s}`]: `thigh_${u}`, [`LowerLeg${s}`]: `calf_${u}`, [`Foot${s}`]: `foot_${u}`,
    [`Thumb2${s}`]: `thumb_01_${u}`, [`Thumb3${s}`]: `thumb_02_${u}` });
  for (const f of ['Index', 'Middle', 'Ring', 'Pinky']) for (let i = 2; i <= 4; i++) QUATERNIUS_TO_UAL[`${f}${i}${s}`] = `${f.toLowerCase()}_0${i - 1}_${u}`;
}

const W = 1280, H = 720;
const deg = THREE.MathUtils.degToRad;
const TAU = Math.PI * 2;
const v3 = ([x, y, z]) => new THREE.Vector3(x, z, -y);          // Blender -> three
const sz = ([x, y, z]) => [x, z, y];                            // sizes/scales: no sign
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];

const MATERIALS = {  // name: [sRGB, roughness, emission, metallic] -- copied from _scene_lib.py
  floor: [[.52, .45, .38], .7], wall: [[.2, .37, .4], .9], trim: [[.9, .88, .84], .5], wood: [[.62, .45, .3], .45],
  metal: [[.2, .2, .22], .35, 0, .8], alu: [[.72, .73, .75], .3, 0, .9], dark: [[.03, .03, .035], .4],
  screen: [[.08, .12, .2], .2, 1.5], code_a: [[.45, .75, 1], .6, 4], code_b: [[.95, .6, .45], .6, 4],
  code_c: [[.6, .9, .55], .6, 4], mug: [[.93, .92, .9], .25], coffee: [[.18, .09, .04], .1], pot: [[.72, .42, .3], .7],
  leaf: [[.25, .5, .25], .6], chair: [[.16, .17, .2], .6], jeans: [[.17, .25, .42], .8], shoe: [[.92, .92, .9], .5],
  hoodie: [[.72, .77, .87], .5], skin: [[.89, .7, .56], .55], hair: [[.12, .08, .06], .7], mouth: [[.45, .18, .16], .5],
  clawd: [[.84, .38, .2], .55], bubble: [[.97, .96, .93], .4], pic_frame: [[.8, .63, .42], .5], canvas: [[.93, .89, .8], .8],
  art_terra: [[.8, .36, .22], .8], art_mustard: [[.88, .66, .22], .8], art_sage: [[.52, .63, .5], .8], art_navy: [[.13, .2, .36], .8],
};
const M = {};
for (const [name, [rgb, rough, emit = 0, metal = 0]] of Object.entries(MATERIALS)) {
  const color = new THREE.Color().setRGB(...rgb, THREE.SRGBColorSpace);
  M[name] = new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal,
    emissive: emit ? color : new THREE.Color(0), emissiveIntensity: emit });
}

const scene = new THREE.Scene();
const add = (mesh, parent) => { (parent || scene).add(mesh); mesh.castShadow = mesh.receiveShadow = true; return mesh; };

function group(loc, yawDeg = 0, parent = null, scale = 1) {
  const g = new THREE.Group();
  g.position.copy(v3(loc));
  g.rotation.y = deg(yawDeg);
  g.scale.setScalar(scale);
  (parent || scene).add(g);
  return g;
}
function box(size, loc, m, parent, bevel = 0, rot = [0, 0, 0]) {
  const [w, h, d] = sz(size);
  const geo = bevel ? new RoundedBoxGeometry(w, h, d, 3, Math.min(bevel, Math.min(w, h, d) / 2)) : new THREE.BoxGeometry(w, h, d);
  const o = new THREE.Mesh(geo, m);
  o.position.copy(v3(loc));
  o.rotation.set(rot[0], rot[2], -rot[1]);  // Blender XYZ euler -> three
  return add(o, parent);
}
function ball(r, loc, m, parent, scale = [1, 1, 1]) {
  const o = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 16), m);
  o.position.copy(v3(loc));
  o.scale.set(...sz(scale));
  return add(o, parent);
}
function cyl(r, depth, loc, m, parent, rot = [0, 0, 0]) {
  const o = new THREE.Mesh(new THREE.CylinderGeometry(r, r, depth, 32), m);
  o.position.copy(v3(loc));
  o.rotation.set(rot[0], rot[2], -rot[1]);
  return add(o, parent);
}
function limb(a, b, r, m, parent) {
  const pa = v3(a), pb = v3(b), dir = pb.clone().sub(pa);
  const o = new THREE.Mesh(new THREE.CylinderGeometry(r, r, dir.length(), 24), m);
  o.position.copy(pa).add(pb).multiplyScalar(.5);
  o.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  add(o, parent);
  ball(r, a, m, parent); ball(r, b, m, parent);
}
function disc(r, loc, m, parent) {
  const o = new THREE.Mesh(new THREE.CircleGeometry(r, 48), m);
  o.position.copy(v3(loc));
  return add(o, parent);
}
function torus(R, r, loc, m, parent, rot = [0, 0, 0]) {
  const o = new THREE.Mesh(new THREE.TorusGeometry(R, r, 16, 48), m);
  o.position.copy(v3(loc));
  o.rotation.set(rot[0] + Math.PI / 2, rot[2], -rot[1]);
  return add(o, parent);
}

// ---- room and desk, straight from _scene_lib.py ----
function room() {
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), M.floor);
  floor.rotation.x = -Math.PI / 2;
  add(floor);
  box([10, .1, 4], [0, 1.3, 2], M.wall);
  box([.1, 10, 4], [-1.6, 0, 2], M.wall);
  box([10, .1, 4], [0, -5, 2], M.wall);
  box([10, .02, .12], [0, 1.24, .06], M.trim);
}
function painting(loc, yaw, [w, h], art) {
  const g = group(loc, yaw);
  box([w, .03, h], [0, -.015, 0], M.pic_frame, g, .004);
  const cw = w - .07, ch = h - .07;
  box([cw, .004, ch], [0, -.031, 0], M.canvas, g);
  art.forEach(([kind, m, u, v, su, sv], i) => {
    const pos = [u * cw / 2, -.034 - i * .002, v * ch / 2];
    if (kind === 'disc') disc(su * Math.min(cw, ch), pos, M[m], g);
    else box([su * cw, .002, sv * ch], pos, M[m], g);
  });
}
const SUNSET = [['disc', 'art_terra', .3, .15, .26, 0], ['rect', 'art_mustard', 0, -.6, 1, .4], ['rect', 'art_navy', 0, -.82, 1, .18]];
const BLOCKS = [['rect', 'art_sage', -.3, .45, .55, .4], ['disc', 'art_mustard', .3, .05, .28, 0], ['rect', 'art_terra', .1, -.55, .7, .3]];
const ARCH = [['disc', 'art_navy', 0, .15, .36, 0], ['rect', 'art_navy', 0, -.275, .72, .425], ['disc', 'art_mustard', 0, .15, .17, 0]];
const DOTS = [['disc', 'art_terra', -.25, .25, .3, 0], ['disc', 'art_sage', .25, -.2, .3, 0], ['rect', 'art_mustard', 0, -.8, .8, .1]];

function desk() {
  box([1.6, .7, .05], [0, 0, .725], M.wood, null, .01);
  for (const x of [-.75, .75]) for (const y of [-.3, .3]) box([.05, .05, .7], [x, y, .35], M.metal);
  const lap = group([-.2, -.05, .75], 8);
  box([.34, .24, .018], [0, 0, .009], M.alu, lap, .004);
  box([.3, .1, .002], [0, -.03, .019], M.dark, lap);
  const hinge = group([0, .12, .018], 0, lap);
  hinge.rotation.x = deg(-14);
  box([.34, .012, .23], [0, 0, .115], M.alu, hinge, .004);
  box([.31, .002, .2], [0, -.0065, .115], M.screen, hinge);
  let seed = 7;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  const codeColors = [M.code_a, M.code_b, M.code_c];
  for (let i = 0; i < 10; i++) {
    const w = .05 + rnd() * .15, indent = [0, .02, .04][Math.floor(rnd() * 3)];
    box([w, .002, .008], [-.13 + indent + w / 2, -.009, .2 - i * .017], codeColors[Math.floor(rnd() * 3)], hinge);
  }
  const mug = group([.2, .18, .75]);
  cyl(.04, .1, [0, 0, .05], M.mug, mug);
  cyl(.034, .002, [0, 0, .098], M.coffee, mug);
  torus(.026, .007, [.045, 0, .05], M.mug, mug, [deg(90), 0, 0]);
  const pot = group([-.65, .18, .75]);
  cyl(.06, .11, [0, 0, .055], M.pot, pot);
  for (const [dx, dy, dz, r] of [[0, 0, .17, .07], [.04, .02, .21, .05], [-.04, -.01, .22, .055], [0, .03, .26, .045]]) ball(r, [dx, dy, dz], M.leaf, pot);
}

// ---- the dev: same shapes, but arms and legs hang off joints so they can move ----
function programmer(loc, yaw, headYaw) {
  const seat = group(loc, yaw);
  const chair = [box([.48, .46, .07], [0, .02, .44], M.chair, seat, .02),
                 box([.46, .06, .52], [0, .26, .8], M.chair, seat, .025, [deg(-8), 0, 0]),
                 cyl(.03, .32, [0, .02, .25], M.metal, seat),
                 cyl(.28, .03, [0, .02, .06], M.metal, seat)];
  const p = group([0, 0, 0], 0, seat);  // the person, apart from the chair, so a ready-made character can take the seat
  box([.36, .3, .16], [0, .04, .55], M.jeans, p, .05);
  const knees = [];
  for (const s of [-1, 1]) {
    const hip = [s * .1, .02, .56], knee = [s * .11, -.38, .56];
    limb(hip, knee, .075, M.jeans, p);
    const k = group(knee, 0, p);  // shin + shoe swing from the knee
    limb([0, -.02, -.02], sub([s * .115, -.43, .12], knee), .062, M.jeans, k);
    box([.11, .22, .07], sub([s * .115, -.48, .045], knee), M.shoe, k, .025);
    knees.push(k);
  }
  const hoodie = box([.42, .26, .5], [0, .05, .87], M.hoodie, p, .09, [deg(-6), 0, 0]);
  torus(.1, .04, [0, .05, 1.1], M.hoodie, p);
  cyl(.05, .12, [0, .03, 1.15], M.skin, p);
  const h = group([0, .03, 1.15], headYaw, p);
  ball(.13, [0, -.01, .15], M.skin, h, [1, 1, 1.08]);
  ball(.136, [0, .02, .2], M.hair, h, [1.02, 1, .82]);
  ball(.06, [.03, -.09, .245], M.hair, h, [1.4, .8, .5]);
  const eyes = [], brows = [];
  for (const s of [-1, 1]) {
    ball(.03, [s * .13, -.01, .15], M.skin, h, [.6, 1, 1]);
    eyes.push(ball(.016, [s * .046, -.128, .165], M.dark, h));
    brows.push(box([.036, .012, .007], [s * .047, -.124, .2], M.hair, h, .002, [0, deg(s * 8), 0]));
  }
  ball(.02, [0, -.145, .13], M.skin, h);
  const mouth = ball(.022, [0, -.122, .09], M.mouth, h, [1.2, .5, .6]);
  const arm = (S, E, Hd, handScale) => {  // shoulder group -> upper arm -> elbow group -> forearm + hand
    const shoulder = group(S, 0, p);
    const e = sub(E, S);
    limb([0, 0, 0], e, .055, M.hoodie, shoulder);
    const elbow = group(e, 0, shoulder);
    const hd = sub(Hd, E);
    limb([0, 0, 0], hd, .05, M.hoodie, elbow);
    ball(.045, hd, M.skin, elbow, handScale);
    return { shoulder, elbow };
  };
  const armR = arm([.22, .04, 1.03], [.25, -.04, .8], [.15, -.3, .66], [1, 1, 1]);        // resting on the desk
  const armL = arm([-.22, .04, 1.03], [-.28, -.08, .82], [-.22, -.32, .98], [.8, .6, 1.1]);  // raised, talks with it
  return { root: seat, body: p, chair, head: h, hoodie, mouth, eyes, brows, knees, armR, armL };
}

// ---- the mascot: legs on the root, everything else on a body group that can bob and squash ----
function mascot(loc, yaw, scale) {
  const c = group(loc, yaw, null, scale);
  const legs = [-.095, -.035, .035, .095].map(x => {
    const leg = group([x, 0, .05], 0, c);
    box([.035, .045, .05], [0, 0, -.025], M.clawd, leg, .004);
    return leg;
  });
  const body = group([0, 0, 0], 0, c);
  box([.26, .13, .15], [0, 0, .125], M.clawd, body, .01);
  const eyes = [], arms = [];
  for (const s of [-1, 1]) {
    const arm = group([s * .118, 0, .13], 0, body);  // side block pivots just inside the body, so a wave opens no gap
    box([.05, .07, .045], [s * .034, 0, 0], M.clawd, arm, .006);
    arms.push(arm);
    eyes.push(box([.022, .01, .042], [s * .055, -.066, .15], M.dark, body, .003));
  }
  const mouth = box([.034, .01, .012], [0, -.066, .108], M.dark, body, .003);
  return { root: c, body, face: group([0, -.06, .14], 0, c), mouth, eyes, arms, legs };  // face anchor on the root: bubbles must not bob with the body
}

function bubble(loc, scale, parent) {
  const b = group(loc, 0, parent, scale);
  const body = ball(.12, [0, 0, 0], M.bubble, b, [1.5, .25, 1]);
  const tail = new THREE.Mesh(new THREE.ConeGeometry(.04, .09, 32), M.bubble);
  tail.position.copy(v3([-.06, 0, -.12]));
  tail.rotation.z = -deg(200);
  add(tail, b);
  b.visible = false;
  return { root: b, body };
}

function lights() {
  const spot = (loc, target, intensity, color, shadow) => {
    const l = new THREE.SpotLight(new THREE.Color(...color), intensity, 0, deg(55), .6, 1.2);
    l.position.copy(v3(loc));
    l.target.position.copy(v3(target));
    scene.add(l, l.target);
    if (shadow) {
      l.castShadow = true;
      l.shadow.mapSize.set(2048, 2048);
      l.shadow.radius = 5;
      l.shadow.bias = -.0004;
      l.shadow.normalBias = .02;  // no striping on the walls (VSM bled, PCF without it shows acne)
    }
  };
  spot([2.2, -1.6, 2.8], [.2, -.5, .9], 42, [1, .95, .88], true);
  spot([-.3, -2.6, 1.8], [.2, -.5, .9], 14, [.75, .85, 1], false);
  spot([-.4, 1.0, 2.2], [.2, -.6, 1.1], 18, [1, .8, .6], false);
  const glow = new THREE.PointLight(new THREE.Color(1, .7, .45), 1.5, 3, 2);
  glow.position.copy(v3([.45, .1, 1.05]));
  scene.add(glow);
  scene.add(new THREE.HemisphereLight(new THREE.Color().setRGB(.55, .7, .72, THREE.SRGBColorSpace),
                                      new THREE.Color().setRGB(.45, .38, .3, THREE.SRGBColorSpace), .9));
}

// ---- build ----
const before = scene.children.length;
room();
painting([-1.55, -3.75, 1.22], 90, [1.3, .75], SUNSET);
painting([-1.15, -4.95, 1.25], 180, [.5, .65], BLOCKS);
painting([-1.55, .33, 1.3], 90, [.5, .65], ARCH);
painting([.3, 1.25, 1.28], 0, [.5, .6], DOTS);
desk();
const roomParts = scene.children.slice(before);  // hidden for the title card: characters on a 2D backdrop
const dev = programmer([-.05, -.85, 0], 112, 22);
const claude = mascot([.42, -.16, .75], 30, 1.25);
const CHAR = { dev, claude };
lights();

const SHOTS = {  // qa_scene.py SHOTS
  dev_talk: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 38, dist: 2.0, side: [.72, .70, .3] },
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  dev_explain: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 38, dist: 2.3, side: [.72, .70, .3], low: .12, aside: .25 },
                 bubble: { loc: [.08, -.05, .58], scale: 1.95 }, card: [.47, .1, .97, .82] },
  claude_talk: { anchor: claude.face, camera: { lens: 40, dist: 1.7, side: [.9, -.6, .35], low: .15 },
                 bubble: { loc: [.11, -.02, .28], scale: 1.7 } },
  claude_explain: { anchor: claude.face, camera: { lens: 40, dist: 1.9, side: [.9, -.6, .35], low: .14, aside: .24 },
                    bubble: { loc: [.04, -.02, .36], scale: 1.42 }, card: [.47, .1, .97, .82] },
  wide: { anchor: claude.face, camera: { offset: [-.4, .3, -.1], lens: 30, dist: 3.6, side: [1, -.9, .45], low: .02 },  // the whole corner, for stills
          bubble: { loc: [.13, -.02, .30], scale: 1.5 } },
  dev_side: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 32, dist: 1.5, side: [-1, .1, .25], low: -.12 },  // stills: hands on the keyboard
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  dev_top: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 30, dist: 1.2, side: [-.45, -.35, 1], low: -.2 },  // stills: over the shoulder, onto the keys
             bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  // the boss (assets/boss_suit.json, role "boss"): anchored to his head at init; claude.face only holds the place
  boss_talk: { anchor: claude.face, camera: { lens: 38, dist: 2.0, side: [.8, -.55, .25], low: -.04 },
               bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  boss_dev: { anchor: claude.face, camera: { lens: 30, dist: 2.8, side: [.7, -1, .35], low: -.12, aside: .12 },  // both of them at the desk
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  boss_body: { anchor: claude.face, camera: { lens: 35, dist: 2.4, side: [.55, -.85, .1], low: -.32 },  // stills: the boss head to toe
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  boss_hips: { anchor: claude.face, camera: { lens: 40, dist: 1.6, side: [.55, -.85, .05], low: -.42 },  // stills: the boss hands at his hips
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  boss_hipsL: { anchor: claude.face, camera: { lens: 40, dist: 1.6, side: [.6, .8, .05], low: -.42 },  // stills: the boss hips from his left
               bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  boss_front: { anchor: claude.face, camera: { lens: 35, dist: 2.3, side: [.8, .55, .15], low: -.28 },  // stills: the boss from his front-left, arms readable
               bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  dev_hands: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 40, dist: .9, side: [-.7, .5, .8], low: -.5 },  // stills: the hands on the keys
               bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
  dev_face: { anchor: dev.head, camera: { offset: [0, -.01, .15], lens: 70, dist: .7, side: [-.14, .99, .05], low: -.1 },  // stills: the glued mouth, face on
              bubble: { loc: [.46, -.05, .25], scale: 1.9 } },
};
for (const shot of Object.values(SHOTS)) shot.bubbleObj = bubble(shot.bubble.loc, shot.bubble.scale, shot.anchor);

const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('c'), antialias: true, preserveDrawingBuffer: true, alpha: true });
renderer.setClearColor(0x000000, 1);
renderer.setSize(W, H, false);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const camera = new THREE.PerspectiveCamera(40, W / H, .05, 50);

function shotFace(cam, anchor, { offset = [0, 0, 0], lens = 85, dist = .55, side = [1, -1, .35], low = 0, aside = 0 }) {
  const hfov = 2 * Math.atan(18 / lens);  // Blender: 36 mm sensor fitted to the wider side
  cam.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(hfov / 2) * H / W));
  const target = anchor.localToWorld(v3(offset));
  cam.position.copy(target).add(v3(side).normalize().multiplyScalar(dist));
  cam.lookAt(target);
  const right = new THREE.Vector3(1, 0, 0).applyQuaternion(cam.quaternion);
  const up = new THREE.Vector3(0, 1, 0).applyQuaternion(cam.quaternion);
  cam.lookAt(target.clone().addScaledVector(right, dist * aside).addScaledVector(up, dist * low));
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld(true);  // project() needs matrixWorldInverse current before any render has run
}

function screenBox(obj) {  // pixel bbox of obj's bounding box as the camera sees it
  obj.updateWorldMatrix(true, false);
  const bb = new THREE.Box3().setFromObject(obj);
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (let i = 0; i < 8; i++) {
    const p = new THREE.Vector3(i & 1 ? bb.max.x : bb.min.x, i & 2 ? bb.max.y : bb.min.y, i & 4 ? bb.max.z : bb.min.z).project(camera);
    const x = (p.x + 1) / 2 * W, y = (1 - p.y) / 2 * H;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  return [x0, y0, x1, y1];
}

// ---- faces and bodies ----
const SPEAKER = { dev: { accent: '#3a68b0', tint: '#d8e4f5' }, claude: { accent: '#c95e34', tint: '#fbe2d3' } };
const POSE = {  // qa_scene.py FACE_POSES (Blender scale order); the first pose of a part is its rest
  dev: { mouth: { closed: {}, half: { scale: [.92, 1, 1.6], lift: -.006 }, open: { scale: [.85, 1, 2.2], lift: -.012 } },
         eyes: { rest: {}, blink: { scale: [1.1, 1, .15] } }, brows: { rest: {}, up: { lift: .012 } } },
  claude: { mouth: { closed: { hidden: true }, half: {}, open: { scale: [1.15, 1, 2.3], lift: -.006 } },
            eyes: { rest: {}, wide: { scale: [1.15, 1, 1.3] }, blink: { scale: [1.25, 1, .16] } } },
  dev_rigged: { mouth: { closed: { scale: [1.1, 1, .5] }, half: {}, open: { scale: [.95, 1, 1.8] } },  // a mouth glued to a bone: scale only
                eyes: { rest: {} }, brows: { rest: {} } },
};
const EMPHASIS = { dev: ['brows', 'up'], claude: ['eyes', 'wide'] };
const ENERGY = { closed: .25, half: .7, open: 1 };

function pose(part, { scale = [1, 1, 1], lift = 0, hidden = false }) {
  if (!part.userData.rest) part.userData.rest = { y: part.position.y, scale: part.scale.clone() };
  const [sx, sy, sz_] = scale;
  part.scale.copy(part.userData.rest.scale).multiply(new THREE.Vector3(sx, sz_, sy));
  part.position.y = part.userData.rest.y + lift;
  part.visible = !hidden;
}
const parts = (who) => ({ mouth: [CHAR[who].mouth].flat(), eyes: CHAR[who].eyes, brows: CHAR[who].brows || [] });
const posesOf = (who) => POSE[who === 'dev' && CHAR.dev.rigged ? 'dev_rigged' : who];

// Body language: idle breathing/sway for everyone; while speaking, gestures scaled by how loud
// the voice is at that moment (`energy`). All sines of the frame number, so deterministic.
// `look` 0..1 turns the dev from the mascot to the boss (neck and head share the ~130 degrees: turning the chest pulls the hands off the keys).
function turnAboutUp(bone, radians) {  // rotate a bone about the world vertical, whatever its parents do
  bone.parent.updateWorldMatrix(true, false);
  const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
  const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), radians);
  bone.quaternion.premultiply(pw.clone().invert().multiply(q).multiply(pw));
}
function animateBodies(f, fps, energy, emph = {}, look = 0) {
  const s = (period, phase = 0) => Math.sin(TAU * f / (fps * period) + phase);
  const e = energy.dev, c = energy.claude;
  if (CHAR.dev.rigged) {
    const b = CHAR.dev.bones;
    for (const x of Object.values(b)) x.rotation.copy(x.userData.base);
    if (look > 0) for (const [bone, d] of [[b.Neck, 55], [b.Head, 75]]) turnAboutUp(bone, deg(d * look));
    // hands rest still on the keyboard (the user's call): no arm or chest motion, the head carries the talking
    b.Head.rotation.x += .04 * s(2.1) * (.3 + e) + (emph.dev ? -.09 : 0);  // a nod opens each sentence
    b.Head.rotation.y += .06 * s(3.7) * (.3 + e);
    b.LowerLegR.rotation.z += .08 * e * s(.5);
  } else {
  dev.hoodie.scale.y = 1 + .012 * s(3.2);
  dev.head.rotation.x = .035 * s(2.1) * (.3 + e) + .05 * e * s(.8, 1);
  dev.head.rotation.y = deg(22) + .05 * s(3.7) * (.3 + e);
  dev.armL.shoulder.rotation.set(.22 * e * s(.9), 0, .15 * e * s(1.3, 1) + .02 * s(2.9));
  dev.armL.elbow.rotation.set(.3 * e * s(.7, .5), .1 * e * s(1.1), 0);
  dev.armR.shoulder.rotation.set(.03 * s(2.6, 2), 0, .02 * s(3.1));
  dev.knees[1].rotation.x = .07 * e * s(.5);
  dev.knees[0].rotation.x = .015 * s(4.1);
  }

  const bob = c * Math.abs(s(.55)) * .012 + .003 * s(2.4);
  claude.body.position.y = bob;
  const squash = 1 + .05 * c * s(.55);
  claude.body.scale.set(1 / Math.sqrt(squash), squash, 1 / Math.sqrt(squash));
  claude.body.rotation.y = .05 * c * s(1.1) + .01 * s(3.3);
  claude.arms.forEach((arm, i) => { const sg = i ? 1 : -1; arm.rotation.z = sg * (.22 * c * s(.8, i * .6) + .06 * s(2.9, i)); });
  claude.legs.forEach((leg, i) => { leg.rotation.x = .18 * c * s(.55, i * Math.PI / 2); });
}

// ---- ready-made glTF assets (KayKit, Kenney...) dropped into the room ----
// spec: [{url, loc (Blender coords), yaw, height (metres, scales the model to it) | scale, clip (animation name),
//         asIs (keep the file's own origin and scale: parts of one character must share them),
//         animations (another glb whose clips drive this rig -- same bone names), replaceDev (hide the built dev, keep the chair)}]
const assets = [];
window.loadAssets = async function (spec) {
  const loader = new GLTFLoader();
  const report = [];
  for (const a of spec) {
    const gltf = await loader.loadAsync(a.url);
    if (a.animations) {
      const lib = await loader.loadAsync(a.animations);
      gltf.animations = lib.animations;
      if (a.retarget) {  // the library's clips re-expressed for this model's skeleton
        const skinnedOf = (o) => { let m = null; o.traverse(x => { if (!m && x.isSkinnedMesh) m = x; }); return m; };
        const target = skinnedOf(gltf.scene), source = skinnedOf(lib.scene);
        const srcSize = new THREE.Box3().setFromObject(lib.scene).getSize(new THREE.Vector3());
        console.error('retarget source size', srcSize.toArray().map(v => +v.toFixed(2)), 'bones', source.skeleton.bones.length);
        const opts = { names: QUATERNIUS_TO_UAL, hip: 'Hips', useFirstFramePosition: true, fps: 30, ...(a.retargetOptions || {}) };
        if (Array.isArray(opts.hipInfluence)) opts.hipInfluence = new THREE.Vector3(...opts.hipInfluence);
        gltf.animations = lib.animations.filter(c => !a.clips || a.clips.includes(c.name)).map(c => {
          const r = SkeletonUtils.retargetClip(target, source, c, opts);
          r.name = c.name;
          return r;
        });
      }
    }
    if (a.replaceDev) {  // the chair goes where the character sits
      dev.body.visible = false;
      dev.root.position.copy(v3(a.loc));
      dev.root.rotation.y = deg(a.yaw || 0);
    }
    const root = gltf.scene;
    let skinned = 0, hidden = 0;
    root.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; if (o.isSkinnedMesh) { skinned++; o.frustumCulled = false; } } });
    if (skinned && a.bodyOnly !== false) {  // character packs ship every weapon/accessory loose around the figure: keep the figure
      root.traverse(o => { if (o.isMesh && !o.isSkinnedMesh) { o.visible = false; hidden++; } });
    }
    root.updateWorldMatrix(true, true);
    const bb = new THREE.Box3();
    root.traverse(o => { if (o.isMesh && o.visible) { o.geometry.computeBoundingBox(); bb.union(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld)); } });
    const size = bb.getSize(new THREE.Vector3());
    const s = a.asIs ? 1 : a.height ? a.height / size.y : (a.scale || 1);
    root.scale.setScalar(s);
    if (!a.asIs) root.position.set(-(bb.min.x + bb.max.x) / 2 * s, -bb.min.y * s, -(bb.min.z + bb.max.z) / 2 * s);  // feet on the floor, centred
    const g = group(a.loc, a.yaw || 0);
    if (a.offset) g.position.add(v3(a.offset));
    g.add(root);
    // pose: a still pose for a rig that has no fitting clip. {boneName: [x, y, z]} adds local degrees;
    // {boneName: [["side"|"fwd"|"up", degrees], ...]} rotates the bone about the character's own world axes
    // (right / facing / up), which is how one thinks about a knee or a shoulder; applied in order, parents first.
    scene.updateMatrixWorld(true);
    const head = root.getObjectByName('Head');
    if (head) a.headRest = head.getWorldQuaternion(new THREE.Quaternion());  // so the glued mouth can follow the posed head
    const upW = new THREE.Vector3(0, 1, 0), fwdW = new THREE.Vector3(0, 0, 1).applyAxisAngle(upW, deg(a.yaw || 0));
    const AX = { up: upW, fwd: fwdW, side: new THREE.Vector3().crossVectors(fwdW, upW) };
    for (const [name, rot] of Object.entries(a.pose || {})) {
      const bone = root.getObjectByName(name) || root.getObjectByName(name.replace(/[\[\]\.:\/]/g, ''));  // GLTFLoader strips "." from "UpperLeg.L"
      if (!bone) { console.error('no bone', name); continue; }
      if (typeof rot[0] === 'number') { bone.rotation.set(bone.rotation.x + deg(rot[0]), bone.rotation.y + deg(rot[1]), bone.rotation.z + deg(rot[2])); continue; }
      for (const [axis, degrees] of rot) {
        scene.updateMatrixWorld(true);
        const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
        const q = new THREE.Quaternion().setFromAxisAngle(AX[axis], deg(degrees));
        bone.quaternion.premultiply(pw.clone().invert().multiply(q).multiply(pw));
      }
    }
    // ik: {handBone: {to: [side, fwd, up], pole: [side, fwd, up]}} puts the wrist at a point given in metres from the
    // character's feet (right / facing / up), the elbow bending towards `pole`: upper arm and forearm are aimed, so
    // no guessing which way a rig's bones turn. Run after `pose`, so the shoulders and torso are where they will be.
    const along = v => new THREE.Vector3().addScaledVector(AX.side, v[0]).addScaledVector(AX.fwd, v[1]).addScaledVector(AX.up, v[2]);
    const wp = o => o.getWorldPosition(new THREE.Vector3());
    const aim = (bone, child, target) => {  // turn bone so that child moves onto the line towards target
      scene.updateMatrixWorld(true);
      const p = wp(bone), q = new THREE.Quaternion().setFromUnitVectors(wp(child).sub(p).normalize(), target.clone().sub(p).normalize());
      const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
      bone.quaternion.premultiply(pw.clone().invert().multiply(q).multiply(pw));
    };
    // `at` instead of `to`: the wrist point in room (Blender) coordinates, e.g. on the laptop. `fingers` (room point)
    // aims the hand so its `finger` bone points there, then `thumb` turns it about that line until the thumb bone
    // points along `thumbTo` (character axes): thumb inwards = palm down, whatever the rig's bone rolls are.
    const byName = n => root.getObjectByName(n) || root.getObjectByName(n.replace(/\./g, ''));
    for (const [name, { to, at, pole = [0, -1, 0], fingers, fingersTo, finger, thumb, thumbTo }] of Object.entries(a.ik || {})) {
      const hand = byName(name);
      if (!hand) { console.error('no bone', name); continue; }
      const lower = hand.parent, upper = lower.parent;
      scene.updateMatrixWorld(true);
      const S = wp(upper), la = S.distanceTo(wp(lower)), lb = wp(lower).distanceTo(wp(hand));
      const T = at ? v3(at) : wp(g).add(along(to));
      const d = Math.min(S.distanceTo(T), la + lb - 1e-4), dir = T.clone().sub(S).normalize();
      if (a.ikDebug) console.error('ik', name, 'shoulder', S.toArray().map(v => +v.toFixed(3)), 'la', la.toFixed(3), 'lb', lb.toFixed(3), 'dist', S.distanceTo(T).toFixed(3), 'feet', wp(g).toArray().map(v => +v.toFixed(3)));
      const cosA = (la * la + d * d - lb * lb) / (2 * la * d), P = along(pole);
      const bend = P.sub(dir.clone().multiplyScalar(P.dot(dir))).normalize();
      const E = S.clone().addScaledVector(dir, la * cosA).addScaledVector(bend, la * Math.sqrt(Math.max(0, 1 - cosA * cosA)));
      aim(upper, lower, E);
      aim(lower, hand, T);
      if ((fingers || fingersTo) && finger) {  // fingersTo: the same point in character axes from the feet
        const F = fingers ? v3(fingers) : wp(g).add(along(fingersTo)), fb = byName(finger);
        aim(hand, fb, F);
        if (thumb && thumbTo) {
          scene.updateMatrixWorld(true);
          const W = wp(hand), axis = F.clone().sub(W).normalize();
          const flat = v => v.sub(axis.clone().multiplyScalar(v.dot(axis))).normalize();
          const t = flat(wp(byName(thumb)).sub(W)), want = flat(along(thumbTo));
          const angle = Math.atan2(new THREE.Vector3().crossVectors(t, want).dot(axis), t.dot(want));
          const pw = hand.parent.getWorldQuaternion(new THREE.Quaternion());
          hand.quaternion.premultiply(pw.clone().invert().multiply(new THREE.Quaternion().setFromAxisAngle(axis, angle)).multiply(pw));
        }
      }
    }
    for (const [name, rot] of Object.entries(a.after || {})) {  // wrist/finger turns once the arm is placed, same form as pose
      const bone = root.getObjectByName(name) || root.getObjectByName(name.replace(/\./g, ''));
      if (!bone) { console.error('no bone', name); continue; }
      for (const [axis, degrees] of rot) {
        scene.updateMatrixWorld(true);
        const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
        bone.quaternion.premultiply(pw.clone().invert().multiply(new THREE.Quaternion().setFromAxisAngle(AX[axis], deg(degrees))).multiply(pw));
      }
    }
    let mixer = null, clip = null;
    if (gltf.animations.length) {
      clip = THREE.AnimationClip.findByName(gltf.animations, a.clip) || gltf.animations[0];
      mixer = new THREE.AnimationMixer(root);
      mixer.clipAction(clip).play();
    }
    assets.push({ mixer });
    if (a.role) riggedCharacter(root, g, a);
    report.push({ file: a.url.split('/').pop(), size: size.toArray().map(v => +v.toFixed(2)), scale: +s.toFixed(3),
                  hidden, clip: clip && clip.name, clips: gltf.animations.map(c => c.name) });
  }
  return report;
};

// A ready-made rigged character with a speaking role (the dev takes the built dev's seat; others, like
// the boss, just stand in the room): the speech bubble and camera hang from a fixed anchor at the
// character's head, a small mouth mesh is glued to the Head bone for lip-sync, and body language is
// layered on the pose by rotating bones (procedural -- the library clips did not retarget cleanly).
function riggedCharacter(root, g, a) {
  const bone = n => root.getObjectByName(n) || root.getObjectByName(n.replace(/\./g, ''));
  const bones = Object.fromEntries(['Head', 'Neck', 'Chest', 'UpperArm.L', 'LowerArm.L', 'UpperArm.R', 'LowerArm.R', 'LowerLeg.L', 'LowerLeg.R']
    .map(n => [n.replace(/\./g, ''), bone(n)]));
  for (const b of Object.values(bones)) b.userData.base = b.rotation.clone();
  scene.updateMatrixWorld(true);
  const headPos = bones.Head.getWorldPosition(new THREE.Vector3());
  const fwd = new THREE.Vector3(0, 0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), deg(a.yaw || 0));  // Blender -Y = three +Z
  const face = a.face || {};
  const anchor = new THREE.Group();  // static: the bubble must not jiggle with the head
  anchor.position.copy(headPos).addScaledVector(fwd, face.anchorFwd ?? 0).add(new THREE.Vector3(0, face.anchorUp ?? .1, 0));
  anchor.rotation.y = deg((a.yaw || 0) + (face.anchorYaw ?? 22));  // same frame as the built dev's head, so the bubble offsets still apply
  scene.add(anchor);
  const mouth = new THREE.Mesh(new THREE.SphereGeometry(face.mouthR ?? .012, 24, 12), M.mouth);
  mouth.scale.set(1.3, .5, .5);
  bones.Head.add(mouth);
  const side = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0));  // the character's right
  // the mouth offset is measured on the unposed, upright head, then turned the way the pose turned the head
  const turn = a.headRest ? bones.Head.getWorldQuaternion(new THREE.Quaternion()).multiply(a.headRest.clone().invert()) : new THREE.Quaternion();
  const offset = new THREE.Vector3().addScaledVector(fwd, face.mouthFwd ?? .09).addScaledVector(side, face.mouthSide ?? 0)
    .add(new THREE.Vector3(0, face.mouthUp ?? .04, 0)).applyQuaternion(turn);
  mouth.position.copy(bones.Head.worldToLocal(headPos.clone().add(offset)));
  mouth.scale.divide(bones.Head.getWorldScale(new THREE.Vector3()));
  CHAR[a.role] = { rigged: true, root: g, head: anchor, mouth: [mouth], eyes: [], brows: [], bones, headRest: a.headRest };
}

// ---- timeline ----
let T = null;  // from shoot.mjs: {fps, move, turns: [{speaker, text, shot, frame_start, voice_frame, frame_end, cues, beats, mouth}]}
const shotCams = {};  // shot name -> {pos, quat, fov} at the rest pose

function easeInOut(t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

function placeCamera(f) {
  const i = T.turns.findIndex(t => f >= t.frame_start && f <= t.frame_end);
  const turn = T.turns[Math.max(i, 0)];
  const to = shotCams[turn.shot];
  const from = i > 0 ? shotCams[T.turns[i - 1].shot] : to;
  let t = 1;
  if (f < turn.voice_frame) t = easeInOut((f - (turn.frame_start - 1)) / (turn.voice_frame - (turn.frame_start - 1)));
  camera.position.lerpVectors(from.pos, to.pos, t);
  camera.quaternion.slerpQuaternions(from.quat, to.quat, t);
  camera.fov = from.fov + (to.fov - from.fov) * t;
  camera.updateProjectionMatrix();
  return turn;
}

// words of a turn's text: {html word with ** -> bold, chars before it (no spaces, no **), seconds it is spoken}
function words(turn) {
  const out = [];
  let bold = false, chars = 0;
  for (const raw of turn.text.split(/\s+/).filter(Boolean)) {
    let html = '', shown = '';
    for (const piece of raw.split(/(\*\*)/)) {
      if (piece === '**') { bold = !bold; continue; }
      if (!piece) continue;
      html += bold ? `<b>${piece}</b>` : piece;
      shown += piece;
    }
    const cue = turn.cues ? turn.cues.filter(c => c[0] <= chars).pop() : null;
    out.push({ html, chars, t: cue ? cue[1] : (turn.seconds || 3) * .85 * chars / Math.max(1, turn.text.replace(/\s|\*\*/g, '').length) });
    chars += shown.length;
  }
  return out;
}

const bubbleEl = document.getElementById('bubble');
function chunkHtml(ws) { return `<span>${ws.map(w => `<span class="w" data-t="${w.t}">${w.html}</span>`).join(' ')}</span>`; }
function fits(html, w, h, size) {
  bubbleEl.innerHTML = html;
  bubbleEl.style.width = `${w}px`; bubbleEl.style.height = `${h}px`; bubbleEl.style.fontSize = `${size}px`;
  for (const el of bubbleEl.querySelectorAll('.w')) el.classList.add('on');
  return bubbleEl.scrollHeight <= h + 1 && bubbleEl.scrollWidth <= w + 1;
}
// largest font that fits the whole text, else sentence groups at the smallest font (like compose.bubble_chunks)
function layoutTurn(turn) {
  const [x0, y0, x1, y1] = turn.box;
  const w = (x1 - x0) * .68, h = (y1 - y0) * .62;
  const maxSize = Math.round(H * .05), minSize = Math.round(H * .03);
  const ws = words(turn);
  for (let size = Math.min(maxSize, Math.round(h * .4)); size >= minSize; size--) {
    if (fits(chunkHtml(ws), w, h, size)) return { w, h, chunks: [{ html: chunkHtml(ws), size, t: ws[0].t }] };
  }
  const chunks = [];
  let cur = [];
  const endsSentence = (wd) => /[.!?]["”]?$/.test(wd.html.replace(/<\/?b>/g, ''));
  let sentence = [];
  const sentences = [];
  for (const wd of ws) { sentence.push(wd); if (endsSentence(wd)) { sentences.push(sentence); sentence = []; } }
  if (sentence.length) sentences.push(sentence);
  for (const sen of sentences) {
    const trial = [...cur, ...sen];
    if (cur.length && !fits(chunkHtml(trial), w, h, minSize)) { chunks.push(cur); cur = sen; } else cur = trial;
  }
  if (cur.length) chunks.push(cur);
  return { w, h, chunks: chunks.map(c => ({ html: chunkHtml(c), size: minSize, t: c[0].t })) };
}

window.init = function (timeline) {
  T = timeline;
  if (CHAR.dev.rigged) {  // the dev shots hang from the character's head anchor instead of the built head
    for (const name of ['dev_talk', 'dev_explain', 'dev_side', 'dev_top', 'dev_hands', 'dev_face']) {
      SHOTS[name].anchor = CHAR.dev.head;
      SHOTS[name].camera.offset = [0, 0, 0];
      CHAR.dev.head.add(SHOTS[name].bubbleObj.root);
    }
  }
  if (CHAR.boss) for (const name of ['boss_talk', 'boss_dev', 'boss_body', 'boss_hips', 'boss_hipsL', 'boss_front']) {
    SHOTS[name].anchor = CHAR.boss.head;
    CHAR.boss.head.add(SHOTS[name].bubbleObj.root);
  }
  animateBodies(0, T.fps, { dev: 0, claude: 0 });
  for (const who of ['dev', 'claude']) for (const [part, objs] of Object.entries(parts(who))) for (const o of objs) pose(o, Object.values(posesOf(who)[part])[0]);
  scene.updateMatrixWorld(true);
  for (const [name, shot] of Object.entries(SHOTS)) {
    shotFace(camera, shot.anchor, shot.camera);
    shotCams[name] = { pos: camera.position.clone(), quat: camera.quaternion.clone(), fov: camera.fov };
  }
  for (const turn of T.turns) {
    const shot = SHOTS[turn.shot];
    shotFace(camera, shot.anchor, shot.camera);
    turn.box = screenBox(shot.bubbleObj.body);
    turn.layout = layoutTurn(turn);
    turn.beatFrames = (turn.beats || [0]).map(b => turn.voice_frame + Math.round(b * T.fps));
    if (shot.card) turn.cardEl = document.getElementById(`card-${turn.illustration}`);
  }
  bubbleEl.innerHTML = '';
  return { shots: Object.fromEntries(Object.entries(shotCams).map(([k, v]) => [k, v.pos.toArray().map(x => +x.toFixed(3))])) };
};

const FADE = [.25, .5, .75];
let shownChunk = null;

window.renderFrame = function (f) {
  const turn = placeCamera(f);
  const fps = T.fps;
  const speaking = f >= turn.voice_frame && f <= turn.frame_end ? turn : null;
  const k = speaking ? f - turn.voice_frame : -1;
  const level = speaking ? (turn.mouth[k] || 'closed') : 'closed';

  // faces: mouth follows the voice; emphasis for 4 frames from each sentence start; a blink in the pause before it
  const energy = { dev: 0, claude: 0 }, emphasis = {};
  for (const who of ['dev', 'claude']) {
    const P = parts(who);
    const mine = speaking && turn.speaker === who;
    for (const o of P.mouth) pose(o, posesOf(who).mouth[mine ? level : 'closed']);
    const [ePart, ePose] = EMPHASIS[who];
    let eyes = 'rest', emph = false;
    if (mine) {
      for (const bf of turn.beatFrames) {
        if (f >= bf && f < bf + 4 && bf < turn.frame_end) emph = true;
        if (bf !== turn.beatFrames[0] && f === bf - 2 && (turn.mouth[f - turn.voice_frame] || 'closed') === 'closed') eyes = 'blink';
      }
    } else if ((f + (who === 'dev' ? 17 : 41)) % Math.round(fps * 3.3) === 0) eyes = 'blink';  // the listener blinks now and then
    emphasis[who] = emph;
    for (const o of P.eyes) pose(o, posesOf(who).eyes[eyes]);
    for (const o of P[ePart]) if (ePart !== 'eyes' || eyes === 'rest') pose(o, posesOf(who)[ePart][emph ? ePose : Object.keys(posesOf(who)[ePart])[0]]);
    if (mine) {
      let sum = 0, n = 0;  // loudness smoothed over the frames around this one
      for (let d = -2; d <= 2; d++) { const l = turn.mouth[k + d]; if (l) { sum += ENERGY[l]; n++; } }
      energy[who] = n ? sum / n : 0;
    }
  }
  for (const a of assets) if (a.mixer) a.mixer.setTime(f / fps);  // clip time from the frame number: deterministic
  // the dev turns to the boss while the boss speaks, easing over the camera move into and out of that turn
  const ti = T.turns.indexOf(turn), lookOf = t => t && t.speaker === 'boss' ? 1 : 0;
  let look = lookOf(turn);
  if (f < turn.voice_frame && ti > 0) {
    const t = easeInOut((f - (turn.frame_start - 1)) / (turn.voice_frame - (turn.frame_start - 1)));
    look = lookOf(T.turns[ti - 1]) + (look - lookOf(T.turns[ti - 1])) * t;
  }
  animateBodies(f, fps, energy, emphasis, look);

  for (const s of Object.values(SHOTS)) s.bubbleObj.root.visible = !!speaking && s === SHOTS[turn.shot];

  const t0 = performance.now();
  renderer.render(scene, camera);
  const ms = performance.now() - t0;

  // speech text: the chunk on screen is the last one whose first word has been spoken
  const sp = SPEAKER[turn.speaker];
  document.documentElement.style.setProperty('--accent', sp.accent);
  document.documentElement.style.setProperty('--tint', sp.tint);
  if (speaking) {
    const now = (k + 1) / fps;
    const { w, h, chunks } = turn.layout;
    const chunk = [...chunks].reverse().find(c => c.t <= now) || chunks[0];
    if (shownChunk !== chunk) {
      bubbleEl.innerHTML = chunk.html;
      bubbleEl.style.fontSize = `${chunk.size}px`;
      shownChunk = chunk;
    }
    const [x0, y0, x1, y1] = turn.box;
    bubbleEl.style.width = `${w}px`; bubbleEl.style.height = `${h}px`;
    bubbleEl.style.left = `${(x0 + x1) / 2 - w / 2}px`; bubbleEl.style.top = `${(y0 + y1) / 2 - h / 2}px`;
    bubbleEl.style.display = 'flex';
    for (const el of bubbleEl.querySelectorAll('.w')) el.classList.toggle('on', +el.dataset.t <= now);
  } else {
    bubbleEl.style.display = 'none';
    shownChunk = null;
  }

  // cards: up while the turn is spoken, fading in over the move's last frames and out over the next move's first
  for (const el of document.querySelectorAll('.card')) el.style.display = 'none';
  for (const tn of T.turns) {
    if (!tn.cardEl) continue;
    let opacity = 0;
    if (f >= tn.voice_frame && f <= tn.frame_end) opacity = 1;
    else if (f < tn.voice_frame && f >= tn.frame_start && tn.voice_frame - f <= FADE.length) opacity = FADE[FADE.length - (tn.voice_frame - f)];
    else if (f > tn.frame_end && f - tn.frame_end <= FADE.length) opacity = FADE[FADE.length - (f - tn.frame_end)];
    if (!opacity) continue;
    const [cx0, cy0, cx1, cy1] = SHOTS[tn.shot].card;
    Object.assign(tn.cardEl.style, { display: 'block', opacity, left: `${cx0 * W}px`, top: `${cy0 * H}px`,
      width: `${(cx1 - cx0) * W}px`, height: `${(cy1 - cy0) * H}px`, transform: `translateY(${(1 - opacity) * H * .03}px)` });
    const spc = SPEAKER[tn.speaker];
    tn.cardEl.style.setProperty('--accent', spc.accent);
    tn.cardEl.style.setProperty('--tint', spc.tint);
  }
  return { ms };
};
window.renderStill = function (shot, f = 1, look = 0) {  // one frame of a named shot with everyone at rest, no bubble or card
  for (const s of Object.values(SHOTS)) s.bubbleObj.root.visible = false;
  for (const el of document.querySelectorAll('.card')) el.style.display = 'none';
  bubbleEl.style.display = 'none';
  animateBodies(f, T ? T.fps : 12, { dev: 0, claude: 0 }, {}, look);
  for (const a of assets) if (a.mixer) a.mixer.setTime(f / (T ? T.fps : 12));
  shotFace(camera, SHOTS[shot].anchor, SHOTS[shot].camera);
  renderer.render(scene, camera);
};
// Title card: both characters cut out on the page's 2D backdrop (#stage.title), text in HTML.
// opts: {gap, mascotScale, camDist, camHeight, aim} tune the two-shot.
window.renderTitle = function (opts = {}) {
  for (const o of roomParts) o.visible = false;
  for (const s of Object.values(SHOTS)) s.bubbleObj.root.visible = false;
  for (const el of document.querySelectorAll('.card')) el.style.display = 'none';
  bubbleEl.style.display = 'none';
  document.getElementById('stage').classList.add('title');
  document.getElementById('title').style.display = 'block';
  if (opts.h1) document.querySelector('#title h1').innerHTML = opts.h1;    // per-video title text
  if (opts.sub) document.querySelector('#title .sub').innerHTML = opts.sub;
  animateBodies(1, 12, { dev: 0, claude: 0 });
  for (const a of assets) if (a.mixer) a.mixer.setTime(0);
  for (const o of parts('claude').eyes) pose(o, POSE.claude.eyes.wide);
  // the dev's chair stays (it is his), the mascot comes down to the floor beside him, both face the camera
  // portrait: the dev's face and shoulders fill the left half (like the old avatar_dev.png), the mascot
  // floats by his shoulder -- a poster, not a room, so nothing has to stand on the floor
  const yaw = dev.root.rotation.y;
  const fwd = new THREE.Vector3(0, 0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), yaw);
  const right = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0));
  scene.updateMatrixWorld(true);
  if (CHAR.dev.headRest) {  // a portrait looks into the camera: undo the pose's head turn (towards the mascot), keep its tilt
    const h = CHAR.dev.bones.Head;
    const facing = fwd.clone().applyQuaternion(h.getWorldQuaternion(new THREE.Quaternion()).multiply(CHAR.dev.headRest.clone().invert()));
    turnAboutUp(h, Math.atan2(fwd.x, fwd.z) - Math.atan2(facing.x, facing.z));
    scene.updateMatrixWorld(true);
  }
  const head = CHAR.dev.head.getWorldPosition(new THREE.Vector3());
  claude.root.position.copy(head).addScaledVector(fwd, opts.gap ?? .5).addScaledVector(right, opts.side ?? .04).add(new THREE.Vector3(0, opts.mascotUp ?? -.3, 0));
  claude.root.rotation.y = yaw + deg(opts.mascotTurn ?? 25);
  claude.root.scale.setScalar(opts.mascotScale ?? .8);
  claude.root.visible = !!opts.mascot3d;  // default: the 2D avatar in index.html (#title-mascot) plays the mascot
  const aim = head.clone().addScaledVector(right, opts.aimSide ?? -.28).add(new THREE.Vector3(0, opts.aim ?? -.08, 0));
  camera.position.copy(head).addScaledVector(fwd, opts.camDist ?? 1.5).addScaledVector(right, opts.camSide ?? -.1).add(new THREE.Vector3(0, opts.camHeight ?? .05, 0));
  camera.fov = opts.fov ?? 32;
  camera.lookAt(aim);
  camera.updateProjectionMatrix();
  renderer.setClearColor(0x000000, 0);
  renderer.render(scene, camera);
};
window.gpu = () => { const gl = renderer.getContext(); const ext = gl.getExtension('WEBGL_debug_renderer_info'); return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unknown'; };
window.ready = true;
