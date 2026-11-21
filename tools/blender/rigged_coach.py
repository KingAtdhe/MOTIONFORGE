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
                    w = max(0.0, min(1.0, 1.0 - (ball_z - fb.tail_local.z) / 0.035))
                    D = delta(src)
                    fw_ = D @ Vector((0, -1, 0))
                    flat = Matrix.Rotation(math.atan2(fw_.x, -fw_.y), 3, "Z")
                    if fw_.z < 0 and w > 0:
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
