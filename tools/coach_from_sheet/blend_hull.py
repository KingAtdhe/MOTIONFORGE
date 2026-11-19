import sys, numpy as np, bpy, bmesh
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
d = np.load("./hull.npz")
v, f = d["verts"], d["faces"]
me = bpy.data.meshes.new("coach")
me.from_pydata(v.tolist(), [], f[:, ::-1].tolist())
me.update()
ob = bpy.data.objects.new("coach", me)
bpy.context.collection.objects.link(ob)
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
me.remesh_voxel_size = 0.005
bpy.ops.object.voxel_remesh()
bm = bmesh.new(); bm.from_mesh(me)
# drop loose crumbs (stray hair strands): keep connected pieces with > 3% of the vertices
bm.verts.ensure_lookup_table()
seen = set(); groups = []
for v in bm.verts:
    if v.index in seen:
        continue
    stack = [v]; comp = []
    seen.add(v.index)
    while stack:
        a = stack.pop(); comp.append(a)
        for e in a.link_edges:
            b = e.other_vert(a)
            if b.index not in seen:
                seen.add(b.index); stack.append(b)
    groups.append(comp)
big = max(len(g) for g in groups)
dead = [v for g in groups if len(g) < 0.03 * big for v in g]
bmesh.ops.delete(bm, geom=dead, context="VERTS")
print("loose pieces removed", sum(1 for g in groups if len(g) < 0.03 * big))
bm.to_mesh(me); bm.free()
m = ob.modifiers.new("s", "CORRECTIVE_SMOOTH"); m.iterations = 10; m.smooth_type = "LENGTH_WEIGHTED"
bpy.ops.object.modifier_apply(modifier=m.name)
print("tris before", len(me.polygons))
dec = ob.modifiers.new("d", "DECIMATE"); dec.ratio = 24000 / (2 * len(me.polygons))
bpy.ops.object.modifier_apply(modifier=dec.name)
print("tris after", sum(len(p.vertices) - 2 for p in ob.data.polygons))
bpy.ops.object.shade_smooth()
bpy.ops.wm.save_as_mainfile(filepath="./hull.blend")
