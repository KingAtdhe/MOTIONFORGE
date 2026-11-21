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
- Added 2026-11-21: warmup_march, hip_hinge_down, hip_hinge_up, boxing_lead_hook, boxing_slip, footwork_lateral,
  reverse_lunge, calf_raise, step_jack, glute_bridge, plank_hold (all authored in tools/blender/authored_clips.py)
- Added later 2026-11-21: 29 more clips (see coach_*.clips.json) and prop bones dumbbell_L/R, kettlebell, band, bench
  (tools/blender/coach_props.py)

Do not create all animations before the rig and export pipeline are tested. First create one avatar and one simple animation, export to GLB, and verify on a real Android device.

## Status (2026-11-18, Phase 2)

Built by `tools/blender/build_trainer.py` (Blender 5.3, run headless). Rebuild with
`python tools/blender/build_trainer.py --previews` using Blender's Python / the `bpy` module.

- Avatar v1: stylised training-mannequin look (clean, faceless head; short-sleeve shirt, shorts,
  trainers). ~5.5k vertices / 10.5k triangles (v2: athletic proportions, sculpted head with separate hair shell, closed hands), 6 materials, no textures, 21 bones, ≤4 influences. **Superseded 19 Nov 2026 by the coach build (`build_coach.py`): ~35k tris, 25 bones (adds `fingers_L/R`, `fingertips_L/R`), cel-shaded vertex colours, unlit materials.**
- Rest pose: A-pose. Units: metres. 30 fps. Root motion: none (hips bone carries translation).
- Clips exported (all **draft, pending coach review**): idle_neutral, squat_down, squat_up,
  boxing_stance, boxing_jab, boxing_cross, boxing_guard_return, footwork_forward, footwork_backward.
- Not yet made: pushup_down, pushup_up (prone pose needs separate work), hip hinge (no clip planned
  in the manifest yet).
- Known draft limitations: hands are simplified mittens; footwork clips allow some foot sliding;
  feet do not plant with IK.
- glTF-Validator: 0 errors, 1 warning (NODE_SKINNED_MESH_NON_ROOT, standard for Blender exports,
  harmless because the mesh has no parent transform).
