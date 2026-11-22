"""Render the frames for each lesson's motion study (multi-exposure plate), after Marey's chronophotographs.

Usage: python tools/blender/render_studies.py assets/blender/source/coach_f.blend <frames_dir> [lesson ...]
Writes <frames_dir>/<lesson>_<i>.png (RGBA, fixed camera per lesson, last frame = the key position).
Compose them with tools/compose_studies.py.
"""
import math, os, sys, time
import bpy
from mathutils import Vector

src, out = sys.argv[1:3]
only = set(sys.argv[3:])
_code = open(os.path.join(os.path.dirname(__file__), "render_thumbs.py")).read()
_ns = {}
exec(_code[_code.index("SHOTS = {"):_code.index("bpy.ops.wm.open_mainfile")], _ns)
SHOTS = {k: v for k, v in _ns["SHOTS"].items() if k != "hero"}
N = 7
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("MF_SAMPLES", "16")); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 3
sc.render.film_transparent = True; sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.render.resolution_x, sc.render.resolution_y = 600, 750
arm = bpy.data.objects.get("coach_rig") or next(o for o in bpy.data.objects if o.type == "ARMATURE")
MIX = arm.name == "coach_rig"
def bone(name):
    if not MIX: return arm.pose.bones[name]
    if name in ("hips", "head"): return arm.pose.bones["mixamorig:" + name.capitalize()]
    base, side = name.rsplit("_", 1); sd = "Left" if side == "L" else "Right"
    return arm.pose.bones["mixamorig:" + sd + {"hand": "Hand", "shin": "Leg", "foot": "Foot"}[base]]
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm)
for o in list(bpy.data.objects):
    if o.type == "LIGHT" or (o.type == "MESH" and o is not mesh and not o.name.startswith("prop_")):
        bpy.data.objects.remove(o)
w = sc.world or bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.2, 0.22, 0.25, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 60; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
def bbox():
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pts = [ev.matrix_world @ v.co for i, v in enumerate(ev.data.vertices) if i % 9 == 0]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])
def area(n, e, s, col, loc, t):
    d = bpy.data.lights.new(n, "AREA"); d.energy, d.size, d.color = e, s, col
    o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(t) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
def pick(act, how):
    f0, f1 = (int(x) for x in act.frame_range)
    if isinstance(how, float): return round(f0 + how * (f1 - f0))
    if isinstance(how, tuple):
        sc.frame_set(f0); p0 = (arm.matrix_world @ bone(how[1]).head).copy(); best, dist = f0, -1.0
        for f in range(f0, f1 + 1):
            sc.frame_set(f); d = ((arm.matrix_world @ bone(how[1]).head) - p0).length
            if d > dist: best, dist = f, d
        return best
    if how == "start": return f0
    if how == "end": return f1
    best, score = f0, None
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        s = min((arm.matrix_world @ bone(f"hand_{x}").tail).y for x in "LR") if how == "punch" else -max((arm.matrix_world @ bone(f"shin_{x}").head).z for x in "LR")
        if score is None or s < score: best, score = f, s
    return best
for key, (clip, how, yaw_deg) in SHOTS.items():
    if only and key not in only: continue
    t0 = time.time()
    act = bpy.data.actions[clip]
    if arm.animation_data is None: arm.animation_data_create()
    arm.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    k = pick(act, how)
    a = f1 if k == f0 else f0          # the study runs from the far end of the clip into the key position
    frames = [round(a + i * (k - a) / (N - 1)) for i in range(N)]
    lo = Vector((9, 9, 9)); hi = Vector((-9, -9, -9))
    for f in frames:
        sc.frame_set(f); p, q = bbox()
        lo = Vector([min(lo[i], p[i]) for i in range(3)]); hi = Vector([max(hi[i], q[i]) for i in range(3)])
    c = (lo + hi) / 2; yaw = math.radians(yaw_deg)
    fwd = Vector((-math.sin(yaw), math.cos(yaw), 0)); right = Vector((math.cos(yaw), math.sin(yaw), 0))
    fov = 2 * math.atan(12 / cam.data.lens)
    h = (hi - lo).z; wd = abs((hi - lo).x * math.cos(yaw)) + abs((hi - lo).y * math.sin(yaw))
    dist = max(h * 1.14 / 2 / math.tan(fov / 2), wd * 1.14 * 750 / 600 / 2 / math.tan(fov / 2))
    cam.location = c - fwd * dist + Vector((0, 0, 0.04 * h))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    for o in [o for o in sc.objects if o.type == "LIGHT"]: bpy.data.objects.remove(o)
    area("key", 380, 2.5, (1, .96, .9), c - fwd * 3 + right * 2.2 + Vector((0, 0, 2.2)), c)
    area("fill", 140, 3.5, (.85, .92, 1), c - fwd * 3 - right * 2.5 + Vector((0, 0, .6)), c)
    area("rim", 320, 1.2, (1, 1, 1), c + fwd * 2.5 + Vector((0, 0, 1.6)), c)
    for i, f in enumerate(frames):
        sc.frame_set(f); sc.render.filepath = os.path.join(out, f"{key}_{i}.png")
        bpy.ops.render.render(write_still=True)
    print("STUDY", key, frames, f"{time.time() - t0:.0f}s", flush=True)
