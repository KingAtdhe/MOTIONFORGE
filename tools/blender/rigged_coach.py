"""Use the owner's professionally rigged coach (Tripo export, Mixamo-style skeleton with its own skin weights) instead
of MOTIONFORGE's auto-rig.

The exercise clips are still generated on the MOTIONFORGE rig (trainer_anim / mocap / IK passes). That rig is built
from this skeleton's own joint positions (joints()), so both rest poses match; transfer() then copies each frame
onto the Mixamo bones: every bone takes the world-space rotation change of its MOTIONFORGE counterpart, limbs are
re-aimed at the posed MOTIONFORGE limb so directions match exactly, and the hips carry the root motion.
"""
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


def prepare_textures(mesh, res=2048):
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
                feeds_rough = any(l.to_socket.name in ("Roughness",) or (l.to_node.type == "SEPARATE_COLOR") for l in n.outputs[0].links)
                if feeds_rough and img.colorspace_settings.name != "sRGB":
                    px = np.array(img.pixels[:], np.float32).reshape(-1, 4)
                    px[:, 1] = 0.45 + 0.50 * np.clip(px[:, 1], 0, 1)
                    img.pixels[:] = px.ravel()
                    print("roughness remapped on", img.name)
                img.pack()


def bn_is_root(arm, name):
    return arm.data.bones[name].parent is None
