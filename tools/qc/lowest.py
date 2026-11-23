import sys, bpy, numpy as np
glb = sys.argv[-2]; clips = sys.argv[-1].split(",")
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("prop_") and o.find_armature() == arm][0]
gi = {g.index: g.name for g in mesh.vertex_groups}
grp = [gi[max(v.groups, key=lambda g: g.weight).group].replace("mixamorig:", "") if v.groups else "-" for v in mesh.data.vertices]
for c in clips:
    act = bpy.data.actions[c]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    a, b = int(act.frame_range[0]), int(act.frame_range[1]); rep = {}
    for f in range(a, b + 1, 4):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); e = mesh.evaluated_get(dg); me = e.to_mesh()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ np.array(mesh.matrix_world)[:3, :3].T + np.array(mesh.matrix_world)[:3, 3]
        e.to_mesh_clear()
        below = co[:, 2] < -0.004
        for g in set(np.array(grp)[below]):
            m = co[np.array(grp) == g, 2].min()
            rep[g] = min(rep.get(g, 0), m)
    print(c, {k: round(v * 100, 1) for k, v in sorted(rep.items(), key=lambda x: x[1])[:6]})
