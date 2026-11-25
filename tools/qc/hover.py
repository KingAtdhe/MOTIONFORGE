"""Hands that should rest on the floor but hover: per clip, frames where a hand's lowest skin point is 0.5-4 cm above
the floor (a hand on the floor is at ~0; a lifted hand is far higher). Usage: hover.py <coach.glb> clip,clip"""
import bpy, sys, numpy as np
glb, clips = sys.argv[-2], sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and "prop" not in o.name)
gi = {g.index: g.name for g in mesh.vertex_groups}
H = {s: np.array([v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if (s + "Hand") in gi[g.group]) > 0.6]) for s in ("Left", "Right")}
co = np.empty(len(mesh.data.vertices) * 3, np.float32)
for clip in clips:
    act = bpy.data.actions[clip]; arm.animation_data.action = act
    a, b = [int(x) for x in act.frame_range]
    bad = []
    for f in range(a, b + 1, 2):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m2 = ev.to_mesh()
        m2.vertices.foreach_get("co", co); ev.to_mesh_clear(); c = co.reshape(-1, 3)
        for s in H:
            z = float(c[H[s], 2].min()) * 100
            if 0.5 < z < 4.0:
                bad.append((f, s[0], round(z, 1)))
    print("HOVER", clip, len(bad), bad[:6])
