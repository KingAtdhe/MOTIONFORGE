"""
MOTIONFORGE coach — sculpt-style character build (from scratch, no base mesh).

Workflow (the same stages a character artist follows, done in code):
  1. Block out anatomy with primitive muscle forms (ellipsoids / tapered capsules) on the rig joints.
  2. Fuse and smooth them with a voxel remesh (digital clay), then reduce to a game-ready polycount.
  3. Paint cavity shading into vertex colours so muscle definition reads on a phone.
  4. Rig with automatic weights; cut clothing from the body surface so it deforms with it.
  5. Add head detail (eyes, brows, lips, ears), hair, hands with fingers, gloves and trainers.
  6. Bake the animation clips, save the .blend, export GLB + clip manifest, render a turnaround.

Design reference: owner-supplied "Workout Coach" sheet (female coach). No logo is reproduced.
Run: python tools/blender/build_coach.py [--previews]
"""
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)

import trainer_anim as ta  # noqa: E402
import trainer_rig as tr  # noqa: E402
from trainer_body import J, material, srgb  # noqa: E402

Z = Vector((0, 0, 1))


# ----------------------------------------------------------------------------- clay primitives
class Clay:
    """Collects primitive forms into one mesh that is later voxel-fused."""

    def __init__(self):
        self.bm = bmesh.new()

    def _add(self, verts_fn, matrix):
        geom = verts_fn()
        bmesh.ops.transform(self.bm, matrix=matrix, verts=geom)

    def ell(self, c, r, axis=None, frame=None):
        """Ellipsoid at c with radii r=(x,y,z). axis: direction for local Z. frame: 3x3 local axes."""
        rot = Matrix.Identity(3)
        if frame is not None:
            rot = frame
        elif axis is not None:
            rot = Z.rotation_difference(Vector(axis).normalized()).to_matrix()
        m = Matrix.Translation(Vector(c)) @ rot.to_4x4() @ Matrix.Diagonal((r[0], r[1], r[2], 1.0))
        self._add(lambda: bmesh.ops.create_uvsphere(self.bm, u_segments=20, v_segments=12, radius=1.0)["verts"], m)

    def seg(self, a, b, r1, r2):
        """Tapered capsule from a (radius r1) to b (radius r2)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        rot = Z.rotation_difference(d.normalized()).to_matrix().to_4x4()
        m = Matrix.Translation((a + b) / 2) @ rot
        self._add(lambda: bmesh.ops.create_cone(self.bm, cap_ends=True, segments=18, radius1=r1, radius2=r2, depth=d.length)["verts"], m)
        self.ell(a, (r1, r1, r1))
        self.ell(b, (r2, r2, r2))

    def build(self, name, voxel, smooth=6, tris=None, smooth_factor=0.5):
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        mesh.remesh_voxel_size = voxel
        mesh.remesh_voxel_adaptivity = 0.0
        bpy.ops.object.voxel_remesh()
        if smooth:
            mod = obj.modifiers.new("smooth", "SMOOTH")
            mod.factor = smooth_factor
            mod.iterations = smooth
            bpy.ops.object.modifier_apply(modifier=mod.name)
        if tris:
            current = sum(len(p.vertices) - 2 for p in obj.data.polygons)
            if current > tris:
                dec = obj.modifiers.new("dec", "DECIMATE")
                dec.ratio = tris / current
                bpy.ops.object.modifier_apply(modifier=dec.name)
        bpy.ops.object.shade_smooth()
        return obj


def lerp(a, b, t):
    return Vector(a) + (Vector(b) - Vector(a)) * t


# ----------------------------------------------------------------------------- body sculpt (female athletic)
def sculpt_body():
    c = Clay()
    # torso
    c.ell((0, 0.008, 0.955), (0.150, 0.100, 0.095))            # pelvis
    c.ell((0, 0.0, 1.085), (0.112, 0.082, 0.115))              # waist
    c.ell((0, 0.004, 1.255), (0.132, 0.098, 0.135))            # ribcage
    c.ell((0, 0.004, 1.385), (0.150, 0.084, 0.068))            # shoulder girdle
    c.seg((0, 0.008, 1.43), (0, -0.002, 1.525), 0.045, 0.040)  # neck
    for s in (1, -1):
        c.ell((s * 0.078, 0.062, 0.925), (0.086, 0.088, 0.094))    # glute
        c.ell((s * 0.066, -0.082, 1.292), (0.062, 0.054, 0.058))   # chest
        c.ell((s * 0.050, 0.028, 1.462), (0.058, 0.046, 0.044), axis=(s * 0.5, 0, 1))    # trapezius
        c.ell((s * 0.110, 0.010, 1.428), (0.078, 0.052, 0.034), axis=(s * 0.28, 0, 1))    # shoulder slope
        c.ell((s * 0.122, 0.034, 1.275), (0.040, 0.058, 0.110))    # lat
        c.ell((s * 0.088, -0.036, 1.085), (0.026, 0.034, 0.080))   # oblique
        for i, zc in enumerate((1.045, 1.105, 1.165)):             # abdominals
            c.ell((s * 0.030, -0.074 - 0.003 * i, zc), (0.026, 0.010, 0.022))
        c.ell((s * 0.050, 0.066, 1.330), (0.044, 0.030, 0.070))    # scapular / upper back
        # arm
        S, E, W = J[f"upper_arm_{'L' if s > 0 else 'R'}"], J[f"forearm_{'L' if s > 0 else 'R'}"], J[f"hand_{'L' if s > 0 else 'R'}"]
        d = (E - S).normalized()
        c.ell(S + Vector((s * 0.004, 0, -0.014)), (0.064, 0.062, 0.066))                 # deltoid
        c.seg(S, E, 0.049, 0.040)
        c.ell(lerp(S, E, 0.52) + Vector((0, -0.017, 0)), (0.036, 0.036, 0.082), axis=d)  # biceps
        c.ell(lerp(S, E, 0.50) + Vector((0, 0.019, 0)), (0.034, 0.034, 0.088), axis=d)   # triceps
        f = (W - E).normalized()
        c.seg(E, W, 0.040, 0.028)
        c.ell(lerp(E, W, 0.27), (0.042, 0.039, 0.072), axis=f)                           # forearm
        # leg
        H, K, A = J[f"thigh_{'L' if s > 0 else 'R'}"], J[f"shin_{'L' if s > 0 else 'R'}"], J[f"foot_{'L' if s > 0 else 'R'}"]
        t = (K - H).normalized()
        c.seg(H + Vector((0, 0, -0.02)), K, 0.082, 0.050)
        c.ell(lerp(H, K, 0.42) + Vector((s * 0.008, -0.026, 0)), (0.060, 0.056, 0.150), axis=t)   # quadriceps
        c.ell(lerp(H, K, 0.50) + Vector((0, 0.030, 0)), (0.054, 0.050, 0.140), axis=t)            # hamstrings
        c.ell(lerp(H, K, 0.84) + Vector((-s * 0.020, -0.018, 0)), (0.028, 0.026, 0.045), axis=t)  # inner quad
        c.ell(K + Vector((0, -0.008, 0)), (0.047, 0.050, 0.050))                                  # knee
        g = (A - K).normalized()
        c.seg(K, A + Vector((0, 0, 0.02)), 0.046, 0.030)
        c.ell(lerp(K, A, 0.30) + Vector((0, 0.024, 0)), (0.044, 0.047, 0.100), axis=g)            # calf
        c.ell(A + Vector((0, 0.0, 0.0)), (0.034, 0.040, 0.040))                                   # ankle
    return c.build("coach_body", voxel=0.0055, smooth=6, tris=11000)


def sculpt_head():
    c = Clay()
    hz = 1.622
    c.ell((0, 0.012, hz + 0.018), (0.073, 0.090, 0.082))            # cranium
    c.ell((0, -0.020, hz - 0.030), (0.060, 0.072, 0.080))           # face mass
    c.ell((0, -0.050, hz - 0.090), (0.030, 0.026, 0.024))           # chin
    c.ell((0, -0.094, hz - 0.012), (0.011, 0.014, 0.026))           # nose bridge
    c.ell((0, -0.104, hz - 0.030), (0.0125, 0.011, 0.010))          # nose tip
    c.ell((0, -0.080, hz - 0.062), (0.026, 0.012, 0.014))           # mouth mound
    c.seg((0, 0.006, hz - 0.080), (0, 0.010, hz - 0.112), 0.037, 0.039)  # neck stub (overlaps body neck)
    for s in (1, -1):
        c.ell((s * 0.030, -0.076, hz + 0.022), (0.024, 0.010, 0.007))   # brow ridge
        c.ell((s * 0.040, -0.060, hz - 0.024), (0.018, 0.016, 0.014))   # cheekbone
        c.ell((s * 0.038, -0.028, hz - 0.060), (0.022, 0.032, 0.028))   # jaw
        c.ell((s * 0.011, -0.098, hz - 0.034), (0.008, 0.007, 0.006))   # nostril wing
        c.ell((s * 0.075, 0.012, hz - 0.008), (0.008, 0.015, 0.026), axis=(s * 0.25, 0.15, 1))  # ear
    return c.build("coach_head", voxel=0.0026, smooth=9, tris=5200, smooth_factor=0.5), hz


def face_parts(hz, mats):
    """Eyes, lashes, brows and lips as small separate forms."""
    out = []

    def piece(name, mat, fn, voxel=0.0012, smooth=2, tris=260):
        c = Clay()
        fn(c)
        o = c.build(name, voxel=voxel, smooth=smooth, tris=tris)
        o.data.materials.append(mat)
        out.append(o)

    for s in (1, -1):
        ex, ey, ez = s * 0.0305, -0.0775, hz + 0.004
        piece("eye_white", mats["eye"], lambda c: c.ell((ex, ey, ez), (0.0135, 0.0075, 0.0072)))
        piece("iris", mats["iris"], lambda c: c.ell((ex - s * 0.0005, ey - 0.0064, ez + 0.0004), (0.0056, 0.0022, 0.0058)), voxel=0.0009, tris=160)
        piece("pupil", mats["dark"], lambda c: c.ell((ex - s * 0.0005, ey - 0.0078, ez + 0.0004), (0.0026, 0.0012, 0.0027)), voxel=0.0007, tris=80)
        piece("lash", mats["dark"], lambda c: (c.seg((ex - s * 0.0135, ey - 0.0030, ez + 0.0035), (ex, ey - 0.0068, ez + 0.0076), 0.0013, 0.0017),
                                               c.seg((ex, ey - 0.0068, ez + 0.0076), (ex + s * 0.0150, ey - 0.0020, ez + 0.0062), 0.0017, 0.0010)), voxel=0.0008, tris=180)
        piece("brow", mats["hair"], lambda c: (c.seg((ex - s * 0.0150, ey - 0.0105, ez + 0.0185), (ex + s * 0.0040, ey - 0.0105, ez + 0.0230), 0.0030, 0.0028),
                                               c.seg((ex + s * 0.0040, ey - 0.0105, ez + 0.0230), (ex + s * 0.0200, ey - 0.0050, ez + 0.0190), 0.0028, 0.0012)), voxel=0.0010, tris=200)
    my = hz - 0.060
    piece("lip_upper", mats["lip"], lambda c: (c.ell((0.008, -0.0915, my + 0.0030), (0.0100, 0.0045, 0.0034)), c.ell((-0.008, -0.0915, my + 0.0030), (0.0100, 0.0045, 0.0034))), tris=240)
    piece("lip_lower", mats["lip"], lambda c: c.ell((0, -0.0905, my - 0.0040), (0.0150, 0.0055, 0.0046)), tris=200)
    return out


def sculpt_hair(hz, mats):
    c = Clay()
    c.ell((0, 0.020, hz + 0.028), (0.080, 0.097, 0.086))                    # cap
    # swept fringe and face-framing locks
    for s, off in ((1, 0.0), (-1, 0.012)):
        c.seg((s * 0.010, -0.070, hz + 0.092), (s * 0.058, -0.072, hz + 0.052), 0.022, 0.016)
        c.seg((s * 0.058, -0.072, hz + 0.052), (s * 0.078, -0.040, hz - 0.010 - off), 0.016, 0.010)
        c.seg((s * 0.078, -0.040, hz - 0.010 - off), (s * 0.074, -0.034, hz - 0.070 - off), 0.010, 0.005)
    # ponytail: gathered at the crown, falls behind the shoulders in tapering clumps
    tie = Vector((0, 0.088, hz + 0.070))
    pts = [tie, Vector((0, 0.150, hz + 0.075)), Vector((0, 0.190, hz + 0.010)), Vector((0.006, 0.200, hz - 0.090)), Vector((-0.004, 0.188, hz - 0.190)), Vector((0.004, 0.170, hz - 0.290))]
    rad = [0.040, 0.050, 0.050, 0.044, 0.034, 0.014]
    for i in range(len(pts) - 1):
        c.seg(pts[i], pts[i + 1], rad[i], rad[i + 1])
    for dx, dz, r in ((0.034, -0.02, 0.020), (-0.036, -0.05, 0.018), (0.022, -0.10, 0.016), (-0.026, 0.02, 0.018)):
        c.seg(pts[2] + Vector((dx, 0, dz)), pts[4] + Vector((dx * 1.2, 0.006, dz - 0.03)), r, r * 0.45)
    hair = c.build("coach_hair", voxel=0.0045, smooth=3, tris=3600, smooth_factor=0.4)
    # cut the hairline: keep top/back, clear the face
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector((0, -0.058, hz + 0.040)), plane_no=Vector((0, 0.94, 0.34)), clear_inner=False)
    doomed = [f for f in bm.faces if (f.calc_center_median() - Vector((0, -0.058, hz + 0.040))).dot(Vector((0, 0.94, 0.34))) < 0
              and abs(f.calc_center_median().x) < 0.050 and f.calc_center_median().z < hz + 0.075]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(hair.data)
    bm.free()
    hair.data.materials.append(mats["hair"])
    c2 = Clay()
    c2.ell(tie + Vector((0, 0.022, 0.004)), (0.030, 0.014, 0.030), axis=(0, 1, 0.1))
    band = c2.build("hair_tie", voxel=0.003, smooth=2, tris=220)
    band.data.materials.append(mats["tie"])
    return [hair, band]


def sculpt_hand(side, mats):
    s = 1 if side == "L" else -1
    W, T = J[f"hand_{side}"], J[f"hand_tip_{side}"]
    d = (T - W).normalized()                    # along the fingers
    y = Vector((0, -1, 0))                      # toward the thumb (forward)
    x = d.cross(y).normalized()                 # palm normal
    y = x.cross(d).normalized()
    frame = Matrix((x, y, d)).transposed()
    c = Clay()
    c.ell(W + d * 0.046, (0.0135, 0.040, 0.050), frame=frame)                 # palm
    c.seg(W - d * 0.02, W + d * 0.012, 0.026, 0.027)                           # wrist
    lengths = (0.066, 0.076, 0.071, 0.056)
    for i, L in enumerate(lengths):
        off = (1.5 - i) * 0.0195
        base = W + d * 0.088 + y * off
        mid = base + (d * 0.92 - x * s * 0.0 + y * (1.5 - i) * 0.03).normalized() * L * 0.55
        tip = mid + (d * 0.86 - x * 0.50 * s * 0 + Vector((-s * 0.25, 0, -0.1))).normalized() * L * 0.45
        c.seg(base, mid, 0.0098, 0.0090)
        c.seg(mid, tip, 0.0090, 0.0076)
    tb = W + d * 0.030 + y * 0.034
    tm = tb + (d * 0.75 + y * 0.66).normalized() * 0.036
    c.seg(tb, tm, 0.0125, 0.0105)
    c.seg(tm, tm + (d * 0.92 + y * 0.30).normalized() * 0.030, 0.0105, 0.0085)
    hand = c.build(f"coach_hand_{side}", voxel=0.0026, smooth=3, tris=1300, smooth_factor=0.4)
    hand.data.materials.append(mats["skin"])
    # fingerless glove: palm wrap + cuff
    g = Clay()
    g.ell(W + d * 0.044, (0.0185, 0.0445, 0.047), frame=frame)
    g.seg(W - d * 0.030, W + d * 0.012, 0.0305, 0.0315)
    glove = g.build(f"coach_glove_{side}", voxel=0.003, smooth=2, tris=700)
    glove.data.materials.append(mats["black"])
    strap = Clay()
    strap.seg(W - d * 0.020, W - d * 0.004, 0.0335, 0.0335)
    st = strap.build(f"coach_strap_{side}", voxel=0.003, smooth=1, tris=260)
    st.data.materials.append(mats["accent"])
    return [hand, glove, st]


def sculpt_shoe(side, mats):
    s = 1 if side == "L" else -1
    x = J[f"foot_{side}"].x
    c = Clay()
    c.ell((x, -0.050, 0.052), (0.047, 0.118, 0.040))
    c.ell((x + s * 0.004, -0.140, 0.042), (0.045, 0.052, 0.030))
    c.ell((x, 0.036, 0.062), (0.041, 0.046, 0.052))
    c.seg((x, 0.012, 0.070), (x, 0.012, 0.125), 0.040, 0.037)
    upper = c.build(f"coach_shoe_{side}", voxel=0.004, smooth=3, tris=1300, smooth_factor=0.4)
    for v in upper.data.vertices:
        if v.co.z < 0.020:
            v.co.z = 0.020
    upper.data.materials.append(mats["black"])
    upper.data.materials.append(mats["accent"])
    for p in upper.data.polygons:  # side flash + heel
        cc = p.center
        if cc.y > 0.060 and 0.05 < cc.z < 0.10:
            p.material_index = 1
    so = Clay()
    so.ell((x + s * 0.002, -0.052, 0.012), (0.051, 0.150, 0.020))
    sole = so.build(f"coach_sole_{side}", voxel=0.004, smooth=2, tris=500)
    for v in sole.data.vertices:
        v.co.z = min(max(v.co.z, 0.0), 0.024)
    sole.data.materials.append(mats["white"])
    sole.data.materials.append(mats["accent"])
    for p in sole.data.polygons:
        if p.center.z < 0.004:
            p.material_index = 1
    return [upper, sole]


# ----------------------------------------------------------------------------- painting & clothing
def paint_cavity(obj, strength=3.0, blur=2):
    """Vertex-colour cavity shading: darkens creases between muscle forms, lifts the peaks slightly."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    val = []
    for v in bm.verts:
        if not v.link_edges:
            val.append(0.0)
            continue
        avg = Vector()
        el = 0.0
        for e in v.link_edges:
            o = e.other_vert(v)
            avg += o.co
            el += e.calc_length()
        n = len(v.link_edges)
        val.append(((avg / n) - v.co).dot(v.normal) / max(el / n, 1e-6))
    for _ in range(blur):
        nv = []
        for v in bm.verts:
            acc, n = val[v.index], 1
            for e in v.link_edges:
                acc += val[e.other_vert(v).index]
                n += 1
            nv.append(acc / n)
        val = nv
    attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT") if "Col" not in mesh.color_attributes else mesh.color_attributes["Col"]
    bm.free()
    for i, d in enumerate(val):
        k = 1.0 - strength * max(d, 0.0) + 0.5 * max(-d, 0.0)
        k = max(0.50, min(1.10, k))
        attr.data[i].color = (k, k * 0.96 if k < 1 else k, k * 0.93 if k < 1 else k, 1.0)
    mesh.color_attributes.active_color = attr
    mesh.color_attributes.render_color_index = list(mesh.color_attributes).index(attr)


def white_colour(obj):
    mesh = obj.data
    if "Col" in mesh.color_attributes:
        return
    attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for d in attr.data:
        d.color = (1, 1, 1, 1)


def cut_garment(body, name, keep, thickness, mat_fn, mats_list):
    """Duplicates the body faces selected by keep(centre) into a shell that sits on the skin.
    Vertex groups (skin weights) are carried over, so the garment deforms with the body."""
    g = body.copy()
    g.data = body.data.copy()
    g.name = name
    bpy.context.collection.objects.link(g)
    bm = bmesh.new()
    bm.from_mesh(g.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f.calc_center_median())], context="FACES")
    bm.to_mesh(g.data)
    bm.free()
    g.data.materials.clear()
    for m in mats_list:
        g.data.materials.append(m)
    bpy.context.view_layer.objects.active = g
    bpy.ops.object.select_all(action="DESELECT")
    g.select_set(True)
    for mod in list(g.modifiers):
        g.modifiers.remove(mod)
    dis = g.modifiers.new("lift", "DISPLACE")
    dis.strength = thickness
    dis.mid_level = 0.0
    bpy.ops.object.modifier_apply(modifier=dis.name)
    for p in g.data.polygons:
        p.material_index = mat_fn(p.center)
    for d in g.data.color_attributes["Col"].data:  # keep a softened version of the form shading
        k = 0.55 + 0.45 * d.color[0]
        d.color = (k, k, k, 1)
    return g


def vcol_material(name, rgb, roughness):
    m = material(name, rgb, roughness)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    col = nt.nodes.new("ShaderNodeVertexColor")
    col.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*rgb, 1.0)
    nt.links.new(col.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return m


# ----------------------------------------------------------------------------- build
scene = bpy.context.scene
scene.render.fps = ta.FPS

M = {
    "skin": vcol_material("coach_skin", srgb("D08A58"), 0.38),
    "black": vcol_material("coach_black", srgb("2A2B33"), 0.62),
    "accent": material("coach_accent", srgb("E0263A"), 0.55),
    "hair": vcol_material("coach_hair", srgb("4A2A1A"), 0.55),
    "eye": material("coach_eye", srgb("F4F0EA"), 0.3),
    "iris": material("coach_iris", srgb("7A4A26"), 0.3),
    "dark": material("coach_dark", srgb("140E0C"), 0.5),
    "lip": material("coach_lip", srgb("B5484C"), 0.4),
    "tie": material("coach_tie", srgb("2B4FA8"), 0.6),
    "white": material("coach_white", srgb("ECEAE6"), 0.6),
}

body = sculpt_body()
body.data.materials.append(M["skin"])
_bm = bmesh.new()
_bm.from_mesh(body.data)
for co, no in (((0, 0, 1.212), (0, 0, 1)), ((0, 0, 1.345), (0, 0, 1)), ((0, 0, 0.300), (0, 0, 1)), ((0, 0, 1.008), (0, 0, 1)), ((0, 0, 0.985), (0, 0, 1)),
               ((0.040, 0, 0), (1, 0, 0)), ((-0.040, 0, 0), (1, 0, 0)), ((0.105, 0, 0), (1, 0, 0)), ((-0.105, 0, 0), (1, 0, 0)), ((0, 0.02, 0), (0, 1, 0)), ((0, -0.012, 0), (0, 1, 0)), ((0, 0, 1.352), (0.7071, 0, 0.7071)), ((0, 0, 1.352), (-0.7071, 0, 0.7071))):
    bmesh.ops.bisect_plane(_bm, geom=_bm.verts[:] + _bm.edges[:] + _bm.faces[:], plane_co=co, plane_no=no)
_bm.to_mesh(body.data)
_bm.free()
paint_cavity(body)

arm = tr.build_armature()
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
assert len(body.vertex_groups) > 5, "automatic weights failed"


def torso_x(cz):
    return 0.175 if cz > 1.2 else 0.30


def bra_keep(c):
    ax = abs(c.x)
    if 1.212 < c.z < 1.345 and ax < 0.20:
        return True
    if 1.345 <= c.z < 1.475 and ax < 0.105:
        return (c.y < 0.02 and (ax > 0.040 or c.z - ax < 1.352)) or c.y >= 0.02   # scoop neck, straps, upper-back panel
    return False


def leg_keep(c):
    return 0.300 < c.z < 1.008 and abs(c.x) < 0.30


def leg_mat(c):
    ax = abs(c.x)
    if 0.985 < c.z:
        return 1                                    # waistband accent line
    if 0.34 < c.z < 0.86 and -0.012 < c.y < 0.02 and ax > 0.105:
        return 1                                    # outer-leg stripe
    return 0


bra = cut_garment(body, "coach_bra", bra_keep, 0.0045, lambda c: 0, [M["black"], M["accent"]])
leggings = cut_garment(body, "coach_leggings", leg_keep, 0.0035, leg_mat, [M["black"], M["accent"]])

head, hz = sculpt_head()
head.data.materials.append(M["skin"])
paint_cavity(head, strength=1.6, blur=2)
rigid = {"head": [head] + face_parts(hz, M) + sculpt_hair(hz, M)}
_pivot = Vector((0, 0.0, hz - 0.105))
for _o in rigid["head"]:
    for _v in _o.data.vertices:
        _v.co = _pivot + (_v.co - _pivot) * 1.10
for side in ("L", "R"):
    rigid[f"hand_{side}"] = sculpt_hand(side, M)
    rigid[f"foot_{side}"] = sculpt_shoe(side, M)
paint_cavity(rigid["head"][-2], strength=1.8, blur=1)   # hair clumps

parts = [bra, leggings]
for bone, objs in rigid.items():
    for o in objs:
        white_colour(o)
        grp = o.vertex_groups.new(name=bone)
        grp.add(range(len(o.data.vertices)), 1.0, "REPLACE")
        parts.append(o)

bpy.ops.object.select_all(action="DESELECT")
for p in parts:
    p.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
body.name = body.data.name = "trainer_avatar"
if not any(m.type == "ARMATURE" for m in body.modifiers):
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
body.parent = arm
# ---- cel shading baked into vertex colours (two bands, cool tinted shadow) + cavity as ink
_L = Vector((-0.45, -0.62, 0.64)).normalized()
_TINT = (0.60, 0.50, 0.64)
_col = body.data.color_attributes["Col"]
for _i, _v in enumerate(body.data.vertices):
    _f = max(0.0, min(1.0, (_v.normal.dot(_L) + 0.10) / 0.10))
    _c = _col.data[_i].color
    _ink = min(1.0, _c[0]) ** 1.8
    _col.data[_i].color = tuple(_ink * (_TINT[k] * (1 - _f) + _f) for k in range(3)) + (1.0,)

# ---- outline: inverted hull from a lighter copy (flipped normals, black, back faces culled by the engine)
M["outline"] = material("coach_outline", (0.02, 0.02, 0.03), 1.0)
hull = body.copy()
hull.data = body.data.copy()
hull.name = "coach_outline"
bpy.context.collection.objects.link(hull)
for _m in list(hull.modifiers):
    hull.modifiers.remove(_m)
bpy.ops.object.select_all(action="DESELECT")
hull.select_set(True)
bpy.context.view_layer.objects.active = hull
_d = hull.modifiers.new("dec", "DECIMATE")
_d.ratio = 0.38
bpy.ops.object.modifier_apply(modifier=_d.name)
_p = hull.modifiers.new("push", "DISPLACE")
_p.strength = 0.0042
_p.mid_level = 0.0
bpy.ops.object.modifier_apply(modifier=_p.name)
_hb = bmesh.new()
_hb.from_mesh(hull.data)
bmesh.ops.reverse_faces(_hb, faces=_hb.faces[:])
_hb.to_mesh(hull.data)
_hb.free()
hull.data.materials.clear()
hull.data.materials.append(M["outline"])
for _pl in hull.data.polygons:
    _pl.material_index = 0
bpy.ops.object.select_all(action="DESELECT")
hull.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()

body.data.validate()
tri_count = sum(len(p.vertices) - 2 for p in body.data.polygons)
print("TRIS", tri_count, "VERTS", len(body.data.vertices))

ta.build_clips(arm)
arm.animation_data.action = None

src = os.path.join(ROOT, "assets/blender/source/trainer_avatar.blend")
exp = os.path.join(ROOT, "assets/blender/exports/trainer_avatar.glb")
app_copy = os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.glb")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=src, compress=True)

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm.select_set(True)
kw = dict(filepath=exp, export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_texcoords=False, export_normals=True,
          export_materials="EXPORT", export_skins=True, export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
          export_frame_range=False, export_anim_single_armature=True, export_reset_pose_bones=True)
try:
    bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", export_all_vertex_colors=False, **kw)
except TypeError:
    bpy.ops.export_scene.gltf(**kw)
import struct  # noqa: E402

with open(exp, "rb") as fh:
    _raw = fh.read()
_jl = struct.unpack("<I", _raw[12:16])[0]
_g = json.loads(_raw[20:20 + _jl])
_rest = _raw[20 + _jl:]
for _mt in _g["materials"]:
    _mt.setdefault("extensions", {})["KHR_materials_unlit"] = {}
    _mt["doubleSided"] = False
_g["extensionsUsed"] = sorted(set(_g.get("extensionsUsed", []) + ["KHR_materials_unlit"]))
_js = json.dumps(_g, separators=(",", ":")).encode()
_js += b" " * ((4 - len(_js) % 4) % 4)
with open(exp, "wb") as fh:
    fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(_js) + len(_rest)) + struct.pack("<II", len(_js), 0x4E4F534A) + _js + _rest)
shutil.copyfile(exp, app_copy)
print("EXPORTED", os.path.getsize(exp))

manifest = {"asset": "models/trainer_avatar.glb", "generator": "tools/blender/build_coach.py", "fps": ta.FPS,
            "clips": [{"name": n, "durationSeconds": round(d, 3), "reviewStatus": "draft_pending_coach_review"} for n, d, _ in ta.clip_specs()]}
with open(os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.clips.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")

if "--previews" in sys.argv:
    import preview as pv
    from mathutils import Vector as V

    prev = os.path.join(ROOT, "assets/blender/previews")
    os.makedirs(prev, exist_ok=True)
    for f in os.listdir(prev):
        if f.endswith(".png"):
            os.remove(os.path.join(prev, f))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 72
    try:
        scene.cycles.use_denoising = True
    except Exception:
        pass
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    world = bpy.data.worlds.new("studio")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.70, 0.71, 0.75, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.85

    def area(name, loc, energy, size, color=(1, 1, 1)):
        l = bpy.data.lights.new(name, "AREA")
        l.energy, l.size, l.color = energy, size, color
        o = bpy.data.objects.new(name, l)
        bpy.context.collection.objects.link(o)
        o.location = loc
        return o

    rig_lights = [area("key", (-2.4, -3.2, 3.0), 250, 2.6, (1.0, 0.96, 0.92)), area("fill", (2.8, -2.4, 1.6), 60, 3.0, (0.9, 0.94, 1.0)),
                  area("rim_l", (-2.2, 2.6, 2.6), 380, 1.4), area("rim_r", (2.4, 2.4, 2.4), 320, 1.4, (1.0, 0.9, 0.9)), area("top", (0, 0.4, 4.2), 70, 2.0)]
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    floor = bpy.context.active_object
    fm = material("studio_floor", (0.55, 0.56, 0.60), 0.6)
    floor.data.materials.append(fm)
    skin_bsdf = M["skin"].node_tree.nodes["Principled BSDF"]
    for key, val in (("Subsurface Weight", 0.12), ("Subsurface Radius", (1.0, 0.35, 0.2)), ("Subsurface Scale", 0.02)):
        try:
            skin_bsdf.inputs[key].default_value = val
        except Exception:
            pass
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "None"
    except Exception:
        pass
    for _m in list(body.data.materials):
        nt = _m.node_tree
        bs = nt.nodes.get("Principled BSDF")
        mixn = next((n for n in nt.nodes if n.type == "MIX"), None)
        rgb = tuple(mixn.inputs[6].default_value) if mixn else tuple(bs.inputs["Base Color"].default_value)
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        if _m.name == "coach_outline":
            em.inputs[0].default_value = (0.02, 0.02, 0.03, 1)
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            tr = nt.nodes.new("ShaderNodeBsdfTransparent")
            mx = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(geo.outputs["Backfacing"], mx.inputs[0])
            nt.links.new(em.outputs[0], mx.inputs[1])
            nt.links.new(tr.outputs[0], mx.inputs[2])
            nt.links.new(mx.outputs[0], out.inputs[0])
        else:
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = 1.0
            mul.inputs[6].default_value = rgb
            nt.links.new(vc.outputs["Color"], mul.inputs[7])
            nt.links.new(mul.outputs[2], em.inputs[0])
            nt.links.new(em.outputs[0], out.inputs[0])
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam

    def shot(name, clip, frame, yaw, target, dist, lens, res, light_yaw=None):
        if clip is None:
            arm.animation_data.action = None
            for pb in arm.pose.bones:
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.location = (0, 0, 0)
        else:
            arm.animation_data.action = bpy.data.actions[clip]
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        y = math.radians(yaw)
        t = V(target)
        cam.location = (t.x + dist * math.sin(y), t.y - dist * math.cos(y), t.z + dist * 0.06)
        cam.rotation_euler = (t - V(cam.location)).to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = lens
        # lights follow the camera so every view is lit like the hero shot
        rot = Matrix.Rotation(y, 4, "Z")
        for lo, base in zip(rig_lights, ((-2.4, -3.2, 3.0), (2.8, -2.4, 1.6), (-2.2, 2.6, 2.6), (2.4, 2.4, 2.4), (0, 0.4, 4.2))):
            lo.location = rot @ V(base) + V((t.x, t.y, 0))
            lo.rotation_euler = (V((t.x, t.y, 1.0)) - lo.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(prev, name + ".png")
        bpy.ops.render.render(write_still=True)

    full = dict(target=(0, 0, 0.90), dist=6.2, lens=85, res=(520, 1040))
    shot("hero", "idle_neutral", 1, 24, (0.0, 0, 1.20), 2.7, 70, (900, 1300))
    shot("turn_front", "idle_neutral", 1, 0, **full)
    shot("turn_side", "idle_neutral", 1, 90, **full)
    shot("turn_back", "idle_neutral", 1, 180, **full)
    shot("pose_squat", "squat_down", 49, 38, (0, -0.15, 0.75), 4.2, 70, (640, 800))
    shot("pose_jab", "boxing_jab", 13, 58, (0, -0.2, 0.95), 4.6, 70, (640, 800))
    shot("pose_cross", "boxing_cross", 15, 70, (0, -0.2, 0.95), 4.6, 70, (640, 800))
    shot("pose_step", "footwork_forward", 15, 100, (0, -0.1, 0.92), 4.8, 70, (640, 800))
    shot("det_face", "idle_neutral", 1, 12, (0, 0, 1.60), 1.5, 105, (560, 560))
    shot("det_core", "idle_neutral", 1, 16, (0, 0, 1.16), 1.6, 90, (560, 560))
    shot("det_glove", None, 1, 20, tuple(J["hand_L"] + V((0.03, 0, -0.04))), 0.85, 90, (560, 560))
    shot("det_shoe", "idle_neutral", 1, 52, (0.09, -0.04, 0.08), 0.95, 80, (560, 560))
    arm.animation_data.action = None
