"""Liquid-glass 3D logo plate: a glass app-icon slab that fills with the brand colour, built in Blender Cycles.

Runs inside Blender (bpy is Blender's own Python, so there is no PEP 723 header and `uv run` cannot run it):
  Blender -b --factory-startup --python-exit-code 1 -P tools/glass_logo.py -- CONFIG.json
          [--out plate.blend] [--root DIR] [--aspect 9:16] [--height 1920]
          [--render OUTDIR --frames 320-1012 [--samples 16] [--percent 100]]
--factory-startup keeps the user's add-ons and preferences out (the GPU choice is set for this session only).
--aspect overrides the config's aspect and takes that aspect's default height unless --height is also given, so
one config makes both the 16:9 and the 9:16 plates.
Writes the .blend (--out, else the config's "out", else <config stem>.blend in the working directory), prints the
plate ranges, and with --render renders PNG frames OUTDIR/f00320.png... --frames takes ranges and lists
("320-1012", "330,760,2100", "320-400,2100"); there is no default, because a full plate is hours of GPU time.
Renders are resumable: overwrite off and placeholders on, so a re-run or a second process on the same range skips
frames already written (or claimed). Stop a render by killing it, then delete the zero-byte placeholder it left.

Paths in the config resolve against --root (e.g. the run folder), else the config file's folder; globs are expanded
and sorted. Keys starting with "_" are comments. Unknown keys fail, so a typo cannot silently fall back to a default.
Exit 1 before building anything when the config is invalid: a missing logo, a logo without alpha, no orbit image,
an unknown shape or aspect, a timeline key that is not a number.

CONFIG (defaults in brackets; units: the icon's half-width is 1, angles in degrees):
  logo          RGBA PNG with real alpha, drawn on a plane just inside the front wall [required].
                Make one with tools/logo_matte.py.
  logo_scale    share of the inner face the logo spans, aspect kept [1.0]
  accent        brand colour, sRGB hex: liquid, its glow and absorption, backdrop glow, strip tint ["#4dffff"]
  shape         "squircle" (superellipse, `squircle_n` [5], app-icon corners) | "circle" | "rounded"
                (rounded rectangle, `corner` [0.45] of the half-width) ["squircle"]
  thickness     slab depth [0.34];  rim  edge roundover radius [0.17];  wall  glass wall thickness [0.045]
  aspect        "16:9" | "9:16" | "1:1" ["16:9"];  height  output px [short side 1080: 1080, or 1920 for 9:16]
  fps           scene frames per second [60]. Frame = round(edit seconds x fps): every time below is an EDIT time,
                so plate frame N lands at edit time N/fps and the plate drops onto the timeline without offsets.
  out           .blend path [see above]
  timeline      every section optional; times in edit seconds:
    reveal      {"t": scene start, "keys": [[t, yaw, pitch, rise]...] icon sway (rise in half-widths, [0]),
                 "camera": [[t, distance, z]...] camera distance from the icon [[[t, 7.0]]]}
    fill        {"t0": liquid starts rising, "t1": full, "keys": [[t, level 0-1]...] in between [eased 0 -> 1],
                 "waves": [[t, strength]...] [ramp 0.05 -> 0.12 -> 0 as it fills],
                 "slosh": [[t, tilt]...] surface tilt [+5/-6/+3 over the second half]}
                level 0 = surface below the cavity (waves included), 1 = above it.
    spin        {"t0", "t1", "turns" [1]}: yaw from the pose at t0 to turns x 360 at t1 (ends facing front)
    dive        {"t0", "t1", "target": [x, z] [[0.58, 0.52]]}: the camera flies (eased) from its distance into
                the liquid behind the logo, off-centre; the icon turns 2 degrees further. Everything holds after t1
                (the frame is all liquid: cut or dissolve on it).
    lockup      {"t0", "t1", "settle" [t0 + 1.4], "distance": [start, end] [[11.4, 12.5]], "camera_z" [-0.5]
                 (negative lifts the icon above centre, room for a line below), "yaw" [38], "pitch" [-6]}:
                the icon arrives turned by yaw, settles to front at `settle`, drifts gently to t1, camera eases out.
    sweeps      [t, ...] or [[t, duration, power]...]: a soft light bar crosses the glass [0.9 s, 2200 W]
    orbit       {"images": [paths/globs], "count" [28], "radius" [2.75], "size" [0.3] half-size of each cover,
                 "t_in" (starts growing), "t_full" (full size), "t_out" (gone; collapses over the last 0.14 s),
                 "turn" [330] degrees from t_in until the collapse, accelerating, "tilt" [74],
                 "upright" [true for 9:16]: the ring stands up and orbits top-to-bottom in a tall frame,
                 "backoff" [2.6]: in a tall frame, camera keys inside (t_in, t_out) move back this far, all but
                 the dive's end}
                covers are centre-cropped to square and seen through the glass as refraction.
    glow_pulses {"times": [...], "decay" [0.62], "peak" [2.2], "base" [0.9], "fall" [0.2] s}: backdrop flashes,
                e.g. an echo throw's repeats; pulse i peaks at base + (peak - base) x decay^i.
    glow_envelope  per-sample backdrop strength (1.0 = resting glow), music-driven: a list starting at reveal.t at
                one value per scene frame, or {"t0", "rate" samples/s [fps], "values": [...]}.
                Pulses key the same socket; keep the two apart in time.
    bubbles     {"count" [46], "seed" [7]}: bubbles rise through the liquid while it fills, vanish at the surface.

Lessons baked in (Demo Artist trailer, 2026-09-29, Blender 5.2 Cycles on an M5 Max):
- View transform Khronos PBR Neutral: AgX washed the aqua out to a pale mint.
- The studio HDRI lights diffuse only. In glossy and transmission rays its round light panels mirror in the flat
  glass faces as blown-out discs over the logo (frames 368-488 of the first render; rotating the HDRI only moved
  the discs), so the world is taken out of those rays and strip lights plus a top rim strip draw the glass edges.
  The key light is hidden from glossy/transmission for the same reason.
- Thin film (320 nm, IOR 1.33) on the glass gives the iridescent rim.
- A white light bar reflected in that film reads lavender, so the sweep's reflection copy is tinted (0.45, 0.9, 1.0)
  while a white twin lights the logo through the glass; sweeps step on and off (CONSTANT keys), since keys 0.01 s
  apart round onto one frame and left 3 s BEZIER ramps between sweeps in the first plates.
  Measured on the trailer's final 16:9 (f570): the tinted reflection reads pale cream on the front face (149, 152, 124)
  and near-neutral grey on the back face (147, 141, 154), against a saturated lavender before; try a milder tint on
  three sweep angles before a new plate if a pure white highlight matters.
- The liquid is the cavity mesh intersected (Boolean) with an icon-space box behind the logo plane and a world-space
  fill box whose top is a displaced wave grid: gravity stays world-down while the icon sways and spins.
  The Manifold solver gives the same liquid as Exact (vertex counts and volumes equal at frames 330-2100) in
  0.03-0.04 s instead of 0.13-0.21 s per evaluation (2026-09-29).
- 16 spp + OpenImageDenoise measured identical to 32 and 72 spp (mean difference 0.7/255) at about half the time
  of 32. About 40% of each 1080p frame was CPU-side work (a 1-spp frame took 4.2 s), so two renders in parallel
  raise throughput; the Booleans are only a small part of it (above).
- The first render of a new feature set compiles the Metal GPU kernels: 242 s for the first 20% test frame while
  another render held the GPU, then 0.5-1.4 s per frame. Time a second run, not the first.
- Motion blur shutter 0.45. Camera sensor fit AUTO keeps the icon's size against the short side in 9:16; the
  camera backs off while the orbit ring is up so the ring stays in a tall frame.
- Renders are resumable with overwrite off + placeholders (plates were queued and restarted many times).
"""
import argparse, glob, json, math, os, random, sys, time

try:
    import bpy, bmesh
    from bpy_extras import anim_utils
except ImportError:
    sys.exit("glass_logo.py runs inside Blender: Blender -b --factory-startup --python-exit-code 1 "
             "-P tools/glass_logo.py -- CONFIG.json")

ASPECTS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1)}
TOP_KEYS = {"logo", "logo_scale", "accent", "shape", "squircle_n", "corner", "thickness", "rim", "wall", "aspect",
            "height", "fps", "out", "timeline"}
SECTIONS = {"reveal": {"t", "keys", "camera"}, "fill": {"t0", "t1", "keys", "waves", "slosh"},
            "spin": {"t0", "t1", "turns"}, "dive": {"t0", "t1", "target"},
            "lockup": {"t0", "t1", "settle", "distance", "camera_z", "yaw", "pitch"}, "sweeps": None,
            "orbit": {"images", "count", "radius", "size", "t_in", "t_full", "t_out", "turn", "tilt", "upright", "backoff"},
            "glow_pulses": {"times", "decay", "peak", "base", "fall"}, "glow_envelope": {"t0", "rate", "values"},
            "bubbles": {"count", "seed"}}
EMPTY, FULL = -1.25, 1.35  # liquid surface heights for level 0 and 1: past the cavity with the waves' amplitude


def fail(msg):
    sys.exit(f"glass_logo: {msg}")


# ---------------------------------------------------------------- config
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="glass_logo.py", description="Liquid-glass logo plate (see the module docstring).")
    ap.add_argument("config")
    ap.add_argument("--out", help=".blend to write")
    ap.add_argument("--root", help="folder that relative config paths resolve against [the config's folder]")
    ap.add_argument("--aspect", choices=sorted(ASPECTS))
    ap.add_argument("--height", type=int)
    ap.add_argument("--render", metavar="OUTDIR")
    ap.add_argument("--frames", help="scene frames: 320-1012, 330,760,2100 or a mix")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--percent", type=int, default=100, help="resolution percentage (test renders: 20-25)")
    a = ap.parse_args(argv)
    if a.render and not a.frames:
        fail("--render needs --frames (a full plate is hours; name the range)")
    return a


def num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        fail(f"{what} must be a number, got {v!r}")
    return float(v)


def load_config(a):
    try:
        with open(a.config) as fh:
            cfg = json.load(fh)
    except FileNotFoundError:
        fail(f"config not found: {a.config}")
    except json.JSONDecodeError as e:
        fail(f"{a.config}: invalid JSON ({e})")
    root = os.path.abspath(os.path.expanduser(a.root)) if a.root else os.path.dirname(os.path.abspath(a.config))

    def path(p):
        p = os.path.expanduser(p)
        return p if os.path.isabs(p) else os.path.join(root, p)

    extra = {k for k in cfg if not k.startswith("_")} - TOP_KEYS
    if extra:
        fail(f"unknown config keys: {', '.join(sorted(extra))}")
    tl = cfg.get("timeline", {})
    extra = {k for k in tl if not k.startswith("_")} - set(SECTIONS)
    if extra:
        fail(f"unknown timeline sections: {', '.join(sorted(extra))}")
    for sec, allowed in SECTIONS.items():
        if allowed and isinstance(tl.get(sec), dict):
            extra = {k for k in tl[sec] if not k.startswith("_")} - allowed
            if extra:
                fail(f"unknown keys in timeline.{sec}: {', '.join(sorted(extra))} (allowed: {', '.join(sorted(allowed))})")
    if not cfg.get("logo"):
        fail("config needs \"logo\": an RGBA PNG with alpha (tools/logo_matte.py makes one)")
    cfg["logo"] = path(cfg["logo"])
    if not os.path.isfile(cfg["logo"]):
        fail(f"logo not found: {cfg['logo']}")
    acc = cfg.setdefault("accent", "#4dffff").lstrip("#")
    if len(acc) != 6 or any(c not in "0123456789abcdefABCDEF" for c in acc):
        fail(f"accent {cfg['accent']!r}: expected #rrggbb")
    if cfg.setdefault("shape", "squircle") not in ("squircle", "circle", "rounded"):
        fail(f"shape {cfg['shape']!r}: squircle | circle | rounded")
    if a.aspect:
        cfg["aspect"] = a.aspect
    if cfg.setdefault("aspect", "16:9") not in ASPECTS:
        fail(f"aspect {cfg['aspect']!r}: {' | '.join(ASPECTS)}")
    if a.height:
        cfg["height"] = a.height
    elif a.aspect:
        cfg.pop("height", None)  # an aspect override takes that aspect's default size
    for k, d in (("logo_scale", 1.0), ("squircle_n", 5.0), ("corner", 0.45), ("thickness", 0.34), ("rim", 0.17),
                 ("wall", 0.045), ("fps", 60)):
        cfg[k] = num(cfg.get(k, d), k)
    cfg["height"] = int(num(cfg.get("height", 1920 if cfg["aspect"] == "9:16" else 1080), "height"))
    if not (0 < cfg["wall"] < cfg["rim"] < 1 and cfg["thickness"] > 2 * cfg["wall"]):
        fail("need 0 < wall < rim < 1 and thickness > 2 x wall")
    orb = tl.get("orbit")
    if orb:
        files = []
        for pat in orb.get("images", []):
            hits = sorted(glob.glob(path(pat)))
            if not hits:
                fail(f"orbit image not found: {path(pat)}")
            files += hits
        if not files:
            fail("orbit needs \"images\": [paths or globs]")
        orb["images"] = files[:int(orb.get("count", 28))]
        for k in ("t_in", "t_full", "t_out"):
            num(orb.get(k), f"orbit.{k}")
    for sec, keys in (("fill", ("t0", "t1")), ("spin", ("t0", "t1")), ("dive", ("t0", "t1")), ("lockup", ("t0", "t1")),
                      ("reveal", ("t",))):
        for k in keys:
            if sec in tl:
                num(tl[sec].get(k), f"{sec}.{k}")
    cfg["timeline"] = tl
    cfg["out"] = os.path.abspath(a.out) if a.out else path(cfg["out"]) if cfg.get("out") else \
        os.path.abspath(os.path.splitext(os.path.basename(a.config))[0] + ".blend")
    return cfg


def srgb_to_linear(hexs):
    c = [int(hexs.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


# ---------------------------------------------------------------- geometry
def outline_raw(shape, hw, hh, n, corner, samples=8192):
    if shape in ("squircle", "circle"):
        e = 2.0 if shape == "circle" else n
        out = []
        for i in range(samples):
            t = 2 * math.pi * i / samples
            c, s = math.cos(t), math.sin(t)
            out.append((hw * math.copysign(abs(c) ** (2 / e), c), hh * math.copysign(abs(s) ** (2 / e), s)))
        return out
    r = corner * min(hw, hh)
    out, per = [], samples // 4
    for q, (cx, cz) in enumerate(((hw - r, hh - r), (-(hw - r), hh - r), (-(hw - r), -(hh - r)), (hw - r, -(hh - r)))):
        for i in range(per):  # each quarter arc; the straight edges come from the resampling between arcs
            t = math.pi / 2 * (q + i / per)
            out.append((cx + r * math.cos(t), cz + r * math.sin(t)))
    return out


def outline(cfg, hw, hh, N=384):
    """N points evenly spaced by arc length (so the rim's quads stay even around tight corners)."""
    raw = outline_raw(cfg["shape"], hw, hh, cfg["squircle_n"], cfg["corner"])
    S = len(raw)
    seg = [math.dist(raw[i], raw[(i + 1) % S]) for i in range(S)]
    step = sum(seg) / N
    out, acc, j = [], 0.0, 0
    for k in range(N):
        target = k * step
        while acc + seg[j] < target:
            acc += seg[j]; j += 1
        f = (target - acc) / seg[j]
        a, b = raw[j], raw[(j + 1) % S]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def normals(pts):
    out = []
    for i in range(len(pts)):
        a, b = pts[i - 1], pts[(i + 1) % len(pts)]
        dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz)
        out.append((dz / L, -dx / L))
    return out


def link(ob):
    bpy.context.collection.objects.link(ob)
    return ob


def slab(cfg, name, hw, hh, T, r, M=28, flip=False):
    """Closed slab in the XZ plane, depth T along Y, edges rounded by an elliptical sweep (r in-plane, T/2 deep)."""
    outer = outline(cfg, hw, hh); nr = normals(outer)
    inner = [(x - r * nx, z - r * nz) for (x, z), (nx, nz) in zip(outer, nr)]
    bm = bmesh.new(); rings = []
    for j in range(M + 1):
        phi = -math.pi / 2 + math.pi * j / M
        rings.append([bm.verts.new((px + r * math.cos(phi) * nx, (T / 2) * math.sin(phi), pz + r * math.cos(phi) * nz))
                      for (px, pz), (nx, nz) in zip(inner, nr)])
    N = len(outer)
    for j in range(M):
        for i in range(N):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % N], rings[j + 1][(i + 1) % N], rings[j + 1][i]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[M])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if flip:
        for f in bm.faces:
            f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return link(bpy.data.objects.new(name, me))


def flat_profile(cfg, name, hw, hh, y, N=384, shape=None):
    pts = outline(dict(cfg, shape=shape or cfg["shape"]), hw, hh, N)
    bm = bmesh.new(); vs = [bm.verts.new((x, y, z)) for x, z in pts]
    face = bm.faces.new(vs)
    uvl = bm.loops.layers.uv.new()
    for loop in face.loops:
        x, _, z = loop.vert.co
        loop[uvl].uv = ((x + hw) / (2 * hw), (z + hh) / (2 * hh))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))


# ---------------------------------------------------------------- materials
def new_material(name):
    m = bpy.data.materials.new(name)
    if not m.node_tree:  # Blender 5 materials always have nodes; use_nodes goes away in 6.0
        m.use_nodes = True
    return m


def principled(name, **inputs):
    m = new_material(name)
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in inputs.items():
        b.inputs[k].default_value = v
    return m, b


def image_material(name, path, emission, roughness, fit, scale=1.0, specular=None):
    """Image on a UV-mapped plane. fit="cover" centre-crops to the square face; "contain" keeps the whole image
    (the rest of the face is transparent, the image node clips outside 0-1)."""
    m = new_material(name)
    nt = m.node_tree; pb = nt.nodes["Principled BSDF"]
    im = nt.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(path, check_existing=True)
    im.extension = 'CLIP'
    w, h = im.image.size
    r = (w / h) if h else 1.0
    su, sv = (1 / r, 1.0) if (r > 1) == (fit == "cover") else (1.0, r)
    su, sv = su / scale, sv / scale
    uv = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (su, sv, 1); mp.inputs["Location"].default_value = ((1 - su) / 2, (1 - sv) / 2, 0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], im.inputs["Vector"])
    nt.links.new(im.outputs["Color"], pb.inputs["Base Color"]); nt.links.new(im.outputs["Color"], pb.inputs["Emission Color"])
    pb.inputs["Emission Strength"].default_value = emission; pb.inputs["Roughness"].default_value = roughness
    if specular is not None:
        pb.inputs["Specular IOR Level"].default_value = specular
    return m, nt, pb, im


# ---------------------------------------------------------------- animation
class Keys:
    def __init__(self, fps):
        self.fps = fps

    def F(self, t):
        return round(t * self.fps)

    def __call__(self, owner, prop, t, value, index=-1, interp='BEZIER', ease=None):
        """Key a value at edit time t. The interpolation is always set: a new key copies the previous key's,
        so one CONSTANT hold would otherwise leak into every later key on that curve."""
        if index < 0:
            setattr(owner, prop, value)
        else:
            getattr(owner, prop)[index] = value
        owner.keyframe_insert(data_path=prop, index=index, frame=self.F(t))
        if interp:
            for kp in self.points(owner, prop, index):
                if abs(kp.co.x - self.F(t)) < 0.5:
                    kp.interpolation = interp; kp.easing = ease or 'AUTO'

    @staticmethod
    def curves(owner, prop, index=-1):
        ad = owner.id_data.animation_data
        if not ad or not ad.action:
            return []
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)  # Blender 5: slotted actions
        full = owner.path_from_id(prop)
        return [c for c in cb.fcurves if c.data_path == full and (index < 0 or c.array_index == index)]

    def points(self, owner, prop, index=-1):
        return [kp for c in self.curves(owner, prop, index) for kp in c.keyframe_points]

    def hold_last(self, owner, prop, before):
        """Make the last key before `before` constant, so the next section's first key is a clean cut."""
        for c in self.curves(owner, prop):
            ks = [kp for kp in c.keyframe_points if kp.co.x < self.F(before) - 0.5]
            if ks:
                ks[-1].interpolation = 'CONSTANT'


def pairs(v, what, width):
    out = []
    for row in v:
        if not isinstance(row, (list, tuple)) or not (2 <= len(row) <= width):
            fail(f"{what}: rows are [t, ...] with 2-{width} numbers, got {row!r}")
        out.append([num(x, what) for x in row])
    return out


# ---------------------------------------------------------------- build
def pick_device(sc):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = 'GPU'
            return kind
    sc.cycles.device = 'CPU'
    return 'CPU'


def check_logo_alpha(path):
    img = bpy.data.images.load(path, check_existing=True)
    if img.channels < 4 or img.size[0] == 0:
        fail(f"logo has no alpha channel: {path} (tools/logo_matte.py makes one)")
    import numpy as np
    px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32); img.pixels.foreach_get(px)
    if px[3::4].min() > 0.99:
        fail(f"logo is fully opaque: {path}; the glass needs the art cut out (tools/logo_matte.py)")
    return img


def build(cfg):
    t_start = time.time()
    fps = int(cfg["fps"]); K = Keys(fps); F = K.F
    tl = cfg["timeline"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    logo_img = check_logo_alpha(cfg["logo"])
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    device = pick_device(sc)
    sc.render.fps = fps
    wr, hr = ASPECTS[cfg["aspect"]]
    sc.render.resolution_y = cfg["height"]; sc.render.resolution_x = round(cfg["height"] * wr / hr)
    sc.cycles.samples = 16                    # + OIDN: identical to 32/72 spp (0.7/255) at about half the time
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
    sc.render.use_persistent_data = True
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 14; sc.cycles.transmission_bounces = 14; sc.cycles.glossy_bounces = 6
    sc.cycles.transparent_max_bounces = 16; sc.cycles.diffuse_bounces = 3
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.6; sc.cycles.sample_clamp_indirect = 8
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
    sc.view_settings.view_transform = 'Khronos PBR Neutral'  # AgX washed the accent out

    acc = srgb_to_linear(cfg["accent"])
    deep = [c ** 1.4 for c in acc]            # emission: a touch deeper than the base
    mix = lambda a_, b_, f: tuple(x + (y - x) * f for x, y in zip(a_, b_))

    # ---- geometry (icon half-width 1; X right, Y away from camera, Z up)
    HW = HH = 1.0; T, R, W = cfg["thickness"], cfg["rim"], cfg["wall"]
    rig = link(bpy.data.objects.new("IconRig", None))
    shell = slab(cfg, "GlassOuter", HW, HH, T, R)
    cavity = slab(cfg, "GlassInner", HW - W, HH - W, T - 2 * W, R - W, flip=True)
    AV_Y = -(T / 2 - W) + 0.012               # logo plane just inside the front wall
    logo = flat_profile(cfg, "Logo", HW - W - 0.004, HH - W - 0.004, AV_Y)
    liquid = slab(cfg, "Liquid", HW - W - 0.004, HH - W - 0.004, T - 2 * W - 0.008, R - W - 0.004)
    for o in (shell, cavity, logo, liquid):
        o.parent = rig

    # liquid = cavity AND behind-the-logo box (icon space) AND fill box (world space: gravity stays down)
    bpy.ops.mesh.primitive_cube_add(size=1)
    back = bpy.context.active_object; back.name = "LiquidBackCut"
    back.scale = (3, 1, 3); back.location = (0, AV_Y + 0.004 + 0.5, 0); back.parent = rig
    back.hide_render = True; back.display_type = 'WIRE'
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=96, y_segments=96, size=1.6)
    ext = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
    for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z = -4.0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Fill"); bm.to_mesh(me); bm.free()
    fill = link(bpy.data.objects.new("LiquidFill", me))
    vg = fill.vertex_groups.new(name="top"); vg.add([v.index for v in me.vertices if abs(v.co.z) < 1e-6], 1.0, 'REPLACE')
    fill.hide_render = True; fill.display_type = 'WIRE'
    cl = fill.constraints.new('COPY_LOCATION'); cl.target = rig; cl.use_offset = True
    wave_tex = bpy.data.textures.new("Waves", 'CLOUDS'); wave_tex.noise_scale = 0.55; wave_tex.noise_depth = 2
    wave_ctl = link(bpy.data.objects.new("WaveCtl", None))
    disp = fill.modifiers.new("Waves", 'DISPLACE'); disp.texture = wave_tex; disp.vertex_group = "top"
    disp.texture_coords = 'OBJECT'; disp.texture_coords_object = wave_ctl; disp.direction = 'Z'
    disp.mid_level = 0.5; disp.strength = 0.0
    fill.location.z = EMPTY
    for name, ob in (("Back", back), ("Level", fill)):
        b = liquid.modifiers.new(name, 'BOOLEAN'); b.operation = 'INTERSECT'; b.object = ob
        try:
            b.solver = 'MANIFOLD'  # same mesh as EXACT (vertex count and volume), about 5x faster to evaluate
        except TypeError:          # Blender before 4.5
            b.solver = 'EXACT'

    # ---- materials
    glass, _ = principled("Glass", **{"Base Color": (1, 1, 1, 1), "Roughness": 0.0, "IOR": 1.47,
                                      "Transmission Weight": 1.0, "Specular IOR Level": 0.5,
                                      "Thin Film Thickness": 320.0, "Thin Film IOR": 1.33})  # iridescent rim
    shell.data.materials.append(glass); cavity.data.materials.append(glass)
    liq, _ = principled("Liquid", **{"Base Color": (*acc, 1), "Roughness": 0.02, "IOR": 1.33, "Transmission Weight": 1.0,
                                     "Emission Color": (*[c * 0.92 for c in deep], 1), "Emission Strength": 0.55})
    va = liq.node_tree.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = (*[c ** 1.1 for c in acc], 1); va.inputs["Density"].default_value = 2.5
    liq.node_tree.links.new(va.outputs["Volume"], liq.node_tree.nodes["Material Output"].inputs["Volume"])
    liquid.data.materials.append(liq)
    lm, lnt, lpb, lim = image_material("Logo", cfg["logo"], 0.22, 0.4, "contain", cfg["logo_scale"])
    lim.image = logo_img; lim.image.alpha_mode = 'STRAIGHT'
    lnt.links.new(lim.outputs["Alpha"], lpb.inputs["Alpha"])
    logo.data.materials.append(lm)

    # backdrop: near-black with a soft accent glow the glass refracts
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 0), rotation=(math.radians(90), 0, 0))
    bd = bpy.context.active_object; bd.name = "Backdrop"
    bdm = new_material("Backdrop")
    n = bdm.node_tree.nodes; ln = bdm.node_tree.links; n.clear()
    out = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission")
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
    ramp = n.new("ShaderNodeValToRGB")
    mp.inputs["Scale"].default_value = (0.16, 0.16, 0.16)
    ln.new(tc.outputs["Object"], mp.inputs["Vector"]); ln.new(mp.outputs["Vector"], gr.inputs["Vector"])
    ln.new(gr.outputs["Fac"], ramp.inputs["Fac"])
    dark = (0.0008, 0.0009, 0.0012)
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].position = 0.86
    ramp.color_ramp.elements[1].color = (*[max(d, c * 0.013) for d, c in zip(dark, acc)], 1)
    e = ramp.color_ramp.elements.new(0.975); e.color = (*[max(d, c * 0.075) for d, c in zip(dark, acc)], 1)
    ln.new(ramp.outputs["Color"], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
    ln.new(em.outputs["Emission"], out.inputs["Surface"])
    bd.data.materials.append(bdm); bd.visible_shadow = False

    # world: studio HDRI for diffuse light only; black to the camera; out of glossy and transmission rays
    w = bpy.data.worlds.new("World"); sc.world = w
    if not w.node_tree:
        w.use_nodes = True
    wn = w.node_tree.nodes; wl = w.node_tree.links; wn.clear()
    wo = wn.new("ShaderNodeOutputWorld")
    bgc = wn.new("ShaderNodeBackground"); bgc.inputs["Strength"].default_value = 0.45
    hdri = os.path.join(bpy.utils.system_resource('DATAFILES', path="studiolights/world"), "studio.exr")
    if os.path.isfile(hdri):
        env = wn.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri)
        wl.new(env.outputs["Color"], bgc.inputs["Color"])
    else:
        bgc.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
        print(f"glass_logo: studio HDRI not found at {hdri}; diffuse fill is flat grey")
    blk = wn.new("ShaderNodeBackground"); blk.inputs["Color"].default_value = (*dark, 1)
    lp = wn.new("ShaderNodeLightPath"); mixs = wn.new("ShaderNodeMixShader")
    wl.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"]); wl.new(bgc.outputs["Background"], mixs.inputs[1])
    wl.new(blk.outputs["Background"], mixs.inputs[2]); wl.new(mixs.outputs["Shader"], wo.inputs["Surface"])
    # its round light panels mirror in the flat glass faces as blown-out discs; rotating it only moves them
    w.cycles_visibility.glossy = False; w.cycles_visibility.transmission = False

    def area(name, size, loc, power, color=(1, 1, 1), size_y=None):
        ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'; ld.size = size; ld.size_y = size_y or size
        ld.energy = power; ld.color = color
        ob = link(bpy.data.objects.new(name, ld)); ob.location = loc
        tgt = link(bpy.data.objects.new(name + "_t", None))
        tr = ob.constraints.new('TRACK_TO'); tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
        return ob
    key = area("Key", 3.2, (-3.2, -3.4, 3.0), 700, size_y=1.4)
    key.visible_glossy = False; key.visible_transmission = False  # lights the logo; in the glass it is a blob
    area("StripL", 0.22, (-3.6, 0.8, 0.2), 900, size_y=6.0)          # the strips draw the glass edges
    area("StripR", 0.22, (3.6, 0.6, 0.4), 700, color=mix((1, 1, 1), acc, 0.27), size_y=6.0)
    area("Top", 4.0, (0, -0.5, 4.6), 380, size_y=1.0)
    area("RimTop", 0.18, (0.8, 2.2, 3.4), 520, color=mix((1, 1, 1), acc, 0.1), size_y=6.0)
    # The sweep is two lights on one path: white lights the logo through the glass (transmission), and a copy seen
    # only in reflections carries an aqua-white tint. A white bar reflected in the thin film reads lavender (the
    # Demo Artist intro, frames 551-919: a pale violet streak across the face); (0.45, 0.9, 1.0) cancels the film's
    # tint to a cool white whatever the brand colour.
    sweep = area("Sweep", 0.35, (-5, -4.0, 0.0), 0, size_y=7.0)
    sweep.visible_glossy = False
    sweep_g = area("SweepGloss", 0.35, (-5, -4.0, 0.0), 0, color=(0.45, 0.9, 1.0), size_y=7.0)
    sweep_g.visible_diffuse = False; sweep_g.visible_transmission = False; sweep_g.visible_camera = False

    cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 55; cam_d.sensor_fit = 'AUTO'  # icon keeps size vs short side
    cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6; cam_d.dof.focus_object = rig
    cam = link(bpy.data.objects.new("Cam", cam_d)); sc.camera = cam
    cam.rotation_euler = (math.radians(90), 0, 0); cam.location = (0, -7.0, 0.0)

    # ---- timeline
    rev = tl.get("reveal", {})
    t0 = num(rev.get("t", 0.0), "reveal.t")
    ends = [t0]
    rkeys = pairs(rev.get("keys", [[t0, 0, 0, 0]]), "reveal.keys", 4)
    for row in rkeys:
        t, yaw, pitch, rise = (row + [0, 0, 0])[:4]
        K(rig, "rotation_euler", t, math.radians(pitch), 0); K(rig, "rotation_euler", t, math.radians(yaw), 2)
        K(rig, "location", t, rise, 2)
    ckeys = pairs(rev.get("camera", [[t0, 7.0]]), "reveal.camera", 3)
    K(cam, "location", ckeys[0][0], 0.0, 0)
    for row in ckeys:
        t, d, z = (row + [0])[:3]
        K(cam, "location", t, -d, 1); K(cam, "location", t, z, 2)
    ends += [r[0] for r in rkeys + ckeys]
    base_yaw = 0.0

    fl = tl.get("fill")
    if fl:
        a_, b_ = num(fl["t0"], "fill.t0"), num(fl["t1"], "fill.t1"); d = b_ - a_
        level = lambda f: EMPTY + f * (FULL - EMPTY)
        K(fill, "location", t0, EMPTY, 2)
        for t, f in [[a_, 0.0]] + pairs(fl.get("keys", [[a_ + d / 2, 0.45]]), "fill.keys", 2) + [[b_, 1.0]]:
            K(fill, "location", t, level(f), 2)
        waves = fl.get("waves") or [[t0, 0], [a_, 0.05], [a_ + 0.53 * d, 0.07], [a_ + 0.8 * d, 0.12], [b_ - 0.2, 0.06],
                                    [b_ + 0.46, 0]]
        for t, s in pairs(waves, "fill.waves", 2):
            K(disp, "strength", t, s)
        slosh = fl.get("slosh") or [[a_ + 0.53 * d, 0], [a_ + 0.72 * d, 5], [a_ + 0.89 * d, -6], [b_ + 0.22, 3], [b_ + 0.8, 0]]
        for t, ang in pairs(slosh, "fill.slosh", 2):
            K(fill, "rotation_euler", t, math.radians(ang), 1)
        ends += [b_ + 0.8]

    sp = tl.get("spin")
    if sp:
        a_, b_ = num(sp["t0"], "spin.t0"), num(sp["t1"], "spin.t1")
        sc.frame_set(F(a_))
        K(rig, "rotation_euler", a_, rig.rotation_euler[2], 2); K(rig, "rotation_euler", a_, rig.rotation_euler[0], 0)
        base_yaw = 2 * math.pi * num(sp.get("turns", 1), "spin.turns")
        K(rig, "rotation_euler", b_, base_yaw, 2); K(rig, "rotation_euler", b_, 0.0, 0); K(rig, "location", b_, 0.0, 2)
        ends += [b_]

    dv = tl.get("dive")
    if dv:
        a_, b_ = num(dv["t0"], "dive.t0"), num(dv["t1"], "dive.t1")
        tx, tz = [num(v, "dive.target") for v in dv.get("target", [0.58, 0.52])]
        sc.frame_set(F(a_))
        for i in range(3):  # hold the camera where it is, then fly (eased) into the liquid
            K(cam, "location", a_, cam.location[i], i)
        for i, v in enumerate((tx, -0.02, tz)):
            K(cam, "location", b_, v, i, interp='CONSTANT')
        K(rig, "rotation_euler", b_, base_yaw + math.radians(2), 2, interp='CONSTANT')
        K(rig, "rotation_euler", b_, math.radians(-1.5), 0, interp='CONSTANT')
        ends += [b_]

    lk = tl.get("lockup")
    if lk:
        a_, b_ = num(lk["t0"], "lockup.t0"), num(lk["t1"], "lockup.t1")
        st = num(lk.get("settle", a_ + 1.4), "lockup.settle")
        d0, d1 = [num(v, "lockup.distance") for v in lk.get("distance", [11.4, 12.5])]
        cz = num(lk.get("camera_z", -0.5), "lockup.camera_z")
        yaw, pitch = num(lk.get("yaw", 38), "lockup.yaw"), num(lk.get("pitch", -6), "lockup.pitch")
        for ob, prop in ((rig, "rotation_euler"), (rig, "location"), (cam, "location")):
            K.hold_last(ob, prop, a_)
        if fl:
            K(fill, "location", a_ - 0.5, FULL, 2); K(disp, "strength", a_ - 0.5, 0.0)
        drift = st + 0.53 * (b_ - st)
        for t, y_, p_, z_ in ((a_, yaw, pitch, -0.08), (st, 0, 0, 0.0), (drift, -2.5, 1.2, 0.02), (b_, 1.5, -0.8, 0.0)):
            K(rig, "rotation_euler", t, base_yaw + math.radians(y_), 2); K(rig, "rotation_euler", t, math.radians(p_), 0)
            K(rig, "location", t, z_, 2)
        for t, dd, zz in ((a_, d0, cz), (b_, d1, cz * 1.12)):
            K(cam, "location", t, 0.0, 0); K(cam, "location", t, -dd, 1); K(cam, "location", t, zz, 2)
        ends += [b_]

    for lt in (sweep, sweep_g):   # off from frame 0 (a curve holds its first key's value before it)
        K(lt.data, "energy", 0.0, 0, interp='CONSTANT')
    for s in tl.get("sweeps", []):
        t, dur, power = (list(s) + [0.9, 2200][len(s) - 1:]) if isinstance(s, list) else (s, 0.9, 2200)
        t, dur, power = num(t, "sweeps"), num(dur, "sweeps"), num(power, "sweeps")
        # Step the light on and off (CONSTANT): it is off to the side at both ends, so the step is invisible. Keys a
        # hair apart (t and t + 0.01) round onto one frame and leave BEZIER ramps between sweeps: in the Demo Artist
        # plates the light faded up over 3 s between two sweeps and sat at full power through the lockup.
        for lt in (sweep, sweep_g):
            K(lt.data, "energy", t, power, interp='CONSTANT'); K(lt.data, "energy", t + dur, 0, interp='CONSTANT')
            K(lt, "location", t, -5.0, 0, interp='LINEAR'); K(lt, "location", t + dur, 5.0, 0, interp='LINEAR')
        ends += [t + dur]

    covers = 0
    orb = tl.get("orbit")
    tall = sc.render.resolution_y > sc.render.resolution_x
    if orb:
        ti, tf, to = (num(orb[k], f"orbit.{k}") for k in ("t_in", "t_full", "t_out"))
        upright = orb.get("upright", tall)
        ring = link(bpy.data.objects.new("Orbit", None))
        ring.rotation_euler = (math.radians(num(orb.get("tilt", 74), "orbit.tilt")), math.radians(82 if upright else -8), 0)
        rad, size = num(orb.get("radius", 2.75), "orbit.radius"), num(orb.get("size", 0.3), "orbit.size")
        files = orb["images"]; covers = len(files)
        for i, path in enumerate(files):
            ob = flat_profile(cfg, f"Cover{i:02d}", size, size, 0.0, N=96, shape="squircle")
            ang = 2 * math.pi * i / covers
            ob.location = (rad * math.cos(ang), rad * math.sin(ang), 0.0)
            ob.rotation_euler = (math.radians(-90), 0, ang + math.pi / 2); ob.parent = ring
            m = image_material(f"Cover{i:02d}", path, 0.22, 0.6, "cover", specular=0.2)[0]
            ob.data.materials.append(m)
        for t, s in ((t0, 0.0), (ti, 0.0), (tf, 1.0), (to - 0.14, 1.0), (to, 0.0)):
            ring.scale = (s, s, s); ring.keyframe_insert("scale", frame=F(t))
        turn = num(orb.get("turn", 330), "orbit.turn")
        for f, share in ((0, 0), (1 / 3, 40 / 330), (2 / 3, 130 / 330), (1, 1)):  # accelerating, until it collapses
            K(ring, "rotation_euler", ti + f * (to - 0.14 - ti), math.radians(turn * share), 2)
        if tall:  # back the camera off while the ring is up, so it stays in a tall frame
            back_off = num(orb.get("backoff", 2.6), "orbit.backoff")
            stop = min(to, num(dv["t1"], "dive.t1")) if dv else to  # the dive still ends inside the liquid
            for c in K.curves(cam, "location", 1):
                inside = [kp for kp in c.keyframe_points if F(ti) < kp.co.x < F(stop)]
                if not inside:
                    sc.frame_set(F(tf)); K(cam, "location", tf, cam.location[1], 1)
                    inside = [kp for kp in c.keyframe_points if abs(kp.co.x - F(tf)) < 0.5]
                for kp in inside:
                    kp.co.y -= back_off; kp.handle_left.y -= back_off; kp.handle_right.y -= back_off
                c.update()
        ends += [to]

    # the wave texture drifts for the whole piece
    t_end = max(ends)
    K(wave_ctl, "location", t0, 0.0, 0, interp='LINEAR'); K(wave_ctl, "location", t_end, 0.47 * (t_end - t0), 0, interp='LINEAR')
    K(wave_ctl, "location", t0, 0.0, 1, interp='LINEAR'); K(wave_ctl, "location", t_end, 0.28 * (t_end - t0), 1, interp='LINEAR')

    nb = 0
    bub = tl.get("bubbles", {} if fl else None)
    if fl and bub is not None:
        lc = K.curves(fill, "location", 2)[0]
        a_, b_ = num(fl["t0"], "fill.t0"), num(fl["t1"], "fill.t1")
        bm_, _ = principled("Bubble", **{"Base Color": (1, 1, 1, 1), "Roughness": 0.0, "IOR": 0.75, "Transmission Weight": 1.0})
        rng = random.Random(int(bub.get("seed", 7)))
        y_lo, y_hi = AV_Y + 0.028, T / 2 - W - 0.035
        z_lo, z_hi = -(HH - W) + 0.035, (HH - W) - 0.025
        for i in range(int(bub.get("count", 46))):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.010, 0.030), segments=16, ring_count=8)
            b = bpy.context.active_object; b.name = f"Bubble{i:02d}"; b.data.materials.append(bm_); b.parent = rig
            for p_ in b.data.polygons:
                p_.use_smooth = True
            ts = rng.uniform(a_ + 0.22, b_ - 0.3); v = rng.uniform(0.7, 1.4)
            x0 = rng.uniform(-0.8, 0.8); y0 = rng.uniform(y_lo, y_hi)
            b.scale = (0, 0, 0); b.keyframe_insert("scale", frame=F(ts) - 1)
            t = ts
            while t < b_ + 0.6:
                z = z_lo + v * (t - ts)
                alive = z < lc.evaluate(t * fps) - 0.03 and z < z_hi
                b.location = (x0 + 0.03 * math.sin(7 * (t - ts) + i), y0, z); b.keyframe_insert("location", frame=F(t))
                s_ = 1.0 if alive else 0.0
                b.scale = (s_, s_, s_); b.keyframe_insert("scale", frame=F(t))
                if not alive:
                    break
                t += 1 / 20
            nb += 1

    strength = em.inputs["Strength"]
    env_ = tl.get("glow_envelope")
    if env_:
        spec = env_ if isinstance(env_, dict) else {"t0": t0, "rate": fps, "values": env_}
        et0, rate = num(spec.get("t0", t0), "glow_envelope.t0"), num(spec.get("rate", fps), "glow_envelope.rate")
        for i, v in enumerate(spec["values"]):
            strength.default_value = num(v, "glow_envelope.values")
            strength.keyframe_insert("default_value", frame=round((et0 + i / rate) * fps))
    gp = tl.get("glow_pulses")
    if gp:
        base, peak = num(gp.get("base", 0.9), "glow_pulses.base"), num(gp.get("peak", 2.2), "glow_pulses.peak")
        decay, fall = num(gp.get("decay", 0.62), "glow_pulses.decay"), num(gp.get("fall", 0.2), "glow_pulses.fall")
        times = [num(t, "glow_pulses.times") for t in gp.get("times", [])]
        for i, t in enumerate(times):
            for tt, v in ((t - 0.03, base), (t, base + (peak - base) * decay ** i), (t + fall, base)):
                strength.default_value = v; strength.keyframe_insert("default_value", frame=F(tt))
        if times:
            ends.append(times[-1] + fall)

    sc.frame_start, sc.frame_end = F(t0), F(max(ends))
    sc.frame_set(sc.frame_start)
    os.makedirs(os.path.dirname(cfg["out"]) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=cfg["out"])
    print(f"glass_logo: saved {cfg['out']}  {sc.render.resolution_x}x{sc.render.resolution_y} @ {fps} fps  "
          f"{cfg['shape']} {cfg['accent']}  covers {covers}  bubbles {nb}  device {device}  "
          f"built in {time.time() - t_start:.1f}s")
    plates = [("scene", t0, max(ends))]
    last = max([t0] + [tl[k]["t1"] for k in ("fill", "spin", "dive") if k in tl])
    if lk:
        plates += [("opening", t0, last), ("lockup", lk["t0"], lk["t1"])]
    for name, a_, b_ in plates:
        print(f"glass_logo: plate {name}: frames {F(a_)}-{F(b_)}  (edit {a_:.2f}-{b_:.2f} s)")
    return sc


# ---------------------------------------------------------------- render
def parse_frames(spec):
    out = []
    for part in spec.split(","):
        a_, _, b_ = part.strip().partition("-")
        try:
            a_ = int(a_); b_ = int(b_) if b_ else a_
        except ValueError:
            fail(f"--frames {spec!r}: use 320-1012, 330,760 or a mix")
        if b_ < a_:
            fail(f"--frames {part!r}: end before start")
        out.append((a_, b_))
    return out


def render(sc, outdir, ranges, samples, percent):
    sc.cycles.samples = samples; sc.render.resolution_percentage = percent
    sc.render.filepath = os.path.join(os.path.abspath(outdir), "f#####")
    s = sc.render.image_settings; s.file_format = 'PNG'; s.color_mode = 'RGB'; s.color_depth = '8'
    sc.render.use_overwrite = False; sc.render.use_placeholder = True  # resumable, and safe to run twice
    clock = {}
    bpy.app.handlers.render_pre.append(lambda s_, *_: clock.__setitem__("t", time.time()))
    bpy.app.handlers.render_post.append(
        lambda s_, *_: print(f"glass_logo: FRAME {s_.frame_current} {time.time() - clock.get('t', time.time()):.1f}s",
                             flush=True))
    t = time.time()
    for a_, b_ in ranges:
        sc.frame_start, sc.frame_end = a_, b_
        bpy.ops.render.render(animation=True)
    print(f"glass_logo: rendered {outdir} in {time.time() - t:.1f}s ({samples} spp, {percent}%)")


def main():
    a = parse_args()
    cfg = load_config(a)
    sc = build(cfg)
    if a.render:
        render(sc, a.render, parse_frames(a.frames), a.samples, a.percent)


if __name__ == "__main__":
    main()
