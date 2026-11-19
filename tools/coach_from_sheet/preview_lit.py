"""Studio-lit Cycles renders (3-point lighting + soft ambient) of the coach: preview_lit.py <blend> <outdir> [quick]"""
import math, os, sys, bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
out = argv[1]; quick = len(argv) > 2
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24 if quick else 64
try:
    sc.cycles.use_denoising = True
except Exception:
    pass
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Punchy"
except Exception:
    pass
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.55, 0.56, 0.60, 1); bg.inputs[1].default_value = 0.55
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if arm.animation_data is None:
    arm.animation_data_create()


def area(name, energy, size, color):
    l = bpy.data.lights.new(name, "AREA"); l.energy, l.size, l.color = energy, size, color
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); return o


rig = [(area("key", 260, 1.8, (1.0, 0.95, 0.90)), (-2.2, -2.8, 2.6)), (area("fill", 70, 3.0, (0.85, 0.9, 1.0)), (2.6, -2.2, 1.4)),
       (area("rim_l", 380, 1.0, (1.0, 1.0, 1.0)), (-2.0, 2.4, 2.2)), (area("rim_r", 300, 1.0, (1.0, 0.92, 0.88)), (2.2, 2.2, 2.0))]
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam


def shot(name, clip, frame, yaw, target, dist, lens, res):
    arm.animation_data.action = bpy.data.actions[clip]
    sc.frame_set(frame)
    y = math.radians(yaw); t = Vector(target)
    cam.location = (t.x + dist * math.sin(y), t.y - dist * math.cos(y), t.z)
    cam.rotation_euler = (math.radians(90), 0, y)
    cam.data.lens = lens
    R = __import__("mathutils").Matrix.Rotation(y, 4, "Z")
    for o, base in rig:
        o.location = R @ Vector(base) + Vector((t.x, t.y, 0))
        o.rotation_euler = (Vector((t.x, t.y, 1.1)) - o.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)


s = 0.5 if quick else 1.0
full = dict(target=(0, 0, 0.86), dist=6.2, lens=85, res=(int(460 * s), int(1000 * s)))
shot("hero", "idle_neutral", 1, 28, (0.02, 0, 1.12), 2.25, 60, (int(900 * s), int(1300 * s)))
shot("det_face", "idle_neutral", 1, 25, (0, 0, 1.53), 1.2, 105, (int(560 * s), int(560 * s)))
shot("det_core", "idle_neutral", 1, 22, (0, 0, 1.14), 1.6, 90, (int(560 * s), int(560 * s)))
shot("pose_jab", "boxing_jab", 13, 58, (0, -0.2, 0.95), 4.6, 70, (int(640 * s), int(800 * s)))
if not quick:
    shot("turn_front", "idle_neutral", 1, 0, **full)
    shot("turn_side", "idle_neutral", 1, 90, **full)
    shot("turn_back", "idle_neutral", 1, 180, **full)
    shot("pose_cross", "boxing_cross", 15, 70, (0, -0.2, 0.95), 4.6, 70, (640, 800))
    shot("pose_squat", "squat_down", 49, 38, (0, -0.15, 0.72), 4.4, 70, (640, 800))
    shot("pose_step", "footwork_forward", 15, 100, (0, -0.1, 0.92), 4.8, 70, (640, 800))
    shot("det_glove", "boxing_stance", 1, 50, (0.05, -0.25, 1.30), 1.2, 90, (560, 560))
    shot("det_shoe", "idle_neutral", 1, 40, (0.12, -0.04, 0.08), 1.1, 80, (560, 560))
