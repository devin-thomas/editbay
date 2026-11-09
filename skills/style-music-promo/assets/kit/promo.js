// Timeline helpers for music promos (GSAP, one paused timeline). Load after gsap and the map/shot data.
//   const K = makePromo(tl, { vertical: false, fps: 60 });
//   K.pick(h, v)                     landscape value or portrait value (one pose table, two layouts)
//   K.touches(list, screens)         real taps and drags from the performance log (see app-capture)
//   K.pulses(times808, clapTimes)    device-layer pulses on the beat
//   K.driver(duration, fn)           per-frame callback fn(T) for canvases and counters (a proxy tween: seek-safe)
//   K.openState(target, vars)        state that must show on frame 0 (zero-duration sets at 0 don't render frame 0)
//   K.bloom(sel, t, peak)            the hit: an accent bloom on the mark (additive), held 2 frames, gone in 0.25 s
//   K.flatMark(sel, cue)             the no-GPU motif (mark.css): clear -> reveal -> fill on the hit -> echo pulses
// Every fromTo here passes immediateRender: false. GSAP renders a fromTo's from-values when the tween is created,
// so without it a pulse layer sits at scale 1.016 and 5 px low from frame 0 until its first hit.
window.makePromo = function (tl, opts) {
  const V = !!opts.vertical, FPS = opts.fps || 60, IR = { immediateRender: false };
  const $ = (sel) => (typeof sel === "string" ? document.querySelector(sel) : sel);
  const K = {
    pick: (h, v) => (V ? v : h),
    touches(list, screens, pxPerPt = { ph: 372 / 402, pad: 1040 / 1376, fl: 372 / 402 }) {
      list.forEach((tc, k) => {
        const el = document.getElementById("t" + k), [w, h] = screens[tc.dev];
        el.style.left = (tc.x / w) * 100 + "%"; el.style.top = (tc.y / h) * 100 + "%";
        if (tc.kind === "tap") {
          tl.fromTo(el, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.07, ease: "power2.out", ...IR }, tc.t);
          tl.to(el, { opacity: 0, scale: 1.75, duration: 0.36, ease: "power2.out" }, tc.t + 0.14);
        } else {
          const px = pxPerPt[tc.dev];
          tl.fromTo(el, { opacity: 0, scale: 0.7, x: 0, y: 0 }, { opacity: 1, scale: 1, duration: 0.05, ...IR }, tc.t);
          tl.to(el, { x: (tc.x1 - tc.x) * px, y: (tc.y1 - tc.y) * px, duration: Math.max(0.08, tc.t1 - tc.t), ease: "power1.in" }, tc.t);
          tl.to(el, { opacity: 0, scale: 0.6, duration: 0.16, ease: "power2.out" }, tc.t1);
        }
      });
    },
    pulses(t808, claps, layer = "#devs") {
      t808.forEach((t) => tl.fromTo(layer, { scale: 1.016 }, { scale: 1, duration: 0.26, ease: "power2.out", ...IR }, t));
      claps.forEach((t) => tl.fromTo(layer, { y: 5 }, { y: 0, duration: 0.2, ease: "power2.out", ...IR }, t));
    },
    driver(duration, fn) {
      const clock = { t: 0 };
      tl.to(clock, { t: duration, duration, ease: "none", onUpdate: () => fn(clock.t) }, 0);
      fn(0);
    },
    openState(target, vars) { gsap.set(target, vars); tl.set(target, vars, 0); },
    bloom(sel, t, peak = 0.3) {
      // Additive and accent-tinted (mark.css .fm-bloom: radial gradient, mix-blend-mode screen). A full-frame white
      // overlay at 0.5 turned the DemoIdent draft's dark frame flat grey on the hit; keep the peak at or under 0.35.
      const p = Math.min(peak, 0.35);
      K.openState(sel, { opacity: 0 });
      tl.set(sel, { opacity: p }, t);
      tl.to(sel, { opacity: 0, duration: 0.25, ease: "power2.out" }, t + 2 / FPS);
    },
    flatMark(sel, cue) {
      // cue: { hit, reveal: [t0, t1] (optional), echoes: [edit times] (optional), bloom: "#bloom" (optional),
      //        clearOpacity: 0.35, revealScale: 0.9, punch: 1.06 }
      const m = $(sel), q = (c) => m.querySelector(c);
      const grey = q(".fm-grey"), col = q(".fm-col"), ringW = q(".fm-ringW"), ringA = q(".fm-ringA"), burst = q(".fm-burst");
      const clear = cue.clearOpacity ?? 0.35, s0 = cue.revealScale ?? 0.9;
      K.openState(m, { opacity: clear, scale: cue.reveal ? s0 : 1 });
      K.openState(grey, { opacity: 1 }); K.openState(col, { opacity: 0 });
      K.openState(ringW, { opacity: 1 }); K.openState([ringA, burst], { opacity: 0, scale: 1 });
      if (cue.reveal) {
        const [a, b] = cue.reveal;
        tl.to(m, { opacity: 1, duration: Math.min(0.7, b - a), ease: "power1.out" }, a);
        tl.to(m, { scale: 1, duration: b - a, ease: "power1.inOut" }, a);
      } else if (clear < 1) {
        tl.to(m, { opacity: 1, duration: 0.1, ease: "none" }, cue.hit);
      }
      // The hit: cross-fade to colour in 0.1 s, the white ring hands over to the accent ring, a ring burst to 1.6x
      // over 0.6 s, a 6 % scale punch decaying in 0.35 s, and the bloom.
      tl.to(col, { opacity: 1, duration: 0.1, ease: "none" }, cue.hit);
      tl.to([grey, ringW], { opacity: 0, duration: 0.1, ease: "none" }, cue.hit);
      tl.to(ringA, { opacity: 1, duration: 0.1, ease: "none" }, cue.hit);
      tl.fromTo(burst, { scale: 1, opacity: 0.9 }, { scale: 1.6, opacity: 0, duration: 0.6, ease: "power2.out", ...IR }, cue.hit);
      tl.fromTo(m, { scale: cue.punch ?? 1.06 }, { scale: 1, duration: 0.35, ease: "power2.out", ...IR }, cue.hit);
      if (cue.bloom) K.bloom(cue.bloom, cue.hit);
      // Echo repeats (echo_tail --json hits): the accent ring breathes 3 % halving about every repeat (0.62^k).
      (cue.echoes || []).forEach((t, k) =>
        tl.fromTo(ringA, { scale: 1 + 0.03 * Math.pow(0.62, k) }, { scale: 1, duration: 0.3, ease: "power2.out", ...IR }, t));
    },
  };
  return K;
};
