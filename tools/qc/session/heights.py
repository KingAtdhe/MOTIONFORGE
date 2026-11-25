import bpy, sys
glb, clip, bones = sys.argv[-3], sys.argv[-2], sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); act = bpy.data.actions[clip]; arm.animation_data.action = act
pb = {x.name.split(":")[-1]: x for x in arm.pose.bones}
a, b = [int(x) for x in act.frame_range]
rng = {n: [9, -9] for n in bones}
for f in range(a, b + 1, 2):
    bpy.context.scene.frame_set(f)
    for n in bones:
        z = (arm.matrix_world @ pb[n].head).z
        rng[n][0] = min(rng[n][0], z); rng[n][1] = max(rng[n][1], z)
print("H", clip, " ".join(f"{n}:{lo*100:.0f}->{hi*100:.0f}cm" for n, (lo, hi) in rng.items()))
