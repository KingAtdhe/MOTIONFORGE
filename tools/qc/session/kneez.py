import bpy, sys
glb, clip, bones = sys.argv[-3], sys.argv[-2], sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); act = bpy.data.actions[clip]; arm.animation_data.action = act
pb = {x.name.split(":")[-1]: x for x in arm.pose.bones}
a, b = [int(x) for x in act.frame_range]; out = []
for f in range(a, b + 1, 8):
    bpy.context.scene.frame_set(f)
    out.append(f"{f}:" + "/".join("%.0f" % ((arm.matrix_world @ pb[n].head).z * 100) for n in bones))
print("K", clip, " ".join(out))
