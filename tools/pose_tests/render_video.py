"""Render a test video (PNG frames) of a coach GLB performing a clip sequence, seen by a phone-like camera.
args: glb out_dir view(front|side|q45|q-45) seq fps [w h]
seq: comma list of clip names, '*N' repeats a group: e.g. "idle_neutral@1.0,(squat_down,squat_up)*3,idle_neutral@1.0"
"""
import sys, os, math, re, bpy
from mathutils import Vector
glb, out, view, seq, fps = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
W, H = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (360, 640)
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("RV_SAMPLES", "6")); sc.cycles.use_denoising = False
sc.cycles.max_bounces = 3; sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 88; sc.view_settings.view_transform = "Standard"
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.55, 0.56, 1)
def mat(n, c):
    m = bpy.data.materials.new(n); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (*c, 1); return m
bpy.ops.mesh.primitive_plane_add(size=12); bpy.context.object.data.materials.append(mat("floor", (0.42, 0.38, 0.33)))
# room walls behind (so the background is not a studio void)
for loc, rot in (((0, 3.5, 2), (math.radians(90), 0, 0)), ((3.5, 0, 2), (math.radians(90), 0, math.radians(90))), ((-3.5, 0, 2), (math.radians(90), 0, math.radians(90))), ((0, -4.5, 2), (math.radians(90), 0, 0))):
    bpy.ops.mesh.primitive_plane_add(size=8, location=loc, rotation=rot); bpy.context.object.data.materials.append(mat("wall", (0.78, 0.76, 0.72)))
LIGHT = float(os.environ.get("RV_LIGHT", "1.0"))          # <1 = dim room
w.node_tree.nodes["Background"].inputs[1].default_value = LIGHT
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 2.5 * LIGHT; so = bpy.data.objects.new("s", sun); sc.collection.objects.link(so); so.rotation_euler = (0.8, 0.3, 0.9)
ar = bpy.data.lights.new("a", "AREA"); ar.energy = 300 * LIGHT; ar.size = 2; ao = bpy.data.objects.new("a", ar); sc.collection.objects.link(ao); ao.location = (0, -3, 3); ao.rotation_euler = (math.radians(45), 0, 0)
if os.environ.get("RV_BUSY"):                              # cluttered room: shelves, boxes, a plant, posters
    import random
    rnd = random.Random(7)
    for i in range(26):
        x = rnd.uniform(-3.2, 3.2); y = rnd.uniform(1.2, 3.3)
        if abs(x) < 0.9 and y < 2.0: continue
        sz = rnd.uniform(0.2, 0.9)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, sz / 2 + rnd.uniform(0, 1.2)))
        o = bpy.context.object; o.scale = (sz * rnd.uniform(0.5, 1.6), sz * rnd.uniform(0.4, 1.0), sz * rnd.uniform(0.5, 1.8))
        o.data.materials.append(mat("clutter%d" % i, (rnd.random(), rnd.random(), rnd.random())))
    for i in range(5):
        bpy.ops.mesh.primitive_plane_add(size=0.8, location=(rnd.uniform(-3, 3), 3.45, rnd.uniform(1.2, 2.4)), rotation=(math.radians(90), 0, 0))
        bpy.context.object.data.materials.append(mat("poster%d" % i, (rnd.random(), rnd.random() * 0.5, rnd.random())))
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(float(os.environ.get("RV_FOV", "62")))   # phone camera, vertical FOV
yaw = {"front": 0.0, "side": 90.0, "q45": 45.0, "q-45": -45.0, "back": 180.0}.get(view, None)
if yaw is None: yaw = float(view)
dist = float(os.environ.get("RV_DIST", "2.9")); ch = float(os.environ.get("RV_CAMH", "0.95"))
a = math.radians(yaw)
cam.location = Vector((dist * math.sin(a), -dist * math.cos(a), ch))
tgt = Vector((0, 0, float(os.environ.get("RV_TGTH", "0.85"))))
cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
# expand the sequence
def expand(s):
    while "(" in s:
        s = re.sub(r"\(([^()]*)\)\*(\d+)", lambda m: ",".join([m.group(1)] * int(m.group(2))), s)
    return [x for x in s.split(",") if x]
items = []
for it in expand(seq):
    name, _, dur = it.partition("@")
    name, _, speed = name.partition("^")
    name_hold = name.endswith("!"); name = name.rstrip("!")      # name^3 = play 3x faster, name^0.3 = slow motion
    sp = float(speed) if speed else 1.0
    act = bpy.data.actions[name]; a0, b0 = act.frame_range
    if dur and name_hold:   # name!@dur: hold the clip's last pose for dur seconds
        for i in range(int(float(dur) * fps)): items.append((act, b0))
    elif dur:   # loop a clip for dur seconds
        n = int(float(dur) * fps)
        for i in range(n): items.append((act, a0 + ((i * 30.0 / fps) % max(b0 - a0, 1))))
    else:
        n = int(round((b0 - a0) / 30.0 * fps / sp)) + 1
        for i in range(n): items.append((act, min(b0, a0 + i * 30.0 * sp / fps)))
print("RV frames", len(items), flush=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
fault = os.environ.get("RV_FAULT")
if fault:
    import faults
    fault_fn = faults.FAULTS[fault]
fctx = {}
cur = None
pick = set(int(x) for x in os.environ.get("RV_PICK", "").split(",") if x)
for i, (act, f) in enumerate(items):
    if act is not cur:
        arm.animation_data.action = act
        try: arm.animation_data.action_slot = act.slots[0]
        except Exception: pass
        cur = act
    sc.frame_set(int(f), subframe=f - int(f))
    if fault:
        fault_fn(arm, fctx)
    if pick and i not in pick:
        continue
    if fault:
        # rendering re-evaluates the action and would overwrite the edited pose: freeze it for this render
        keep = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones}
        arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.location, pb.rotation_quaternion, pb.scale = keep[pb.name]
        bpy.context.view_layer.update()
        cur = None
    sc.render.filepath = os.path.join(out, "f%04d.jpg" % i); bpy.ops.render.render(write_still=True)
open(os.path.join(out, "meta.txt"), "w").write("fps=%d\nframes=%d\nseq=%s\nview=%s\nfault=%s\n" % (fps, len(items), seq, view, fault))
print("RV done", out, flush=True)
