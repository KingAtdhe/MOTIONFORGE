"""
MOTIONFORGE trainer avatar — body construction (from scratch, no base mesh).

The body is built from a hand-authored joint graph: each vertex carries a skin radius, the
Skin modifier turns the graph into a closed organic hull, and a Subdivision Surface smooths it.
Head, hands and shoes are shaped separately. No third-party or template human mesh is used.

Conventions: metres, Blender Z up, character faces -Y (glTF exporter converts to +Y up, +Z forward).
Character's left side is +X. Rest pose is an A-pose (arms ~45° below horizontal).
"""
import math
import bmesh
import bpy
from mathutils import Vector

# ----------------------------------------------------------------------------- joints
# Shared with the rig (trainer_rig.py) so the skeleton matches the body exactly.
HIP_Z = 0.93
J = {
    "pelvis": Vector((0, 0.0, 0.95)),
    "spine": Vector((0, 0.0, 1.08)),
    "chest": Vector((0, 0.0, 1.27)),
    "neck": Vector((0, 0.0, 1.47)),
    "head": Vector((0, -0.005, 1.57)),
    "head_top": Vector((0, -0.005, 1.79)),
}
ARM_DROP = math.radians(45)
for side, s in (("L", 1), ("R", -1)):
    sh = Vector((0.198 * s, 0.0, 1.43))
    J[f"shoulder_{side}"] = Vector((0.06 * s, -0.005, 1.43))
    J[f"upper_arm_{side}"] = sh
    el = sh + Vector((0.285 * math.cos(ARM_DROP) * s, 0.0, -0.285 * math.sin(ARM_DROP)))
    J[f"forearm_{side}"] = el
    wr = el + Vector((0.255 * math.cos(ARM_DROP) * s, -0.01, -0.255 * math.sin(ARM_DROP)))
    J[f"hand_{side}"] = wr
    J[f"hand_tip_{side}"] = wr + Vector((0.17 * math.cos(ARM_DROP) * s, -0.01, -0.17 * math.sin(ARM_DROP)))
    J[f"thigh_{side}"] = Vector((0.088 * s, 0.0, HIP_Z))
    J[f"shin_{side}"] = Vector((0.095 * s, -0.01, 0.515))
    J[f"foot_{side}"] = Vector((0.097 * s, 0.015, 0.09))
    J[f"toe_{side}"] = Vector((0.10 * s, -0.135, 0.03))
    J[f"toe_tip_{side}"] = Vector((0.10 * s, -0.19, 0.03))


def _lerp(a, b, t):
    return a + (b - a) * t


def build_body_graph():
    """Returns (verts, edges, radii) for the skin-modifier graph."""
    verts, radii, edges = [], [], []

    def v(p, rx, ry=None, k=1.42):
        verts.append(Vector(p))
        radii.append((rx * k, (ry if ry is not None else rx) * k))
        return len(verts) - 1

    T = 1.22  # torso radius factor

    # torso (x radius = width, y radius = depth)
    crotch = v((0, 0.0, 0.87), 0.07, 0.07, T)
    pelvis = v(J["pelvis"], 0.142, 0.104, T)
    waist = v((0, 0.0, 1.07), 0.122, 0.092, T)
    ribs = v((0, -0.005, 1.19), 0.143, 0.104, T)
    chest = v((0, -0.016, 1.30), 0.168, 0.116, T)
    upper = v((0, -0.004, 1.39), 0.158, 0.096, T)
    neck0 = v((0, 0.004, 1.475), 0.05, 0.054)
    neck1 = v((0, 0.0, 1.575), 0.052, 0.056)
    edges += [(crotch, pelvis), (pelvis, waist), (waist, ribs), (ribs, chest), (chest, upper), (upper, neck0), (neck0, neck1)]

    for side, s in (("L", 1), ("R", -1)):
        # shoulder cap and arm
        cap = v((0.14 * s, 0.0, 1.415), 0.056, 0.054)
        sh = v(J[f"upper_arm_{side}"], 0.054, 0.054)
        edges += [(upper, cap), (cap, sh)]
        prev = sh
        for t, r in ((0.35, 0.052), (0.7, 0.044)):
            n = v(_lerp(J[f"upper_arm_{side}"], J[f"forearm_{side}"], t), r)
            edges.append((prev, n)); prev = n
        el = v(J[f"forearm_{side}"], 0.038)
        edges.append((prev, el)); prev = el
        for t, r in ((0.3, 0.042), (0.7, 0.032)):
            n = v(_lerp(J[f"forearm_{side}"], J[f"hand_{side}"], t), r)
            edges.append((prev, n)); prev = n
        wr = v(J[f"hand_{side}"], 0.026, 0.022)
        edges.append((prev, wr))

        # leg: from pelvis through hip joint
        hip = v(J[f"thigh_{side}"] + Vector((0.006 * s, 0, -0.03)), 0.072, 0.076)
        edges += [(pelvis, hip)]
        prev = hip
        for t, r in ((0.3, 0.078), (0.65, 0.064)):
            n = v(_lerp(J[f"thigh_{side}"], J[f"shin_{side}"], t), r, r * 1.05)
            edges.append((prev, n)); prev = n
        kn = v(J[f"shin_{side}"], 0.046, 0.048)
        edges.append((prev, kn)); prev = kn
        # calf sits behind the shin bone (+Y), then the leg tapers to the ankle
        for t, r, ry, back in ((0.28, 0.048, 0.054, 0.014), (0.62, 0.034, 0.036, 0.004)):
            n = v(_lerp(J[f"shin_{side}"], J[f"foot_{side}"], t) + Vector((0, back, 0)), r, ry)
            edges.append((prev, n)); prev = n
        an = v(J[f"foot_{side}"] + Vector((0, 0, 0.02)), 0.026, 0.028)
        edges.append((prev, an))
    return verts, edges, radii


def make_skin_object(name, verts, edges, radii, root_index=0, subdiv=2):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in verts], edges, [])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    skin = obj.modifiers.new("skin", "SKIN")
    skin.use_smooth_shade = True
    skin.branch_smoothing = 0.6
    for i, r in enumerate(radii):
        mesh.skin_vertices[0].data[i].radius = r
    for i, sv in enumerate(mesh.skin_vertices[0].data):
        sv.use_root = (i == root_index)
    sub = obj.modifiers.new("subd", "SUBSURF")
    sub.levels = subdiv
    sub.render_levels = subdiv
    apply_modifiers(obj)
    return obj


def apply_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


HEAD_CENTRE = Vector((0, -0.012, 1.66))


def _head_point(p, grow=1.0):
    """Maps a unit-sphere point to the sculpted head surface."""
    sx, sy, sz = 0.088 * grow, 0.104 * grow, 0.122 * grow
    if p.z < 0:  # jaw narrows toward the chin
        sx *= 1.0 - 0.17 * (-p.z) ** 1.6
        sy *= 1.0 - 0.10 * (-p.z)
    q = Vector((p.x * sx, p.y * sy, p.z * sz))
    face = max(0.0, -p.y)
    nose = math.exp(-((p.x / 0.13) ** 2) - (((p.z + 0.08) / 0.17) ** 2)) * face ** 3
    q.y -= 0.022 * nose
    brow = math.exp(-((p.z - 0.2) / 0.1) ** 2) * face ** 2 * math.exp(-(p.x / 0.55) ** 2)
    q.y -= 0.007 * brow
    for ex in (-0.33, 0.33):  # shallow eye sockets
        socket = math.exp(-(((p.x - ex) / 0.15) ** 2) - (((p.z - 0.06) / 0.09) ** 2)) * face ** 2
        q.y += 0.010 * socket
    chin = math.exp(-((p.x / 0.25) ** 2) - (((p.z + 0.82) / 0.2) ** 2)) * face
    q.y -= 0.008 * chin
    ear = math.exp(-((abs(p.x) - 1.0) / 0.1) ** 2 - ((p.y - 0.1) / 0.16) ** 2 - ((p.z - 0.0) / 0.2) ** 2)
    q.x += 0.014 * ear * (1 if p.x > 0 else -1)
    return q + HEAD_CENTRE


def make_head():
    """Egg-shaped head with jaw, brow, nose, eye sockets and ears — sculpted by vertex displacement."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=26, radius=1.0)
    head = bpy.context.active_object
    head.name = "trainer_head"
    for vert in head.data.vertices:
        vert.co = _head_point(vert.co.copy())
    bpy.ops.object.shade_smooth()
    return head


def make_hair():
    """Short hair as its own shell: a slightly larger skull, cut along a hairline plane."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=26, radius=1.0)
    hair = bpy.context.active_object
    hair.name = "trainer_hair"
    for vert in hair.data.vertices:
        p = vert.co.copy()
        q = _head_point(p, grow=1.045) - HEAD_CENTRE
        q.z *= 1.03
        vert.co = q + HEAD_CENTRE + Vector((0, 0.004, 0.002))
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    # hairline: high on the forehead, sweeping down behind the ears to the nape
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=HEAD_CENTRE + Vector((0, -0.07, 0.075)), plane_no=Vector((0, 0.42, 0.9)), clear_inner=True)
    bm.to_mesh(hair.data)
    bm.free()
    bpy.ops.object.shade_smooth()
    return hair


def make_hand(side):
    """Compact, loosely closed hand (reads as a relaxed hand at rest and as a fist in guard)."""
    wr, tip = J[f"hand_{side}"], J[f"hand_tip_{side}"]
    d = (tip - wr).normalized()
    verts, edges, radii = [], [], []

    def v(p, rx, ry=None):
        verts.append(Vector(p)); radii.append((rx, ry if ry is not None else rx)); return len(verts) - 1

    a = v(wr, 0.027, 0.022)
    b = v(wr + d * 0.04, 0.04, 0.026)
    c = v(wr + d * 0.08, 0.043, 0.03)
    e = v(wr + d * 0.108, 0.036, 0.028)
    edges += [(a, b), (b, c), (c, e)]
    th0 = v(wr + d * 0.035 + Vector((0, -0.026, 0)), 0.015)
    th1 = v(wr + d * 0.075 + Vector((0, -0.036, 0)), 0.013)
    edges += [(b, th0), (th0, th1)]
    return make_skin_object(f"trainer_hand_{side}", verts, edges, radii, subdiv=2)


def make_shoe(side):
    s = 1 if side == "L" else -1
    verts, edges, radii = [], [], []

    def v(p, rx, ry=None):
        verts.append(Vector(p)); radii.append((rx, ry if ry is not None else rx)); return len(verts) - 1

    x = J[f"foot_{side}"].x
    heel = v((x, 0.045, 0.045), 0.042, 0.04)
    ank = v((x, 0.01, 0.075), 0.045, 0.045)
    mid = v((x + 0.004 * s, -0.06, 0.04), 0.05, 0.04)
    ball = v((x + 0.006 * s, -0.13, 0.032), 0.05, 0.03)
    toe = v((x + 0.006 * s, -0.185, 0.03), 0.036, 0.024)
    edges += [(heel, ank), (heel, mid), (ank, mid), (mid, ball), (ball, toe)]
    shoe = make_skin_object(f"trainer_shoe_{side}", verts, edges, radii, subdiv=1)
    # flatten the sole onto the floor
    for vert in shoe.data.vertices:
        if vert.co.z < 0.012:
            vert.co.z = 0.0
    return shoe


# ----------------------------------------------------------------------------- materials
def material(name, rgb, roughness=0.75):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def srgb(hexstr):
    """Hex sRGB to linear RGB (Blender colour inputs are linear)."""
    out = []
    for i in (0, 2, 4):
        c = int(hexstr[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


MAT = {}


def build_materials():
    MAT["skin"] = material("trainer_skin", srgb("B98A6A"), 0.55)
    MAT["shirt"] = material("trainer_shirt", srgb("A9D626"), 0.8)
    MAT["shorts"] = material("trainer_shorts", srgb("1B1F24"), 0.8)
    MAT["shoe"] = material("trainer_shoe", srgb("E6E2DA"), 0.7)
    MAT["sole"] = material("trainer_sole", srgb("4A4F55"), 0.9)
    MAT["hair"] = material("trainer_hair", srgb("2A211C"), 0.9)


def cut_seams(obj):
    """Bisect the body along clothing edges so material borders are clean straight seams."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    planes = [((0, 0, SHIRT_HEM_Z), (0, 0, 1)), ((0, 0, SHORTS_HEM_Z), (0, 0, 1))]
    for side in ("L", "R"):
        a, b = J[f"upper_arm_{side}"], J[f"forearm_{side}"]
        d = (b - a).normalized()
        planes.append((tuple(a + d * SLEEVE_LEN), tuple(d)))
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    bm.to_mesh(obj.data)
    bm.free()


SHIRT_HEM_Z = 0.985
SHORTS_HEM_Z = 0.60
SLEEVE_LEN = 0.11  # along the upper arm from the shoulder joint


def _past_sleeve(c):
    for side in ("L", "R"):
        a, b = J[f"upper_arm_{side}"], J[f"forearm_{side}"]
        d = (b - a).normalized()
        if (c - a).dot(d) > SLEEVE_LEN and (c.x > 0) == (a.x > 0) and abs(c.x) > 0.17:
            return True
    return False


def assign_body_materials(body):
    """Clothing by region: short-sleeve shirt, shorts above the knee, skin elsewhere."""
    mats = [MAT["skin"], MAT["shirt"], MAT["shorts"]]
    for m in mats:
        body.data.materials.append(m)
    cut_seams(body)
    for poly in body.data.polygons:
        c = poly.center
        if c.z > SHIRT_HEM_Z and c.z < 1.47 and not _past_sleeve(c):
            poly.material_index = 1  # shirt with short sleeves
        elif SHORTS_HEM_Z < c.z <= SHIRT_HEM_Z:
            poly.material_index = 2  # shorts, above the knee
        else:
            poly.material_index = 0


def assign_head_materials(head):
    head.data.materials.append(MAT["skin"])


def assign_shoe_materials(shoe):
    shoe.data.materials.append(MAT["shoe"])
    shoe.data.materials.append(MAT["sole"])
    for poly in shoe.data.polygons:
        if poly.center.z < 0.014:
            poly.material_index = 1


def build_body():
    build_materials()
    verts, edges, radii = build_body_graph()
    body = make_skin_object("trainer_body", verts, edges, radii, root_index=1, subdiv=2)
    assign_body_materials(body)
    head = make_head()
    assign_head_materials(head)
    hair = make_hair()
    hair.data.materials.append(MAT["hair"])
    parts = [head, hair]
    for side in ("L", "R"):
        h = make_hand(side)
        h.data.materials.append(MAT["skin"])
        s = make_shoe(side)
        assign_shoe_materials(s)
        parts += [h, s]
    return body, parts
