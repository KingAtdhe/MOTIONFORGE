import sys, bpy, numpy as np
glb, clips = sys.argv[-2], sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
names = [b.name for b in arm.pose.bones if any(b.name.endswith(k) for k in ("Hips","Head","Hand","Foot","ForeArm","Leg","Spine2","ToeBase"))]
for c in clips:
    act = bpy.data.actions[c]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = act.frame_range; n = int((b - a) * 30 / 24) + 1; P = {k: [] for k in names}
    for i in range(n):
        f = a + i * 24 / 30; sc.frame_set(int(f), subframe=f - int(f))
        for k in names: P[k].append(np.array(arm.matrix_world @ arm.pose.bones[k].head))
    top = []
    for k in names:
        J = np.linalg.norm(np.diff(np.array(P[k]), 3, axis=0), axis=1) * 27000   # m/s^3 at 30 fps
        i = J.argmax(); top.append((J[i], k.replace("mixamorig:", ""), i))
    top.sort(reverse=True)
    print(c, [(round(j), k, i) for j, k, i in top[:4]])
