"""Biomechanically authored demonstration clips for the MOTIONFORGE control rig (trainer_rig).

Why this exists: the clips retargeted from single-camera video and from combination mocap takes carried the
performers' errors and the tracker's noise (feet sliding, heels lifting in the hinge, a jab that never extended,
uneven push-up arms). A coach demonstration has to show textbook form, so every clip here is built from explicit
joint rules instead: planted feet are pinned exactly, knees track over the toes, the spine keeps its neutral curve,
the eccentric phase is slower than the concentric one, and every repetition returns to the pose it started from.

All poses are solved in armature space (Z up, the character faces -Y, its left is +X):
  torso   world orientations for pelvis / spine / chest / neck / head
  legs    two-bone IK from the hip joint to an ankle derived from the ball of the foot (so heel raises pivot on the ball)
  arms    two-bone IK from the shoulder joint to a wrist target with an elbow pole and an explicit palm direction
These are demonstrations, not measurements: nothing here is tracking data.
"""
import math

import bpy
from mathutils import Matrix, Vector

FPS_OUT = 30          # frames per second of the exported clips
OVERSAMPLE = 4        # clips are authored at FPS_OUT x OVERSAMPLE and resampled once to FPS_OUT on write: resampling the
                      # time-warp from 30 fps poses with straight-line blends stepped the speed at every source frame
                      # (QC: elbow jerk spikes of ~1000 m/s3 at every punch, toes and knees in many clips)
FPS = FPS_OUT * OVERSAMPLE
# Moving legs keep some knee bend: near full stretch a millimetre of hip or foot travel swings the knee a long way, so
# knees straightening to 99-99.6 % stopped and restarted in a frame when a foot landed (QC: knee jerk 500-900 m/s3 in
# marches, lunges, step jack, footwork). Marches 0.996 -> 0.985, lunges 0.992 -> 0.982, step jack 0.990 -> 0.975,
# boxing stance 0.992 -> 0.985, side lunge 0.994 -> 0.985.
SIDES = (("L", 1.0), ("R", -1.0))


def Rx(d):
    return Matrix.Rotation(math.radians(d), 3, "X")     # +: pitch forward (toward -Y)


def Ry(d):
    return Matrix.Rotation(math.radians(d), 3, "Y")     # +: lean toward the character's left (+X)


def Rz(d):
    return Matrix.Rotation(math.radians(d), 3, "Z")     # +: turn toward the character's left


def Q(yaw=0.0, pitch=0.0, roll=0.0):
    return Rz(yaw) @ Rx(pitch) @ Ry(roll)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def smoother(t):
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


def V(x, y, z):
    return Vector((x, y, z))


def _frame(x, y, z):
    m = Matrix((x, y, z))
    m.transpose()
    return m


def _smax(a, b, eps=0.004):
    return 0.5 * (a + b) + math.sqrt((0.5 * (a - b)) ** 2 + eps * eps) - eps


class Rig:
    def __init__(self, arm, height):
        self.arm = arm
        self.k = height / 1.8
        bones = arm.data.bones
        self.rest = {b.name: b.matrix_local.copy() for b in bones}
        self.rest3 = {n: m.to_3x3() for n, m in self.rest.items()}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.order = []

        def walk(b):
            self.order.append(b.name)
            for c in b.children:
                walk(c)
        for b in bones:
            if b.parent is None:
                walk(b)
        H = {b.name: Vector(b.head_local) for b in bones}
        T = {b.name: Vector(b.tail_local) for b in bones}
        self.H = H
        self.P0 = H["hips"].copy()
        self.hj = {s: H[f"thigh_{s}"] - H["hips"] for s, _ in SIDES}
        self.l1 = {s: (H[f"shin_{s}"] - H[f"thigh_{s}"]).length for s, _ in SIDES}
        self.l2 = {s: (H[f"foot_{s}"] - H[f"shin_{s}"]).length for s, _ in SIDES}
        self.fv = {s: T[f"foot_{s}"] - H[f"foot_{s}"] for s, _ in SIDES}                    # ankle -> ball, rest
        self.psi0 = {s: math.degrees(math.atan2(self.fv[s].x, -self.fv[s].y)) for s, _ in SIDES}   # rest toe-out
        self.ball0 = {s: T[f"foot_{s}"].copy() for s, _ in SIDES}
        self.ankle0 = {s: H[f"foot_{s}"].copy() for s, _ in SIDES}
        self.a1 = {s: (H[f"forearm_{s}"] - H[f"upper_arm_{s}"]).length for s, _ in SIDES}
        self.a2 = {s: (H[f"hand_{s}"] - H[f"forearm_{s}"]).length for s, _ in SIDES}
        self.la = self.a1["L"] + self.a2["L"]
        self.leg = self.l1["L"] + self.l2["L"]
        self.sh_half = abs(H["upper_arm_L"].x - H["upper_arm_R"].x) / 2
        self.worst_leg = 0.0
        self.worst_arm = 0.0

    # ---- feet
    def foot_q(self, s, yaw, pitch):
        return Rz(yaw) @ Rx(pitch) @ Rz(-self.psi0[s])

    def foot(self, s, ax, ay, yaw, pitch=0.0, lift=0.0):
        """Foot given by where the ankle would be with the foot flat; a pitch (heel raise) pivots on the ball."""
        flat = self.foot_q(s, yaw, 0.0) @ self.fv[s]
        ball = V(ax + flat.x, ay + flat.y, self.ball0[s].z + lift)
        return (ball, yaw, pitch)

    def ankle(self, s, f):
        ball, yaw, pitch = f
        return ball - self.foot_q(s, yaw, pitch) @ self.fv[s]

    def foot_toward(self, s, A, direction, yaw=0.0):
        """Foot whose ankle sits at A and whose ankle->ball vector points as close as possible to `direction`
        (kneeling and lying poses, where the foot is not flat on the floor)."""
        d = direction.normalized()
        best, bp = None, 0.0
        for i in range(-180, 181, 2):
            v = (self.foot_q(s, yaw, float(i)) @ self.fv[s]).normalized()
            sc = v.dot(d)
            if best is None or sc > best:
                best, bp = sc, float(i)
        # refine inside the winning 2-degree cell (golden-section), so the foot turns smoothly instead of in 2-degree steps
        lo_, hi_ = bp - 2.0, bp + 2.0
        f_ = lambda p: (self.foot_q(s, yaw, p) @ self.fv[s]).normalized().dot(d)
        for _ in range(24):
            m1, m2 = lo_ + (hi_ - lo_) * 0.382, lo_ + (hi_ - lo_) * 0.618
            if f_(m1) < f_(m2):
                lo_ = m1
            else:
                hi_ = m2
        bp = (lo_ + hi_) / 2
        return (A + self.foot_q(s, yaw, bp) @ self.fv[s], yaw, bp)

    def hip_joint(self, sp, s):
        return sp["pos"] + sp["pel"] @ self.hj[s]

    def fit_z(self, sp, ext=0.992, sides=("L", "R")):
        """Highest pelvis at which the straighter leg is extended to `ext` of its length (soft knees, never locked)."""
        lo, hi = 0.15, 1.6
        for _ in range(40):
            mid = (lo + hi) / 2
            sp["pos"].z = mid
            rs = [(self.hip_joint(sp, s) - self.ankle(s, sp["feet"][s])).length / (self.l1[s] + self.l2[s]) for s in sides]
            # smooth maximum of the two legs (equal to max() when they differ clearly, and when they are equal): with a
            # hard max the limiting leg handed over in one frame as a stepping foot landed, and the knee stopped and
            # restarted (QC: knee jerk 500-900 m/s3 in lunges, step jack, marches, footwork)
            worst = rs[0] if len(rs) == 1 else _smax(rs[0], rs[1])
            if worst > ext:
                hi = mid
            else:
                lo = mid
        sp["pos"].z = lo
        return lo

    # ---- solve one pose
    def _child(self, M, name):
        p = self.parent[name]
        return M[p] @ self.rest[p].inverted() @ self.rest[name]

    def torso(self, sp):
        M = {"root": self.rest["root"].copy()}
        M["hips"] = Matrix.Translation(sp["pos"]) @ (sp["pel"] @ self.rest3["hips"]).to_4x4()
        for bn, key in (("spine", "spi"), ("chest", "che"), ("neck", "nek"), ("head", "hed")):
            M[bn] = Matrix.Translation(self._child(M, bn).translation) @ (sp[key] @ self.rest3[bn]).to_4x4()
        for s, sg in SIDES:
            bn = f"shoulder_{s}"
            loc = Rz(-sg * sp.get("prot", {}).get(s, 0.0)) @ Ry(-sg * sp.get("shrug", {}).get(s, 0.0))
            M[bn] = Matrix.Translation(self._child(M, bn).translation) @ (sp["che"] @ loc @ self.rest3[bn]).to_4x4()
        pts = {"S_" + s: self._child(M, f"upper_arm_{s}").translation.copy() for s, _ in SIDES}
        hm = M["head"]
        pts["head"] = hm.translation + hm.to_3x3().col[1] * (0.09 * self.k)
        pts["chest"] = M["chest"].translation.copy()
        pts["hips"] = sp["pos"].copy()
        return M, pts

    def solve(self, sp):
        M, pts = self.torso(sp)
        # legs
        for s, sg in SIDES:
            th, sh, ft = f"thigh_{s}", f"shin_{s}", f"foot_{s}"
            Hp = self._child(M, th).translation
            ball, yaw, pitch = sp["feet"][s]
            qf = self.foot_q(s, yaw, pitch)
            A = ball - qf @ self.fv[s]
            l1, l2 = self.l1[s], self.l2[s]
            d = A - Hp
            over = d.length - (l1 + l2 - 1e-4)
            if over > 0:
                self.worst_leg = max(self.worst_leg, over)
            dist = max(min(d.length, l1 + l2 - 1e-4), abs(l1 - l2) + 1e-4)
            dn = d.normalized()
            pole = sp.get("kpole", {}).get(s, V(0, -1, 0))
            pp = pole - dn * pole.dot(dn)
            pp = pp.normalized() if pp.length > 1e-6 else V(0, -1, 0)
            a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            K = Hp + dn * a + pp * h
            A2 = Hp + dn * dist
            y = (K - Hp).normalized()
            z = -(pp - y * pp.dot(y)).normalized()
            x = y.cross(z)
            M[th] = Matrix.Translation(Hp) @ _frame(x, y, z).to_4x4()
            ys = (A2 - K).normalized()
            zs = x.cross(ys).normalized()
            xs = ys.cross(zs)
            M[sh] = Matrix.Translation(K) @ _frame(xs, ys, zs).to_4x4()
            M[ft] = Matrix.Translation(A2) @ (qf @ self.rest3[ft]).to_4x4()
        # arms
        arms = sp["arms"](pts) if callable(sp["arms"]) else sp["arms"]
        for s, sg in SIDES:
            ua, fa, hd = f"upper_arm_{s}", f"forearm_{s}", f"hand_{s}"
            S = pts["S_" + s]
            t = arms[s]
            l1, l2 = self.a1[s], self.a2[s]
            d = t["w"] - S
            over = d.length - (l1 + l2) * 0.999
            if over > 0:
                self.worst_arm = max(self.worst_arm, over)
            dist = max(min(d.length, (l1 + l2) * 0.999), abs(l1 - l2) + 1e-4)
            dn = d.normalized()
            pole = t.get("pole", V(0, 1, -0.3))
            pp = pole - dn * pole.dot(dn)
            pp = pp.normalized() if pp.length > 1e-6 else V(0, 1, 0)
            a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
            h = math.sqrt(max(l1 * l1 - a * a, 0.0))
            E = S + dn * a + pp * h
            W = S + dn * dist
            y = (E - S).normalized()
            bv = (W - E) - y * (W - E).dot(y)
            bv = bv.normalized() if bv.length > 1e-6 else -pp
            x = bv * sg
            z = x.cross(y).normalized()
            x = y.cross(z)
            M[ua] = Matrix.Translation(S) @ _frame(x, y, z).to_4x4()
            yf = (W - E).normalized()
            zf = (z - yf * z.dot(yf)).normalized()
            xf = yf.cross(zf)
            fing = t.get("fingers")
            fing = fing.normalized() if fing is not None else yf
            palm = t["palm"]
            zh = -(palm - fing * palm.dot(fing))
            zh = zh.normalized() if zh.length > 1e-6 else zf
            xh = fing.cross(zh)
            # the forearm takes half of the wrist's pronation / supination, as the real forearm does over its length
            # The twist is read from both hand axes, each weighted by how square it sits to the forearm. Reading it from
            # the palm axis alone was ill-conditioned with the wrist bent back 90 deg (push-ups, planks: the palm normal
            # runs along the forearm) and the forearm flipped up to 69 deg in one frame (QC).
            zp = zh - yf * zh.dot(yf)
            xp = xh - yf * xh.dot(yf)
            cz, sz = zf.dot(zp), zf.cross(zp).dot(yf)               # angle of the hand's z about the forearm
            cx, sx = xf.dot(xp), xf.cross(xp).dot(yf)               # angle of the hand's x about the forearm
            c_, s_ = cz * zp.length + cx * xp.length, sz * zp.length + sx * xp.length
            if c_ * c_ + s_ * s_ > 1e-8:
                tw = math.atan2(s_, c_)
                tw = max(-1.2, min(1.2, tw)) * 0.5
                rot = Matrix.Rotation(tw, 3, yf)
                xf, zf = rot @ xf, rot @ zf
            M[fa] = Matrix.Translation(E) @ _frame(xf, yf, zf).to_4x4()
            M[hd] = Matrix.Translation(W) @ _frame(xh, fing, zh).to_4x4()
        for bn in self.order:
            if bn not in M:
                M[bn] = self._child(M, bn)
        if "world" in sp:                                       # whole-body turn (e.g. a pivot on one foot)
            W = sp["world"]
            # the root bone's translation is never keyed, so the turn is applied from the hips down (the hips carry it)
            M = {k: (m if k == "root" else W @ m) for k, m in M.items()}
        return M

    def write(self, name, specs):
        """Solves every frame, then (1) retimes the clip so held poses pass quicker than movement (RETIME), and
        (2) adds follow-through: head, neck and, unless the hands are planted, the upper back lag the body slightly
        (LAG). First and last frames are kept exactly, so loops and down/up pairs still join."""
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm = self.arm
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        reach0 = (self.worst_leg, self.worst_arm)
        self.worst_leg = self.worst_arm = 0.0
        specs = _with_life(name, specs)
        frames_ = []                                             # per frame: {bone: (loc, rot)}, activity sample
        prev = {}
        track = ("hips", "head", "hand_L", "hand_R", "foot_L", "foot_R")
        last_pts = None
        acts = []
        for sp in specs:
            M = self.solve(sp)
            fr = {}
            for bn in self.order:
                p = self.parent[bn]
                inherit = self.rest[bn] if p is None else M[p] @ self.rest[p].inverted() @ self.rest[bn]
                loc, rot, _ = (inherit.inverted() @ M[bn]).decompose()
                if bn in prev and prev[bn].dot(rot) < 0:
                    rot = -rot
                prev[bn] = rot
                fr[bn] = (loc if bn == "hips" else Vector((0, 0, 0)), rot)
            frames_.append(fr)
            pts = [M[b].translation.copy() for b in track if b in M]
            acts.append(0.0 if last_pts is None else max((a - b).length for a, b in zip(pts, last_pts)) * FPS)
            last_pts = pts
        if self.worst_arm > 0.005 or self.worst_leg > 0.005:
            print(f"  over-reach in {name}: leg {self.worst_leg * 100:.1f} cm, arm {self.worst_arm * 100:.1f} cm")
        self.worst_leg, self.worst_arm = max(reach0[0], self.worst_leg), max(reach0[1], self.worst_arm)
        frames_ = _retime(frames_, acts, RETIME.get(name, RETIME_DEFAULT), self.order)
        frames_ = _follow_through(frames_, self.order, name)
        frames_ = _desync(frames_, name)
        for f, fr in enumerate(frames_):
            for bn in self.order:
                loc, rot = fr[bn]
                pb = arm.pose.bones[bn]
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = rot
                pb.keyframe_insert("rotation_quaternion", frame=f + 1)
                pb.location = loc
                pb.keyframe_insert("location", frame=f + 1)
        act.frame_range = (1, len(frames_))
        arm.animation_data.action = None
        return act


# =============================================================================================== timing and follow-through
# (speed of held poses, speed of movement). Holds pass ~2.2x quicker, movement ~1.2x; rhythm drills keep their tempo.
RETIME_DEFAULT = (2.2, 1.2)
RETIME = {name: (1.0, 1.0) for name in ("idle_neutral", "warmup_march", "high_knee_march", "step_jack", "arm_circles",
                                         "plank_hold", "boxing_stance")}
# knee lifts: the default warp sped the lifts up 1.2x and the pauses 2.2x -- rushed, snappy lifts (QC); gentler here
RETIME.update({"knee_crunch": (1.4, 1.0), "oblique_crunch": (1.4, 1.0), "mountain_climber_slow": (1.4, 1.0),
               "bird_dog": (1.4, 1.0)})      # (the default warp sped the slow landings up -- hands arrived with a bump)
# clips whose hands rest on the floor: the upper back must not lag, or the planted hands would slide
PLANTED_HANDS = ("pushup_", "knee_pushup_", "incline_pushup_", "plank_hold", "mountain_climber_slow", "bird_dog",
                 "cat_cow", "superman", "glute_bridge")
# per-frame follow factor (1 = no lag); lower = more lag. Applied in time order, after retiming.
LAG = {"head": 0.45, "neck": 0.62}
LAG_BACK = {"chest": 0.72, "spine": 0.80}
# hanging arms trail the body a little (pendulum) in clips where they only hang at the sides
HANGING_ARMS = ("reverse_lunge", "split_squat", "calf_raise", "idle_neutral", "hip_hinge_", "superman")
LAG_ARMS = {"upper_arm_L": 0.78, "upper_arm_R": 0.78, "forearm_L": 0.85, "forearm_R": 0.85}


def _retime(frames_, acts, speeds, order):
    """Time-warp: each source frame lasts 1 / speed, where speed blends from `still` to `moving` with the body's activity
    (max speed of hips / head / hands / feet). The speed profile is smoothed so the warp itself never jerks."""
    still, moving = speeds
    n = len(frames_)
    if n < 3:
        return frames_
    acts = acts[:]
    acts[0] = acts[1]
    sp = [lerp(still, moving, smooth(a / 0.10)) for a in acts]
    w = 5 * OVERSAMPLE
    sp = [sum(sp[max(0, i - w):min(n, i + w + 1)]) / (min(n, i + w + 1) - max(0, i - w)) for i in range(n)]
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + 0.5 * (1.0 / sp[i - 1] + 1.0 / sp[i]))
    total = cum[-1]
    m = max(3, int(round(total / OVERSAMPLE)) + 1)          # output frames at FPS_OUT
    out = []
    k = 0
    for j in range(m):
        tgt = total * j / (m - 1)
        while k < n - 2 and cum[k + 1] < tgt:
            k += 1
        a = 0.0 if cum[k + 1] == cum[k] else (tgt - cum[k]) / (cum[k + 1] - cum[k])
        a = max(0.0, min(1.0, a))
        f0, f1 = frames_[k], frames_[k + 1]
        fr = {}
        for bn in order:
            l0, r0 = f0[bn]
            l1, r1 = f1[bn]
            fr[bn] = (l0.lerp(l1, a), r0.slerp(r1, a))
        out.append(fr)
    out[0], out[-1] = frames_[0], frames_[-1]
    return out


def _follow_through(frames_, order, name):
    """Lag selected bones' local rotations behind their solved values (exponential follow). Loops are pre-rolled so the
    seam matches; clips that start and end in different poses start from their first frame. The last few frames blend
    back to the solved pose so down/up pairs still meet exactly."""
    gains = dict(LAG)
    if not any(name.startswith(p) for p in PLANTED_HANDS):
        gains.update(LAG_BACK)
    if any(name.startswith(p) for p in HANGING_ARMS) and not name.startswith("superman"):
        gains.update(LAG_ARMS)
    gains = {b: g for b, g in gains.items() if b in order}
    n = len(frames_)
    if n < 4 or not gains:
        return frames_
    first, last = frames_[0], frames_[-1]
    loop = all(first[b][1].rotation_difference(last[b][1]).angle < 1e-3 for b in gains)
    out = [dict(fr) for fr in frames_]
    for bn, g in gains.items():
        state = frames_[-1][bn][1].copy() if loop else frames_[0][bn][1].copy()
        if loop:                                                 # pre-roll one cycle so the start continues the end
            for fr in frames_:
                state = state.slerp(fr[bn][1], g)
        for i, fr in enumerate(frames_):
            state = state.slerp(fr[bn][1], g)
            out[i][bn] = (fr[bn][0], state.copy())
        if not loop:                                             # land exactly on the final pose
            tail = min(8, n - 1)
            for t_ in range(tail):
                i = n - tail + t_
                a = smooth((t_ + 1) / tail)
                out[i][bn] = (frames_[i][bn][0], out[i][bn][1].slerp(frames_[i][bn][1], a))
    return out


# =============================================================================================== shared pieces
def breath(t, period=4.0, phase=0.0):
    return math.sin(2 * math.pi * (t / period) + phase)


def torso_spec(pos, yaw=0.0, pitch=0.0, roll=0.0, spine=0.0, chest=0.0, chest_yaw=0.0, head_pitch=0.0, head_yaw=0.0, br=0.0):
    """pitch = pelvis forward tilt; spine / chest add flexion on top; br lifts the chest on an in-breath."""
    pel = Q(yaw, pitch, roll)
    spi = Q(yaw + chest_yaw * 0.4, pitch + spine, roll * 0.5)
    che = Q(yaw + chest_yaw, pitch + spine + chest - 1.2 * br, 0.0)
    nek = Q(lerp(yaw + chest_yaw, head_yaw, 0.5), lerp(pitch + spine + chest, head_pitch, 0.6), 0.0)
    hed = Q(head_yaw, head_pitch, 0.0)
    return {"pos": pos, "pel": pel, "spi": spi, "che": che, "nek": nek, "hed": hed, "shrug": {"L": 1.0 * br, "R": 1.0 * br}, "prot": {}}


def hang(r, pts, s, sg, out=0.085, fwd=0.03, reach=0.990):
    """Relaxed arm at the side: elbow slightly bent and pointing back, palm toward the thigh."""
    S = pts["S_" + s]
    return {"w": S + V(sg * out * r.k, -fwd * r.k, -math.sqrt(max((reach * r.la) ** 2 - (out * r.k) ** 2 - (fwd * r.k) ** 2, 1e-6))),
            "pole": V(sg * 0.25, 1.0, 0.1), "palm": V(-sg, 0.15, 0)}


def mix_arm(a, b, t):
    out = {"w": a["w"].lerp(b["w"], t), "pole": a["pole"].lerp(b["pole"], t), "palm": a["palm"].lerp(b["palm"], t)}
    fa, fb = a.get("fingers"), b.get("fingers")
    if fa is not None or fb is not None:
        if fa is None or fb is None:
            out["fingers"] = None if t < 0.5 else fb
            if fa is not None and t < 0.5:
                out["fingers"] = fa
        else:
            out["fingers"] = fa.lerp(fb, t)
    return out


def frames(seconds):
    return int(round(seconds * FPS)) + 1


# =============================================================================================== idle
def idle(r, st):
    T = 4.0
    n = frames(T)
    w = 0.098 * r.k * st["stance"]
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        sway = math.sin(2 * math.pi * t / T)
        b = breath(t, T, 0.6)
        feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 9.0) for s, sg in SIDES}
        sp = torso_spec(V(0.011 * r.k * sway * st["sway"], r.P0.y + 0.004 * r.k * math.sin(4 * math.pi * t / T + 0.8), 0), roll=-0.9 * sway * st["sway"],
                        pitch=1.0, spine=0.5, chest=-1.0, head_pitch=1.0 + 0.6 * b, head_yaw=1.6 * math.sin(2 * math.pi * t / T + 1.3), br=b)
        sp["feet"] = feet
        sp["pos"].x = 0.011 * r.k * st["sway"]
        r.fit_z(sp, 0.994)
        z = sp["pos"].z
        sp["pos"] = V(0.011 * r.k * sway * st["sway"], sp["pos"].y, z - 0.002 * r.k * (1 - math.cos(4 * math.pi * t / T)) / 2)
        lag = math.sin(2 * math.pi * (t - 0.25) / T)
        sp["arms"] = lambda pts, lag=lag, b=b: {s: hang(r, pts, s, sg, out=st["arm_out"] + 0.003 * b, fwd=0.03 + 0.006 * lag * sg) for s, sg in SIDES}
        out.append(sp)
    return out


# =============================================================================================== march
def march(r, st, step_s=0.86, lift_m=0.22, fwd_m=0.16, swing=0.9, win=(0.10, 0.80), soft=False, arm_out=0.15):
    Ts = step_s * st["tempo"]
    steps = 4
    T = Ts * steps
    n = frames(T)
    w = 0.092 * r.k
    lift, fwd = lift_m * r.k, fwd_m * r.k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        step = int(t / Ts) % steps
        u = (t / Ts) % 1.0
        var = 1.0 + 0.035 * math.sin(2 * math.pi * t / T + 1.0)
        feet = {}
        for s, sg in SIDES:
            swinging = (step % 2 == 0) == (s == "L")
            g = 0.0
            if swinging:
                x = (u - win[0]) / win[1]
                a = smooth(x) if soft else smoother(x)
                g = math.sin(math.pi * a)
            f = r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0, pitch=34.0 * g)
            ball = f[0] + V(0, -fwd * g * g * var, lift * g * var)
            # the heel leaves first and the toes touch first: the pitch above pivots on the ball while it is still down
            feet[s] = (ball, f[1], f[2])
        sw = -math.sin(math.pi * t / Ts)                        # weight sits over the standing leg at mid-swing
        bob = -0.005 * r.k * math.cos(2 * math.pi * t / Ts)     # lowest at the changeover, tallest at mid-swing
        b = breath(t, T / 2, 0.3)
        sp = torso_spec(V(0.027 * r.k * sw, r.P0.y + 0.006 * r.k, 0), yaw=3.0 * sw, roll=2.4 * sw, pitch=3.5, spine=1.0, chest_yaw=-7.5 * sw,
                        head_pitch=1.5, head_yaw=0.0, br=b * 0.6)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
        # pelvis height from the standing leg only
        stand = "R" if step % 2 == 0 else "L"
        other = "L" if stand == "R" else "R"
        z_stand = r.fit_z(sp, 0.985, sides=(stand,))
        z_other = r.fit_z(sp, 0.985, sides=(other,))
        # blend the height across the changeover (half each at the switch, the standing leg at mid-swing), so the pelvis
        # never steps when the standing leg changes
        ws = 0.5 + 0.5 * math.sin(math.pi * u)
        sp["pos"].z = min(z_stand, lerp(z_other, z_stand, ws)) + bob - 0.005 * r.k
        lagt = t - 0.045
        arm_w = -math.sin(math.pi * lagt / Ts)                  # +1 at mid right-leg swing ... left arm forward then

        def arms(pts, arm_w=arm_w, var=var):
            res = {}
            for s, sg in SIDES:
                wv = (arm_w if s == "L" else -arm_w) * st["swing"] * var * swing
                a = math.radians(4.0 + 34.0 * wv)   # each arm goes forward with the opposite knee
                S = pts["S_" + s]
                ud = V(sg * arm_out, -math.sin(a), -math.cos(a)).normalized()   # (0.10: the hands brushed through the thighs -- QC)
                E = S + ud * r.a1[s]
                e = a + math.radians(80.0 + 14.0 * wv)                 # the elbow closes a little on the way up, opens behind the hip
                fd = V(-sg * 0.16, -math.sin(e), -math.cos(e)).normalized()
                res[s] = {"w": E + fd * r.a2[s], "pole": V(sg * 0.25, 1.0, -0.2), "palm": V(-sg, 0.1, 0.1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== squat
def _squat_pose(r, st, u, a, t, width=1.02, toe=20.0, lean_max=40.0, shin=33.0, arms_mode="reach"):
    """u: depth 0 (standing) .. 1 (thighs parallel); a: arms 0 (hanging) .. 1 (reaching forward).
    width / toe / lean_max / shin shape the stance (defaults: the bodyweight squat; wider + more toe-out = sumo)."""
    w = r.sh_half * width * st["stance"]
    feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * toe) for s, sg in SIDES}
    b = breath(t, 4.0, 0.0)
    lean = lean_max * (u ** 0.8)
    sp = torso_spec(V(0, r.P0.y, 0), pitch=1.0 + lean * 0.80, spine=lean * 0.10, chest=lean * 0.10 - 1.0, head_pitch=2.0 + 9.0 * u, br=b * (1 - 0.6 * u))
    sp["feet"] = feet
    sp["kpole"] = {s: V(sg * math.sin(math.radians(toe)) * 1.15, -math.cos(math.radians(toe)), 0) for s, sg in SIDES}   # knees over toes
    z_top = r.fit_z(sp, 0.992)
    # bottom: shins lean ~33 deg over the toes, hip joints level with the knees
    s_ = "L"
    A = r.ankle(s_, feet[s_])
    sig = math.radians(shin)
    kz = A.z + r.l2[s_] * math.cos(sig)
    k_fwd = r.l2[s_] * math.sin(sig)
    kx = A.x + k_fwd * math.sin(math.radians(toe))
    ky = A.y - k_fwd * math.cos(math.radians(toe))
    hjx = r.hj[s_].x
    back = math.sqrt(max(r.l1[s_] ** 2 - (kx - hjx) ** 2 - (0.012 * r.k) ** 2, 1e-6))
    hip_y, hip_z = ky + back, kz + 0.012 * r.k
    pel_b = Q(0, 1.0 + lean_max * 0.80, 0)
    off = pel_b @ r.hj[s_]
    y_b, z_b = hip_y - off.y, hip_z - off.z
    sp["pos"] = V(0, lerp(r.P0.y + 0.004 * r.k, y_b, u ** 0.9), lerp(z_top, z_b, u))

    def arms(pts):
        res = {}
        if arms_mode == "hang":                                  # dumbbells hanging at the sides, palms in
            return {s: hang(r, pts, s, sg, out=0.11 + 0.08 * u, fwd=0.0, reach=0.985) for s, sg in SIDES}   # wider as the knees come out (first render: weights against the knees)
        if arms_mode == "chest":                                 # hands together in front of the chest
            for s, sg in SIDES:
                S = pts["S_" + s]
                c = (pts["S_L"] + pts["S_R"]) / 2
                res[s] = {"w": V(c.x + sg * 0.035 * r.k, c.y - 0.24 * r.k, c.z - 0.17 * r.k), "pole": V(sg * 0.6, 0.5, -1.0),
                          "fingers": V(-sg * 0.3, -0.2, 1.0), "palm": V(-sg, 0.0, 0.0)}
            return res
        for s, sg in SIDES:
            S = pts["S_" + s]
            ang = math.radians(86.0 * a)
            reach = lerp(0.990, 0.985, a) * r.la
            dirv = V(lerp(sg * 0.13, -sg * 0.03, a), -math.sin(ang), -math.cos(ang)).normalized()
            res[s] = {"w": S + dirv * reach, "pole": V(sg * 0.5, 0.7, -0.6 * a + 0.1), "palm": V(-sg * lerp(1.0, 0.35, a), 0.15 * (1 - a), -a)}
        return res
    sp["arms"] = arms
    return sp


def squat(r, st):
    down, up = [], []
    hold0, lower, hold1 = 0.35, 2.0 * st["tempo"], 0.30
    n = frames(hold0 + lower + hold1)
    for i in range(n):
        t = i / FPS
        tau = (t - hold0) / lower
        down.append(_squat_pose(r, st, smoother(tau), smooth((t - hold0 + 0.05) / (lower * 0.8)), t))
    T0 = (n - 1) / FPS
    rise, top = 1.45 * st["tempo"], 0.5
    m = frames(rise + top)
    for i in range(m):
        t = i / FPS
        u = 1.0 - smoother(t / rise)
        a = 1.0 - smooth((t - 0.30 * rise) / (0.70 * rise))
        up.append(_squat_pose(r, st, u, a, T0 + t))
    up[-1] = _squat_pose(r, st, 0.0, 0.0, 0.0)
    down[0] = _squat_pose(r, st, 0.0, 0.0, 0.0)
    return down, up


# =============================================================================================== hip hinge
def _hinge_pose(r, st, u, t, grip=None):
    w = 0.105 * r.k * st["stance"]
    feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0) for s, sg in SIDES}
    b = breath(t, 4.0, 0.0)
    lean = 64.0 * u
    sp = torso_spec(V(0, r.P0.y, 0), pitch=1.0 + lean * 0.93, spine=lean * 0.035, chest=lean * 0.035 - 1.0, head_pitch=2.0 + (lean - 14.0 * u) * 0.92, br=b * (1 - 0.5 * u))
    sp["feet"] = feet
    sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
    z_top = r.fit_z(sp, 0.992)
    # bottom: shins stay vertical, knees soften ~22 deg, the hips travel straight back
    s_ = "L"
    A = r.ankle(s_, feet[s_])
    th = math.radians(22.0)
    sh = math.radians(-2.0)
    hip_y = A.y - r.l2[s_] * math.sin(sh) + r.l1[s_] * math.sin(th)
    hip_z = A.z + r.l2[s_] * math.cos(sh) + r.l1[s_] * math.cos(th) - 0.004 * r.k
    off = Q(0, 1.0 + 64.0 * 0.93, 0) @ r.hj[s_]
    y_b, z_b = hip_y - off.y, hip_z - off.z
    sp["pos"] = V(0, lerp(r.P0.y + 0.004 * r.k, y_b, u), lerp(z_top, z_b, u ** 1.3))

    def arms(pts):
        res = {}
        for s, sg in SIDES:
            S = pts["S_" + s]
            beta = math.radians(16.0 * u)                       # hands stay close to the legs: arms angle back toward the shins
            reach = 0.992 * r.la
            x_in = lerp(0.04, -0.035, u) * r.k
            dirv = V(sg * x_in / reach, lerp(-0.07, 0.0, u) + math.sin(beta), -math.cos(beta)).normalized()
            if grip == "front":
                # dumbbell RDL: overhand grip, the weights in front of the thighs (not beside them), sliding down close
                x_t = sg * HINGE_GRIP_X * r.k - S.x
                fwd = lerp(HINGE_GRIP_FWD, HINGE_GRIP_FWD_B, u)
                dirv = V(x_t / reach, -fwd + math.sin(beta), -1.0)
                dirv.z = -math.sqrt(max(1.0 - dirv.x ** 2 - dirv.y ** 2, 0.05))
                dirv.normalize()
                res[s] = {"w": S + dirv * reach, "pole": V(sg * 0.5, 0.8, 0.3), "fingers": dirv, "palm": V(-sg * 0.1, 1.0, 0.25 * u)}
                continue
            res[s] = {"w": S + dirv * reach, "pole": V(sg * 0.6, 0.5 - 0.4 * u, 0.6 * u), "palm": V(-sg * (1 - u) * 0.6, 1.0, 0.3 * u)}
        return res
    sp["arms"] = arms
    return sp


HINGE_GRIP_X, HINGE_GRIP_FWD, HINGE_GRIP_FWD_B = 0.160, 0.32, 0.13   # (0.22, then 0.28 on the male coach: plates in the thighs standing -- QC)


def hinge(r, st, grip=None):
    hold0, lower, hold1 = 0.35, 2.0 * st["tempo"], 0.40
    n = frames(hold0 + lower + hold1)
    down = [_hinge_pose(r, st, smoother((i / FPS - hold0) / lower), i / FPS, grip) for i in range(n)]
    T0 = (n - 1) / FPS
    rise, top = 1.55 * st["tempo"], 0.5
    m = frames(rise + top)
    up = [_hinge_pose(r, st, 1.0 - smoother((i / FPS) / rise), T0 + i / FPS, grip) for i in range(m)]
    up[-1] = _hinge_pose(r, st, 0.0, 0.0, grip)
    down[0] = _hinge_pose(r, st, 0.0, 0.0, grip)
    return down, up


# =============================================================================================== push-up
def _pushup_geometry(r, st):
    wrist_h = st["wrist_h"] * r.k
    yB = 0.66 * r.k

    def body(phi):
        feet = {}
        for s, sg in SIDES:
            ball = V(sg * 0.07 * r.k, yB, r.ball0[s].z)
            feet[s] = (ball, 0.0, phi - 4.0)
        A = r.ankle("L", feet["L"])
        up = Rx(phi) @ V(0, 0, 1)
        hipj = V(0, A.y, A.z) + up * (r.leg * st.get("leg_ext", 0.996))
        pel = Q(0, phi, 0)
        mid = (r.hj["L"] + r.hj["R"]) / 2
        pos = hipj - pel @ mid
        return feet, pos

    def blades(d):
        return 7.0 - 15.0 * d                                     # shoulder blades spread at the top, draw together at the bottom

    def shoulders(phi, d):
        feet, pos = body(phi)
        sp = torso_spec(pos, pitch=phi)
        sp["feet"] = feet
        sp["prot"] = {"L": blades(d), "R": blades(d)}
        sp["shrug"] = {"L": -2.0, "R": -2.0}
        _, pts = r.torso(sp)
        return pts

    def solve_phi(target_z, d):
        lo, hi = 15.0, 92.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if shoulders(mid, d)["S_L"].z > target_z:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    dx = 0.105 * r.k
    # soft elbows at the top (0.985 of the arm's reach): at 0.9965 the arms were all but locked and the elbow swung
    # wildly whenever the planted hands were pinned (QC: forearm jitter of 5-8 cm a frame on the male coach)
    top_z = wrist_h + math.sqrt((st.get("top_reach", TOP_REACH) * r.la) ** 2 - dx ** 2 - (0.03 * r.k) ** 2)
    phi_top = solve_phi(top_z, 0.0)
    phi_bot = solve_phi(wrist_h + st.get("bottom_h", 0.175) * r.k, 1.0)
    top = shoulders(phi_top, 0.0)
    wrist = {s: V(top["S_" + s].x + sg * dx, top["S_" + s].y + 0.03 * r.k, wrist_h) for s, sg in SIDES}
    return body, phi_top, phi_bot, wrist, blades


def _pushup_pose(r, st, geo, d, t):
    body, phi_top, phi_bot, wrist, blades = geo
    phi = lerp(phi_top, phi_bot, d)
    feet, pos = body(phi)
    b = breath(t, 4.0, 0.0)
    sp = torso_spec(pos, pitch=phi, spine=0.0, chest=0.0, head_pitch=phi - 8.0 + 2.0 * d, br=0.0)
    sp["nek"] = Q(0, phi - 3.0, 0)
    sp["feet"] = feet
    sp["kpole"] = {s: V(0, -0.2, -1) for s, sg in SIDES}
    prot = blades(d)
    sp["prot"] = {"L": prot, "R": prot}
    sp["shrug"] = {"L": -2.0, "R": -2.0}
    sp["arms"] = {s: {"w": wrist[s], "pole": V(sg * 0.72, 0.68, 0.15), "fingers": V(sg * 0.14, -1, 0), "palm": V(0, 0, -1)} for s, sg in SIDES}
    return sp


def pushup(r, st):
    geo = _pushup_geometry(r, st)
    hold0, lower, hold1 = 0.40, 2.0 * st["tempo"], 0.25
    n = frames(hold0 + lower + hold1)
    down = [_pushup_pose(r, st, geo, smoother((i / FPS - hold0) / lower), i / FPS) for i in range(n)]
    T0 = (n - 1) / FPS
    press, top = 1.25 * st["tempo"], 0.5
    m = frames(press + top)
    up = [_pushup_pose(r, st, geo, 1.0 - smoother((i / FPS) / press), T0 + i / FPS) for i in range(m)]
    up[-1] = _pushup_pose(r, st, geo, 0.0, 0.0)
    down[0] = _pushup_pose(r, st, geo, 0.0, 0.0)
    return down, up


# =============================================================================================== boxing
# push-up family: arms at the top of the press. At 0.985 (male 0.972) the elbows were near lockout and unlocked with a
# burst as each rep began (QC: elbow jerk ~800 m/s3 on the exported coaches)
TOP_REACH = 0.968

# straight punches stop short of a locked elbow (the lessons say so). At 0.9965 of the arm the elbow was all but locked:
# near lockout a millimetre of hand travel swings the elbow a long way, so it stopped dead and restarted in a frame
# (QC: elbow jerk ~650 m/s3 on the rig, ~1200 on the exported coach, in every jab and cross)
PUNCH_REACH = 0.955


def _stance_pose(r, st, t, e_jab=0.0, e_cross=0.0, travel=0.0, lead_step=0.0, rear_step=0.0, bob_amp=1.0, loop=3.2,
                 e_hook=0.0, slip=0.0, travel_x=0.0, e_rhook=0.0, e_rup=0.0, e_lup=0.0, dip=0.0, hip=None, jab_dz=0.0, pull=0.0,
                 cross_dz=0.0, hook_dz=0.0, rhook_dz=0.0, e_parry=0.0, e_catch=0.0, e_cover=0.0, e_bblock=0.0, bounce=0.0):
    """Orthodox stance (left foot leads, target straight ahead at -Y).
    e_jab / e_cross / e_hook: 0 guard .. 1 full extension. travel: forward shift of the whole stance (m).
    lead_step / rear_step: 0..1 bell while that foot is in the air during a push-step.
    slip: -1 (head to the left) .. +1 (head to the right, outside a jab). travel_x: sideways shift (m, + = left).
    hip: optional e_* values for the hips and feet, sampled a little ahead of the arm's, so the turn starts in the hips
    and the fist follows (kinetic chain).
    jab_dz: the jab's target height relative to the shoulder (m, negative = to the body).
    pull: 0..1 pull-back: the weight goes onto the rear leg and the upper body leans back out of range, head level.
    cross_dz / hook_dz / rhook_dz: target height of the cross / lead hook / rear hook (m, negative = to the body).
    e_parry: rear hand taps the incoming jab aside, across in front of the face. e_catch: rear palm opens a little in
    front of the face to catch a jab. e_cover: both gloves up tight to the temples, elbows in (high block). e_bblock:
    the lead elbow drops onto the ribs with a small crunch to that side (body block). bounce: 0..1 the light bounce on
    the balls of the feet."""
    k = r.k
    # a living stance: an uneven bounce on the balls of the feet (two harmonics that close on the loop), a slow sway
    n1 = max(1, round(loop / 0.85))
    n2 = max(1, round(loop / 2.0))
    ph = 2 * math.pi * t / loop
    bob = 0.65 * math.sin(n1 * ph) + 0.35 * math.sin(n2 * ph + 1.1)
    sway = math.sin(ph + 0.7)
    b = breath(t, loop, 0.4)                                     # one breath per loop, so the clip closes on itself
    hv = {"e_jab": e_jab, "e_cross": e_cross, "e_hook": e_hook, "e_rhook": e_rhook, "e_rup": e_rup, "e_lup": e_lup}
    hv.update(hip or {})
    # rear-hand punches turn the body like the cross (less for the uppercut); the lead uppercut turns it slightly the other way
    c = max(hv["e_cross"], 0.75 * hv["e_rhook"], 0.45 * hv["e_rup"])      # hips and feet
    ca = max(e_cross, 0.75 * e_rhook, 0.45 * e_rup)                        # chest and shoulders
    e_any = max(e_jab, e_cross, e_hook, e_rhook, e_rup, e_lup)
    # feet: lead toes turned in a little, rear foot ~50 deg out on its ball; the cross pivots the rear foot
    h = hv["e_hook"]
    # the lead hook pivots on the ball of the lead foot (heel turns out) as the hips turn through
    lead = r.foot("L", 0.115 * k * st["stance"], -0.155 * k, -18.0, pitch=0.0)
    lead = (lead[0], lerp(-18.0, -58.0, h), 16.0 * h)                # ball stays put; the heel swings out
    rear_yaw = lerp(-52.0, -8.0, c)
    rear_pitch = lerp(13.0, 30.0, c)
    rear = r.foot("R", -0.115 * k * st["stance"], 0.175 * k, -52.0, pitch=0.0)
    rear = (rear[0], rear_yaw, rear_pitch)
    shift = V(travel_x, -travel, 0)
    feet = {"L": (lead[0] + shift, lead[1], lead[2]), "R": (rear[0] + shift, rear[1], rear[2])}
    yaw_p = lerp(-34.0, 6.0, c) - 5.0 * hv["e_jab"] - 14.0 * h - 8.0 * hv["e_lup"]
    yaw_c = lerp(-42.0, 30.0, ca) - 12.0 * e_jab - 30.0 * e_hook - 18.0 * e_lup
    # weight moves onto the lead leg with each straight punch; a slow side-to-side sway when idle
    pos = V(0.012 * k * c + travel_x - 0.06 * k * slip + 0.006 * k * sway * bob_amp,
            0.012 * k - 0.045 * k * hv["e_jab"] - 0.075 * k * c - travel + 0.10 * k * pull, 0)
    sp = torso_spec(pos, yaw=yaw_p, pitch=2.5 + 2.0 * c + 1.5 * hv["e_jab"], spine=2.0, chest=5.0 + 2.5 * e_any, chest_yaw=yaw_c - yaw_p,
                    head_pitch=13.0 + 2.0 * max(e_jab, ca), head_yaw=lerp(-4.0, 3.0, ca) + 1.5 * math.sin(ph + 1.9) * bob_amp,
                    br=b * 0.5 * (1.0 - 0.6 * e_any))
    sp["feet"] = feet
    sp["kpole"] = {"L": V(-0.22 - 0.55 * h, -1, 0), "R": V(lerp(-0.75, -0.15, c), -1, 0)}
    if slip:
        # slip: bend the knees a little and lean the upper body sideways off the centre line; the head stays level
        a = abs(slip)
        sp["spi"] = Ry(-9.0 * slip) @ sp["spi"]
        sp["che"] = Ry(-17.0 * slip) @ sp["che"]
        sp["nek"] = Ry(-11.0 * slip) @ sp["nek"]
        sp["hed"] = Ry(-3.0 * slip) @ sp["hed"]
        sp["kpole"]["L"] = sp["kpole"]["L"] + V(-0.3 * slip, 0, 0)
    if e_bblock:
        # the lead side shortens: chest bends a little toward the lead hip and turns in, head stays over the feet
        sp["spi"] = Ry(5.0 * e_bblock) @ sp["spi"]
        sp["che"] = Ry(9.0 * e_bblock) @ Rz(-6.0 * e_bblock) @ sp["che"]
        sp["nek"] = Ry(-6.0 * e_bblock) @ sp["nek"]
    if e_cover:
        sp["che"] = Rx(4.0 * e_cover) @ sp["che"]                 # shoulders round a little behind the gloves, chin down
        sp["hed"] = Rx(6.0 * e_cover) @ sp["hed"]
    if bounce:
        # on the balls of both feet: the lead heel lifts too
        ball, yaw, pitch = sp["feet"]["L"]
        sp["feet"]["L"] = (ball, yaw, pitch + 10.0 * bounce)
        ball, yaw, pitch = sp["feet"]["R"]
        sp["feet"]["R"] = (ball, yaw, pitch + 6.0 * bounce)
    z = r.fit_z(sp, 0.985)
    # uppercuts: the knees dip first and drive up with the punch
    eu = max(hv["e_rup"], hv["e_lup"])
    up_dip = 0.035 * math.sin(math.pi * eu) ** 2 * (1.0 - eu)          # smooth: down early in the punch, back up as it lands
    sp["pos"].z = z - (0.044 + 0.007 * bob * bob_amp + 0.012 * c + 0.028 * abs(slip) + 0.10 * dip + up_dip + 0.03 * e_cover + 0.02 * e_bblock) * k
    if pull:
        # lean back from the hips over the rear leg; the neck tucks the chin so the eyes stay on the target
        # (first render: 13 deg at the chest was lost in the stance's forward lean -- now the shoulders end behind the hips)
        sp["pel"] = Rx(-7.0 * pull) @ sp["pel"]
        sp["spi"] = Rx(-16.0 * pull) @ sp["spi"]
        sp["che"] = Rx(-24.0 * pull) @ sp["che"]
        sp["nek"] = Rx(-10.0 * pull) @ sp["nek"]
        sp["hed"] = Rx(4.0 * pull) @ sp["hed"]
        sp["pos"].z -= 0.022 * k * pull
    if dip:
        sp["pel"] = Rx(6.0 * dip) @ sp["pel"]
        sp["spi"] = Rx(8.0 * dip) @ sp["spi"]
        sp["che"] = Rx(10.0 * dip) @ sp["che"]
    sp["shrug"] = {"L": 3.0 + 13.0 * e_jab, "R": 3.0 + 13.0 * ca}
    sp["prot"] = {"L": 7.0 + 12.0 * e_jab, "R": 5.0 + 14.0 * ca}
    drift = {"L": math.sin(n2 * ph + 0.4), "R": math.sin(n2 * ph + 2.2)}

    # (the e_* values are already eased by the punch curve; easing the arm blends a second time packed the elbow's
    # turn into a few frames -- QC: jerk 500-1200 m/s3 in hooks, blocks, parry, catch, uppercuts)
    def arms(pts):
        Hc = pts["head"]
        # guard: small independent drifts so the hands never look welded in place; the resting hand tucks in to the chin
        # while the other one punches
        tuck_r = max(e_jab, e_hook, e_lup, e_bblock)
        tuck_l = max(ca, e_parry, e_catch)
        gl = {"w": Hc + V(0.10 * k - 0.02 * k * tuck_l, -0.25 * k + 0.03 * k * tuck_l, -0.19 * k + 0.02 * k * tuck_l + 0.006 * k * drift["L"] * bob_amp),
              "pole": V(0.30, 0.25, -1), "fingers": V(-0.10, -0.30, 1.0), "palm": V(-1.0, 0.45, 0.0)}
        gr = {"w": Hc + V(-0.09 * k + 0.015 * k * tuck_r, -0.13 * k + 0.01 * k * tuck_r, -0.205 * k + 0.015 * k * tuck_r + 0.006 * k * drift["R"] * bob_amp),
              "pole": V(-0.30, 0.35, -1), "fingers": V(0.10, -0.25, 1.0), "palm": V(1.0, 0.45, 0.0)}
        res = {"L": gl, "R": gr}

        def straight(g, e, tgt, sg):
            """Straight punch: the fist travels the straight line from the chin with the elbow kept down behind it; the fist
            only turns over (palm down, elbow rotating out a little) in the last part of the extension."""
            # spread over the whole extension: (e-0.2)/0.8 through smoother() still packed ~80 deg of fist turn into one
            # frame at full speed (QC: rotation jump 80 deg/frame in every jab)
            turn = smooth(e)
            ext = {"w": tgt, "pole": V(sg * 0.5, 0.05, -0.75), "fingers": V(0, -1, 0), "palm": V(sg * 0.12, 0, -1)}
            out = mix_arm(g, ext, turn)
            out["pole"] = g["pole"].lerp(V(sg * 0.18, 0.05, -1.0), smooth(min(1.0, e * 2.0))).lerp(ext["pole"], turn)
            out["w"] = g["w"].lerp(tgt, e)
            return out
        if e_jab > 0:
            S = pts["S_L"]
            dz = 0.08 * k + jab_dz
            tgt = V(0.03 * k, S.y - math.sqrt(max((PUNCH_REACH * r.la) ** 2 - (S.x - 0.03 * k) ** 2 - dz ** 2, 1e-6)), S.z + dz)
            res["L"] = straight(gl, e_jab, tgt, 1.0)
        if e_cross > 0:
            S = pts["S_R"]
            dz = 0.08 * k + cross_dz
            tgt = V(0.01 * k, S.y - math.sqrt(max((PUNCH_REACH * r.la) ** 2 - (S.x - 0.01 * k) ** 2 - dz ** 2, 1e-6)), S.z + dz)
            res["R"] = straight(gr, e_cross, tgt, -1.0)
        if e_parry > 0:
            # a small tap across: the rear palm meets the jab in front of the lead shoulder and pushes it aside
            pa = {"w": gr["w"] + V(0.13 * k, -0.11 * k, 0.01 * k), "pole": V(-0.6, 0.3, -1.0), "fingers": V(0.25, -0.30, 1.0),
                  "palm": V(1.0, -0.6, 0.0)}
            res["R"] = mix_arm(gr, pa, e_parry)
        if e_catch > 0:
            # the rear palm opens toward the jab a hand's width in front of the face (it does not reach out for it)
            ca_ = {"w": gr["w"] + V(0.035 * k, -0.08 * k, 0.03 * k), "pole": V(-0.4, 0.3, -1.0), "fingers": V(0.05, -0.15, 1.0),
                   "palm": V(0.15, -1.0, 0.1)}
            res["R"] = mix_arm(gr, ca_, e_catch)
        if e_cover > 0:
            # high block: the gloves come up to the temples, forearms close in front of the face, elbows down and in
            for side, sg in (("L", 1.0), ("R", -1.0)):
                g = res[side]
                # gloves at the temples (QC: higher, they sat on top of the head)
                cv = {"w": Hc + V(sg * 0.080 * k, -0.100 * k, -0.115 * k), "pole": V(sg * 0.15, -0.35, -1.0), "fingers": V(-sg * 0.05, 0.10, 1.0),
                      "palm": V(-sg * 0.6, -0.8, 0.0)}
                res[side] = mix_arm(g, cv, e_cover)
        if e_bblock > 0:
            # body block: the lead elbow drops onto the ribs, the glove stays by the cheek
            bb = {"w": Hc + V(0.085 * k, -0.135 * k, -0.135 * k), "pole": V(0.15, 0.05, -1.0), "fingers": V(-0.15, -0.10, 1.0),
                  "palm": V(-1.0, 0.2, 0.0)}
            res["L"] = mix_arm(res["L"], bb, e_bblock)
        if e_rhook > 0:
            # rear hook: mirror of the lead hook, turned through by the rear foot and hips
            S = pts["S_R"]
            low = min(1.0, max(0.0, -rhook_dz / (0.25 * k)))       # to the body: elbow lower, fist turns palm-in / up
            tgt = V(Hc.x + 0.02 * k + 0.04 * k * low, S.y - 0.34 * k + 0.04 * k * low, S.z + 0.015 * k + rhook_dz)
            hk = {"w": tgt, "pole": V(-1.0, 0.25, 0.15).lerp(V(-0.7, 0.35, -0.6), low), "fingers": V(1.0, -0.35, 0.0),
                  "palm": V(0.0, 0.1, -1.0).lerp(V(0.0, 0.3, 1.0), 0.6 * low)}
            res["R"] = mix_arm(gr, hk, e_rhook)
            res["R"]["w"] = gr["w"].lerp(tgt, e_rhook) + V(-0.10 * k * math.sin(math.pi * e_rhook), 0, 0.02 * k * math.sin(math.pi * e_rhook))
        for side, e, sgn in (("R", e_rup, -1.0), ("L", e_lup, 1.0)):
            if e > 0:
                # uppercut: the fist drops a little, then rises close to the body to chin height, palm toward the face
                g = gl if side == "L" else gr
                S = pts["S_" + side]
                tgt = V(Hc.x + sgn * 0.02 * k, S.y - 0.27 * k, Hc.z - 0.05 * k)
                up = {"w": tgt, "pole": V(sgn * 0.3, 0.3, -1.0), "fingers": V(0.0, 0.25, 1.0), "palm": V(0.0, 1.0, 0.25)}
                res[side] = mix_arm(g, up, e)
                # (sin squared: the plain sine was cut off at e = 0.71 while still moving -- a corner in the fist's path)
                # one easing only, no fist dip -- the knees dip (up_dip). (A 7 cm fist dip reversing into the rise and a
                # second easing on top packed the acceleration into a few frames: elbow jerk ~1100 m/s3 -- QC)
                res[side]["w"] = g["w"].lerp(tgt, e) + V(0, -0.02 * k * e, 0)
        if e_hook > 0:
            # lead hook: elbow rises to shoulder height, forearm level, the fist swings round to just in front of the chin
            hh = e_hook
            S = pts["S_L"]
            low = min(1.0, max(0.0, -hook_dz / (0.25 * k)))
            tgt = V(Hc.x - 0.02 * k - 0.04 * k * low, S.y - 0.34 * k + 0.04 * k * low, S.z + 0.015 * k + hook_dz)
            hk = {"w": tgt, "pole": V(1.0, 0.25, 0.15).lerp(V(0.7, 0.35, -0.6), low), "fingers": V(-1.0, -0.35, 0.0),
                  "palm": V(0.0, 0.1, -1.0).lerp(V(0.0, 0.3, 1.0), 0.6 * low)}
            res["L"] = mix_arm(gl, hk, hh)
            res["L"]["w"] = gl["w"].lerp(tgt, hh) + V(0.10 * k * math.sin(math.pi * hh), 0, 0.02 * k * math.sin(math.pi * hh))   # swings out and round
        return res
    sp["arms"] = arms
    # push-step: the stepping foot skims the floor
    for s, g in (("L", lead_step), ("R", rear_step)):
        if g > 0:
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, 0, 0.03 * k * g), yaw, pitch + (6.0 * g if s == "R" else -4.0 * g))
    return sp


PUNCH_TEMPO = 1.12   # every extension and return 12 % longer (2026-11-26: punches were the highest-jerk clips; jerk ~ 1/time^3)


def _punch_curve(t, start, out, hold, back):
    out *= PUNCH_TEMPO
    back *= PUNCH_TEMPO
    if t < start:
        return 0.0
    t -= start
    # cubic ease both ways. (Tried 2026-11-26: the quintic and a bounded-jerk profile, smoother on paper, both raised
    # the measured mesh jerk of every punch -- their higher peak acceleration outweighs the cubic's softer ends.)
    if t < out:
        return smooth(t / out)
    t -= out
    if t < hold:
        return 1.0
    t -= hold
    u = max(0.0, min(1.0, t / back))
    # eased both ends. (smooth(u) ** 0.75 started the return with infinite acceleration -- QC: the elbow stopped dead
    # and left at full speed within a frame, jerk ~1000 m/s3 in every punch; before that a plain cut was a 3-4 cm snap)
    return 1.0 - smooth(u)


def stance(r, st):
    T = 3.2
    n = frames(T)
    return [_stance_pose(r, st, T * i / (n - 1), loop=T) for i in range(n)]


def jab(r, st):
    """Beginner tempo, matching the lesson text: a smooth, controlled extension that stops short of a locked elbow."""
    T = 2.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_jab=_punch_curve(t, 0.35, 0.45, 0.15, 0.50), loop=T,
                                hip={"e_jab": _punch_curve(t + 0.05, 0.35, 0.45, 0.15, 0.50)}))
    return out


def cross(r, st):
    T = 2.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_cross=_punch_curve(t, 0.35, 0.50, 0.15, 0.55), loop=T,
                                hip={"e_cross": _punch_curve(t + 0.08, 0.35, 0.50, 0.15, 0.55)}))
    return out


def guard_return(r, st):
    """The lesson: one hand moves slightly away from the face and comes straight back; pause; then the other hand."""
    T = 4.8
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        lead = 0.40 * _punch_curve(t, 0.40, 0.55, 0.30, 0.50)
        rear = 0.32 * _punch_curve(t, 2.80, 0.55, 0.30, 0.50)
        out.append(_stance_pose(r, st, t, e_jab=lead, e_cross=rear, loop=T))
    return out


def footwork(r, st):
    """Push-step in, then push-step out: the foot nearest the direction of travel moves first, the other follows,
    and the stance is the same width before and after."""
    step = 0.20 * r.k
    T = 1.6
    n = frames(T)

    def phase(t, forward):
        first = smoother((t - 0.20) / 0.38)                       # first foot in the air 0.20 - 0.50
        second = smoother((t - 0.46) / 0.38)                      # second foot follows 0.46 - 0.76
        body = smoother((t - 0.18) / 0.60)
        g1 = math.sin(math.pi * first)
        g2 = math.sin(math.pi * second)
        return first, second, body, g1, g2
    fwd, back = [], []
    for i in range(n):
        t = T * i / (n - 1)
        first, second, body, g1, g2 = phase(t, True)
        sp = _stance_pose(r, st, t, travel=step * body, lead_step=g1, rear_step=g2, bob_amp=0.0, loop=2 * T)
        for s, prog in (("L", first), ("R", second)):
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, -step * (prog - body), 0), yaw, pitch)
        fwd.append(sp)
        sp = _stance_pose(r, st, T + t, travel=step * (1 - body), lead_step=g2, rear_step=g1, bob_amp=0.0, loop=2 * T)
        for s, prog in (("R", first), ("L", second)):
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, step * (prog - body), 0), yaw, pitch)
        back.append(sp)
    return fwd, back


def lead_hook(r, st):
    """Beginner lead hook at a controlled tempo: elbow up to shoulder height, forearm level, the turn comes from the
    lead foot and hips; straight back to guard."""
    T = 2.4
    n = frames(T)
    return [_stance_pose(r, st, T * i / (n - 1), e_hook=_punch_curve(T * i / (n - 1), 0.35, 0.45, 0.20, 0.55), loop=T,
                         hip={"e_hook": _punch_curve(T * i / (n - 1) + 0.07, 0.35, 0.45, 0.20, 0.55)}) for i in range(n)]


def slip(r, st):
    """Slip to the right (outside an incoming jab), back to centre, then to the left; hands stay up."""
    T = 4.0
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        sl = 0.85 * _punch_curve(t, 0.40, 0.40, 0.25, 0.45) - 0.85 * _punch_curve(t, 2.15, 0.40, 0.25, 0.45)
        out.append(_stance_pose(r, st, t, slip=sl, bob_amp=0.3, loop=T))
    return out


def footwork_lateral(r, st):
    """Push-step to the left (the left foot moves first), then back to the right (the right foot moves first)."""
    step = 0.18 * r.k
    T = 1.6
    n = frames(T)
    out = []
    for direction in (1.0, -1.0):
        for i in range(n if direction > 0 else n):
            t = T * i / (n - 1)
            first = smoother((t - 0.20) / 0.38)   # (quintic: the cubic jolted at start and stop -- QC)
            second = smoother((t - 0.46) / 0.38)
            body = smoother((t - 0.18) / 0.60)
            g1, g2 = math.sin(math.pi * first), math.sin(math.pi * second)
            base = 0.0 if direction > 0 else step
            tx = base + direction * step * body
            lead_first = direction > 0
            sp = _stance_pose(r, st, t + (0 if direction > 0 else T), travel_x=tx,
                              lead_step=g1 if lead_first else g2, rear_step=g2 if lead_first else g1, bob_amp=0.0, loop=2 * T)
            for s_, prog in ((("L", first), ("R", second)) if lead_first else (("R", first), ("L", second))):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball + V(direction * step * (prog - body), 0, 0), yaw, pitch)
            if direction < 0 and i == 0:
                continue                                         # the first frame of the return equals the last of the step out
            out.append(sp)
    return out


# =============================================================================================== reverse lunge
def _lunge_geometry(r, st, back):
    """Bottom of a reverse lunge with leg `back` stepping back: front shin ~10 deg forward, front thigh just above
    level, rear knee a hand's width above the floor, rear heel up, torso upright with a slight lean."""
    k = r.k
    front = "L" if back == "R" else "R"
    fg = 1.0 if front == "L" else -1.0
    w = 0.095 * k * st["stance"]
    ff = r.foot(front, fg * w, r.ankle0[front].y, fg * 6.0)
    Af = r.ankle(front, ff)
    sh, th = math.radians(10.0), math.radians(8.0)
    Kf = Af + V(0, -r.l2[front] * math.sin(sh), r.l2[front] * math.cos(sh))
    Hf = Kf + V(0, r.l1[front] * math.cos(th), r.l1[front] * math.sin(th))
    lean = 8.0
    pel = Q(0, lean, 0)
    pos_b = V(0, 0, 0)
    pos_b = Hf - pel @ r.hj[front]
    pos_b.x = 0.0
    Hr = pos_b + pel @ r.hj[back]
    knee_z = 0.11 * k
    dz = Hr.z - knee_z
    Kr = V(Hr.x, Hr.y + math.sqrt(max(r.l1[back] ** 2 - dz * dz, 1e-6)), knee_z)
    pitch = 58.0
    bg = -fg
    probe = r.foot(back, bg * w, 0.0, bg * 4.0, pitch=pitch)
    off = probe[0] - r.ankle(back, probe)                       # ankle -> ball with the heel raised
    Az = r.ball0[back].z - off.z
    Ax = bg * w + 0.0
    dd = r.l2[back] ** 2 - (Az - Kr.z) ** 2 - (Ax - Kr.x) ** 2
    Ay = Kr.y + math.sqrt(max(dd, 1e-6))
    ball_b = V(Ax + off.x, Ay + off.y, r.ball0[back].z)
    return front, ff, ball_b, pitch, pos_b, lean


def _lunge_pose(r, st, geo, back, step, u, t):
    front, ff, ball_b, pitch, pos_b, lean = geo
    k = r.k
    bg = 1.0 if back == "L" else -1.0
    w = 0.095 * k * st["stance"]
    home = r.foot(back, bg * w, r.ankle0[back].y, bg * 6.0)
    g = math.sin(math.pi * smoother(step))           # (a sine of the linear step left and landed with a jolt)
    ball = home[0].lerp(ball_b, smoother(step)) + V(0, 0, 0.05 * k * g)
    yaw = lerp(home[1], bg * 4.0, smoother(step))      # (eased: the step and depth arrive linear; used raw, the knee
                                                       # direction, foot turn and lean stopped dead -- QC knee jerk)
    feet = {front: ff, back: (ball, yaw, pitch * smooth(min(1.0, step * 1.3)))}
    b = breath(t, 4.3, 0.0)
    # the hips travel back partly with the step and the rest while lowering, as in a real lunge
    hy = 0.6 * smoother(step) + 0.4 * smoother(u)
    sp = torso_spec(V(0, lerp(r.P0.y + 0.004 * k, pos_b.y, hy), 0), pitch=lerp(1.5, lean, smoother(u)), spine=0.5, chest=-1.0,
                    head_pitch=1.5 + 3.0 * smoother(u), br=b * 0.6)
    sp["feet"] = feet
    sp["kpole"] = {front: V(0, -1, 0), back: V(0, -1, -0.6 * smoother(step))}
    # pelvis height: a smooth blend between standing tall and the split-stance top (fitting it frame by frame while the
    # foot travels gives a kink where the rear leg becomes the limiting one)
    probe = dict(sp)
    probe["pos"] = V(0, r.P0.y + 0.004 * k, 0)
    probe["feet"] = {front: ff, back: home}
    z_stand = r.fit_z(probe, 0.982)
    probe["pos"] = V(0, lerp(r.P0.y + 0.004 * k, pos_b.y, 0.6), 0)
    probe["feet"] = {front: ff, back: (ball_b, bg * 4.0, pitch)}
    z_split = r.fit_z(probe, 0.982)
    z_top = lerp(z_stand, z_split, smoother(step))
    sp["pos"].z = lerp(z_top, pos_b.z, smoother(u))
    sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=st["arm_out"] + 0.01, fwd=0.03) for s, sg in SIDES}
    return sp


def reverse_lunge(r, st):
    """Right leg steps back and lowers, rises and steps in; then the left leg."""
    tp = st["tempo"]
    step_t, lower, hold, rise, back_t, rest = 0.95 * tp, 1.4 * tp, 0.3, 1.1 * tp, 0.95 * tp, 0.35
    T = step_t + lower + hold + rise + back_t + rest
    out = []
    for back in ("R", "L"):
        geo = _lunge_geometry(r, st, back)
        n = frames(T)
        for i in range(n):
            if back == "L" and i == 0:
                continue
            t = T * i / (n - 1)
            if t < step_t:
                stp, u = t / step_t, 0.0
            elif t < step_t + lower:
                stp, u = 1.0, (t - step_t) / lower
            elif t < step_t + lower + hold:
                stp, u = 1.0, 1.0
            elif t < step_t + lower + hold + rise:
                stp, u = 1.0, 1.0 - (t - step_t - lower - hold) / rise
            elif t < T - rest:
                stp, u = 1.0 - (t - step_t - lower - hold - rise) / back_t, 0.0
            else:
                stp, u = 0.0, 0.0
            out.append(_lunge_pose(r, st, geo, back, stp, u, t + (T if back == "L" else 0)))
    return out


# =============================================================================================== calf raise
def calf_raise(r, st):
    tp = st["tempo"]
    hold0, up, top, down, hold1 = 0.4, 1.0 * tp, 0.6, 1.6 * tp, 0.4
    T = hold0 + up + top + down + hold1
    n = frames(T)
    w = 0.095 * r.k * st["stance"]
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t < hold0:
            e = 0.0
        elif t < hold0 + up:
            e = smoother((t - hold0) / up)
        elif t < hold0 + up + top:
            e = 1.0
        elif t < hold0 + up + top + down:
            e = 1.0 - smoother((t - hold0 - up - top) / down)
        else:
            e = 0.0
        feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 5.0, pitch=27.0 * e) for s, sg in SIDES}
        b = breath(t, T, 0.0)
        sp = torso_spec(V(0, r.P0.y + 0.004 * r.k - 0.012 * r.k * e, 0), pitch=1.0, spine=0.5, chest=-1.0, head_pitch=1.0, br=b * 0.6)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.08, -1, 0) for s, sg in SIDES}
        r.fit_z(sp, 0.994)
        sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=st["arm_out"], fwd=0.03) for s, sg in SIDES}
        out.append(sp)
    return out


# =============================================================================================== step jack
def step_jack(r, st):
    """Low-impact jumping jack: one foot steps out to the side as both arms sweep overhead, then back in; alternate."""
    k = r.k
    Ts = 1.4 * st["tempo"]
    T = 2 * Ts
    n = frames(T)
    w0 = 0.075 * k
    reach_out = 0.30 * k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        side = "R" if t < Ts else "L"
        u = (t % Ts) / Ts if i < n - 1 else 1.0
        e = math.sin(math.pi * smooth(min(1.0, u / 0.92)))     # 0 -> 1 (out, arms up) -> 0
        lift = math.sin(math.pi * smooth(min(1.0, u / 0.46))) if u < 0.46 else math.sin(math.pi * smooth(min(1.0, (u - 0.46) / 0.46)))
        feet = {}
        for s, sg in SIDES:
            moving = s == side
            ax = sg * (w0 + (reach_out * e if moving else 0.0))
            f = r.foot(s, ax, r.ankle0[s].y, sg * 8.0, pitch=(12.0 * lift if moving else 0.0))
            feet[s] = (f[0] + V(0, 0, 0.065 * k * lift if moving else 0.0), f[1], f[2])
        b = breath(t, T, 0.0)
        cx = 0.5 * (feet["L"][0].x + feet["R"][0].x)
        sp = torso_spec(V(cx * 0.8, r.P0.y + 0.004 * k, 0), pitch=1.0, spine=0.5, chest=-1.5 - 2.0 * e, head_pitch=0.5, br=b * 0.5)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.15, -1, 0) for s, sg in SIDES}
        r.fit_z(sp, 0.975)

        def arms(pts, e=e):
            res = {}
            a = math.radians(lerp(9.0, 162.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = V(sg * math.sin(a), -0.10 - 0.06 * e, -math.cos(a)).normalized()
                palm = V(-sg * (1.0 - e), -e, 0.15).normalized()
                res[s] = {"w": S + d * (0.988 * r.la), "pole": V(0, 1.0, -0.2), "fingers": d, "palm": palm}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== glute bridge
def glute_bridge(r, st):
    """Lying on the back, knees bent, feet flat: the hips lift until shoulders, hips and knees form one line, then lower."""
    k = r.k
    tp = st["tempo"]
    hold0, up, top, down, hold1 = 0.6, 1.2 * tp, 1.0, 1.6 * tp, 0.5
    T = hold0 + up + top + down + hold1
    n = frames(T)
    S_z = 0.085 * k                                              # shoulder joints resting on the floor
    S_y = 0.40 * k
    hjL = r.hj["L"]
    l1, l2 = r.l1["L"], r.l2["L"]
    A_z = r.ankle0["L"].z
    alpha_bot = math.radians(3.0)

    def body(alpha):
        sp = torso_spec(V(0, 0, 0), pitch=-90.0 - math.degrees(alpha), head_pitch=-90.0 + 0.0)
        _, pts = r.torso(sp)
        mid = (pts["S_L"] + pts["S_R"]) / 2
        sp["pos"] = V(0, S_y, S_z) - mid
        return sp
    def knee(alpha):
        sp = body(alpha)
        return sp["pos"] + sp["pel"] @ hjL + V(0, -math.cos(alpha), math.sin(alpha)) * l1

    # the top: the hip-knee line continues the shoulder-hip line and the shin drops vertically to a flat foot
    lo, hi = 0.0, math.radians(45.0)
    for _ in range(40):
        m = (lo + hi) / 2
        if knee(m).z - l2 > A_z:
            hi = m
        else:
            lo = m
    alpha_top = (lo + hi) / 2
    K = knee(alpha_top)
    ankle_y = K.y
    w = 0.10 * k * st["stance"]
    feet = {}
    for s, sg in SIDES:
        f = r.foot(s, sg * w, 0.0, sg * 4.0)
        a0 = r.ankle(s, f)
        feet[s] = (f[0] + V(0, ankle_y - a0.y, 0), f[1], f[2])
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t < hold0:
            e = 0.0
        elif t < hold0 + up:
            e = smoother((t - hold0) / up)
        elif t < hold0 + up + top:
            e = 1.0
        elif t < hold0 + up + top + down:
            e = 1.0 - smoother((t - hold0 - up - top) / down)
        else:
            e = 0.0
        sp = body(lerp(alpha_bot, alpha_top, e))
        b = breath(t, T, 0.0)
        sp["che"] = Rx(-1.2 * b * 0.5) @ sp["che"]
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.12, -0.4, 1.0) for s, sg in SIDES}

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                wz = 0.085 * k                                   # (QC: at 0.035 the forearms sank 3 cm into the floor)
                dx = sg * 0.11 * k
                dy = -math.sqrt(max((0.985 * r.la) ** 2 - dx * dx - (S.z - wz) ** 2, 1e-6))
                res[s] = {"w": V(S.x + dx, S.y + dy, wz), "pole": V(sg * 0.4, 0, -1.0), "fingers": V(sg * 0.1, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== forearm plank
def plank_hold(r, st):
    """Forearm plank: elbows under the shoulders, forearms on the floor, one straight line from head to heels; breathing."""
    k = r.k
    T = 4.0
    n = frames(T)
    elbow_z = 0.07 * k                                           # (QC: at 0.045 the forearms sank 1.4 cm into the floor)
    yB = 0.70 * k

    def body(phi):
        feet = {}
        for s, sg in SIDES:
            ball = V(sg * 0.075 * k, yB, r.ball0[s].z)
            feet[s] = (ball, 0.0, phi - 2.0)
        A = r.ankle("L", feet["L"])
        up = Rx(phi) @ V(0, 0, 1)
        hipj = V(0, A.y, A.z) + up * (r.leg * 0.996)
        pel = Q(0, phi, 0)
        mid = (r.hj["L"] + r.hj["R"]) / 2
        return feet, hipj - pel @ mid

    def shoulders(phi):
        feet, pos = body(phi)
        sp = torso_spec(pos, pitch=phi)
        sp["feet"] = feet
        sp["prot"] = {"L": 6.0, "R": 6.0}
        _, pts = r.torso(sp)
        return pts
    target = elbow_z + r.a1["L"] * 0.995
    lo, hi = 50.0, 89.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if shoulders(mid)["S_L"].z > target:
            lo = mid
        else:
            hi = mid
    phi = (lo + hi) / 2
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        b = breath(t, T, 0.0)
        feet, pos = body(phi)
        sp = torso_spec(pos + V(0, 0, 0.003 * k * b), pitch=phi, head_pitch=phi - 6.0, br=b * 0.4)
        sp["feet"] = feet
        sp["kpole"] = {s: V(0, -0.2, -1) for s, sg in SIDES}
        sp["prot"] = {"L": 6.0, "R": 6.0}

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                E = V(S.x - sg * 0.01 * k, S.y, elbow_z)
                Wp = E + V(-sg * 0.06 * k, -math.sqrt(max(r.a2[s] ** 2 - (0.06 * k) ** 2, 1e-6)) * 0.995, 0)
                res[s] = {"w": Wp, "pole": V(0, 0.5, -1.0), "fingers": V(-sg * 0.25, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== batch 2 (no equipment)
def _phases(t, segs):
    """segs: list of (duration, start_value, end_value); smootherstep inside each segment. Returns the value at t."""
    acc = 0.0
    for d, a, b in segs:
        if t <= acc + d:
            # clamped to the segment's range (rounding can land a hair outside it; u ** 0.8 of -1e-17 is complex)
            return max(min(a, b), min(max(a, b), lerp(a, b, smoother((t - acc) / d)))) if d > 0 else b
        acc += d
    return segs[-1][2]


def _rep_segments(st, hold0=0.35, down=2.0, hold1=0.3, up=1.4, top=0.4):
    tp = st["tempo"]
    segs = [(hold0, 0, 0), (down * tp, 0, 1), (hold1, 1, 1), (up * tp, 1, 0), (top, 0, 0)]
    return segs, sum(d for d, _, _ in segs)


def sumo_squat(r, st):
    """Wide stance, toes turned out ~35 deg, knees track over the toes, chest tall; hands together in front of the chest."""
    kw = dict(width=1.75, toe=35.0, lean_max=22.0, shin=18.0, arms_mode="chest")
    down, up = [], []
    hold0, lower, hold1 = 0.35, 2.0 * st["tempo"], 0.30
    n = frames(hold0 + lower + hold1)
    for i in range(n):
        t = i / FPS
        down.append(_squat_pose(r, st, 0.85 * smoother((t - hold0) / lower), 1.0, t, **kw))
    T0 = (n - 1) / FPS
    rise, top = 1.45 * st["tempo"], 0.5
    m = frames(rise + top)
    for i in range(m):
        t = i / FPS
        up.append(_squat_pose(r, st, 0.85 * (1.0 - smoother(t / rise)), 1.0, T0 + t, **kw))
    return down, up


def split_squat(r, st):
    """Split stance held (right foot back on its ball); the body lowers straight down and rises, no stepping."""
    geo = _lunge_geometry(r, st, "R")
    segs, T = _rep_segments(st, 0.4, 1.6, 0.3, 1.2, 0.4)
    n = frames(T)
    return [_lunge_pose(r, st, geo, "R", 1.0, _phases(T * i / (n - 1), segs), T * i / (n - 1)) for i in range(n)]


def _side_lunge_pose(r, st, side, u, t):
    """Wide stance; the weight shifts over one foot, that knee bends over the toes, hips go back, the other leg stays long."""
    k = r.k
    w = 0.40 * k * st["stance"]
    feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 14.0) for s, sg in SIDES}
    sg_b = 1.0 if side == "L" else -1.0
    straight = "R" if side == "L" else "L"
    b = breath(t, 4.0, 0.0)
    lean = 28.0 * u
    sp = torso_spec(V(sg_b * 0.30 * k * u, r.P0.y + 0.004 * k + 0.10 * k * u, 0), pitch=1.0 + lean, spine=0.5, chest=-1.0,
                    head_pitch=1.5 + lean * 0.7, roll=-sg_b * 3.0 * u, br=b * 0.5)
    sp["feet"] = feet
    sp["kpole"] = {s: V(sg * 0.35, -1, 0) for s, sg in SIDES}
    r.fit_z(sp, 0.985, sides=(straight,))                       # the long leg sets the height; the bent leg follows
    sp["arms"] = lambda pts: {s: {"w": (pts["S_L"] + pts["S_R"]) / 2 + V(sg * 0.035 * k, -0.25 * k, -0.20 * k),
                                  "pole": V(sg * 0.6, 0.5, -1.0), "fingers": V(-sg * 0.3, -0.2, 1.0), "palm": V(-sg, 0, 0)} for s, sg in SIDES}
    return sp


def side_lunge(r, st):
    tp = st["tempo"]
    segs = [(0.4, 0, 0), (1.4 * tp, 0, 1), (0.3, 1, 1), (1.1 * tp, 1, 0), (0.3, 0, 0)]
    T1 = sum(d for d, _, _ in segs)
    n = frames(T1)
    out = []
    for side in ("R", "L"):
        for i in range(n):
            if side == "L" and i == 0:
                continue
            t = T1 * i / (n - 1)
            out.append(_side_lunge_pose(r, st, side, _phases(t, segs), t + (T1 if side == "L" else 0)))
    return out


def high_knee_march(r, st):
    # thigh up to about level. QC: with the warm-up march's timing the knee shot up at ~3.8 m/s and dropped straight
    # back (jerky); now a longer, evenly paced lift
    return march(r, st, step_s=1.10, lift_m=0.46, fwd_m=0.24, swing=1.25, win=(0.05, 0.90), soft=True, arm_out=0.24)


def arm_circles(r, st):
    """Arms out at shoulder height, small circles: two forward, two backward."""
    k = r.k
    T = 4.8
    n = frames(T)
    w = 0.098 * k * st["stance"]
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        rise = smoother(min(1.0, t / 0.5)) * smoother(min(1.0, (T - t) / 0.5))
        # two circles forward, a smooth stop, two back (QC: the direction flipped instantly at half time -- a jolt)
        uu = t / (T / 2)
        ph = 4 * math.pi * math.sin(0.5 * math.pi * min(uu, 2.0 - uu))
        b = breath(t, T, 0.0)
        feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 9.0) for s, sg in SIDES}
        sp = torso_spec(V(0, r.P0.y + 0.004 * k, 0), pitch=1.0, spine=0.5, chest=-1.0, head_pitch=1.0, br=b * 0.6)
        sp["feet"] = feet
        r.fit_z(sp, 0.994)

        def arms(pts, ph=ph, rise=rise):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                d_out = V(sg, -0.10, 0.02).normalized()
                circ = V(0, math.sin(ph), math.cos(ph)) * (0.09 * k * rise)
                outw = S + d_out * (0.90 * r.la) + circ                 # the circle stays inside the arm's reach
                hangw = hang(r, pts, s, sg, out=st["arm_out"])
                # the fingers turn from pointing down to pointing out as the arm rises (they switched over in one frame
                # at half height -- QC: the hands snapped ~38 deg)
                fing = V(0, 0, -1).lerp(d_out, smooth(rise))
                res[s] = {"w": hangw["w"].lerp(outw, rise), "pole": V(0, 1.0, -0.3 * rise),
                          "fingers": fing.normalized() if fing.length > 1e-6 else d_out,
                          "palm": V(-sg * (1 - rise), 0.15 * (1 - rise), -rise)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# ---- kneeling / all fours
def _quadruped_base(r, st, knee_y=0.20, spine=0.0, chest=0.0, head=0.0, pel_extra=0.0, wrists_fixed=None, pitch_fixed=None):
    """Hands under shoulders, knees under hips, shins and feet flat behind. Returns (spec, wrists, knees)."""
    k = r.k
    kz = 0.055 * k
    knees = {s: V(r.hj[s].x, knee_y * k, kz) for s, _ in SIDES}
    Hs = {s: knees[s] + V(0, 0, r.l1[s] * 0.998) for s, _ in SIDES}
    feet = {}
    for s, sg in SIDES:
        A = knees[s] + V(0, r.l2[s] * math.cos(math.radians(6.0)), r.l2[s] * math.sin(math.radians(6.0)))
        feet[s] = r.foot_toward(s, A, V(0, 1.0, -0.25))
    mid_h = (Hs["L"] + Hs["R"]) / 2
    mid_j = (r.hj["L"] + r.hj["R"]) / 2
    wrist_h = 0.058 * k                                          # (QC: at 0.050 the palms sank ~0.8 cm into the floor)

    def spec(pitch):
        sp = torso_spec(V(0, 0, 0), pitch=pitch + pel_extra, spine=spine, chest=chest, head_pitch=pitch - 14.0 + head)
        sp["pos"] = mid_h - sp["pel"] @ mid_j
        return sp
    lo, hi = 60.0, 110.0
    for _ in range(0 if pitch_fixed is not None else 40):
        m = (lo + hi) / 2
        _, pts = r.torso(spec(m))
        if wrists_fixed:                                         # planted hands: straight arms must still reach them
            too_far = max((pts["S_" + s_] - wrists_fixed[s_]).length for s_, _ in SIDES) > 0.993 * r.la
        else:
            too_far = pts["S_L"].z > wrist_h + 0.945 * r.la      # soft elbows, as people hold all fours
        if too_far:
            lo = m
        else:
            hi = m
    pitch = pitch_fixed if pitch_fixed is not None else (lo + hi) / 2
    sp = spec(pitch)
    _, pts = r.torso(sp)
    wrists = {s: V(pts["S_" + s].x + sg * 0.01 * k, pts["S_" + s].y - 0.02 * k, wrist_h) for s, sg in SIDES}
    sp["feet"] = feet
    sp["kpole"] = {s: V(0, -0.3, -1) for s, _ in SIDES}
    return sp, wrists, pitch


def _hands_on_floor(wrists, sides=("L", "R")):
    return {s: {"w": wrists[s], "pole": V(sg * 0.5, 0.6, 0.1), "fingers": V(-sg * 0.1, -1, 0), "palm": V(0, 0, -1)} for s, sg in SIDES}


def cat_cow(r, st):
    """On all fours: round the back (cat), then let the chest sink and lift the gaze (cow). Hands and knees stay put."""
    T = 6.0
    n = frames(T)
    base, wrists, pitch0 = _quadruped_base(r, st)

    def shoulders(x):
        sp, _, _ = _quadruped_base(r, st, spine=16.0 * x, chest=16.0 * x, head=24.0 * x, pel_extra=-16.0 * x, pitch_fixed=pitch0)
        _, pts = r.torso(sp)
        return pts
    # plant the hands under where the shoulders are midway between full cat and full cow, so both ends stay in reach
    cat_, cow_ = shoulders(1.0), shoulders(-1.0)
    wrists = {s_: V(wrists[s_].x, (cat_["S_" + s_].y + cow_["S_" + s_].y) / 2 - 0.02 * r.k, wrists[s_].z) for s_, _ in SIDES}
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        x = _phases(t, [(0.4, 0, 0), (1.6, 0, 1), (0.6, 1, 1), (1.6, 1, -1), (0.6, -1, -1), (1.2, -1, 0)])   # +1 cat, -1 cow
        # the spine curves between hips and shoulders: the pelvis tilts one way, the upper back the other, so the shoulders
        # stay over the hands (cat: tail tucks, back rounds up, head drops; cow: tail lifts, chest sinks, gaze lifts)
        # (the signs used to be reversed: the back sagged in "cat" while the head tucked -- QC, both coaches)
        sp, _, _ = _quadruped_base(r, st, spine=16.0 * x, chest=16.0 * x, head=24.0 * x, pel_extra=-16.0 * x, pitch_fixed=pitch0)
        for _ in range(6):                                       # if the rounded back lifts the shoulders out of reach,
            _, pts = r.torso(sp)                                 # the hips settle a little lower
            gap = max((pts["S_" + s_] - wrists[s_]).length for s_, _ in SIDES) - 0.985 * r.la
            if gap <= 0:
                break
            sp["pos"] = sp["pos"] - V(0, 0, gap * 1.2)
        sp["arms"] = _hands_on_floor(wrists)
        out.append(sp)
    return out


def bird_dog(r, st):
    """On all fours: reach one arm forward and the opposite leg back to hip height, hold, return; then the other side."""
    k = r.k
    base, wrists, pitch0 = _quadruped_base(r, st)
    segs = [(0.4, 0, 0), (1.3 * st["tempo"], 0, 1), (0.8, 1, 1), (1.1 * st["tempo"], 1, 0), (0.3, 0, 0)]
    T1 = sum(d for d, _, _ in segs)
    n = frames(T1)
    out = []
    for arm_side in ("R", "L"):
        leg = "L" if arm_side == "R" else "R"
        for i in range(n):
            if arm_side == "L" and i == 0:
                continue
            t = T1 * i / (n - 1)
            e = _phases(t, segs)
            sp, _, _ = _quadruped_base(r, st)
            feet = dict(sp["feet"])
            Hj = sp["pos"] + sp["pel"] @ r.hj[leg]
            A_ext = Hj + V(0, 0.99 * r.leg, 0.0)
            A0 = r.ankle(leg, feet[leg])
            A = A0.lerp(A_ext, e) + V(0, 0, 0.10 * k * math.sin(math.pi * e) * (1 - e))
            feet[leg] = r.foot_toward(leg, A, V(0, 1.0, -0.25).lerp(V(0, 0.2, -1.0), smooth(e)))
            sp["feet"] = feet
            # the reaching leg's pole blends in with the reach (switching it at the change of side twisted the kneeling
            # leg in one frame -- QC)
            sp["kpole"] = {s: (V(0, -0.3, -1).lerp(V(0, 0.2, -1), smooth(e / 0.15)) if s == leg else V(0, -0.3, -1)) for s, _ in SIDES}

            def arms(pts, e=e, arm_side=arm_side):   # (bound now: read late, both reps used the last side -- QC)
                res = _hands_on_floor(wrists)
                S = pts["S_" + arm_side]
                sg = 1.0 if arm_side == "L" else -1.0
                fwd = S + V(sg * 0.03 * k, -0.985 * r.la, 0.0)
                # the hand peels straight up off the floor first, then reaches forward (it used to slide forward while
                # still low, so the planted-hand pin held it back and let go with a jump -- QC)
                ef = smooth((e - 0.25) / 0.75)
                up = 0.07 * k * smooth(e / 0.25) * (1.0 - ef)       # (over 0.15 the male hand left in a burst -- QC)
                # at rest the lifting arm is exactly the planted arm (its own pole bent it and held the male hand 2.5 cm
                # up, and the elbow switched direction where the sides change -- QC); the lift pose blends in as it peels
                pl = _hands_on_floor(wrists)[arm_side]
                g = smooth(e / 0.25)
                res[arm_side] = {"w": wrists[arm_side].lerp(fwd, ef) + V(0, 0, up),
                                 "pole": pl["pole"].lerp(V(sg * 0.4, 0.6, -0.5), g).lerp(V(sg * 0.2, 0, -1), ef),
                                 "fingers": V(-sg * 0.1, -1, 0), "palm": V(0, 0, -1).lerp(V(-sg, 0, -0.2), ef)}
                return res
            sp["arms"] = arms
            out.append(sp)
    return out


def _kneeling_line(r, st, theta, knee_y):
    """Knees on the floor; one straight line from knees through hips to shoulders, `theta` deg above the floor."""
    k = r.k
    kz = 0.055 * k
    knees = {s: V(r.hj[s].x, knee_y, kz) for s, _ in SIDES}
    th = math.radians(theta)
    d = V(0, -math.cos(th), math.sin(th))
    H = {s: knees[s] + d * r.l1[s] * 0.998 for s, _ in SIDES}
    pitch = 90.0 - theta
    sp = torso_spec(V(0, 0, 0), pitch=pitch, head_pitch=pitch - 8.0)
    mid_h = (H["L"] + H["R"]) / 2
    mid_j = (r.hj["L"] + r.hj["R"]) / 2
    sp["pos"] = mid_h - sp["pel"] @ mid_j
    feet = {}
    for s, sg in SIDES:
        A = knees[s] + V(0, r.l2[s] * math.cos(math.radians(20.0)), r.l2[s] * math.sin(math.radians(20.0)))
        feet[s] = r.foot_toward(s, A, V(0, 1.0, -0.5))
    sp["feet"] = feet
    sp["kpole"] = {s: V(0, 0.2, -1) for s, _ in SIDES}
    return sp


def knee_pushup(r, st):
    """Push-up from the knees: one straight line knees-hips-shoulders, hands a little wider than the shoulders."""
    k = r.k
    wrist_h = 0.050 * k
    knee_y = 0.25 * k

    def sz(theta):
        _, pts = r.torso(_kneeling_line(r, st, theta, knee_y))
        return pts["S_L"].z

    def solve(target):
        lo, hi = 2.0, 70.0
        for _ in range(40):
            m = (lo + hi) / 2
            if sz(m) < target:
                lo = m
            else:
                hi = m
        return (lo + hi) / 2
    dx = 0.105 * k
    # soft elbows at the top, as in the push-up (0.9965 was locked: elbow jitter / male hands sliding -- QC)
    th_top = solve(wrist_h + math.sqrt((st.get("top_reach", TOP_REACH) * r.la) ** 2 - dx ** 2 - (0.03 * k) ** 2))
    th_bot = solve(wrist_h + 0.215 * k)                           # chest a fist above the floor, elbows clear of it
    _, top = r.torso(_kneeling_line(r, st, th_top, knee_y))
    wrist = {s: V(top["S_" + s].x + sg * dx, top["S_" + s].y + 0.03 * k, wrist_h) for s, sg in SIDES}

    def pose(d):
        sp = _kneeling_line(r, st, lerp(th_top, th_bot, d), knee_y)
        sp["prot"] = {"L": 7.0 - 15.0 * d, "R": 7.0 - 15.0 * d}
        sp["arms"] = {s: {"w": wrist[s], "pole": V(sg * 0.72, 0.68, 0.15), "fingers": V(sg * 0.14, -1, 0), "palm": V(0, 0, -1)} for s, sg in SIDES}
        return sp
    hold0, lower, hold1 = 0.40, 1.8 * st["tempo"], 0.25
    n = frames(hold0 + lower + hold1)
    down = [pose(smoother((i / FPS - hold0) / lower)) for i in range(n)]
    press, topt = 1.2 * st["tempo"], 0.5
    m = frames(press + topt)
    up = [pose(1.0 - smoother((i / FPS) / press)) for i in range(m)]
    return down, up


def _soft_len(d, dmax, knee=0.04):
    """Length d limited softly to dmax: unchanged below dmax * (1 - knee), then easing into dmax with no corner (a hard
    clamp, or none, left a leg locked straight and unlocking in a frame -- QC mountain climber)."""
    d0 = dmax * (1.0 - knee)
    if d <= d0:
        return d
    w = dmax - d0
    return d0 + w * (1.0 - math.exp(-(d - d0) / w))


def mountain_climber_slow(r, st):
    """High plank (push-up top); one knee drives toward the chest and returns, then the other. Slow, controlled."""
    k = r.k
    st = dict(st)
    st["leg_ext"] = 0.972          # the support leg keeps a bend (at 0.990 it was stretched past full length as the hips rose and unlocked in one frame -- QC)
    geo = _pushup_geometry(r, st)
    body, phi_top, phi_bot, wrist, blades = geo
    segs = [(0.3, 0, 0), (1.3 * st["tempo"], 0, 1), (0.3, 1, 1), (1.2 * st["tempo"], 1, 0), (0.2, 0, 0)]
    T1 = sum(d for d, _, _ in segs)
    n = frames(T1)
    out = []
    for side in ("R", "L"):
        for i in range(n):
            if side == "L" and i == 0:
                continue
            t = T1 * i / (n - 1)
            e = _phases(t, segs)
            sp = _pushup_pose(r, st, geo, 0.0, t)
            # the body pivots about the shoulders (hands stay planted) and the hips rise a little while the knee passes
            # under them, so the knee never brushes the floor
            # (sin**0.6 had an infinite slope at the start of each drive: the hips jolted up -- QC jerk peak)
            dl = st.get("mc_lift", 24.0) * smooth(min(1.0, e / 0.55))    # hips rise gradually with the knee     # (QC: at 15 deg the knee brushed the floor)
            _, pts0 = r.torso(sp)
            Sm = (pts0["S_L"] + pts0["S_R"]) / 2
            Rd = Rx(dl)
            for key_ in ("pel", "spi", "che", "nek", "hed"):
                sp[key_] = Rd @ sp[key_]
            sp["pos"] = Sm + Rd @ (sp["pos"] - Sm)
            feet, _ = body(phi_top)
            other = "L" if side == "R" else "R"
            ob, oy, op = feet[other]
            feet[other] = (ob, oy, op + 1.5 * dl)            # the support heel rises as the hips do (no over-reach)
            ball, yaw, pitch = feet[side]
            Hj = sp["pos"] + sp["pel"] @ r.hj[side]
            K_in = Hj + V(0, -0.36 * k, -0.05 * k)           # knee drives up toward the chest
            A_in = K_in + (V(0, 0.9, -0.30).normalized()) * r.l2[side]      # the foot hovers under the hips, off the floor
            A0 = r.ankle(side, feet[side])
            # The leg is driven by its joint angles: the thigh swings forward from the plank line to the chest while the
            # knee folds early, so the knee travels forward well above the floor and the foot stays tucked up behind it.
            # (QC: moving the ankle on a straight line made the knee drop onto the floor halfway, shin vertical.)
            def _ang(v):                                     # angle of a direction in the body's side plane
                return math.atan2(-v.y, -v.z)
            th0, th1 = _ang((A0 - Hj).normalized()), _ang((K_in - Hj).normalized())
            fl_in = _ang((A_in - K_in).normalized()) - th1   # knee flexion at the top (shin relative to thigh)
            es = smooth(e)
            th = lerp(th0, th1, es)
            fl = fl_in * smooth(min(1.0, e / 0.70))          # the knee folds early (over 0.55 it snapped shut, QC)
            thigh = V(0, -math.sin(th), -math.cos(th))
            shin = V(0, -math.sin(th + fl), -math.cos(th + fl))
            Kp = Hj + thigh * (r.l1[side] * 0.999)
            A = Kp + shin * (r.l2[side] * 0.999)
            A = A0.lerp(A, smooth(e / 0.08))                # starts exactly at the planted ankle (no step at the side switch)
            A.x = lerp(A0.x, A_in.x, es)
            A.z = max(A.z, lerp(A0.z, 0.11 * k, smooth(min(1.0, e / 0.25))))     # the foot never brushes the floor
            # (the limit starts above the planted length 0.972, so the planted leg is untouched and both sides join)
            A = Hj + (A - Hj) * (_soft_len((A - Hj).length, 0.994 * r.leg, knee=0.018) / max((A - Hj).length, 1e-6))
            d0 = (r.foot_q(side, yaw, pitch) @ r.fv[side]).normalized()
            feet[side] = r.foot_toward(side, A, d0.lerp(V(0, 0.5, -1.0).normalized(), smooth(e)), yaw=yaw)
            sp["feet"] = feet
            sg_ = 1.0 if side == "L" else -1.0                    # the knee travels a little outside the elbow line
            # The driving knee's pole turns with the thigh (the kneecap faces the floor in the plank and comes round to
            # the front as the thigh swings forward). Switching between two fixed poles twisted the near-straight leg
            # about its own axis in a few frames (QC: the shin spun ~45 deg per frame).
            sp["kpole"] = {s: V(sg_ * 0.12 * es, -math.cos(th), math.sin(th)) if s == side else V(0, -0.2, -1) for s, _ in SIDES}
            out.append(sp)
    return out


# ---- lying
def dead_bug(r, st):
    """On the back, hips and knees at 90 deg, arms to the ceiling; one arm lowers overhead as the opposite leg reaches out
    long, both stop just above the floor; return; switch sides. Lower back stays down."""
    k = r.k
    S_z, S_y = 0.085 * k, 0.40 * k
    sp0 = torso_spec(V(0, 0, 0), pitch=-92.0, head_pitch=-90.0)
    _, pts = r.torso(sp0)
    mid = (pts["S_L"] + pts["S_R"]) / 2
    pos = V(0, S_y, S_z) - mid
    segs = [(0.4, 0, 0), (1.6 * st["tempo"], 0, 1), (0.4, 1, 1), (1.3 * st["tempo"], 1, 0), (0.2, 0, 0)]
    T1 = sum(d for d, _, _ in segs)
    n = frames(T1)
    out = []
    for arm_side in ("R", "L"):
        leg = "L" if arm_side == "R" else "R"
        for i in range(n):
            if arm_side == "L" and i == 0:
                continue
            t = T1 * i / (n - 1)
            e = _phases(t, segs)
            b = breath(t, T1, 0.0)
            sp = torso_spec(pos.copy(), pitch=-92.0, head_pitch=-90.0, br=b * 0.5)
            feet, poles = {}, {}
            for s, sg in SIDES:
                Hj = sp["pos"] + sp["pel"] @ r.hj[s]
                K = Hj + V(0, -0.02 * k, r.l1[s] * 0.999)
                A_tab = K + V(0, -r.l2[s] * 0.999, 0)
                if s == leg:
                    A_long = Hj + V(0, -0.985 * r.leg * math.cos(math.radians(14.0)), 0.985 * r.leg * math.sin(math.radians(14.0)))
                    A = A_tab.lerp(A_long, e)
                else:
                    A = A_tab
                feet[s] = r.foot_toward(s, A, V(0, -0.35, 1.0))
                poles[s] = V(0, 1.0, 1.0)                        # knee above the hip (the hip->ankle line runs forward-up)
            sp["feet"] = feet
            sp["kpole"] = poles

            def arms(pts, e=e, arm_side=arm_side):   # (bound now: read late, both reps used the last side -- QC)
                res = {}
                for s, sg in SIDES:
                    S = pts["S_" + s]
                    upw = S + V(0, -0.02 * k, 0.985 * r.la)
                    over = S + V(sg * 0.02 * k, 0.985 * r.la * math.cos(math.radians(12.0)), 0.985 * r.la * math.sin(math.radians(12.0)))
                    w = upw.lerp(over, e) if s == arm_side else upw
                    if s == arm_side:
                        w = w + V(0, 0, 0.12 * k * math.sin(math.pi * e) * (1 - e))
                    res[s] = {"w": w, "pole": V(sg * 0.5, 0, -1.0), "fingers": (w - S).normalized(), "palm": V(-sg, 0, 0)}
                return res
            sp["arms"] = arms
            out.append(sp)
    return out


def superman(r, st):
    """Face down, arms reaching forward; lift arms, chest and legs a few centimetres, hold, lower. Gaze stays down."""
    k = r.k
    segs = [(0.5, 0, 0), (1.2 * st["tempo"], 0, 1), (1.0, 1, 1), (1.4 * st["tempo"], 1, 0), (0.4, 0, 0)]
    T = sum(d for d, _, _ in segs)
    n = frames(T)
    hip_z = 0.105 * k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = torso_spec(V(0, 0, 0), pitch=90.0, spine=-5.0 * e, chest=-7.0 * e, head_pitch=86.0 - 10.0 * e)
        mid_j = (r.hj["L"] + r.hj["R"]) / 2
        sp["pos"] = V(0, 0.05 * k, hip_z) - sp["pel"] @ mid_j
        feet = {}
        for s, sg in SIDES:
            Hj = sp["pos"] + sp["pel"] @ r.hj[s]
            ang = math.radians(4.0 + 9.0 * e)
            A = Hj + V(sg * 0.02 * k, 0.99 * r.leg * math.cos(ang), 0.99 * r.leg * math.sin(ang) - 0.03 * k)
            feet[s] = r.foot_toward(s, A, V(0, 1.0, -0.15))
        sp["feet"] = feet
        sp["kpole"] = {s: V(0, 0, -1) for s, _ in SIDES}

        def arms(pts, e=e):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                ang = math.radians(-6.0 + 14.0 * e)
                w = S + V(sg * 0.10 * k, -0.985 * r.la * math.cos(ang), 0.985 * r.la * math.sin(ang))
                res[s] = {"w": w, "pole": V(sg * 0.3, 0, 1.0), "fingers": V(0, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# ---- boxing batch 2
def _single_punch(r, st, key, out_s=0.45, hold=0.15, back=0.55, T=2.4):
    n = frames(T)
    return [_stance_pose(r, st, T * i / (n - 1), loop=T, **{key: _punch_curve(T * i / (n - 1), 0.35, out_s, hold, back)},
                         hip={key: _punch_curve(T * i / (n - 1) + 0.07, 0.35, out_s, hold, back)}) for i in range(n)]


def rear_uppercut(r, st):
    return _single_punch(r, st, "e_rup", 0.50, 0.15, 0.55)


def lead_uppercut(r, st):
    return _single_punch(r, st, "e_lup", 0.50, 0.15, 0.55)


def rear_hook(r, st):
    return _single_punch(r, st, "e_rhook", 0.50, 0.20, 0.55)


def roll(r, st):
    """Roll under an imaginary hook: knees bend, the upper body travels in a U from one side to the other, guard up."""
    T = 4.0
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        x = _phases(t, [(0.4, 0, 0), (0.35, 0, -0.6), (0.9, -0.6, 0.6), (0.35, 0.6, 0), (0.4, 0, 0), (0.35, 0, 0.6), (0.9, 0.6, -0.6), (0.35, -0.6, 0)])
        # the knees bend only while the head travels under (deepest in the middle of each U), never at rest
        dip = _phases(t, [(0.75, 0, 0), (0.45, 0, 1), (0.45, 1, 0), (1.1, 0, 0), (0.45, 0, 1), (0.45, 1, 0), (0.35, 0, 0)])
        out.append(_stance_pose(r, st, t, slip=x, dip=dip * 0.9, bob_amp=0.3, loop=T))
    return out


def footwork_pivot(r, st):
    """Pivot on the ball of the lead foot: the rear foot swings round ~40 deg and the whole stance turns with it; then back."""
    T = 3.2
    n = frames(T)
    base = _stance_pose(r, st, 0.0, loop=T)
    P = base["feet"]["L"][0].copy()
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        a = 40.0 * _phases(t, [(0.4, 0, 0), (0.6, 0, 1), (0.6, 1, 1), (0.6, 1, 0), (1.0, 0, 0)])
        lift = math.sin(math.pi * smooth((t - 0.4) / 0.6)) if 0.4 < t < 1.0 else (math.sin(math.pi * smooth((t - 1.6) / 0.6)) if 1.6 < t < 2.2 else 0.0)
        sp = _stance_pose(r, st, t, bob_amp=0.0, loop=T, rear_step=lift * 1.6)
        W = Matrix.Translation(P) @ Matrix.Rotation(math.radians(a), 4, "Z") @ Matrix.Translation(-P)
        sp["world"] = W
        # feet are solved in the unturned frame; the lead foot stays planted because the turn is about its ball
        out.append(sp)
    return out


# =============================================================================================== equipment
def _stand(r, st, t, w=0.10, toe=7.0, pitch=1.0, T=4.0, dz=0.0):
    k = r.k
    feet = {s: r.foot(s, sg * w * k * st["stance"], r.ankle0[s].y, sg * toe) for s, sg in SIDES}
    b = breath(t, T, 0.0)
    sp = torso_spec(V(0, r.P0.y + 0.004 * k, 0), pitch=pitch, spine=0.5, chest=-1.0, head_pitch=1.0, br=b * 0.6)
    sp["feet"] = feet
    sp["kpole"] = {s: V(sg * 0.08, -1, 0) for s, sg in SIDES}
    r.fit_z(sp, 0.990)
    sp["pos"].z -= dz * k
    return sp


CURL_TOP, CURL_ELBOW_FWD, CURL_OUT = 118.0, 0.06, 0.10


def db_curl(r, st):
    """Elbows stay by the sides; the dumbbells curl up with palms turning up, then lower slowly."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.1, 0.3, 1.8, 0.3)       # lifting 1.1 s, lowering 1.8 s
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            th = math.radians(8.0 + CURL_TOP * e)
            for s, sg in SIDES:
                S = pts["S_" + s]
                # the elbows stay by the sides but drift a little forward at the top, so the dumbbells finish in front of
                # the shoulders rather than inside the chest
                E = S + V(sg * (0.055 - 0.02 * e) * k, (0.01 - CURL_ELBOW_FWD * smooth(e)) * k, -r.a1[s] * 0.999)
                fd = V(sg * (0.12 + (CURL_OUT - 0.07) * e), -math.sin(th), -math.cos(th)).normalized()
                res[s] = {"w": E + fd * r.a2[s] * 0.999, "pole": V(sg * 0.15, 1.0, 0.0), "fingers": fd,
                          "palm": V(-sg * 0.25, -math.cos(th), math.sin(th))}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_shoulder_press(r, st):
    """Dumbbells at shoulder height, palms forward; press straight up to just short of locked, lower to the shoulders."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.2, 0.3, 1.8, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T, pitch=0.0)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                lo = S + V(sg * 0.10 * k, -0.04 * k, 0.05 * k)
                hi = S + V(sg * 0.06 * k, -0.03 * k, 0.985 * r.la)
                res[s] = {"w": lo.lerp(hi, e), "pole": V(sg * 1.0, 0.15, -0.6), "fingers": V(-sg * 0.1, 0, 1), "palm": V(0, -1, 0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_lateral_raise(r, st):
    """Arms rise out to the sides to shoulder height with a soft elbow, palms down, and lower slowly."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.2, 0.3, 1.8, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            a = math.radians(lerp(10.0, 86.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = V(sg * math.sin(a), -0.12, -math.cos(a)).normalized()
                res[s] = {"w": S + d * (0.96 * r.la), "pole": V(0, 1.0, 0.4), "fingers": d, "palm": V(-sg * (1 - e) * 0.8, 0.0, -e - 0.2)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_rdl(r, st):
    """Romanian deadlift with dumbbells: the hip hinge, overhand grip, weights sliding close down the front of the thighs."""
    return hinge(r, st, grip="front")


def db_bent_over_row(r, st):
    """Hinged ~45 deg with a flat back; the elbows pull back past the ribs, then the arms lower straight down."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.0, 0.4, 1.6, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _hinge_pose(r, st, 0.70, t)

        def arms(pts, e=e):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                down = S + V(sg * 0.02 * k, -0.04 * k, -0.985 * r.la)
                top = S + V(sg * 0.07 * k, 0.15 * k, -0.30 * k)
                res[s] = {"w": down.lerp(top, e), "pole": V(sg * 0.35, 1.0, 0.6), "fingers": V(0, -0.2, -1), "palm": V(-sg, 0, 0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


KB_DEPTH, KB_LEAN, KB_FWD_TOP = 1.0, 57.0, 0.21   # (0.15: the bell sat in the thighs at the top -- QC)


def _kb_pose(r, st, u, t):
    """Kettlebell deadlift: wide stance, hips back and down, flat back; both hands on the handle between the feet."""
    sp = _squat_pose(r, st, u * KB_DEPTH, 0.0, t, width=1.55, toe=25.0, lean_max=st.get("kb_lean", KB_LEAN), shin=22.0)
    k = r.k
    fwd = lerp(KB_FWD_TOP, 0.01, smooth(u)) * k                  # standing: the bell hangs in front of the hips, not between the thighs

    def arms(pts):
        res = {}
        mid = (pts["S_L"] + pts["S_R"]) / 2
        for s, sg in SIDES:
            S = pts["S_" + s]
            x = sg * 0.045 * k
            dz2 = (0.985 * r.la) ** 2 - (S.x - x) ** 2 - (S.y - mid.y + fwd) ** 2
            res[s] = {"w": V(x, mid.y - fwd, S.z - math.sqrt(max(dz2, 1e-6))), "pole": V(sg * 0.6, 0.6, 0.2),
                      "fingers": V(-sg * 0.2, 0.1, -1), "palm": V(0, 1.0, 0)}
        return res
    sp["arms"] = arms
    return sp


def kb_deadlift(r, st):
    hold0, lower, hold1 = 0.35, 1.8 * st["tempo"], 0.35
    n = frames(hold0 + lower + hold1)
    down = [_kb_pose(r, st, smoother((i / FPS - hold0) / lower), i / FPS) for i in range(n)]
    T0 = (n - 1) / FPS
    rise, top = 1.3 * st["tempo"], 0.5
    m = frames(rise + top)
    up = [_kb_pose(r, st, 1.0 - smoother((i / FPS) / rise), T0 + i / FPS) for i in range(m)]
    return down, up


def band_pull_apart(r, st):
    """Arms straight in front at shoulder height holding a light band; pull the hands apart until the arms are out to
    the sides, squeezing the shoulder blades; return slowly."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.1, 0.4, 1.6, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T)
        _effort(sp, e)
        sp["prot"] = {"L": 6.0 - 16.0 * e, "R": 6.0 - 16.0 * e}

        def arms(pts, e=e):
            res = {}
            a = math.radians(lerp(9.0, 82.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = V(sg * math.sin(a), -math.cos(a), -0.06).normalized()
                res[s] = {"w": S + d * (0.98 * r.la), "pole": V(sg * 0.2, 0.3, -1.0), "fingers": d, "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


INCLINE_BENCH_H = 0.45                                         # m, seat height of the bench the hands rest on


def incline_pushup(r, st):
    """Push-up with the hands on a sturdy bench: same straight line from head to heels, easier angle."""
    st2 = dict(st)
    st2["wrist_h"] = (INCLINE_BENCH_H + 0.035) / r.k
    st2["bottom_h"] = 0.25                                       # (QC: lower, the chest lay on the bench at the bottom)
    return pushup(r, st2)


# =============================================================================================== batch 3 (2026-11-23)
def _forward_lunge_pose(r, st, geo, back, step, u, t):
    """The reverse lunge's validated bottom position, reached the other way: the FRONT foot steps forward while the
    back foot stays planted (its heel rises as the weight moves onto the ball)."""
    front, ff, ball_b, pitch, pos_b, lean = geo
    k = r.k
    bg = 1.0 if back == "L" else -1.0
    w = 0.095 * k * st["stance"]
    home_b = r.foot(back, bg * w, r.ankle0[back].y, bg * 6.0)
    D = ball_b - home_b[0]                                          # how far the back foot travels in the reverse lunge
    D.z = 0.0
    g = math.sin(math.pi * smoother(step))           # (a sine of the linear step left and landed with a jolt)
    fball = ff[0] - D * smoother(step) + V(0, 0, 0.05 * k * g)
    feet = {front: (fball, ff[1], 0.0), back: (home_b[0], lerp(home_b[1], bg * 4.0, smoother(step)), pitch * smooth(min(1.0, step * 1.3)))}
    b = breath(t, 4.3, 0.0)
    # the hips travel forward with the step and settle between the feet while lowering
    hy = 0.6 * smoother(step) + 0.4 * smoother(u)
    end_y = pos_b.y - D.y
    sp = torso_spec(V(0, lerp(r.P0.y + 0.004 * k, end_y, hy), 0), pitch=lerp(1.5, lean, smoother(u)), spine=0.5, chest=-1.0,
                    head_pitch=1.5 + 3.0 * smoother(u), br=b * 0.6)
    sp["feet"] = feet
    sp["kpole"] = {front: V(0, -1, 0.2 * smoother(step)), back: V(0, -1, -0.6 * smoother(step))}
    probe = dict(sp)
    probe["pos"] = V(0, r.P0.y + 0.004 * k, 0)
    probe["feet"] = {front: ff, back: home_b}
    z_stand = r.fit_z(probe, 0.982)
    probe["pos"] = V(0, lerp(r.P0.y + 0.004 * k, end_y, 0.6), 0)
    probe["feet"] = {front: (ff[0] - D, ff[1], 0.0), back: (home_b[0], bg * 4.0, pitch)}
    z_split = r.fit_z(probe, 0.982)
    z_top = lerp(z_stand, z_split, smoother(step))
    sp["pos"].z = lerp(z_top, pos_b.z, smoother(u))
    sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=st["arm_out"] + 0.01, fwd=0.03) for s, sg in SIDES}
    return sp


def forward_lunge(r, st):
    """Right foot steps forward and the body lowers between the feet; push back to standing; then the left foot."""
    tp = st["tempo"]
    step_t, lower, hold, rise, back_t, rest = 0.95 * tp, 1.3 * tp, 0.3, 1.1 * tp, 1.0 * tp, 0.35
    T = step_t + lower + hold + rise + back_t + rest
    out = []
    for fwd in ("R", "L"):
        back = "L" if fwd == "R" else "R"
        geo = _lunge_geometry(r, st, back)
        n = frames(T)
        for i in range(n):
            if fwd == "L" and i == 0:
                continue
            t = T * i / (n - 1)
            if t < step_t:
                stp, u = t / step_t, 0.0
            elif t < step_t + lower:
                stp, u = 1.0, (t - step_t) / lower
            elif t < step_t + lower + hold:
                stp, u = 1.0, 1.0
            elif t < step_t + lower + hold + rise:
                stp, u = 1.0, 1.0 - (t - step_t - lower - hold) / rise
            elif t < T - rest:
                stp, u = 1.0 - (t - step_t - lower - hold - rise) / back_t, 0.0
            else:
                stp, u = 0.0, 0.0
            out.append(_forward_lunge_pose(r, st, geo, back, stp, u, t + (T if fwd == "L" else 0)))
    return out


def db_hammer_curl(r, st):
    """Curl with the palms facing each other (thumbs up) the whole way; elbows by the sides, slow on the way down."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.1, 0.3, 1.8, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            th = math.radians(8.0 + CURL_TOP * e)
            for s, sg in SIDES:
                S = pts["S_" + s]
                E = S + V(sg * (0.055 - 0.02 * e) * k, (0.01 - CURL_ELBOW_FWD * smooth(e)) * k, -r.a1[s] * 0.999)
                fd = V(sg * (0.10 + 0.04 * e), -math.sin(th), -math.cos(th)).normalized()
                palm = V(-sg, 0.0, 0.0)                              # thumbs up: palm toward the body's midline
                palm = (palm - fd * palm.dot(fd)).normalized()
                res[s] = {"w": E + fd * r.a2[s] * 0.999, "pole": V(sg * 0.15, 1.0, 0.0), "fingers": fd, "palm": palm}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_front_raise(r, st):
    """Arms rise in front to shoulder height with a soft elbow, palms turning from the thighs to the floor; lower slowly."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.2, 0.3, 1.8, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            a = math.radians(lerp(18.0, 84.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                # hands at shoulder width: two dumbbells held across the body need ~0.3 m between the hands or their
                # inner ends collide in front of the hips (seen in the first render)
                d = V(sg * 0.06, -math.sin(a), -math.cos(a)).normalized()
                palm = V(0.0, 1.0 - e, -0.15 - e)
                palm = (palm - d * palm.dot(d)).normalized()
                res[s] = {"w": S + d * (0.96 * r.la), "pole": V(sg * 0.6, 0.2, 0.4), "fingers": d, "palm": palm}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def one_two(r, st):
    """Jab, then cross: the cross starts as the jab comes home, the hips turn into each punch; back to guard."""
    T = 2.9
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_jab=_punch_curve(t, 0.30, 0.40, 0.10, 0.42), e_cross=_punch_curve(t, 0.95, 0.42, 0.12, 0.50),
                                loop=T, hip={"e_jab": _punch_curve(t + 0.05, 0.30, 0.40, 0.10, 0.42),
                                             "e_cross": _punch_curve(t + 0.08, 0.95, 0.42, 0.12, 0.50)}))
    return out


def one_two_hook(r, st):
    """Jab, cross, lead hook: each punch starts as the one before comes home; back to guard."""
    T = 3.7
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_jab=_punch_curve(t, 0.30, 0.40, 0.10, 0.42), e_cross=_punch_curve(t, 0.95, 0.42, 0.12, 0.50),
                                e_hook=_punch_curve(t, 1.70, 0.45, 0.18, 0.55), loop=T,
                                hip={"e_jab": _punch_curve(t + 0.05, 0.30, 0.40, 0.10, 0.42),
                                     "e_cross": _punch_curve(t + 0.08, 0.95, 0.42, 0.12, 0.50),
                                     "e_hook": _punch_curve(t + 0.07, 1.70, 0.45, 0.18, 0.55)}))
    return out


# =============================================================================================== batch 4 (2026-11-23)
def knee_crunch(r, st):
    """Standing knee crunch: hands by the ears, elbows wide; one knee drives up to hip height while the chest curls a
    little toward it and turns so the opposite elbow comes toward the knee; down with control; then the other side.
    The stepping is the march's (validated: planted foot, pelvis height from the standing leg, blended changeover)."""
    Ts = 1.7 * st["tempo"]
    steps = 4
    T = Ts * steps
    n = frames(T)
    w = 0.092 * r.k
    lift, fwd = 0.50 * r.k, 0.26 * r.k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        step = int(t / Ts) % steps
        u = (t / Ts) % 1.0
        feet = {}
        gs = 0.0
        up_side = "L" if step % 2 == 0 else "R"
        for s, sg in SIDES:
            g = 0.0
            if s == up_side:
                a = smoother((u - 0.12) / 0.76)
                g = math.sin(math.pi * a)
                gs = g
            f = r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0, pitch=30.0 * g)
            ball = f[0] + V(0, -fwd * g * g, lift * g)
            feet[s] = (ball, f[1], f[2])
        usg = 1.0 if up_side == "L" else -1.0
        crunch = gs ** 1.2
        b = breath(t, T / 2, 0.3)
        sp = torso_spec(V(0.020 * r.k * usg * -gs, r.P0.y + 0.006 * r.k, 0), yaw=0.0, roll=-2.0 * usg * gs, pitch=3.5 + 6.0 * crunch,
                        spine=1.0 + 9.0 * crunch, chest=-1.0 + 6.0 * crunch, chest_yaw=11.0 * usg * crunch,
                        head_pitch=1.5 + 6.0 * crunch, br=b * 0.6)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
        stand = "R" if up_side == "L" else "L"
        other = up_side
        z_stand = r.fit_z(sp, 0.985, sides=(stand,))
        z_other = r.fit_z(sp, 0.985, sides=(other,))
        ws = 0.5 + 0.5 * math.sin(math.pi * u)
        sp["pos"].z = min(z_stand, lerp(z_other, z_stand, ws)) - 0.005 * r.k

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                # fingertips by the ears: wrists just above and behind the shoulders, elbows out to the sides
                wpos = S + V(-sg * 0.045 * r.k, 0.035 * r.k, 0.205 * r.k)
                res[s] = {"w": wpos, "pole": V(sg * 1.0, -0.15, 0.25), "fingers": V(-sg * 0.3, 0.2, 1.0).normalized(), "palm": V(-sg * 0.2, -1.0, 0.0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_reverse_fly(r, st):
    """Hinged ~45 deg with a flat back, arms hanging; raise the arms out to the sides with a soft elbow, squeezing the
    shoulder blades; lower slowly."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.1, 0.4, 1.7, 0.3)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _hinge_pose(r, st, 0.70, t)

        def arms(pts, e=e):
            res = {}
            a = math.radians(lerp(6.0, 70.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = V(sg * math.sin(a), -0.10 * math.cos(a), -math.cos(a)).normalized()
                palm = V(-sg * (1.0 - e), 0.0, -e)
                palm = (palm - d * palm.dot(d)).normalized() if palm.length > 1e-6 else V(0, 0, -1)
                res[s] = {"w": S + d * (0.95 * r.la), "pole": V(sg * 0.2, 1.0, 0.3), "fingers": d, "palm": palm}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def db_overhead_triceps(r, st):
    """Dumbbells overhead, palms in, upper arms by the head; bend the elbows to lower the weights behind the head, keep
    the elbows pointing up; straighten."""
    k = r.k
    segs, T = _rep_segments(st, 0.4, 1.6, 0.3, 1.2, 0.4)        # lowering slow, pressing up a little quicker
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, T=T, pitch=0.0)
        _effort(sp, e)

        def arms(pts, e=e):
            res = {}
            th = math.radians(lerp(6.0, 128.0, e))               # elbow bend: forearms end pointing down behind the head
            for s, sg in SIDES:
                S = pts["S_" + s]
                # upper arm near vertical beside the ear, the elbow pointing up; the forearm drops behind the head, a
                # little out to the side so the weights pass beside the head, not into it (first render: elbows too
                # wide and forearms level -- the weights stuck out beside the head)
                E = S + V(sg * 0.06 * k, 0.045 * k, r.a1[s] * 0.97)
                fd = V(sg * 0.16, math.sin(th), math.cos(th)).normalized()
                res[s] = {"w": E + fd * r.a2[s] * 0.97, "pole": V(sg * 0.3, -0.4, 1.0), "fingers": fd,
                          "palm": (V(-sg, 0, 0) - fd * V(-sg, 0, 0).dot(fd)).normalized()}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def jab_jab_cross(r, st):
    """Double jab then cross (1-1-2): the second jab starts as the first comes back; the cross follows the second."""
    T = 3.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        j = min(1.0, _punch_curve(t, 0.30, 0.38, 0.08, 0.36) + _punch_curve(t, 0.95, 0.38, 0.10, 0.40))
        jh = min(1.0, _punch_curve(t + 0.05, 0.30, 0.38, 0.08, 0.36) + _punch_curve(t + 0.05, 0.95, 0.38, 0.10, 0.40))
        c = _punch_curve(t, 1.62, 0.42, 0.12, 0.50)
        out.append(_stance_pose(r, st, t, e_jab=j, e_cross=c, loop=T,
                                hip={"e_jab": jh, "e_cross": _punch_curve(t + 0.08, 1.62, 0.42, 0.12, 0.50)}))
    return out


# =============================================================================================== batch 5 (2026-11-23)
def db_squat(r, st):
    """Bodyweight squat path with a dumbbell hanging in each hand, palms in, arms long beside the legs."""
    segs, T = _rep_segments(st, 0.4, 2.0, 0.3, 1.45, 0.45)
    n = frames(T)
    return [_squat_pose(r, st, 0.92 * _phases(T * i / (n - 1), segs), 0.0, T * i / (n - 1), arms_mode="hang")
            for i in range(n)]


def db_reverse_lunge(r, st):
    """The validated reverse lunge (right then left) with dumbbells hanging at the sides."""
    return reverse_lunge(r, st)


OBL_SIGN = 1.0


def oblique_crunch(r, st):
    """Standing oblique crunch: hands by the ears, elbows wide; one knee lifts out to the side (hip opened ~35 deg)
    while the trunk bends sideways so that elbow comes down toward it; back to standing; then the other side.
    Stepping as the knee crunch (planted foot, pelvis height from the standing leg)."""
    Ts = 1.8 * st["tempo"]
    steps = 4
    T = Ts * steps
    n = frames(T)
    w = 0.092 * r.k
    lift, side = 0.34 * r.k, 0.12 * r.k                            # foot stays under the knee (first render: shin flung out)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        step = int(t / Ts) % steps
        u = (t / Ts) % 1.0
        up_side = "L" if step % 2 == 0 else "R"
        usg = 1.0 if up_side == "L" else -1.0
        feet = {}
        gs = 0.0
        for s, sg in SIDES:
            g = 0.0
            if s == up_side:
                g = math.sin(math.pi * smoother((u - 0.12) / 0.76))
                gs = g
            # the toe turns out and the foot moves sideways only once it is off the floor (first audit: 1.5 cm slide
            # from the foot pivoting at lift-off)
            f = r.foot(s, sg * w, r.ankle0[s].y, sg * (6.0 + 30.0 * g * g), pitch=25.0 * g)
            feet[s] = (f[0] + V(sg * side * g ** 1.5, -0.05 * r.k * g, lift * g), f[1], f[2])
        c = gs ** 1.2
        b = breath(t, T / 2, 0.3)
        # side bend toward the lifted knee (roll), the pelvis shifts a little over the standing foot
        sp = torso_spec(V(-0.022 * r.k * usg * gs, r.P0.y + 0.004 * r.k, 0), roll=-3.0 * usg * gs, pitch=2.0 + 2.0 * c,
                        spine=1.0, chest=-1.0, br=b * 0.6, head_pitch=1.5)
        bend = OBL_SIGN * 24.0 * usg * c                         # trunk side bend toward the lifted knee
        sp["spi"] = Ry(bend * 0.45) @ sp["spi"]
        sp["che"] = Ry(bend) @ sp["che"]
        sp["nek"] = Ry(bend * 0.8) @ sp["nek"]
        sp["hed"] = Ry(bend * 0.6) @ sp["hed"]
        sp["feet"] = feet
        # the lifted knee's pole blends in with the lift: switching it while the leg is straight twisted the whole
        # leg about its axis in one frame (glitch at the change of side)
        sp["kpole"] = {s: V(sg * 0.10, -1, 0).lerp(V(sg * 0.65, -0.55, 0.55), gs if s == up_side else 0.0) for s, sg in SIDES}
        stand = "R" if up_side == "L" else "L"
        z_stand = r.fit_z(sp, 0.985, sides=(stand,))
        z_other = r.fit_z(sp, 0.985, sides=(up_side,))
        ws = 0.5 + 0.5 * math.sin(math.pi * u)
        sp["pos"].z = min(z_stand, lerp(z_other, z_stand, ws)) - 0.005 * r.k

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                wpos = S + V(-sg * 0.045 * r.k, 0.035 * r.k, 0.205 * r.k)
                res[s] = {"w": wpos, "pole": V(sg * 1.0, -0.15, 0.25), "fingers": V(-sg * 0.3, 0.2, 1.0).normalized(), "palm": V(-sg * 0.2, -1.0, 0.0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def double_jab(r, st):
    """Two quick jabs (the second starts as the first comes back), then a moment in guard."""
    T = 2.6
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        # (summed, not max(): the max of two overlapping curves has a corner where they cross -- QC: hand jerk ~1500)
        j = min(1.0, _punch_curve(t, 0.30, 0.36, 0.08, 0.34) + _punch_curve(t, 0.92, 0.36, 0.10, 0.40))
        jh = min(1.0, _punch_curve(t + 0.05, 0.30, 0.36, 0.08, 0.34) + _punch_curve(t + 0.05, 0.92, 0.36, 0.10, 0.40))
        out.append(_stance_pose(r, st, t, e_jab=j, loop=T, hip={"e_jab": jh}))
    return out


# =============================================================================================== batch 6 — fighting (2026-11-23)
def body_jab(r, st):
    """Jab to the body: the knees bend to change level first (no bending at the waist), the jab lands at the
    opponent's chest height, then the hand comes home and the legs straighten back to the stance."""
    T = 2.8
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        lv = _punch_curve(t, 0.25, 0.40, 0.75, 0.55)               # level change starts before the punch, ends after it
        e = _punch_curve(t, 0.45, 0.40, 0.15, 0.45)
        eh = _punch_curve(t + 0.05, 0.45, 0.40, 0.15, 0.45)
        out.append(_stance_pose(r, st, t, e_jab=e, dip=0.85 * lv, jab_dz=-0.20 * r.k, loop=T, hip={"e_jab": eh}))
    return out


def cross_hook(r, st):
    """Cross then lead hook (2-3): the hips turn through for the cross and turn back for the hook."""
    T = 2.8
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        c = _punch_curve(t, 0.30, 0.40, 0.10, 0.42)
        ch = _punch_curve(t + 0.08, 0.30, 0.40, 0.10, 0.42)
        h = _punch_curve(t, 0.95, 0.40, 0.15, 0.50)
        hh = _punch_curve(t + 0.07, 0.95, 0.40, 0.15, 0.50)
        out.append(_stance_pose(r, st, t, e_cross=c, e_hook=h, loop=T, hip={"e_cross": ch, "e_hook": hh}))
    return out


def pull_back(r, st):
    """Pull back: from the stance the weight shifts onto the rear leg and the upper body leans back just out of reach,
    hands up, eyes on the target; then back to the stance. Done twice per clip."""
    T = 3.6
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        p = _punch_curve(t, 0.35, 0.40, 0.30, 0.50) + _punch_curve(t, 2.00, 0.40, 0.30, 0.50)
        out.append(_stance_pose(r, st, t, pull=min(1.0, p), bob_amp=0.4, loop=T))
    return out


def step_jab(r, st):
    """Step-jab: the jab lands as the lead foot lands from a push-step forward, the rear foot follows; then a push-step
    back to where it started, hands in guard."""
    step = 0.20 * r.k
    T = 1.7
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        first = smoother((t - 0.20) / 0.38)
        second = smoother((t - 0.48) / 0.38)
        body = smoother((t - 0.18) / 0.60)
        g1, g2 = math.sin(math.pi * first), math.sin(math.pi * second)
        e = _punch_curve(t, 0.18, 0.34, 0.12, 0.45)
        sp = _stance_pose(r, st, t, e_jab=e, travel=step * body, lead_step=g1, rear_step=g2, bob_amp=0.0, loop=2 * T,
                          hip={"e_jab": _punch_curve(t + 0.05, 0.18, 0.34, 0.12, 0.45)})
        for s_, prog in (("L", first), ("R", second)):
            ball, yaw, pitch = sp["feet"][s_]
            sp["feet"][s_] = (ball + V(0, -step * (prog - body), 0), yaw, pitch)
        out.append(sp)
    for i in range(1, n):
        t = T * i / (n - 1)
        first = smoother((t - 0.20) / 0.38)
        second = smoother((t - 0.46) / 0.38)
        body = smoother((t - 0.18) / 0.60)
        g1, g2 = math.sin(math.pi * first), math.sin(math.pi * second)
        sp = _stance_pose(r, st, T + t, travel=step * (1 - body), lead_step=g2, rear_step=g1, bob_amp=0.0, loop=2 * T)
        for s_, prog in (("R", first), ("L", second)):
            ball, yaw, pitch = sp["feet"][s_]
            sp["feet"][s_] = (ball + V(0, step * (prog - body), 0), yaw, pitch)
        out.append(sp)
    return out


# =============================================================================================== natural movement (2026-11-24)
# QC metrics (tools/qc/natural.py) found the clips too clean to read as a person: 20-40 % of frames with no joint moving
# at all (holds frozen like a mannequin, the plank 98 %), both arms moving as exact mirror images in every two-handed
# exercise, and the head and chest dead still while the arms lift dumbbells. Three small layers fix that.

# Lying / planted clips: breathing only (no sway that would slide the body on the floor)
LIFE_FLOOR = ("pushup_", "knee_pushup_", "incline_pushup_", "plank_hold", "mountain_climber_slow", "bird_dog", "cat_cow",
              "superman", "glute_bridge", "dead_bug")


def _with_life(name, specs):
    """A living body under every clip: a slow postural sway of the pelvis, a little breathing in the chest, small head
    adjustments. Whole cycles over the clip (zero at both ends), so loops and down/up pairs still join exactly; the
    pelvis only ever moves down (never over-reaching a straight standing leg); planted feet / hands are absolute IK
    targets, so they stay put."""
    n = len(specs)
    if n < 8:
        return specs
    T = n / FPS
    floor = name.startswith(LIFE_FLOOR)
    k1 = max(1, round(T / 3.6))                                 # breaths per clip
    k2 = max(1, round(T / 5.0))                                 # sway cycles per clip
    out = []
    for i, sp in enumerate(specs):
        sp = dict(sp)
        u = i / (n - 1)
        br = math.sin(2 * math.pi * k1 * u)
        sw = math.sin(2 * math.pi * k2 * u)
        sw2 = math.sin(4 * math.pi * k2 * u + 0.8 * math.sin(2 * math.pi * k2 * u))
        if not floor:
            pos = sp["pos"].copy()
            pos.x += 0.0035 * sw
            pos.z -= 0.0012 * (1.0 - math.cos(2 * math.pi * k1 * u)) * 0.5
            sp["pos"] = pos
            sp["pel"] = Ry(0.5 * sw) @ sp["pel"]
            sp["spi"] = Ry(-0.4 * sw) @ sp["spi"]
            sp["hed"] = Rz(1.2 * sw2) @ Rx(0.7 * br) @ sp["hed"]
            sp["nek"] = Rz(0.6 * sw2) @ sp["nek"]
        else:                                                   # on the floor: the trunk rises and falls with the breath
            pos = sp["pos"].copy()
            pos.z += 0.0022 * br
            sp["pos"] = pos
            sp["hed"] = Rx(0.8 * br) @ Rz(0.8 * sw2) @ sp["hed"]
        sp["che"] = Rx(-0.7 * br) @ sp["che"]                  # in-breath: the chest lifts a little
        sh = dict(sp.get("shrug", {}))
        for s_ in ("L", "R"):
            sh[s_] = sh.get(s_, 0.0) + 0.8 * max(0.0, br)
        sp["shrug"] = sh
        out.append(sp)
    return out


def _effort(sp, e):
    """Standing dumbbell work: the trunk answers the load -- a slight lean back and lift of the chest as the weights
    go up, the head steady (it counter-rotates a little), shoulders braced."""
    sp["che"] = Rx(-1.6 * e) @ sp["che"]
    sp["spi"] = Rx(-0.8 * e) @ sp["spi"]
    sp["hed"] = Rx(1.2 * e) @ sp["hed"]
    sh = dict(sp.get("shrug", {}))
    for s_ in ("L", "R"):
        sh[s_] = sh.get(s_, 0.0) + 1.5 * e
    sp["shrug"] = sh


# Two-handed moves: the left arm trails the right by a couple of frames (people never move both arms as exact mirror
# images). Clips that start and end at rest only; never in down/up pairs (the join would break) or planted hands.
DESYNC = {"db_curl": 2, "db_hammer_curl": 2, "db_shoulder_press": 2, "db_lateral_raise": 2, "db_front_raise": 2,
          "db_overhead_triceps": 2, "db_reverse_fly": 2, "db_bent_over_row": 2, "arm_circles": 1, "step_jack": 1,
          "db_squat": 1, "db_reverse_lunge": 1, "reverse_lunge": 1, "calf_raise": 1,
          "db_shrug": 2, "db_calf_raise": 1, "good_morning": 1, "squat_calf_raise": 1}
DESYNC_BONES = ("shoulder_L", "upper_arm_L", "forearm_L", "hand_L")


def _desync(frames_, name):
    d = DESYNC.get(name, 0)
    n = len(frames_)
    if not d or n < 4 * d:
        return frames_
    out = []
    for i, fr in enumerate(frames_):
        fr = dict(fr)
        j = max(0, i - d)
        if i >= n - d:                                         # the last frames ease back onto the clip's own end pose
            a = (i - (n - d - 1)) / d
            for bn in DESYNC_BONES:
                if bn in fr:
                    l0, r0 = frames_[j][bn]
                    l1, r1 = frames_[i][bn]
                    fr[bn] = (l0.lerp(l1, a), r0.slerp(r1, a))
        else:
            for bn in DESYNC_BONES:
                if bn in fr:
                    fr[bn] = frames_[j][bn]
        out.append(fr)
    return out


# which clips show which prop (tools/blender/coach_props.py adds the meshes and keys their visibility)
PROPS_BY_CLIP = {
    "db_curl": ("dumbbell_L", "dumbbell_R"), "db_shoulder_press": ("dumbbell_L", "dumbbell_R"),
    "db_lateral_raise": ("dumbbell_L", "dumbbell_R"), "db_bent_over_row": ("dumbbell_L", "dumbbell_R"),
    "db_rdl_down": ("dumbbell_L", "dumbbell_R"), "db_rdl_up": ("dumbbell_L", "dumbbell_R"),
    "kb_deadlift_down": ("kettlebell",), "kb_deadlift_up": ("kettlebell",),
    "band_pull_apart": ("band",),
    "db_hammer_curl": ("dumbbell_L", "dumbbell_R"), "db_front_raise": ("dumbbell_L", "dumbbell_R"),
    "db_reverse_fly": ("dumbbell_L", "dumbbell_R"), "db_overhead_triceps": ("dumbbell_L", "dumbbell_R"),
    "db_squat": ("dumbbell_L", "dumbbell_R"), "db_reverse_lunge": ("dumbbell_L", "dumbbell_R"),
    "incline_pushup_down": ("bench",), "incline_pushup_up": ("bench",),
}


STYLE = {
    # the two coaches perform the same technique; only build-related details differ
    "coach_f": {"stance": 1.0, "sway": 1.0, "arm_out": 0.085, "tempo": 1.0, "swing": 1.0, "wrist_h": 0.050},
    "coach_m": {"stance": 1.06, "sway": 0.8, "arm_out": 0.105, "tempo": 1.04, "swing": 0.9, "wrist_h": 0.050, "kb_lean": 64.0,
                "mc_lift": 17.0, "top_reach": 0.958},   # (0.985: the male's longer mesh arms could not reach -- hands slid)   # longer arms: the hips sit higher in the plank, less lift needed (24 over-reached 5.7 cm)
}


# clips in which no shoe rests on the floor: the build must not pull the shoes down to it
NO_FLOOR_CONTACT = {"dead_bug", "superman", "reverse_crunch", "toe_taps"}
# batch 7 (clips_fit2.py): props per clip, floor clips breathe only
PROPS_BY_CLIP.update({
    "db_goblet_squat": ("dumbbell_goblet",), "db_floor_press": ("dumbbell_L", "dumbbell_R"), "db_shrug": ("dumbbell_L", "dumbbell_R"),
    "db_calf_raise": ("dumbbell_L", "dumbbell_R"), "kb_swing": ("kettlebell",), "bench_dip": ("bench_dip",),
    "wall_pushup": ("wall_front",), "wall_sit": ("wall_back",),
})
LIFE_FLOOR = LIFE_FLOOR + ("crunch", "heel_taps", "reverse_crunch", "toe_taps", "high_plank", "shoulder_taps", "single_leg_bridge",
                           "donkey_kick", "fire_hydrant", "childs_pose", "bear_hold", "db_floor_press", "bench_dip", "wall_pushup")


def build_all(arm, height, name):
    """Replaces every demonstration clip on the control rig with its authored version. Returns the clip names."""
    st = STYLE.get(name, STYLE["coach_f"])
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    r = Rig(arm, height)
    r.write("idle_neutral", idle(r, st))
    r.write("warmup_march", march(r, st))
    for base, fn in (("squat", squat), ("hip_hinge", hinge), ("pushup", pushup)):
        d, u = fn(r, st)
        r.write(base + "_down", d)
        r.write(base + "_up", u)
    r.write("boxing_stance", stance(r, st))
    r.write("boxing_jab", jab(r, st))
    r.write("boxing_cross", cross(r, st))
    r.write("boxing_guard_return", guard_return(r, st))
    f, b = footwork(r, st)
    r.write("footwork_forward", f)
    r.write("footwork_backward", b)
    # added 2026-11-21 (owner's request for more exercises)
    r.write("boxing_lead_hook", lead_hook(r, st))
    r.write("boxing_slip", slip(r, st))
    r.write("footwork_lateral", footwork_lateral(r, st))
    r.write("reverse_lunge", reverse_lunge(r, st))
    r.write("calf_raise", calf_raise(r, st))
    r.write("step_jack", step_jack(r, st))
    r.write("glute_bridge", glute_bridge(r, st))
    r.write("plank_hold", plank_hold(r, st))
    # batch 2 (2026-11-21)
    for base, fn in (("sumo_squat", sumo_squat), ("knee_pushup", knee_pushup)):
        d, u = fn(r, st)
        r.write(base + "_down", d)
        r.write(base + "_up", u)
    for name, fn in (("split_squat", split_squat), ("side_lunge", side_lunge), ("high_knee_march", high_knee_march),
                     ("arm_circles", arm_circles), ("cat_cow", cat_cow), ("bird_dog", bird_dog),
                     ("mountain_climber_slow", mountain_climber_slow), ("dead_bug", dead_bug), ("superman", superman),
                     ("boxing_rear_uppercut", rear_uppercut), ("boxing_lead_uppercut", lead_uppercut), ("boxing_rear_hook", rear_hook),
                     ("boxing_roll", roll), ("footwork_pivot", footwork_pivot)):
        r.write(name, fn(r, st))
    # equipment
    for base, fn in (("db_rdl", db_rdl), ("kb_deadlift", kb_deadlift), ("incline_pushup", incline_pushup)):
        d, u = fn(r, st)
        r.write(base + "_down", d)
        r.write(base + "_up", u)
    for name, fn in (("db_curl", db_curl), ("db_shoulder_press", db_shoulder_press), ("db_lateral_raise", db_lateral_raise),
                     ("db_bent_over_row", db_bent_over_row), ("band_pull_apart", band_pull_apart)):
        r.write(name, fn(r, st))
    # batch 3 (2026-11-23)
    for name, fn in (("forward_lunge", forward_lunge), ("db_hammer_curl", db_hammer_curl), ("db_front_raise", db_front_raise),
                     ("boxing_one_two", one_two), ("boxing_one_two_hook", one_two_hook)):
        r.write(name, fn(r, st))
    # batch 4 (2026-11-23)
    for name, fn in (("knee_crunch", knee_crunch), ("db_reverse_fly", db_reverse_fly), ("db_overhead_triceps", db_overhead_triceps),
                     ("boxing_jab_jab_cross", jab_jab_cross)):
        r.write(name, fn(r, st))
    # batch 5 (2026-11-23)
    for name, fn in (("db_squat", db_squat), ("db_reverse_lunge", db_reverse_lunge), ("oblique_crunch", oblique_crunch),
                     ("boxing_double_jab", double_jab)):
        r.write(name, fn(r, st))
    # batch 6 — fighting (2026-11-23)
    for name, fn in (("boxing_body_jab", body_jab), ("boxing_cross_hook", cross_hook), ("boxing_pull_back", pull_back),
                     ("boxing_step_jab", step_jab)):
        r.write(name, fn(r, st))
    # batch 7 — 30 fighting fundamentals (2026-11-24)
    import clips_fight2 as cf2
    RETIME.update(cf2.RETIME)
    for name, fn in cf2.CLIPS:
        r.write(name, fn(r, st))
    # batch 7 — 30 fitness lessons (2026-11-24)
    import clips_fit2 as cfit
    RETIME.update(cfit.RETIME)
    for name, fn in cfit.CLIPS:
        r.write(name, fn(r, st))
    # batch 8 — cool-down stretches (2026-11-26)
    import clips_stretch as cst
    RETIME.update(cst.RETIME)
    for name, fn in cst.CLIPS:
        r.write(name, fn(r, st))
    # batch 9 — mobility (2026-11-27)
    import clips_mobility as cmo
    RETIME.update(cmo.RETIME)
    for name, fn in cmo.CLIPS:
        r.write(name, fn(r, st))
    print("authored clips:", len(bpy.data.actions), "| worst leg over-reach", round(r.worst_leg, 4), "m, arm", round(r.worst_arm, 4), "m")
    return [a.name for a in bpy.data.actions]
