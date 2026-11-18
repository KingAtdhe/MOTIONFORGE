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
    "head": Vector((0, -0.005, 1.56)),
    "head_top": Vector((0, -0.005, 1.76)),
}
ARM_DROP = math.radians(45)
for side, s in (("L", 1), ("R", -1)):
    sh = Vector((0.185 * s, 0.0, 1.425))
    J[f"shoulder_{side}"] = Vector((0.06 * s, -0.005, 1.43))
    J[f"upper_arm_{side}"] = sh
    el = sh + Vector((0.285 * math.cos(ARM_DROP) * s, 0.0, -0.285 * math.sin(ARM_DROP)))
    J[f"forearm_{side}"] = el
    wr = el + Vector((0.255 * math.cos(ARM_DROP) * s, -0.01, -0.255 * math.sin(ARM_DROP)))
    J[f"hand_{side}"] = wr
    J[f"hand_tip_{side}"] = wr + Vector((0.17 * math.cos(ARM_DROP) * s, -0.01, -0.17 * math.sin(ARM_DROP)))
    J[f"thigh_{side}"] = Vector((0.092 * s, 0.0, HIP_Z))
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
    pelvis = v(J["pelvis"], 0.158, 0.112, T)
    waist = v((0, 0.0, 1.06), 0.135, 0.098, T)
    ribs = v((0, -0.005, 1.18), 0.148, 0.106, T)
    chest = v((0, -0.012, 1.29), 0.165, 0.112, T)
    upper = v((0, -0.005, 1.385), 0.15, 0.098, T)
    neck0 = v((0, 0.0, 1.46), 0.05, 0.052)
    neck1 = v((0, 0.0, 1.55), 0.045, 0.048)
    edges += [(crotch, pelvis), (pelvis, waist), (waist, ribs), (ribs, chest), (chest, upper), (upper, neck0), (neck0, neck1)]

    for side, s in (("L", 1), ("R", -1)):
        # shoulder cap and arm
        cap = v((0.125 * s, 0.0, 1.405), 0.058, 0.055)
        sh = v(J[f"upper_arm_{side}"], 0.058, 0.058)
        edges += [(upper, cap), (cap, sh)]
        prev = sh
        for t, r in ((0.35, 0.054), (0.7, 0.047)):
            n = v(_lerp(J[f"upper_arm_{side}"], J[f"forearm_{side}"], t), r)
            edges.append((prev, n)); prev = n
        el = v(J[f"forearm_{side}"], 0.041)
        edges.append((prev, el)); prev = el
        for t, r in ((0.3, 0.043), (0.7, 0.034)):
            n = v(_lerp(J[f"forearm_{side}"], J[f"hand_{side}"], t), r)
            edges.append((prev, n)); prev = n
        wr = v(J[f"hand_{side}"], 0.029, 0.024)
        edges.append((prev, wr))

        # leg: from pelvis through hip joint
        hip = v(J[f"thigh_{side}"] + Vector((0.008 * s, 0, -0.03)), 0.072, 0.074)
        edges += [(pelvis, hip)]
        prev = hip
        for t, r in ((0.3, 0.083), (0.65, 0.068)):
            n = v(_lerp(J[f"thigh_{side}"], J[f"shin_{side}"], t), r, r * 1.05)
            edges.append((prev, n)); prev = n
        kn = v(J[f"shin_{side}"], 0.045, 0.048)
        edges.append((prev, kn)); prev = kn
        # calf sits behind the shin bone (+Y), then the leg tapers to the ankle
        for t, r, ry, back in ((0.28, 0.046, 0.05, 0.012), (0.62, 0.034, 0.036, 0.004)):
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


def make_head():
    """Egg-shaped head with a gentle jaw, brow and nose — sculpted by vertex displacement."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=18, radius=1.0)
    head = bpy.context.active_object
    head.name = "trainer_head"
    centre = Vector((0, -0.012, 1.655))
    for vert in head.data.vertices:
        p = vert.co.copy()
        sx, sy, sz = 0.083, 0.098, 0.115
        # narrow the jaw / chin
        if p.z < 0:
            k = 1.0 - 0.28 * (-p.z) ** 1.4
            sx *= k
            sy *= 1.0 - 0.12 * (-p.z)
        q = Vector((p.x * sx, p.y * sy, p.z * sz))
        # nose: small forward bump on the face (-Y) centre line
        face = max(0.0, -p.y)
        nose = math.exp(-((p.x / 0.16) ** 2) - (((p.z + 0.05) / 0.2) ** 2)) * face ** 3
        q.y -= 0.018 * nose
        # brow ridge
        brow = math.exp(-((p.z - 0.25) / 0.12) ** 2) * face ** 2 * math.exp(-(p.x / 0.6) ** 2)
        q.y -= 0.006 * brow
        # ears: small side bumps
        ear = math.exp(-((abs(p.x) - 1.0) / 0.12) ** 2 - (p.y / 0.18) ** 2 - ((p.z - 0.02) / 0.22) ** 2)
        q.x += 0.012 * ear * (1 if p.x > 0 else -1)
        vert.co = q + centre
    bpy.ops.object.shade_smooth()
    return head


def make_hand(side):
    """Simple relaxed hand: palm block + thumb, built from a skin graph."""
    s = 1 if side == "L" else -1
    wr, tip = J[f"hand_{side}"], J[f"hand_tip_{side}"]
    d = (tip - wr).normalized()
    verts, edges, radii = [], [], []

    def v(p, rx, ry=None):
        verts.append(Vector(p)); radii.append((rx, ry if ry is not None else rx)); return len(verts) - 1

    a = v(wr, 0.026, 0.02)
    b = v(wr + d * 0.05, 0.042, 0.018)
    c = v(wr + d * 0.095, 0.044, 0.016)
    e = v(wr + d * 0.15, 0.036, 0.013)
    f = v(wr + d * 0.175, 0.028, 0.011)
    edges += [(a, b), (b, c), (c, e), (e, f)]
    th0 = v(wr + d * 0.03 + Vector((0, -0.022, 0)), 0.014)
    th1 = v(wr + d * 0.075 + Vector((0, -0.045, 0)), 0.011)
    edges += [(b, th0), (th0, th1)]
    return make_skin_object(f"trainer_hand_{side}", verts, edges, radii, subdiv=1)


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
    MAT["skin"] = material("trainer_skin", srgb("B07E5E"), 0.6)
    MAT["shirt"] = material("trainer_shirt", srgb("2C4A52"), 0.85)
    MAT["shorts"] = material("trainer_shorts", srgb("23272C"), 0.85)
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
    head.data.materials.append(MAT["hair"])
    centre = Vector((0, -0.012, 1.655))
    for poly in head.data.polygons:
        p = poly.center - centre
        # short hair: top and back of the head
        if p.z > 0.045 - 0.06 * max(0.0, p.y / 0.1) or (p.y > 0.03 and p.z > -0.04):
            poly.material_index = 1


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
    parts = [head]
    for side in ("L", "R"):
        h = make_hand(side)
        h.data.materials.append(MAT["skin"])
        s = make_shoe(side)
        assign_shoe_materials(s)
        parts += [h, s]
    return body, parts
