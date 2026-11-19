"""Retarget recorded joint positions (CMU skeleton, see assets/mocap) onto the MOTIONFORGE rig.

Per frame, in hierarchy order, each rig bone is turned so it points the way the matching recorded bone points
(world-space direction matching). Hips and chest also take the recorded side-to-side axis so the pelvis and ribcage
twist like the performer's; limbs use the smallest rotation (no twist). The basis is computed directly from the
rest/parent matrices, so no scene updates are needed per bone. The performance is turned to face -Y and scaled to
the character's leg length; the build's floor-contact pass then keeps the shoes on the floor."""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector

# rig bone -> (from joint, to joint) in the CMU skeleton
DIRS = {
    "spine": ("Hips", "Spine1"), "chest": ("Spine1", "Neck1"), "neck": ("Neck1", "Head"), "head": ("Neck1", "Head"),
    "shoulder_L": ("LeftShoulder", "LeftArm"), "upper_arm_L": ("LeftArm", "LeftForeArm"), "forearm_L": ("LeftForeArm", "LeftHand"),
    "hand_L": ("LeftHand", "LeftFingerBase"),
    "shoulder_R": ("RightShoulder", "RightArm"), "upper_arm_R": ("RightArm", "RightForeArm"), "forearm_R": ("RightForeArm", "RightHand"),
    "hand_R": ("RightHand", "RightFingerBase"),
    "thigh_L": ("LeftUpLeg", "LeftLeg"), "shin_L": ("LeftLeg", "LeftFoot"), "foot_L": ("LeftFoot", "LeftToeBase"),
    "thigh_R": ("RightUpLeg", "RightLeg"), "shin_R": ("RightLeg", "RightFoot"), "foot_R": ("RightFoot", "RightToeBase"),
}
# bones that also take the recorded left-right axis (full orientation)
FRAMES = {"hips": (("Hips", "Spine"), ("RightUpLeg", "LeftUpLeg")), "chest": (("Spine1", "Neck1"), ("RightArm", "LeftArm"))}


def _frame(up, side):
    up = up.normalized()
    side = (side - up * side.dot(up)).normalized()
    fwd = side.cross(up)
    return Matrix((side, up, fwd)).transposed()            # columns: side, up, forward


def retarget(arm, data, f0, f1, name, rig_side=("thigh_R", "thigh_L"), smooth=2, loop=False, fps=30, settle=0, hold=None, turn=0.0):
    """settle > 0: append that many frames easing from the last recorded pose back to the first one, so a single
    punch cut out of a combination returns to guard instead of running into the next punch.
    hold=("L", g): the left arm keeps its pose from recorded frame g (< f0, a guard) for the whole clip, so a rear
    punch cut from a combination doesn't show the lead hand still coming back from the jab."""
    g0 = min(f0, hold[1]) if hold else f0
    P = np.asarray(data["P"], np.float64)[g0:f1 + 1]
    I = {n: i for i, n in enumerate(list(data["names"]))}
    if smooth:
        from scipy.ndimage import gaussian_filter1d
        P = gaussian_filter1d(P, smooth * 0.5, axis=0, mode="nearest")
    # face -Y: mean recorded forward (side x up) rotated onto -Y, start over the origin
    side = P[:, I["LeftUpLeg"]] - P[:, I["RightUpLeg"]]
    up = np.array([0.0, 0.0, 1.0])
    fwd = np.cross(side, up).mean(0)       # Blender: X x Z ... forward for a character whose left is +X is -Y
    ang = math.atan2(fwd[1], fwd[0]) - math.atan2(-1.0, 0.0)
    ang -= math.radians(turn)              # extra turn (deg, counter-clockwise seen from above), e.g. so punches aim at -Y
    R = np.array([[math.cos(-ang), -math.sin(-ang), 0], [math.sin(-ang), math.cos(-ang), 0], [0, 0, 1]])
    P = P @ R.T
    hips0 = P[0, I["Hips"]].copy()
    P[:, :, 0] -= hips0[0]
    P[:, :, 1] -= hips0[1]
    # scale: performer's leg length -> character's
    bones = arm.data.bones
    leg_rig = bones["thigh_L"].length + bones["shin_L"].length
    leg_rec = np.median(np.linalg.norm(P[:, I["LeftUpLeg"]] - P[:, I["LeftLeg"]], axis=1) + np.linalg.norm(P[:, I["LeftLeg"]] - P[:, I["LeftFoot"]], axis=1))
    k = leg_rig / leg_rec
    floor = np.percentile(P[:, [I["LeftToeBase"], I["RightToeBase"]], 2], 5)
    P[:, :, 2] -= floor
    P *= k
    V = lambda f, j: Vector(P[f, I[j]])

    order = []
    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    walk(bones["root"])
    rest = {b.name: b.matrix_local.copy() for b in bones}
    rf = {}
    for bn, ((a, b_), (sa, sb)) in FRAMES.items():
        bone = bones[bn]
        upr = Vector(bone.tail_local) - Vector(bone.head_local)
        sider = Vector(bones[rig_side[1]].head_local) - Vector(bones[rig_side[0]].head_local) if bn == "hips" else \
            Vector(bones["upper_arm_L"].head_local) - Vector(bones["upper_arm_R"].head_local)
        rf[bn] = _frame(upr, sider)

    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    n = P.shape[0]
    keys = {}
    for f in range(n):
        pose = {}
        for b in order:
            if b.name == "root":
                pose[b.name] = rest[b.name].copy()
                continue
            par = b.parent
            inherit = pose[par.name] @ rest[par.name].inverted() @ rest[b.name]
            if b.name in FRAMES:
                (a, b_), (sa, sb) = FRAMES[b.name]
                F = _frame(V(f, b_) - V(f, a), V(f, sb) - V(f, sa))
                D = F @ rf[b.name].transposed()
                rot = D @ rest[b.name].to_3x3()
                loc = V(f, "Hips") if b.name == "hips" else inherit.translation
                if b.name == "hips":
                    loc = loc + (Vector(bones["hips"].head_local) - Vector((0, 0, bones["hips"].head_local.z))) * 0
                new = Matrix.Translation(loc) @ rot.to_4x4()
            elif b.name in DIRS and DIRS[b.name][1] in I:
                a, b_ = DIRS[b.name]
                t = (V(f, b_) - V(f, a))
                y0 = inherit.to_3x3().col[1]
                q = y0.rotation_difference(t.normalized()) if t.length > 1e-6 else y0.rotation_difference(y0)
                new = Matrix.Translation(inherit.translation) @ (q.to_matrix() @ inherit.to_3x3()).to_4x4()
            else:
                new = inherit
            pose[b.name] = new
            if abs(inherit.determinant()) < 1e-9 or abs(new.determinant()) < 1e-9:
                raise RuntimeError(f"singular at {b.name} frame {f}: inherit det {inherit.determinant()} new det {new.determinant()}")
            basis = inherit.inverted() @ new
            l, r, _ = basis.decompose()
            keys.setdefault(b.name, []).append((r, l if b.name == "hips" else Vector((0, 0, 0))))
    if hold:
        side_, g = hold
        gi = g - g0
        for bn in (f"shoulder_{side_}", f"upper_arm_{side_}", f"forearm_{side_}", f"hand_{side_}"):
            r_hold = keys[bn][gi][0]
            keys[bn] = [(r_hold, l) for (_, l) in keys[bn]]
        cut = f0 - g0
        keys = {bn: seq[cut:] for bn, seq in keys.items()}
        n -= cut
    if loop and n > 16:
        # blend the last K frames toward the first pose so the clip loops without a pop
        K = min(12, n // 3)
        for bn, seq in keys.items():
            r0, l0 = seq[0]
            for i in range(K):
                w = (i + 1) / K
                r, l = seq[n - K + i]
                seq[n - K + i] = (r.slerp(r0, w * w * (3 - 2 * w)), l.lerp(l0, w * w * (3 - 2 * w)))
    if settle:
        for bn, seq in keys.items():
            (r0, l0), (r1, l1) = seq[0], seq[-1]
            for i in range(settle):
                w = (i + 1) / settle
                w = w * w * (3 - 2 * w)
                seq.append((r1.slerp(r0, w), l1.lerp(l0, w)))
        n += settle
    for bn, seq in keys.items():
        pb = arm.pose.bones[bn]
        pb.rotation_mode = "QUATERNION"
        for f, (r, l) in enumerate(seq):
            pb.rotation_quaternion = r
            pb.location = l
            pb.keyframe_insert("rotation_quaternion", frame=f + 1)
            pb.keyframe_insert("location", frame=f + 1)
    act.frame_range = (1, n)
    arm.animation_data.action = None
    return act, n / fps
