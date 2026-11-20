"""Read-only inspection of an imported rigged GLB: normals, duplicates, manifoldness, transforms, materials, UVs,
skin weights. Prints a report; changes nothing on disk."""
import bpy, bmesh, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
print("== FILE", path)
for o in bpy.data.objects:
    print(f"object {o.name!r} type {o.type} parent {o.parent.name if o.parent else None} loc {tuple(round(v,4) for v in o.location)} "
          f"rot {tuple(round(math.degrees(v),2) for v in o.rotation_euler)} scale {tuple(round(v,4) for v in o.scale)}")
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    me = o.data
    print(f"\n== MESH {o.name}: verts {len(me.vertices)} faces {len(me.polygons)} tris {sum(len(p.vertices)-2 for p in me.polygons)}")
    dims = o.dimensions; print("dimensions (m, world)", tuple(round(v,3) for v in o.matrix_world.to_3x3() @ Vector(dims)))
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    # winding consistency: an interior edge shared by 2 faces must be traversed in opposite directions
    bad_wind = 0
    for e in bm.edges:
        if len(e.link_faces) == 2:
            f1, f2 = e.link_faces
            def dirn(f):
                vs = [v for v in f.verts]
                i = vs.index(e.verts[0]); return vs[(i + 1) % len(vs)] == e.verts[1]
            if dirn(f1) == dirn(f2): bad_wind += 1
    nm = [e for e in bm.edges if not e.is_manifold]
    boundary = [e for e in bm.edges if e.is_boundary]
    multi = [e for e in bm.edges if len(e.link_faces) > 2]
    loose_v = [v for v in bm.verts if not v.link_faces]
    zero_f = [f for f in bm.faces if f.calc_area() < 1e-10]
    # exact duplicate verts (positions within 1e-6 m)
    from collections import defaultdict
    grid = defaultdict(list)
    for v in bm.verts: grid[tuple(round(c, 6) for c in v.co)].append(v.index)
    dup_groups = [g for g in grid.values() if len(g) > 1]
    # duplicate faces (same vertex set)
    fset = defaultdict(int)
    for f in bm.faces: fset[tuple(sorted(v.index for v in f.verts))] += 1
    dup_faces = sum(c - 1 for c in fset.values() if c > 1)
    # outward check: per connected shell, signed volume sign (closed shells only meaningful)
    shells = []; seen = set()
    for f in bm.faces:
        if f.index in seen: continue
        stack = [f]; comp = []
        while stack:
            g = stack.pop()
            if g.index in seen: continue
            seen.add(g.index); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: stack.append(h)
        shells.append(comp)
    neg = 0; vols = []
    for comp in shells:
        vol = 0.0
        for f in comp:
            vs = [v.co for v in f.verts]
            for i in range(1, len(vs) - 1):
                vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
        vols.append((len(comp), vol))
        if vol < 0: neg += 1
    print(f"winding conflicts {bad_wind} | non-manifold edges {len(nm)} (boundary {len(boundary)}, >2 faces {len(multi)}) | loose verts {len(loose_v)} | zero-area faces {len(zero_f)}")
    print(f"exact duplicate vertex positions: {len(dup_groups)} groups ({sum(len(g) for g in dup_groups)} verts) | duplicate faces {dup_faces}")
    print(f"connected shells {len(shells)}; shells with inward (negative) volume {neg}; biggest shells {sorted(vols, key=lambda x: -x[0])[:6]}")
    # normals vs. outward direction for the main shell: fraction of faces whose normal points toward the body centre
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    # custom split normals present?
    print("has custom split normals", me.has_custom_normals)
    # UVs / materials
    print("uv layers", [u.name for u in me.uv_layers], "| materials", [m.name if m else None for m in me.materials])
    if me.uv_layers:
        uv = me.uv_layers.active.data
        out = sum(1 for l in uv if not (-0.001 <= l.uv.x <= 1.001 and -0.001 <= l.uv.y <= 1.001))
        print(f"uv loops outside 0..1: {out} of {len(uv)}")
    for m in me.materials:
        if not m or not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                link = [l.to_socket.name for l in n.outputs[0].links]
                print(f"  texture {n.image.name} {n.image.size[0]}x{n.image.size[1]} colorspace {n.image.colorspace_settings.name} -> {link}")
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            for k in ("Metallic", "Roughness", "Alpha"):
                s = bsdf.inputs[k]; print(f"  {k}: linked {s.is_linked} value {round(s.default_value,3) if not s.is_linked else '-'}")
        print("  blend", m.blend_method if hasattr(m, "blend_method") else "", "backface culling", m.use_backface_culling)
    # skin weights
    arm = o.find_armature()
    if arm:
        names = {g.index: g.name for g in o.vertex_groups}
        bones = {b.name for b in arm.data.bones}
        unweighted = 0; over4 = 0; badsum = 0
        for v in me.vertices:
            ws = [g.weight for g in v.groups if g.weight > 1e-6 and names.get(g.group) in bones]
            if not ws: unweighted += 1
            if len(ws) > 4: over4 += 1
            if ws and abs(sum(ws) - 1) > 0.02: badsum += 1
        print(f"skin: armature {arm.name} bones {len(bones)} | unweighted verts {unweighted} | >4 influences {over4} | weight sum off by >2% {badsum}")
    bm.free()
