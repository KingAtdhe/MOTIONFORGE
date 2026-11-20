"""Owner's Tripo FBX (mesh + Mixamo-named skeleton + PBR maps) -> rigged GLB for build_coach_mesh.py --rigged.

Only repairs what the inspection (tools/blender/inspect_mesh.py, inspect_welded.py, docs/MESH_INSPECTION.md) found:
whole sub-meshes whose faces all point into the body (e.g. eyelash strips) are flipped outward. Shape, proportions,
UVs, weights and textures are untouched.
usage: python import_tripo_fbx.py IN.fbx OUT.glb   (also writes OUT_static.glb)"""
import sys
import bpy, bmesh
from mathutils import Vector

src, dst = sys.argv[1], sys.argv[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
arm = mesh.find_armature()
for o in list(bpy.data.objects):
    if o not in (mesh, arm):
        bpy.data.objects.remove(o)
bones = [(arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local) for b in arm.data.bones]


def axis_point(p):
    best = None
    for h, t in bones:
        d = t - h
        u = max(0.0, min(1.0, (p - h).dot(d) / max(d.length_squared, 1e-12)))
        q = h + d * u
        if best is None or (p - q).length < best[0]:
            best = ((p - q).length, q)
    return best[1]


bm = bmesh.new(); bm.from_mesh(mesh.data); bm.faces.ensure_lookup_table()
M = mesh.matrix_world
seen, flipped = set(), 0
for f in bm.faces:
    if f.index in seen:
        continue
    st, comp = [f], []
    while st:
        g = st.pop()
        if g.index in seen:
            continue
        seen.add(g.index); comp.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen:
                    st.append(h)
    out = 0
    for g in comp:
        c = M @ g.calc_center_median(); q = axis_point(c)
        n = (M.to_3x3() @ g.normal)
        if (c - q).length > 1e-6 and n.dot((c - q).normalized()) > 0:
            out += 1
    if len(comp) >= 12 and out / len(comp) < 0.10:          # the whole piece faces inward: flip it
        for g in comp:
            g.normal_flip()
        flipped += 1
bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
print("inside-out pieces flipped:", flipped)
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_skins=True, export_animations=False,
                          export_image_format="JPEG", export_yup=True)
print("wrote", dst)
# a plain (unrigged) copy of the same mesh for the build's first stage (it measures and bakes a static mesh)
static = dst.replace(".glb", "_static.glb")
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=static, export_format="GLB", use_selection=True, export_skins=False,
                          export_animations=False, export_image_format="JPEG", export_yup=True)
print("wrote", static)
