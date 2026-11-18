# Asset origin and rights

| Asset | Origin | Rights |
|---|---|---|
| `source/trainer_avatar.blend`, `exports/trainer_avatar.glb` (+ app copy) | Generated from scratch by `tools/blender/build_trainer.py` (body from a hand-authored joint graph via Blender's Skin + Subdivision modifiers; head sculpted procedurally; own armature and keyframed poses). No base mesh, template human (e.g. MakeHuman), scan, purchased asset or real-person likeness is used. | Owned by the MOTIONFORGE project. |
| `previews/*.png` | Cycles renders of the above, produced by the same script (`--previews`). | Same. |
| Phase 0 test figure (`tools/generate_spike_glb.py`) | Generated boxes. Not shipped in the app any more. | Same. |

Fonts, textures and HDRIs: none are used.

All animation clips are **draft** and must be reviewed by a qualified fitness / boxing coach before
public release (see `docs/MOVEMENT_ANALYSIS_AND_SAFETY.md` §8 and `docs/BLENDER_ASSET_SPEC.md`).
