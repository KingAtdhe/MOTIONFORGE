"""Training equipment for the coach GLBs, modelled from scratch: hex dumbbells, a kettlebell, a light resistance band and
a flat bench.

Each prop is a small mesh skinned 100 % to its own bone:
  dumbbell_L / dumbbell_R / kettlebell  children of the coach's hand bones (held in the fist)
  band                                  child of the left hand, aimed at the right fist and scaled to the gap
                                        on every frame, so the band stretches between the hands
  bench                                 a root bone of its own (stays on the floor whatever the body does)
Every clip keys every prop bone's scale: 1 in the clips that use it (authored_clips.PROPS_BY_CLIP), ~0 elsewhere, so a
prop never shows up in a lesson that does not use it and the GLB player needs no extra logic.

Placement: each held prop is positioned once from a reference frame of the clip that uses it, where the authored hand
orientation is known (fingers / palm directions), then fixed to the hand bone.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

HIDDEN = 1e-4


def _material(name, rgb, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def _prism(bm, axis_len, radius, sides, x0, rotate=0.0):
    """Closed prism along local X from x0 to x0 + axis_len."""
    ring0, ring1 = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides + rotate
        y, z = radius * math.cos(a), radius * math.sin(a)
        ring0.append(bm.verts.new((x0, y, z)))
        ring1.append(bm.verts.new((x0 + axis_len, y, z)))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    bm.faces.new(list(reversed(ring0)))
    bm.faces.new(ring1)


def dumbbell_mesh(k):
    """Hex dumbbell, handle along local X centred on the origin (the grip)."""
    bm = bmesh.new()
    h = 0.130 * k
    _prism(bm, h, 0.0155 * k, 12, -h / 2)                             # knurled handle
    for sgn in (-1, 1):
        _prism(bm, 0.012 * k, 0.024 * k, 12, sgn * h / 2 - (0.012 * k if sgn < 0 else 0))   # collars
        x0 = sgn * (h / 2 + 0.012 * k) - (0.062 * k if sgn < 0 else 0)
        _prism(bm, 0.062 * k, 0.050 * k, 6, x0, rotate=math.pi / 6)      # hex heads
    return bm, [(0, 12 * 2 + 2, "metal"), (None, None, "rubber")]


def kettlebell_mesh(k):
    """Kettlebell: handle bar along local X at the origin (the grip), bell below (-Z)."""
    bm = bmesh.new()
    r = 0.105 * k
    cz = -0.155 * k
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=r, matrix=Matrix.Translation((0, 0, cz)))
    for v in bm.verts:                                                  # flat base
        if v.co.z < cz - 0.80 * r:
            v.co.z = cz - 0.80 * r
    # handle: a bent bar (grip along X, two posts down into the bell)
    w = 0.075 * k
    path = [(-w, 0, -0.065 * k), (-w, 0, -0.010 * k), (-w * 0.75, 0, 0.012 * k), (0, 0, 0.018 * k), (w * 0.75, 0, 0.012 * k),
            (w, 0, -0.010 * k), (w, 0, -0.065 * k)]
    rad, sides = 0.014 * k, 8
    rings = []
    for i, p in enumerate(path):
        a = Vector(path[max(i - 1, 0)])
        b = Vector(path[min(i + 1, len(path) - 1)])
        t = (b - a).normalized()
        n1 = t.cross(Vector((0, 1, 0))).normalized()
        n2 = t.cross(n1).normalized()
        ring = [bm.verts.new(Vector(p) + (n1 * math.cos(2 * math.pi * j / sides) + n2 * math.sin(2 * math.pi * j / sides)) * rad)
                for j in range(sides)]
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            jj = (j + 1) % sides
            bm.faces.new((r0[j], r0[jj], r1[jj], r1[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return bm


def tube_between(bm, p0, p1, radius, segs=24, sides=8):
    """Tube from p0 to p1; returns per-vertex parameter t (0 at p0, 1 at p1)."""
    d = (p1 - p0)
    t_ = d.normalized()
    n1 = t_.cross(Vector((0, 0, 1)))
    if n1.length < 1e-3:
        n1 = t_.cross(Vector((0, 1, 0)))
    n1.normalize()
    n2 = t_.cross(n1).normalized()
    rings, params = [], {}
    for i in range(segs + 1):
        f = i / segs
        c = p0 + d * f
        ring = []
        for j in range(sides):
            a = 2 * math.pi * j / sides
            v = bm.verts.new(c + (n1 * math.cos(a) + n2 * math.sin(a)) * radius)
            params[v] = f
            ring.append(v)
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            jj = (j + 1) % sides
            bm.faces.new((r0[j], r0[jj], r1[jj], r1[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return params


def bench_mesh(k):
    """Flat bench: padded top 1.0 x 0.32 m, top surface at the origin, four splayed legs down to z = -height."""
    from authored_clips import INCLINE_BENCH_H
    bm = bmesh.new()
    H = INCLINE_BENCH_H
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, -0.035)) @ Matrix.Diagonal((1.00, 0.32, 0.07, 1.0)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, -0.085)) @ Matrix.Diagonal((0.92, 0.22, 0.03, 1.0)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            top = Vector((sx * 0.40, sy * 0.09, -0.10))
            bot = Vector((sx * 0.44, sy * 0.13, -H))
            tube_between(bm, top, bot, 0.016, segs=1, sides=8)
    return bm


def wall_mesh():
    """A plain wall panel 1.8 m wide, 2.3 m tall, 0.10 m thick: front face at y = 0 (facing +Y), floor at z = 0."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.05, 1.15)) @ Matrix.Diagonal((1.8, 0.10, 2.3, 1.0)))
    return bm


def _skin_world(mesh, frame):
    """Evaluated vertex positions (armature space = world here) of the coach mesh at `frame`."""
    import numpy as np
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    m2 = ev.to_mesh()
    co = np.empty(len(m2.vertices) * 3, np.float32)
    m2.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    return co.reshape(-1, 3)


# ---------------------------------------------------------------------------------------------------------------- build
def _new_bone(arm, name, matrix, parent):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones.new(name)
    eb.head = (0, 0, 0)
    eb.tail = (0, 0.08, 0)
    eb.matrix = matrix
    eb.parent = arm.data.edit_bones[parent] if parent else None
    eb.use_connect = False
    eb.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")


def _skinned_object(arm, name, bm, matrix, groups, materials):
    """groups: {bone name: weight fn(vertex) or 1.0}. Mesh vertices are given in prop space and moved by `matrix`."""
    bm.transform(matrix)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    for g, wfn in groups.items():
        vg = ob.vertex_groups.new(name=g)
        for v in me.vertices:
            w = wfn(v) if callable(wfn) else wfn
            if w > 0:
                vg.add([v.index], w, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    for p in me.polygons:
        p.use_smooth = False
    return ob


def _pose_world(arm, clip, frame, bone):
    arm.animation_data.action = bpy.data.actions[clip]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[bone].matrix


def _frame_from(f, p):
    """Orthonormal prop frame: X = handle axis (through the fist), Y = fingers, Z = palm normal."""
    y = f.normalized()
    z = (p - y * p.dot(y)).normalized()
    x = y.cross(z)
    M = Matrix((x, y, z)).transposed()
    return M


def add_props(arm, k):
    """Adds all prop bones and meshes to the coach armature `arm` (rest pose) and keys their visibility per clip.
    Returns the new mesh objects (to be exported with the coach)."""
    import authored_clips as ac
    HAND = {"L": "mixamorig:LeftHand", "R": "mixamorig:RightHand"}
    metal = _material("prop_metal", (0.55, 0.56, 0.58), 0.35, 0.9)
    rubber = _material("prop_rubber", (0.06, 0.06, 0.07), 0.8)
    iron = _material("prop_iron", (0.10, 0.10, 0.11), 0.55, 0.6)
    band_m = _material("prop_band", (0.10, 0.62, 0.58), 0.7)
    pad = _material("prop_pad", (0.08, 0.08, 0.09), 0.75)
    frame_m = _material("prop_frame", (0.32, 0.33, 0.35), 0.4, 0.8)
    objs = []
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}

    def held(clip, side, f, p, along=0.072, palm=0.024):
        """Prop matrix (armature space, rest pose) for a grip in `side`'s fist at the first frame of `clip`."""
        Hw = _pose_world(arm, clip, int(bpy.data.actions[clip].frame_range[0]), HAND[side])
        R = _frame_from(f, p)
        g = Hw.translation + f.normalized() * along * k + R.col[2] * palm * k
        P = Matrix.Translation(g) @ R.to_4x4()
        X = Hw.inverted() @ P
        return rest[HAND[side]] @ X, Hw

    # dumbbells: reference = curl at the bottom (fingers down, palm forward, turned in a little)
    th = math.radians(8.0)
    for s, sg in (("L", 1.0), ("R", -1.0)):
        f = Vector((sg * 0.05, -math.sin(th), -math.cos(th)))
        p = Vector((-sg * 0.25, -math.cos(th), math.sin(th)))
        M, _ = held("db_curl", s, f, p)
        _new_bone(arm, "dumbbell_" + s, M, HAND[s])
        bm, _ = dumbbell_mesh(k)
        ob = _skinned_object(arm, "prop_dumbbell_" + s, bm, M, {"dumbbell_" + s: 1.0}, [metal, rubber])
        for poly in ob.data.polygons:                                  # heads rubber, handle and collars metal
            c = sum((ob.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
            poly.material_index = 1 if (M.inverted() @ c).x.__abs__() > 0.077 * k else 0
        objs.append(ob)

    # kettlebell: reference = first frame of the deadlift (arms hang, both fists on the handle, palms toward the body)
    clip = "kb_deadlift_down"
    f = Vector((0.2, 0.1, -1.0))
    p = Vector((0, 1.0, 0))
    ML, HL = held(clip, "L", Vector((-0.2, 0.1, -1.0)), p)
    MR, HR = held(clip, "R", f, p)
    PL = HL @ (rest[HAND["L"]].inverted() @ ML)
    PR = HR @ (rest[HAND["R"]].inverted() @ MR)
    mid = (PL.translation + PR.translation) / 2
    xax = (PL.translation - PR.translation).normalized()
    zax = Vector((0, 0, 1))
    yax = zax.cross(xax).normalized()
    zax = xax.cross(yax)
    Pk = Matrix.Translation(mid) @ Matrix((xax, yax, zax)).transposed().to_4x4()
    Mk = rest[HAND["R"]] @ (HR.inverted() @ Pk)
    _new_bone(arm, "kettlebell", Mk, HAND["R"])
    objs.append(_skinned_object(arm, "prop_kettlebell", kettlebell_mesh(k), Mk, {"kettlebell": 1.0}, [iron]))

    # band: one bone from the left fist aiming at the right fist, scaled along its length to the gap each frame
    clip = "band_pull_apart"
    X = {}
    for s_, sg in (("L", 1.0), ("R", -1.0)):
        a = math.radians(9.0)
        f = Vector((sg * math.sin(a), -math.cos(a), -0.06))
        M, Hw = held(clip, s_, f, Vector((0, 0, -1.0)), along=0.060, palm=0.012)
        X[s_] = rest[HAND[s_]].inverted() @ M                           # grip in hand-local space
    head = (rest[HAND["L"]] @ X["L"]).translation
    tail = (rest[HAND["R"]] @ X["R"]).translation
    Lr = (tail - head).length

    def aim(h, t, up_hint):
        y = (t - h).normalized()
        x = up_hint.cross(y)
        if x.length < 1e-4:
            x = Vector((0, 1, 0)).cross(y)
        x.normalize()
        z = x.cross(y)
        return Matrix((x, y, z)).transposed()
    Rb = aim(head, tail, Vector((0, 0, 1)))
    Mb_rest = Matrix.Translation(head) @ Rb.to_4x4()
    _new_bone(arm, "band", Mb_rest, HAND["L"])
    bm = bmesh.new()
    tube_between(bm, Vector((0, 0, 0)), Vector((0, Lr, 0)), 0.0075 * k, segs=6, sides=8)
    objs.append(_skinned_object(arm, "prop_band", bm, Mb_rest, {"band": 1.0}, [band_m]))
    act = bpy.data.actions[clip]
    arm.animation_data.action = act
    pb = arm.pose.bones["band"]
    pb.rotation_mode = "QUATERNION"
    a0, b0 = [int(x) for x in act.frame_range]
    for fr in range(a0, b0 + 1):
        bpy.context.scene.frame_set(fr)
        bpy.context.view_layer.update()
        gL = (arm.pose.bones[HAND["L"]].matrix @ X["L"]).translation
        gR = (arm.pose.bones[HAND["R"]].matrix @ X["R"]).translation
        R = aim(gL, gR, Vector((0, 0, 1)))
        pb.matrix = Matrix.Translation(gL) @ R.to_4x4() @ Matrix.Diagonal((1.0, (gR - gL).length / Lr, 1.0, 1.0))
        bpy.context.view_layer.update()
        pb.keyframe_insert("location", frame=fr)
        pb.keyframe_insert("rotation_quaternion", frame=fr)
        pb.keyframe_insert("scale", frame=fr)
    BAKED = {("band", clip)}

    # bench: under the hands of the incline push-up, top surface at the bench height
    clip = "incline_pushup_down"
    HL = _pose_world(arm, clip, int(bpy.data.actions[clip].frame_range[0]), HAND["L"])
    HR = _pose_world(arm, clip, int(bpy.data.actions[clip].frame_range[0]), HAND["R"])
    hy = (HL.translation.y + HR.translation.y) / 2
    # the hands rest at the near edge (first QC: the bench reached 10 cm under the body and the chest sank into it
    # at the bottom of the rep)
    Mb = Matrix.Translation((0.0, hy - 0.135 * k, ac.INCLINE_BENCH_H))
    _new_bone(arm, "bench", Mb, None)
    bm = bench_mesh(k)
    ob = _skinned_object(arm, "prop_bench", bm, Mb, {"bench": 1.0}, [pad, frame_m])
    for poly in ob.data.polygons:
        c = sum((ob.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
        poly.material_index = 0 if c.z > ac.INCLINE_BENCH_H - 0.075 else 1
    objs.append(ob)

    # ---- batch 7 (2026-11-24)
    import numpy as np
    coach = next(o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and not o.name.startswith("prop_"))
    gi = {g.index: g.name for g in coach.vertex_groups}
    hand_v = np.array([v.index for v in coach.data.vertices if sum(g.weight for g in v.groups if "Hand" in gi[g.group]) > 0.6])

    def first(clip):
        return int(bpy.data.actions[clip].frame_range[0])

    def act(clip):
        arm.animation_data.action = bpy.data.actions[clip]

    # goblet dumbbell: upright between the cupped hands, the top end under the palms (parented to the right hand)
    clip = "db_goblet_squat"
    HL = _pose_world(arm, clip, first(clip), HAND["L"])
    HR = _pose_world(arm, clip, first(clip), HAND["R"])
    mid = (HL.translation + HR.translation) / 2 + Vector((0, -0.010 * k, -0.095 * k))
    Pg = Matrix.Translation(mid) @ Matrix((Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((-1, 0, 0)))).transposed().to_4x4()
    Mg = rest[HAND["R"]] @ (HR.inverted() @ Pg)
    _new_bone(arm, "dumbbell_goblet", Mg, HAND["R"])
    bm, _ = dumbbell_mesh(k)
    ob = _skinned_object(arm, "prop_dumbbell_goblet", bm, Mg, {"dumbbell_goblet": 1.0}, [metal, rubber])
    for poly in ob.data.polygons:
        c = sum((ob.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
        poly.material_index = 1 if (Mg.inverted() @ c).x.__abs__() > 0.077 * k else 0
    objs.append(ob)

    # dip bench: behind the body, the hands on its near (front) edge
    clip = "bench_dip"
    HL = _pose_world(arm, clip, first(clip), HAND["L"])
    HR = _pose_world(arm, clip, first(clip), HAND["R"])
    hy = (HL.translation.y + HR.translation.y) / 2
    import clips_fit2 as cfit
    Md = Matrix.Translation((0.0, hy + 0.125 * k, cfit.DIP_BENCH_H))
    _new_bone(arm, "bench_dip", Md, None)
    ob = _skinned_object(arm, "prop_bench_dip", bench_mesh(k), Md, {"bench_dip": 1.0}, [pad, frame_m])
    for poly in ob.data.polygons:
        c = sum((ob.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
        poly.material_index = 0 if c.z > cfit.DIP_BENCH_H - 0.075 else 1
    objs.append(ob)

    wall_m = _material("prop_wall", (0.80, 0.80, 0.78), 0.9)
    # wall in front (wall push-up): its face where the palms touch it
    act("wall_pushup")
    co = _skin_world(coach, first("wall_pushup"))
    yf = float(co[hand_v, 1].min())
    Mw = Matrix.Translation((0.0, yf, 0.0))
    _new_bone(arm, "wall_front", Mw, None)
    objs.append(_skinned_object(arm, "prop_wall_front", wall_mesh(), Mw, {"wall_front": 1.0}, [wall_m]))
    # wall behind (wall sit): its face where the back of the pelvis / shoulder blades touch it, at the bottom of the sit
    act("wall_sit")
    fa, fb = [int(x) for x in bpy.data.actions["wall_sit"].frame_range]
    yb = -1.0
    for fr in (fa, (fa + fb) // 2):
        co = _skin_world(coach, fr)
        sel = co[:, 2] > 0.30
        yb = max(yb, float(co[sel, 1].max()))
    Mw = Matrix.Translation((0.0, yb, 0.0)) @ Matrix.Rotation(math.pi, 4, "Z")
    _new_bone(arm, "wall_back", Mw, None)
    objs.append(_skinned_object(arm, "prop_wall_back", wall_mesh(), Mw, {"wall_back": 1.0}, [wall_m]))
    arm.animation_data.action = None

    # visibility: key every prop bone in every clip
    bones = ["dumbbell_L", "dumbbell_R", "kettlebell", "band", "bench", "dumbbell_goblet", "bench_dip", "wall_front", "wall_back"]
    group = {b: b for b in bones}
    for act in bpy.data.actions:
        arm.animation_data.action = act
        a, b = [int(x) for x in act.frame_range]
        used = set(ac.PROPS_BY_CLIP.get(act.name, ()))
        for bn in bones:
            if (bn, act.name) in BAKED:
                continue
            pb = arm.pose.bones[bn]
            sc = 1.0 if group[bn] in used else HIDDEN
            pb.scale = (sc, sc, sc)
            pb.location = (0, 0, 0)
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            for fr in (a, b):
                pb.keyframe_insert("scale", frame=fr)
                pb.keyframe_insert("location", frame=fr)
                pb.keyframe_insert("rotation_quaternion", frame=fr)
    arm.animation_data.action = None
    return objs
