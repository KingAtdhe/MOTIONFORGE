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

from trainer_rig import BONES

FPS = 30

# ----------------------------------------------------------------------------- pose helpers
LEG_THIGH = 0.418
LEG_SHIN = 0.427


def q_world(rots):
    q = Quaternion()
    for axis, deg in rots:
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
    g = 45 if side == "L" else -45
    rots = [("Y", g), ("X", flex)]
    if twist:
        rots.append(("Z", twist))
    rots.append(("Y", -g))
    return rots


# ----------------------------------------------------------------------------- base poses
def arms_down(bend=12):
    return {
        "upper_arm_L": [("Y", 40), ("X", -4)], "upper_arm_R": [("Y", -40), ("X", -4)],
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
        "upper_arm_L": [("Y", 40 + 5 * depth), ("X", -4 - (86 + lean) * depth)],
        "upper_arm_R": [("Y", -40 - 5 * depth), ("X", -4 - (86 + lean) * depth)],
        "forearm_L": hinge("L", -12 + 8 * depth), "forearm_R": hinge("R", -12 + 8 * depth),
        "hand_L": hinge("L", 0, 8), "hand_R": hinge("R", 0, -8),
    })
    return pose


TORSO_TURN = 32  # hips (24) + chest (8) turn in stance; arms aim back at the target by this much


def arm(side, forward, flex, tuck=0.0, aim=TORSO_TURN, out=0.0):
    """Upper arm: lower from A-pose to hanging, raise forward by `forward` deg, tuck elbow toward the
    body midline, then rotate about Z so the arm points at the target despite the torso turn."""
    s = 1 if side == "L" else -1
    return {
        f"upper_arm_{side}": [("Y", 45 * s - out * s), ("X", -forward), ("Z", -tuck * s), ("Z", aim)],
        f"forearm_{side}": hinge(side, -flex),
        f"hand_{side}": hinge(side, 8),
    }


def guard(lead_forward=38, rear_forward=30, lead_flex=122, rear_flex=132):
    return merge(arm("L", lead_forward, lead_flex, tuck=12), arm("R", rear_forward, rear_flex, tuck=16))


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
        arm("L", 38 + 50 * t, 122 - 112 * t, tuck=12 * (1 - t), aim=TORSO_TURN + extra),
        arm("R", 30, 132, tuck=16, aim=TORSO_TURN + extra),
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
        arm("L", 38, 122 + 6 * t, tuck=12, aim=total),
        arm("R", 30 + 58 * t, 132 - 122 * t, tuck=16 * (1 - t), aim=total),
    )


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
        return merge(NEUTRAL, {"chest": [("X", 1.2 * b)], "spine": [("X", 0.6 * b)], "head": [("X", -0.6 * b)]})

    def squat_down(t):
        return squat(ease(t / 1.6))

    def squat_up(t):
        return squat(1 - ease(t / 1.6))

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
        """Forward then back (or back then forward) shuffle step, 0.25 m, lead foot moves first."""
        d = 0.22
        sign = 1 if forward_first else -1

        def phase(p, moving_leg):
            # p 0..1 within a single step; moving leg lifts slightly mid-step
            lift = math.sin(math.pi * p)
            pose = stance()
            if moving_leg == "L":
                pose = merge(pose, {"thigh_L": [("X", -8 * lift)], "shin_L": [("X", 14 * lift)], "foot_L": [("X", -6 * lift)]})
            else:
                pose = merge(pose, {"thigh_R": [("X", -6 * lift)], "shin_R": [("X", 12 * lift)], "foot_R": [("X", -6 * lift)]})
            return pose

        seg = 0.45
        # sequence: lead foot, rear foot, (reverse direction) rear foot, lead foot
        order = [("L", 1), ("R", 1), ("R", -1), ("L", -1)] if forward_first else [("R", -1), ("L", -1), ("L", 1), ("R", 1)]
        i = min(3, int(t // seg))
        p = ease((t - i * seg) / seg)
        travelled = sum(0.5 * d * o[1] for o in order[:i]) + 0.5 * d * order[i][1] * p
        pose = phase(p, order[i][0])
        loc = pose.get("hips_loc", (0, 0, 0))
        pose["hips_loc"] = (loc[0], loc[1] - travelled, loc[2])
        return pose

    return [
        ("idle_neutral", 3.0, idle),
        ("squat_down", 1.6, squat_down),
        ("squat_up", 1.6, squat_up),
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
