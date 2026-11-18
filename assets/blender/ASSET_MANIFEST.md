# Blender Asset Manifest

Keep Blender source files in this folder. Export runtime GLB files to `assets/blender/exports/`.

Initial required files:
- `trainer_avatar.blend`
- `trainer_avatar.glb`
- `training_studio.blend`
- `training_studio.glb`

Required animation clip names:
- idle_neutral
- squat_down
- squat_up
- pushup_down
- pushup_up
- boxing_stance
- boxing_jab
- boxing_cross
- boxing_guard_return
- footwork_forward
- footwork_backward

Do not create all animations before the rig and export pipeline are tested. First create one avatar and one simple animation, export to GLB, and verify on a real Android device.
