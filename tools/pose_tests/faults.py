"""Deliberate form faults layered on the coach animation at render time (pose-space edits after each frame is
evaluated), for checking that the app's form cues fire on real pose-model output. World axes: coach faces -Y, Z up,
coach's left is +X."""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector

P = "mixamorig:"


def _upd():
    bpy.context.view_layer.update()


def head(arm, b):
    return arm.matrix_world @ arm.pose.bones[P + b].head


def rotate(arm, b, q, pivot):
    """Rotate pose bone b (and so its children) by world quaternion q about world point pivot."""
    pb = arm.pose.bones[P + b]
    M = arm.matrix_world @ pb.matrix
    Mn = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ M
    pb.matrix = arm.matrix_world.inverted() @ Mn
    _upd()


def aim(arm, b, child, target, w=1.0):
    """Rotate bone b about its head so that the head of bone `child` moves toward world point target (weight w)."""
    hd = head(arm, b)
    cur = head(arm, child) - hd
    want = target - hd
    if cur.length < 1e-6 or want.length < 1e-6:
        return
    q = cur.rotation_difference(want)
    q = Quaternion().slerp(q, max(0.0, min(1.0, w)))
    rotate(arm, b, q, hd)


def _knee_flex(arm, s):
    hp, kn, an = head(arm, s + "UpLeg"), head(arm, s + "Leg"), head(arm, s + "Foot")
    a = (hp - kn).angle(an - kn)
    return 180.0 - math.degrees(a)


def knees_in(arm, ctx, deg=28.0):
    """Valgus: each knee swings toward the midline about its own hip-ankle line; hips and ankles stay put."""
    for s in ("Left", "Right"):
        w = max(0.0, min(1.0, (_knee_flex(arm, s) - 15.0) / 70.0))
        if w <= 0:
            continue
        hp, an = head(arm, s + "UpLeg"), head(arm, s + "Foot")
        axis = (an - hp).normalized()
        kn = head(arm, s + "Leg")
        best = None
        for sgn in (1, -1):
            q = Quaternion(axis, math.radians(deg * w * sgn))
            k2 = hp + q @ (kn - hp)
            if best is None or abs(k2.x) < best[0]:
                best = (abs(k2.x), q)
        rotate(arm, s + "UpLeg", best[1], hp)
        aim(arm, s + "Leg", s + "Foot", an)


def _hip_drop(arm, ctx):
    z = head(arm, "Hips").z
    ctx.setdefault("z0", z)
    ctx["z0"] = max(ctx["z0"], z)
    return max(0.0, min(1.0, (ctx["z0"] - z) / ctx.get("drop_full", 0.30)))


def lean(arm, ctx, deg=30.0):
    """Extra forward lean of the upper body, growing with how far the hips have dropped."""
    w = _hip_drop(arm, ctx)
    if w > 0:
        rotate(arm, "Spine", Quaternion(Vector((1, 0, 0)), math.radians(deg * w)), head(arm, "Spine"))


def hips(arm, ctx, dz):
    """Push-up hips sag (dz < 0) or pike (dz > 0): the pelvis moves, shoulders and feet stay where they were."""
    neck, fl, fr = head(arm, "Neck"), head(arm, "LeftFoot"), head(arm, "RightFoot")
    pb = arm.pose.bones[P + "Hips"]
    M = arm.matrix_world @ pb.matrix
    pb.matrix = arm.matrix_world.inverted() @ (Matrix.Translation((0, 0, dz)) @ M)
    _upd()
    aim(arm, "Spine", "Neck", neck)
    aim(arm, "LeftUpLeg", "LeftFoot", fl)
    aim(arm, "RightUpLeg", "RightFoot", fr)


def _drop_arm(arm, s, w):
    sh = head(arm, s + "Arm")
    up = (head(arm, s + "ForeArm") - sh).length
    fo = (head(arm, s + "Hand") - head(arm, s + "ForeArm")).length
    elbow = sh + Vector((0, -0.10, -1)).normalized() * up
    aim(arm, s + "Arm", s + "ForeArm", elbow, w)
    el = head(arm, s + "ForeArm")
    aim(arm, s + "ForeArm", s + "Hand", el + Vector((0, -0.35, -1)).normalized() * fo, w)


def rear_drop(arm, ctx):
    """The rear (right) hand drops to the chest/belly while the lead (left) arm is extended."""
    sh, hd = head(arm, "LeftArm"), head(arm, "LeftHand")
    reach = (hd - sh).length / ((head(arm, "LeftForeArm") - sh).length + (hd - head(arm, "LeftForeArm")).length)
    w = max(0.0, min(1.0, (reach - 0.55) / 0.25))
    if w > 0:
        _drop_arm(arm, "Right", w)


def hands_low(arm, ctx):
    for s in ("Left", "Right"):
        _drop_arm(arm, s, 1.0)


FAULTS = {
    "knees_in": knees_in,
    "chest_drop": lambda a, c: lean(a, c, 38.0),
    "lunge_lean": lambda a, c: lean(a, c, 34.0),
    "hips_sag": lambda a, c: hips(a, c, -0.13),
    "hips_pike": lambda a, c: hips(a, c, +0.16),
    "rear_drop": rear_drop,
    "hands_low": hands_low,
}
