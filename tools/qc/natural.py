"""Naturalness metrics per clip: frozen (no joint moves >0.5 mm/frame), mirror symmetry of the two hands / two feet
(mean mirrored-position difference, cm, only when they move), peak jerk vs median (spikiness)."""
import sys, bpy, numpy as np
glb = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; sc.render.fps = 30; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
B = {k: next(b for b in arm.pose.bones if b.name.endswith(k)) for k in ("Hips", "Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot", "LeftForeArm", "RightForeArm", "Spine2")}
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = act.frame_range; n = int((b - a) * 30 / 24) + 1
    P = {k: [] for k in B}
    for i in range(n):
        f = a + i * 24 / 30; sc.frame_set(int(f), subframe=f - int(f))
        for k, pb in B.items(): P[k].append(np.array(arm.matrix_world @ pb.head))
    P = {k: np.array(v) for k, v in P.items()}
    sp = np.max([np.linalg.norm(np.diff(P[k], axis=0), axis=1) for k in P], axis=0)
    frozen = (sp < 0.0005).mean() * 100
    def mir(l, r):
        L, R = P[l].copy(), P[r].copy(); R[:, 0] *= -1
        mv = np.linalg.norm(np.diff(P[l], axis=0), axis=1).sum() + np.linalg.norm(np.diff(P[r], axis=0), axis=1).sum()
        if mv < 0.10: return None
        d = (L - L.mean(0)) - (R - R.mean(0))
        return np.linalg.norm(d, axis=1).mean() * 100
    hs, fs = mir("LeftHand", "RightHand"), mir("LeftFoot", "RightFoot")
    j = np.linalg.norm(np.diff(P["Hips"], 3, axis=0), axis=1)
    jh = max(np.linalg.norm(np.diff(P[k], 3, axis=0), axis=1).max() / (np.median(np.linalg.norm(np.diff(P[k], 3, axis=0), axis=1)) + 1e-5) for k in ("LeftHand", "RightHand", "Head"))
    hd = np.linalg.norm(np.diff(P["Head"], axis=0), axis=1).sum() * 100
    print(f"{act.name:24s} {n/30:4.1f}s frozen {frozen:4.0f}% handsMirror {'-' if hs is None else f'{hs:4.1f}'} feetMirror {'-' if fs is None else f'{fs:4.1f}'} headPath {hd:5.0f}cm jerkSpike {jh:5.0f}")
