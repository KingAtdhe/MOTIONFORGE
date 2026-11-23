import sys, os, json, math, bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
glb, out, lessons_json = a[0], a[1], a[2]
only = set(a[3].split(",")) if len(a) > 3 and a[3] else None
NF = int(os.environ.get("NF", "8"))
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = int(os.environ.get("SAMPLES", "4")); sc.cycles.use_denoising = False
sc.cycles.max_bounces = 2; sc.render.resolution_x, sc.render.resolution_y = 240, 300
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 85; sc.view_settings.view_transform = "Standard"
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if not arm.animation_data: arm.animation_data_create()
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.62, 1)
m = bpy.data.materials.new("floor"); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.42, 0.5, 1)
bpy.ops.mesh.primitive_plane_add(size=12); bpy.context.object.data.materials.append(m)
# floor grid lines every 25 cm to make sliding feet visible
gm = bpy.data.materials.new("grid"); gm.use_nodes = True; gm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
for i in range(-8, 9):
    for rot in (0, 90):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.001)); o = bpy.context.object
        o.scale = (0.004, 4, 1) if rot == 0 else (4, 0.004, 1); o.location = (i * 0.25, 0, 0.001) if rot == 0 else (0, i * 0.25, 0.001)
        o.data.materials.append(gm)
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3; so = bpy.data.objects.new("s", sun); sc.collection.objects.link(so); so.rotation_euler = (0.7, 0.2, 0.6)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 35
L = json.load(open(lessons_json))
avail = {x.name: x for x in bpy.data.actions}
def resolve(d):
    if d.endswith("_down") and d[:-5] + "_up" in avail: return [d, d[:-5] + "_up"]
    pr = {"footwork_forward": "footwork_backward", "footwork_backward": "footwork_forward"}
    if d in pr: return [d, pr[d]]
    return [d]
for les in L:
    if only and les["id"] not in only: continue
    seq = resolve(les["demoAnimation"])
    frames = []
    for n in seq:
        act = avail[n]; f0, f1 = act.frame_range
        frames += [(act, f) for f in range(int(round(f0)), int(math.floor(f1)) + 1)]
    picks = [frames[round(i * (len(frames) - 1) / (NF - 1))] for i in range(NF)]
    low = les["id"] in ("glute_bridge", "forearm_plank", "push_up", "knee_push_up", "dead_bug", "bird_dog", "cat_cow", "superman", "slow_mountain_climber", "incline_push_up")
    for vi, yaw in enumerate((25.0, 90.0)):
        r = math.radians(yaw); d = 3.6 if low else 3.2
        tz = 0.45 if low else 0.9
        cam.location = Vector((d * math.sin(r), -d * math.cos(r), 1.3 if low else 1.15))
        cam.rotation_euler = (Vector((0, 0 if not low else 0.2, tz)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        for i, (act, f) in enumerate(picks):
            arm.animation_data.action = act
            try: arm.animation_data.action_slot = act.slots[0]
            except Exception: pass
            sc.frame_set(f)
            sc.render.filepath = os.path.join(out, f"{les['id']}__{vi}_{i}.jpg"); bpy.ops.render.render(write_still=True)
    print("SHEET", les["id"], flush=True)
