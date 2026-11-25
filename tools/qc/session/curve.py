import bpy, sys
glb, clip = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); act = bpy.data.actions[clip]; arm.animation_data.action = act
pb = {x.name.split(":")[-1]: x for x in arm.pose.bones}
a, b = [int(x) for x in act.frame_range]
out = []
for f in range(a, b + 1, 10):
    bpy.context.scene.frame_set(f)
    H, S, N = (arm.matrix_world @ pb[n].head for n in ("Hips", "Spine2", "Neck"))
    d = (N - H).normalized(); v = (S - H) - d * (S - H).dot(d)
    out.append(f"{f}:{v.z*100:+.1f}")
print("C", clip, " ".join(out))
