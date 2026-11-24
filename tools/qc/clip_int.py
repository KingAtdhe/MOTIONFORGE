"""Hand / dumbbell passing through the legs or torso: distance of hand bones and props to body segments (capsules)."""
import sys, bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=sys.argv[-1])
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); B = arm.pose.bones
g = lambda n: next(b for b in B if b.name.endswith(n))
seg = {"thighL": ("LeftUpLeg", "LeftLeg", 0.085), "thighR": ("RightUpLeg", "RightLeg", 0.085), "shinL": ("LeftLeg", "LeftFoot", 0.06),
       "shinR": ("RightLeg", "RightFoot", 0.06), "torso": ("Hips", "Neck", 0.12), "head": ("Head", "HeadTop_End", 0.09)}
pts = {"handL": "LeftHand", "handR": "RightHand"}
for p in ("dumbbell_L", "dumbbell_R", "kettlebell"):
    if any(b.name == p for b in B): pts[p] = p
def dseg(p, a, b):
    v = b - a; t = np.clip(np.dot(p - a, v) / np.dot(v, v), 0, 1); return np.linalg.norm(p - (a + t * v))
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    worst = []
    for f in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1, 2):
        sc.frame_set(f)
        S = {k: (np.array(arm.matrix_world @ g(a).head), np.array(arm.matrix_world @ g(b).head), r) for k, (a, b, r) in seg.items()}
        for pk, pn in pts.items():
            pb = g(pn); vis = pb.scale.length > 0.3 if pk.startswith(("dumb", "kett")) else True
            if not vis: continue
            p = np.array(arm.matrix_world @ (pb.head if pk.startswith("hand") else (pb.head + pb.tail) / 2))
            for sk, (a, b, r) in S.items():
                if pk.startswith("hand") and sk == "head": continue
                pen = r + (0.03 if pk.startswith("hand") else 0.05) - dseg(p, a, b)
                if pen > 0.03: worst.append((round(pen * 100, 1), pk, sk, f))
    if worst: print(act.name, sorted(worst, reverse=True)[:3])
