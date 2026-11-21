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

## Video-tracked takes (vid_*.npz)

Tracked from free stock videos with MediaPipe Pose Landmarker (heavy) on a workstation, then converted to the same
joint format: `tools/mocap/video_pose.py` (landmarks) → `tools/mocap/landmarks_to_joints.py` (Z-up joints, 30 fps,
smoothing, feet on the floor, optional slow-down / reverse). The videos themselves are not stored in the repo and no
video frames ship in the app; only the joint positions below.

| file | source video (licence) | conversion | used for |
|---|---|---|---|
| vid_march.npz | Pexels 6326808, man doing high-knee march, front view (Pexels licence, free use) | full clip, sigma 1.6 | warmup_march (f94–275, two cycles, looped) |
| vid_squat.npz | Mixkit 52116, woman squatting in a gym (Mixkit Stock Video Free License) | src f64–110, 0.6x speed | squat_down (f6–50), squat_up (f50–88) |
| vid_hinge_down.npz | Mixkit 52120, woman stretching on the street (Mixkit Stock Video Free License) | src f46–59 (flat-back start of the forward bend only), 0.3x | hip_hinge_down |
| vid_hinge_up.npz | same | same frames reversed, 0.34x | hip_hinge_up |
| vid_pushup_down.npz | Pexels 4742661, man doing push-ups in a gym, side view (Pexels licence, free use) | src f362–387, 0.7x, legs straightened (`--straight-legs`) | pushup_down |
| vid_pushup_up.npz | same | src f386–442, 1.6x, legs straightened | pushup_up |

Tracked but not used: Pexels 4806552 shadowboxing (legs out of frame, punches toward the camera track poorly — CMU
13_18 stays for the boxing clips), Pexels 8165998 standing (hands in pockets), Mixkit 52117 (figure too small),
Mixkit 11766 push-ups (filmed head-on, legs hidden — the push-up stays procedural). Mixkit 40967 (sparring) and
608 (runner filmed from behind) were not tracked: out of the lesson scope / unusable angle.

Second batch (also tracked, not used): Pexels 7187515 (side-view silhouette shadowboxing — tracks well, but from a
single side camera the near and far arm get confused, so punches came out twisted; CMU 13_18 is studio mocap and
stays), Pexels 6296168, 7187405, 7187538 (mostly guard / legs out of frame), Pexels 4804794, 6388436, 8858126, 4812839
push-ups (elbow bend and body height not recoverable from the camera angle, or a one-leg yoga variant — the
procedural push-up with planted hands stays). CMU 14_01–03 were checked for footwork: they are free-form in-and-out
boxing with ducks and lunges, not a beginner step-drag drill, so footwork stays hand-keyed.

Third batch: Pexels 4742661 used for the push-up (hands pinned to the floor in the build by `plant_hands`). Not used:
Pixabay 13134 (good side-view push-ups, but on handles), Pexels 4804817 (push-up bars), 6893310 (filmed from the front-
side, legs hidden), and three footwork clips (16908132, 9943379, 7187519) that only show the feet and shins, so there is
no body to track. Footwork and guard return stay hand-keyed.

## More CMU takes (2026-11-20)

| file | CMU take | used for |
|---|---|---|
| 15_13_steps.npz | subject 15 — boxing, frames 70–145, mirrored left↔right (the performer stands southpaw) | footwork_forward (f5–48: lead foot steps in, back out) |
| 15_13_steps_back.npz | same, frames 20–48 then 6–20 | footwork_backward (starts stepped in, retreats first) |

Checked and not used: 22_14 / 23_14 / 13_30 / 14_14 squats (all go to full depth, sitting on the heels — the beginner
squat stays from video), 14_06 (the "stretch" there is an overhead side bend, not a hip hinge), 14_20 / 13_31 "bend
over" (toe touches), 20_06 soldiers march (walks forward; the warm-up is on the spot), 17_10 / 79_08 / 80_10 / 13_17
(big lunging steps or standing still). CMU has no push-up.

## Status (2026-11-21)
The shipped coach clips are no longer retargeted from these takes. They are authored from biomechanical rules in
`tools/blender/authored_clips.py`. The takes are kept for reference and can still be built with `MF_LEGACY_MOCAP=1`.
