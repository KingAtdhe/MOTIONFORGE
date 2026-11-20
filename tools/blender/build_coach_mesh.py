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
TRIS = int(args[args.index("--tris") + 1]) if "--tris" in args else 90000
# Keep the source model's own UV layout and texture (crisp, colours exactly as the owner's model); only the normal map
# is re-baked so the high-res surface detail survives decimation. --rebake restores the old full re-bake.
KEEP_UV = "--rebake" not in args
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
    # fingertips: the hand hangs beside the thigh; it ends at the lowest height where the body still reaches
    # further out than the thigh does below the hand
    wz = J[f"hand_{side}"].z
    below = band(wz - 0.13 * H * 0.85 / 0.85 * 0.9, 0.006)
    thigh_out = (below[:, 0] * sgn).max() if len(below) else abs(J[f"hand_{side}"].x) - 0.05
    tip_z = wz - 0.02
    for z in np.arange(wz - 0.02, wz - 0.16, -0.004):
        b_ = band(z, 0.003)
        b_ = b_[b_[:, 0] * sgn > thigh_out + 0.008]
        if len(b_) < 4:
            break
        tip_z = z
    tip = band(tip_z, 0.012)
    tip = tip[tip[:, 0] * sgn > thigh_out + 0.004]
    J[f"hand_tip_{side}"] = Vector(tip.mean(0)) if len(tip) else fit(lo)
    print("hand", side, "length", round(wz - tip_z, 3), "thigh_out", round(float(thigh_out), 3))
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

RIGGED = args[args.index("--rigged") + 1] if "--rigged" in args else None
if RIGGED:
    import rigged_coach as rc  # noqa: E402
    mx_arm, mx_mesh = rc.load(RIGGED, HEIGHT)
    J.update(rc.joints(mx_arm, mx_mesh, HEIGHT))
    print("joints from rigged skeleton", {k: tuple(round(c, 3) for c in J[k]) for k in ("upper_arm_L", "hand_L", "thigh_L", "foot_L")})

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
if not KEEP_UV:
    while lo.data.uv_layers:
        lo.data.uv_layers.remove(lo.data.uv_layers[0])
    lo.data.uv_layers.new(name="UVMap")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
else:
    while len(lo.data.uv_layers) > 1:
        lo.data.uv_layers.remove(lo.data.uv_layers[-1])

# ---------------------------------------------------------------- bake hi -> lo
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 1
sc.render.bake.use_selected_to_active = True
sc.render.bake.cage_extrusion = 0.02   # decimation moves the surface >1 cm on muscles; short rays missed and left dark lines
sc.render.bake.max_ray_distance = 0.06
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
def source_image(socket_name):
    """The source material's texture feeding a Principled input (glTF import), resized to RES."""
    def walk(sock):
        for l in sock.links:
            n = l.from_node
            if n.type == "TEX_IMAGE":
                return n.image
            for i in n.inputs:
                r = walk(i)
                if r:
                    return r
        return None
    img = walk(hbs.inputs[socket_name])
    cp = img.copy()
    cp.scale(RES, RES)
    return cp


if KEEP_UV:
    base = source_image("Base Color")
    base.name = "base.png"
    base.filepath_raw = os.path.join(WORK, "base.png")
    base.file_format = "PNG"
    base.save()
    out["base.png"] = base
    mr_src = source_image("Roughness")       # glTF metallicRoughness: roughness in G
    rpx = np.array(mr_src.pixels[:], np.float32).reshape(RES, RES, 4)
    rough = bpy.data.images.new("rough.png", RES, RES)
    rough.colorspace_settings.name = "Non-Color"
    rp = np.zeros_like(rpx)
    rp[..., 0] = rp[..., 1] = rp[..., 2] = rpx[..., 1]
    rp[..., 3] = 1
    rough.pixels[:] = rp.ravel()
    out["rough.png"] = rough
    bake("NORMAL", "normal.png", "Non-Color", normal_space="TANGENT")
else:
    bake("DIFFUSE", "base.png")
    bake("ROUGHNESS", "rough.png", "Non-Color")
    bake("NORMAL", "normal.png", "Non-Color", normal_space="TANGENT")

# ---- colour: the generated texture is much darker than the owner's sheet; grade skin to the sheet's skin tone and
#      lift the dark fabric a little so the coach reads clearly in the app
SKIN = {"coach_f": (0.847, 0.494, 0.345), "coach_m": (0.702, 0.388, 0.255)}.get(NAME)
if SKIN and "--no-grade" not in args and not KEEP_UV:
    img = out["base.png"]
    px = np.array(img.pixels[:], np.float32).reshape(RES, RES, 4)
    rgb = px[..., :3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    skin_m = (r > g * 1.15) & (g > b * 1.05) & (r > 0.12)
    # Blender image pixels are linear for sRGB images: compare in display space
    to_s = lambda x: np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)
    to_l = lambda x: np.where(x <= 0.04045, x / 12.92, np.power((np.clip(x, 0, None) + 0.055) / 1.055, 2.4))
    srgb = to_s(rgb)
    med = np.median(srgb[skin_m], axis=0)
    gain = np.clip(np.array(SKIN) / np.maximum(med, 1e-3), 1.0, 2.2)
    from scipy.ndimage import gaussian_filter
    w = gaussian_filter(skin_m.astype(np.float32), 2.0)[..., None]
    lifted = srgb * gain * w + (srgb * 1.18 + 0.025) * (1 - w)          # skin to sheet tone; fabric lifted
    px[..., :3] = to_l(np.clip(lifted, 0, 1))
    img.pixels[:] = px.ravel()
    img.save()
    print("graded skin", med.round(3), "->", SKIN, "gain", gain.round(2))

# metal is ~0 for this character; pack roughness into G (glTF metallicRoughness)
r = np.array(out["rough.png"].pixels[:], np.float32).reshape(RES, RES, 4)
mr = np.zeros_like(r)
mr[..., 0] = 1.0
# the source scans bake a near-mirror roughness (median ~0.1) that reads as oily plastic under real-time lights;
# remap to a skin/fabric range (0.45 .. 0.95) keeping the relative detail
mr[..., 1] = 0.45 + 0.50 * np.clip(r[..., 0], 0.0, 1.0)
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
K1, K2 = 0.48, 0.72                     # knuckle line and middle finger joint, as fractions of wrist->fingertip
_Lh = (Vector(J["hand_tip_L"]) - Vector(J["hand_L"])).length
tr.KNUCKLE, tr.PROX = K1 * _Lh, (K2 - K1) * _Lh
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
bpy.data.objects.remove(proxy)

# ---- weight clean-up (things heat weighting gets wrong on a sculpt with arms close to the body)
ARM_BONES = {f"{b}_{s_}" for b in ("upper_arm", "forearm", "hand", "fingers", "fingertips") for s_ in ("L", "R")}
arm_inner = {}                       # per side: z -> x where the arm piece starts (below the armpit)
for side, sgn in (("L", 1), ("R", -1)):
    tab = []
    for z in np.arange(0.44 * H, 0.75 * H, 0.005 * H):
        b_ = band(z)
        x = np.sort(b_[:, 0][b_[:, 0] * sgn > 0] * sgn)
        if len(x) > 10:
            g = np.diff(x)
            i = int(np.argmax(g))
            if g[i] > 0.012:
                tab.append((z, x[i] + g[i] * 0.5))
    arm_inner[side] = np.array(tab)
armpit_z = {s_: arm_inner[s_][:, 0].max() for s_ in arm_inner}
gid = {g.name: g.index for g in lo.vertex_groups}
inv = {i: n for n, i in gid.items()}
head_z = J["neck"].z + 0.035 * H
changed = 0
for vv in lo.data.vertices:
    co = vv.co
    side = "L" if co.x > 0 else "R"
    tb_ = arm_inner[side]
    sx = abs(J[f"upper_arm_{side}"].x)
    if co.z > head_z:                                                       # head and hair: only head / neck may move them
        stray = [g for g in vv.groups if inv[g.group] not in ("head", "neck")]
        if stray:
            for g in stray:
                lo.vertex_groups[g.group].remove([vv.index])
            if not any(g.weight > 0.01 for g in vv.groups):
                lo.vertex_groups["head"].add([vv.index], 1.0, "REPLACE")
            changed += 1
        continue
    # how much the arm may move this vertex: 0 on the torso, ramping to 1 at the arm (no hard seam)
    if co.z < armpit_z[side] - 0.005 and co.z > max(tb_[:, 0].min(), J[f"forearm_{side}"].z):
        xi = float(np.interp(co.z, tb_[:, 0], tb_[:, 1]))
        k = np.clip((abs(co.x) - (xi - 0.03)) / 0.03, 0.0, 1.0)
    elif co.z >= armpit_z[side] - 0.005 and co.z < J["neck"].z:
        k = np.clip((abs(co.x) - 0.55 * sx) / (0.40 * sx), 0.0, 1.0)      # chest / shoulder top: pecs belong to the chest
    else:
        k = 1.0
    if k < 0.999:
        arm_w = [(g.group, g.weight) for g in vv.groups if inv[g.group] in ARM_BONES]
        if arm_w:
            moved = 0.0
            for gi, w in arm_w:
                nw = w * k
                moved += w - nw
                if nw < 0.005:
                    lo.vertex_groups[gi].remove([vv.index])
                else:
                    lo.vertex_groups[gi].add([vv.index], nw, "REPLACE")
            tgt = "chest" if co.z > J["chest"].z - 0.05 else "spine"
            cur = next((g.weight for g in vv.groups if inv[g.group] == tgt), 0.0)
            lo.vertex_groups[tgt].add([vv.index], cur + moved, "REPLACE")
            changed += 1
for vv in lo.data.vertices:                                                 # anything left unweighted -> nearest torso bone
    if not any(g.weight > 0.01 for g in vv.groups):
        lo.vertex_groups["head" if vv.co.z > head_z else ("chest" if vv.co.z > J["chest"].z else "spine")].add([vv.index], 1.0, "REPLACE")
print("weight clean-up changed", changed)


# ---- regional weight smoothing (Laplacian, along mesh edges). Heat weights leave hard steps where the shorts meet the
#      thighs, along the flanks and in the armpits; with linear-blend skinning those steps turn into spikes, folds and
#      torn-looking creases in a deep squat or a twisting punch. Smooth hard in those bands only (hands, fingers and
#      head keep their sharp, deliberate weights), feathered at the band edges so no new seam appears.
def smooth_bands(bands):
    nv = len(lo.data.vertices)
    names = [g.name for g in lo.vertex_groups]
    Wt = np.zeros((nv, len(names)), np.float32)
    for vv in lo.data.vertices:
        for g in vv.groups:
            Wt[vv.index, g.group] = g.weight
    ed = np.array([e.vertices[:] for e in lo.data.edges], np.int64)
    deg = np.bincount(ed.ravel(), minlength=nv).astype(np.float32)
    co = np.array([vv.co[:] for vv in lo.data.vertices], np.float32)
    frozen = [i for i, n in enumerate(names) if n.startswith(("hand_", "fingers_", "fingertips_", "head", "foot_"))]
    for (z0, z1, feather, repeat, factor, xmin) in bands:
        z = co[:, 2] / H
        m = np.clip(np.minimum(z - z0, z1 - z) / feather, 0, 1)
        if xmin:
            m *= np.clip((np.abs(co[:, 0]) / H - xmin) / 0.02, 0, 1)
        touches_frozen = Wt[:, frozen].sum(1) > 0.05
        m[touches_frozen] = 0
        m = (m * m * (3 - 2 * m) * factor)[:, None]
        for _ in range(repeat):
            acc = np.zeros_like(Wt)
            np.add.at(acc, ed[:, 0], Wt[ed[:, 1]])
            np.add.at(acc, ed[:, 1], Wt[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            Wt = Wt * (1 - m) + avg * m
    Wt /= np.maximum(Wt.sum(1, keepdims=True), 1e-6)
    for gi, n in enumerate(names):
        g = lo.vertex_groups[n]
        col = Wt[:, gi]
        idx = np.nonzero(col > 1e-4)[0]
        g.remove(list(range(nv)))
        for i in idx:
            g.add([int(i)], float(col[i]), "REPLACE")


# ---- pelvis and shorts: rebuild hips/thigh weights from geometry. Heat weights give the loose shorts, pockets and
#      flaps (often separate shells) patchy hips/thigh splits that tear into spikes when the thigh flexes. Here the
#      thigh share rises smoothly with distance below the hip joint, and left/right blend across the midline, like
#      cloth following the leg. Arm/hand vertices hanging at this height are left alone.
def pelvis_weights():
    hz = (J["thigh_L"].z + J["thigh_R"].z) / 2
    hw = abs(J["thigh_L"].x - J["thigh_R"].x) / 2
    gh = lo.vertex_groups["hips"]
    gl, gr = lo.vertex_groups["thigh_L"], lo.vertex_groups["thigh_R"]
    gs = lo.vertex_groups["spine"]
    arm_idx = {lo.vertex_groups[n].index for n in lo.vertex_groups.keys() if n.startswith(("upper_arm", "forearm", "hand", "finger", "shin", "foot"))}
    top, bottom = hz + 0.05 * H, hz - 0.25 * H          # long, gentle ramp: no fins on the shorts in a deep squat
    knee = (J["shin_L"].z + J["shin_R"].z) / 2
    n = 0
    for vv in lo.data.vertices:
        z = vv.co.z
        if z > top + 0.03 * H or z < knee + 0.03 * H:          # whole shorts down to just above the knee
            continue
        if sum(g.weight for g in vv.groups if g.group in arm_idx) > 0.05:
            continue
        t = _ss(top, bottom, z)                                 # 0 at the waist .. 1 well down the thigh
        side = _ss(-0.35 * hw, 0.35 * hw, vv.co.x)              # 0 = right leg .. 1 = left leg
        wth = t
        whips = 1 - t
        # keep a little of any spine weight already at the waistband
        wsp = 0.0
        for g in vv.groups:
            if g.group == gs.index:
                wsp = g.weight * (1 - t)
        tot = wth + whips + wsp
        for g in list(vv.groups):
            if lo.vertex_groups[g.group].name not in ("hips", "thigh_L", "thigh_R", "spine"):
                lo.vertex_groups[g.group].remove([vv.index])
        gh.add([vv.index], whips / tot, "REPLACE")
        gs.add([vv.index], wsp / tot, "REPLACE")
        gl.add([vv.index], wth * side / tot, "REPLACE")
        gr.add([vv.index], wth * (1 - side) / tot, "REPLACE")
        n += 1
    print("pelvis weights rebuilt", n)


def _ss(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


pelvis_weights()

# (z from, z to [fraction of height], feather, iterations, strength, min |x| or 0)
smooth_bands([
    (0.34, 0.60, 0.04, 30, 0.6, 0),        # pelvis, shorts, upper thighs
    (0.55, 0.80, 0.04, 14, 0.5, 0),        # flanks / ribcage twist
    (0.68, 0.86, 0.03, 14, 0.5, 0.075),    # shoulders and armpits
])
print("regional smoothing done")
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = lo
lo.select_set(True)
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.5, repeat=2)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
lo.parent = arm
mod = lo.modifiers.new("Armature", "ARMATURE"); mod.object = arm
groups = {g.index: g.name for g in lo.vertex_groups}
unweighted = sum(1 for vv in lo.data.vertices if not any(g.weight > 0.01 for g in vv.groups))
print("weights: groups", len(groups), "unweighted verts", unweighted)
if False:
    pass
# ---- finger weights: split each hand along its length (palm | proximal row | middle+tip rows) so it can make a fist
def _ss(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


THUMB_W = {"L": [], "R": []}
for side in ("L", "R"):
    W_, T_ = Vector(J[f"hand_{side}"]), Vector(J[f"hand_tip_{side}"])
    Lh = (T_ - W_).length
    d_ = (T_ - W_).normalized()
    gh, gf, gt = lo.vertex_groups[f"hand_{side}"], lo.vertex_groups[f"fingers_{side}"], lo.vertex_groups[f"fingertips_{side}"]
    for vv in lo.data.vertices:
        hw = next((g.weight for g in vv.groups if g.group == gh.index), 0.0)
        if hw < 0.5:
            continue
        t = (vv.co - W_).dot(d_) / Lh
        w2 = _ss(K2 - 0.05, K2 + 0.05, t)
        w1 = _ss(K1 - 0.06, K1 + 0.06, t) * (1 - w2)
        sgn_ = 1 if side == "L" else -1
        fwd_off = -(vv.co.y - (W_.y + d_.y * (vv.co - W_).dot(d_)))       # in front of the hand axis
        in_off = (W_.x - vv.co.x) * sgn_                                    # toward the body (palm side)
        TH = 0.055 * Lh / 0.08 if Lh < 0.08 else 0.055                      # hand-size scale
        f0, i0 = 0.22 * TH, 0.14 * TH
        if fwd_off > f0 and in_off > i0 and 0.05 < t < 0.95:               # thumb: palm side, front edge
            k = _ss(f0, f0 + 0.01, fwd_off) * _ss(i0, i0 + 0.01, in_off)
            gh.add([vv.index], hw * (1 - 0.8 * k), "REPLACE")
            gf.add([vv.index], hw * 0.8 * k, "REPLACE")
            continue
        if w1 + w2 < 0.01:
            continue
        rest_w = hw * (1 - w1 - w2)
        gh.add([vv.index], rest_w, "REPLACE")
        gf.add([vv.index], hw * w1, "REPLACE")
        gt.add([vv.index], hw * w2, "REPLACE")
_ua = J["forearm_L"] - J["upper_arm_L"]
ta.REST_ARM = math.degrees(math.atan2(abs(_ua.x), -_ua.z))
ta.LEG_THIGH = (J["shin_L"] - J["thigh_L"]).length
ta.LEG_SHIN = (J["foot_L"] - J["shin_L"]).length
print("rest arm", round(ta.REST_ARM, 1), "legs", round(ta.LEG_THIGH, 3), round(ta.LEG_SHIN, 3))
# guard: fists in front of the chin, clear of a sculpted (bulkier) chest
ta.G_LEAD_FWD, ta.G_LEAD_FLEX, ta.G_LEAD_TUCK = 52, 112, 4
ta.G_REAR_FWD, ta.G_REAR_FLEX, ta.G_REAR_TUCK = 50, 120, 6
ta.build_clips(arm)

# ---- recorded motion (CMU mocap, assets/mocap) replaces the hand-keyed clips where a clean take exists
import mocap_retarget as mr  # noqa: E402
MOCAP = {  # clip: (take, first frame, last frame, loops, frames easing back to the first pose)
    "idle_neutral": ("111_28", 10, 100, True, 0),
    "boxing_stance": ("13_18", 113, 142, True, 0),
    # 13_18 only has jab-cross combinations: keep the jab (peak f99) and ease back to guard before the cross starts
    "boxing_jab": ("13_18", 88, 104, False, 14),
    # cross (peak f33) from the same combination; the lead arm holds its guard pose from f15 (before the jab)
    "boxing_cross": ("13_18", 22, 42, False, 10),
}
# (tried: CMU 13_29 squat softened toward standing — blending a deep squat's joint rotations doesn't give a natural
#  shallow squat (knees shoot forward, hips stay under the body), so the squat stays hand-keyed with mocap-like timing)
# blend recorded poses toward the standing frame: keeps the performer's timing, balance and torso/hip coordination
# but at a beginner depth (knees ~95 deg instead of a full deep squat). value: (amount kept, standing frame)
SOFTEN = {}
HOLD = {"boxing_cross": ("L", 15)}
# the performer stands bladed, so "hips forward" is ~45 deg off the punching line; turn the boxing takes so punches
# go straight at the viewer's target (-Y), like the hand-keyed footwork / guard clips
TURN = {"boxing_stance": -40.0, "boxing_jab": -40.0, "boxing_cross": -20.0}
for clip, (take, f0, f1, loops, settle) in MOCAP.items():
    old_act = bpy.data.actions.get(clip)
    if old_act:
        bpy.data.actions.remove(old_act)
    act_, _ = mr.retarget(arm, np.load(os.path.join(ROOT, "assets/mocap", take + ".npz")), f0, f1, clip, loop=loops, settle=settle, hold=HOLD.get(clip), turn=TURN.get(clip, 0.0))
    act_.name = clip
    print("mocap", clip, take, f0, f1)


def soften(act, keep, ref):
    from mathutils import Quaternion  # noqa: F401
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    frames = list(range(a_, b_ + 1))
    poses = []
    for f in frames:
        sc.frame_set(f)
        poses.append({pb.name: (pb.rotation_quaternion.copy(), pb.location.copy()) for pb in arm.pose.bones})
    base = poses[0] if ref == "first" else poses[-1]
    for f, pose in zip(frames, poses):
        for name, (q, loc) in pose.items():
            pb = arm.pose.bones[name]
            q0, l0 = base[name]
            if q0.dot(q) < 0:
                q = -q
            pb.rotation_quaternion = q0.slerp(q, keep)
            pb.location = l0.lerp(loc, keep)
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("location", frame=f)
    arm.animation_data.action = None


# the recorded boxer drops his chin hard toward the chest; on the full-detail coach that hides the face behind the
# guard. Keep 40 % of the recorded neck/head bend relative to the ribcage (chin slightly down, eyes forward).
def lift_head(act, keep=0.4):
    from mathutils import Quaternion
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    vals = {}
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        vals[f] = {n: arm.pose.bones[n].rotation_quaternion.copy() for n in ("neck", "head")}
    for f, d in vals.items():
        for n, q in d.items():
            pb = arm.pose.bones[n]
            pb.rotation_quaternion = Quaternion().slerp(q, keep)
            pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


for clip in ("boxing_stance", "boxing_jab", "boxing_cross"):
    lift_head(bpy.data.actions[clip])

for clip, (keep, ref) in SOFTEN.items():
    soften(bpy.data.actions[clip], keep, ref)
    print("softened", clip, keep)


# ---- push-up (prone) clips: whole body pivots about the toes as a straight plank, hands planted on the floor
#      under the shoulders (two-bone IK baked to keys), elbows track back at ~45 degrees from the body.
def build_pushups():
    import mathutils
    from mathutils import Matrix, Quaternion
    bones = arm.data.bones
    H_ = Vector(bones["hips"].head_local)
    toe = (Vector(bones["foot_L"].tail_local) + Vector(bones["foot_R"].tail_local)) / 2
    sh = (Vector(bones["upper_arm_L"].head_local) + Vector(bones["upper_arm_R"].head_local)) / 2
    L_body = (sh - toe).length
    arm_len = (bones["upper_arm_L"].length + bones["forearm_L"].length + 0.6 * bones["hand_L"].length)
    rest_angle = math.atan2(sh.z - toe.z, -(sh.y - toe.y))          # rest: body vertical -> ~90 deg

    def plank(h_sh):
        """hips rotation (about X, forward pitch) and location so toes stay at the floor point and the shoulders
        are h_sh above the floor"""
        theta = math.asin(max(0.05, min(0.95, h_sh / L_body)))          # body angle above horizontal
        pitch = rest_angle - theta
        R = Matrix.Rotation(pitch, 3, "X")                               # positive X pitches the body forward
        toe_new = H_ + R @ (toe - H_)
        # toes on the floor; body centred on the origin along Y so the app frames it like the standing clips
        d = Vector((0, 0, 0.012)) - Vector((0, 0, toe_new.z)) + Vector((0, 0.5 * L_body + 0.10 - toe_new.y, 0))
        return pitch, d, R

    # IK targets: hands under the shoulders (a bit wider), on the floor; poles behind and out for the elbows
    tgt, pole = {}, {}
    pitch0, d0, R0 = plank(arm_len * 1.0 + 0.035)
    sh_top = {s_: H_ + R0 @ (Vector(bones[f"upper_arm_{s_}"].head_local) - H_) + d0 for s_ in ("L", "R")}
    for s_, sg in (("L", 1), ("R", -1)):
        e = bpy.data.objects.new(f"ik_{s_}", None); bpy.context.collection.objects.link(e)
        e.location = (sh_top[s_].x * 1.25, sh_top[s_].y - 0.02, 0.035)
        tgt[s_] = e
        p_ = bpy.data.objects.new(f"pole_{s_}", None); bpy.context.collection.objects.link(p_)
        p_.location = (sh_top[s_].x * 1.25 + sg * 0.35, sh_top[s_].y + 0.45, 0.45)
        pole[s_] = p_
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    cons = []
    for s_ in ("L", "R"):
        c = arm.pose.bones[f"forearm_{s_}"].constraints.new("IK")
        c.target = tgt[s_]; c.pole_target = pole[s_]; c.chain_count = 2; c.pole_angle = math.radians(45 if s_ == "L" else 135)
        cons.append((f"forearm_{s_}", c))
    bpy.ops.object.mode_set(mode="OBJECT")

    def bake(name, h_from, h_to, dur):
        act = bpy.data.actions.new(name); act.use_fake_user = True
        arm.animation_data.action = act
        n = int(round(dur * ta.FPS))
        for f in range(n + 1):
            t = ta.ease(f / n)
            h = h_from + (h_to - h_from) * t
            pitch, d, R = plank(h)
            for pb in arm.pose.bones:
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
            hb = arm.pose.bones["hips"]
            rest = bones["hips"].matrix_local.to_3x3()
            q = Quaternion((1, 0, 0), pitch)
            hb.rotation_quaternion = rest.to_quaternion().inverted() @ q @ rest.to_quaternion()
            hb.location = rest.inverted() @ d
            for s_ in ("L", "R"):                                         # toes tucked: feet flexed onto the toes
                fb = arm.pose.bones[f"foot_{s_}"]; fr = bones[f"foot_{s_}"].matrix_local.to_3x3().to_quaternion()
                fb.rotation_quaternion = fr.inverted() @ Quaternion((1, 0, 0), math.radians(-35)) @ fr
            sb = arm.pose.bones["spine"]; sr = bones["spine"].matrix_local.to_3x3().to_quaternion()
            sb.rotation_quaternion = sr.inverted() @ Quaternion((1, 0, 0), math.radians(8)) @ sr      # flatten the plank
            nb = arm.pose.bones["neck"]; nr = bones["neck"].matrix_local.to_3x3().to_quaternion()
            nb.rotation_quaternion = nr.inverted() @ Quaternion((1, 0, 0), math.radians(-28)) @ nr   # look at the floor ahead
            for fb_ in ("fingers_L", "fingers_R", "fingertips_L", "fingertips_R"):
                pass
            for pb in arm.pose.bones:
                if pb.name.split("_")[0] not in ("upper", "forearm", "hand"):
                    pb.keyframe_insert("rotation_quaternion", frame=f + 1)
                    pb.keyframe_insert("location", frame=f + 1)
        # arms: evaluate the IK and bake its visual result into keys on this action
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        for pb in arm.pose.bones:
            sel = pb.name.split("_")[0] in ("upper", "forearm", "hand")
            if hasattr(pb, "select"):
                pb.select = sel
            else:
                pb.bone.select = sel
        bpy.ops.nla.bake(frame_start=1, frame_end=n + 1, only_selected=True, visual_keying=True, clear_constraints=False,
                         use_current_action=True, bake_types={"POSE"}, channel_types={"ROTATION"})
        bpy.ops.object.mode_set(mode="OBJECT")
        # hands flat on the floor: fingers forward (-Y), palm down, per frame (after the arm IK bake)
        for f in range(1, n + 2):
            sc.frame_set(f)
            for s_, sg in (("L", 1), ("R", -1)):
                pb = arm.pose.bones[f"hand_{s_}"]
                M = pb.matrix.copy()
                rest_rot = bones[f"hand_{s_}"].matrix_local.to_3x3()
                cur = M.to_3x3()
                d_now = (cur @ rest_rot.inverted() @ (Vector(bones[f"hand_{s_}"].tail_local) - Vector(bones[f"hand_{s_}"].head_local)).normalized())
                palm_now = cur @ rest_rot.inverted() @ Vector((-sg, 0, 0))
                def frame(a, b):
                    a = a.normalized(); b = (b - a * b.dot(a)).normalized(); return Matrix((a, b, a.cross(b))).transposed()
                R = frame(Vector((0.0, -1.0, -0.12)), Vector((0, 0, -1))) @ frame(d_now, palm_now).inverted()
                pb.matrix = Matrix.Translation(M.translation) @ (R @ cur).to_4x4()
                bpy.context.view_layer.update()
                pb.keyframe_insert("rotation_quaternion", frame=f)
        act.frame_range = (1, n + 1)
        return act

    top, bottom = arm_len * 1.0 + 0.035, 0.37 * HEIGHT / 1.7
    bake("pushup_down", top, bottom, 1.4)
    bake("pushup_up", bottom, top, 1.2)
    for bn, c in cons:
        arm.pose.bones[bn].constraints.remove(c)
    for o in list(tgt.values()) + list(pole.values()):
        bpy.data.objects.remove(o)
    arm.animation_data.action = None


build_pushups()

# ---- foot lock: while a foot is on the floor and nearly still, pin it where it landed (removes foot skating
#      from retargeted mocap and from hand-keyed hip motion); two-bone analytic IK on thigh/shin, foot keeps its
#      world orientation.
def foot_lock(act, planted=False, pin_start=False):
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    frames = list(range(a_, b_ + 1))
    if planted:
        # stationary drill: hold the hips' horizontal position at its average (keep the bounce), feet pinned all clip
        hb = arm.pose.bones["hips"]
        locs = []
        for f in frames:
            sc.frame_set(f)
            locs.append(hb.location.copy())
        mean = sum(locs, Vector()) / len(locs)
        rest3 = arm.data.bones["hips"].matrix_local.to_3x3()
        for f, l in zip(frames, locs):
            w = rest3 @ l
            wm = rest3 @ mean
            hb.location = rest3.inverted() @ Vector((wm.x, wm.y, w.z))
            hb.keyframe_insert("location", frame=f)
    track = {"L": [], "R": []}
    for f in frames:
        sc.frame_set(f)
        for s_ in ("L", "R"):
            track[s_].append(Vector(arm.pose.bones[f"foot_{s_}"].head))
    ground = min(min(p.z for p in track[s_]) for s_ in track)
    for s_ in ("L", "R"):
        P = track[s_]
        n = len(P)
        contact = []
        for i in range(n):
            v = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).xy.length / (2 / ta.FPS)
            contact.append(planted or pin_start or (P[i].z < ground + 0.03 and v < 0.45))
        # segments
        segs, i = [], 0
        while i < n:
            if contact[i]:
                j = i
                while j + 1 < n and contact[j + 1]:
                    j += 1
                if j - i >= 2:
                    segs.append((i, j))
                i = j + 1
            else:
                i += 1
        target = list(P)
        weight = [0.0] * n
        for (i0, i1) in segs:
            anchor = (sum(P, Vector()) / n) if planted else P[(i0 + i1) // 2].copy()
            if pin_start:                                   # squats: both feet stay exactly where they started
                anchor = P[0].copy() if act.name.endswith("_down") else P[-1].copy()
            if planted:
                anchor.z = 0
            for k in range(i0, i1 + 1):
                target[k] = Vector((anchor.x, anchor.y, min(P[k].z, ground + 0.006) if planted else (anchor.z if pin_start else P[k].z)))
                weight[k] = 1.0
            for k in range(1, 4):                                   # blend in / out over 3 frames
                for kk, w in ((i0 - k, 1 - k / 4), (i1 + k, 1 - k / 4)):
                    if 0 <= kk < n and weight[kk] < w:
                        weight[kk] = w
                        target[kk] = P[kk].lerp(Vector((anchor.x, anchor.y, P[kk].z)), w)
        for k, f in enumerate(frames):
            if weight[k] <= 0.0 or (target[k] - P[k]).length < 0.002:
                continue
            sc.frame_set(f)
            th, sh_, ft = arm.pose.bones[f"thigh_{s_}"], arm.pose.bones[f"shin_{s_}"], arm.pose.bones[f"foot_{s_}"]
            foot_m = ft.matrix.copy()
            Hp, K, A = Vector(th.head), Vector(sh_.head), Vector(ft.head)
            A2 = target[k]
            l1, l2 = (K - Hp).length, (A - K).length
            dvec = A2 - Hp
            dist = min(dvec.length, l1 + l2 - 1e-4)
            dn = dvec.normalized()
            bend = (K - Hp) - dn * (K - Hp).dot(dn)                     # keep the knee's bend direction
            if pin_start:                                               # squat: knees track over the toes
                want = Vector((0.28 if s_ == "L" else -0.28, -1.0, 0.0))
                bend = want - dn * want.dot(dn)
            if bend.length < 1e-5:
                bend = Vector((0, -1, 0))
            bend.normalize()
            a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            K2 = Hp + dn * a + bend * h
            for pb, tail in ((th, K2), (sh_, Hp + dn * dist)):
                M = pb.matrix.copy()
                cur = (Vector(pb.tail) - Vector(pb.head)).normalized()
                q = cur.rotation_difference((tail - Vector(pb.head)).normalized())
                pb.matrix = Matrix.Translation(M.translation) @ (q.to_matrix() @ M.to_3x3()).to_4x4()
                bpy.context.view_layer.update()
            ft.matrix = Matrix.Translation(Vector(ft.head)) @ foot_m.to_3x3().to_4x4()
            bpy.context.view_layer.update()
            for pb in (th, sh_, ft):
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


from mathutils import Matrix  # noqa: E402
for act in list(bpy.data.actions):
    if not act.name.startswith("pushup_"):
        foot_lock(act, planted=act.name in ("boxing_stance", "idle_neutral"), pin_start=act.name.startswith("squat_"))
print("foot lock done")


# ---- guard height: the boxing takes drop the non-punching hand to chest height between punches; a beginner lesson
#      should show the guard at the chin. Whenever an arm is retracted, pull its wrist (two-bone IK, elbow keeps its
#      bend direction, fist keeps its orientation) to the stance clip's average guard position relative to the head (fists stay at the chin).
def guard_targets(ref):
    pbs = arm.pose.bones
    arm.animation_data.action = ref
    ra, rb = [int(x) for x in ref.frame_range]
    acc = {"L": Vector(), "R": Vector()}
    for f in range(ra, rb + 1):
        sc.frame_set(f)
        ci = pbs["head"].matrix.inverted()
        for s_ in acc:
            acc[s_] += ci @ Vector(pbs[f"hand_{s_}"].head)
    arm.animation_data.action = None
    return {s_: v / (rb - ra + 1) for s_, v in acc.items()}


# the recorded boxer holds his fists at eyebrow height (rear one higher); a beginner guard sits at the chin
GUARD_DROP = {"L": 0.04 * HEIGHT / 1.8, "R": 0.10 * HEIGHT / 1.8}


def guard_fix(act, guard):
    pbs = arm.pose.bones
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        for s_ in ("L", "R"):
            ua, fa, hd = pbs[f"upper_arm_{s_}"], pbs[f"forearm_{s_}"], pbs[f"hand_{s_}"]
            S, K, W = Vector(ua.head), Vector(fa.head), Vector(hd.head)
            l1, l2 = (K - S).length, (W - K).length
            ext = (W - S).length / (l1 + l2)
            w = min(max((0.80 - ext) / 0.20, 0.0), 1.0)
            w = w * w * (3 - 2 * w)
            if w < 0.01:
                continue
            target = W.lerp(pbs["head"].matrix @ guard[s_] - Vector((0, 0, GUARD_DROP[s_])), w)
            hand_m = hd.matrix.copy()
            dvec = target - S
            dist = min(dvec.length, l1 + l2 - 1e-4)
            dn = dvec.normalized()
            bend = (K - S) - dn * (K - S).dot(dn)
            bend = bend.normalized() if bend.length > 1e-5 else Vector((0, 0, -1))
            a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            K2 = S + dn * a + bend * h
            for pb, tail in ((ua, K2), (fa, S + dn * dist)):
                M = pb.matrix.copy()
                cur = (Vector(pb.tail) - Vector(pb.head)).normalized()
                q = cur.rotation_difference((tail - Vector(pb.head)).normalized())
                pb.matrix = Matrix.Translation(M.translation) @ (q.to_matrix() @ M.to_3x3()).to_4x4()
                bpy.context.view_layer.update()
            hd.matrix = Matrix.Translation(Vector(hd.head)) @ hand_m.to_3x3().to_4x4()
            bpy.context.view_layer.update()
            for pb in (ua, fa, hd):
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


_guard = guard_targets(bpy.data.actions["boxing_stance"])
for clip in ("boxing_stance", "boxing_jab", "boxing_cross"):
    guard_fix(bpy.data.actions[clip], _guard)
print("guard fix done")

# ---- hands: closed fist in every boxing clip, relaxed elsewhere, open and flat for the push-up
GRIP = {"boxing_": 0.95, "footwork_": 0.95, "pushup_": 0.0}


def key_grip(act, amount):
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    for s_ in ("L", "R"):
        for bn, (axis, deg) in ((f"fingers_{s_}", ta.grip(s_, amount)[f"fingers_{s_}"][0][1]), (f"fingertips_{s_}", ta.grip(s_, amount)[f"fingertips_{s_}"][0][1])):
            pb = arm.pose.bones[bn]
            rq = arm.data.bones[bn].matrix_local.to_3x3().to_quaternion()
            from mathutils import Quaternion
            q = rq.inverted() @ Quaternion(Vector(axis).normalized(), math.radians(deg)) @ rq
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            for f in range(a_, b_ + 1):
                pb.keyframe_insert("rotation_quaternion", frame=f)


for act in bpy.data.actions:
    amt = next((v for k, v in GRIP.items() if act.name.startswith(k)), 0.4)
    key_grip(act, amt)
arm.animation_data.action = None

# ---- floor contact: after baking, lift / lower the hips each frame so the lowest point of the shoes touches the floor
foot_vs = np.array([vv.index for vv in lo.data.vertices if vv.co.z < 0.13 * H])
ground_rest = float(min(lo.data.vertices[i].co.z for i in foot_vs))
hips_pb = arm.pose.bones["hips"]
for act in bpy.data.actions:
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    fc = [c for c in act.fcurves if c.data_path == 'pose.bones["hips"].location'] if hasattr(act, "fcurves") else []
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = lo.evaluated_get(dg)
        m2 = ev.to_mesh()
        zmin = min(m2.vertices[i].co.z for i in foot_vs)
        ev.to_mesh_clear()
        dz = ground_rest - zmin
        if abs(dz) > 0.002:
            rest_m = arm.data.bones["hips"].matrix_local.to_3x3()
            hips_pb.location = hips_pb.location + rest_m.inverted() @ Vector((0, 0, dz))
            hips_pb.keyframe_insert("location", frame=f)
arm.animation_data.action = None
print("TRIS", sum(len(p.vertices) - 2 for p in lo.data.polygons))

# ---- rigged coach: carry every finished clip over to the owner's skeleton and export that instead
if RIGGED:
    names = [a.name for a in bpy.data.actions]
    for n in names:
        bpy.data.actions[n].name = "src_" + n
    for n in names:
        rc.transfer(arm, mx_arm, bpy.data.actions["src_" + n], sc, n)
    if not os.environ.get("KEEP_SRC"):
        for n in names:
            bpy.data.actions.remove(bpy.data.actions["src_" + n])
    rc.prepare_textures(mx_mesh)
    print("transferred", len(names), "clips to the rigged coach")

# ---------------------------------------------------------------- save + export
for img in out.values():
    img.pack()
mrimg.pack()
blend = os.path.join(ROOT, "assets/blender/source", NAME + ".blend")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
exp = os.path.join(ROOT, "assets/blender/exports", NAME + ".glb")
bpy.ops.object.select_all(action="DESELECT")
if RIGGED:
    mx_mesh.select_set(True)
    mx_arm.select_set(True)
else:
    lo.select_set(True)
    arm.select_set(True)
bpy.ops.export_scene.gltf(filepath=exp, export_format="GLB", use_selection=True, export_yup=True, export_apply=False, export_texcoords=True,
                          export_normals=True, export_tangents=True, export_materials="EXPORT", export_image_format="JPEG", export_jpeg_quality=88,
                          export_skins=True, export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                          export_frame_range=False, export_anim_single_armature=True, export_reset_pose_bones=True)


def fix_tangents(path):
    """Faces with zero UV area get a zero TANGENT from the exporter (invalid glTF); give them any unit vector
    perpendicular to the normal, w = 1. Patched in place, same byte layout."""
    import json as _json, struct as _struct
    data = bytearray(open(path, "rb").read())
    jlen = _struct.unpack_from("<I", data, 12)[0]
    gj = _json.loads(bytes(data[20:20 + jlen]))
    bin0 = 20 + jlen + 8
    fixed = 0
    for mesh in gj["meshes"]:
        for prim in mesh["primitives"]:
            at = prim["attributes"]
            if "TANGENT" not in at:
                continue

            def view(acc_i, comps):
                acc = gj["accessors"][acc_i]
                bv = gj["bufferViews"][acc["bufferView"]]
                off = bin0 + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                return np.frombuffer(data, np.float32, acc["count"] * comps, off).reshape(-1, comps), off
            t, toff = view(at["TANGENT"], 4)
            n, _ = view(at["NORMAL"], 3)
            t = t.copy()
            bad = np.linalg.norm(t[:, :3], axis=1) < 0.5
            for i in np.nonzero(bad)[0]:
                nn = n[i] / max(np.linalg.norm(n[i]), 1e-9)
                a = np.array([1.0, 0, 0]) if abs(nn[0]) < 0.9 else np.array([0, 1.0, 0])
                tt = np.cross(nn, a)
                tt /= np.linalg.norm(tt)
                t[i] = (*tt, 1.0)
            fixed += int(bad.sum())
            data[toff:toff + t.nbytes] = t.astype(np.float32).tobytes()
    open(path, "wb").write(bytes(data))
    print("fixed tangents", fixed)


fix_tangents(exp)
print("EXPORTED", exp, os.path.getsize(exp))
ORDER = [n for n, _, _ in ta.clip_specs()] + ["pushup_down", "pushup_up"]
manifest = {"asset": f"models/{NAME}.glb", "generator": "tools/blender/build_coach_mesh.py", "fps": ta.FPS,
            "clips": [{"name": n, "durationSeconds": round((bpy.data.actions[n].frame_range[1] - bpy.data.actions[n].frame_range[0]) / ta.FPS, 3),
                       "reviewStatus": "draft_pending_coach_review"} for n in ORDER]}
if "--app" in args:
    shutil.copyfile(exp, os.path.join(ROOT, "app/src/main/assets/models", NAME + ".glb"))
    with open(os.path.join(ROOT, "app/src/main/assets/models", NAME + ".clips.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
