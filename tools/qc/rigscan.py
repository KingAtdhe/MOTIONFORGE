"""Rig-level scan of every authored clip (no build): runs build_all with Rig.write replaced by a probe that solves each
frame and reports, per clip, the worst jerk (m/s3 at 30 fps) of hands / elbows / feet / knees / hips / head and the
closest any arm or leg gets to full stretch (1.0 = locked straight). Usage (repo root):
  ../bpyenv/bin/python tools/qc/rigscan.py -- coach_f [out.json]"""
import bpy, sys, json, numpy as np
sys.path.insert(0, "tools/blender")
a = sys.argv[sys.argv.index("--") + 1:]
coach = a[0]
out = a[1] if len(a) > 1 else f"/tmp/rigscan_{coach}.json"
bpy.ops.wm.open_mainfile(filepath=f"assets/blender/source/{coach}.blend")
import authored_clips as ac
arm = bpy.data.objects["trainer_rig"]
BONES = ("hand_L", "hand_R", "forearm_L", "forearm_R", "foot_L", "foot_R", "shin_L", "shin_R", "hips", "head")
res = {}


def probe(self, name, specs):
    specs = ac._with_life(name, specs)
    P = {b: [] for b in BONES}
    stretch = 0.0
    for sp in specs[::ac.OVERSAMPLE]:
        M = self.solve(sp)
        for b in BONES:
            P[b].append(np.array(M[b].translation))
        for s in "LR":
            S = M[f"upper_arm_{s}"].translation; W = M[f"hand_{s}"].translation
            stretch = max(stretch, (W - S).length / (self.a1[s] + self.a2[s]))
            Hp = M[f"thigh_{s}"].translation; A = M[f"foot_{s}"].translation
            stretch = max(stretch, (A - Hp).length / (self.l1[s] + self.l2[s]))
    top = []
    for b, L in P.items():
        if len(L) < 5:
            continue
        J = np.linalg.norm(np.diff(np.array(L), 3, axis=0), axis=1) * 27000
        top.append((int(J.max()), b, int(J.argmax())))
    top.sort(reverse=True)
    res[name] = {"jerk": top[0][0], "at": top[0][1:], "second": top[1][:2] if len(top) > 1 else None, "stretch": round(stretch, 4)}
    print("SCAN", name, res[name], flush=True)


ac.Rig.write = probe
ac.build_all(arm, 1.70 if coach == "coach_f" else 1.85, coach)
json.dump(res, open(out, "w"), indent=1)
