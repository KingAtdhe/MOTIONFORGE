import bpy, sys, numpy as np
sys.path.insert(0, "tools/blender")
a = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=f"assets/blender/source/{a[0]}.blend")
import authored_clips as ac, clips_fight2 as cg, clips_fit2 as cf
arm = bpy.data.objects["trainer_rig"]
r = ac.Rig(arm, 1.70 if a[0].endswith("f") else 1.85); st = ac.STYLE[a[0]]
fn = dict(getattr(ac, "CLIPS", ())); fn.update(dict(cg.CLIPS)); fn.update(dict(cf.CLIPS))
specs = (fn.get(a[1]) or getattr(ac, a[1]))(r, st); bone = a[2]
P = []
for sp in specs[::4]:
    M = r.solve(sp); P.append(np.array(M[bone].translation))
P = np.array(P); v = np.linalg.norm(np.diff(P, axis=0), axis=1) * 100
print("SPEED", " ".join(f"{x:.1f}" for x in v[int(a[3]):int(a[4])]))
print("KEYS", list(r.solve(specs[0]).keys())[:40])
