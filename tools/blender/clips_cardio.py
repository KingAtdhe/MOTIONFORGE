"""Batch 10 (2026-11-28): cardio & HIIT. Jumping jack, high knees, butt kicks (jog), fast feet, skater hop, plank jack,
mountain climber (quick), speed punches. Same rig solver and helpers as authored_clips / clips_fit2.

These are the first clips with flight (both feet off the floor): the build's floor-contact pass must not pull them
down, so they are listed in AIRBORNE (rigged_coach.floor_contact only lifts feet out of the floor for them, never
pulls a jump down). Every clip starts and ends in the same pose, so it loops.
"""
import math

from authored_clips import (V, SIDES, frames, smooth, smoother, lerp, breath, torso_spec, _stance_pose, _punch_curve,
                            _pushup_geometry, _pushup_pose, mountain_climber_slow)
from clips_fit2 import _dir


def _bell(u, a, b):
    """0 outside [a, b], a smooth sine bump inside."""
    if u <= a or u >= b:
        return 0.0
    return math.sin(math.pi * smooth((u - a) / (b - a)))


def _ramp(u, a, b):
    """0 before a, 1 after b, smootherstep between."""
    return smoother(min(1.0, max(0.0, (u - a) / (b - a))))


# =============================================================================================== jumping jack
def jumping_jack(r, st):
    """Jumping jack: a small jump out to feet wide as both arms sweep overhead, then a jump back in as the arms come
    down. Landings on the balls of the feet with soft knees. Four jacks."""
    k = r.k
    Tj = 1.05 * st["tempo"]
    jacks = 4
    T = Tj * jacks
    n = frames(T)
    w_in, w_out = 0.075 * k, 0.24 * k * st["stance"]
    H = 0.055 * k                                               # foot clearance at the top of each hop
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        u = (t % Tj) / Tj if i < n - 1 else 0.0
        # out: push 0.00-0.08, flight 0.08-0.34, land 0.34-0.46; in: push 0.50-0.58, flight 0.58-0.84, land 0.84-0.96
        fl = _bell(u, 0.08, 0.34) + _bell(u, 0.58, 0.84)
        wide = _ramp(u, 0.08, 0.34) - _ramp(u, 0.58, 0.84)
        land = _bell(u, 0.30, 0.52) + _bell(u, 0.80, 1.02) + _bell(u + 1.0, 0.80, 1.02)
        push = _bell(u, -0.02, 0.10) + _bell(u, 0.46, 0.60)
        arm = _ramp(u, 0.04, 0.44) - _ramp(u, 0.54, 0.94)
        feet = {}
        for s, sg in SIDES:
            x = sg * lerp(w_in, w_out, wide)
            pitch = 14.0 * push + 26.0 * fl + 8.0 * land               # on the balls: push off, toes down in the air
            f = r.foot(s, x, r.ankle0[s].y, sg * lerp(6.0, 14.0, wide), pitch=pitch)
            feet[s] = (f[0] + V(0, 0, H * fl), f[1], f[2])
        b = breath(t, T, 0.0)
        sp = torso_spec(V(0, r.P0.y + 0.004 * k, 0), pitch=2.0 + 4.0 * land, spine=0.5, chest=-1.0 - 2.0 * arm,
                        head_pitch=1.0 + 2.0 * land, br=b * 0.4)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * lerp(0.12, 0.30, wide), -1, 0) for s, sg in SIDES}
        r.fit_z(sp, 0.978 - 0.05 * land)                            # knees soften to take each landing

        def arms(pts, e=arm):
            res = {}
            a = math.radians(lerp(10.0, 160.0, e))
            for s, sg in SIDES:
                S = pts["S_" + s]
                d = V(sg * math.sin(a), -0.10 - 0.06 * e, -math.cos(a)).normalized()
                palm = V(-sg * (1.0 - e), -e, 0.15).normalized()
                res[s] = {"w": S + d * (0.975 * r.la), "pole": V(0, 1.0, -0.2), "fingers": d, "palm": palm}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== jogging family
def _jog(r, st, step_s, kind, steps=8):
    """Jogging on the spot, on the balls of the feet, one foot landing as the other leaves.
    kind: "knees" (thigh up to about level), "kicks" (heel up behind toward the seat), "feet" (quick small steps in a
    low, wide ready stance)."""
    k = r.k
    Ts = step_s * st["tempo"]
    T = Ts * steps
    n = frames(T)
    feet_mode = kind == "feet"
    w = (0.16 if feet_mode else 0.092) * k * (st["stance"] if feet_mode else 1.0)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        step = int(t / Ts) % steps if i < n - 1 else 0
        u = (t / Ts) % 1.0 if i < n - 1 else 0.0
        up = "L" if step % 2 == 0 else "R"
        stand = "R" if up == "L" else "L"
        sgu = 1.0 if up == "L" else -1.0
        g = math.sin(math.pi * smooth(min(1.0, max(0.0, (u - 0.02) / 0.94))))
        home = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * (10.0 if feet_mode else 6.0)) for s, sg in SIDES}
        sw = -sgu * math.sin(math.pi * u)
        lean = 14.0 if feet_mode else 5.0
        b = breath(t, T / 2, 0.3)
        sp = torso_spec(V(0.016 * k * sw, r.P0.y + (0.03 if feet_mode else 0.008) * k, 0), roll=1.5 * sw, yaw=2.0 * sw,
                        pitch=lean, spine=1.0 + 0.4 * lean, chest_yaw=-5.0 * sw, head_pitch=lean * 0.6, br=b * 0.6)
        # the standing foot stays on its ball and rises a little more as it pushes (the light bounce of a jog)
        feet = {}
        for s, sg in SIDES:
            f = home[s]
            feet[s] = (f[0], f[1], (12.0 if feet_mode else 16.0) + (8.0 if feet_mode else 14.0) * math.sin(math.pi * u))
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
        ext = 0.90 if feet_mode else 0.982
        z_both = r.fit_z(sp, ext)
        z_st = r.fit_z(sp, ext, sides=(stand,))
        sp["pos"].z = lerp(z_both, z_st, math.sin(math.pi * u)) - 0.004 * k
        if kind == "knees":
            lift, fwd = 0.40 * k, 0.20 * k
            f = r.foot(up, sgu * w, r.ankle0[up].y, sgu * 6.0, pitch=16.0 + 22.0 * g)
            feet[up] = (f[0] + V(0, -fwd * g * g, lift * g), f[1], f[2])
        elif kind == "feet":
            f = r.foot(up, sgu * w, r.ankle0[up].y, sgu * 10.0, pitch=20.0 + 10.0 * g)
            feet[up] = (f[0] + V(0, -0.015 * k * g, 0.07 * k * g), f[1], f[2])
        else:   # kicks: the thigh stays near vertical, the heel swings up behind (butt_kicks geometry, quicker)
            Hj = r.hip_joint(sp, up)
            K = Hj + _dir(10.0 * g) * r.l1[up] * 0.999
            A = K + _dir(10.0 * g - 118.0 * g) * r.l2[up] * 0.999
            A0 = r.ankle(up, home[up])
            A_0 = Hj + _dir(0.0) * (r.l1[up] + r.l2[up]) * 0.999
            A = A + (A0 - A_0) * (1.0 - smooth(g))
            # the blend toward home can pass farther from the hip than the leg reaches; keep it inside so the knee
            # never snaps straight (that read as a 2 cm over-reach and a jerk spike at the knee)
            d = A - Hj
            reach = (r.l1[up] + r.l2[up]) * 0.985
            if d.length > reach:
                A = Hj + d.normalized() * reach
            bl =smooth(min(1.0, g / 0.6))
            f0 = (r.foot_q(up, home[up][1], 16.0) @ r.fv[up]).normalized()
            feet[up] = r.foot_toward(up, A, f0.lerp(_dir(10.0 * g - 118.0 * g + 90.0 + 30.0 * g), bl), yaw=home[up][1])
        sp["kpole"][up] = V(sgu * 0.05, -1, 0)
        aw = -math.sin(math.pi * (t - 0.03) / Ts)
        amp = {"knees": 0.95, "kicks": 0.8, "feet": 0.45}[kind]

        def arms(pts, aw=aw, amp=amp):
            res = {}
            for s, sg in SIDES:
                wv = (aw if s == "L" else -aw) * amp
                a = math.radians((20.0 if feet_mode else 8.0) + 34.0 * wv)
                S = pts["S_" + s]
                E = S + V(sg * 0.12, -math.sin(a), -math.cos(a)).normalized() * r.a1[s]
                ee = a + math.radians(88.0 + 8.0 * wv)                  # elbows near 90 degrees, a running arm
                res[s] = {"w": E + V(-sg * 0.14, -math.sin(ee), -math.cos(ee)).normalized() * r.a2[s],
                          "pole": V(sg * 0.25, 1.0, -0.2), "palm": V(-sg, 0.1, 0.1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def high_knees(r, st):
    """High knees: a light jog on the spot, each thigh driving up to about hip height, arms pumping."""
    return _jog(r, st, 0.44, "knees")


def butt_kick_jog(r, st):
    """Butt kicks (jog): a light jog on the spot, each heel flicking up behind toward the seat."""
    return _jog(r, st, 0.40, "kicks")


def fast_feet(r, st):
    """Fast feet: a low, wide ready stance, chest forward, quick small steps on the balls of the feet."""
    return _jog(r, st, 0.24, "feet", steps=12)


# =============================================================================================== skater hop
def skater_hop(r, st):
    """Skater hop: a sideways bound from one foot to the other, landing softly on a bent knee with the chest a little
    forward; the free foot swings behind without touching. Arms swing across."""
    k = r.k
    X = 0.25 * k
    Ts = 1.25 * st["tempo"]
    T = 2 * Ts
    n = frames(T)
    out = []

    def hold(side_plant):
        sgp = 1.0 if side_plant == "L" else -1.0
        other = "R" if side_plant == "L" else "L"
        xc = sgp * X
        plant = r.foot(side_plant, xc + sgp * 0.06 * k, r.ankle0[side_plant].y, sgp * 8.0)
        # the free foot hangs behind and across, a few centimetres off the floor
        free = r.foot(other, xc + sgp * 0.02 * k, r.ankle0[other].y + 0.28 * k, -sgp * 6.0, pitch=48.0)
        free = (free[0] + V(0, 0, 0.05 * k), free[1], free[2])
        return {side_plant: plant, other: free}
    Hd = {"L": hold("L"), "R": hold("R")}
    for i in range(n):
        t = T * i / (n - 1)
        half = 0 if t < Ts else 1
        u = (t - half * Ts) / Ts if i < n - 1 else 1.0
        src, dst = ("L", "R") if half == 0 else ("R", "L")
        ab = _ramp(u, 0.12, 0.52)                                   # the body travels over
        fl = _bell(u, 0.18, 0.50)                                   # both feet off the floor
        feet = {}
        for s_ in (src, dst):
            f0, f1 = Hd[src][s_], Hd[dst][s_]
            prog = _ramp(u, 0.14, 0.50) if s_ == dst else _ramp(u, 0.16, 0.62)
            hgt = 0.07 * k * fl if s_ == dst else 0.05 * k * math.sin(math.pi * prog)
            ball = f0[0].lerp(f1[0], prog) + V(0, 0, hgt)
            pitch = lerp(f0[2], f1[2], prog) + 18.0 * fl
            feet[s_] = (ball, lerp(f0[1], f1[1], prog), pitch)
        x_c = lerp(X if src == "L" else -X, X if dst == "L" else -X, ab)
        dip = 1.0 - 0.85 * math.sin(math.pi * ab)                   # low on the landing leg, tall in the air
        b = breath(t, T, 0.0)
        sp = torso_spec(V(x_c, r.P0.y + 0.045 * k * dip, 0), pitch=5.0 + 16.0 * dip, spine=2.0, chest=2.0, head_pitch=4.0 + 11.0 * dip,
                        roll=-3.0 * x_c / X, br=b * 0.5)
        sp["feet"] = feet
        sp["kpole"] = {s_: V(sg * 0.2, -1, 0) for s_, sg in SIDES}
        z_src = r.fit_z(sp, 0.990, sides=(src,))
        z_dst = r.fit_z(sp, 0.990, sides=(dst,))
        sp["pos"].z = lerp(z_src, z_dst, ab) - 0.085 * k * dip
        sw = x_c / X

        def arms(pts, sw=sw):
            res = {}
            for s_, sg in SIDES:
                S = pts["S_" + s_]
                fw = -sg * sw
                a_ = math.radians(12.0 + 36.0 * fw)
                d = V(sg * 0.12 - 0.16 * sw * max(fw, 0.0) * sg * sg, -math.sin(a_), -math.cos(a_)).normalized()
                res[s_] = {"w": S + d * (0.95 * r.la), "pole": V(sg * 0.3, 1.0, 0.0), "palm": V(-sg, 0.1, 0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== plank jack
def plank_jack(r, st):
    """Plank jack: from a high plank, a small jump of both feet out wide and back together, hands planted, hips level."""
    k = r.k
    st2 = dict(st)
    st2["top_reach"] = min(0.965, st.get("top_reach", 0.968))
    geo = _pushup_geometry(r, st2)
    Tj = 1.0 * st["tempo"]
    jacks = 4
    T = Tj * jacks
    n = frames(T)
    W = 0.13 * k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        u = (t % Tj) / Tj if i < n - 1 else 0.0
        fl = _bell(u, 0.06, 0.40) + _bell(u, 0.56, 0.90)
        wide = _ramp(u, 0.06, 0.40) - _ramp(u, 0.56, 0.90)
        sp = _pushup_pose(r, st2, geo, 0.0, t)
        feet = {}
        for s, (ball, yaw, pitch) in sp["feet"].items():
            sg = 1.0 if s == "L" else -1.0
            feet[s] = (ball + V(sg * W * wide, 0, 0.035 * k * fl), yaw + sg * 6.0 * wide, pitch)
        sp["feet"] = feet
        sp["pos"] = sp["pos"] + V(0, 0, 0.018 * k * fl)               # the hips lift a little with each hop
        out.append(sp)
    return out


# =============================================================================================== mountain climber (quick)
def mountain_climber(r, st):
    """Mountain climber at running pace: the slow climber's positions, played much quicker (RETIME below)."""
    return mountain_climber_slow(r, st)


# =============================================================================================== speed punches
def speed_punches(r, st):
    """Speed punches: quick, relaxed jab-cross pairs from the stance, each hand back to the guard before the next;
    light bounce. Four pairs."""
    pair = 0.62
    T = 4 * pair + 0.3
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        ej = ec = 0.0
        hj = hc = 0.0
        for p in range(4):
            s0 = 0.15 + p * pair
            ej = max(ej, _punch_curve(t, s0, 0.20, 0.02, 0.22))
            ec = max(ec, _punch_curve(t, s0 + pair / 2, 0.21, 0.02, 0.23))
            hj = max(hj, _punch_curve(t + 0.04, s0, 0.20, 0.02, 0.22))
            hc = max(hc, _punch_curve(t + 0.06, s0 + pair / 2, 0.21, 0.02, 0.23))
        out.append(_stance_pose(r, st, t, e_jab=ej, e_cross=ec, loop=T, bounce=0.6, hip={"e_jab": hj, "e_cross": hc}))
    return out


CLIPS = (
    ("jumping_jack", jumping_jack), ("high_knees", high_knees), ("butt_kick_jog", butt_kick_jog), ("fast_feet", fast_feet),
    ("skater_hop", skater_hop), ("plank_jack", plank_jack), ("mountain_climber", mountain_climber),
    ("boxing_speed_punches", speed_punches),
)
# rhythm drills keep their tempo; the quick climber plays the slow one's poses about twice as fast
RETIME = {n: (1.0, 1.0) for n in ("jumping_jack", "high_knees", "butt_kick_jog", "fast_feet", "skater_hop", "plank_jack",
                                  "boxing_speed_punches")}
RETIME["mountain_climber"] = (3.2, 2.1)
# flight: the build only lifts feet out of the floor for these, it never pulls a jump down
AIRBORNE = {"jumping_jack", "high_knees", "butt_kick_jog", "fast_feet", "skater_hop", "plank_jack"}
PLANTED = ("plank_jack", "mountain_climber")
