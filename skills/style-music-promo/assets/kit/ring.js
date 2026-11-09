// Spectrum ring on a 2D canvas, read from the track map's bands by frame (seek-safe, no WebGL). The standalone form of
// stage.js's ring: 72 bars mirrored over the 32 log bands, height 0.12 + 2.6 (band/99)^2.2 (0.6 + 0.8 mix) in units
// of radius / 4.6 (the stage's proportions), times opts.gain.
// makeRing(canvas, aud, opts) -> draw(T, on = 1). aud: {fps, bands, features: {mix}} from the map JSON.
// opts: { w, h (CSS px; the canvas is 2x), cx, cy, radius, bars: 72, color: "#4dffff", barWidth: 4, gain: 1,
//         glow: 16, mirror: true, spin: (T) => radians }
// Use it for the densest moment (the flurry, an ident's hit bar), not throughout; `on` fades it (0-1).
window.makeRing = function (canvas, aud, o) {
  if (!aud || !aud.bands || !aud.bands.length || !aud.fps) throw new Error("makeRing: AUD.fps and AUD.bands missing (copy them from the map JSON)");
  const ctx = canvas.getContext("2d"), N = o.bars ?? 72, R = o.radius, W = o.w, H = o.h, MIR = o.mirror ?? true;
  const frame = (T) => Math.max(0, Math.min(aud.bands.length - 1, Math.round(T * aud.fps)));
  const MIX = aud.features && aud.features.mix;
  return function draw(T, on = 1) {
    ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!(on > 0.001)) return;
    const f = frame(T), b = aud.bands[f] || [], m = MIX ? MIX[Math.min(MIX.length - 1, f)] || 0 : 0.5;
    const bw = o.barWidth ?? 4, unit = (R / 4.6) * (o.gain ?? 1), half = MIR ? N / 2 : N;
    ctx.translate(o.cx ?? W / 2, o.cy ?? H / 2);
    ctx.rotate(o.spin ? o.spin(T) : 0);
    ctx.globalAlpha = 0.85 * on;
    ctx.fillStyle = o.color ?? "#4dffff";
    ctx.shadowColor = o.color ?? "#4dffff";
    ctx.shadowBlur = o.glow ?? 16;
    for (let i = 0; i < N; i++) {
      const k = MIR && i >= half ? N - 1 - i : i;
      const v = (b[Math.floor((k / half) * 32)] || 0) / 99;
      const len = (0.12 + 2.6 * Math.pow(v, 2.2) * (0.6 + 0.8 * m)) * unit * on;
      const a = (i / N) * Math.PI * 2;
      ctx.save(); ctx.rotate(a); ctx.fillRect(-bw / 2, -(R + len), bw, len); ctx.restore();
    }
  };
};
