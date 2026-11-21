"""Biomechanics audit per clip: tempo, knee/hip/elbow angles, torso lean, head pitch, foot slide, floor, COM vs feet, loop seam, velocity spikes."""
import sys, bpy, numpy as np
from mathutils import Vector
if sys.argv[1].endswith(".glb"):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=sys.argv[1])
else:
    bpy.ops.wm.open_mainfile(filepath=sys.argv[1])
only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
sc = bpy.context.scene; sc.render.fps = 30
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if not arm.animation_data: arm.animation_data_create()
print("ARM", arm.name, len(arm.pose.bones), [o.name for o in bpy.data.objects if o.type=="ARMATURE"])
B = arm.pose.bones
if len(sys.argv) > 3: print(sorted(b.name for b in B)); 
def find(*c):
    for n in c:
        for b in B:
            if b.name.lower().endswith(n.lower()): return b.name
    return None
N = dict(hips=find("Hips","hips"), spine=find("Spine","spine"), chest=find("Spine2","chest"), neck=find("Neck","neck"), head=find("Head","head"))
for s, S in (("L","Left"),("R","Right")):
    N["thigh"+s]=find(S+"UpLeg","thigh_"+s); N["shin"+s]=find(S+"Leg","shin_"+s); N["foot"+s]=find(S+"Foot","foot_"+s); N["toe"+s]=find(S+"ToeBase","toe_"+s)
    N["uarm"+s]=find(S+"Arm","upper_arm_"+s); N["farm"+s]=find(S+"ForeArm","forearm_"+s); N["hand"+s]=find(S+"Hand","hand_"+s)
def W(n, tail=False):
    b = B[N[n]]; return arm.matrix_world @ (b.tail if tail else b.head)
def ang(a, b, c):
    u, v = (a - b).normalized(), (c - b).normalized(); return np.degrees(np.arccos(max(-1, min(1, u.dot(v)))))
for act in bpy.data.actions:
    if only and act.name not in only: continue
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = [int(x) for x in act.frame_range]
    R = {k: [] for k in "kneeL kneeR hipL hipR elbL elbR lean head hipz hipx hipy footL footR toeL toeR handL handR kneeLx kneeRx".split()}
    for f in range(a, b + 1):
        sc.frame_set(f)
        for s in "LR":
            R["knee"+s].append(ang(W("thigh"+s), W("shin"+s), W("foot"+s)))
            R["hip"+s].append(ang(W("chest"), W("thigh"+s), W("shin"+s)))
            R["elb"+s].append(ang(W("uarm"+s), W("farm"+s), W("hand"+s)))
            R["foot"+s].append(np.array(W("foot"+s))); R["toe"+s].append(np.array(W("toe"+s) if N["toe"+s] else W("foot"+s, True)))
            R["hand"+s].append(np.array(W("hand"+s)))
            R["knee"+s+"x"].append(W("shin"+s).x - W("foot"+s).x)
        t = W("neck") - W("hips"); R["lean"].append(np.degrees(np.arctan2(np.hypot(t.x, t.y), t.z)))
        h = W("head", True) - W("head"); R["head"].append(np.degrees(np.arctan2(-h.y, h.z)))
        p = W("hips"); R["hipz"].append(p.z); R["hipx"].append(p.x); R["hipy"].append(p.y)
    A = {k: np.array(v) for k, v in R.items()}
    n = b - a + 1
    sl = {}
    for s_ in "LR":
        F = A["foot"+s_]; T = A["toe"+s_]
        planted = T[:, 2] < T[:, 2].min() + 0.012
        d = np.linalg.norm(np.diff(T[:, :2], axis=0), axis=1)
        sl[s_] = (d[planted[1:] & planted[:-1]].sum()*100, F[:,2].min(), F[:,2].max(), T[:,2].min(), T[:,2].max())
    acc = max((np.abs(np.diff(np.linalg.norm(np.diff(A[k], axis=0), axis=1) * 30)) * 30).max() for k in ("handL","handR"))
    hz = np.abs(np.diff(A["hipz"], 2)).max() * 900
    print(f"{act.name:20s} {n/30:4.2f}s knee {A['kneeL'].min():3.0f}-{A['kneeL'].max():3.0f}/{A['kneeR'].min():3.0f}-{A['kneeR'].max():3.0f} hip {A['hipL'].min():3.0f}-{A['hipL'].max():3.0f} elb {A['elbL'].min():3.0f}-{A['elbL'].max():3.0f}/{A['elbR'].min():3.0f}-{A['elbR'].max():3.0f} lean {A['lean'].min():2.0f}-{A['lean'].max():2.0f} head {A['head'].min():3.0f}..{A['head'].max():3.0f} hipsZ {A['hipz'].min():.2f}-{A['hipz'].max():.2f} | slide L{sl['L'][0]:.1f} R{sl['R'][0]:.1f}cm toeZ L{sl['L'][3]:.3f}-{sl['L'][4]:.3f} R{sl['R'][3]:.3f}-{sl['R'][4]:.3f} | handAcc {acc:.0f} hipAcc {hz:.1f}")
