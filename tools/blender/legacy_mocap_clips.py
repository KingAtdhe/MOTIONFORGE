"""Legacy clip pipeline: clips retargeted from the recorded takes in assets/mocap (video landmarks and CMU mocap),
plus the foot-lock, guard and pose clean-up passes written for them.

Not part of the normal build. The shipped clips are authored in authored_clips.py. build_coach_mesh.py executes this
file inside its own namespace only when MF_LEGACY_MOCAP=1, so the takes can still be built for comparison.
"""
# ruff: noqa
# ---- recorded motion (CMU mocap, assets/mocap) replaces the hand-keyed clips where a clean take exists
import mocap_retarget as mr  # noqa: E402
MOCAP = {  # clip: (take, first frame, last frame, loops, frames easing back to the first pose)
    "idle_neutral": ("111_28", 10, 100, True, 0),
    "boxing_stance": ("13_18", 113, 142, True, 0),
    # 13_18 only has jab-cross combinations: keep the jab (peak f99) and ease back to guard before the cross starts
    "boxing_jab": ("13_18", 88, 104, False, 14),
    # cross (peak f33) from the same combination; the lead arm holds its guard pose from f15 (before the jab)
    "boxing_cross": ("13_18", 22, 42, False, 10),
    # tracked from real-person stock videos with MediaPipe (tools/mocap, see assets/mocap/README.md)
    "warmup_march": ("vid_march", 94, 275, True, 0),      # two full left-right cycles, looped
    "squat_down": ("vid_squat", 6, 50, False, 0),          # standing -> bottom (video slowed to 0.6x)
    "squat_up": ("vid_squat", 50, 88, False, 0),           # bottom -> standing
    # only the flat-back first part of a forward bend (before it rounds into a toe touch), slowed; up = reversed
    "hip_hinge_down": ("vid_hinge_down", 0, 54, False, 0),
    "hip_hinge_up": ("vid_hinge_up", 0, 48, False, 0),
    # side-view gym push-up (Pexels 4742661): lowering slowed to 0.7x, pushing up sped to 1.6x for an even tempo;
    # hands are planted on the floor afterwards (plant_hands)
    "pushup_down": ("vid_pushup_down", 0, 43, False, 0),
    "pushup_up": ("vid_pushup_up", 0, 42, False, 0),
    # CMU 15_13 push-step drill (frames 70-145, mirrored to an orthodox stance): lead foot steps in, rear follows,
    # then back out. Legs and travel come from the recording; the upper body is replaced by the recorded guard
    # below (the performer jabs while stepping, which the footwork lesson doesn't teach). Backward = the same drill
    # started from the stepped-in position, so it retreats first.
    "footwork_forward": ("15_13_steps", 5, 48, False, 0),
    "footwork_backward": ("15_13_steps_back", 0, 43, False, 0),
}
# (tried: CMU 13_29 squat softened toward standing — blending a deep squat's joint rotations doesn't give a natural
#  shallow squat (knees shoot forward, hips stay under the body), so the squat stays hand-keyed with mocap-like timing)
# blend recorded poses toward the standing frame: keeps the performer's timing, balance and torso/hip coordination
# but at a beginner depth (knees ~95 deg instead of a full deep squat). value: (amount kept, standing frame)
SOFTEN = {}
HOLD = {"boxing_cross": ("L", 15)}
# the performer stands bladed, so "hips forward" is ~45 deg off the punching line; turn the boxing takes so punches
# go straight at the viewer's target (-Y), like the hand-keyed footwork / guard clips
TURN = {"boxing_stance": -40.0, "boxing_jab": -40.0, "boxing_cross": -20.0, "footwork_forward": -40.0, "footwork_backward": -40.0}
for clip, (take, f0, f1, loops, settle) in MOCAP.items():
    old_act = bpy.data.actions.get(clip)
    if old_act:
        bpy.data.actions.remove(old_act)
    act_, _ = mr.retarget(arm, np.load(os.path.join(ROOT, "assets/mocap", take + ".npz")), f0, f1, clip, loop=loops, settle=settle, hold=HOLD.get(clip), turn=TURN.get(clip, 0.0))
    act_.name = clip
    print("mocap", clip, take, f0, f1)


def _dbg(tag):
    if not os.environ.get("MF_DEBUG"):
        return
    for cn in ("squat_down", "hip_hinge_down"):
        a_ = bpy.data.actions.get(cn)
        if a_ is None:
            continue
        arm.animation_data.action = a_
        o = []
        for f in (int(a_.frame_range[0]), int(a_.frame_range[1])):
            sc.frame_set(f)
            o.append((round(arm.pose.bones["hips"].head.z, 3), round(arm.pose.bones["foot_L"].head.z, 3)))
        arm.animation_data.action = None
        print("DBG", tag, cn, "hips/foot z first,last", o)


_dbg("retarget")


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
    lift_head(bpy.data.actions[clip], keep=0.12)   # head up: eyes look over the gloves instead of hiding behind them

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



def plant_hands(acts):
    """Recorded push-ups: pin each hand to one spot on the floor for both clips (the tracked wrists slide and hover a
    little), elbows keep their recorded direction (IK pole from the average elbow), palm flat, fingers forward."""
    from mathutils import Matrix
    bones = arm.data.bones
    spots, poles = {"L": [], "R": []}, {"L": [], "R": []}
    for act in acts:
        arm.animation_data.action = act
        a_, b_ = [int(x) for x in act.frame_range]
        for f in range(a_, b_ + 1):
            sc.frame_set(f)
            for s_ in ("L", "R"):
                spots[s_].append(Vector(arm.pose.bones[f"hand_{s_}"].head))
                poles[s_].append(Vector(arm.pose.bones[f"forearm_{s_}"].head) - Vector(arm.pose.bones[f"upper_arm_{s_}"].head))
    tgt, pole, cons = {}, {}, []
    for s_ in ("L", "R"):
        P_ = sum(spots[s_], Vector()) / len(spots[s_])
        e = bpy.data.objects.new(f"pik_{s_}", None); bpy.context.collection.objects.link(e)
        e.location = (P_.x, P_.y, 0.035)
        tgt[s_] = e
        sh0 = Vector(arm.pose.bones[f"upper_arm_{s_}"].head)
        el = sum(poles[s_], Vector()) / len(poles[s_])
        p_ = bpy.data.objects.new(f"ppole_{s_}", None); bpy.context.collection.objects.link(p_)
        p_.location = sh0 + el.normalized() * 0.6 + Vector((0, 0, 0.2))
        pole[s_] = p_
        c = arm.pose.bones[f"forearm_{s_}"].constraints.new("IK")
        c.target = e; c.pole_target = p_; c.chain_count = 2; c.pole_angle = math.radians(-90)
        cons.append((f"forearm_{s_}", c))
    for act in acts:
        arm.animation_data.action = act
        a_, b_ = [int(x) for x in act.frame_range]
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        for pb in arm.pose.bones:
            sel = pb.name.split("_")[0] in ("upper", "forearm")
            if hasattr(pb, "select"):
                pb.select = sel
            else:
                pb.bone.select = sel
        bpy.ops.nla.bake(frame_start=a_, frame_end=b_, only_selected=True, visual_keying=True, clear_constraints=False,
                         use_current_action=True, bake_types={"POSE"}, channel_types={"ROTATION"})
        bpy.ops.object.mode_set(mode="OBJECT")
    for bn, c in cons:
        arm.pose.bones[bn].constraints.remove(c)
    for o in list(tgt.values()) + list(pole.values()):
        bpy.data.objects.remove(o)
    # palms flat, fingers pointing ahead of the body (head direction is -Y)
    def frame(a, b):
        a = a.normalized(); b = (b - a * b.dot(a)).normalized(); return Matrix((a, b, a.cross(b))).transposed()
    for act in acts:
        arm.animation_data.action = act
        a_, b_ = [int(x) for x in act.frame_range]
        for f in range(a_, b_ + 1):
            sc.frame_set(f)
            for s_, sg in (("L", 1), ("R", -1)):
                pb = arm.pose.bones[f"hand_{s_}"]
                M = pb.matrix.copy()
                rest_rot = bones[f"hand_{s_}"].matrix_local.to_3x3()
                cur = M.to_3x3()
                d_now = cur @ rest_rot.inverted() @ (Vector(bones[f"hand_{s_}"].tail_local) - Vector(bones[f"hand_{s_}"].head_local)).normalized()
                palm_now = cur @ rest_rot.inverted() @ Vector((-sg, 0, 0))
                R = frame(Vector((0.0, -1.0, -0.12)), Vector((0, 0, -1))) @ frame(d_now, palm_now).inverted()
                pb.matrix = Matrix.Translation(M.translation) @ (R @ cur).to_4x4()
                bpy.context.view_layer.update()
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


if "pushup_down" in bpy.data.actions and "pushup_up" in bpy.data.actions:
    plant_hands([bpy.data.actions["pushup_down"], bpy.data.actions["pushup_up"]])
    print("push-ups from video, hands planted")
else:
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
        foot_lock(act, planted=act.name in ("boxing_stance", "idle_neutral"), pin_start=act.name.startswith(("squat_", "hip_hinge_")))  # footwork: planted-foot detection pins each landing
print("foot lock done")
_dbg("footlock")


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
# fists at chin / cheekbone height (the wrists sit ~9 cm below the knuckles of a closed fist held upright)
GUARD_DROP = {"L": 0.15 * HEIGHT / 1.8, "R": 0.19 * HEIGHT / 1.8}


def guard_fix(act, guard, drop=None):
    drop = drop or GUARD_DROP
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
            target = W.lerp(pbs["head"].matrix @ guard[s_] - Vector((0, 0, drop[s_])), w)
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
_dbg("guard")

# squat: the recorded performer holds her clasped hands at her chin, which reads as a boxing guard on the coach.
# Same two-bone fix, hands lowered to the middle of the chest (clasped in front, the usual teaching position).
def ik_hands(act, target_at):
    """two-bone arm IK per frame toward target_at(side, shoulder_pos) (world); elbow keeps its bend direction,
    the hand keeps its orientation."""
    from mathutils import Matrix as _M
    pbs = arm.pose.bones
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        for s_ in ("L", "R"):
            ua, fa, hd = pbs[f"upper_arm_{s_}"], pbs[f"forearm_{s_}"], pbs[f"hand_{s_}"]
            S, K = Vector(ua.head), Vector(fa.head)
            l1, l2 = (K - S).length, (Vector(hd.head) - K).length
            target = target_at(s_, S)
            hand_m = hd.matrix.copy()
            dvec = target - S
            dist = min(dvec.length, l1 + l2 - 1e-4)
            dn = dvec.normalized()
            bend = (K - S) - dn * (K - S).dot(dn)
            bend = bend.normalized() if bend.length > 1e-5 else Vector((0, 0.3, -1)).normalized()
            a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            K2 = S + dn * a + bend * h
            for pb, tail in ((ua, K2), (fa, S + dn * dist)):
                M = pb.matrix.copy()
                cur = (Vector(pb.tail) - Vector(pb.head)).normalized()
                q = cur.rotation_difference((tail - Vector(pb.head)).normalized())
                pb.matrix = _M.Translation(M.translation) @ (q.to_matrix() @ M.to_3x3()).to_4x4()
                bpy.context.view_layer.update()
            hd.matrix = _M.Translation(Vector(hd.head)) @ hand_m.to_3x3().to_4x4()
            bpy.context.view_layer.update()
            for pb in (ua, fa, hd):
                pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None




# ---- pose clean-up for the coaches' build. The recordings come from slim performers; on these very muscular bodies
#      their arms sink into the lats and the legs press together. Small, constant world-space corrections:
def spread(act, bones_deg):
    """rotate each listed bone about the world forward axis (Y) at its head, every frame; positive = away from the
    body's midline for that side. Feet get the opposite turn so the soles stay flat."""
    from mathutils import Matrix as _M
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        for bn, deg in bones_deg:
            sgn = -1.0 if bn.endswith("_L") else 1.0          # left side is +X: rotate about +Y by a negative angle
            pb = arm.pose.bones[bn]
            hd = Vector(pb.head)
            R = _M.Translation(hd) @ _M.Rotation(math.radians(deg) * sgn, 4, "Y") @ _M.Translation(-hd)
            pb.matrix = R @ pb.matrix
            bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


def straighten(act, bones_keep):
    """keep only part of each bone's own (local) bend: a rounded back becomes a flat back, the bend stays at the hips."""
    from mathutils import Quaternion
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    vals = {}
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        vals[f] = {bn: arm.pose.bones[bn].rotation_quaternion.copy() for bn, _ in bones_keep}
    for f, d in vals.items():
        for bn, keep in bones_keep:
            pb = arm.pose.bones[bn]
            pb.rotation_quaternion = Quaternion().slerp(d[bn], keep)
            pb.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None


_k = HEIGHT / 1.8
# (the 2026-11 coaches have realistic athletic builds; the old bodybuilder coaches needed 12-15 degrees)
_legs = [("thigh_L", 3.0), ("thigh_R", 3.0), ("foot_L", -3.0), ("foot_R", -3.0)]
_arms = [("upper_arm_L", 5.0), ("upper_arm_R", 5.0)]
spread(bpy.data.actions["idle_neutral"], _legs + _arms)       # hip-width feet, arms hang clear of the body
spread(bpy.data.actions["warmup_march"], _arms)
# hip hinge: the recorded forward bend rounds the back and drops the head; a hinge keeps the back flat
for clip in ("hip_hinge_down", "hip_hinge_up"):
    straighten(bpy.data.actions[clip], [("spine", 0.35), ("chest", 0.3), ("neck", 0.4), ("head", 0.4)])
    # arms hang straight down from the shoulders, slightly ahead of the legs
    ik_hands(bpy.data.actions[clip], lambda s_, S: S + Vector(((0.04 if s_ == "L" else -0.04) * _k, -0.04 * _k, -0.62 * _k)))
_k = HEIGHT / 1.8
if "squat_down" in bpy.data.actions:
    # squat: arms reach forward at shoulder height as a counterbalance (the recording holds the hands at the chin)
    def _sq_target(s_, S):
        return S + Vector(((0.07 if s_ == "L" else -0.07) * _k, -0.52 * _k, -0.06 * _k))
    for clip in ("squat_down", "squat_up"):
        straighten(bpy.data.actions[clip], [("neck", 0.35), ("head", 0.35)])    # eyes ahead, not at the floor
        ik_hands(bpy.data.actions[clip], _sq_target)
    print("squat hands lowered")

# march: the recording holds both hands still in front of the waist. Natural marching swings each arm with the
# opposite leg: hand target moves forward when the other knee is up, back when its own knee is up, elbow ~90 deg.
_m = bpy.data.actions["warmup_march"]
arm.animation_data.action = _m
_ma, _mb = [int(x) for x in _m.frame_range]
_kz = []
for f in range(_ma, _mb + 1):
    sc.frame_set(f)
    _kz.append(arm.pose.bones["shin_L"].head.z - arm.pose.bones["shin_R"].head.z)
_amp = max(1e-3, max(abs(x) for x in _kz))
arm.animation_data.action = None


def _march_target(s_, S):
    f = sc.frame_current
    lift = _kz[f - _ma] / _amp                      # +1: left knee up, -1: right knee up
    swing = -lift if s_ == "L" else lift            # each arm goes forward with the opposite knee
    fwd = (0.06 + 0.30 * swing) * _k                # -Y is forward
    return S + Vector(((0.08 if s_ == "L" else -0.08) * _k, -fwd, (-0.44 + 0.12 * max(swing, 0)) * _k))


straighten(_m, [("spine", 0.3), ("chest", 0.3), ("neck", 0.5), ("head", 0.5)])   # tall torso, eyes ahead
ik_hands(_m, _march_target)

# hip hinge: the performer never stands fully up; start the lowering from, and finish the rising in, the standing pose


def _blend_ends(act, at_start, span=0.35):
    from mathutils import Quaternion
    poses = sample(act)
    n = len(poses)
    k = max(2, int(n * span))
    arm.animation_data.action = act
    a_ = int(act.frame_range[0])
    for i in range(n):
        w = 0.0
        if at_start and i < k:
            w = 1.0 - (i / k)
        if not at_start and i >= n - k:
            w = (i - (n - k)) / k
        if w <= 0:
            continue
        w = w * w * (3 - 2 * w)
        for bn in ("spine", "chest", "neck", "head", "thigh_L", "thigh_R", "shin_L", "shin_R", "foot_L", "foot_R"):
            q0 = poses[i][bn][0]; q1 = _idle0[bn][0]
            if q0.dot(q1) < 0:
                q1 = -q1
            pb = arm.pose.bones[bn]
            pb.rotation_quaternion = q0.slerp(q1, w)
            pb.keyframe_insert("rotation_quaternion", frame=a_ + i)
        hb = arm.pose.bones["hips"]
        q0 = poses[i]["hips"][0]; q1 = _idle0["hips"][0]
        if q0.dot(q1) < 0:
            q1 = -q1
        hb.rotation_quaternion = q0.slerp(q1, w)
        hb.location = poses[i]["hips"][1].lerp(_idle0["hips"][1], w)
        hb.keyframe_insert("rotation_quaternion", frame=a_ + i); hb.keyframe_insert("location", frame=a_ + i)
    arm.animation_data.action = None
print("pose clean-up done")
_dbg("cleanup")


# ---- recorded upper body for the two drills that have no clean recording of their own
#      guard return: the recorded stance (13_18, guard-fixed) all clip long, the lead arm moves part of the way toward
#      the recorded jab's extended pose and comes straight back to guard.
#      footwork: the recorded push-steps (CMU 15_13) keep their legs and travel; everything above the hips takes the
#      recorded stance guard.
UPPER = ("spine", "chest", "neck", "head", "shoulder_L", "upper_arm_L", "forearm_L", "hand_L",
         "shoulder_R", "upper_arm_R", "forearm_R", "hand_R")
LEAD_ARM = ("shoulder_L", "upper_arm_L", "forearm_L", "hand_L")


def sample(act):
    arm.animation_data.action = act
    a_, b_ = [int(x) for x in act.frame_range]
    out_ = []
    for f in range(a_, b_ + 1):
        sc.frame_set(f)
        out_.append({pb.name: (pb.rotation_quaternion.copy(), pb.location.copy()) for pb in arm.pose.bones})
    return out_



_idle0 = sample(bpy.data.actions["idle_neutral"])[0]
_blend_ends(bpy.data.actions["hip_hinge_down"], at_start=True)
_blend_ends(bpy.data.actions["hip_hinge_up"], at_start=False)
print("march arm swing + hinge stands tall at both ends")
_stance = sample(bpy.data.actions["boxing_stance"])
_jab = sample(bpy.data.actions["boxing_jab"])
# the jab's most extended frame: largest lead-hand distance from the shoulder
def _reach(i):
    arm.animation_data.action = bpy.data.actions["boxing_jab"]
    sc.frame_set(int(bpy.data.actions["boxing_jab"].frame_range[0]) + i)
    return (Vector(arm.pose.bones["hand_L"].head) - Vector(arm.pose.bones["upper_arm_L"].head)).length
_peak = max(range(len(_jab)), key=_reach)


def _write(name, n, pose_at):
    old_ = bpy.data.actions.get(name)
    keep_legs = sample(old_) if old_ else None
    if old_:
        bpy.data.actions.remove(old_)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f in range(n):
        pose = pose_at(f, keep_legs)
        for bn, (q, loc) in pose.items():
            pb = arm.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q; pb.location = loc
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)
            pb.keyframe_insert("location", frame=f + 1)
    act.frame_range = (1, n)
    arm.animation_data.action = None


_reaches = [_reach(i) for i in range(len(_jab))]
_r0, _rp = _reaches[0], _reaches[_peak]
# frame on the jab's way out where the hand has covered ~55 % of the reach: "slightly away from the face"
_part = next(i for i in range(_peak + 1) if _reaches[i] >= _r0 + 0.55 * (_rp - _r0))


def _guard_return(f, _old):
    t = f / ta.FPS
    base = dict(_stance[f % len(_stance)])
    # out 0.5 s, hold 0.25 s, straight back 0.5 s along the same recorded path, settle in guard
    if t < 0.5:
        u = ta.ease(t / 0.5)
    elif t < 0.75:
        u = 1.0
    elif t < 1.25:
        u = 1.0 - ta.ease((t - 0.75) / 0.5)
    else:
        u = 0.0
    g = u * _part
    i0 = int(g); i1 = min(i0 + 1, len(_jab) - 1); k = g - i0
    for bn in LEAD_ARM:
        qa, qb = _jab[i0][bn][0], _jab[i1][bn][0]
        if qa.dot(qb) < 0:
            qb = -qb
        qj = qa.slerp(qb, k)
        # blend from the stance's own (breathing) guard into the jab path, so the start and end match the guard
        qs = base[bn][0]
        if qs.dot(qj) < 0:
            qj = -qj
        base[bn] = (qs.slerp(qj, min(1.0, u * 4.0)), base[bn][1])
    return base


_write("boxing_guard_return", int(round(1.4 * ta.FPS)) + 1, _guard_return)


def _footwork(f, old):
    pose = dict(old[min(f, len(old) - 1)])
    st = _stance[f % len(_stance)]
    for bn in UPPER:
        pose[bn] = (st[bn][0], pose[bn][1])
    return pose


for _fw in ("footwork_forward", "footwork_backward"):
    _n = int(bpy.data.actions[_fw].frame_range[1] - bpy.data.actions[_fw].frame_range[0]) + 1
    _write(_fw, _n, _footwork)
    guard_fix(bpy.data.actions[_fw], _guard)        # the drill crouches deeper than the stance: keep fists at the chin
print("recorded upper body on guard_return / footwork")
_dbg("upper")

# ---- hands: closed fist in every boxing clip, relaxed elsewhere, open and flat for the push-up
