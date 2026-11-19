# Motion capture source

Joint positions (30 fps, metres, Blender Z-up) extracted from the CMU Graphics Lab Motion Capture Database,
BVH conversion by Bruce Hahne (cgspeed), copy at github.com/sfd158/cmu-mocap. CMU and the converter place no
restrictions on use (see CMU_READMEFIRST.txt). Extracted with `tools/blender/mocap_extract.py`.

| file | CMU take | used for |
|---|---|---|
| 13_18.npz | subject 13 — boxing | boxing_stance (f113–142), boxing_jab (f88–118), boxing_cross (f20–50) |
| 13_29.npz | subject 13 — squats | not used (too deep for the lesson) |
| 22_14.npz | subject 22 — alternating squats | not used yet |
| 111_28.npz (f10–100) | standing still | idle_neutral |
