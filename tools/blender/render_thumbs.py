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
    "reverse_lunge": ("reverse_lunge", ("far", "hips"), 65),
    "glute_bridge": ("glute_bridge", ("far", "hips"), 70),
    "forearm_plank": ("plank_hold", 0.0, 70),
    "step_jack": ("step_jack", ("far", "hand_R"), 15),
    "calf_raise": ("calf_raise", ("far", "hips"), 45),
    "boxing_lead_hook": ("boxing_lead_hook", ("far", "hand_L"), -40),
    "boxing_slip": ("boxing_slip", ("far", "head"), 25),
    "footwork_lateral": ("footwork_lateral", ("far", "hips"), 30),
    "sumo_squat": ("sumo_squat_down", "end", 25),
    "split_squat": ("split_squat", ("far", "hips"), 65),
    "side_lunge": ("side_lunge", ("far", "hips"), 15),
    "knee_push_up": ("knee_pushup_down", "start", 70),
    "slow_mountain_climber": ("mountain_climber_slow", ("far", "foot_R"), 70),
    "dead_bug": ("dead_bug", ("far", "hand_R"), 70),
    "bird_dog": ("bird_dog", ("far", "hand_R"), 70),
    "superman": ("superman", ("far", "hand_R"), 70),
    "high_knee_march": ("high_knee_march", "knee", 50),
    "arm_circles": ("arm_circles", 0.3, 20),
    "cat_cow": ("cat_cow", 0.38, 70),
    "dumbbell_biceps_curl": ("db_curl", ("far", "hand_R"), 30),
    "dumbbell_shoulder_press": ("db_shoulder_press", 0.0, 25),
    "dumbbell_lateral_raise": ("db_lateral_raise", ("far", "hand_R"), 15),
    "dumbbell_bent_over_row": ("db_bent_over_row", ("far", "hand_R"), 65),
    "dumbbell_romanian_deadlift": ("db_rdl_down", "end", 70),
    "kettlebell_deadlift": ("kb_deadlift_down", "end", 40),
    "band_pull_apart": ("band_pull_apart", ("far", "hand_R"), 20),
    "incline_push_up": ("incline_pushup_down", "start", 60),
    "boxing_rear_uppercut": ("boxing_rear_uppercut", ("far", "hand_R"), -35),
    "boxing_lead_uppercut": ("boxing_lead_uppercut", ("far", "hand_L"), -35),
    "boxing_rear_hook": ("boxing_rear_hook", ("far", "hand_R"), -35),
    "boxing_roll": ("boxing_roll", ("far", "head"), 20),
    "footwork_pivot": ("footwork_pivot", ("far", "foot_R"), 30),
    "forward_lunge": ("forward_lunge", ("far", "hips"), 65),
    "dumbbell_hammer_curl": ("db_hammer_curl", ("far", "hand_R"), 30),
    "dumbbell_front_raise": ("db_front_raise", ("far", "hand_R"), 40),
    "boxing_one_two": ("boxing_one_two", ("far", "hand_R"), -35),
    "boxing_one_two_hook": ("boxing_one_two_hook", ("far", "hand_L"), -35),
    "standing_knee_crunch": ("knee_crunch", "knee", 40),
    "dumbbell_reverse_fly": ("db_reverse_fly", ("far", "hand_R"), 25),
    "dumbbell_overhead_triceps_extension": ("db_overhead_triceps", ("far", "hand_R"), 55),
    "boxing_jab_jab_cross": ("boxing_jab_jab_cross", ("far", "hand_R"), -35),
    "dumbbell_squat": ("db_squat", ("far", "hips"), 40),
    "dumbbell_reverse_lunge": ("db_reverse_lunge", ("far", "hips"), 55),
    "standing_oblique_crunch": ("oblique_crunch", "knee", 20),
    "boxing_double_jab": ("boxing_double_jab", "punch", -35),
    "boxing_body_jab": ("boxing_body_jab", "punch", -40),
    "boxing_cross_hook": ("boxing_cross_hook", ("far", "hand_L"), -35),
    "boxing_pull_back": ("boxing_pull_back", ("far", "head"), 70),
    "boxing_step_jab": ("boxing_step_jab", "punch", -60),
    # batch 7 (2026-11-24)
    "good_morning": ("good_morning", ("far", "head"), 75),
    "curtsy_lunge": ("curtsy_lunge", ("far", "hips"), 25),
    "squat_calf_raise": ("squat_calf_raise", ("far", "hips"), 60),
    "single_leg_balance": ("single_leg_balance", ("far", "foot_R"), 40),
    "single_leg_rdl": ("single_leg_rdl", ("far", "foot_R"), 75),
    "side_leg_raise": ("side_leg_raise", ("far", "foot_R"), 10),
    "glute_kickback": ("glute_kickback", ("far", "foot_R"), 75),
    "butt_kicks": ("butt_kicks", ("far", "foot_L"), 70),
    "standing_torso_twist": ("torso_twist", ("far", "hand_R"), 15),
    "standing_side_bend": ("side_bend", ("far", "hand_R"), 5),
    "skater_step": ("skater_step", ("far", "hips"), 20),
    "wall_push_up": ("wall_pushup", ("far", "head"), 70),
    "wall_sit": ("wall_sit", ("far", "hips"), 65),
    "dumbbell_goblet_squat": ("db_goblet_squat", ("far", "hips"), 55),
    "dumbbell_floor_press": ("db_floor_press", ("far", "hand_R"), 70),
    "dumbbell_shrug": ("db_shrug", ("far", "hand_R"), 25),
    "dumbbell_calf_raise": ("db_calf_raise", ("far", "hips"), 50),
    "kettlebell_swing": ("kb_swing", ("far", "hand_R"), 75),
    "bench_dip": ("bench_dip", ("far", "hips"), 60),
    "crunch": ("crunch", ("far", "head"), 70),
    "heel_taps": ("heel_taps", ("far", "hand_R"), 50),
    "reverse_crunch": ("reverse_crunch", ("far", "hips"), 70),
    "tabletop_toe_taps": ("toe_taps", ("far", "foot_R"), 70),
    "high_plank": ("high_plank", 0.0, 70),
    "plank_shoulder_taps": ("shoulder_taps", ("far", "hand_R"), 40),
    "single_leg_glute_bridge": ("single_leg_bridge", ("far", "hips"), 70),
    "donkey_kick": ("donkey_kick", ("far", "foot_R"), 70),
    "fire_hydrant": ("fire_hydrant", ("far", "foot_R"), 30),
    "childs_pose": ("childs_pose", ("far", "hips"), 70),
    "bear_plank_hold": ("bear_hold", ("far", "hips"), 55),
    "boxing_body_cross": ("boxing_body_cross", ("far", "hand_R"), -45),
    "boxing_body_hook": ("boxing_body_hook", ("far", "hand_L"), -40),
    "boxing_rear_body_hook": ("boxing_rear_body_hook", ("far", "hand_R"), -40),
    "boxing_jab_body_cross": ("boxing_jab_body_cross", ("far", "hand_R"), -45),
    "boxing_body_head_jab": ("boxing_body_head_jab", ("far", "hand_L"), -50),
    "boxing_parry": ("boxing_parry", ("far", "hand_R"), -25),
    "boxing_catch": ("boxing_catch", ("far", "hand_R"), -25),
    "boxing_high_block": ("boxing_high_block", ("far", "hand_L"), -20),
    "boxing_body_block": ("boxing_body_block", ("far", "hand_L"), -25),
    "boxing_duck": ("boxing_duck", ("far", "head"), 30),
    "boxing_block_cross": ("boxing_block_cross", ("far", "hand_R"), -40),
    "boxing_jab_slip": ("boxing_jab_slip", ("far", "head"), 20),
    "boxing_slip_cross": ("boxing_slip_cross", ("far", "hand_R"), -40),
    "boxing_roll_hook": ("boxing_roll_hook", ("far", "hand_L"), -30),
    "boxing_pull_counter": ("boxing_pull_counter", ("far", "hand_R"), -45),
    "boxing_jab_uppercut": ("boxing_jab_uppercut", ("far", "hand_R"), -35),
    "boxing_uppercut_hook": ("boxing_uppercut_hook", ("far", "hand_L"), -35),
    "boxing_hook_cross": ("boxing_hook_cross", ("far", "hand_R"), -40),
    "boxing_cross_hook_cross": ("boxing_cross_hook_cross", ("far", "hand_L"), -40),
    "boxing_one_two_uppercut": ("boxing_one_two_uppercut", ("far", "hand_R"), -40),
    "boxing_uppercuts": ("boxing_uppercuts", ("far", "hand_R"), -35),
    "boxing_stance_bounce": ("boxing_stance_bounce", 0.25, 30),
    "boxing_fist_rolls": ("boxing_fist_rolls", 0.3, -30),
    "footwork_circle_left": ("footwork_circle_left", ("far", "foot_R"), 25),
    "footwork_circle_right": ("footwork_circle_right", ("far", "foot_R"), 25),
    "footwork_angle_step": ("footwork_angle_step", ("far", "foot_R"), 25),
    "footwork_in_out": ("footwork_shuffle", ("far", "hips"), 60),
    "boxing_back_jab": ("boxing_back_jab", "punch", -55),
    "boxing_lateral_jab": ("boxing_lateral_jab", "punch", -45),
    "boxing_jab_pivot": ("boxing_jab_pivot", ("far", "foot_R"), 25),
    "hero": ("idle_neutral", 0.0, 18),
}

bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"   # keep the source texture colours (AgX bleached the skin)
sc.render.image_settings.file_format = "WEBP"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.quality = 82

# the owner's rigged coach (coach_rig) when present, else the MOTIONFORGE rig
arm = bpy.data.objects.get("coach_rig") or next(o for o in bpy.data.objects if o.type == "ARMATURE")
MIX = arm.name == "coach_rig"


def bone(name):
    """MOTIONFORGE bone name -> this armature's bone."""
    if not MIX:
        return arm.pose.bones[name]
    if name in ("hips", "head"):
        return arm.pose.bones["mixamorig:" + name.capitalize()]
    base, side = name.rsplit("_", 1)
    sd = "Left" if side == "L" else "Right"
    return arm.pose.bones["mixamorig:" + sd + {"hand": "Hand", "shin": "Leg", "foot": "Foot"}[base]]
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm)
for o in list(bpy.data.objects):
    if o.type == "LIGHT" or (o.type == "MESH" and o is not mesh and not o.name.startswith("prop_")):
        bpy.data.objects.remove(o)

world = sc.world or bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.25, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9


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
    if isinstance(how, tuple) and how[0] == "far":       # frame where this bone is furthest from where it started
        sc.frame_set(f0)
        p0 = (arm.matrix_world @ bone(how[1]).head).copy()
        best, dist = f0, -1.0
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            d = ((arm.matrix_world @ bone(how[1]).head) - p0).length
            if d > dist:
                best, dist = f, d
        return best
    if how == "start":
        return f0
    if how == "end":
        return f1
    best, score = f0, None
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        if how == "punch":  # hand furthest forward (coach faces -Y)
            s = min((arm.matrix_world @ bone(f"hand_{x}").tail).y for x in "LR")
        else:  # knee: highest knee
            s = -max((arm.matrix_world @ bone(f"shin_{x}").head).z for x in "LR")
        if score is None or s < score:
            best, score = f, s
    return best


for key, (clip, how, yaw_deg) in SHOTS.items():
    act = bpy.data.actions[clip]
    if arm.animation_data is None:
        arm.animation_data_create()
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
    area("key", 380, 2.5, (1.0, 0.96, 0.9), c - fwd * 3 + right * 2.2 + Vector((0, 0, 2.2)), c)
    area("fill", 160, 3.5, (0.85, 0.92, 1.0), c - fwd * 3 - right * 2.5 + Vector((0, 0, 0.6)), c)
    area("rimL", 260, 1.2, (0.9, 1.0, 0.7), c + fwd * 2.5 - right * 1.6 + Vector((0, 0, 1.6)), c)
    area("rimR", 260, 1.2, (1.0, 0.75, 0.6), c + fwd * 2.5 + right * 1.6 + Vector((0, 0, 1.6)), c)
    sc.render.filepath = os.path.join(out_dir, f"{key}.webp")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", key, sc.frame_current)
