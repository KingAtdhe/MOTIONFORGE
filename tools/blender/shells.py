import bpy, bmesh, sys
from mathutils import Vector
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path)
o = next(o for o in bpy.data.objects if o.type == "MESH"); arm = o.find_armature()
print("BONES", [b.name for b in arm.data.bones])
bones = [(b.name, arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local) for b in arm.data.bones]
def nearest(p):
    best = None
    for n, h, t in bones:
        d = t - h; u = max(0, min(1, (p - h).dot(d) / max(d.length_squared, 1e-12))); q = h + d * u
        if best is None or (p - q).length < best[0]: best = ((p - q).length, n, q)
    return best
bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); bm.faces.ensure_lookup_table()
seen = set()
for f in bm.faces:
    if f.index in seen: continue
    st = [f]; comp = []
    while st:
        g = st.pop()
        if g.index in seen: continue
        seen.add(g.index); comp.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen: st.append(h)
    vol = sum(sum(vs[0].co.dot(vs[i].co.cross(vs[i + 1].co)) / 6 for i in range(1, len(vs) - 1)) for vs in ([*g.verts] for g in comp))
    open_e = sum(1 for g in comp for e in g.edges if e.is_boundary)
    # outward agreement: face normal vs direction away from the nearest bone axis
    agree = 0
    for g in comp:
        c = g.calc_center_median(); _, n, q = nearest(c)
        if (c - q).length > 1e-6 and g.normal.dot((c - q).normalized()) > 0: agree += 1
    c = sum((g.calc_center_median() for g in comp), Vector()) / len(comp)
    print(f"SHELL faces {len(comp):5d} near {nearest(c)[1]:28s} open edges {open_e:4d} volume {vol:+.6f} normals facing out {agree / len(comp):.0%}")
