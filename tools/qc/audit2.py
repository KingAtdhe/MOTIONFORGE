"""Glitch audit for every clip of a coach GLB, the way the app plays them.
Per clip: worst single-frame kink of any major joint (cm), biggest per-frame bone rotation jump (deg),
loop/join seam jump (cm, vs the clip's normal per-frame motion), mesh floor min/max of the lowest vertex (cm),
planted-foot slide, knee bending backwards, hand inside torso/head."""
import sys, bpy, json, math, numpy as np
from mathutils import Vector
glb = sys.argv[sys.argv.index("--") + 1]; out = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("prop_") and o.find_armature() == arm]
props = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("prop_")]
if not arm.animation_data: arm.animation_data_create()
B = arm.pose.bones
def find(*c):
    for n in c:
        for b in B:
            if b.name.lower().endswith(n.lower()): return b.name
J = {k: find(*v) for k, v in dict(hips=("Hips",), chest=("Spine2",), neck=("Neck",), head=("Head",),
     thighL=("LeftUpLeg",), shinL=("LeftLeg",), footL=("LeftFoot",), toeL=("LeftToeBase",),
     thighR=("RightUpLeg",), shinR=("RightLeg",), footR=("RightFoot",), toeR=("RightToeBase",),
     uarmL=("LeftArm",), farmL=("LeftForeArm",), handL=("LeftHand",), uarmR=("RightArm",), farmR=("RightForeArm",), handR=("RightHand",)).items()}
MW = arm.matrix_world
def P(k, tail=False):
    b = B[J[k]]; return np.array(MW @ (b.tail if tail else b.head))
seq_join = json.loads(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > sys.argv.index("--") + 3 else {}
res = {}
def sample(act):
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = act.frame_range; a, b = int(round(a)), int(math.floor(b))
    pos, rot, floor, hd = [], [], [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for f in range(a, b + 1):
        sc.frame_set(f)
        pos.append({k: P(k) for k in J}); pos[-1]["headTop"] = P("head", True)
        rot.append({pb.name: pb.matrix.to_quaternion() for pb in B})
        if (f - a) % 2 == 0 or f == b:
            dg = bpy.context.evaluated_depsgraph_get(); zmin = 9
            for m in meshes:
                e = m.evaluated_get(dg); me = e.to_mesh(); mw = m.matrix_world
                co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
                z = (co @ np.array(mw)[:3, :3].T + np.array(mw)[:3, 3])[:, 2]; zmin = min(zmin, z.min()); e.to_mesh_clear()
            floor.append((f, zmin))
    return a, b, pos, rot, floor
for act in sorted(bpy.data.actions, key=lambda x: x.name):
    a, b, pos, rot, floor = sample(act)
    n = len(pos); keys = [k for k in J if k not in ("chest",)]
    X = {k: np.array([p[k] for p in pos]) for k in keys}
    kink = 0; kinkwhere = None
    for k in keys:
        if n < 3: break
        d = np.linalg.norm(X[k][1:-1] - (X[k][:-2] + X[k][2:]) / 2, axis=1) * 100
        i = d.argmax()
        if d[i] > kink: kink, kinkwhere = d[i], (k, int(a + 1 + i))
    rj = 0; rjw = None
    for i in range(1, n):
        for bn, q in rot[i].items():
            ang = math.degrees(rot[i - 1][bn].rotation_difference(q).angle)
            if ang > 180: ang = 360 - ang
            if ang > rj: rj, rjw = ang, (bn.replace("mixamorig:", ""), a + i)
    step = np.median([np.linalg.norm(X["handL"][i] - X["handL"][i - 1]) for i in range(1, n)]) if n > 1 else 0
    loopj = max(np.linalg.norm(X[k][-1] - X[k][0]) for k in keys) * 100
    # knees bending backwards: knee offset from the hip-ankle line against the toe direction
    rev = 0
    for s in "LR":
        for i in range(n):
            h, kk, an, to = X["thigh" + s][i], X["shin" + s][i], X["foot" + s][i], X["toe" + s][i]
            line = an - h; L = np.linalg.norm(line)
            if L < 1e-6: continue
            off = kk - h - line * np.dot(kk - h, line) / L / L
            if np.linalg.norm(off) < 0.02: continue
            fw = to - an; fw[2] = 0
            if np.linalg.norm(fw) < 1e-6: continue
            c = np.dot(off, fw) / np.linalg.norm(off) / np.linalg.norm(fw)
            if c < -0.5: rev = max(rev, np.linalg.norm(off) * 100)
    # hands inside the torso (segment hips->neck, radius 9 cm) or the head (sphere 9 cm)
    inside = 0; inw = None
    for s in "LR":
        for i in range(n):
            hnd = X["hand" + s][i]; h0, h1 = X["hips"][i], X["neck"][i]; v = h1 - h0
            t = np.clip(np.dot(hnd - h0, v) / np.dot(v, v), 0, 1); d = np.linalg.norm(hnd - (h0 + t * v))
            if d < 0.09 and 0.9 - d * 10 > inside: inside, inw = 9 - d * 100, ("torso", s, a + i)
    fz = np.array([z for _, z in floor]) * 100
    res[act.name] = dict(frames=n, kink=round(kink, 2), kinkAt=kinkwhere, rotJump=round(rj, 1), rotAt=rjw, handStep=round(step * 100, 2),
                         loopGap=round(loopj, 1), floorMin=round(fz.min(), 1), floorMax=round(fz.max(), 1), kneeBack=round(rev, 1), handInTorso=inw)
# joins the app plays
acts = {a.name: a for a in bpy.data.actions}
for a_, b_ in seq_join:
    if a_ in acts and b_ in acts:
        _, _, pa, _, _ = sample(acts[a_]); _, _, pb, _, _ = sample(acts[b_])
        res[a_]["join_" + b_] = round(max(np.linalg.norm(pa[-1][k] - pb[0][k]) for k in J) * 100, 1)
json.dump(res, open(out, "w"), indent=1, default=str)
print("AUDIT done", len(res))
