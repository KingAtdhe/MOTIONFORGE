import bpy, sys, numpy as np
glb, clip = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and "prop" not in o.name)
gi = {g.index: g.name for g in mesh.vertex_groups}
H = {s: np.array([v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if (s + "Hand") in gi[g.group]) > 0.6]) for s in ("Left", "Right")}
act = bpy.data.actions[clip]; arm.animation_data.action = act
a, b = [int(x) for x in act.frame_range]
co = np.empty(len(mesh.data.vertices) * 3, np.float32)
for f in range(a, b + 1, 6):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m2 = ev.to_mesh()
    m2.vertices.foreach_get("co", co); ev.to_mesh_clear(); c = co.reshape(-1, 3)
    print("F", f, " ".join(f"{s[0]} z{c[H[s],2].min()*100:5.1f} xy({c[H[s],0].mean()*100:5.1f},{c[H[s],1].mean()*100:5.1f})" for s in H))
