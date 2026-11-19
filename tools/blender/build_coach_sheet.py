"""
MOTIONFORGE female coach v5 — built from the owner's "Workout Coach" sheet.

Stages (tools/coach_from_sheet/, run in this order; see README there):
  masks.py  -> silhouettes of the front / side / back views
  hull.py   -> body volume from the front + side outlines (cross-sections per row) -> marching-cubes surface
  blend_hull.py, bake.py -> Blender mesh, UVs, baked texel positions/normals
  project.py -> the owner's painting projected onto the surface (front, both sides, back), chest logo removed
This script: rig (with finger bones), sculpted fist-capable hands in place of the painted ones, A-pose rest,
9 clips, unlit textured GLB + clip manifest, previews.
Run: python tools/blender/build_coach_sheet.py <work_dir> [--previews]
"""
import json, math, os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WORK = sys.argv[1]
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "hull_uv.blend"))
import trainer_body as tb  # noqa: E402

# ---- joints measured on the sheet model (metres, character faces -Y, left = +X)
J = tb.J
J.update({"pelvis": Vector((0, 0.0, 0.95)), "spine": Vector((0, -0.01, 1.08)), "chest": Vector((0, -0.01, 1.25)),
          "neck": Vector((0, 0.01, 1.42)), "head": Vector((0, 0.0, 1.50)), "head_top": Vector((0, 0.0, 1.70))})
for side, s in (("L", 1), ("R", -1)):
    J[f"shoulder_{side}"] = Vector((0.03 * s, 0.0, 1.40))
    J[f"upper_arm_{side}"] = Vector((0.128 * s, -0.012, 1.36))
    J[f"forearm_{side}"] = Vector((0.195 * s, -0.045, 1.12))
    J[f"hand_{side}"] = Vector((0.243 * s, -0.004, 0.945))
    J[f"hand_tip_{side}"] = Vector((0.262 * s, -0.020, 0.775))
    J[f"thigh_{side}"] = Vector((0.095 * s, -0.01, 0.88))
    J[f"shin_{side}"] = Vector((0.172 * s, 0.0, 0.47))
    J[f"foot_{side}"] = Vector((0.232 * s, 0.02, 0.085))
    J[f"toe_{side}"] = Vector((0.234 * s, -0.12, 0.03))
    J[f"toe_tip_{side}"] = Vector((0.236 * s, -0.155, 0.03))

import trainer_rig as tr  # noqa: E402
import trainer_anim as ta  # noqa: E402
from trainer_body import material, srgb  # noqa: E402
import build_coach_parts as parts  # noqa: E402  (sculpt_hand / Clay shared with the earlier coach build)

scene = bpy.context.scene
scene.render.fps = ta.FPS
body = next(o for o in bpy.data.objects if o.type == "MESH")
body.name = body.data.name = "trainer_avatar"

# ---- body material: the projected painting
# LIT: real-light materials (light-free base colour + baked normal map from detail.py / detail_bake.py)
LIT = os.path.exists(os.path.join(WORK, "coach_normal.png")) and "--unlit" not in sys.argv
img = bpy.data.images.load(os.path.join(WORK, "coach_basecolor.png" if LIT else "coach_albedo.png"))
img.name = "coach_basecolor" if LIT else "coach_albedo"
mbody = bpy.data.materials.new("coach_body")
mbody.use_nodes = True
nt = mbody.node_tree
bs = nt.nodes["Principled BSDF"]
bs.inputs["Roughness"].default_value = 0.55
it = nt.nodes.new("ShaderNodeTexImage")
it.image = img
nt.links.new(it.outputs[0], bs.inputs["Base Color"])
if LIT:
    nimg = bpy.data.images.load(os.path.join(WORK, "coach_normal.png"))
    nimg.name = "coach_normal"
    nimg.colorspace_settings.name = "Non-Color"
    nt_ = nt.nodes.new("ShaderNodeTexImage"); nt_.image = nimg
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nt_.outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bs.inputs["Normal"])
    if os.path.exists(os.path.join(WORK, "coach_mr.png")):
        mimg = bpy.data.images.load(os.path.join(WORK, "coach_mr.png")); mimg.name = "coach_mr"
        mimg.colorspace_settings.name = "Non-Color"
        mt_ = nt.nodes.new("ShaderNodeTexImage"); mt_.image = mimg
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(mt_.outputs[0], sep.inputs[0])
        nt.links.new(sep.outputs[1], bs.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bs.inputs["Metallic"])
    try:
        bs.inputs["Specular IOR Level"].default_value = 0.35
    except KeyError:
        pass
if LIT and os.path.exists(os.path.join(WORK, "coach_skin.json")):
    _rgb = json.load(open(os.path.join(WORK, "coach_skin.json")))["skin_rgb"]
    M_SKIN_RGB = tuple(c ** 2.2 for c in _rgb)          # sRGB texture value -> linear factor
else:
    M_SKIN_RGB = None
print("LIT materials" if LIT else "UNLIT materials")
body.data.materials.clear()
body.data.materials.append(mbody)

# ---- remove the painted hands below the glove cuff (replaced by sculpted hands that can make fists)
bm = bmesh.new()
bm.from_mesh(body.data)
dead = [v for v in bm.verts if abs(v.co.x) > 0.212 and 0.74 < v.co.z < 0.952]
bmesh.ops.delete(bm, geom=dead, context="VERTS")
bm.to_mesh(body.data)
bm.free()

M = {"skin": material("coach_hand_skin", srgb("D9905F"), 0.5), "black": material("coach_glove", srgb("1E1D22"), 0.6),
     "accent": material("coach_glove_accent", srgb("C7283A"), 0.55), "paint": material("coach_glove_paint", (1.0, 1.0, 1.0), 0.6)}
if M_SKIN_RGB:
    M["skin"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*M_SKIN_RGB, 1.0)
for m in list(M.values()) + [mbody]:
    nt_ = m.node_tree
    b_ = nt_.nodes["Principled BSDF"]
    b_.inputs["Roughness"].default_value = 0.6
    vc = nt_.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mul = nt_.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    src_link = b_.inputs["Base Color"].links
    if src_link:
        nt_.links.new(src_link[0].from_socket, mul.inputs[6])
    else:
        mul.inputs[6].default_value = b_.inputs["Base Color"].default_value
    nt_.links.new(vc.outputs["Color"], mul.inputs[7])
    nt_.links.new(mul.outputs[2], b_.inputs["Base Color"])

arm = tr.build_armature()
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
assert len(body.vertex_groups) > 10, "automatic weights failed"
# fingers never take body weights
for g in list(body.vertex_groups):
    if g.name.startswith("finger"):
        body.vertex_groups.remove(g)

# vertex colours: white on the painted body; soft painted-style light on the sculpted hands so they sit
# with the painting instead of reading as flat cut-outs (glTF multiplies base colour by COLOR_0)
LIGHT = Vector((-0.45, -0.70, 0.55)).normalized()


def shade(o, white=False):
    me = o.data
    a = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for v in me.vertices:
        if white or LIT:
            k = 1.0
        else:
            k = 0.58 + 0.52 * max(0.0, v.normal.dot(LIGHT)) + 0.08 * v.normal.z
        a.data[v.index].color = (k, k * 0.97, k * 0.95, 1.0)
    me.color_attributes.active_color = a
    me.color_attributes.render_color_index = 0


shade(body, white=True)
GLOVE = (0.055, 0.052, 0.062)
RED = (0.78, 0.13, 0.20)


def glove_details(side, objs):
    """Glove as on the sheet's detail panel: black glove and wrist strap, the glove also covers the first finger
    row, a red outlined panel on the back of the hand and red dots over the knuckles; bare fingertips.
    Painted per vertex (white base x vertex colour) so the red edges come out soft rather than stair-stepped."""
    from trainer_rig import KNUCKLE
    s_ = 1 if side == "L" else -1
    W_, T_ = J[f"hand_{side}"], J[f"hand_tip_{side}"]
    d_ = (T_ - W_).normalized()
    y_ = Vector((0, -1, 0))
    x_ = d_.cross(y_).normalized()
    y_ = x_.cross(d_).normalized()
    back = -x_ * s_
    for o in objs:
        if not o.name.startswith(("coach_fingers_", "coach_strap_", "coach_glove_")):
            continue
        me = o.data
        me.materials.clear()
        me.materials.append(M["paint"])
        a = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        for v in me.vertices:
            c = v.co - W_
            du, dy = c.dot(d_), c.dot(y_)
            col = GLOVE
            facing_back = v.normal.dot(back)
            if o.name.startswith("coach_glove_") and facing_back > 0.45:
                ring = max(abs(du - 0.049) / 0.023, abs(dy) / 0.024)
                if 0.78 < ring < 1.0:
                    col = RED
            if o.name.startswith("coach_fingers_") and facing_back > 0.4 and abs(du - KNUCKLE - 0.006) < 0.007:
                if min(abs(dy - (1.5 - i) * 0.0192) for i in range(4)) < 0.0055:
                    col = RED
            k = 1.0 if LIT else 0.62 + 0.55 * max(0.0, v.normal.dot(LIGHT)) + 0.08 * v.normal.z
            a.data[v.index].color = (col[0] * k, col[1] * k, col[2] * k, 1.0)
        me.color_attributes.active_color = a
        me.color_attributes.render_color_index = 0
        o["painted"] = True


pieces = []
for side in ("L", "R"):
    hp = parts.sculpt_hand(side, M)
    glove_details(side, [o for objs in hp.values() for o in objs])
    for bone, objs in hp.items():
        for o in objs:
            if not o.get("painted"):
                shade(o)
            g = o.vertex_groups.new(name=bone)
            g.add(range(len(o.data.vertices)), 1.0, "REPLACE")
            pieces.append(o)
bpy.ops.object.select_all(action="DESELECT")
for p in pieces:
    p.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
if not any(m.type == "ARMATURE" for m in body.modifiers):
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
body.parent = arm

# ---- new rest pose: arms to the 45-degree A-pose the clips are written for, legs a little closer together
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")


def swing(bone, target_dir):
    pb = arm.pose.bones[bone]
    head = arm.matrix_world.inverted() @ pb.head
    cur = (pb.tail - pb.head).normalized()
    R = cur.rotation_difference(Vector(target_dir).normalized()).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


# arms stay in the sheet's pose (no rest re-pose = no stretched shoulders); the clips are told the rest angle
_ua = (J["forearm_L"] - J["upper_arm_L"])
ta.REST_ARM = math.degrees(math.atan2(math.hypot(_ua.x, 0.0), -_ua.z))
print("rest arm angle", round(ta.REST_ARM, 1))
for side, s in (("L", 1), ("R", -1)):
    d = (J[f"shin_{side}"] - J[f"thigh_{side}"]).normalized()
    swing(f"thigh_{side}", (d.x * 0.45, d.y, d.z))
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active = body
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
mod = next(m for m in body.modifiers if m.type == "ARMATURE")
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode="OBJECT")
mod = body.modifiers.new("Armature", "ARMATURE")
mod.object = arm
# the clip maths reads joint positions: refresh them from the new rest skeleton
for b in arm.data.bones:
    pass
for side in ("L", "R"):
    for key, bone in (("upper_arm", "upper_arm"), ("forearm", "forearm"), ("hand", "hand"), ("thigh", "thigh"), ("shin", "shin"), ("foot", "foot")):
        J[f"{key}_{side}"] = arm.data.bones[f"{bone}_{side}"].head_local.copy()
    J[f"hand_tip_{side}"] = arm.data.bones[f"hand_{side}"].tail_local.copy()
    J[f"toe_{side}"] = arm.data.bones[f"foot_{side}"].tail_local.copy()
ta.LEG_THIGH = (J["shin_L"] - J["thigh_L"]).length
ta.LEG_SHIN = (J["foot_L"] - J["shin_L"]).length
print("legs", round(ta.LEG_THIGH, 3), round(ta.LEG_SHIN, 3))

body.data.validate()
tri_count = sum(len(p.vertices) - 2 for p in body.data.polygons)
print("TRIS", tri_count, "VERTS", len(body.data.vertices))
ta.build_clips(arm)
arm.animation_data.action = None

src = os.path.join(ROOT, "assets/blender/source/trainer_avatar.blend")
exp = os.path.join(ROOT, "assets/blender/exports/trainer_avatar.glb")
app_copy = os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.glb")
img.pack()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=src, compress=True)
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
arm.select_set(True)
bpy.ops.export_scene.gltf(filepath=exp, export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_texcoords=True,
                          export_normals=True, export_materials="EXPORT", export_image_format="JPEG", export_jpeg_quality=90, export_vertex_color="ACTIVE",
                          export_skins=True, export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                          export_frame_range=False, export_anim_single_armature=True, export_reset_pose_bones=True)
with open(exp, "rb") as fh:
    raw = fh.read()
jl = struct.unpack("<I", raw[12:16])[0]
g = json.loads(raw[20:20 + jl])
rest = raw[20 + jl:]
for mt in g["materials"]:
    if not LIT:
        mt.setdefault("extensions", {})["KHR_materials_unlit"] = {}
    mt["doubleSided"] = False
if not LIT:
    g["extensionsUsed"] = sorted(set(g.get("extensionsUsed", []) + ["KHR_materials_unlit"]))
js = json.dumps(g, separators=(",", ":")).encode()
js += b" " * ((4 - len(js) % 4) % 4)
with open(exp, "wb") as fh:
    fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(rest)) + struct.pack("<II", len(js), 0x4E4F534A) + js + rest)
shutil.copyfile(exp, app_copy)
print("EXPORTED", os.path.getsize(exp))
manifest = {"asset": "models/trainer_avatar.glb", "generator": "tools/blender/build_coach_sheet.py", "fps": ta.FPS,
            "clips": [{"name": n, "durationSeconds": round(dd, 3), "reviewStatus": "draft_pending_coach_review"} for n, dd, _ in ta.clip_specs()]}
with open(os.path.join(ROOT, "app/src/main/assets/models/trainer_avatar.clips.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")
