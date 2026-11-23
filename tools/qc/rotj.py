import sys, bpy, math
glb = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); B = arm.pose.bones
for act in sorted(bpy.data.actions, key=lambda x: x.name):
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = int(round(act.frame_range[0])), int(act.frame_range[1])
    prev = None; worst = {}
    for f in range(a, b + 1):
        sc.frame_set(f); cur = {pb.name: pb.matrix_basis.to_quaternion() for pb in B}
        if prev:
            for n, q in cur.items():
                d = math.degrees(prev[n].rotation_difference(q).angle); d = min(d, 360 - d)
                if d > worst.get(n, (0,))[0]: worst[n] = (d, f)
        prev = cur
    top = sorted(((v[0], n.replace("mixamorig:", ""), v[1]) for n, v in worst.items()), reverse=True)[:4]
    print(act.name.ljust(24), " ".join(f"{n}:{d:.0f}@{f}" for d, n, f in top))
