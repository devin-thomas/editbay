// SoundCloud-style waveform that scrolls with the song, drawn from the track map's peaks (seek-safe).
// makeWave(canvas, aud, opts) -> draw(T). The canvas is 2x its CSS size (crisp at 4K); draw units are CSS pixels.
// aud.wave is the map JSON's wave as written: {start, dur, peaks}. wave.start is the edit time where peaks[0] plays
// (window start + offset), so a window cut from mid-song needs no slicing. opts.preroll overrides it (same meaning).
// opts: { w, h, mid, pxPerSec, preroll, accentTop, accentBottom, idle, fadeIn:[a,b], fadeOut:[a,b], height, edge }
window.makeWave = function (canvas, aud, o) {
  if (!aud || !aud.wave || !aud.wave.peaks || !aud.wave.peaks.length) throw new Error("makeWave: AUD.wave.peaks missing (copy the map JSON's wave)");
  const pre = o.preroll ?? aud.wave.start;
  if (typeof pre !== "number") throw new Error("makeWave: no start time (AUD.wave.start or opts.preroll)");
  const ctx = canvas.getContext("2d"), PK = aud.wave.peaks, DT = aud.wave.dur / PK.length;
  const W = o.w, H = o.h, MID = o.mid ?? H / 2, CX = W / 2, PITCH = 6, PX = o.pxPerSec ?? 240;
  const grad = ctx.createLinearGradient(0, MID - (o.height ?? 200), 0, MID);
  grad.addColorStop(0, o.accentTop ?? "#9ffcff"); grad.addColorStop(1, o.accentBottom ?? "#27c7d6");
  const ramp = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
  return function draw(T) {
    ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const vis = ramp(T, ...(o.fadeIn ?? [0.15, 0.65])) * (1 - ramp(T, ...(o.fadeOut ?? [1e9, 1e9 + 1])));
    if (vis <= 0) return;
    const s = T - pre;                                                              // seconds since peaks[0]
    for (let i = 0; i < W / PITCH; i++) {
      const x = i * PITCH, bs = Math.max(0, s) + (x + PITCH / 2 - CX) / PX;       // song time under this bar
      let amp = 0;
      if (bs >= 0) for (let k = Math.floor(bs / DT); k <= Math.floor((bs + PITCH / PX) / DT) && k < PK.length; k++)
        amp = Math.max(amp, Math.abs(PK[k][0]), Math.abs(PK[k][1]));
      const h = 3 + amp * (o.height ?? 200), played = x + PITCH / 2 < CX && s > 0;
      const edge = Math.min(1, Math.min(x, W - x) / (o.edge ?? 260));
      ctx.globalAlpha = vis * edge; ctx.fillStyle = played ? grad : (o.idle ?? "#39404a");
      ctx.fillRect(x, MID - h, PITCH - 2, h);
      ctx.globalAlpha = vis * edge * 0.28; ctx.fillRect(x, MID + 3, PITCH - 2, h * 0.42);
    }
    ctx.globalAlpha = vis; ctx.fillStyle = "#e9ffff"; ctx.fillRect(CX - 1, MID - (o.height ?? 200) * 1.18, 2, (o.height ?? 200) * 1.65);
  };
};
