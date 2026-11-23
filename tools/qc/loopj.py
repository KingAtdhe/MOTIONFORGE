import sys, bpy, numpy as np
glb = sys.argv[-2]; clips = sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for c in clips:
    act = bpy.data.actions[c]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = act.frame_range
    def pos(f):
        sc.frame_set(int(f), subframe=f - int(f)); return {pb.name: np.array(arm.matrix_world @ pb.head) for pb in arm.pose.bones if "Hand" not in pb.name[10:] or pb.name.endswith("Hand")}
    P0, P1, Pm = pos(a), pos(b), pos(b - 1)
    gaps = sorted(((np.linalg.norm(P1[k] - P0[k]) * 100, np.linalg.norm(P1[k] - Pm[k]) * 100, k.replace("mixamorig:", "")) for k in P0), reverse=True)[:4]
    print(c, a, b, [(round(g, 1), round(s, 1), k) for g, s, k in gaps])
