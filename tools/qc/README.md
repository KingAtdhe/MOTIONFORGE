# Clip QC (glitch audit)

Run with the Blender Python (`bpyenv/bin/python`), from the repo root.

- `audit2.py -- <coach.glb> <out.json> "$(cat tools/qc/joins.json)"` — per clip: worst single-frame kink of any major
  joint, biggest per-frame bone rotation, loop seam, lowest skin vertex (floor), knees bending backwards, hands in the
  torso, and the joins the app plays (down→up, footwork pairs).
- `rotj.py <coach.glb>` — the four biggest per-frame bone rotations per clip (finds snaps and twists).
- `lowest.py <coach.glb> clip,clip` — which body parts sink below the floor, and how far.
- `series.py <coach.glb> <clip> <bone>` — per-frame speed and kink of one joint.
- `loopj.py <coach.glb> clip,clip` — where a loop does not close.
- `sheets.py -- <coach.glb> <dir> <exercises.json> [ids]` then `montage2.py <dir> <out.jpg> id,id` — 8 frames of every
  lesson as the app plays it, 3/4 and side, for a visual pass.
- `close.py -- <coach.glb> <dir> clip:f1,f2:yaw[:dist] ...` + `strip.py` — close-ups of chosen frames.
- `natural.py <coach.glb>` — naturalness per clip: % frames with nothing moving (frozen), how mirror-identical the two
  hands / feet move, head path, jerk spikes.
- `jerk.py <coach.glb> clip,clip` — the four biggest jerk peaks (m/s³) per clip, with joint and frame.
- `clip_int.py <coach.glb>` — hands, dumbbells and the kettlebell passing into the thighs, shins or torso.
