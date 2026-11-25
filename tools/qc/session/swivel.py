import bpy, sys, math
glb, c, a, b = sys.argv[-4], sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE"); arm.animation_data.action = bpy.data.actions[c]
pb = {x.name.split(":")[-1]: x for x in arm.pose.bones}
from mathutils import Vector
out = []
for f in range(a, b + 1):
    bpy.context.scene.frame_set(f)
    row = []
    for s in ("Left", "Right"):
        S, E, W = (arm.matrix_world @ pb[s + n].head for n in ("Arm", "ForeArm", "Hand"))
        ax = (W - S).normalized()
        e = (E - S) - ax * (E - S).dot(ax)
        ref = Vector((0, 0, 1)) - ax * ax.z
        ang = math.degrees(math.atan2(ref.cross(e).dot(ax), ref.dot(e)))
        row.append("%6.1f" % ang)
    out.append("%d:%s" % (f, "/".join(row)))
print(" ".join(out))
