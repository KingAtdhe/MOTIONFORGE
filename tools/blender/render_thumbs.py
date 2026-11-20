"""Render lesson thumbnails and a hero portrait of a coach for the app UI.

Usage: python tools/blender/render_thumbs.py assets/blender/source/coach_f.blend coach_f <out_dir>
Writes <out_dir>/<exercise_id>.webp (transparent, 3:4) and hero.webp.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

src, coach, out_dir = sys.argv[1:4]
os.makedirs(out_dir, exist_ok=True)

# exercise id -> (clip, frame picker, camera yaw in degrees; 0 = front)
SHOTS = {
    "standing_mobility_warmup": ("warmup_march", "knee", 60),
    "bodyweight_squat": ("squat_down", "end", 65),
    "hip_hinge": ("hip_hinge_down", "end", 80),
    "push_up": ("pushup_down", "start", 70),
    "boxing_stance": ("boxing_stance", 0.3, 30),
    "boxing_jab": ("boxing_jab", "punch", -55),
    "boxing_cross": ("boxing_cross", "punch", -55),
    "boxing_guard_return": ("boxing_guard_return", "end", 30),
    "footwork_forward_backward": ("footwork_forward", 0.4, 55),
    "hero": ("boxing_stance", 0.3, 22),
}

bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.render.image_settings.file_format = "WEBP"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.quality = 82

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm)
for o in list(bpy.data.objects):
    if o.type == "LIGHT" or (o.type == "MESH" and o is not mesh):
        bpy.data.objects.remove(o)

world = sc.world or bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.25, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6


def area(name, energy, size, color, loc, target):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = energy, size, color
    o = bpy.data.objects.new(name, d)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 70


def bbox():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    pts = [ev.matrix_world @ v.co for v in ev.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def pick(act, how):
    f0, f1 = (int(x) for x in act.frame_range)
    if isinstance(how, float):
        return round(f0 + how * (f1 - f0))
    if how == "start":
        return f0
    if how == "end":
        return f1
    best, score = f0, None
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        if how == "punch":  # hand furthest forward (coach faces -Y)
            s = min((arm.matrix_world @ arm.pose.bones[f"hand_{x}"].tail).y for x in "LR")
        else:  # knee: highest knee
            s = -max((arm.matrix_world @ arm.pose.bones[f"shin_{x}"].head).z for x in "LR")
        if score is None or s < score:
            best, score = f, s
    return best


for key, (clip, how, yaw_deg) in SHOTS.items():
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    sc.frame_set(pick(act, how))
    lo, hi = bbox()
    c = (lo + hi) / 2
    hero = key == "hero"
    sc.render.resolution_x, sc.render.resolution_y = (900, 1200) if hero else (480, 640)
    yaw = math.radians(yaw_deg)
    fwd = Vector((-math.sin(yaw), math.cos(yaw), 0))  # camera looks along this
    # frame the body: fit max of height and projected width into a 3:4 view with margin
    w = max(abs((hi - lo).x * math.cos(yaw)) + abs((hi - lo).y * math.sin(yaw)), 0.3)
    h = (hi - lo).z
    sensor = cam.data.sensor_width
    fov_w = 2 * math.atan(sensor / 2 / cam.data.lens)
    fov_h = 2 * math.atan(sensor * 4 / 3 / 2 / cam.data.lens)
    cam.data.sensor_fit = "HORIZONTAL"
    dist = max(w * 1.12 / 2 / math.tan(fov_w / 2), h * 1.06 / 2 / math.tan(fov_h / 2))
    cam.location = c - fwd * dist + Vector((0, 0, 0.06 * h))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    for o in [o for o in sc.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o)
    right = Vector((math.cos(yaw), math.sin(yaw), 0))
    area("key", 650, 2.5, (1.0, 0.96, 0.9), c - fwd * 3 + right * 2.2 + Vector((0, 0, 2.2)), c)
    area("fill", 220, 3.5, (0.85, 0.92, 1.0), c - fwd * 3 - right * 2.5 + Vector((0, 0, 0.6)), c)
    area("rimL", 520, 1.2, (0.9, 1.0, 0.7), c + fwd * 2.5 - right * 1.6 + Vector((0, 0, 1.6)), c)
    area("rimR", 520, 1.2, (1.0, 0.75, 0.6), c + fwd * 2.5 + right * 1.6 + Vector((0, 0, 1.6)), c)
    sc.render.filepath = os.path.join(out_dir, f"{key}.webp")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", key, sc.frame_current)
