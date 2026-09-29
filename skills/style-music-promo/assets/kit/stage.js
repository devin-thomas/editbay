// The hook's 3D stage: every release cover as a wall that scrolls with the in-app flings and pulses on the 808s,
// then gathers into an orbiting sphere with a spectrum ring for the flurry, and implodes as the hook ends.
// Pure function of time: render(t) derives every position and colour from t and the song analysis.
// Trailer-shaped: it needs every window.STAGE.phase time (see kit.md). For the ring alone use ring.js.
// window.STAGE: {start, end, W, H, fov, events: {bass (track_map events.grid.bass; "b808" also read), clap},
//   flings: [[t, v]...], flingTau, phase: {enter, wallTurn, morphStart, morphEnd, swap1, flurry, swap2, ringIn,
//   ringOut, implodeStart, implodeEnd}, art: [file names], artDir ("assets/art256/"), canvas ("stage"),
//   cols (28), rows (26: two stacked copies of a 13-row wall, so the scroll wraps)}. window.AUD: {fps, features, bands}.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const CFG0 = window.STAGE, W = CFG0.W, H = CFG0.H, SS = 2; // drawn at 2x, shown at W x H
const CFG = window.STAGE; // written by build.py: times, events, art list
const AUD = window.AUD;
const T0 = CFG.start, T1 = CFG.end;
const BASS = CFG.events.bass || CFG.events.b808 || []; // track_map writes events.bass; the trailer's build named it b808
for (const k of ["enter", "wallTurn", "morphStart", "morphEnd", "swap1", "flurry", "swap2", "ringIn", "ringOut", "implodeStart", "implodeEnd"])
  if (typeof (CFG.phase || {})[k] !== "number") throw new Error("stage.js: window.STAGE.phase." + k + " missing (see kit.md)");

const canvas = document.getElementById(CFG.canvas || "stage");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W * SS, H * SS, false);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x020304, 13, 40);
const camera = new THREE.PerspectiveCamera(CFG0.fov, W / H, 0.1, 400);

const composer = new EffectComposer(renderer);
composer.setPixelRatio(1);
composer.setSize(W * SS, H * SS);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W * SS, H * SS), 0.75, 0.55, 0.62);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---------- helpers ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const easeOutExpo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp(x)));
const easeInOutCubic = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const lerp = (a, b, k) => a + (b - a) * k;
function frameOf(t) { return Math.max(0, Math.min(AUD.features.mix.length - 1, Math.round(t * AUD.fps))); }
function feat(name, t) { return AUD.features[name][frameOf(t)] || 0; }
// sum of decaying pulses from a list of hit times
function pulse(times, t, tau) {
  let v = 0;
  for (const h of times) { const d = t - h; if (d >= 0 && d < tau * 6) v += Math.exp(-d / tau); }
  return v;
}
// scroll position from fling impulses: each impulse adds velocity that decays exponentially
function scrollAt(t) {
  let p = 0;
  for (const [ti, a] of CFG.flings) { const d = t - ti; if (d > 0) p += a * CFG.flingTau * (1 - Math.exp(-d / CFG.flingTau)); }
  return p;
}

// ---------- covers ----------
function roundedGeo(size, r) {
  const s = size / 2, sh = new THREE.Shape();
  sh.moveTo(-s + r, -s); sh.lineTo(s - r, -s); sh.quadraticCurveTo(s, -s, s, -s + r); sh.lineTo(s, s - r);
  sh.quadraticCurveTo(s, s, s - r, s); sh.lineTo(-s + r, s); sh.quadraticCurveTo(-s, s, -s, s - r); sh.lineTo(-s, -s + r);
  sh.quadraticCurveTo(-s, -s, -s + r, -s);
  const g = new THREE.ShapeGeometry(sh, 6), uv = g.attributes.uv, pos = g.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / size + 0.5, pos.getY(i) / size + 0.5);
  return g;
}
const COVER = 1.0, GAP = 0.14, PITCH = COVER + GAP;
const geo = roundedGeo(COVER, 0.1);
const loader = new THREE.TextureLoader();
const COLS = CFG.cols || 28, ROWS = CFG.rows || 26, HALF = ROWS / 2; // two stacked copies of a wall, so the scroll wraps
const covers = [];
const group = new THREE.Group();
scene.add(group);
const textures = CFG.art.map((f) => {
  const tx = loader.load((CFG.artDir || "assets/art256/") + f);
  tx.colorSpace = THREE.SRGBColorSpace;
  tx.anisotropy = 4;
  return tx;
});
// deterministic shuffle so neighbouring covers differ
function rng(seed) { return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let x = Math.imul(seed ^ (seed >>> 15), 1 | seed); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }
const rand = rng(1729);
const order = textures.map((_, i) => i).sort(() => rand() - 0.5);
const N = COLS * ROWS;
// sphere targets (Fibonacci), same count as covers
const sphere = [];
for (let i = 0; i < N; i++) {
  const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = i * Math.PI * (3 - Math.sqrt(5));
  sphere.push(new THREE.Vector3(Math.cos(th) * r, y, Math.sin(th) * r));
}
for (let i = 0; i < N; i++) {
  const c = i % COLS, r = Math.floor(i / COLS);
  const mat = new THREE.MeshBasicMaterial({ map: textures[order[i % textures.length]], transparent: true, side: THREE.DoubleSide, fog: true });
  const m = new THREE.Mesh(geo, mat);
  const d = Math.hypot(c - (COLS - 1) / 2, (r % HALF) - (HALF - 1) / 2);
  covers.push({ m, c, r, d, seed: rand(), sph: sphere[(i * 97) % N] });
  group.add(m);
}

// spectrum ring
const RING = 72;
const barGeo = new THREE.BoxGeometry(0.09, 1, 0.09);
barGeo.translate(0, 0.5, 0);
const ring = new THREE.Group();
scene.add(ring);
const bars = [];
for (let i = 0; i < RING; i++) {
  const mat = new THREE.MeshBasicMaterial({ color: 0x4dffff, transparent: true, fog: false });
  const b = new THREE.Mesh(barGeo, mat);
  const a = (i / RING) * Math.PI * 2;
  b.position.set(Math.cos(a) * 4.6, Math.sin(a) * 4.6, 0);
  b.rotation.z = a - Math.PI / 2;
  bars.push(b); ring.add(b);
}

// sphere spin: slow drift, a push on "changed my phone", then fast through the flurry
function spinAt(t) {
  const P = CFG.phase;
  return 0.16 * (t - T0) + 1.1 * smooth((t - P.swap1) / 0.7) + 2.8 * smooth((t - P.flurry) / 2.2) + 1.0 * smooth((t - P.swap2) / 0.7);
}
const qWall = new THREE.Quaternion(), qLook = new THREE.Quaternion(), mLook = new THREE.Matrix4(), EUL = new THREE.Euler(), UP = new THREE.Vector3(0, 1, 0);

// ---------- the render ----------
const V = new THREE.Vector3();
function render(t) {
  if (t < T0 - 0.05 || t > T1 + 0.05) return;
  const lt = t - T0;
  const kick = pulse(BASS, t, 0.16), clap = pulse(CFG.events.clap || [], t, 0.12);
  const scroll = scrollAt(t);
  const P = CFG.phase; // phase boundaries
  // wall -> sphere morph and final implode
  const morph = easeInOutCubic((t - P.morphStart) / (P.morphEnd - P.morphStart));
  const implode = easeInOutCubic((t - P.implodeStart) / (P.implodeEnd - P.implodeStart));
  const spin = spinAt(t);
  // camera: slow drift, clap kicks
  const camZ = lerp(15.5, 17.5, smooth((t - P.morphStart) / 2.5)) - 0.35 * clap;
  camera.position.set(Math.sin(lt * 0.23) * 0.6, Math.cos(lt * 0.19) * 0.35, camZ);
  camera.fov = CFG.fov - 1.2 * clap;
  camera.updateProjectionMatrix();
  camera.lookAt(0, 0, 0);
  // wall orientation eases from a receding angle to frontal as the phrases move on
  const yaw = lerp(-0.42, 0.22, smooth((t - P.wallTurn) / 3.0));
  for (const cv of covers) {
    const { m, c, r, d, seed, sph } = cv;
    // entrance: fly in from depth, staggered from the centre out
    const enter = easeOutExpo((t - (P.enter + d * 0.018)) / 0.55);
    let wx = (c - (COLS - 1) / 2) * PITCH;
    let wy = ((r * PITCH + scroll) % (ROWS * PITCH)) - (ROWS * PITCH) / 2 + PITCH / 2;
    let wz = lerp(-60, 0, enter);
    // rotate the wall plane
    const cx = wx * Math.cos(yaw), cz = wz - wx * Math.sin(yaw) - 4;
    // sphere target (radius breathes with the kick)
    const R = 8.2 + 0.35 * kick;
    V.copy(sph).applyAxisAngle(new THREE.Vector3(0, 1, 0), spin).applyAxisAngle(new THREE.Vector3(1, 0, 0), 0.35);
    const sx = V.x * R, sy = V.y * R, sz = V.z * R - 6;
    let x = lerp(cx, sx, morph), y = lerp(wy, sy, morph), z = lerp(cz, sz, morph);
    // implode to the centre
    x *= 1 - implode; y *= 1 - implode; z = lerp(z, -6, implode);
    m.position.set(x, y, z);
    qWall.setFromEuler(EUL.set(0, yaw, 0));
    mLook.lookAt(camera.position, m.position, UP); qLook.setFromRotationMatrix(mLook);
    m.quaternion.slerpQuaternions(qWall, qLook, morph);
    const s = (1 + 0.06 * kick * Math.exp(-d * 0.12)) * (1 - 0.7 * implode);
    m.scale.setScalar(Math.max(0.001, s));
    // brightness: a kick wave spreading from the centre, claps flash everything a little
    let wave = 0;
    for (const h of BASS) { const dd = t - h - d * 0.025; if (dd >= 0 && dd < 0.6) wave += Math.exp(-dd / 0.14); }
    const b = 0.21 + 0.5 * wave + 0.18 * clap + 0.1 * feat("mel", t);
    m.material.color.setScalar(Math.min(1.6, b));
    m.material.opacity = enter * (1 - implode);
  }
  // spectrum ring
  const ringOn = smooth((t - P.ringIn) / 0.4) * (1 - smooth((t - P.ringOut) / 0.35));
  ring.visible = ringOn > 0.001;
  ring.position.set(0, 0, 2.2);
  ring.rotation.z = spin * 0.5;
  const fr = frameOf(t), bands = AUD.bands[fr] || [];
  for (let i = 0; i < RING; i++) {
    const k = i < RING / 2 ? i : RING - 1 - i;               // mirrored
    const v = (bands[Math.floor((k / (RING / 2)) * 32)] || 0) / 99;
    const h = 0.12 + 2.6 * Math.pow(v, 2.2) * (0.6 + 0.8 * feat("mix", t));
    bars[i].scale.set(1, h * ringOn, 1);
    bars[i].material.opacity = 0.85 * ringOn;
  }
  bloom.strength = 0.55 + 0.5 * kick + 0.25 * clap;
  composer.render();
}

window.__stage = { render };
window.addEventListener("hf-seek", (e) => render(e.detail.time));
THREE.DefaultLoadingManager.onLoad = () => render(window.__hfThreeTime || window.__stageTime || 0);
render(window.__hfThreeTime || 0);
