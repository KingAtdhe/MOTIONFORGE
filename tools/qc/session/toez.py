import sys, bpy, numpy as np
glb, c = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
sc = bpy.context.scene; arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("prop_") and o.find_armature() == arm][0]
gi = {g.index: g.name for g in mesh.vertex_groups}
grp = np.array([gi[max(v.groups, key=lambda g: g.weight).group].replace("mixamorig:", "") if v.groups else "-" for v in mesh.data.vertices])
act = bpy.data.actions[c]; arm.animation_data.action = act
a, b = int(act.frame_range[0]), int(act.frame_range[1]); out=[]
for f in range(a, b + 1, int(sys.argv[-3]) if sys.argv[-3].isdigit() else 6):
    sc.frame_set(f); e = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = e.to_mesh()
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3) @ np.array(mesh.matrix_world)[:3, :3].T + np.array(mesh.matrix_world)[:3, 3]; e.to_mesh_clear()
    out.append("%d:%.1f/%.1f/%.1f" % (f, co[grp=="LeftToeBase",2].min()*100, co[grp=="RightToeBase",2].min()*100, co[np.char.find(grp,"Hand")>=0,2].min()*100))
print(" ".join(out))
