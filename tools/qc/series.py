import sys, bpy, numpy as np
glb, clip, bone = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
act = bpy.data.actions[clip]; arm.animation_data.action = act
try: arm.animation_data.action_slot = act.slots[0]
except Exception: pass
pb = next(b for b in arm.pose.bones if b.name.endswith(bone))
a, b = int(act.frame_range[0]), int(act.frame_range[1]); P = []
for f in range(a, b + 1): sc.frame_set(f); P.append(np.array(arm.matrix_world @ pb.head))
P = np.array(P); v = np.linalg.norm(np.diff(P, axis=0), axis=1) * 100
print("speed cm/frame:", " ".join(f"{x:.1f}" for x in v))
k = np.linalg.norm(P[1:-1] - (P[:-2] + P[2:]) / 2, axis=1) * 100
print("kink:", " ".join(f"{x:.1f}" for x in k))
print("first", P[0].round(3), "last", P[-1].round(3))
