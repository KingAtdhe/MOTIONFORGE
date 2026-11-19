# Coach from the owner's sheet (female coach v5)

Builds the in-app female coach from `assets/blender/references/workout_coach_owner_sheet.png`
(the owner's painted Workout Coach sheet): body shape from the front + side outlines, the painting
projected onto it, then rig, hands and clips in Blender. No base mesh or bought model.

Run from a scratch work directory (`WORK`), Blender Python = `pip install bpy==5.3.0`, plus numpy, scipy,
scikit-image and Pillow for the system Python:

```
cd $WORK
python  $REPO/tools/coach_from_sheet/masks.py          # silhouettes + hair masks -> mask_*.npy
python  $REPO/tools/coach_from_sheet/hull.py           # cross-section volume -> hull.npz, parts.npy
bpy     $REPO/tools/coach_from_sheet/blend_hull.py     # mesh, loose crumbs removed, ~24k tris -> hull.blend
bpy     $REPO/tools/coach_from_sheet/bake.py hull.blend hull_uv.blend 2048   # UVs + texel position/normal
python  $REPO/tools/coach_from_sheet/project.py        # painting -> coach_albedo.png (logo removed)
bpy     $REPO/tools/blender/build_coach_sheet.py $WORK # rig, fist hands, A-pose rest, clips, GLB + manifest
bpy     $REPO/tools/coach_from_sheet/preview_unlit.py $REPO/assets/blender/source/trainer_avatar.blend $REPO/assets/blender/previews
```
Checks: `ortho.py` + `overlay.py` (outline overlap with the sheet), `clay.py`, `texview.py`, `animview.py`.

Limits: the sheet's figures are ~420 px tall, so the painted detail is soft up close; the sides of the head and
torso are blended between views; hands are sculpted (painted hands cannot make fists).
