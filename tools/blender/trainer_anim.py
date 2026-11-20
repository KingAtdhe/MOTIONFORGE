"""
MOTIONFORGE trainer animation clips (DRAFT — every clip needs qualified-coach review before release).

Poses are written as rotations about armature axes, applied in the parent's posed frame:
  X axis: positive pitches an upward bone forward (character faces -Y) / a downward bone backward.
  Y axis: positive swings a left (+X) downward-outward bone down toward the body.
  Z axis: positive turns the body so its left side moves backward.
Each bone value is an ordered list of (axis, degrees); the first entry is applied first.
"""
import math
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from trainer_body import J
from trainer_rig import BONES

FPS = 30

# ----------------------------------------------------------------------------- pose helpers
LEG_THIGH = 0.418
LEG_SHIN = 0.427


def q_world(rots):
    q = Quaternion()
    for axis, deg in rots:
        if axis == "A":  # arbitrary axis in armature space: deg = (axis_vector, degrees)
            q = Quaternion(Vector(deg[0]).normalized(), math.radians(deg[1])) @ q
            continue
        e = Euler((math.radians(deg) if axis == "X" else 0, math.radians(deg) if axis == "Y" else 0,
                   math.radians(deg) if axis == "Z" else 0), "XYZ")
        q = e.to_quaternion() @ q
    return q


def merge(*poses):
    out = {}
    for p in poses:
        for k, v in p.items():
            if k == "hips_loc":
                a = out.get(k, (0, 0, 0))
                out[k] = tuple(a[i] + v[i] for i in range(3))
            else:
                out[k] = out.get(k, []) + list(v)
    return out


def lerp_pose(a, b, t):
    """Interpolate two poses (rotation lists are converted to quaternions and slerped)."""
    out = {}
    keys = set(a) | set(b)
    for k in keys:
        if k == "hips_loc":
            va, vb = a.get(k, (0, 0, 0)), b.get(k, (0, 0, 0))
            out[k] = tuple(va[i] + (vb[i] - va[i]) * t for i in range(3))
        else:
            out[k] = ("Q", q_world(a.get(k, [])).slerp(q_world(b.get(k, [])), t))
    return out


def apply_pose(arm, pose, frame):
    for name in BONES:
        pb = arm.pose.bones[name]
        rest = arm.data.bones[name].matrix_local.to_3x3()
        rq = rest.to_quaternion()
        val = pose.get(name, [])
        qw = val[1] if isinstance(val, tuple) and val and val[0] == "Q" else q_world(val)
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rq.inverted() @ qw @ rq
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if name == "hips":
            loc = Vector(pose.get("hips_loc", (0, 0, 0)))
            pb.location = rest.inverted() @ loc
        else:
            pb.location = (0, 0, 0)
        pb.keyframe_insert("location", frame=frame)


def leg_pose(side, thigh_x, shin_abs_x, abduct=0.0, foot_turn=0.0):
    """Thigh pitch, absolute shin pitch; foot kept flat. Negative thigh_x = knee forward."""
    s = 1 if side == "L" else -1
    return {
        f"thigh_{side}": [("Y", -abduct * s), ("X", thigh_x)],
        f"shin_{side}": [("X", shin_abs_x - thigh_x)],
        f"foot_{side}": [("X", -shin_abs_x), ("Z", foot_turn * s)],
    }


def hip_offset(thigh_x, shin_abs_x):
    """Vertical drop and forward(-Y) shift of the hips that keep the ankle where it stood."""
    t, s = math.radians(thigh_x), math.radians(shin_abs_x)
    drop = (LEG_THIGH + LEG_SHIN) - (LEG_THIGH * math.cos(t) + LEG_SHIN * math.cos(s))
    # ankle y relative to hip = -(L_t sin(-t)) ... knee forward is -Y in Blender
    knee_y = LEG_THIGH * math.sin(t)  # thigh_x negative -> knee at -Y
    ankle_y = knee_y + LEG_SHIN * math.sin(s)
    return drop, -ankle_y  # hips must move by -ankle_y in Y to keep ankle fixed


def hinge(side, flex, twist=0.0):
    """Elbow / wrist flex about the arm's own hinge axis. The arm's rest pose is a 45° A-pose, so the
    rotation is done in a frame where the arm hangs vertically: negative flex bends forward."""
    g = REST_ARM if side == "L" else -REST_ARM
    rots = [("Y", g), ("X", flex)]
    if twist:
        rots.append(("Z", twist))
    rots.append(("Y", -g))
    return rots


def curl_axis(side):
    """Axis (armature rest space) that rolls the fingers toward the palm."""
    s = 1 if side == "L" else -1
    d = (J[f"hand_tip_{side}"] - J[f"hand_{side}"]).normalized()
    palm = d.cross(Vector((0, -1, 0))).normalized() * s
    return tuple(d.cross(palm).normalized())


def grip(side, amount):
    """amount 0 = open hand, 0.3 = relaxed, 1 = closed fist."""
    a = curl_axis(side)
    return {f"fingers_{side}": [("A", (a, 92 * amount))], f"fingertips_{side}": [("A", (a, 105 * amount))]}


RELAXED = 0.55
# angle (degrees from vertical) of the upper arm in the rig's rest pose; 45 = the classic A-pose.
# Characters built in their reference pose (arms near the body) set this so clips need no rest re-pose.
REST_ARM = 45.0


# ----------------------------------------------------------------------------- base poses
def arms_down(bend=12):
    return {**grip("L", RELAXED), **grip("R", RELAXED),
        "upper_arm_L": [("Y", REST_ARM - 5), ("X", -4)], "upper_arm_R": [("Y", -(REST_ARM - 5)), ("X", -4)],
        "forearm_L": hinge("L", -bend), "forearm_R": hinge("R", -bend),
        "hand_L": hinge("L", 0, 8), "hand_R": hinge("R", 0, -8),
    }


NEUTRAL = arms_down()


def squat(depth):
    """depth 0..1 (1 = bottom of the draft squat)."""
    thigh, shin = -78 * depth, 24 * depth
    drop, fwd = hip_offset(thigh, shin)
    pose = merge(
        leg_pose("L", thigh, shin, abduct=6 * depth, foot_turn=8 * depth),
        leg_pose("R", thigh, shin, abduct=6 * depth, foot_turn=8 * depth),
        {"spine": [("X", 20 * depth)], "chest": [("X", 12 * depth)], "neck": [("X", -14 * depth)], "head": [("X", -8 * depth)],
         "hips_loc": (0, fwd, -drop)},
    )
    # arms rise forward for balance (relative to the leaning chest)
    lean = 32 * depth
    pose = merge(pose, {
        "upper_arm_L": [("Y", REST_ARM - 5 + 5 * depth), ("X", -4 - (86 + lean) * depth), ("Z", 14 * depth)],
        "upper_arm_R": [("Y", -(REST_ARM - 5) - 5 * depth), ("X", -4 - (86 + lean) * depth), ("Z", -14 * depth)],
        "forearm_L": hinge("L", -12 + 8 * depth), "forearm_R": hinge("R", -12 + 8 * depth),
        "hand_L": hinge("L", 0, 8), "hand_R": hinge("R", 0, -8),
        **grip("L", RELAXED + 0.25 * depth), **grip("R", RELAXED + 0.25 * depth),
    })
    return pose


TORSO_TURN = 32  # hips (24) + chest (8) turn in stance; arms aim back at the target by this much


def arm(side, forward, flex, tuck=0.0, aim=TORSO_TURN, out=0.0):
    """Upper arm: lower from A-pose to hanging, raise forward by `forward` deg, tuck elbow toward the
    body midline, then rotate about Z so the arm points at the target despite the torso turn."""
    s = 1 if side == "L" else -1
    return {
        f"upper_arm_{side}": [("Y", REST_ARM * s - out * s), ("X", -forward), ("Z", -tuck * s), ("Z", aim)],
        f"forearm_{side}": hinge(side, -flex),
        f"hand_{side}": hinge(side, 8),
        **grip(side, 1.0),
    }


# Guard geometry (degrees). Bulkier characters need the fists further in front of the chest; builds may override.
G_LEAD_FWD, G_LEAD_FLEX, G_LEAD_TUCK = 38, 122, 12
G_REAR_FWD, G_REAR_FLEX, G_REAR_TUCK = 30, 132, 16


def guard(lead_forward=None, rear_forward=None, lead_flex=None, rear_flex=None):
    return merge(arm("L", G_LEAD_FWD if lead_forward is None else lead_forward, G_LEAD_FLEX if lead_flex is None else lead_flex, tuck=G_LEAD_TUCK),
                 arm("R", G_REAR_FWD if rear_forward is None else rear_forward, G_REAR_FLEX if rear_flex is None else rear_flex, tuck=G_REAR_TUCK))


def stance_body(turn=24, sink=0.035, chest_turn=8):
    thigh_l, shin_l = -14, 6
    thigh_r, shin_r = 12, 18
    return merge(
        leg_pose("L", thigh_l, shin_l, abduct=4, foot_turn=-10),
        leg_pose("R", thigh_r, shin_r, abduct=4, foot_turn=28),
        {
            "hips": [("Z", -turn)],
            "chest": [("Z", -chest_turn)],
            "neck": [("Z", (turn + chest_turn) * 0.5)],
            "head": [("Z", (turn + chest_turn) * 0.5), ("X", 6)],
            "hips_loc": (0, 0, -sink),
        },
    )


def stance(**guard_kw):
    return merge(stance_body(), guard(**guard_kw))


def jab_pose(t):
    """t 0..1 extension of the lead (left) hand toward head height in front."""
    extra = 6 * t  # lead shoulder turns slightly further forward
    return merge(
        stance_body(turn=24, chest_turn=8 + extra),
        arm("L", G_LEAD_FWD + (88 - G_LEAD_FWD) * t, G_LEAD_FLEX - (G_LEAD_FLEX - 10) * t, tuck=G_LEAD_TUCK * (1 - t), aim=TORSO_TURN + extra),
        arm("R", G_REAR_FWD, G_REAR_FLEX, tuck=G_REAR_TUCK, aim=TORSO_TURN + extra),
    )


def cross_pose(t):
    """t 0..1 extension of the rear (right) hand with hip/shoulder rotation and rear-heel pivot."""
    hips_turn = 24 - 30 * t
    chest_turn = 8 - 16 * t
    total = hips_turn + chest_turn
    body = merge(
        leg_pose("L", -14, 6, abduct=4, foot_turn=-10),
        leg_pose("R", 12 - 4 * t, 18 + 4 * t, abduct=4, foot_turn=28 + 30 * t),
        {
            "hips": [("Z", -hips_turn)],
            "chest": [("Z", -chest_turn)],
            "neck": [("Z", total * 0.5)],
            "head": [("Z", total * 0.5), ("X", 6)],
            "hips_loc": (0, -0.02 * t, -0.035),
        },
    )
    return merge(
        body,
        arm("L", G_LEAD_FWD, G_LEAD_FLEX + 6 * t, tuck=G_LEAD_TUCK, aim=total),
        arm("R", G_REAR_FWD + (88 - G_REAR_FWD) * t, G_REAR_FLEX - (G_REAR_FLEX - 10) * t, tuck=G_REAR_TUCK * (1 - t), aim=total),
    )


STANCE_LEGS = {"L": dict(thigh=-14, shin=6, abduct=4, foot_turn=-10), "R": dict(thigh=12, shin=18, abduct=4, foot_turn=28)}
STANCE_TURN = 24


def leg_ik(ay, az):
    """Two-bone sagittal IK. ay: ankle Blender-Y relative to the hip (negative = forward), az: distance
    below the hip. Returns (thigh_x, shin_abs_x) in degrees with the knee bending forward."""
    dist = min(math.hypot(ay, az), LEG_THIGH + LEG_SHIN - 1e-4)
    base = math.atan2(ay, az)
    a = math.acos(max(-1.0, min(1.0, (LEG_THIGH ** 2 + dist ** 2 - LEG_SHIN ** 2) / (2 * LEG_THIGH * dist))))
    t = base - a
    ky, kz = LEG_THIGH * math.sin(t), LEG_THIGH * math.cos(t)
    return math.degrees(t), math.degrees(math.atan2(ay - ky, az - kz))


def planted_leg(side, forward, lift=0.0):
    """Stance leg whose ankle sits `forward` metres (world, toward the target) from where the stance
    puts it, relative to the hips, and `lift` metres off the floor."""
    st = STANCE_LEGS[side]
    t0, s0 = math.radians(st["thigh"]), math.radians(st["shin"])
    ay = LEG_THIGH * math.sin(t0) + LEG_SHIN * math.sin(s0)
    az = LEG_THIGH * math.cos(t0) + LEG_SHIN * math.cos(s0)
    # world forward (-Y) expressed in the turned hips frame
    turn = math.radians(-STANCE_TURN)
    wx, wy = 0.0, -forward
    lx = math.cos(turn) * wx + math.sin(turn) * wy
    ly = -math.sin(turn) * wx + math.cos(turn) * wy
    thigh, shin = leg_ik(ay + ly, az - lift)
    out = lx if side == "L" else -lx
    abduct = st["abduct"] + math.degrees(math.atan2(out, az))
    return leg_pose(side, thigh, shin, abduct=abduct, foot_turn=st["foot_turn"])


# ----------------------------------------------------------------------------- clips
def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def bake_clip(arm, name, duration, pose_at):
    """Samples pose_at(time_seconds) every frame into a new action."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    frames = max(2, int(round(duration * FPS)))
    for f in range(frames + 1):
        apply_pose(arm, pose_at(f / FPS), f + 1)
    act.frame_range = (1, frames + 1)
    return act


def clip_specs():
    stance_pose = stance()
    lead_down = stance(lead_forward=18, rear_forward=14, lead_flex=95, rear_flex=105)

    def idle(t):
        b = math.sin(2 * math.pi * t / 3.0)
        return merge(arms_down(), {"chest": [("X", 1.2 * b)], "spine": [("X", 0.6 * b)], "head": [("X", -0.6 * b)]})

    def squat_down(t):
        # controlled descent: gentle start, steady middle, decelerating into the bottom with a tiny settle; the arms
        # trail the hips slightly (they rise as a counterweight once the hips are moving back)
        x = min(1.0, t / 1.7)
        d = x * x * (3 - 2 * x)
        d = min(1.0, d * 1.02) if x < 0.95 else 1.0 - 0.015 * math.sin(math.pi * (x - 0.95) / 0.05)
        return breathe(squat_lag(d, x), t)

    def squat_up(t):
        # drive up: quicker out of the bottom, easing into a tall finish
        x = min(1.0, t / 1.3)
        d = 1 - (1 - (1 - x) ** 2) ** 1.2
        return breathe(squat_lag(d, 1 - x), t)

    def squat_lag(d, x):
        pose = squat(d)
        lag = max(0.0, min(1.0, d * 1.15 - 0.08))              # arms a beat behind the hips
        for s_ in ("L", "R"):
            pose[f"upper_arm_{s_}"] = squat(lag)[f"upper_arm_{s_}"]
        return pose

    def breathe(pose, t):
        b = math.sin(2 * math.pi * t / 3.4)
        out = dict(pose)
        out["chest"] = list(pose.get("chest", [])) + [("X", 0.8 * b)]
        out["head"] = list(pose.get("head", [])) + [("X", -0.5 * b)]
        return out

    def stance_clip(t):
        # gentle, relaxed sway in stance (weight stays centred)
        b = math.sin(2 * math.pi * t / 2.4)
        return merge(stance(), {"hips_loc": (0.008 * b, 0, 0.004 * abs(b))})

    def jab(t):
        if t < 0.35:
            return jab_pose(ease(t / 0.35))
        if t < 0.5:
            return jab_pose(1.0)
        return jab_pose(1 - ease((t - 0.5) / 0.5))

    def cross(t):
        if t < 0.4:
            return cross_pose(ease(t / 0.4))
        if t < 0.55:
            return cross_pose(1.0)
        return cross_pose(1 - ease((t - 0.55) / 0.55))

    def guard_return(t):
        if t < 0.5:
            return lerp_pose(stance_pose, lead_down, ease(t / 0.5))
        if t < 0.8:
            return lerp_pose(lead_down, lead_down, 1)
        return lerp_pose(lead_down, stance_pose, ease((t - 0.8) / 0.6))

    def step(t, forward_first):
        """Shuffle step forward then back (or back then forward), lead foot moves first.
        Feet are planted: the standing foot keeps its floor position while the hips travel, solved
        with two-bone leg IK, so there is no foot sliding."""
        d = 0.16
        seg = 0.45
        order = [("L", 1), ("R", 1), ("R", -1), ("L", -1)] if forward_first else [("R", -1), ("L", -1), ("L", 1), ("R", 1)]
        i = min(3, int(t // seg))
        p = ease((t - i * seg) / seg)
        foot = {"L": 0.0, "R": 0.0}
        for leg, direction in order[:i]:
            foot[leg] += d * direction
        moving, direction = order[i]
        foot[moving] += d * direction * p
        hips = sum(0.5 * d * o[1] for o in order[:i]) + 0.5 * d * direction * p
        lift = math.sin(math.pi * p)
        pose = stance()
        for side in ("L", "R"):
            pose.update(planted_leg(side, foot[side] - hips, 0.030 * lift if side == moving else 0.0))
        loc = pose.get("hips_loc", (0, 0, 0))
        pose["hips_loc"] = (loc[0], loc[1] - hips, loc[2])
        return pose

    def march(t):
        """Brisk, relaxed march on the spot (warm-up), 75 steps/min. Layered like a real gait cycle rather than
        one sine: the knee rises with a soft hold at the top and a quicker drop, the pelvis shifts over the
        standing leg and its free side lifts, the ribcage counter-rotates, arms swing opposite with bent elbows
        trailing the shoulder slightly, the head stays level, and the body dips a little as each foot lands."""
        T = 1.6                                   # one left + one right step
        ph = (t % T) / T                          # 0..1
        def bell(x):                              # 0..1..0 over x in [0,1], quick rise, held top, faster fall
            if x <= 0 or x >= 1:
                return 0.0
            up = min(1.0, x / 0.42)
            down = min(1.0, (1 - x) / 0.34)
            return ease(min(up, down))
        lift_l = bell(ph * 2)                     # left knee in the first half
        lift_r = bell(ph * 2 - 1)                 # right knee in the second half
        side = math.sin(2 * math.pi * ph)         # +1 weight on the right (left knee up) .. -1 weight on the left
        def leg(sd, lift):
            thigh = -82 * lift
            shin = 10 * lift                      # shin hangs nearly vertical under the raised knee (knee ~ 95 deg)
            pose = leg_pose(sd, thigh, shin)
            pose[f"foot_{sd}"] = [("X", -shin + 18 * lift)]   # toes point down a little while the foot is up
            return pose
        # arms: opposite to the legs, swing follows the shoulder with a short lag
        arm_ph = 2 * math.pi * (ph - 0.04)
        swing = 38 * math.sin(arm_ph)             # + swings the left arm back while the left knee is up
        elbow_l = 78 + 12 * max(0.0, -math.sin(arm_ph))
        elbow_r = 78 + 12 * max(0.0, math.sin(arm_ph))
        land = max(0.0, math.cos(4 * math.pi * ph)) ** 6   # short dip when a foot meets the floor
        breath = math.sin(2 * math.pi * t / 3.2)
        pose = merge(
            leg("L", lift_l), leg("R", lift_r),
            {**grip("L", 0.5), **grip("R", 0.5),
             # left knee up -> right arm forward
             "upper_arm_L": [("Y", REST_ARM - 8), ("X", -4 + swing)],
             "upper_arm_R": [("Y", -(REST_ARM - 8)), ("X", -4 - swing)],
             "forearm_L": hinge("L", -elbow_l), "forearm_R": hinge("R", -elbow_r),
             "hand_L": hinge("L", -6, 8), "hand_R": hinge("R", -6, -8),
             "hips": [("Z", -5 * side), ("Y", 3.0 * side), ("X", 2)],
             "spine": [("Z", 3 * side), ("Y", -1.5 * side), ("X", 1 + 0.6 * breath)],
             "chest": [("Z", 4 * side), ("Y", -1.5 * side), ("X", 1 + 0.8 * breath)],
             "neck": [("Z", -1.5 * side)], "head": [("Z", -1.0 * side), ("X", -2)],
             "hips_loc": (0.022 * side, 0, 0.010 * (lift_l + lift_r) - 0.012 * land)},
        )
        return pose

    def hinge_pose(d):
        """d 0..1: hips slide back, chest tips forward with a long back, knees stay soft."""
        back, drop = 0.13 * d, 0.025 * d
        thigh, shin = leg_ik(-back, LEG_THIGH + LEG_SHIN - 0.01 - drop)
        tilt = 38 * d                    # pelvis pitch; the legs are children of the hips, so they are counter-rotated
        return merge(
            arms_down(bend=10),
            leg_pose("L", thigh - tilt, shin - tilt), leg_pose("R", thigh - tilt, shin - tilt),
            {"foot_L": [("X", -tilt)], "foot_R": [("X", -tilt)],
             "hips": [("X", tilt)], "spine": [("X", 8 * d)], "chest": [("X", 4 * d)],
             "neck": [("X", -16 * d)], "head": [("X", -10 * d)],
             "upper_arm_L": [("X", -30 * d)], "upper_arm_R": [("X", -30 * d)],
             "hips_loc": (0, back, -drop)},
        )

    return [
        ("warmup_march", 4.8, march),
        ("hip_hinge_down", 1.6, lambda t: hinge_pose(ease(t / 1.6))),
        ("hip_hinge_up", 1.4, lambda t: hinge_pose(1 - ease(t / 1.4))),
        ("idle_neutral", 3.0, idle),
        ("squat_down", 1.7, squat_down),
        ("squat_up", 1.3, squat_up),
        ("boxing_stance", 2.4, stance_clip),
        ("boxing_jab", 1.0, jab),
        ("boxing_cross", 1.1, cross),
        ("boxing_guard_return", 1.4, guard_return),
        ("footwork_forward", 1.8, lambda t: step(t, True)),
        ("footwork_backward", 1.8, lambda t: step(t, False)),
    ]


def build_clips(arm):
    acts = []
    for name, duration, fn in clip_specs():
        acts.append(bake_clip(arm, name, duration, fn))
    return acts
