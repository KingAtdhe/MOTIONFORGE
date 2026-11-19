import sys, os, bpy, numpy as np
src, dst = sys.argv[1], sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_anim.bvh(filepath=src, global_scale=0.056444, frame_start=1, use_fps_scale=False, rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
act = arm.animation_data.action
a, b = [int(x) for x in act.frame_range]
names = [pb.name for pb in arm.pose.bones]
sc = bpy.context.scene
frames = list(range(a, b + 1, 4))           # 120 fps -> 30 fps
P = np.zeros((len(frames), len(names), 3), np.float32)
for i, f in enumerate(frames):
    sc.frame_set(f)
    for j, pb in enumerate(arm.pose.bones):
        P[i, j] = arm.matrix_world @ pb.head
T = np.array([arm.matrix_world @ pb.tail for pb in arm.pose.bones])
np.savez_compressed(dst, P=P, names=np.array(names), parents=np.array([pb.parent.name if pb.parent else "" for pb in arm.pose.bones]))
print(os.path.basename(src), P.shape, "height", round(float(P[0, :, 2].max() - P[0, :, 2].min()), 2))
