import os
"""Use the owner's professionally rigged coach (Tripo export, Mixamo-style skeleton with its own skin weights) instead
of MOTIONFORGE's auto-rig.

The exercise clips are still generated on the MOTIONFORGE rig (trainer_anim / mocap / IK passes). That rig is built
from this skeleton's own joint positions (joints()), so both rest poses match; transfer() then copies each frame
onto the Mixamo bones: every bone takes the world-space rotation change of its MOTIONFORGE counterpart, limbs are
re-aimed at the posed MOTIONFORGE limb so directions match exactly, and the hips carry the root motion.
"""
import math
import bpy
from mathutils import Matrix, Vector

P = "mixamorig:"


def load(path, height):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    mesh = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    arm = next(o for o in new if o.type == "ARMATURE")
    # keep the world placement the importer gave them (a parent node may carry the Y-up -> Z-up turn) before
    # dropping helper objects
    for o in (arm, mesh):
        mw = o.matrix_world.copy()
        if o.parent is not None and o.parent not in (arm, mesh):
            o.parent = None
            o.matrix_world = mw
    for o in new:
        if o not in (mesh, arm):
            bpy.data.objects.remove(o)
    if arm.animation_data:
        arm.animation_data.action = None
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg).to_mesh()
    pts = [mesh.matrix_world @ v.co for v in ev.vertices]
    mesh.evaluated_get(dg).to_mesh_clear()
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = height / (hi.z - lo.z)
    T = Matrix.Translation(Vector((-(lo.x + hi.x) / 2 * s, -(lo.y + hi.y) / 2 * s, -lo.z * s))) @ Matrix.Scale(s, 4)
    if mesh.parent is not arm:
        mesh.matrix_world = T @ mesh.matrix_world
    arm.matrix_world = T @ arm.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    for o in (arm, mesh):
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    arm.data.pose_position = "POSE"
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    arm.name, mesh.name = "coach_rig", "coach_body"
    print("rigged coach loaded: scale", round(s, 4), "bones", len(arm.data.bones), "verts", len(mesh.data.vertices))
    return arm, mesh


def joints(arm, mesh, height):
    """MOTIONFORGE joint positions (trainer_rig names) taken from the Mixamo skeleton."""
    B = arm.data.bones
    h = lambda n: Vector(B[P + n].head_local)
    t = lambda n: Vector(B[P + n].tail_local)
    J = {
        "pelvis": h("Hips"), "spine": h("Spine1"), "chest": h("Spine2"), "neck": h("Neck"), "head": h("Head"),
        "head_top": Vector((h("Head").x, h("Head").y, height)),
    }
    for s, side in (("L", "Left"), ("R", "Right")):
        J[f"shoulder_{s}"] = h(side + "Shoulder")
        J[f"upper_arm_{s}"] = h(side + "Arm")
        J[f"forearm_{s}"] = h(side + "ForeArm")
        J[f"hand_{s}"] = h(side + "Hand")
        J[f"hand_tip_{s}"] = t(side + "HandMiddle3")
        J[f"thigh_{s}"] = h(side + "UpLeg")
        J[f"shin_{s}"] = h(side + "Leg")
        J[f"foot_{s}"] = h(side + "Foot")
        J[f"toe_{s}"] = h(side + "ToeBase")
        J[f"toe_tip_{s}"] = t(side + "ToeBase")
    return J


# Mixamo bone -> (MOTIONFORGE source bone(s), re-aim direction?)
def _mapping():
    m = {"Hips": ("hips", False), "Spine": ("spine", True), "Spine1": (("spine", "chest"), True), "Spine2": ("chest", True),
         "Neck": ("neck", True), "Head": ("head", False)}
    for s, side in (("L", "Left"), ("R", "Right")):
        m.update({
            side + "Shoulder": (f"shoulder_{s}", True), side + "Arm": (f"upper_arm_{s}", True),
            side + "ForeArm": (f"forearm_{s}", True), side + "Hand": (f"hand_{s}", False),
            side + "UpLeg": (f"thigh_{s}", True), side + "Leg": (f"shin_{s}", True), side + "Foot": (f"foot_{s}", False),
            side + "ToeBase": (f"foot_{s}", False),
            side + "HandThumb1": (f"hand_{s}", False), side + "HandThumb2": (f"fingers_{s}", False),
            side + "HandThumb3": (f"fingers_{s}", False),
        })
        for f in ("Index", "Middle", "Ring", "Pinky"):
            m[f"{side}Hand{f}1"] = (f"fingers_{s}", False)
            m[f"{side}Hand{f}2"] = (f"fingertips_{s}", False)
            m[f"{side}Hand{f}3"] = (f"fingertips_{s}", False)
    return {P + k: v for k, v in m.items()}


MAP = _mapping()


def transfer(src_arm, dst_arm, act, scene, name):
    src_arm.animation_data.action = act
    a, b = [int(x) for x in act.frame_range]
    rest_s = {bn.name: bn.matrix_local.copy() for bn in src_arm.data.bones}
    rest_d = {bn.name: bn.matrix_local.copy() for bn in dst_arm.data.bones}
    order = []

    def walk(bn):
        order.append(bn)
        for c in bn.children:
            walk(c)
    for root in [bn for bn in dst_arm.data.bones if bn.parent is None]:
        walk(root)
    new = bpy.data.actions.new(name)
    new.use_fake_user = True
    if dst_arm.animation_data is None:
        dst_arm.animation_data_create()
    dst_arm.animation_data.action = new
    keys = {}
    for f in range(a, b + 1):
        scene.frame_set(f)
        ps = {pb.name: pb.matrix.copy() for pb in src_arm.pose.bones}

        def delta(src):
            if isinstance(src, tuple):
                q1 = delta(src[0]).to_quaternion()
                q2 = delta(src[1]).to_quaternion()
                if q1.dot(q2) < 0:
                    q2 = -q2
                return q1.slerp(q2, 0.5).to_matrix()
            return ps[src].to_3x3() @ rest_s[src].to_3x3().inverted()
        posed = {}
        for bn in order:
            if bn.parent is not None:
                inherit = posed[bn.parent.name] @ rest_d[bn.parent.name].inverted() @ rest_d[bn.name]
            else:
                inherit = rest_d[bn.name].copy()
            spec = MAP.get(bn.name)
            if spec is None:
                new_m = inherit
            else:
                src, aim = spec
                R = delta(src) @ rest_d[bn.name].to_3x3()
                if aim:
                    s0 = src[1] if isinstance(src, tuple) else src
                    want = Vector(ps[s0].col[1][:3]).normalized()
                    if isinstance(src, tuple):
                        want = (Vector(ps[src[0]].col[1][:3]).normalized() + want).normalized()
                    cur = Vector(R.col[1]).normalized()
                    R = cur.rotation_difference(want).to_matrix() @ R
                if bn.name.endswith("ToeBase"):
                    # toes stay flat on the floor while the heel is raised (they bend at the ball instead of pointing down)
                    fb = src_arm.data.bones[src]
                    ball_z = (ps[src].translation + Vector(ps[src].col[1][:3]).normalized() * fb.length).z
                    # (over 3.5 cm the toes snapped flat on a quick landing -- QC: curtsy lunge toe jerk ~900 m/s3)
                    u_ = max(0.0, min(1.0, (ball_z - fb.tail_local.z) / 0.06))
                    w = 1.0 - u_ * u_ * (3.0 - 2.0 * u_)
                    D = delta(src)
                    fw_ = D @ Vector((0, -1, 0))
                    flat = Matrix.Rotation(math.atan2(fw_.x, -fw_.y), 3, "Z")
                    # eased in as the foot tips toes-down (a hard switch at level snapped the toes ~50 deg in one frame
                    # whenever a foot pitched through level near the floor -- mountain climber, bird dog)
                    w *= max(0.0, min(1.0, -fw_.z / 0.25))
                    if w > 0:
                        qd, qf_ = D.to_quaternion(), flat.to_quaternion()
                        if qd.dot(qf_) < 0:
                            qf_ = -qf_
                        R = qd.slerp(qf_, w).to_matrix() @ rest_d[bn.name].to_3x3()
                if bn.parent is None:
                    loc = rest_d[bn.name].translation + (ps["hips"].translation - rest_s["hips"].translation)
                else:
                    loc = inherit.translation
                new_m = Matrix.Translation(loc) @ R.to_4x4()
            posed[bn.name] = new_m
            basis = inherit.inverted() @ new_m
            l, r, _ = basis.decompose()
            keys.setdefault(bn.name, []).append((f, r, l))
    for bname, seq in keys.items():
        pb = dst_arm.pose.bones[bname]
        pb.rotation_mode = "QUATERNION"
        prev = None
        for f, r, l in seq:
            if prev is not None and prev.dot(r) < 0:
                r = -r
            prev = r
            pb.rotation_quaternion = r
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if bn_is_root(dst_arm, bname):
                pb.location = l
                pb.keyframe_insert("location", frame=f)
    new.frame_range = (a, b)
    src_arm.animation_data.action = None
    dst_arm.animation_data.action = None
    return new


def prepare_textures(mesh, res=2048, clean_skin=False):
    """Phone-sized textures; the source roughness is near-mirror (reads as oily plastic) -> remap to skin/fabric."""
    import numpy as np
    for mat in mesh.data.materials:
        if not mat or not mat.use_nodes:
            continue
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                img = n.image
                if img.size[0] > res:
                    img.scale(res, res)
                feeds_base = any(l.to_socket.name == "Base Color" for l in n.outputs[0].links)
                if feeds_base and clean_skin:
                    import skin_cleanup
                    w, h = img.size
                    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
                    # 8-bit images hand back their stored (sRGB-encoded) values; float images are linear
                    lin = px[..., :3]
                    srgb = lin if not img.is_float else np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
                    srgb, frac = skin_cleanup.clean(srgb)
                    px[..., :3] = srgb if not img.is_float else np.where(srgb <= 0.04045, srgb / 12.92, np.power((srgb + 0.055) / 1.055, 2.4))
                    img.pixels[:] = px.ravel()
                    print("skin highlight streaks removed:", round(frac * 100, 2), "% of texture")
                feeds_rough = any(l.to_socket.name in ("Roughness",) or (l.to_node.type == "SEPARATE_COLOR") for l in n.outputs[0].links)
                if feeds_rough and img.colorspace_settings.name != "sRGB":
                    px = np.array(img.pixels[:], np.float32).reshape(-1, 4)
                    px[:, 1] = 0.45 + 0.50 * np.clip(px[:, 1], 0, 1)
                    # metallic (B): the source paints ~16 % metal over skin and fabric, which darkens them and reads as
                    # plastic on a phone (no reflections to show). Only the few genuinely metal bits (> 0.5) stay metal.
                    before = float(px[:, 2].mean())
                    px[:, 2] = np.where(px[:, 2] > 0.5, px[:, 2], 0.0)
                    img.pixels[:] = px.ravel()
                    print("roughness remapped on", img.name, "| metallic mean", round(before, 3), "->", round(float(px[:, 2].mean()), 3))
                img.pack()


def bn_is_root(arm, name):
    return arm.data.bones[name].parent is None


def fix_shorts(mesh, arm, radius=0.04, iterations=4):
    """Loose shorts: Tripo's skin weights hand the lower shorts and cargo pockets partly to the shin bones, so they
    swing out with the lower leg in a deep squat. Cloth above the knee (found by texture colour: not skin) is moved
    onto the thigh, then the pelvis/thigh weights of that cloth are blended with its spatial neighbours (the mesh is
    split at every UV seam, so neighbours are found by distance, not edges)."""
    import numpy as np
    from mathutils.kdtree import KDTree
    import skin_cleanup
    mat = mesh.data.materials[0]
    img = next(n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and any(l.to_socket.name == "Base Color" for l in n.outputs[0].links))
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[..., :3]
    uv = mesh.data.uv_layers.active.data
    nv = len(mesh.data.vertices)
    vuv = np.zeros((nv, 2))
    cnt = np.zeros(nv)
    for loop in mesh.data.loops:
        vuv[loop.vertex_index] += uv[loop.index].uv
        cnt[loop.vertex_index] += 1
    vuv /= np.maximum(cnt, 1)[:, None]
    xi = np.clip((vuv[:, 0] % 1.0) * (w - 1), 0, w - 1).astype(int)
    yi = np.clip((vuv[:, 1] % 1.0) * (h - 1), 0, h - 1).astype(int)
    col = px[yi, xi]
    hh, ss, vv = skin_cleanup._hsv(col)
    skin = (hh > 0.015) & (hh < 0.11) & (ss > 0.42) & (vv > 0.30)
    co = np.array([v.co[:] for v in mesh.data.vertices])
    B = arm.data.bones
    knee = (B[P + "LeftLeg"].head_local.z + B[P + "RightLeg"].head_local.z) / 2
    hipz = B[P + "Hips"].head_local.z
    names = [g.name for g in mesh.vertex_groups]
    gi = {n: i for i, n in enumerate(names)}
    Wt = np.zeros((nv, len(names)), np.float32)
    for v in mesh.data.vertices:
        for g in v.groups:
            Wt[v.index, g.group] = g.weight
    band = (~skin) & (co[:, 2] > knee - 0.06) & (co[:, 2] < hipz + 0.06)
    # the hands (dark gloves) hang at shorts height in the rest pose: anything on an arm bone is not shorts
    arm_cols = [i for i, n in enumerate(names) if any(k in n for k in ("Arm", "Hand", "Shoulder"))]
    band &= Wt[:, arm_cols].sum(1) < 0.02
    upper = band & (co[:, 2] > knee + 0.10)              # leave the hem round the knee to Tripo's weights
    for side in ("Left", "Right"):
        leg, up, foot = gi.get(P + side + "Leg"), gi.get(P + side + "UpLeg"), gi.get(P + side + "Foot")
        for src in (leg, foot):
            if src is None or up is None:
                continue
            Wt[upper, up] += Wt[upper, src]
            Wt[upper, src] = 0
    # the side of the shorts round the hip (pockets, flaps) rides with the pelvis more than with the thigh, so
    # it doesn't flare out when the thigh lifts or swings out
    upz = (B[P + "LeftUpLeg"].head_local.z + B[P + "RightUpLeg"].head_local.z) / 2
    hw = abs(B[P + "LeftUpLeg"].head_local.x)
    t = np.clip((co[:, 2] - (upz - 0.16)) / 0.20, 0, 1) * np.clip((np.abs(co[:, 0]) - 0.6 * hw) / (0.6 * hw), 0, 1)
    t = (t * t * (3 - 2 * t)) * band
    hips_i = gi[P + "Hips"]
    onehot = np.zeros_like(Wt)
    onehot[:, hips_i] = 1.0
    Wt = Wt * (1 - 0.7 * t[:, None]) + onehot * (0.7 * t[:, None])
    kd = KDTree(nv)
    for i, c in enumerate(co):
        kd.insert(c, i)
    kd.balance()
    idx = np.nonzero(band)[0]
    nbrs = [np.array([j for (_, j, _) in kd.find_range(co[i], radius) if band[j]] or [i]) for i in idx]
    keep = [gi[n] for n in names if n.endswith(("Hips", "UpLeg", "Spine"))]
    for _ in range(iterations):
        new = Wt.copy()
        for k, i in enumerate(idx):
            nb = nbrs[k]
            new[i, keep] = Wt[nb][:, keep].mean(0)
        Wt = new
    Wt[band] /= np.maximum(Wt[band].sum(1, keepdims=True), 1e-6)
    for n, g_i in gi.items():
        g = mesh.vertex_groups[n]
        for i in idx:
            val = float(Wt[i, g_i])
            if val > 1e-4:
                g.add([int(i)], val, "REPLACE")
            else:
                g.remove([int(i)])
    print("shorts weights fixed on", len(idx), "cloth vertices")


def strip_hand_leaks(mesh):
    """In the rest pose the hands touch the thighs, and the auto-skinning leaked small finger/hand weights onto the
    shorts/leggings there; when the arms lift those patches are dragged after the hands (fins). Any vertex that
    mostly belongs to the legs, hips or spine drops its hand/finger weights."""
    names = [g.name for g in mesh.vertex_groups]
    hand = {i for i, n in enumerate(names) if "Hand" in n}
    body = {i for i, n in enumerate(names) if n.endswith(("UpLeg", "Leg", "Hips", "Spine", "Spine1", "Foot"))}
    fixed = 0
    for v in mesh.data.vertices:
        ws = {g.group: g.weight for g in v.groups}
        if not ws:
            continue
        top = max(ws, key=ws.get)
        hw = sum(w for g, w in ws.items() if g in hand)
        if top in body and hw > 0:
            rest = sum(w for g, w in ws.items() if g not in hand)
            for g in list(ws):
                if g in hand:
                    mesh.vertex_groups[g].remove([v.index])
                else:
                    mesh.vertex_groups[g].add([v.index], ws[g] / max(rest, 1e-6), "REPLACE")
            fixed += 1
    print("hand-weight leaks removed on", fixed, "vertices")


def _enclosed(comp, bm):
    """True if the piece sits inside the rest of the body: rays from its centre in six directions all hit other
    geometry an odd number of times. Eyelashes, brows, laces and other surface parts are outside and are kept."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    ids = {f.index for f in comp}
    others = [[v.co.copy() for v in f.verts] for f in bm.faces if f.index not in ids]
    verts, polys = [], []
    for fv in others:
        polys.append(list(range(len(verts), len(verts) + len(fv)))); verts.extend(fv)
    tree = BVHTree.FromPolygons(verts, polys)
    c = sum((f.calc_center_median() for f in comp), Vector()) / len(comp)
    for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((0, 0, 1)), Vector((0, 0, -1))):
        hits, p = 0, c.copy()
        for _ in range(50):
            loc, _n, _i, _d = tree.ray_cast(p, d)
            if loc is None:
                break
            hits += 1; p = loc + d * 1e-5
        if hits % 2 == 0:
            return False
    return True


def repair_mesh(mesh):
    """Minimal, shape-preserving repair of the imported coach mesh (see docs/MESH_INSPECTION.md):
    - delete tiny disconnected fragments (< 40 faces) that sit fully inside the body (surface parts are kept),
    - close pinholes: boundary loops of <= 8 edges that are real holes (not UV-seam splits), using only the existing
      vertices, so no vertex moves; the new corners take UVs from neighbouring faces, skin weights are unchanged.
    Normals are left as imported (consistent winding, outward, custom split normals kept)."""
    import bmesh
    from collections import defaultdict
    me = mesh.data
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    key = lambda co: (round(co.x, 6), round(co.y, 6), round(co.z, 6))
    # fragments: connectivity through shared positions (seam splits count as connected)
    pos_faces = defaultdict(list)
    for f in bm.faces:
        for v in f.verts:
            pos_faces[key(v.co)].append(f)
    seen, frags = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        st, comp = [f], []
        while st:
            g = st.pop()
            if g.index in seen:
                continue
            seen.add(g.index); comp.append(g)
            for v in g.verts:
                for h in pos_faces[key(v.co)]:
                    if h.index not in seen:
                        st.append(h)
        if len(comp) < 40 and _enclosed(comp, bm):
            frags.append(comp)
    dead = {f for comp in frags for f in comp}
    if dead:
        bmesh.ops.delete(bm, geom=list(dead), context="FACES")
    # pinholes: boundary edges with no coincident partner edge are real holes
    bnd = [e for e in bm.edges if e.is_boundary]
    ekey = lambda e: tuple(sorted((key(e.verts[0].co), key(e.verts[1].co))))
    count = defaultdict(int)
    for e in bnd:
        count[ekey(e)] += 1
    holes = [e for e in bnd if count[ekey(e)] == 1]
    adj = defaultdict(list)
    for e in holes:
        a, b = key(e.verts[0].co), key(e.verts[1].co)
        adj[a].append((b, e)); adj[b].append((a, e))
    used, filled = set(), 0
    for e0 in holes:
        if e0 in used:
            continue
        # walk the loop by positions
        start = key(e0.verts[0].co); cur, prev_e = key(e0.verts[1].co), e0
        ring = [start]; edges = [e0]; ok = True
        while cur != start:
            ring.append(cur)
            nxt = [(p, e) for p, e in adj[cur] if e is not prev_e]
            if len(nxt) != 1 or len(ring) > 8:
                ok = False; break
            cur, prev_e = nxt[0]; edges.append(prev_e)
        used.update(edges)
        if not ok or len(ring) < 3:
            continue
        # one existing vertex per ring position (from the hole edges themselves)
        pick = {}
        for e in edges:
            for v in e.verts:
                pick.setdefault(key(v.co), v)
        verts = [pick[k] for k in ring]
        try:
            f = bm.faces.new(verts)
        except ValueError:
            continue
        if f.calc_area() < 1e-9:            # a sliver crack, not a hole: nothing to close
            bm.faces.remove(f)
            continue
        # winding opposite to the neighbour along the first hole edge
        ne = edges[0]; nf = ne.link_faces[0] if ne.link_faces[0] is not f else ne.link_faces[1]
        def fwd(face):
            vs = list(face.verts); i = vs.index(ne.verts[0]) if ne.verts[0] in vs else None
            return None if i is None else vs[(i + 1) % len(vs)] == ne.verts[1]
        if fwd(f) is not None and fwd(f) == fwd(nf):
            f.normal_flip()
        f.material_index = nf.material_index; f.smooth = True
        if uv:
            for l in f.loops:
                src = next((ll for ll in l.vert.link_loops if ll.face is not f), None)
                if src:
                    l[uv].uv = src[uv].uv.copy()
        filled += 1
    bm.to_mesh(me); bm.free(); me.update()
    print(f"mesh repair: removed {len(frags)} fragment(s) ({len(dead)} faces), closed {filled} pinholes")


def floor_contact(arm, mesh, scene, names):
    """Per frame, move the hips vertically so the lowest point of the shoes rests on the floor (z = rest-pose sole height).
    Measured on the real skinned mesh, so squats lower the body instead of lifting the feet."""
    import numpy as np
    gi = {g.index: g.name for g in mesh.vertex_groups}
    feet = []
    for v in mesh.data.vertices:
        w = sum(g.weight for g in v.groups if any(k in gi[g.group] for k in ("Foot", "ToeBase", "Toe_End")))
        if w > 0.6:
            feet.append(v.index)
    feet = np.array(feet)
    co = np.empty(len(mesh.data.vertices) * 3, np.float32)
    mesh.data.vertices.foreach_get("co", co)
    ground = float(co.reshape(-1, 3)[feet, 2].min())
    hips = next(pb for pb in arm.pose.bones if pb.parent is None)
    rest_inv = arm.data.bones[hips.name].matrix_local.to_3x3().inverted()
    worst = 0.0
    for n in names:
        act = bpy.data.actions[n]
        arm.animation_data.action = act
        a, b = [int(x) for x in act.frame_range]
        dzs = []
        for f in range(a, b + 1):
            scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            ev = mesh.evaluated_get(dg)
            m2 = ev.to_mesh()
            m2.vertices.foreach_get("co", co)
            ev.to_mesh_clear()
            dzs.append(ground - float(co.reshape(-1, 3)[feet, 2].min()))
        if CONTACTS.get(n, ("",))[0] == "hands" and len(dzs) > 8:
            # hands on the floor: the body is moved smoothly (the lowest shoe point hops between ball, toe and the other
            # foot as a leg drives; following it frame by frame jerked the shoulders, and the pinned arms whipped the
            # elbows -- QC: forearm jitter up to 6 cm a frame in the mountain climber)
            ker = (1, 2, 3, 4, 3, 2, 1)
            h_ = len(ker) // 2
            sm = []
            for i in range(len(dzs)):
                acc = wsum = 0.0
                for j, kw in enumerate(ker):
                    ii = min(len(dzs) - 1, max(0, i + j - h_))
                    acc += kw * dzs[ii]; wsum += kw
                sm.append(acc / wsum)
            sm[0], sm[-1] = dzs[0], dzs[-1]
            dzs = sm
        elif len(dzs) > 8:
            # every other clip: the lowest shoe point hands over between the feet (or heel and toe) as a foot lifts or
            # lands, and following it frame by frame stepped the whole body by millimetres (QC: foot jerk ~1300 m/s3 in
            # the glute kickback). The largest need nearby (nothing sinks), then a short ease; ends exact (loops close).
            mx = [max(dzs[max(0, i - 2):i + 3]) for i in range(len(dzs))]
            ker = (1, 2, 3, 2, 1)
            sm = [sum(kw * mx[min(len(mx) - 1, max(0, i + j - 2))] for j, kw in enumerate(ker)) / 9.0 for i in range(len(mx))]
            sm[0], sm[-1] = dzs[0], dzs[-1]
            dzs = sm
        for f, dz in zip(range(a, b + 1), dzs):
            scene.frame_set(f)
            hips.location = hips.location + rest_inv @ Vector((0, 0, dz))
            hips.keyframe_insert("location", frame=f)
        worst = max(worst, max(abs(d) for d in dzs))
        if n.startswith("pushup_"):
            hands = np.array([v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if "Hand" in gi[g.group]) > 0.6])
            gaps = []
            for f in (a, b):
                scene.frame_set(f)
                dg = bpy.context.evaluated_depsgraph_get()
                ev = mesh.evaluated_get(dg)
                m2 = ev.to_mesh()
                m2.vertices.foreach_get("co", co)
                ev.to_mesh_clear()
                gaps.append(round(float(co.reshape(-1, 3)[hands, 2].min()) - ground, 3))
            print("  ", n, "palm height above the floor at first / last frame:", gaps)
    arm.animation_data.action = None
    print("floor contact on the rigged mesh: feet verts", len(feet), "largest correction", round(worst, 3), "m")


def finger_pose(arm, amount):
    """Finger and thumb rotations (pose-bone basis quaternions) for a hand closed by `amount`: 0 open, ~0.25 relaxed,
    1 a closed fist with the thumb folded across the front of the index and middle fingers.
    Solved from the rest pose itself (T-pose, palms down), so it does not depend on bone roll conventions."""
    from mathutils import Quaternion
    out = {}
    bones = arm.data.bones
    down = Vector((0, 0, -1))
    back = Vector((0, 1, 0))
    curl = {1: 82.0, 2: 98.0, 3: 62.0}
    spread_in = {"Index": 4.0, "Middle": 0.0, "Ring": -4.0, "Pinky": -9.0}

    def local(bn, axis, deg):
        r = bones[bn].matrix_local.to_3x3()
        return Quaternion((r.inverted() @ axis).normalized(), math.radians(deg))
    for side in ("Left", "Right"):
        hand = bones[P + side + "Hand"]
        mid = bones[P + side + "HandMiddle1"]
        d_hand = (Vector(mid.head_local) - Vector(hand.head_local)).normalized()
        for fn in ("Index", "Middle", "Ring", "Pinky"):
            for j in (1, 2, 3):
                bn = f"{P}{side}Hand{fn}{j}"
                b = bones[bn]
                d = (Vector(b.tail_local) - Vector(b.head_local)).normalized()
                q = local(bn, d.cross(down), curl[j] * amount)
                if j == 1:                                   # knuckles close up as the fist forms
                    q = local(bn, down, spread_in[fn] * amount * (1 if side == "Left" else -1)) @ q
                out[bn] = q
        t1, t2, t3 = (f"{P}{side}HandThumb{j}" for j in (1, 2, 3))
        t = (Vector(bones[t1].tail_local) - Vector(bones[t1].head_local)).normalized()
        flex = t.cross(back)                                  # swings the thumb across the palm toward the little finger
        # thumb 1: drop under the palm (opposition), then start to fold across
        out[t1] = local(t1, flex, 22.0 * amount) @ local(t1, d_hand * (1 if side == "Left" else -1), THUMB_OPPOSE * amount)
        out[t2] = local(t2, flex, 38.0 * amount)
        out[t3] = local(t3, flex, 58.0 * amount)
    return out


THUMB_OPPOSE = 48.0


def key_fingers(arm, scene, grip_for):
    """Keys finger_pose on every frame of every clip; grip_for(clip name) gives the amount of closure."""
    for act in bpy.data.actions:
        arm.animation_data.action = act
        a, b = [int(x) for x in act.frame_range]
        pose = finger_pose(arm, grip_for(act.name))
        for bn, q in pose.items():
            pb = arm.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            for f in range(a, b + 1):
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


# ---------------------------------------------------------------------------------------------- floor contacts
# The clips are authored on MOTIONFORGE's rig and carried over by rotation, so where the real coach's skin meets the
# floor can differ from the plan (thicker hands, knees, back of the head). This pass works on the real skinned mesh:
#   kneel  — knees rest on the floor (hips move vertically), then planted hands are pinned to the floor
#   hands  — planted hands are pinned: palm on the floor, wrist held in place (no sliding, no hovering, no sinking)
#   back   — lying on the back: the head is tucked just enough that it never sinks into the floor
#   prone  — lying face down: belly / thighs rest on the floor, head clear
# clips in which a hand leaves the floor on purpose (the pin lets go smoothly); in every other contact clip the hands
# stay planted the whole time
LIFTING_HANDS = ("bird_dog", "shoulder_taps")
KNEEL_FOOT_SMOOTH = True        # kneeling feet: measure the needed turn per frame, apply it eased over time
CONTACTS = {
    "cat_cow": ("kneel",), "bird_dog": ("kneel",), "knee_pushup_down": ("kneel",), "knee_pushup_up": ("kneel",),
    "plank_hold": ("hands",), "mountain_climber_slow": ("hands",), "pushup_down": ("hands",), "pushup_up": ("hands",),
    "glute_bridge": ("bridge",), "dead_bug": ("back",), "superman": ("prone",),
    # batch 7 (clips_fit2.py)
    "crunch": ("bridge",), "heel_taps": ("bridge",), "db_floor_press": ("bridge",), "single_leg_bridge": ("bridge",),
    "reverse_crunch": ("back",), "toe_taps": ("back",),
    "high_plank": ("hands",), "bear_hold": ("hands",),
    # (shoulder_taps: not pinned -- releasing the pin as a hand lifts jolted the elbow 7 cm in a frame; the authored hands
    # stay put on their own)
    "donkey_kick": ("kneel",), "fire_hydrant": ("kneel",), "childs_pose": ("kneel",),
}


def _regions(mesh):
    import numpy as np
    gi = {g.index: g.name for g in mesh.vertex_groups}
    keys = {"footL": ("LeftFoot", "LeftToe"), "footR": ("RightFoot", "RightToe"), "shin": ("LeftLeg", "RightLeg"), "thigh": ("UpLeg",),
            "handL": ("LeftHand",), "handR": ("RightHand",), "farm": ("ForeArm",), "head": ("Head", "Neck"), "torso": ("Spine", "Hips", "Shoulder")}
    out = {}
    for v in mesh.data.vertices:
        if not v.groups:
            continue
        n = gi[max(v.groups, key=lambda g: g.weight).group]
        for k, ks in keys.items():
            if any(x in n for x in ks) and not (k == "torso" and "Leg" in n):
                out.setdefault(k, []).append(v.index)
                break
    return {k: np.array(v) for k, v in out.items()}


def _skin_z(mesh):
    import numpy as np
    bpy.context.view_layer.update()
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(mesh.matrix_world)
    return (M[:3, :3] @ co.T).T + M[:3, 3]


def _key(pb, loc=False):
    pb.keyframe_insert("rotation_quaternion")
    if loc:
        pb.keyframe_insert("location")


def _set_world(arm, pb, Mw):
    pb.matrix = arm.matrix_world.inverted() @ Mw
    # only the rotation (and the root's location) is keyed and exported: rounding left a little scale / offset on each
    # assignment that was never keyed, so it piled up across clips (male left hand at 1.4 x 1.7 x 0.46 by the end) and
    # the contact passes measured a distorted arm while the export reset it -- QC: male plank hand 3 cm in the floor
    pb.scale = (1.0, 1.0, 1.0)
    if pb.parent is not None:
        pb.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def _world(arm, pb):
    return arm.matrix_world @ pb.matrix


def _rotate_about(arm, pb, axis, angle):
    Mw = _world(arm, pb)
    t = Mw.translation.copy()
    R = Matrix.Rotation(angle, 4, axis.normalized())
    _set_world(arm, pb, Matrix.Translation(t) @ R @ Matrix.Translation(-t) @ Mw)


def _two_bone(arm, side, target, limb="arm"):
    """Moves the wrist (or ankle) of `side` to `target` (world): shoulder (hip) fixed, elbow (knee) kept in its bend
    plane, hand (foot) keeps its world orientation."""
    S_ = "Left" if side == "L" else "Right"
    names = ("Arm", "ForeArm", "Hand") if limb == "arm" else ("UpLeg", "Leg", "Foot")
    ua, fa, hd = (arm.pose.bones[P + S_ + n] for n in names)
    hand_rot = _world(arm, hd).to_3x3().copy()
    Sh, El, Wr = _world(arm, ua).translation, _world(arm, fa).translation, _world(arm, hd).translation
    l1, l2 = (El - Sh).length, (Wr - El).length
    to_t = target - Sh
    d = min(max(to_t.length, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9995)
    dirT = to_t.normalized()
    n = (El - Sh).cross(Wr - Sh)
    if n.length < 1e-6:
        n = Vector((1, 0, 0))
    n.normalize()
    cosA = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    A = math.acos(cosA)
    # of the two elbow solutions in the bend plane, keep the one nearest the current elbow (never flips)
    cands = [Sh + (Matrix.Rotation(sg * A, 3, n) @ dirT) * l1 for sg in (1.0, -1.0)]
    E_new = min(cands, key=lambda c: (c - El).length)
    W_new = Sh + dirT * d
    r1 = (El - Sh).rotation_difference(E_new - Sh).to_matrix().to_4x4()
    _set_world(arm, ua, Matrix.Translation(Sh) @ r1 @ Matrix.Translation(-Sh) @ _world(arm, ua))
    E2, W2 = _world(arm, fa).translation, _world(arm, hd).translation
    r2 = (W2 - E2).rotation_difference(W_new - E2).to_matrix().to_4x4()
    _set_world(arm, fa, Matrix.Translation(E2) @ r2 @ Matrix.Translation(-E2) @ _world(arm, fa))
    Wt = _world(arm, hd).translation
    _set_world(arm, hd, Matrix.Translation(Wt) @ hand_rot.to_4x4())
    for pb in (ua, fa, hd):
        _key(pb)


def smooth_(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def settle_contacts(arm, mesh, scene, names):
    """See CONTACTS. Prints, per clip, the worst remaining penetration and hand drift."""
    import numpy as np
    R = _regions(mesh)
    hips = next(pb for pb in arm.pose.bones if pb.parent is None)
    neck, head = arm.pose.bones[P + "Neck"], arm.pose.bones[P + "Head"]
    for n in names:
        mode = CONTACTS.get(n)
        if not mode:
            continue
        mode = mode[0]
        act = bpy.data.actions[n]
        arm.animation_data.action = act
        a, b = [int(x) for x in act.frame_range]
        lock = {"L": None, "R": None}
        foot_need = {"L": {}, "R": {}}
        home = {"L": None, "R": None}       # where each hand first planted: it plants there again (loops close exactly)
        land = {"L": a, "R": a}
        worst = 0.0
        # the hands' authored resting height (after the whole-body drop below): the planted weight fades out from just
        # above it. Fading over 4-9 cm instead held a lifting hand on the floor for its first 4 cm and then let it
        # catch up in a few frames -- a visible pop every time a hand left or reached the floor (bird dog, climbers).
        rest = {"L": 9.0, "R": 9.0}
        # lying on the back: the whole clip moves by one constant so the back rests on the floor (QC: the male coach's
        # thicker back sank 4 cm into it; a per-frame shift would jitter as the limbs move)
        back_shift = 0.0
        if mode == "back":
            lows = []
            for f in range(a, b + 1):
                scene.frame_set(f)
                lows.append(_skin_z(mesh)[R["torso"], 2].min())
            back_shift = -min(lows)
        drops = {}
        auth = {"L": {}, "R": {}}
        # on the back with the feet planted: how far the body must rise so the back never sinks into the floor, smoothed
        # over time (lifting it per frame only where it sank popped the whole body up and down -- QC: knee jerk spikes
        # of ~2000 m/s3 in the crunch, heel taps and glute bridge)
        bridge_lift = {}
        if mode == "bridge":
            raw = []
            for f in range(a, b + 1):
                scene.frame_set(f)
                raw.append(max(0.0, -float(_skin_z(mesh)[R["torso"], 2].min())))
            mx = [max(raw[max(0, i - 4):i + 5]) for i in range(len(raw))]          # cover every frame's need...
            ker = (1, 2, 3, 4, 3, 2, 1)
            sm = [sum(kw * mx[min(len(mx) - 1, max(0, i + j - 3))] for j, kw in enumerate(ker)) / 16.0 for i in range(len(mx))]
            sm[0], sm[-1] = mx[0], mx[-1]                                           # ...then ease (ends exact: loops close)
            bridge_lift = {f: v for f, v in zip(range(a, b + 1), sm)}
        reach_raw, reach_drop = [], {}
        if mode in ("kneel", "hands", "prone"):
            raw = []
            for f in range(a, b + 1):
                scene.frame_set(f)
                z = _skin_z(mesh)
                ref = {"kneel": ("shin", "thigh"), "prone": ("torso", "thigh")}.get(mode)
                drop = min(z[R[k], 2].min() for k in ref) if ref else 0.0
                raw.append(drop)
                if mode == "hands":
                    # how far each arm would have to stretch past 98.5 % of its length to put its palm on the floor (the
                    # deforming arms are shorter than the authoring rig's: in the mountain climber the left arm locked
                    # straight and the hand left the floor -- QC)
                    need = 0.0
                    for s in ("L", "R"):
                        S_ = "Left" if s == "L" else "Right"
                        ua_, fa_, hd_ = (arm.pose.bones[P + S_ + nm] for nm in ("Arm", "ForeArm", "Hand"))
                        Sh_, El_, Wr_ = (_world(arm, x).translation for x in (ua_, fa_, hd_))
                        Wf = Wr_ - Vector((0, 0, z[R["hand" + s], 2].min()))
                        need = max(need, (Wf - Sh_).length - 0.985 * ((El_ - Sh_).length + (Wr_ - El_).length))
                    reach_raw.append(max(0.0, need))
                if mode != "prone":
                    for s in ("L", "R"):
                        rest[s] = min(rest[s], z[R["hand" + s], 2].min() - drop)
                        hb = arm.pose.bones[P + ("Left" if s == "L" else "Right") + "Hand"]
                        auth[s][f] = (_world(arm, hb).translation.copy(), z[R["hand" + s], 2].min() - drop)
            # The whole-body drop that puts the knees (belly) on the floor is smoothed over a few frames: the lowest point
            # hops from one knee to the other as a leg leaves or lands, and following it frame by frame jolted the whole
            # body (QC: male bird dog). Ends kept exact so the loop still closes.
            if len(raw) > 8:
                ker = (1, 2, 3, 4, 3, 2, 1)
                sm = [sum(kw * raw[min(len(raw) - 1, max(0, i + j - 3))] for j, kw in enumerate(ker)) / 16.0 for i in range(len(raw))]
                sm[0], sm[-1] = raw[0], raw[-1]
                raw = sm
            drops = {f: d for f, d in zip(range(a, b + 1), raw)}
            if reach_raw and max(reach_raw) > 0.0005:
                mx = [max(reach_raw[max(0, i - 4):i + 5]) for i in range(len(reach_raw))]
                ker = (1, 2, 3, 4, 3, 2, 1)
                sm = [sum(kw * mx[min(len(mx) - 1, max(0, i + j - 3))] for j, kw in enumerate(ker)) / 16.0 for i in range(len(mx))]
                sm[0], sm[-1] = mx[0], mx[-1]
                reach_drop = {f: v * 1.25 for f, v in zip(range(a, b + 1), sm)}
            # a hand's resting height is where it spends most of its time on the floor (25th percentile), not its single
            # lowest frame: a brief authored dip 1.5 cm into the floor made the male bird dog's resting right hand count as
            # half-lifted, so the pin held it 2.5 cm up the whole clip -- QC
            if mode != "prone":
                import numpy as np
                for s in ("L", "R"):
                    if auth[s]:
                        rest[s] = float(np.percentile([h for _, h in auth[s].values()], 25))
                    # never below the floor: a negative resting height made the capped correction below *raise* the hand
                    # a few mm on each of its three solver passes (male bird dog right hand held 2-2.5 cm up -- QC)
                    rest[s] = max(0.0, rest[s])
        # A lifted hand is steered in the air so that it comes down exactly where it first stood (the retargeted arm lands
        # a few cm off on the male coach; sliding it back afterwards was visible). The steer is zero at the top of the
        # reach and full at lift-off / touch-down, so the hand's path stays smooth.
        steer = {"L": {}, "R": {}}
        if n in LIFTING_HANDS:
            for s in ("L", "R"):
                fr_ = sorted(auth[s])
                if not fr_:
                    continue
                down = [f for f in fr_ if auth[s][f][1] <= rest[s] + 0.008]
                if not down:
                    continue
                home0 = auth[s][down[0]][0]
                dset = set(down)
                for f in fr_:
                    if f in dset:
                        continue
                    f0 = max([d for d in down if d < f], default=None)
                    f1 = min([d for d in down if d > f], default=None)
                    o0 = (home0 - auth[s][f0][0]) if f0 is not None else None
                    o1 = (home0 - auth[s][f1][0]) if f1 is not None else None
                    if o0 is None: o0 = o1
                    if o1 is None: o1 = o0
                    u = 0.5 if f0 is None or f1 is None else (f - f0) / float(f1 - f0)
                    off = o0.lerp(o1, smooth_(u))
                    h = auth[s][f][1] - rest[s]
                    w_air = 1.0 - smooth_(h / 0.06)
                    steer[s][f] = Vector((off.x * w_air, off.y * w_air, 0.0))
        for f in range(a, b + 1):
            scene.frame_set(f)
            z = _skin_z(mesh)
            # whole-body vertical: knees / belly on the floor
            ref = {"kneel": ("shin", "thigh"), "prone": ("torso", "thigh")}.get(mode)
            if ref:
                low = drops.get(f, min(z[R[k], 2].min() for k in ref))
                Mw = _world(arm, hips)
                _set_world(arm, hips, Matrix.Translation(Vector((0, 0, -low))) @ Mw)
                _key(hips, loc=True)
                z = _skin_z(mesh)
            # plank: where an arm would lock, the body tips down about the toes (as a real plank does) by the smoothed need
            if mode == "hands" and reach_drop.get(f, 0.0) > 0.0005:
                balls = [_world(arm, arm.pose.bones[P + sd + "Foot"]).translation.copy() for sd in ("Left", "Right")]
                Pv = (balls[0] + balls[1]) / 2
                Sm_ = sum((_world(arm, arm.pose.bones[P + sd + "Arm"]).translation for sd in ("Left", "Right")), Vector()) / 2
                v_ = Sm_ - Pv
                hlen = max(0.2, Vector((v_.x, v_.y)).length)
                ax_ = v_.cross(Vector((0, 0, 1))).normalized()
                th_ = math.atan2(reach_drop[f], hlen)
                _set_world(arm, hips, Matrix.Translation(Pv) @ Matrix.Rotation(-th_, 4, ax_) @ Matrix.Translation(-Pv) @ _world(arm, hips))
                _key(hips, loc=True)
                z = _skin_z(mesh)
            # kneeling: the tops of the feet rest on the floor instead of sinking into it
            if mode == "kneel":
                for s in ("L", "R"):
                    fb = arm.pose.bones[P + ("Left" if s == "L" else "Right") + "Foot"]
                    fz = z[R["foot" + s], 2].min()
                    ax = _world(arm, fb).to_3x3().col[0]
                    if fz < -0.002 and not KNEEL_FOOT_SMOOTH:
                        # the smallest turn that lifts the foot clear, found by bisection (whole 2-degree steps made the
                        # correction jump between frames -- QC: toe jerk ~4000 m/s3 in the fire hydrant / donkey kick)
                        step = math.radians(2.0)
                        _rotate_about(arm, fb, ax, step)
                        up = _skin_z(mesh)[R["foot" + s], 2].min()
                        _rotate_about(arm, fb, ax, -step)
                        sign = 1.0 if up > fz else -1.0
                        lo_, hi_ = 0.0, math.radians(40.0)
                        done = 0.0
                        for _ in range(12):
                            mid = 0.5 * (lo_ + hi_)
                            _rotate_about(arm, fb, ax, sign * (mid - done))
                            done = mid
                            if _skin_z(mesh)[R["foot" + s], 2].min() < -0.002:
                                lo_ = mid
                            else:
                                hi_ = mid
                        _rotate_about(arm, fb, ax, sign * (hi_ - done))
                        fz = _skin_z(mesh)[R["foot" + s], 2].min()
                    if KNEEL_FOOT_SMOOTH:
                        need = 0.0
                        if fz < -0.002:
                            step = math.radians(2.0)
                            _rotate_about(arm, fb, ax, step)
                            up = _skin_z(mesh)[R["foot" + s], 2].min()
                            _rotate_about(arm, fb, ax, -step)
                            sign = 1.0 if up > fz else -1.0
                            lo_, hi_ = 0.0, math.radians(40.0)
                            done = 0.0
                            for _ in range(12):
                                mid = 0.5 * (lo_ + hi_)
                                _rotate_about(arm, fb, ax, sign * (mid - done))
                                done = mid
                                if _skin_z(mesh)[R["foot" + s], 2].min() < -0.002:
                                    lo_ = mid
                                else:
                                    hi_ = mid
                            _rotate_about(arm, fb, ax, -sign * done)          # measured only; applied smoothed below
                            need = sign * hi_
                        foot_need[s][f] = need
                    _key(fb)
                    worst = max(worst, max(0.0, -fz))
                z = _skin_z(mesh)
            # planted hands: pinned to one spot, palm on the floor
            if mode in ("kneel", "hands"):
                for s in ("L", "R"):
                    hz = z[R["hand" + s], 2].min()
                    hd = arm.pose.bones[P + ("Left" if s == "L" else "Right") + "Hand"]
                    # planted weight: full on the floor, fading out smoothly as the hand lifts (no pop when it leaves or lands)
                    if n in LIFTING_HANDS:
                        u_ = max(0.0, min(1.0, (hz - rest[s] - 0.006) / 0.045))
                        wgt = 1.0 - u_ * u_ * (3.0 - 2.0 * u_)
                    else:
                        wgt = 1.0                                  # these hands never leave the floor
                    if wgt <= 0.0:
                        lock[s] = None
                        continue
                    W = _world(arm, hd).translation.copy()
                    # where the hand stands is fixed only once it is really down (for a landing hand: within 8 mm of its
                    # resting height). Fixing it while still 5 cm up pulled the descending hand sideways to that spot
                    # and then let it carry on -- a visible double move on the male coach.
                    if lock[s] is None and (n not in LIFTING_HANDS or hz <= rest[s] + 0.008):
                        lock[s] = W.copy()
                        if n in LIFTING_HANDS and home[s] is not None:
                            lock[s] = Vector((home[s].x, home[s].y, W.z))
                        land[s] = f
                        if home[s] is None:
                            home[s] = W.copy()
                    anchor = lock[s] if lock[s] is not None else W + steer[s].get(f, Vector((0, 0, 0)))
                    if lock[s] is not None and home[s] is not None and (Vector((home[s].x, home[s].y)) - Vector((lock[s].x, lock[s].y))).length < 0.06:
                        # a re-planted hand creeps back to where it first stood over ~0.8 s while it bears weight (snapping
                        # it there made the hand jump 3.5 cm on the male coach; leaving it made the loop jump)
                        anchor = lock[s].lerp(home[s], smooth_((f - land[s]) / 24.0))
                    for _ in range(3):
                        # the height correction stops growing a few mm above the resting level: it removes sinking or
                        # hovering of a planted hand but never holds back a hand that is being lifted on purpose
                        full = Vector((anchor.x, anchor.y, W.z - (min(hz, rest[s] + 0.006) if n in LIFTING_HANDS else hz)))
                        tgt = W.lerp(full, wgt)
                        if (tgt - W).length < 0.0015:
                            break
                        _two_bone(arm, s, tgt)
                        z = _skin_z(mesh)
                        hz = z[R["hand" + s], 2].min()
                        W = _world(arm, hd).translation.copy()
                    if os.environ.get("MF_DEBUG_PIN") == n and f % 12 == 0:
                        print("PINDBG", n, f, s, "hz %.4f rest %.4f wgt %.3f lock %s" % (hz, rest[s], wgt, lock[s] is not None))
                    if wgt >= 1.0:
                        worst = max(worst, abs(hz))
            # bridge: shoulders, arms and back rest on the floor (never in it); the planted feet follow down onto the floor
            if mode == "bridge":
                lift = bridge_lift.get(f, 0.0)
                if lift > 0.0005:
                    _set_world(arm, hips, Matrix.Translation(Vector((0, 0, lift))) @ _world(arm, hips))
                    _key(hips, loc=True)
                    z = _skin_z(mesh)
                for s in ("L", "R"):
                    fz = z[R["foot" + s], 2].min()
                    # planted feet go onto the floor; the pull fades out between 0.5 and 2.5 cm above it, so a foot lifted
                    # on purpose (single-leg bridge) is left alone and nothing switches on or off from one frame to the next
                    wgt = 1.0 if fz <= 0.005 else max(0.0, 1.0 - smooth_((fz - 0.005) / 0.02))
                    if abs(fz) > 0.0015 and wgt > 0.0:
                        fb = arm.pose.bones[P + ("Left" if s == "L" else "Right") + "Foot"]
                        A = _world(arm, fb).translation.copy()
                        _two_bone(arm, s, A - Vector((0, 0, fz * wgt)), limb="leg")
                z = _skin_z(mesh)
            if mode == "back" and abs(back_shift) > 0.002:
                _set_world(arm, hips, Matrix.Translation(Vector((0, 0, back_shift))) @ _world(arm, hips))
                _key(hips, loc=True)
                z = _skin_z(mesh)
            # the back of the head never sinks into the floor
            if mode in ("back", "prone", "bridge"):
                L_ = _world(arm, arm.pose.bones[P + "LeftShoulder"]).translation
                Rr = _world(arm, arm.pose.bones[P + "RightShoulder"]).translation
                axis = L_ - Rr
                hz = z[R["head"], 2].min()
                step = math.radians(2.5)
                sign = None
                tries = 0
                while hz < 0.003 and tries < 14:
                    tries += 1
                    if sign is None:                               # find which way lifts the head
                        _rotate_about(arm, neck, axis, step)
                        up = _skin_z(mesh)[R["head"], 2].min()
                        _rotate_about(arm, neck, axis, -step)
                        sign = 1.0 if up > hz else -1.0
                    _rotate_about(arm, neck, axis, sign * step * 0.4)
                    _rotate_about(arm, head, axis, sign * step * 0.6)
                    hz = _skin_z(mesh)[R["head"], 2].min()
                _key(neck)
                _key(head)
                worst = max(worst, max(0.0, -hz))
                if mode == "prone":
                    z = _skin_z(mesh)
            if mode == "prone":
                low = min(z[R[k], 2].min() for k in ("torso", "thigh"))
                if low < 0:
                    _set_world(arm, hips, Matrix.Translation(Vector((0, 0, -low))) @ _world(arm, hips))
                    _key(hips, loc=True)
        if mode == "kneel" and KNEEL_FOOT_SMOOTH and any(foot_need[s_] for s_ in ("L", "R")):
            # the turns that keep the tops of the feet out of the floor, eased over time: frame by frame they switched
            # on and off as a foot came down (QC: toe jerk 3000-5000 m/s3 in the fire hydrant / donkey kick)
            for s_ in ("L", "R"):
                fr_ = sorted(foot_need[s_])
                v = [foot_need[s_][f_] for f_ in fr_]
                if not any(abs(x) > 1e-6 for x in v):
                    continue
                sgn = 1.0 if sum(v) >= 0 else -1.0
                mag = [abs(x) for x in v]
                mx = [max(mag[max(0, i - 3):i + 4]) for i in range(len(mag))]
                ker = (1, 2, 3, 4, 3, 2, 1)
                sm = [sum(kw * mx[min(len(mx) - 1, max(0, i + j - 3))] for j, kw in enumerate(ker)) / 16.0 for i in range(len(mx))]
                sm[0], sm[-1] = mx[0], mx[-1]
                fb = arm.pose.bones[P + ("Left" if s_ == "L" else "Right") + "Foot"]
                for f_, ang in zip(fr_, sm):
                    if ang <= 1e-6:
                        continue
                    scene.frame_set(f_)
                    ax = _world(arm, fb).to_3x3().col[0]
                    _rotate_about(arm, fb, ax, sgn * ang)
                    _key(fb)
        print(f"  contacts {n}: {mode}, worst remaining {worst * 100:.1f} cm", flush=True)
    arm.animation_data.action = None


def _find_fcurve(act, path, index):
    """F-curve lookup for both legacy and layered (Blender 4.4+) actions."""
    if hasattr(act, "fcurves"):
        return act.fcurves.find(path, index=index)
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                fc = cb.fcurves.find(path, index=index)
                if fc is not None:
                    return fc
    return None


def smooth_toes(arm, passes=5):
    """Low-pass the toe bones' keys in every clip ([1 2 1] / 4, a few passes; first and last keys kept so loops and
    down/up pairs still join). The toes flatten and lift with the ball's height above the floor, which can change a lot
    between two frames when a foot lands or leaves (QC: toes snapping 35-50 deg in one frame -- mountain climber, bird
    dog). Planted toes are constant, so they stay exactly where they are."""
    from mathutils import Quaternion
    for act in bpy.data.actions:
        for pb in arm.pose.bones:
            if not pb.name.endswith("ToeBase"):
                continue
            path = f'pose.bones["{pb.name}"].rotation_quaternion'
            fcs = [_find_fcurve(act, path, i) for i in range(4)]
            if not fcs or any(fc is None for fc in fcs):
                continue
            n = len(fcs[0].keyframe_points)
            if n < 5 or any(len(fc.keyframe_points) != n for fc in fcs):
                continue
            Q = [Quaternion([fcs[i].keyframe_points[j].co[1] for i in range(4)]) for j in range(n)]
            for j in range(1, n):
                if Q[j].dot(Q[j - 1]) < 0:
                    Q[j] = -Q[j]
            for _ in range(passes):
                Q = [Q[0]] + [Quaternion([(Q[j - 1][i] + 2 * Q[j][i] + Q[j + 1][i]) / 4 for i in range(4)]).normalized() for j in range(1, n - 1)] + [Q[-1]]
            for j in range(n):
                for i in range(4):
                    fcs[i].keyframe_points[j].co[1] = Q[j][i]
                    fcs[i].keyframe_points[j].handle_left[1] = Q[j][i]
                    fcs[i].keyframe_points[j].handle_right[1] = Q[j][i]
            for fc in fcs:
                fc.update()
