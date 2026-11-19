"""
MOTIONFORGE coach from a supplied sculpted mesh (owner-supplied GLB, e.g. generated from her Workout Coach sheet).
  1. import, scale to the coach's height (feet on the floor, facing -Y)
  2. game mesh: decimated copy (~30k tris), fresh UVs
  3. bake from the full-detail mesh onto the game mesh: base colour, roughness/metal, tangent normal map (2048)
  4. joints measured on the mesh -> rig (with finger bones) -> automatic weights -> the 9 clips
  5. lit textured GLB + clip manifest
Run: python tools/blender/build_coach_mesh.py <in.glb> <name> <height_m> [--tris N] [--res 2048] [--app]
  --app also copies it to app/src/main/assets/models/<name>.glb with <name>.clips.json
"""
import json, math, os, shutil, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
args = sys.argv[1:]
SRC, NAME, HEIGHT = args[0], args[1], float(args[2])
TRIS = int(args[args.index("--tris") + 1]) if "--tris" in args else 30000
RES = int(args[args.index("--res") + 1]) if "--res" in args else 2048
WORK = os.path.join("/tmp", "coach_" + NAME)
os.makedirs(WORK, exist_ok=True)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
hi = next(o for o in bpy.data.objects if o.type == "MESH")
for o in list(bpy.data.objects):
    if o is not hi and o.type != "MESH":
        bpy.data.objects.remove(o)
hi.parent = None
bpy.context.view_layer.objects.active = hi
hi.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
v = np.empty(len(hi.data.vertices) * 3, np.float32)
hi.data.vertices.foreach_get("co", v)
v = v.reshape(-1, 3)
s = HEIGHT / (v[:, 2].max() - v[:, 2].min())
v = (v - np.array([(v[:, 0].max() + v[:, 0].min()) / 2, (v[:, 1].max() + v[:, 1].min()) / 2, v[:, 2].min()])) * s
hi.data.vertices.foreach_set("co", v.ravel())
hi.data.update()
hi.name = "hi"
print("HI tris", len(hi.data.polygons), "scale", round(s, 3))

# ---------------------------------------------------------------- joints measured on the mesh
H = HEIGHT


def band(z, w=0.006):
    return v[np.abs(v[:, 2] - z) < w]


def outer(z, side):
    """centre of the outermost separate piece (arm or leg) on one side at height z, via the largest x gap"""
    b = band(z)
    x = b[:, 0] * side
    b = b[x > 0.0]
    x = x[x > 0.0]
    if len(x) < 10:
        return None
    o = np.argsort(x)
    xs = x[o]
    g = np.diff(xs)
    i = int(np.argmax(g)) if len(g) else 0
    piece = b[o][i + 1:] if g[i] > 0.012 else b[o]
    return piece.mean(0), (xs[-1] - xs[i + 1]) / 2 if g[i] > 0.012 else None


# crotch: lowest height where the centre line (x ~ 0) has body
zz = np.arange(0.30 * H, 0.65 * H, 0.004)
crotch = next(z for z in zz if (np.abs(band(z, 0.003)[:, 0]) < 0.01).sum() > 3)
J = {}
for side, sgn in (("L", 1), ("R", -1)):
    # arm: below the armpit the outermost piece is the arm
    pts = []
    for z in np.arange(0.44 * H, 0.75 * H, 0.01 * H):
        r = outer(z, sgn)
        if r and r[1] is not None and r[1] < 0.07:
            pts.append(r[0])
    pts = np.array(pts)
    zt = pts[:, 2].max()
    lo = pts[:, 2].min()
    fit = lambda z: Vector(pts[np.argmin(np.abs(pts[:, 2] - z))])
    shoulder_z = 0.815 * H
    up = fit(zt)
    top_dir = (up - fit(zt - 0.12 * H)).normalized()
    sh = up + top_dir * ((shoulder_z - up.z) / max(top_dir.z, 0.3))
    J[f"upper_arm_{side}"] = Vector((sh.x, sh.y * 0.5, shoulder_z))
    J[f"forearm_{side}"] = fit(0.625 * H)
    J[f"hand_{side}"] = fit(0.495 * H)
    tip = band(lo, 0.01)
    tip = tip[tip[:, 0] * sgn > abs(J[f"hand_{side}"].x) - 0.04]
    J[f"hand_tip_{side}"] = Vector(tip.mean(0)) if len(tip) else fit(lo)
    J[f"shoulder_{side}"] = Vector((0.03 * sgn, 0.0, shoulder_z + 0.01 * H))
    # leg
    leg = lambda z: Vector(outer(z, sgn)[0]) if outer(z, sgn) else None
    k = leg(0.285 * H)
    a = leg(0.055 * H)
    hp = leg(crotch - 0.04 * H)
    J[f"thigh_{side}"] = Vector((hp.x, hp.y, crotch + 0.045 * H))
    J[f"shin_{side}"] = Vector((k.x, k.y - 0.01, 0.285 * H))
    J[f"foot_{side}"] = Vector((a.x, a.y + 0.02, 0.05 * H))
    foot = v[(v[:, 2] < 0.05 * H) & (v[:, 0] * sgn > 0.02)]
    J[f"toe_{side}"] = Vector((a.x, foot[:, 1].min() + 0.05, 0.02 * H))
    J[f"toe_tip_{side}"] = Vector((a.x, foot[:, 1].min(), 0.02 * H))
neck = band(0.86 * H)
J.update({"pelvis": Vector((0, 0, crotch + 0.07 * H)), "spine": Vector((0, 0, 0.62 * H)), "chest": Vector((0, 0, 0.72 * H)),
          "neck": Vector((0, neck[:, 1].mean() if len(neck) else 0, 0.84 * H)), "head": Vector((0, 0, 0.885 * H)),
          "head_top": Vector((0, 0, H))})
print("crotch", round(crotch, 3), {k: tuple(round(c, 3) for c in J[k]) for k in ("upper_arm_L", "forearm_L", "hand_L", "hand_tip_L", "thigh_L", "shin_L", "foot_L")})

import trainer_body as tb  # noqa: E402
tb.J.clear()
tb.J.update(J)
import trainer_rig as tr  # noqa: E402
import trainer_anim as ta  # noqa: E402

# ---------------------------------------------------------------- game mesh
lo = hi.copy()
lo.data = hi.data.copy()
lo.name = lo.data.name = NAME
bpy.context.collection.objects.link(lo)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = lo
lo.select_set(True)
dec = lo.modifiers.new("dec", "DECIMATE")
dec.ratio = TRIS / len(hi.data.polygons) / (1 if all(len(p.vertices) == 3 for p in hi.data.polygons[:1000]) else 2)
bpy.ops.object.modifier_apply(modifier=dec.name)
bpy.ops.object.shade_smooth()
print("LO tris", sum(len(p.vertices) - 2 for p in lo.data.polygons))
while lo.data.uv_layers:
    lo.data.uv_layers.remove(lo.data.uv_layers[0])
lo.data.uv_layers.new(name="UVMap")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- bake hi -> lo
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 1
sc.render.bake.use_selected_to_active = True
sc.render.bake.cage_extrusion = 0.008
sc.render.bake.max_ray_distance = 0.02
sc.render.bake.margin = 8
hmat = hi.data.materials[0]
hbs = next(n for n in hmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
out = {}
bake_mat = bpy.data.materials.new("bake")
bake_mat.use_nodes = True
tnode = bake_mat.node_tree.nodes.new("ShaderNodeTexImage")
bake_mat.node_tree.nodes.active = tnode
lo.data.materials.clear()
lo.data.materials.append(bake_mat)


def bake(kind, fname, colorspace="sRGB", **kw):
    img = bpy.data.images.new(fname, RES, RES)
    img.colorspace_settings.name = colorspace
    tnode.image = img
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.bake(type=kind, **kw)
    img.filepath_raw = os.path.join(WORK, fname)
    img.file_format = "PNG" if fname.endswith(".png") else "JPEG"
    img.save()
    out[fname] = img
    print("baked", fname)


sc.render.bake.use_pass_direct = False
sc.render.bake.use_pass_indirect = False
sc.render.bake.use_pass_color = True
bake("DIFFUSE", "base.png")
bake("ROUGHNESS", "rough.png", "Non-Color")
bake("NORMAL", "normal.png", "Non-Color", normal_space="TANGENT")

# metal is ~0 for this character; pack roughness into G (glTF metallicRoughness)
r = np.array(out["rough.png"].pixels[:], np.float32).reshape(RES, RES, 4)
mr = np.zeros_like(r)
mr[..., 0] = 1.0
mr[..., 1] = r[..., 0]
mr[..., 3] = 1.0
mrimg = bpy.data.images.new("mr.png", RES, RES)
mrimg.colorspace_settings.name = "Non-Color"
mrimg.pixels[:] = mr.ravel()
mrimg.filepath_raw = os.path.join(WORK, "mr.png")
mrimg.file_format = "PNG"
mrimg.save()
bpy.data.objects.remove(hi)

# ---------------------------------------------------------------- material
m = bpy.data.materials.new(NAME + "_mat")
m.use_nodes = True
nt = m.node_tree
bs = nt.nodes["Principled BSDF"]
t_base = nt.nodes.new("ShaderNodeTexImage"); t_base.image = out["base.png"]
nt.links.new(t_base.outputs[0], bs.inputs["Base Color"])
t_mr = nt.nodes.new("ShaderNodeTexImage"); t_mr.image = mrimg
sep = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(t_mr.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs[1], bs.inputs["Roughness"])
nt.links.new(sep.outputs[2], bs.inputs["Metallic"])
t_n = nt.nodes.new("ShaderNodeTexImage"); t_n.image = out["normal.png"]
nm = nt.nodes.new("ShaderNodeNormalMap")
nt.links.new(t_n.outputs[0], nm.inputs["Color"])
nt.links.new(nm.outputs[0], bs.inputs["Normal"])
lo.data.materials.clear()
lo.data.materials.append(m)

# ---------------------------------------------------------------- rig + weights
sc.render.fps = ta.FPS
arm = tr.build_armature()
# Heat weights need a clean closed surface: compute them on a voxel-remeshed proxy of the body (merges the loose
# shells a generated mesh has), then transfer to the game mesh by nearest surface point.
proxy = lo.copy(); proxy.data = lo.data.copy(); proxy.name = "weight_proxy"
bpy.context.collection.objects.link(proxy)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = proxy
proxy.select_set(True)
proxy.data.remesh_voxel_size = 0.0032
bpy.ops.object.voxel_remesh()
d2 = proxy.modifiers.new("d", "DECIMATE"); d2.ratio = min(1.0, 60000 / max(len(proxy.data.polygons), 1))
bpy.ops.object.modifier_apply(modifier=d2.name)
bpy.ops.object.select_all(action="DESELECT")
proxy.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
unweighted = sum(1 for vv in proxy.data.vertices if not any(g.weight > 0.01 for g in vv.groups))
print("proxy verts", len(proxy.data.vertices), "unweighted", unweighted)
for g in proxy.vertex_groups:
    lo.vertex_groups.new(name=g.name)
dt = lo.modifiers.new("dt", "DATA_TRANSFER")
dt.object = proxy
dt.use_vert_data = True
dt.data_types_verts = {"VGROUP_WEIGHTS"}
dt.vert_mapping = "POLYINTERP_NEAREST"
dt.layers_vgroup_select_src = "ALL"
dt.layers_vgroup_select_dst = "NAME"
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = lo
lo.select_set(True)
bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.data.objects.remove(proxy)
lo.parent = arm
mod = lo.modifiers.new("Armature", "ARMATURE"); mod.object = arm
groups = {g.index: g.name for g in lo.vertex_groups}
unweighted = sum(1 for vv in lo.data.vertices if not any(g.weight > 0.01 for g in vv.groups))
print("weights: groups", len(groups), "unweighted verts", unweighted)
if False:
    pass
for g in list(lo.vertex_groups):
    if g.name.startswith("finger"):
        lo.vertex_groups.remove(g)      # the sculpted hands are already loosely closed; fingers stay rigid
_ua = J["forearm_L"] - J["upper_arm_L"]
ta.REST_ARM = math.degrees(math.atan2(abs(_ua.x), -_ua.z))
ta.LEG_THIGH = (J["shin_L"] - J["thigh_L"]).length
ta.LEG_SHIN = (J["foot_L"] - J["shin_L"]).length
print("rest arm", round(ta.REST_ARM, 1), "legs", round(ta.LEG_THIGH, 3), round(ta.LEG_SHIN, 3))
ta.build_clips(arm)
arm.animation_data.action = None
print("TRIS", sum(len(p.vertices) - 2 for p in lo.data.polygons))

# ---------------------------------------------------------------- save + export
for img in out.values():
    img.pack()
mrimg.pack()
blend = os.path.join(ROOT, "assets/blender/source", NAME + ".blend")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
exp = os.path.join(ROOT, "assets/blender/exports", NAME + ".glb")
bpy.ops.object.select_all(action="DESELECT")
lo.select_set(True)
arm.select_set(True)
bpy.ops.export_scene.gltf(filepath=exp, export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_texcoords=True,
                          export_normals=True, export_materials="EXPORT", export_image_format="JPEG", export_jpeg_quality=88,
                          export_skins=True, export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                          export_frame_range=False, export_anim_single_armature=True, export_reset_pose_bones=True)
print("EXPORTED", exp, os.path.getsize(exp))
manifest = {"asset": f"models/{NAME}.glb", "generator": "tools/blender/build_coach_mesh.py", "fps": ta.FPS,
            "clips": [{"name": n, "durationSeconds": round(dd, 3), "reviewStatus": "draft_pending_coach_review"} for n, dd, _ in ta.clip_specs()]}
if "--app" in args:
    shutil.copyfile(exp, os.path.join(ROOT, "app/src/main/assets/models", NAME + ".glb"))
    with open(os.path.join(ROOT, "app/src/main/assets/models", NAME + ".clips.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
