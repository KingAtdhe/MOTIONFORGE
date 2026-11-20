import bpy, bmesh, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
o = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bm = bmesh.new(); bm.from_mesh(o.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)       # weld seam splits (copy in memory only)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
bad = 0; bad_faces = set()
for e in bm.edges:
    if len(e.link_faces) == 2:
        f1, f2 = e.link_faces
        def d(f):
            vs = list(f.verts); i = vs.index(e.verts[0]); return vs[(i + 1) % len(vs)] == e.verts[1]
        if d(f1) == d(f2): bad += 1; bad_faces.update((f1.index, f2.index))
boundary = [e for e in bm.edges if e.is_boundary]; multi = [e for e in bm.edges if len(e.link_faces) > 2]
wire = [e for e in bm.edges if not e.link_faces]
zero = [f for f in bm.faces if f.calc_area() < 1e-10]
# hole loops: group boundary edges into loops
seen = set(); loops = []
for e in boundary:
    if e.index in seen: continue
    stack = [e]; n = 0
    while stack:
        x = stack.pop()
        if x.index in seen: continue
        seen.add(x.index); n += 1
        for v in x.verts:
            for y in v.link_edges:
                if y.is_boundary and y.index not in seen: stack.append(y)
    loops.append(n)
shells = []; s2 = set()
for f in bm.faces:
    if f.index in s2: continue
    st = [f]; comp = []
    while st:
        g = st.pop()
        if g.index in s2: continue
        s2.add(g.index); comp.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in s2: st.append(h)
    shells.append(comp)
info = []
for comp in shells:
    vol = 0.0
    for f in comp:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1): vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    info.append((len(comp), vol))
info.sort(key=lambda x: -x[0])
# outward test on the main shell: ray from face centre along its normal should mostly exit the body (hit count even)
bvh = BVHTree.FromBMesh(bm)
main = shells[max(range(len(shells)), key=lambda i: len(shells[i]))]
import random; random.seed(1)
samp = random.sample(main, min(600, len(main))); inward = 0
for f in samp:
    c = f.calc_center_median(); n = f.normal
    hits = 0; p = c + n * 1e-4
    for _ in range(40):
        loc, nor, idx, dist = bvh.ray_cast(p, n)
        if loc is None: break
        hits += 1; p = loc + n * 1e-4
    if hits % 2 == 1: inward += 1
print(f"WELDED {o.name[:20]}: verts {len(bm.verts)} faces {len(bm.faces)}")
print(f"  winding conflicts {bad} (faces {len(bad_faces)}) | open boundary edges {len(boundary)} in {len(loops)} loops (largest {sorted(loops)[-5:]}) | edges with >2 faces {len(multi)} | wire edges {len(wire)} | zero-area faces {len(zero)}")
print(f"  shells {len(shells)}: {info[:8]}")
print(f"  main shell normals pointing inward (odd ray hits): {inward}/{len(samp)}")
