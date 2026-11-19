"""Shared character parts: clay (voxel-fused primitive) builder and fist-capable hands."""
import bpy
import bmesh
from mathutils import Matrix, Vector

from trainer_body import J

Z = Vector((0, 0, 1))


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


def sculpt_hand(side, mats):
    """Palm + thumb (hand bone), proximal finger row (fingers bone), middle+distal rows (fingertips bone).
    Each group is a separate rigid piece with round joint caps, so the fingers can roll into a fist."""
    from trainer_rig import KNUCKLE, PROX
    s = 1 if side == "L" else -1
    W, T = J[f"hand_{side}"], J[f"hand_tip_{side}"]
    d = (T - W).normalized()                         # along the fingers
    y = Vector((0, -1, 0))                           # toward the thumb (forward)
    x = d.cross(y).normalized()
    y = x.cross(d).normalized()
    palm = x * s                                     # palm faces the body
    frame = Matrix((x, y, d)).transposed()
    c = Clay()
    c.ell(W + d * 0.046, (0.0145, 0.041, 0.050), frame=frame)                  # palm
    c.ell(W + d * 0.040 + palm * 0.006 - y * 0.020, (0.012, 0.016, 0.036), frame=frame)  # little-finger heel
    c.seg(W - d * 0.02, W + d * 0.012, 0.026, 0.027)                            # wrist
    tb = W + d * 0.028 + y * 0.032 + palm * 0.006                                # thumb lies along the index finger,
    tm = tb + (d * 0.80 + y * 0.30 + palm * 0.50).normalized() * 0.036          # tucked slightly toward the palm
    c.seg(tb, tm, 0.0130, 0.0108)
    c.seg(tm, tm + (d * 0.85 + palm * 0.50).normalized() * 0.030, 0.0108, 0.0088)
    hand = c.build(f"coach_hand_{side}", voxel=0.0026, smooth=3, tris=650, smooth_factor=0.4)
    p1, p2 = Clay(), Clay()
    for i, L in enumerate((0.040, 0.046, 0.043, 0.032)):          # middle+distal length per finger
        off = (1.5 - i) * 0.0192
        r = 0.0098 - 0.0006 * max(0, i - 1)
        k = W + d * KNUCKLE + y * off
        m = W + d * (KNUCKLE + PROX) + y * off * 0.96
        p1.seg(k, m, r, r * 0.93)
        p2.seg(m, m + d * L * 0.55, r * 0.93, r * 0.86)
        p2.seg(m + d * L * 0.55, m + d * L, r * 0.86, r * 0.74)
    prox = p1.build(f"coach_fingers_{side}", voxel=0.0018, smooth=2, tris=800, smooth_factor=0.4)
    dist = p2.build(f"coach_fingertips_{side}", voxel=0.0022, smooth=2, tris=480, smooth_factor=0.4)
    for o in (hand, prox, dist):
        o.data.materials.append(mats["skin"])
    # fingerless glove: palm wrap + cuff
    g = Clay()
    g.ell(W + d * 0.044, (0.0190, 0.0450, 0.046), frame=frame)
    g.seg(W - d * 0.030, W + d * 0.012, 0.0305, 0.0315)
    glove = g.build(f"coach_glove_{side}", voxel=0.0022, smooth=2, tris=1100)
    glove.data.materials.append(mats["black"])
    strap = Clay()
    strap.seg(W - d * 0.020, W - d * 0.004, 0.0335, 0.0335)
    st = strap.build(f"coach_strap_{side}", voxel=0.003, smooth=1, tris=220)
    st.data.materials.append(mats["accent"])
    return {f"hand_{side}": [hand, glove, st], f"fingers_{side}": [prox], f"fingertips_{side}": [dist]}
