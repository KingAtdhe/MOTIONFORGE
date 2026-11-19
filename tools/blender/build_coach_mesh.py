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
for g in list(lo.vertex_groups):
    if g.name.startswith("finger"):
        lo.vertex_groups.remove(g)      # the sculpted hands are already loosely closed; fingers stay rigid
_ua = J["forearm_L"] - J["upper_arm_L"]
ta.REST_ARM = math.degrees(math.atan2(abs(_ua.x), -_ua.z))
ta.LEG_THIGH = (J["shin_L"] - J["thigh_L"]).length
ta.LEG_SHIN = (J["foot_L"] - J["shin_L"]).length
print("rest arm", round(ta.REST_ARM, 1), "legs", round(ta.LEG_THIGH, 3), round(ta.LEG_SHIN, 3))
# guard: fists in front of the chin, clear of a sculpted (bulkier) chest
ta.G_LEAD_FWD, ta.G_LEAD_FLEX, ta.G_LEAD_TUCK = 52, 112, 4
ta.G_REAR_FWD, ta.G_REAR_FLEX, ta.G_REAR_TUCK = 50, 120, 6
ta.build_clips(arm)


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
        d = Vector((0, 0, 0.012)) - Vector((0, 0, toe_new.z)) + Vector((0, toe.y - toe_new.y + 0.35 * L_body, 0))
        return pitch, d, R

    # IK targets: hands under the shoulders (a bit wider), on the floor; poles behind and out for the elbows
    tgt, pole = {}, {}
    pitch0, d0, R0 = plank(arm_len * 0.97)
    sh_top = {s_: H_ + R0 @ (Vector(bones[f"upper_arm_{s_}"].head_local) - H_) + d0 for s_ in ("L", "R")}
    for s_, sg in (("L", 1), ("R", -1)):
        e = bpy.data.objects.new(f"ik_{s_}", None); bpy.context.collection.objects.link(e)
        e.location = (sh_top[s_].x * 1.25, sh_top[s_].y - 0.02, 0.05)
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
        act.frame_range = (1, n + 1)
        return act

    top, bottom = arm_len * 0.97, 0.20 * HEIGHT / 1.7
    bake("pushup_down", top, bottom, 1.4)
    bake("pushup_up", bottom, top, 1.2)
    for bn, c in cons:
        arm.pose.bones[bn].constraints.remove(c)
    for o in list(tgt.values()) + list(pole.values()):
        bpy.data.objects.remove(o)
    arm.animation_data.action = None


build_pushups()

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
            "clips": [{"name": n, "durationSeconds": round(dd, 3), "reviewStatus": "draft_pending_coach_review"} for n, dd, _ in ta.clip_specs()]
                     + [{"name": "pushup_down", "durationSeconds": 1.4, "reviewStatus": "draft_pending_coach_review"},
                        {"name": "pushup_up", "durationSeconds": 1.2, "reviewStatus": "draft_pending_coach_review"}]}
if "--app" in args:
    shutil.copyfile(exp, os.path.join(ROOT, "app/src/main/assets/models", NAME + ".glb"))
    with open(os.path.join(ROOT, "app/src/main/assets/models", NAME + ".clips.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
