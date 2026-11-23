import sys, os, math, bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
glb, out = a[0], a[1]; jobs = a[2:]          # each job: clip:f1,f2,..:yaw[:low]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 6; sc.cycles.use_denoising = False; sc.cycles.max_bounces = 2
sc.render.resolution_x, sc.render.resolution_y = 360, 450
sc.render.image_settings.file_format = "JPEG"; sc.view_settings.view_transform = "Standard"
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if not arm.animation_data: arm.animation_data_create()
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.62, 1)
m = bpy.data.materials.new("floor"); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.42, 0.5, 1)
bpy.ops.mesh.primitive_plane_add(size=12); bpy.context.object.data.materials.append(m)
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3; so = bpy.data.objects.new("s", sun); sc.collection.objects.link(so); so.rotation_euler = (0.7, 0.2, 0.6)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
os.makedirs(out, exist_ok=True)
hips = next(b for b in arm.pose.bones if b.name.endswith("Hips"))
for job in jobs:
    p = job.split(":"); clip, frames, yaw = p[0], [float(x) for x in p[1].split(",")], float(p[2]); dist = float(p[3]) if len(p) > 3 else 3.2
    act = bpy.data.actions[clip]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    for f in frames:
        sc.frame_set(int(f), subframe=f - int(f))
        c = arm.matrix_world @ hips.head; tgt = Vector((c.x, c.y, max(0.35, c.z * 0.95)))
        r = math.radians(yaw); cam.location = tgt + Vector((dist * math.sin(r), -dist * math.cos(r), 0.35))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out, f"{clip}_{yaw:.0f}_{f:05.1f}.jpg"); bpy.ops.render.render(write_still=True)
print("CLOSE done")
