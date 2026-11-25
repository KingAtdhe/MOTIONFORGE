import bpy, sys
argv = sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
act = bpy.data.actions.get(argv[1]) or [a for a in bpy.data.actions if a.name.startswith(argv[1])][0]
arm.animation_data.action = act
for f in [int(x) for x in argv[2].split(",")]:
    bpy.context.scene.frame_set(f)
    out = []
    for s in ("Left", "Right"):
        pb = {b.name.split(":")[-1]: b for b in arm.pose.bones}
        u, fa, h = (arm.matrix_world @ pb[s + n].head for n in ("Arm", "ForeArm", "Hand"))
        L = (fa - u).length + (h - fa).length
        out.append(f"{s[0]} ext {(h-u).length/L:.4f} elbowbend {180-(fa-u).angle(h-fa)*57.3:.1f}")
    print("F", f, *out)
