# Session QC helpers

Shell scripts and small Blender-Python probes used in the animation QC passes (Nov 2026). Run from the repo root;
they expect the Blender Python at `../bpyenv` (next to the repo):

    python3 -m venv ../bpyenv && ../bpyenv/bin/pip install bpy==5.3.0 numpy pillow

- `buildboth.sh` — rebuild both coaches (`--app` copies GLBs + clips.json into the app), ~10 min, logs in /tmp.
- `scan.sh` — rig-level jerk/stretch per clip (`tools/qc/rigscan.py`), writes /tmp/rigscan_coach_{f,m}.json.
- `qcall.sh` — mesh QC on the exported GLBs (audit2, natural, clip_int, jerk); then `python3 tools/qc/session/rank.py 10`.
- Probes (`../bpyenv/bin/python tools/qc/session/X.py -- <glb> <clip> ...`): `handz` (hand height/xy), `armlen`
  (arm extension), `curve` (cat-cow back curve), `heights`, `kneez`, `toez`, `swivel`; `harn7` evaluates authored clips
  on the rig in `assets/blender/source/coach_X.blend`.
- `mont3.py` / `montsel.py` — contact-sheet pages from `tools/qc/sheets.py` output for a visual pass.
