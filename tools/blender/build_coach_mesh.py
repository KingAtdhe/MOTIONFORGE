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
# (light meshes have few vertices per band: wider band, and a fallback; with --rigged the joints come from the skeleton)
crotch = next((z for z in zz if (np.abs(band(z, 0.006)[:, 0]) < 0.015).sum() > 3), 0.47 * H)
RIGGED = args[args.index("--rigged") + 1] if "--rigged" in args else None
J = {}
# with --rigged the joints come from the owner's skeleton (rigged_coach.joints); measuring them on the mesh is only
# needed for unrigged sources (and fails on light or T-posed meshes)
if not RIGGED:
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

from mathutils import Matrix  # noqa: E402
LEGACY_MOCAP = bool(os.environ.get("MF_LEGACY_MOCAP"))
if LEGACY_MOCAP:
    # recorded takes (video landmarks / CMU mocap): kept for comparison only, see legacy_mocap_clips.py
    exec(compile(open(os.path.join(HERE, "legacy_mocap_clips.py")).read(), "legacy_mocap_clips.py", "exec"), globals())


GRIP = {"boxing_": 0.95, "footwork_": 0.95, "pushup_": 0.0, "warmup_": 0.5}  # everything else: relaxed hands (below)


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


# ---- demonstration clips: authored from biomechanical rules (tools/blender/authored_clips.py)
if not LEGACY_MOCAP:
    import authored_clips as ac  # noqa: E402
    ac.build_all(arm, HEIGHT, NAME)
for act in bpy.data.actions:
    amt = next((v for k, v in GRIP.items() if act.name.startswith(k)), 0.22)
    key_grip(act, amt)
arm.animation_data.action = None

# ---- floor contact: after baking, lift / lower the hips each frame so the lowest point of the shoes touches the floor
foot_vs = np.array([vv.index for vv in lo.data.vertices if vv.co.z < 0.13 * H])
ground_rest = float(min(lo.data.vertices[i].co.z for i in foot_vs))
hips_pb = arm.pose.bones["hips"]
# (rigged coaches: the stand-in mesh's feet do not follow the feet reliably, so the floor is fixed on the real mesh after the transfer)
for act in ([] if RIGGED else bpy.data.actions):
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
    rc.repair_mesh(mx_mesh)
    rc.strip_hand_leaks(mx_mesh)
    if "--fix-shorts" in args:
        rc.fix_shorts(mx_mesh, mx_arm)
    rc.prepare_textures(mx_mesh)
    rc.floor_contact(mx_arm, mx_mesh, sc, names)
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
