// Main timeline. Every time here is trailer time; H[n] is the downbeat of bar n, CL[i] the hook claps (beat 3).
const S = window.SHOT, AUD = window.AUD, H = S.H, CL = S.CLAP, PER = S.PER, W1 = S.W1, W2 = S.W2;
// V: the 9:16 cut. Same beats, same footage; devices sit larger and lower, type lives in the top band.
const V = !!S.V, pick = (h, v) => (V ? v : h);
const tl = gsap.timeline({ paused: true });
const at = (t, target, vars) => tl.to(target, vars, t);
const set = (t, target, vars) => tl.set(target, vars, t);
const fromTo = (t, target, a, b) => tl.fromTo(target, a, b, t);
const $ = (id) => document.getElementById(id);
const frameOf = (t) => Math.max(0, Math.min(AUD.features.mix.length - 1, Math.round(t * AUD.fps)));

// ---------------------------------------------------------------- touches (positions are layout, set once)
S.TOUCHES.forEach((tc, k) => {
  const el = $("t" + k), [w, h] = S.SCREEN[tc.dev];
  el.style.left = (tc.x / w) * 100 + "%";
  el.style.top = (tc.y / h) * 100 + "%";
  if (tc.kind === "tap") {
    fromTo(tc.t, el, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.07, ease: "power2.out" });
    at(tc.t + 0.14, el, { opacity: 0, scale: 1.75, duration: 0.36, ease: "power2.out" });
  } else {
    const px = tc.dev === "pad" ? 1040 / 1376 : 372 / 402;
    fromTo(tc.t, el, { opacity: 0, scale: 0.7, x: 0, y: 0 }, { opacity: 1, scale: 1, duration: 0.05 });
    at(tc.t, el, { x: (tc.x1 - tc.x) * px, y: (tc.y1 - tc.y) * px, duration: Math.max(0.08, tc.t1 - tc.t), ease: "power1.in" });
    at(tc.t1, el, { opacity: 0, scale: 0.6, duration: 0.16, ease: "power2.out" });
  }
});

// ---------------------------------------------------------------- initial states
set(0, ["#pad", "#fl"], { opacity: 0, x: 0, y: 0, z: 0, rotationX: 0, rotationY: 0, rotationZ: 0, scale: 1, filter: "none" });
set(0, "#ph", { z: 0, rotationZ: 0, filter: "none" });
set(0, ["#padz", "#flz"], { x: 0, y: 0, scale: 1, filter: "none", transformOrigin: "50% 50%" });
set(0, "#phz", { x: 0, filter: "none" });
set(0, "#devs", { scale: 1, y: 0, transformOrigin: "50% 50%" });
fromTo(0, ".glare", { x: -220 }, { x: 220, duration: S.DUR, ease: "none" });

// ---------------------------------------------------------------- 0 - 5.34: press play, Now Playing, into the icon
// macro on the song row and the mini player: the real tap (0.955) and the play -> pause flip (1.44) read big,
// then the camera pulls back to the whole phone on the first note
// frame 0 is rendered before the timeline's zero-duration sets apply, so the opening state is also set on load
const OPEN_PH = { opacity: 1, x: 0, y: 0, rotationY: -12, rotationX: 6, scale: pick(1.0, 1.45) };
const OPEN_PHZ = { transformOrigin: "196px 600px", scale: pick(2.25, 2.0), y: -185.5 };
gsap.set("#ph", OPEN_PH); gsap.set("#phz", OPEN_PHZ);
set(0, "#ph", OPEN_PH);
set(0, "#phz", OPEN_PHZ);
at(0, "#ph", { rotationY: -7, rotationX: 4, duration: S.PRE, ease: "sine.inOut" });
at(0, "#phz", { scale: pick(2.08, 1.86), duration: S.PRE, ease: "sine.inOut" });
at(S.PRE, "#phz", { scale: 1, y: 0, duration: 1.4, ease: "power3.inOut" });
at(S.PRE, "#ph", { ...pick({ x: 20, y: 10, rotationY: -9, rotationX: 2, scale: 1.0 }, { x: 0, y: -110, rotationY: -8, rotationX: 3, scale: 1.62 }), duration: 1.95, ease: "power3.inOut" });
set(H[2], "#ph", pick({ x: -150, y: 20, rotationY: 15, rotationX: -3, scale: 1.12 }, { x: -30, y: -80, rotationY: 14, rotationX: -3, scale: 1.78 }));   // cut on bar 2
at(H[2], "#ph", { ...pick({ x: -110, rotationY: 11, scale: 1.16 }, { x: -12, rotationY: 10, scale: 1.84 }), duration: 0.95, ease: "sine.out" });
// the home screen is up by 4.24: glide to front and push into the Lil Gohan icon
at(4.42, "#ph", { x: 0, y: 0, rotationY: 0, rotationX: 0, scale: 1.0, duration: 0.92, ease: "power2.in" });
set(4.42, "#phz", { transformOrigin: "324.6px 215.4px" });
at(4.42, "#phz", { x: -128.6, y: 199.1, scale: 17, duration: 0.92, ease: "expo.in" });
at(5.12, "#phz", { filter: "blur(7px)", duration: 0.22, ease: "power1.in" });
fromTo(4.25, "#homePatch", { opacity: 0 }, { opacity: 1, duration: 0.17, ease: "power1.out" });
set(H[3] + 0.05, "#homePatch", { opacity: 0 });
set(H[3], "#ph", { opacity: 0 });
set(H[3] + 0.02, "#phz", { x: 0, y: 0, scale: 1, filter: "none", transformOrigin: "50% 50%" });
set(H[3], "#flash", { opacity: 0.9 });
at(H[3], "#flash", { opacity: 0, duration: 0.42, ease: "power2.out" });

// ---------------------------------------------------------------- 16.86 DROP: the catalog
set(H[9], "#flash", { opacity: 1 });
at(H[9], "#flash", { opacity: 0, duration: 0.34, ease: "power2.out" });
set(H[9], "#ph", { opacity: 1, rotationZ: 0, ...pick({ x: -110, y: 0, rotationY: 6, rotationX: 2, scale: 1.8 }, { x: 0, y: 250, rotationY: 4, rotationX: 2, scale: 2.2 }) });
at(H[9], "#ph", { ...pick({ x: -250, rotationY: 17, rotationX: 3, scale: 1.04 }, { x: 0, y: 225, rotationY: 10, rotationX: 3, scale: 1.40 }), duration: 0.55, ease: "expo.out" });
at(H[9] + 0.55, "#ph", { ...pick({ rotationY: 13, x: -270 }, { rotationY: 7, x: 0 }), duration: 0.41, ease: "sine.out" });
// clap 1: 663 songs
at(CL[0], "#ph", { ...pick({ x: 400, rotationY: -19, rotationX: 2, scale: 0.98 }, { x: 0, y: 265, rotationY: -10, rotationX: 2, scale: 1.30 }), duration: 0.42, ease: "power3.out" });
fromTo(CL[0], "#st1", { opacity: 0, scale: 1.22, x: pick(-26, 0), filter: "blur(12px)", transformOrigin: pick("0% 50%", "50% 50%") },
       { opacity: 1, scale: 1, x: 0, filter: "blur(0px)", duration: 0.24, ease: "power3.out" });
// bar 10: the iPad takes over
at(H[10], "#st1", { opacity: 0, y: -40, duration: 0.24, ease: "power2.in" });
at(H[10], "#ph", { x: pick(-1250, -1100), rotationY: 45, opacity: 0, duration: 0.34, ease: "power3.in" });
set(H[10], "#pad", { opacity: 1, ...pick({ x: 1300, y: 10, rotationY: -32, rotationX: 3, scale: 0.9 }, { x: 1200, y: 200, rotationY: -30, rotationX: 3, scale: 0.95 }) });
at(H[10], "#pad", { ...pick({ x: 190, rotationY: -15 }, { x: 0, rotationY: -12 }), duration: 0.55, ease: "expo.out" });
// clap 2: 27 hours
at(CL[1], "#pad", { ...pick({ x: 300, rotationY: -19, scale: 0.86 }, { x: 0, y: 255, rotationY: -16, scale: 0.9 }), duration: 0.4, ease: "power3.out" });
fromTo(CL[1], "#st2", { opacity: 0, scale: 1.22, x: pick(-26, 0), filter: "blur(12px)", transformOrigin: pick("0% 50%", "50% 50%") },
       { opacity: 1, scale: 1, x: 0, filter: "blur(0px)", duration: 0.24, ease: "power3.out" });
// bar 11: back to the iPhone, Albums then Collections (real taps on the beat)
at(H[11], "#st2", { opacity: 0, y: -40, duration: 0.22, ease: "power2.in" });
at(H[11], "#pad", { x: pick(1500, 1300), rotationY: -40, opacity: 0, duration: 0.3, ease: "power3.in" });
set(H[11], "#ph", { opacity: 1, ...pick({ x: 900, y: 0, rotationY: -34, rotationX: 2, scale: 1.0 }, { x: 900, y: 255, rotationY: -34, rotationX: 2, scale: 1.33 }) });
at(H[11], "#ph", { ...pick({ x: 330, rotationY: -15 }, { x: 0, rotationY: -12 }), duration: 0.45, ease: "expo.out" });
fromTo(H[11] + 0.06, "#cp1", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.26, ease: "power3.out" });
at(CL[2], "#cp1", { opacity: 0, y: -22, duration: 0.16, ease: "power2.in" });
fromTo(CL[2] + 0.06, "#cp2", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.26, ease: "power3.out" });
at(CL[2], "#ph", { rotationY: pick(-9, -6), x: pick(310, 0), duration: 0.5, ease: "power2.out" });
// bar 12: iPad, Home, and the sidebar folding on the clap
at(H[12], "#cp2", { opacity: 0, y: -22, duration: 0.18, ease: "power2.in" });
at(H[12], "#ph", { x: pick(-1300, -1100), rotationY: 40, opacity: 0, duration: 0.3, ease: "power3.in" });
set(H[12], "#pad", { opacity: 1, ...pick({ x: 60, y: 20, rotationY: 16, rotationX: 4, scale: 0.72 }, { x: 40, y: 180, rotationY: 16, rotationX: 4, scale: 0.7 }) });
at(H[12], "#pad", { ...pick({ scale: 1.0, rotationY: 9, x: 0, y: 0 }, { scale: 0.98, rotationY: 9, x: 0, y: 120 }), duration: 0.6, ease: "expo.out" });
at(CL[3], "#pad", { ...pick({ rotationY: -7, rotationX: 2, x: 20, scale: 1.04 }, { rotationY: -7, rotationX: 2, x: 8, scale: 1.0 }), duration: 0.5, ease: "power3.out" });
// bar 13: iPhone, Producers, Now Playing rises; the covers gather into a sphere
at(H[13], "#pad", { scale: 0.7, opacity: 0, duration: 0.22, ease: "power2.in" });
set(H[13], "#ph", { opacity: 1, x: 0, ...pick({ y: 30, rotationY: -12, rotationX: 5, scale: 0.9 }, { y: 290, rotationY: -12, rotationX: 5, scale: 1.24 }) });
at(H[13], "#ph", { ...pick({ y: 0, rotationY: -4, rotationX: 2, scale: 1.08 }, { y: 230, rotationY: -4, rotationX: 2, scale: 1.38 }), duration: 0.6, ease: "expo.out" });
at(H[13] + 0.6, "#ph", { rotationY: 6, scale: pick(1.14, 1.43), duration: W1.changed - H[13] - 0.6, ease: "sine.inOut" });
fromTo(24.99, "#cp3", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.26, ease: "power3.out" });
at(25.78, "#cp3", { opacity: 0, y: -22, duration: 0.2, ease: "power2.in" });
// "I changed my phone": the iPhone turns into the iPad
at(W1.changed, "#ph", { rotationZ: -90, rotationY: 0, scale: pick(1.34, 1.25), filter: "blur(10px)", duration: 0.26, ease: "power3.in" });
at(W1.changed + 0.2, "#ph", { opacity: 0, duration: 0.07 });
set(W1.changed + 0.27, "#ph", { rotationZ: 0, filter: "none" });
set(W1.changed + 0.16, "#pad", { opacity: 0, x: 0, y: pick(0, 150), rotationX: 0, rotationY: 0, rotationZ: 26, scale: 0.8, filter: "blur(10px)" });
at(W1.changed + 0.16, "#pad", { opacity: 1, duration: 0.08 });
at(W1.changed + 0.16, "#pad", { rotationZ: 0, scale: pick(0.97, 0.96), filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
set(W1.changed + 0.67, "#pad", { filter: "none" });
at(W1.changed + 0.67, "#pad", { rotationY: -8, rotationX: 2, scale: pick(1.02, 0.99), duration: H[15] - W1.changed - 0.67, ease: "sine.inOut" });
// flurry: features on half beats
at(H[15] - 0.12, "#pad", { scale: 0.8, opacity: 0, duration: 0.12, ease: "power2.in" });
S.FLURRY.forEach(([t0, t1, label], k) => {
  const side = k % 2 ? 1 : -1;
  if (k === 0) set(t0, "#fl", { opacity: 1 });
  fromTo(t0, "#fl", pick({ x: 330 + 140 * side, rotationY: -26 * side, rotationX: 3, rotationZ: 0, scale: 1.08, y: 0 },
                          { x: 90 * side, rotationY: -22 * side, rotationX: 3, rotationZ: 0, scale: 1.40, y: 290 }),
         { ...pick({ x: 330, rotationY: -12 * side, scale: 1.0 }, { x: 0, rotationY: -10 * side, scale: 1.32 }), duration: Math.min(0.2, t1 - t0), ease: "expo.out" });
  fromTo(t0, "#fl" + k, { opacity: 0, x: pick(-30 * side, 0), y: pick(0, 16) }, { opacity: 1, x: 0, y: 0, duration: 0.12, ease: "power3.out" });
  set(t1 - 0.005, "#fl" + k, { opacity: 0 });
});
set(H[16], "#fl", { opacity: 0 });
// bar 16: the iPad again, then "had to change my phone" turns it back into the iPhone
set(H[16], "#pad", { opacity: 1, x: 0, y: pick(0, 150), rotationX: 2, rotationY: 10, rotationZ: 0, scale: pick(0.9, 0.92), filter: "none" });
at(H[16], "#pad", { rotationY: 4, scale: pick(0.97, 0.97), duration: 0.34, ease: "expo.out" });
at(W2.change, "#pad", { rotationZ: 90, rotationY: 0, scale: 0.7, filter: "blur(10px)", duration: 0.26, ease: "power3.in" });
at(W2.change + 0.2, "#pad", { opacity: 0, duration: 0.07 });
set(W2.change + 0.16, "#ph", { opacity: 0, x: 0, y: pick(0, 170), rotationX: 0, rotationY: 0, rotationZ: -26, scale: pick(1.3, 1.72), filter: "blur(10px)" });
at(W2.change + 0.16, "#ph", { opacity: 1, duration: 0.08 });
at(W2.change + 0.16, "#ph", { rotationZ: 0, scale: pick(1.0, 1.42), filter: "blur(0px)", duration: 0.5, ease: "expo.out" });
set(W2.change + 0.67, "#ph", { filter: "none" });
// push in on the play/pause control; the real pause lands at S.STOP
set(W2.phone, "#phz", { transformOrigin: "196px 703.4px" });
at(W2.phone, "#phz", { y: pick(-288.9, -408), scale: 2.05, duration: S.STOP - W2.phone - 0.08, ease: "power2.inOut" });
at(W2.phone, "#ph", { rotationY: -3, rotationX: 4, duration: S.STOP - W2.phone, ease: "sine.inOut" });
// cut to the glass lockup
set(S.CUT_LOCK, "#ph", { opacity: 0 });
set(S.CUT_LOCK, "#flash", { opacity: 0.55 });
at(S.CUT_LOCK, "#flash", { opacity: 0, duration: 0.5, ease: "power2.out" });
// lockup type on the echo repeats: repeat k is heard at S.ECHO0 + k beats (its loudest transient, not its window end)
const echo = (k) => S.ECHO0 + k * PER;
fromTo(echo(2), "#lockName", { opacity: 0, y: 22, filter: "blur(10px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.7, ease: "power3.out" });
fromTo(echo(3), "#lockSoon", { opacity: 0, y: 16, filter: "blur(8px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, ease: "power3.out" });
fromTo(echo(4), "#lockDev", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" });
at(H[19] - 0.34, "#black", { opacity: 1, duration: 0.3, ease: "power1.in" });
// studio
set(H[19], "#black", { opacity: 0 });
set(H[19], "#lock", { opacity: 0 });
set(H[19], "#studio", { opacity: 1 });
fromTo(H[19], "#badgeWrap", { scale: 1.14, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.8, ease: "expo.out" });
fromTo(H[19] + 0.26, "#sweep", { "--sx": "0px" }, { "--sx": "560px", duration: 0.95, ease: "power2.inOut" });
fromTo(H[19] + 0.48, "#studioName", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.7, ease: "power3.out" });
fromTo(H[19] + 0.8, "#badgeWrap", { y: 0 }, { y: -6, duration: S.DUR - H[19] - 0.8, ease: "sine.inOut" });   // hold the badge to the last frame

// the scrim sits under the type whenever a stat, caption or flurry label is up
[[CL[0], H[10]], [CL[1], H[11]], [H[11], H[12]], [24.95, 25.8], [H[15], H[16]]].forEach(([a, b]) => {
  at(a - 0.04, "#scrim", { opacity: 1, duration: 0.18, ease: "power2.out" });
  at(b - 0.12, "#scrim", { opacity: 0, duration: 0.2, ease: "power2.in" });
});

// ---------------------------------------------------------------- beat pulses on the device layer
window.STAGE.events.b808.forEach((t) => fromTo(t, "#devs", { scale: 1.016 }, { scale: 1, duration: 0.26, ease: "power2.out" }));
CL.forEach((t) => fromTo(t, "#devs", { y: 5 }, { y: 0, duration: 0.2, ease: "power2.out" }));

// ---------------------------------------------------------------- per-frame drawing (waveform, glow, grain, 3D stage)
const wave = $("wave"), wctx = wave.getContext("2d");
const PK = AUD.wave.peaks, PK_DT = AUD.wave.dur / PK.length;
const grad = wctx.createLinearGradient(0, 40, 0, 280);
grad.addColorStop(0, "#9ffcff"); grad.addColorStop(1, "#27c7d6");
const WW = pick(1920, 1080), WH = pick(560, 420), CX = WW / 2;
function drawWave(t) {
  wctx.setTransform(2, 0, 0, 2, 0, 0);   // canvas is 2x; draw in WW x WH units
  wctx.clearRect(0, 0, WW, WH);
  const s = t - S.PRE, PX = pick(240, 170), PITCH = 6, MID = pick(280, 250);
  const vis = Math.min(1, Math.max(0, (t - 0.15) / 0.5)) * (1 - Math.min(1, Math.max(0, (t - 4.25) / 0.4)));
  if (vis <= 0) return;
  wctx.globalAlpha = vis;
  for (let i = 0; i < WW / PITCH; i++) {
    const x = i * PITCH, bs = Math.max(0, s) + (x + PITCH / 2 - CX) / PX;       // song time under this bar
    let amp = 0;
    if (bs >= 0) {
      const a = Math.floor(bs / PK_DT), b = Math.floor((bs + PITCH / PX) / PK_DT);
      for (let k = a; k <= b && k < PK.length; k++) amp = Math.max(amp, Math.abs(PK[k][0]), Math.abs(PK[k][1]));
    }
    const h = 3 + amp * pick(200, 170), played = x + PITCH / 2 < CX && s > 0;
    const edge = Math.min(1, Math.min(x, WW - x) / pick(260, 140));
    wctx.globalAlpha = vis * edge;
    wctx.fillStyle = played ? grad : "#39404a";
    wctx.fillRect(x, MID - h, PITCH - 2, h);
    wctx.globalAlpha = vis * edge * 0.28;
    wctx.fillRect(x, MID + 3, PITCH - 2, h * 0.42);
  }
  wctx.globalAlpha = vis;
  wctx.fillStyle = "#e9ffff";
  wctx.fillRect(CX - 1, MID - pick(236, 200), 2, pick(330, 280));
}
const glow = $("glow"), grain = $("grain"), st1n = $("st1n");
function frame(t) {
  window.__stageTime = t;
  drawWave(t);
  const f = frameOf(t), mel = AUD.features.mel[f] || 0, bass = AUD.features.bass[f] || 0;
  const g = t < 5.34 ? 0.3 + 0.8 * mel : (t > 16.8 && t < 32.8 ? 0.25 + 0.6 * bass : 0);
  glow.style.opacity = g.toFixed(3);
  const n = Math.floor(t * 24), gx = (n * 73) % 64, gy = (n * 151) % 64;
  grain.style.transform = `translate(${gx}px, ${gy}px)`;
  const cp = Math.min(1, Math.max(0, (t - CL[0]) / 0.55));
  st1n.textContent = String(Math.round(663 * (1 - Math.pow(1 - cp, 2.4))));
  if (window.__stage) window.__stage.render(t);
}
const clock = { t: 0 };
tl.to(clock, { t: S.DUR, duration: S.DUR, ease: "none", onUpdate: () => frame(clock.t) }, 0);
frame(0);
window.__timelines["main"] = tl;
