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

FPS = 30
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

    def hip_joint(self, sp, s):
        return sp["pos"] + sp["pel"] @ self.hj[s]

    def fit_z(self, sp, ext=0.992, sides=("L", "R")):
        """Highest pelvis at which the straighter leg is extended to `ext` of its length (soft knees, never locked)."""
        lo, hi = 0.15, 1.6
        for _ in range(40):
            mid = (lo + hi) / 2
            sp["pos"].z = mid
            worst = max((self.hip_joint(sp, s) - self.ankle(s, sp["feet"][s])).length / (self.l1[s] + self.l2[s]) for s in sides)
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
            zp = zh - yf * zh.dot(yf)
            if zp.length > 1e-4:
                zp.normalize()
                tw = math.atan2(zf.cross(zp).dot(yf), zf.dot(zp))
                tw = max(-1.2, min(1.2, tw)) * 0.5
                rot = Matrix.Rotation(tw, 3, yf)
                xf, zf = rot @ xf, rot @ zf
            M[fa] = Matrix.Translation(E) @ _frame(xf, yf, zf).to_4x4()
            M[hd] = Matrix.Translation(W) @ _frame(xh, fing, zh).to_4x4()
        for bn in self.order:
            if bn not in M:
                M[bn] = self._child(M, bn)
        return M

    def write(self, name, specs):
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm = self.arm
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        prev = {}
        for f, sp in enumerate(specs):
            M = self.solve(sp)
            for bn in self.order:
                p = self.parent[bn]
                inherit = self.rest[bn] if p is None else M[p] @ self.rest[p].inverted() @ self.rest[bn]
                loc, rot, _ = (inherit.inverted() @ M[bn]).decompose()
                if bn in prev and prev[bn].dot(rot) < 0:
                    rot = -rot
                prev[bn] = rot
                pb = arm.pose.bones[bn]
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = rot
                pb.keyframe_insert("rotation_quaternion", frame=f + 1)
                pb.location = loc if bn == "hips" else (0, 0, 0)
                pb.keyframe_insert("location", frame=f + 1)
        act.frame_range = (1, len(specs))
        arm.animation_data.action = None
        return act


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
def march(r, st):
    Ts = 0.62 * st["tempo"]
    steps = 4
    T = Ts * steps
    n = frames(T)
    w = 0.092 * r.k
    lift, fwd = 0.30 * r.k, 0.20 * r.k
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
                a = smooth((u - 0.10) / 0.80)
                g = math.sin(math.pi * a)
            f = r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0, pitch=34.0 * g ** 0.8)
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
        base = r.fit_z(sp, 0.996, sides=(stand,))
        # blend the height across the changeover so the pelvis never steps
        sp["pos"].z = base + bob - 0.005 * r.k
        lagt = t - 0.045
        arm_w = -math.sin(math.pi * lagt / Ts)                  # +1 at mid right-leg swing ... left arm forward then

        def arms(pts, arm_w=arm_w, var=var):
            res = {}
            for s, sg in SIDES:
                wv = (arm_w if s == "L" else -arm_w) * st["swing"] * var
                a = math.radians(4.0 + 34.0 * wv)   # each arm goes forward with the opposite knee
                S = pts["S_" + s]
                ud = V(sg * 0.10, -math.sin(a), -math.cos(a)).normalized()
                E = S + ud * r.a1[s]
                e = a + math.radians(80.0 + 14.0 * wv)                 # the elbow closes a little on the way up, opens behind the hip
                fd = V(-sg * 0.16, -math.sin(e), -math.cos(e)).normalized()
                res[s] = {"w": E + fd * r.a2[s], "pole": V(sg * 0.25, 1.0, -0.2), "palm": V(-sg, 0.1, 0.1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== squat
def _squat_pose(r, st, u, a, t):
    """u: depth 0 (standing) .. 1 (thighs parallel); a: arms 0 (hanging) .. 1 (reaching forward)."""
    w = r.sh_half * 1.02 * st["stance"]
    toe = 20.0
    feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * toe) for s, sg in SIDES}
    b = breath(t, 4.0, 0.0)
    lean = 40.0 * (u ** 0.8)
    sp = torso_spec(V(0, r.P0.y, 0), pitch=1.0 + lean * 0.80, spine=lean * 0.10, chest=lean * 0.10 - 1.0, head_pitch=2.0 + 9.0 * u, br=b * (1 - 0.6 * u))
    sp["feet"] = feet
    sp["kpole"] = {s: V(sg * math.sin(math.radians(toe)) * 1.15, -math.cos(math.radians(toe)), 0) for s, sg in SIDES}   # knees over toes
    z_top = r.fit_z(sp, 0.992)
    # bottom: shins lean ~33 deg over the toes, hip joints level with the knees
    s_ = "L"
    A = r.ankle(s_, feet[s_])
    sig = math.radians(33.0)
    kz = A.z + r.l2[s_] * math.cos(sig)
    k_fwd = r.l2[s_] * math.sin(sig)
    kx = A.x + k_fwd * math.sin(math.radians(toe))
    ky = A.y - k_fwd * math.cos(math.radians(toe))
    hjx = r.hj[s_].x
    back = math.sqrt(max(r.l1[s_] ** 2 - (kx - hjx) ** 2 - (0.012 * r.k) ** 2, 1e-6))
    hip_y, hip_z = ky + back, kz + 0.012 * r.k
    pel_b = Q(0, 1.0 + 40.0 * 0.80, 0)
    off = pel_b @ r.hj[s_]
    y_b, z_b = hip_y - off.y, hip_z - off.z
    sp["pos"] = V(0, lerp(r.P0.y + 0.004 * r.k, y_b, u ** 0.9), lerp(z_top, z_b, u))

    def arms(pts):
        res = {}
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
def _hinge_pose(r, st, u, t):
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
            res[s] = {"w": S + dirv * reach, "pole": V(sg * 0.6, 0.5 - 0.4 * u, 0.6 * u), "palm": V(-sg * (1 - u) * 0.6, 1.0, 0.3 * u)}
        return res
    sp["arms"] = arms
    return sp


def hinge(r, st):
    hold0, lower, hold1 = 0.35, 2.0 * st["tempo"], 0.40
    n = frames(hold0 + lower + hold1)
    down = [_hinge_pose(r, st, smoother((i / FPS - hold0) / lower), i / FPS) for i in range(n)]
    T0 = (n - 1) / FPS
    rise, top = 1.55 * st["tempo"], 0.5
    m = frames(rise + top)
    up = [_hinge_pose(r, st, 1.0 - smoother((i / FPS) / rise), T0 + i / FPS) for i in range(m)]
    up[-1] = _hinge_pose(r, st, 0.0, 0.0)
    down[0] = _hinge_pose(r, st, 0.0, 0.0)
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
        hipj = V(0, A.y, A.z) + up * (r.leg * 0.996)
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
        lo, hi = 40.0, 92.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if shoulders(mid, d)["S_L"].z > target_z:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    dx = 0.105 * r.k
    top_z = wrist_h + math.sqrt((0.9965 * r.la) ** 2 - dx ** 2 - (0.03 * r.k) ** 2)
    phi_top = solve_phi(top_z, 0.0)
    phi_bot = solve_phi(wrist_h + 0.175 * r.k, 1.0)
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
def _stance_pose(r, st, t, e_jab=0.0, e_cross=0.0, travel=0.0, lead_step=0.0, rear_step=0.0, bob_amp=1.0):
    """Orthodox stance (left foot leads, target straight ahead at -Y).
    e_jab / e_cross: 0 guard .. 1 full extension. travel: forward shift of the whole stance (m).
    lead_step / rear_step: 0..1 bell while that foot is in the air during a push-step."""
    k = r.k
    bob = math.sin(2 * math.pi * t / 0.8)
    b = breath(t, 3.2, 0.4)
    c = e_cross
    # feet: lead toes turned in a little, rear foot ~50 deg out on its ball; the cross pivots the rear foot
    lead = r.foot("L", 0.115 * k * st["stance"], -0.155 * k, -18.0, pitch=0.0)
    rear_yaw = lerp(-52.0, -8.0, c)
    rear_pitch = lerp(13.0, 30.0, c)
    rear = r.foot("R", -0.115 * k * st["stance"], 0.175 * k, -52.0, pitch=0.0)
    rear = (rear[0], rear_yaw, rear_pitch)
    feet = {"L": (lead[0] + V(0, -travel, 0), lead[1], lead[2]), "R": (rear[0] + V(0, -travel, 0), rear[1], rear[2])}
    yaw_p = lerp(-34.0, 6.0, c) - 5.0 * e_jab
    yaw_c = lerp(-42.0, 30.0, c) - 12.0 * e_jab
    pos = V(0.012 * k * c, 0.012 * k - 0.035 * k * e_jab - 0.075 * k * c - travel, 0)
    sp = torso_spec(pos, yaw=yaw_p, pitch=2.0 + 2.0 * c, spine=2.0, chest=4.0, chest_yaw=yaw_c - yaw_p,
                    head_pitch=11.0 + 2.0 * max(e_jab, c), head_yaw=lerp(-4.0, 3.0, c), br=b * 0.5)
    sp["feet"] = feet
    sp["kpole"] = {"L": V(-0.22, -1, 0), "R": V(lerp(-0.75, -0.15, c), -1, 0)}
    z = r.fit_z(sp, 0.992)
    sp["pos"].z = z - (0.034 + 0.005 * bob * bob_amp + 0.012 * c) * k
    sp["shrug"] = {"L": 2.0 + 13.0 * e_jab, "R": 2.0 + 13.0 * c}
    sp["prot"] = {"L": 6.0 + 12.0 * e_jab, "R": 4.0 + 14.0 * c}

    def arms(pts):
        Hc = pts["head"]
        gl = {"w": Hc + V(0.10 * k, -0.25 * k, -0.19 * k), "pole": V(0.30, 0.25, -1), "fingers": V(-0.10, -0.30, 1.0), "palm": V(-1.0, 0.45, 0.0)}
        gr = {"w": Hc + V(-0.09 * k, -0.13 * k, -0.205 * k), "pole": V(-0.30, 0.35, -1), "fingers": V(0.10, -0.25, 1.0), "palm": V(1.0, 0.45, 0.0)}
        res = {"L": gl, "R": gr}
        if e_jab > 0:
            S = pts["S_L"]
            tgt = V(0.03 * k, S.y - math.sqrt(max((0.9965 * r.la) ** 2 - (S.x - 0.03 * k) ** 2 - (0.08 * k) ** 2, 1e-6)), S.z + 0.08 * k)
            ext = {"w": tgt, "pole": V(0.55, 0.1, -0.5), "fingers": V(0, -1, 0), "palm": V(0.12, 0, -1)}
            res["L"] = mix_arm(gl, ext, e_jab)
            res["L"]["w"] = gl["w"].lerp(tgt, e_jab)            # the fist travels the straight line to the target
        if e_cross > 0:
            S = pts["S_R"]
            tgt = V(0.01 * k, S.y - math.sqrt(max((0.9965 * r.la) ** 2 - (S.x - 0.01 * k) ** 2 - (0.08 * k) ** 2, 1e-6)), S.z + 0.08 * k)
            ext = {"w": tgt, "pole": V(-0.55, 0.1, -0.5), "fingers": V(0, -1, 0), "palm": V(-0.12, 0, -1)}
            res["R"] = mix_arm(gr, ext, e_cross)
            res["R"]["w"] = gr["w"].lerp(tgt, e_cross)
        return res
    sp["arms"] = arms
    # push-step: the stepping foot skims the floor
    for s, g in (("L", lead_step), ("R", rear_step)):
        if g > 0:
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, 0, 0.03 * k * g), yaw, pitch + (6.0 * g if s == "R" else -4.0 * g))
    return sp


def _punch_curve(t, start, out, hold, back):
    if t < start:
        return 0.0
    t -= start
    if t < out:
        return smooth(t / out)
    t -= out
    if t < hold:
        return 1.0
    t -= hold
    return 1.0 - smoother(t / back)


def stance(r, st):
    T = 1.6
    n = frames(T)
    return [_stance_pose(r, st, T * i / (n - 1)) for i in range(n)]


def jab(r, st):
    T = 1.6
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_jab=_punch_curve(t, 0.30, 0.20, 0.07, 0.30)))
    return out


def cross(r, st):
    T = 1.6
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        out.append(_stance_pose(r, st, t, e_cross=_punch_curve(t, 0.30, 0.26, 0.07, 0.36)))
    return out


def guard_return(r, st):
    """Slow, deliberate version: the lead hand goes out, pauses, and comes straight back to the cheek along the same line."""
    T = 2.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t < 0.3:
            e = 0.0
        elif t < 0.85:
            e = 0.8 * smoother((t - 0.3) / 0.55)
        elif t < 1.15:
            e = 0.8
        else:
            e = 0.8 * (1.0 - smoother((t - 1.15) / 0.45))
        out.append(_stance_pose(r, st, t, e_jab=e))
    return out


def footwork(r, st):
    """Push-step in, then push-step out: the foot nearest the direction of travel moves first, the other follows,
    and the stance is the same width before and after."""
    step = 0.20 * r.k
    T = 1.6
    n = frames(T)

    def phase(t, forward):
        first = smooth((t - 0.20) / 0.30)                       # first foot in the air 0.20 - 0.50
        second = smooth((t - 0.46) / 0.30)                      # second foot follows 0.46 - 0.76
        body = smoother((t - 0.18) / 0.60)
        g1 = math.sin(math.pi * first)
        g2 = math.sin(math.pi * second)
        return first, second, body, g1, g2
    fwd, back = [], []
    for i in range(n):
        t = T * i / (n - 1)
        first, second, body, g1, g2 = phase(t, True)
        sp = _stance_pose(r, st, t, travel=step * body, lead_step=g1, rear_step=g2, bob_amp=0.0)
        for s, prog in (("L", first), ("R", second)):
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, -step * (prog - body), 0), yaw, pitch)
        fwd.append(sp)
        sp = _stance_pose(r, st, t, travel=step * (1 - body), lead_step=g2, rear_step=g1, bob_amp=0.0)
        for s, prog in (("R", first), ("L", second)):
            ball, yaw, pitch = sp["feet"][s]
            sp["feet"][s] = (ball + V(0, step * (prog - body), 0), yaw, pitch)
        back.append(sp)
    return fwd, back


STYLE = {
    # the two coaches perform the same technique; only build-related details differ
    "coach_f": {"stance": 1.0, "sway": 1.0, "arm_out": 0.085, "tempo": 1.0, "swing": 1.0, "wrist_h": 0.050},
    "coach_m": {"stance": 1.06, "sway": 0.8, "arm_out": 0.105, "tempo": 1.04, "swing": 0.9, "wrist_h": 0.050},
}


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
    print("authored clips:", len(bpy.data.actions), "| worst leg over-reach", round(r.worst_leg, 4), "m, arm", round(r.worst_arm, 4), "m")
    return [a.name for a in bpy.data.actions]
