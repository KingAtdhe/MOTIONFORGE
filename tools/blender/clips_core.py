"""Batch 11 (2026-11-28): core & abs. Hollow hold (tuck), bent-knee leg raise, bicycle crunch, plank leg lift,
glute bridge march, side plank (knees) and side plank. Same rig solver and helpers as authored_clips / clips_fit2.

Lying clips use the crunch's frame: on the back, head toward +Y, face up, feet toward -Y. Every clip starts and
ends in the same pose, so it loops.
"""
import math

from authored_clips import V, Rx, Ry, Rz, SIDES, frames, smooth, smoother, lerp, breath, torso_spec, _phases
from clips_fit2 import _loop, _sides, _segs, _lying_base


# =============================================================================================== shared pieces
def _arms_on_floor(r, k):
    """Arms long beside the body on the floor, palms down (the reverse crunch's arms)."""
    def arms(pts):
        res = {}
        for s, sg in SIDES:
            S = pts["S_" + s]
            wz = 0.097 * k          # (at 0.085 the forearm skin pressed ~1 cm into the floor -- QC, reverse crunch)
            dx = sg * 0.12 * k
            dy = -math.sqrt(max((0.985 * r.la) ** 2 - dx * dx - (S.z - wz) ** 2, 1e-6))
            res[s] = {"w": V(S.x + dx, S.y + dy, wz), "pole": V(sg * 0.4, 0, -1.0), "fingers": V(sg * 0.1, -1, 0), "palm": V(0, 0, -1)}
        return res
    return arms


def _chest_frame(pts):
    side = (pts["S_L"] - pts["S_R"]).normalized()
    up = ((pts["S_L"] + pts["S_R"]) / 2 - pts["hips"]).normalized()
    up = (up - side * up.dot(side)).normalized()
    return side, up, side.cross(up)


def _hands_at_temples(r, k):
    """Fingertips lightly at the temples, elbows wide (no pulling on the neck)."""
    def arms(pts):
        side, up, fwd = _chest_frame(pts)
        Sm = (pts["S_L"] + pts["S_R"]) / 2
        res = {}
        for s, sg in SIDES:
            w = Sm + up * (0.215 * k) + side * (sg * 0.085 * k) + fwd * (0.035 * k)
            res[s] = {"w": w, "pole": side * sg + up * 0.35 - fwd * 0.3, "fingers": up * 0.6 - side * (sg * 0.2) + fwd * 0.5,
                      "palm": -side * sg}
        return res
    return arms


def _leg(r, sp, s, hip_deg, knee_deg):
    """A leg in the air while lying on the back. hip_deg: thigh from vertical, + toward the feet end (legs lower), -
    toward the chest. knee_deg: knee bend, 90 = shin level (tabletop), 0 = straight leg. Returns (foot, kpole)."""
    Hj = sp["pos"] + sp["pel"] @ r.hj[s]
    R = Rx(hip_deg)
    th = (R @ V(0, -0.05, 1.0)).normalized()
    K = Hj + th * r.l1[s] * 0.999
    Rk = Rx(hip_deg + knee_deg)                               # knee 0: in line with the thigh; 90: shin level
    sh = (Rk @ V(0, -0.05, 1.0)).normalized()
    A = K + sh * r.l2[s] * 0.999
    # foot a little pointed from square to the shin (the reverse crunch's tabletop foot)
    toe = (Rx(hip_deg + knee_deg - 71.0) @ V(0, -0.05, 1.0)).normalized()
    return r.foot_toward(s, A, toe), (R @ V(0, 1.0, 1.0)).normalized()


def _lowest_hip(r, sp, s, knee_deg, clearance):
    """How far the thigh can tip toward the feet (hip_deg) before the toes come within `clearance` of the floor."""
    lo, hi = 0.0, 85.0
    for _ in range(30):
        m = (lo + hi) / 2
        f, _ = _leg(r, sp, s, m, knee_deg)
        ball = f[0]
        if ball.z > r.ball0[s].z + clearance:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


# =============================================================================================== hollow hold
def hollow_hold(r, st):
    """Hollow hold, tuck version: lower back pressed into the floor, head and shoulders lifted, legs in tabletop with
    the knees a little in, arms reaching long toward the knees. Breathe and hold."""
    k = r.k
    make, _, _ = _lying_base(r, st)
    T = 4.0
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        b = breath(t, T, 0.0)
        sp = make(extra_spine=11.0, extra_chest=18.0, head=22.0, br=b * 0.3, pel_pitch=-95.0)
        feet, poles = {}, {}
        for s, sg in SIDES:
            feet[s], poles[s] = _leg(r, sp, s, -8.0, 95.0)
        sp["feet"] = feet
        sp["kpole"] = poles

        def arms(pts, feet=feet):
            res = {}
            side, up, fwd = _chest_frame(pts)
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = (-up * 0.15 + fwd * 0.10 + V(0, -1.0, 0)).normalized()    # toward the knees, just above the thighs
                d = (d + side * (sg * 0.05)).normalized()
                res[s] = {"w": S + d * (0.975 * r.la), "pole": V(sg * 0.3, 0, 1.0), "fingers": d, "palm": -side * sg}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== bent-knee leg raise
def leg_raise(r, st):
    """Bent-knee leg raise: on the back, arms on the floor, knees bent; lift both legs from just above the floor up to
    tabletop, then lower slowly without letting the feet touch. The lower back stays down."""
    k = r.k
    make, _, _ = _lying_base(r, st)
    sp0 = make()
    low = _lowest_hip(r, sp0, "L", 95.0, 0.05 * k)

    def f(e, t, T):
        sp = make(br=breath(t, T, 0.0) * 0.3, pel_pitch=-93.0 - 3.0 * e, head=4.0)
        hip = lerp(low, 0.0, e)
        feet, poles = {}, {}
        for s, sg in SIDES:
            feet[s], poles[s] = _leg(r, sp, s, hip, lerp(100.0, 92.0, e))
        sp["feet"] = feet
        sp["kpole"] = poles
        sp["arms"] = _arms_on_floor(r, k)
        return sp
    # starts and ends at the low point (the hover), lifts to tabletop in the middle
    return _loop(r, st, [(0.3, 0, 0), (1.3 * st["tempo"], 0, 1), (0.3, 1, 1), (1.7 * st["tempo"], 1, 0), (0.2, 0, 0)], f)


# =============================================================================================== bicycle crunch
def bicycle_crunch(r, st):
    """Bicycle crunch, slow: head and shoulders lifted, fingertips at the temples, elbows wide. One knee comes in as the
    other leg lengthens low; the opposite shoulder turns toward the bent knee. Then switch. Slow and controlled."""
    k = r.k
    make, _, _ = _lying_base(r, st)
    T1 = 1.6 * st["tempo"]
    T = 4 * T1
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        # x: -1 = right knee in (left shoulder turns to it), +1 = left knee in; one full cycle over T/2, twice
        x = -math.cos(2 * math.pi * t / (2 * T1)) if i < n - 1 else -1.0
        x = math.copysign(abs(x) ** 0.7, x)                      # a short pause at each side
        sp = make(extra_spine=9.0, extra_chest=16.0, head=18.0, br=breath(t, T, 0.0) * 0.3, pel_pitch=-95.0)
        # the chest turns about the body's long axis toward the knee coming in
        tw = 20.0 * x
        sp["che"] = Ry(tw) @ sp["che"]
        sp["spi"] = Ry(0.4 * tw) @ sp["spi"]
        sp["nek"] = Ry(0.6 * tw) @ sp["nek"]
        sp["hed"] = Ry(0.6 * tw) @ sp["hed"]
        feet, poles = {}, {}
        for s, sg in SIDES:
            inn = smooth(0.5 + 0.5 * x * sg)                      # 1 = this knee in, 0 = this leg long
            hip = lerp(60.0, -24.0, inn)                          # long leg low (about 30 deg off the floor)
            kn = lerp(8.0, 105.0, inn)
            feet[s], poles[s] = _leg(r, sp, s, hip, kn)
        sp["feet"] = feet
        sp["kpole"] = poles
        sp["arms"] = _hands_at_temples(r, k)
        out.append(sp)
    return out


# =============================================================================================== plank leg lift
def _forearm_plank(r, st):
    """The forearm plank's geometry (authored_clips.plank_hold): returns (phi, body(phi) -> (feet, pos), elbow_z)."""
    from authored_clips import Q
    k = r.k
    elbow_z = 0.07 * k
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
    return (lo + hi) / 2, body, elbow_z


def _forearm_arms(r, k, elbow_z):
    def arms(pts):
        res = {}
        for s, sg in SIDES:
            S = pts["S_" + s]
            E = V(S.x - sg * 0.01 * k, S.y, elbow_z)
            Wp = E + V(-sg * 0.06 * k, -math.sqrt(max(r.a2[s] ** 2 - (0.06 * k) ** 2, 1e-6)) * 0.995, 0)
            res[s] = {"w": Wp, "pole": V(0, 0.5, -1.0), "fingers": V(-sg * 0.25, -1, 0), "palm": V(0, 0, -1)}
        return res
    return arms


def plank_leg_lift(r, st):
    """Forearm plank leg lift: from a forearm plank, one straight leg lifts a hand's width off the floor (squeeze the
    glute), hips stay level and square, lower it; then the other leg."""
    k = r.k
    phi, body, elbow_z = _forearm_plank(r, st)
    feet0, pos0 = body(phi)

    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0
        sp = torso_spec(pos0 + V(-sg * 0.006 * k * e, 0, 0.003 * k * breath(t, 4.0, 0.0)), pitch=phi, head_pitch=phi - 6.0,
                        br=breath(t, 4.0, 0.0) * 0.3)
        sp["feet"] = dict(feet0)
        sp["kpole"] = {s: V(0, -0.2, -1) for s, s_ in SIDES}
        sp["prot"] = {"L": 6.0, "R": 6.0}
        # the lifted leg rotates up about its hip joint, straight, toes pointing down to the floor
        Hj = sp["pos"] + sp["pel"] @ r.hj[side]
        A0 = r.ankle(side, feet0[side])
        d0 = (A0 - Hj)
        ang = 12.0 * e                                           # about a hand's width at the heel
        d = Rx(ang) @ d0                                         # the feet end rises (+Z)
        A = Hj + d.normalized() * min(d0.length, (r.l1[side] + r.l2[side]) * 0.995)
        ball, yaw, pitch = feet0[side]
        fdir = (Rx(ang) @ (ball - A0)).normalized()
        sp["feet"][side] = r.foot_toward(side, A, fdir)
        sp["arms"] = _forearm_arms(r, k, elbow_z)
        return sp
    return _sides(r, st, [(0.3, 0, 0), (0.9 * st["tempo"], 0, 1), (0.6, 1, 1), (0.9 * st["tempo"], 1, 0), (0.3, 0, 0)], fn)


# =============================================================================================== glute bridge march
def glute_bridge_march(r, st):
    """Glute bridge march: hips up in a bridge (shoulders, hips and knees in a line), arms on the floor; one foot lifts
    a few centimetres with the knee kept bent, sets down, then the other. The hips stay level and high."""
    k = r.k
    S_z, S_y = 0.085 * k, 0.40 * k
    hjL = r.hj["L"]
    l1, l2 = r.l1["L"], r.l2["L"]
    A_z = r.ankle0["L"].z

    def body(alpha):
        sp = torso_spec(V(0, 0, 0), pitch=-90.0 - math.degrees(alpha), head_pitch=-90.0)
        _, pts = r.torso(sp)
        mid = (pts["S_L"] + pts["S_R"]) / 2
        sp["pos"] = V(0, S_y, S_z) - mid
        return sp

    def knee(alpha):
        sp = body(alpha)
        return sp["pos"] + sp["pel"] @ hjL + V(0, -math.cos(alpha), math.sin(alpha)) * l1
    lo, hi = 0.0, math.radians(45.0)
    for _ in range(40):
        m = (lo + hi) / 2
        if knee(m).z - l2 > A_z:
            hi = m
        else:
            lo = m
    a_top = (lo + hi) / 2 * 0.90                                # a little below the full bridge: easier to keep level
    K = knee(a_top / 0.90)
    w = 0.10 * k * st["stance"]
    feet0 = {}
    for s, sg in SIDES:
        f = r.foot(s, sg * w, 0.0, sg * 4.0)
        a0 = r.ankle(s, f)
        feet0[s] = (f[0] + V(0, K.y - a0.y, 0), f[1], f[2])

    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0
        sp = body(a_top)
        sp["pel"] = Ry(sg * 1.5 * e) @ sp["pel"]               # a trace of shift; the hips stay level
        sp["feet"] = dict(feet0)
        ball, yaw, pitch = feet0[side]
        sp["feet"][side] = (ball + V(0, 0.035 * k * e, 0.11 * k * e), yaw, pitch + 22.0 * e)
        sp["kpole"] = {s: V(s_ * 0.12, -0.4, 1.0) for s, s_ in SIDES}
        sp["arms"] = _arms_on_floor(r, k)
        return sp
    return _sides(r, st, [(0.3, 0, 0), (0.6 * st["tempo"], 0, 1), (0.35, 1, 1), (0.6 * st["tempo"], 1, 0), (0.2, 0, 0)], fn)


# =============================================================================================== side planks
def _rotate_spec(sp, W, P, theta):
    """Turns a whole pose (pelvis, spine, head, feet, knee poles) by W about the point P. Feet get the turn as a roll."""
    sp["pos"] = P + W @ (sp["pos"] - P)
    for key in ("pel", "spi", "che", "nek", "hed"):
        sp[key] = W @ sp[key]
    feet = {}
    for s, f in sp["feet"].items():
        roll = (f[3] if len(f) > 3 else 0.0) + theta
        feet[s] = (P + W @ (f[0] - P), f[1], f[2], roll)
    sp["feet"] = feet
    sp["kpole"] = {s: W @ v for s, v in sp.get("kpole", {}).items()}


def _side_plank_pose(r, st, knees, theta, br=0.0):
    """Side plank on the left forearm, body facing the front (-Y). Built standing straight (or, with knees, with the
    knees bent and the shins back), then leaned onto the left side by theta degrees and set down so the left foot's
    edge (or the left knee) rests on the floor. Returns the spec and the world turn."""
    k = r.k
    w = 0.075 * k
    sp = torso_spec(V(0, r.P0.y, 0), pitch=0.0, head_pitch=-2.0, br=br)
    if knees:
        sp["pos"].z = r.P0.z
        feet = {}
        for s, sg in SIDES:
            Hj = sp["pos"] + sp["pel"] @ r.hj[s]
            K = V(Hj.x, Hj.y - 0.02 * k, Hj.z - r.l1[s] * 0.999)
            A = K + V(0, r.l2[s] * 0.97, 0.06 * k)               # shins back, a little up from level
            feet[s] = r.foot_toward(s, A, V(0, 1.0, -0.25))
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.05, -1, 0) for s, sg in SIDES}
    else:
        sp["feet"] = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 3.0) for s, sg in SIDES}
        sp["kpole"] = {s: V(sg * 0.05, -1, 0) for s, sg in SIDES}
        r.fit_z(sp, 0.990)
    W = Ry(theta)
    _rotate_spec(sp, W, V(0, 0, 0), theta)
    # set down: the lowest support (left foot's outer edge, or the left knee) on the floor
    if knees:
        Hj = sp["pos"] + sp["pel"] @ r.hj["L"]
        K = Hj + W @ V(0, -0.02 * k, -r.l1["L"] * 0.999)
        dz = 0.055 * k - K.z
    else:
        dz = 0.045 * k - r.ankle("L", sp["feet"]["L"]).z
    sp["pos"] = sp["pos"] + V(0, 0, dz)
    sp["feet"] = {s: (f[0] + V(0, 0, dz),) + tuple(f[1:]) for s, f in sp["feet"].items()}
    sp["shrug"] = {"L": -4.0, "R": 0.5 * br}
    return sp, W


def _side_plank(r, st, knees):
    k = r.k
    elbow_z = 0.07 * k
    target = elbow_z + r.a1["L"] * 0.99

    def shoulder(theta):
        sp, _ = _side_plank_pose(r, st, knees, theta)
        _, pts = r.torso(sp)
        return pts["S_L"]
    lo, hi = 40.0, 89.0
    for _ in range(40):
        m = (lo + hi) / 2
        if shoulder(m).z > target:
            lo = m
        else:
            hi = m
    theta = (lo + hi) / 2
    T = 4.0
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        b = breath(t, T, 0.0)
        sp, W = _side_plank_pose(r, st, knees, theta, br=b * 0.4)

        def arms(pts, W=W, sp=sp):
            res = {}
            S = pts["S_L"]
            E = V(S.x, S.y, elbow_z)
            res["L"] = {"w": E + V(0.02 * k, -r.a2["L"] * 0.97, 0.0), "pole": V(0.2, 1.0, 0.0), "fingers": V(0.1, -1, 0),
                        "palm": V(0, 0, -1)}
            # the top hand rests on the top hip, elbow pointing back
            Hr = sp["pos"] + sp["pel"] @ r.hj["R"]
            res["R"] = {"w": Hr + W @ V(-0.075 * k, -0.01 * k, 0.09 * k), "pole": W @ V(-0.3, 1.0, 0.1),
                        "fingers": W @ V(0.15, -0.35, -1.0), "palm": W @ V(1.0, 0, 0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def side_plank_knees(r, st):
    """Side plank from the knees: on the left forearm, elbow under the shoulder, knees bent with the shins back; hips
    lifted so the head, hips and knees line up; top hand on the hip. Breathe and hold."""
    return _side_plank(r, st, True)


def side_plank(r, st):
    """Side plank: on the left forearm, elbow under the shoulder, legs straight and stacked; hips lifted into one line
    from head to heels; top hand on the hip. Breathe and hold."""
    return _side_plank(r, st, False)


CLIPS = [
    ("hollow_hold", hollow_hold),
    ("leg_raise", leg_raise),
    ("bicycle_crunch", bicycle_crunch),
    ("plank_leg_lift", plank_leg_lift),
    ("glute_bridge_march", glute_bridge_march),
    ("side_plank_knees", side_plank_knees),
    ("side_plank", side_plank),
]
RETIME = {}
PLANTED = ("plank_leg_lift",)
