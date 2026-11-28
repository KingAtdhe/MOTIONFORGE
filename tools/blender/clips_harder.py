"""Batch 12 (2026-11-28): intermediate moves. Jump squat and close-grip push-up. Same rig solver and helpers as
authored_clips. Both loop on themselves (start and end standing / at the top of the plank)."""
import math

from authored_clips import (V, Q, Rx, SIDES, frames, smooth, smoother, lerp, breath, torso_spec, _squat_pose, _phases,
                            TOP_REACH)


# =============================================================================================== jump squat
def jump_squat(r, st):
    """Jump squat: squat to about parallel with the arms reaching forward, drive up through the whole foot and jump a
    little off the floor, land softly on the balls of the feet into a quarter squat, stand. Three reps."""
    k = r.k
    tp = st["tempo"]
    # u: squat depth, a: arms forward, f: flight (0..1), p: on the balls of the feet (push-off / landing)
    seg = [(0.20, 0.0, 0.0), (0.70 * tp, 0.0, 0.68), (0.12, 0.68, 0.68), (0.22, 0.68, 0.0)]
    T_down = sum(d for d, _, _ in seg)
    T_fly = 0.30
    T_land = 0.26
    T_rise = 0.55 * tp
    T1 = T_down + T_fly + T_land + T_rise
    reps = 3
    T = T1 * reps
    n = frames(T)
    H = 0.09 * k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        tt = t % T1 if i < n - 1 else 0.0
        f = p = 0.0
        if tt < T_down:
            u = _phases(tt, seg)
            a = min(1.0, u / 0.68)
            if tt > T_down - 0.18:                                    # the last of the drive: up onto the balls
                p = smooth((tt - (T_down - 0.18)) / 0.18)
        elif tt < T_down + T_fly:
            q = (tt - T_down) / T_fly
            u, a, f, p = 0.0, lerp(0.6, 0.2, q), math.sin(math.pi * q), 1.0
        elif tt < T_down + T_fly + T_land:
            q = (tt - T_down - T_fly) / T_land
            u = 0.40 * math.sin(0.5 * math.pi * smooth(q))         # absorb: down into a quarter squat
            a = lerp(0.2, 0.55, q)
            p = 1.0 - smooth(q)
        else:
            q = (tt - T_down - T_fly - T_land) / T_rise
            u = 0.40 * (1.0 - smoother(q))
            a = 0.55 * (1.0 - smoother(q))
        sp = _squat_pose(r, st, u, a, t)
        if p > 0.0 or f > 0.0:
            feet = {}
            for s, (ball, yaw, pitch) in sp["feet"].items():
                feet[s] = (ball + V(0, 0, H * f), yaw, pitch + 22.0 * p + 10.0 * f)
            sp["feet"] = feet
            if u < 0.05:
                # standing tall on the balls or in the air: the pelvis rides on the legs
                r.fit_z(sp, 0.985)
            else:
                sp["pos"].z += 0.02 * k * p
        out.append(sp)
    return out


# =============================================================================================== close-grip push-up
def _close_geometry(r, st):
    """The push-up's geometry (authored_clips._pushup_geometry) with the hands under the shoulders, a little inside."""
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
        return feet, hipj - pel @ mid

    def blades(d):
        return 6.0 - 12.0 * d

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
    dx = -0.015 * r.k                                              # hands just inside the shoulders
    top_z = wrist_h + math.sqrt((st.get("top_reach", TOP_REACH) * r.la) ** 2 - dx ** 2 - (0.03 * r.k) ** 2)
    phi_top = solve_phi(top_z, 0.0)
    phi_bot = solve_phi(wrist_h + st.get("bottom_h", 0.175) * r.k * 1.15, 1.0)   # a little less deep than the push-up
    top = shoulders(phi_top, 0.0)
    wrist = {s: V(top["S_" + s].x + sg * dx, top["S_" + s].y + 0.03 * r.k, wrist_h) for s, sg in SIDES}
    return body, phi_top, phi_bot, wrist, blades


def close_grip_pushup(r, st):
    """Close-grip push-up: hands under the shoulders, elbows tucked in close to the ribs and pointing back as you lower
    the chest, body in one line; press back up. Two reps, the lowering slower than the press."""
    geo = _close_geometry(r, st)
    body, phi_top, phi_bot, wrist, blades = geo
    tp = st["tempo"]
    seg = [(0.35, 0, 0), (1.8 * tp, 0, 1), (0.25, 1, 1), (1.2 * tp, 1, 0), (0.35, 0, 0)]

    def pose(d, t):
        phi = lerp(phi_top, phi_bot, d)
        feet, pos = body(phi)
        sp = torso_spec(pos, pitch=phi, head_pitch=phi - 8.0 + 2.0 * d)
        sp["nek"] = Q(0, phi - 3.0, 0)
        sp["feet"] = feet
        sp["kpole"] = {s: V(0, -0.2, -1) for s, sg in SIDES}
        sp["prot"] = {"L": blades(d), "R": blades(d)}
        sp["shrug"] = {"L": -2.0, "R": -2.0}
        # elbows tucked: they point back along the body (toward the feet), not out to the sides
        sp["arms"] = {s: {"w": wrist[s], "pole": V(sg * 0.18, 0.95, 0.10), "fingers": V(0, -1, 0), "palm": V(0, 0, -1)}
                      for s, sg in SIDES}
        return sp
    T1 = sum(d for d, _, _ in seg)
    reps = 2
    n = frames(T1 * reps)
    out = []
    for i in range(n):
        t = T1 * reps * i / (n - 1)
        out.append(pose(_phases(t % T1 if i < n - 1 else 0.0, seg), t))
    return out


CLIPS = [
    ("jump_squat", jump_squat),
    ("close_grip_pushup", close_grip_pushup),
]
RETIME = {}
AIRBORNE = ("jump_squat",)
