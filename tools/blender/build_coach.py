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
    c.ell((0, 0.004, 1.392), (0.176, 0.086, 0.066))            # shoulder girdle
    c.seg((0, 0.008, 1.43), (0, -0.002, 1.555), 0.043, 0.039)  # neck
    for s in (1, -1):
        c.ell((s * 0.078, 0.062, 0.925), (0.086, 0.088, 0.094))    # glute
        c.ell((s * 0.066, -0.082, 1.292), (0.062, 0.054, 0.058))   # chest
        c.ell((s * 0.060, 0.026, 1.458), (0.060, 0.046, 0.036))    # trapezius
        c.ell((s * 0.118, 0.010, 1.432), (0.070, 0.050, 0.030))    # shoulder slope
        c.ell((s * 0.122, 0.034, 1.275), (0.040, 0.058, 0.110))    # lat
        c.ell((s * 0.090, -0.040, 1.085), (0.030, 0.038, 0.085))   # oblique
        for i, zc in enumerate((1.045, 1.105, 1.165)):             # abdominals
            c.ell((s * 0.033, -0.071 - 0.004 * i, zc), (0.030, 0.015, 0.025))
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
    return c.build("coach_body", voxel=0.0055, smooth=8, tris=11500)


def sculpt_head():
    c = Clay()
    hz = 1.650
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
        if (0.040 < cc.z < 0.075 and -0.11 < cc.y < 0.0 and (cc.x - x) * s > 0.028) or (cc.y > 0.060 and 0.05 < cc.z < 0.10):
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
def paint_cavity(obj, strength=2.6, blur=3):
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
    "skin": vcol_material("coach_skin", srgb("C98B62"), 0.48),
    "black": vcol_material("coach_black", srgb("1B1C21"), 0.62),
    "accent": material("coach_accent", srgb("E0263A"), 0.55),
    "hair": vcol_material("coach_hair", srgb("3B2418"), 0.55),
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
               ((0.040, 0, 0), (1, 0, 0)), ((-0.040, 0, 0), (1, 0, 0)), ((0.105, 0, 0), (1, 0, 0)), ((-0.105, 0, 0), (1, 0, 0)), ((0, 0.02, 0), (0, 1, 0)), ((0, -0.012, 0), (0, 1, 0)), ((0, 0, 1.405), (0, 0, 1))):
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
        return (c.y < 0.02 and (ax > 0.040 or c.z < 1.405)) or c.y >= 0.02   # scoop neck, straps, upper-back panel
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
shutil.copyfile(exp, app_copy)
print("EXPORTED", os.path.getsize(exp))

manifest = {"asset": "models/trainer_avatar.glb", "generator": "tools/blender/build_coach.py", "fps": ta.FPS,
            "clips": [{"name": n, "durationSeconds": round(d, 3), "reviewStatus": "draft_pending_coach_review"} for n, d, _ in ta.clip_specs()]}
with open(os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.clips.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")

if "--previews" in sys.argv:
    import preview as pv

    prev = os.path.join(ROOT, "assets/blender/previews")
    os.makedirs(prev, exist_ok=True)
    for f in os.listdir(prev):
        if f.endswith(".png"):
            os.remove(os.path.join(prev, f))
    cam = pv.setup_scene(resolution=(520, 760), samples=40)
    scene.view_settings.view_transform = "Standard"
    bpy.data.worlds[0].node_tree.nodes["Background"].inputs[0].default_value = (0.72, 0.73, 0.76, 1)
    bpy.data.objects["preview_floor"].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.56, 0.6, 1)
    shots = [("01_front", "idle_neutral", 1, 0, None), ("02_side", "idle_neutral", 1, 90, None), ("03_back", "idle_neutral", 1, 180, None),
             ("04_threeq", "idle_neutral", 1, 32, None), ("05_face", "idle_neutral", 1, 14, "face"), ("06_guard", "boxing_stance", 1, 25, None),
             ("07_jab", "boxing_jab", 13, 60, None), ("08_squat", "squat_down", 49, 40, None)]
    for name, clip, frame, yaw, mode in shots:
        arm.animation_data.action = bpy.data.actions[clip]
        scene.frame_set(frame)
        if mode == "face":
            pv.aim_camera(cam, yaw, distance=1.6, target=(0, 0, 1.60), height=1.64)
            cam.data.lens = 85
        else:
            cam.data.lens = 50
            pv.aim_camera(cam, yaw, distance=3.6, target=(0, 0, 0.92), height=1.05)
        pv.render_to(os.path.join(prev, name + ".png"))
    arm.animation_data.action = None
