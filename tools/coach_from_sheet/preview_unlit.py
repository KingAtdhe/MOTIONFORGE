"""Unlit (as in the app) Cycles renders of the exported coach: python preview_unlit.py <blend> <outdir>"""
import math, os, sys, bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
out = argv[1]
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24
try:
    sc.cycles.use_denoising = False
except Exception:
    pass
sc.view_settings.view_transform = "Standard"
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.80, 0.84, 1)
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bs = nt.nodes.get("Principled BSDF")
    if bs is None:
        continue
    em = nt.nodes.new("ShaderNodeEmission")
    link = bs.inputs["Base Color"].links
    if link:
        nt.links.new(link[0].from_socket, em.inputs[0])
    else:
        em.inputs[0].default_value = bs.inputs["Base Color"].default_value
    outn = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(em.outputs[0], outn.inputs[0])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam


def shot(name, clip, frame, yaw, target, dist, lens, res):
    if clip is None:
        arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    else:
        arm.animation_data.action = bpy.data.actions[clip]
    sc.frame_set(frame)
    y = math.radians(yaw); t = Vector(target)
    cam.location = (t.x + dist * math.sin(y), t.y - dist * math.cos(y), t.z)
    cam.rotation_euler = (math.radians(90), 0, y)
    cam.data.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)


if arm.animation_data is None:
    arm.animation_data_create()
full = dict(target=(0, 0, 0.86), dist=6.2, lens=85, res=(460, 1000))
shot("turn_front", "idle_neutral", 1, 0, **full)
shot("turn_side", "idle_neutral", 1, 90, **full)
shot("turn_back", "idle_neutral", 1, 180, **full)
shot("hero", "idle_neutral", 1, 24, (0.02, 0, 1.12), 2.25, 60, (900, 1300))
shot("pose_squat", "squat_down", 49, 38, (0, -0.15, 0.72), 4.4, 70, (640, 800))
shot("pose_jab", "boxing_jab", 13, 58, (0, -0.2, 0.95), 4.6, 70, (640, 800))
shot("pose_cross", "boxing_cross", 15, 70, (0, -0.2, 0.95), 4.6, 70, (640, 800))
shot("pose_step", "footwork_forward", 15, 100, (0, -0.1, 0.92), 4.8, 70, (640, 800))
shot("det_face", "idle_neutral", 1, 15, (0, 0, 1.56), 1.3, 105, (560, 560))
shot("det_core", "idle_neutral", 1, 16, (0, 0, 1.14), 1.6, 90, (560, 560))
shot("det_glove", "boxing_stance", 1, 50, (0.05, -0.25, 1.30), 1.2, 90, (560, 560))
shot("det_shoe", "idle_neutral", 1, 40, (0.12, -0.04, 0.08), 1.1, 80, (560, 560))
