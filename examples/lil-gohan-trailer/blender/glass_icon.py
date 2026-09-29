"""Liquid-glass Lil Gohan app icon for the trailer. Builds the scene and saves glass_icon.blend.
Timeline: scene frame = trailer time x 60 (60 fps). The song's beat k is at T = 1.5 + 0.48k."""
import bpy, bmesh, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 60
def F(t): return round(t * FPS)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'; prefs.get_devices()
for d in prefs.devices: d.use = True
sc.cycles.device = 'GPU'
sc.render.fps = FPS
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.cycles.samples = 72
sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
sc.render.use_persistent_data = True
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPENIMAGEDENOISE'
sc.cycles.max_bounces = 14; sc.cycles.transmission_bounces = 14; sc.cycles.glossy_bounces = 6
sc.cycles.transparent_max_bounces = 16; sc.cycles.diffuse_bounces = 3
sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.cycles.blur_glossy = 0.6
sc.cycles.sample_clamp_indirect = 8
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
sc.view_settings.view_transform = 'Khronos PBR Neutral'

# ---------- geometry ----------
def squircle(hw, hh, n=5.0, samples=8192, N=384):
    raw = []
    for i in range(samples):
        t = 2 * math.pi * i / samples
        c, s = math.cos(t), math.sin(t)
        raw.append((hw * math.copysign(abs(c) ** (2 / n), c), hh * math.copysign(abs(s) ** (2 / n), s)))
    seg = [math.dist(raw[i], raw[(i + 1) % samples]) for i in range(samples)]
    total = sum(seg); step = total / N
    out, acc, j = [], 0.0, 0
    for k in range(N):
        target = k * step
        while acc + seg[j] < target: acc += seg[j]; j += 1
        f = (target - acc) / seg[j]
        a, b = raw[j], raw[(j + 1) % samples]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out

def normals(pts):
    N = len(pts); out = []
    for i in range(N):
        a, b = pts[i - 1], pts[(i + 1) % N]
        dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz)
        out.append((dz / L, -dx / L))
    return out

def slab(name, hw, hh, T, r, M=28, N=384, flip=False, uv=False):
    outer = squircle(hw, hh, N=N); nr = normals(outer)
    inner = [(x - r * nx, z - r * nz) for (x, z), (nx, nz) in zip(outer, nr)]
    bm = bmesh.new(); rings = []
    for j in range(M + 1):
        phi = -math.pi / 2 + math.pi * j / M
        rings.append([bm.verts.new((px + r * math.cos(phi) * nx, (T / 2) * math.sin(phi), pz + r * math.cos(phi) * nz))
                      for (px, pz), (nx, nz) in zip(inner, nr)])
    for j in range(M):
        for i in range(N):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % N], rings[j + 1][(i + 1) % N], rings[j + 1][i]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[M])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if flip:
        for f in bm.faces: f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    return ob

def flat_profile(name, hw, hh, y, N=384):
    pts = squircle(hw, hh, N=N)
    bm = bmesh.new(); vs = [bm.verts.new((x, y, z)) for x, z in pts]
    face = bm.faces.new(vs)
    uvl = bm.loops.layers.uv.new()
    for loop in face.loops:
        x, _, z = loop.vert.co
        loop[uvl].uv = ((x + hw) / (2 * hw), (z + hh) / (2 * hh))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    return ob

HW = HH = 1.0; T = 0.34; R = 0.17; W = 0.045
rig = bpy.data.objects.new("IconRig", None); bpy.context.collection.objects.link(rig)
shell = slab("GlassOuter", HW, HH, T, R)
cavity = slab("GlassInner", HW - W, HH - W, T - 2 * W, R - W, flip=True)
AV_Y = -(T / 2 - W) + 0.012
avatar = flat_profile("Avatar", HW - W - 0.004, HH - W - 0.004, AV_Y)
liquid = slab("Liquid", HW - W - 0.004, HH - W - 0.004, T - 2 * W - 0.008, R - W - 0.004)
for o in (shell, cavity, avatar, liquid): o.parent = rig

# liquid boundaries: behind the avatar (icon space), below the level (world space)
bpy.ops.mesh.primitive_cube_add(size=1)
back = bpy.context.active_object; back.name = "LiquidBackCut"
back.scale = (3, 1, 3); back.location = (0, AV_Y + 0.004 + 0.5, 0); back.parent = rig
back.hide_render = True; back.display_type = 'WIRE'

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=96, y_segments=96, size=1.6)
for v in bm.verts: v.co.z = 0.0
top = list(bm.verts)
ext = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces))
for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.z = -4.0
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("Fill"); bm.to_mesh(me); bm.free()
fill = bpy.data.objects.new("LiquidFill", me); bpy.context.collection.objects.link(fill)
vg = fill.vertex_groups.new(name="top"); vg.add([v.index for v in me.vertices if abs(v.co.z) < 1e-6], 1.0, 'REPLACE')
fill.hide_render = True; fill.display_type = 'WIRE'
cl = fill.constraints.new('COPY_LOCATION'); cl.target = rig; cl.use_offset = True
wave_tex = bpy.data.textures.new("Waves", 'CLOUDS'); wave_tex.noise_scale = 0.55; wave_tex.noise_depth = 2
wave_ctl = bpy.data.objects.new("WaveCtl", None); bpy.context.collection.objects.link(wave_ctl)
disp = fill.modifiers.new("Waves", 'DISPLACE'); disp.texture = wave_tex; disp.vertex_group = "top"
disp.texture_coords = 'OBJECT'; disp.texture_coords_object = wave_ctl; disp.direction = 'Z'; disp.mid_level = 0.5; disp.strength = 0.0

b1 = liquid.modifiers.new("Back", 'BOOLEAN'); b1.operation = 'INTERSECT'; b1.object = back; b1.solver = 'EXACT'
b2 = liquid.modifiers.new("Level", 'BOOLEAN'); b2.operation = 'INTERSECT'; b2.object = fill; b2.solver = 'EXACT'

# ---------- materials ----------
def principled(name, **inputs):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    for k, v in inputs.items():
        if k in b.inputs: b.inputs[k].default_value = v
    return m, b

AQUA = (0.074, 1.0, 1.0, 1.0)
glass, gb = principled("Glass", **{"Base Color": (1, 1, 1, 1), "Roughness": 0.0, "IOR": 1.47, "Transmission Weight": 1.0,
                                   "Specular IOR Level": 0.5, "Thin Film Thickness": 320.0, "Thin Film IOR": 1.33})
shell.data.materials.append(glass); cavity.data.materials.append(glass)
liq, lb = principled("Liquid", **{"Base Color": AQUA, "Roughness": 0.02, "IOR": 1.33, "Transmission Weight": 1.0,
                                  "Emission Color": (0.02, 0.85, 0.95, 1), "Emission Strength": 0.55})
va = liq.node_tree.nodes.new("ShaderNodeVolumeAbsorption"); va.inputs["Color"].default_value = (0.05, 0.95, 1.0, 1); va.inputs["Density"].default_value = 2.5
liq.node_tree.links.new(va.outputs["Volume"], liq.node_tree.nodes["Material Output"].inputs["Volume"])
liquid.data.materials.append(liq)
av = bpy.data.materials.new("Avatar"); av.use_nodes = True
nt = av.node_tree; ab = nt.nodes["Principled BSDF"]
img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(HERE, "avatar-alpha.png"))
img.image.alpha_mode = 'STRAIGHT'
nt.links.new(img.outputs["Color"], ab.inputs["Base Color"]); nt.links.new(img.outputs["Alpha"], ab.inputs["Alpha"])
nt.links.new(img.outputs["Color"], ab.inputs["Emission Color"]); ab.inputs["Emission Strength"].default_value = 0.22
ab.inputs["Roughness"].default_value = 0.4
avatar.data.materials.append(av)

# backdrop: dark with a soft aqua glow the glass can refract
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 0), rotation=(math.radians(90), 0, 0))
bd = bpy.context.active_object; bd.name = "Backdrop"
bm_ = bpy.data.materials.new("Backdrop"); bm_.use_nodes = True
n = bm_.node_tree.nodes; l = bm_.node_tree.links; n.clear()
out = n.new("ShaderNodeOutputMaterial"); em = n.new("ShaderNodeEmission")
tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping"); gr = n.new("ShaderNodeTexGradient"); gr.gradient_type = 'SPHERICAL'
ramp = n.new("ShaderNodeValToRGB")
mp.inputs["Scale"].default_value = (0.16, 0.16, 0.16)
l.new(tc.outputs["Object"], mp.inputs["Vector"]); l.new(mp.outputs["Vector"], gr.inputs["Vector"]); l.new(gr.outputs["Fac"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].color = (0.0008, 0.0009, 0.0012, 1)
ramp.color_ramp.elements[1].position = 0.86; ramp.color_ramp.elements[1].color = (0.0012, 0.012, 0.015, 1)
e = ramp.color_ramp.elements.new(0.975); e.color = (0.004, 0.07, 0.08, 1)
l.new(ramp.outputs["Color"], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
l.new(em.outputs["Emission"], out.inputs["Surface"])
bd.data.materials.append(bm_)
bd.visible_shadow = False

# world: studio HDRI for reflections only
w = bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
wn = w.node_tree.nodes; wl = w.node_tree.links; wn.clear()
wo = wn.new("ShaderNodeOutputWorld"); env = wn.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load("/Applications/Blender.app/Contents/Resources/5.2/datafiles/studiolights/world/studio.exr")
bgc = wn.new("ShaderNodeBackground"); bgc.inputs["Strength"].default_value = 0.45
blk = wn.new("ShaderNodeBackground"); blk.inputs["Color"].default_value = (0.0008, 0.0009, 0.0012, 1)
lp = wn.new("ShaderNodeLightPath"); mix = wn.new("ShaderNodeMixShader")
wl.new(env.outputs["Color"], bgc.inputs["Color"])
wl.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"]); wl.new(bgc.outputs["Background"], mix.inputs[1]); wl.new(blk.outputs["Background"], mix.inputs[2])
wl.new(mix.outputs["Shader"], wo.inputs["Surface"])
# the HDRI's round light panels mirror in the flat glass faces as blown-out discs over the avatar's face
# (frames 368-488 of the first render, and again mid-spin); the strip lights draw the glass edges instead
w.cycles_visibility.glossy = False; w.cycles_visibility.transmission = False

def area(name, size, loc, power, color=(1, 1, 1), shape='RECTANGLE', size_y=None, target=(0, 0, 0)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = shape; ld.size = size; ld.size_y = size_y or size
    ld.energy = power; ld.color = color
    ob = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(ob); ob.location = loc
    tr = ob.constraints.new('TRACK_TO'); tgt = bpy.data.objects.new(name + "_t", None); bpy.context.collection.objects.link(tgt)
    tgt.location = target; tr.target = tgt; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    return ob, tgt
key, _ = area("Key", 3.2, (-3.2, -3.4, 3.0), 700, size_y=1.4)
# the key lights the avatar and the covers only; seen in the glass it becomes a blown-out blob over the face
key.visible_glossy = False; key.visible_transmission = False
stripL, _ = area("StripL", 0.22, (-3.6, 0.8, 0.2), 900, size_y=6.0)
stripR, _ = area("StripR", 0.22, (3.6, 0.6, 0.4), 700, color=(0.75, 1.0, 1.0), size_y=6.0)
topl, _ = area("Top", 4.0, (0, -0.5, 4.6), 380, size_y=1.0)
sweep, sweep_t = area("Sweep", 0.35, (-5, -4.0, 0.0), 0, size_y=7.0)
rimT, _ = area("RimTop", 0.18, (0.8, 2.2, 3.4), 520, color=(0.9, 1.0, 1.0), size_y=6.0)

cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 55; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6
cam = bpy.data.objects.new("Cam", cam_d); bpy.context.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (math.radians(90), 0, 0); cam.location = (0, -7.0, 0.0)
cam_d.dof.focus_object = rig

# ---------- animation ----------
from bpy_extras import anim_utils
def key_(ob, path, t, value, index=-1, interp='BEZIER', ease=None):
    setattr(ob, path, value) if index < 0 else getattr(ob, path).__setitem__(index, value)
    ob.keyframe_insert(data_path=path, index=index, frame=F(t))
    idb = ob.id_data; ad = idb.animation_data
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for c in cb.fcurves:
        if c.data_path.endswith(path) and (index < 0 or c.array_index == index):
            for kp in c.keyframe_points:
                if abs(kp.co.x - F(t)) < 0.5: kp.interpolation = interp; kp.easing = ease or 'AUTO'

# the build's contract lives in trailer time; the empty state sits below the cavity
EMPTY, FULL = -1.25, 1.35
# --- intro (T 5.34 -> 16.86) ---
for t, yaw, pitch, bob in [(5.34, 0, 0, 0.00), (7.26, 24, -5, 0.04), (9.18, -16, 6, -0.02), (11.10, 13, -3, 0.03), (13.02, -8, 4, 0.0)]:
    key_(rig, "rotation_euler", t, math.radians(pitch), 0); key_(rig, "rotation_euler", t, math.radians(yaw), 2)
    key_(rig, "location", t, bob, 2)
key_(rig, "rotation_euler", 16.62, math.radians(360), 2); key_(rig, "rotation_euler", 16.62, 0.0, 0)
key_(rig, "location", 16.62, 0.0, 2)
key_(rig, "rotation_euler", 16.86, math.radians(362), 2); key_(rig, "rotation_euler", 16.86, math.radians(-1.5), 0)
for t, y, z in [(5.34, -5.6, 0.0), (9.18, -7.2, 0.0), (13.02, -8.0, 0.0), (16.60, -6.4, 0.0)]:
    key_(cam, "location", t, y, 1); key_(cam, "location", t, z, 2)
key_(cam, "location", 16.60, 0.0, 0)
key_(cam, "location", 16.86, -0.02, 1, interp='EXPO', ease='EASE_IN'); key_(cam, "location", 16.86, 0.52, 2); key_(cam, "location", 16.86, 0.58, 0)
for t, lv in [(5.34, EMPTY), (9.18, EMPTY), (11.10, -0.66), (13.02, -0.08), (14.94, 0.55), (16.40, FULL)]:
    key_(fill, "location", t, lv, 2)
for t, s in [(5.34, 0.0), (9.18, 0.05), (13.02, 0.07), (14.94, 0.12), (16.2, 0.06), (16.86, 0.0)]:
    key_(disp, "strength", t, s)
for t, ang in [(13.02, 0), (14.4, 5), (15.6, -6), (16.62, 3), (17.2, 0)]:
    key_(fill, "rotation_euler", t, math.radians(ang), 1)
for t, x in [(5.34, 0.0), (17.0, 5.5)]:
    key_(wave_ctl, "location", t, x, 0, interp='LINEAR')
    key_(wave_ctl, "location", t, x * 0.6, 1, interp='LINEAR')
# light sweeps on bar downbeats 3, 5, 7 (T 5.34, 9.18, 13.02) and on the lockup
def sweep_at(t0, dur=0.9, power=2200):
    key_(sweep.data, "energy", t0 - 0.01, 0); key_(sweep.data, "energy", t0, power); key_(sweep.data, "energy", t0 + dur, power); key_(sweep.data, "energy", t0 + dur + 0.01, 0)
    key_(sweep, "location", t0, -5.0, 0, interp='LINEAR'); key_(sweep, "location", t0 + dur, 5.0, 0, interp='LINEAR')
for t in (5.40, 9.18, 13.02): sweep_at(t)
sweep_at(14.62, dur=0.7, power=1800)

# --- lockup (T 32.22 -> 37.0): full, settling to front, one shine ---
key_(fill, "location", 31.5, FULL, 2); key_(disp, "strength", 31.5, 0.0)
key_(cam, "location", 17.2, 0.0, 0, interp="CONSTANT"); key_(cam, "location", 32.0, 0.0, 0); key_(cam, "location", 32.0, -11.4, 1); key_(cam, "location", 32.0, -0.50, 2)
for t, yaw, pitch, z in [(32.88, 38, -6, -0.08), (34.30, 0, 0, 0.0), (35.9, -2.5, 1.2, 0.02), (37.3, 1.5, -0.8, 0.0)]:
    key_(rig, "rotation_euler", t, math.radians(360 + yaw), 2); key_(rig, "rotation_euler", t, math.radians(pitch), 0); key_(rig, "location", t, z, 2)
for t, y, z in [(32.88, -11.4, -0.50), (37.3, -12.5, -0.56)]:
    key_(cam, "location", t, y, 1); key_(cam, "location", t, z, 2)
sweep_at(34.14, dur=1.1, power=2600)


import json, random
AUDIO = json.load(open(os.path.join(HERE, "..", "data", "audio.json")))
ART = json.load(open(os.path.join(HERE, "..", "assets", "art", "art.json")))

# covers orbit on a tilted ring behind and around the glass (bars 6-8), refracted through it
orbit = bpy.data.objects.new("Orbit", None); bpy.context.collection.objects.link(orbit)
orbit.rotation_euler = (math.radians(74), math.radians(-8), 0)
picks = [a for a in ART if a["kind"] == "album" and (a["srcWidth"] or 0) >= 500][:28]
NC = len(picks)
for i, a in enumerate(picks):
    ob = flat_profile(f"Cover{i:02d}", 0.3, 0.3, 0.0, N=96)
    ang = 2 * math.pi * i / NC
    ob.location = (2.75 * math.cos(ang), 2.75 * math.sin(ang), 0.0)
    ob.rotation_euler = (math.radians(-90), 0, ang + math.pi / 2)
    ob.parent = orbit
    m = bpy.data.materials.new(f"Cover{i:02d}"); m.use_nodes = True
    nt2 = m.node_tree; pb = nt2.nodes["Principled BSDF"]
    im = nt2.nodes.new("ShaderNodeTexImage"); im.image = bpy.data.images.load(os.path.join(HERE, "..", "assets", "art", a["file"]))
    nt2.links.new(im.outputs["Color"], pb.inputs["Base Color"]); nt2.links.new(im.outputs["Color"], pb.inputs["Emission Color"])
    pb.inputs["Emission Strength"].default_value = 0.22; pb.inputs["Roughness"].default_value = 0.6; pb.inputs["Specular IOR Level"].default_value = 0.2
    ob.data.materials.append(m)
for t, sc_ in [(5.34, 0.0), (11.10, 0.0), (12.4, 1.0), (16.86, 1.0), (17.0, 0.0)]:
    orbit.scale = (sc_, sc_, sc_); orbit.keyframe_insert("scale", frame=F(t))
for t, ang in [(11.10, 0), (13.02, 40), (14.94, 130), (16.86, 330)]:
    key_(orbit, "rotation_euler", t, math.radians(ang), 2)

# bubbles rise through the liquid while it fills and vanish at the surface
fcl = [c for c in anim_utils.action_get_channelbag_for_slot(fill.animation_data.action, fill.animation_data.action_slot).fcurves
       if c.data_path == "location" and c.array_index == 2][0]
bub_mat, bbs = principled("Bubble", **{"Base Color": (1, 1, 1, 1), "Roughness": 0.0, "IOR": 0.75, "Transmission Weight": 1.0})
rng = random.Random(7)
for i in range(46):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.010, 0.030), segments=16, ring_count=8)
    b = bpy.context.active_object; b.name = f"Bubble{i:02d}"; b.data.materials.append(bub_mat); b.parent = rig
    for p_ in b.data.polygons: p_.use_smooth = True
    t0 = rng.uniform(9.4, 16.1); v = rng.uniform(0.7, 1.4); x0 = rng.uniform(-0.8, 0.8); y0 = rng.uniform(-0.085, 0.09)
    b.scale = (0, 0, 0); b.keyframe_insert("scale", frame=F(t0) - 1)
    t = t0
    while t < 17.0:
        z = -0.92 + v * (t - t0)
        level = fcl.evaluate(t * FPS)
        alive = z < level - 0.03 and z < 0.93
        b.location = (x0 + 0.03 * math.sin(7 * (t - t0) + i), y0, z); b.keyframe_insert("location", frame=F(t))
        s_ = 1.0 if alive else 0.0
        b.scale = (s_, s_, s_); b.keyframe_insert("scale", frame=F(t))
        if not alive: break
        t += 1 / 20

# backdrop breathes with the melody and vocals, and with the echo tail after the pause
emn = [n_ for n_ in bm_.node_tree.nodes if n_.type == 'EMISSION'][0]
fe = AUDIO["features"]
for f in range(F(5.2), F(17.0), 2):
    v = 0.75 + 0.9 * fe["mel"][f] + 0.6 * fe["vox"][f]
    emn.inputs["Strength"].default_value = v; emn.inputs["Strength"].keyframe_insert("default_value", frame=f)
STOP_T = 1.442 + 31.313   # the real in-app pause (take E2); the echo throw repeats every beat from there
ECHO0 = 32.4457   # echo_tail --json throwTransient: repeat k is heard at ECHO0 + k beats (0.309 s before STOP_T + k beats)
for t, v in [(STOP_T - 0.03, 0.9), (STOP_T, 2.2)] + [(ECHO0 + 0.48005 * k + d, (0.9 + 1.1 * 0.62 ** (k - 1) if d == 0 else 0.9)) for k in range(1, 7) for d in (0, 0.2)] + [(37.3, 0.9)]:
    emn.inputs["Strength"].default_value = v; emn.inputs["Strength"].keyframe_insert("default_value", frame=F(t))

sc.frame_start, sc.frame_end = F(5.34), F(16.86)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "glass_icon.blend"))
print("saved", sc.frame_start, sc.frame_end)
