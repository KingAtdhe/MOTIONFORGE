"""
Builds the MOTIONFORGE trainer avatar end to end, from scratch:
body mesh -> armature -> skin weights -> draft animation clips -> .blend source -> GLB export.

Run with Blender's Python (e.g. `blender -b -P tools/blender/build_trainer.py` or the `bpy` module):
    python tools/blender/build_trainer.py [--previews]
Outputs (relative to repo root):
    assets/blender/source/trainer_avatar.blend
    assets/blender/exports/trainer_avatar.glb
    app/src/main/assets/models/trainer_avatar.glb   (copy used by the app)
    assets/blender/previews/*.png                   (with --previews)
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

import bpy  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)

import trainer_anim as ta  # noqa: E402
import trainer_body as tb  # noqa: E402
import trainer_rig as tr  # noqa: E402

scene = bpy.context.scene
scene.render.fps = ta.FPS

body, parts = tb.build_body()
arm = tr.build_armature()
avatar = tr.skin(body, parts, arm)
actions = ta.build_clips(arm)
arm.animation_data.action = None

src = os.path.join(ROOT, "assets/blender/source/trainer_avatar.blend")
exp = os.path.join(ROOT, "assets/blender/exports/trainer_avatar.glb")
app_copy = os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.glb")
for p in (src, exp, app_copy):
    os.makedirs(os.path.dirname(p), exist_ok=True)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=src, compress=True)

bpy.ops.object.select_all(action="DESELECT")
avatar.select_set(True)
arm.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=exp,
    export_format="GLB",
    use_selection=True,
    export_yup=True,
    export_apply=True,
    export_texcoords=False,
    export_normals=True,
    export_materials="EXPORT",
    export_skins=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_range=False,
    export_anim_single_armature=True,
    export_reset_pose_bones=True,
)
shutil.copyfile(exp, app_copy)
print("EXPORTED", exp, os.path.getsize(exp))

# Clip manifest read by the app (which clips exist, their length, and review status).
import json  # noqa: E402

manifest = {
    "asset": "models/trainer_avatar.glb",
    "generator": "tools/blender/build_trainer.py",
    "fps": ta.FPS,
    "clips": [
        {"name": name, "durationSeconds": round(duration, 3), "reviewStatus": "draft_pending_coach_review"}
        for name, duration, _ in ta.clip_specs()
    ],
}
with open(os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.clips.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")

if "--previews" in sys.argv:
    import preview as pv

    prev_dir = os.path.join(ROOT, "assets/blender/previews")
    os.makedirs(prev_dir, exist_ok=True)
    cam = pv.setup_scene(resolution=(360, 520), samples=12)
    shots = [
        ("idle_neutral", 1, 0), ("squat_down", 49, 0), ("squat_down", 49, 90),
        ("boxing_stance", 1, 0), ("boxing_stance", 1, 90), ("boxing_jab", 13, 0), ("boxing_jab", 13, 90),
        ("boxing_cross", 15, 0), ("boxing_guard_return", 21, 0), ("footwork_forward", 15, 90),
    ]
    for name, frame, yaw in shots:
        arm.animation_data.action = bpy.data.actions[name]
        scene.frame_set(frame)
        pv.aim_camera(cam, yaw)
        pv.render_to(os.path.join(prev_dir, f"{name}_f{frame}_y{yaw}.png"))
    arm.animation_data.action = None
