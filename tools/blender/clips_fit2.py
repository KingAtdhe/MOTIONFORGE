"""Batch 7, fitness (2026-11-24): 30 more beginner lessons, authored with the same rig solver and helpers as
authored_clips (feet as IK targets, pelvis height from the legs, soft knees and elbows, life layer added on write).
Every clip loops on itself or starts and ends in the same position.
"""
import math

import authored_clips as ac
from authored_clips import (V, Q, Rx, Ry, Rz, SIDES, FPS, frames, smooth, smoother, lerp, breath, torso_spec, hang, mix_arm,
                            _phases, _rep_segments, _stand, _effort, _squat_pose, _hinge_pose, _pushup_geometry, _pushup_pose,
                            _quadruped_base, _hands_on_floor)


def _loop(r, st, segs, fn):
    T = sum(d for d, _, _ in segs)
    n = frames(T)
    return [fn(_phases(T * i / (n - 1), segs), T * i / (n - 1), T) for i in range(n)]


def _sides(r, st, segs, fn, order=("R", "L")):
    """One rep per side: `fn(side, e, t)`; the second side's first frame is dropped (it equals the first side's last)."""
    T1 = sum(d for d, _, _ in segs)
    n = frames(T1)
    out = []
    for j, side in enumerate(order):
        for i in range(n):
            if j and i == 0:
                continue
            t = T1 * i / (n - 1)
            out.append(fn(side, _phases(t, segs), t + j * T1))
    return out


def _segs(st, hold0=0.4, go=1.3, hold=0.4, back=1.2, rest=0.3):
    tp = st["tempo"]
    return [(hold0, 0, 0), (go * tp, 0, 1), (hold, 1, 1), (back * tp, 1, 0), (rest, 0, 0)]


def _chest_cross(r, k):
    """Arms folded across the chest, each hand on the opposite shoulder."""
    def arms(pts):
        # offsets in the chest's own frame, so the fold is the same standing, hinged or lying on the back (QC: with
        # world offsets the folded arms sank 12 cm into the floor in the crunch)
        side = (pts["S_L"] - pts["S_R"]).normalized()
        up = ((pts["S_L"] + pts["S_R"]) / 2 - pts["hips"]).normalized()
        up = (up - side * up.dot(side)).normalized()
        fwd = side.cross(up)
        res = {}
        for s, sg in SIDES:
            O = pts["S_" + ("R" if s == "L" else "L")]
            res[s] = {"w": O + side * (sg * 0.02 * k) + fwd * (0.115 * k) - up * (0.075 * k),
                      "pole": side * (sg * 0.25) + fwd * 0.7 - up, "fingers": side * (-sg) - fwd * 0.1 + up * 0.25, "palm": -fwd}
        return res
    return arms


def _dir(a):
    """Unit vector in the side (Y-Z) plane, `a` degrees from straight down toward the front (-Y)."""
    a = math.radians(a)
    return V(0, -math.sin(a), -math.cos(a))


# =============================================================================================== standing, no equipment
def good_morning(r, st):
    """Bodyweight good morning: arms folded on the chest, soft knees, the hips go back and the flat back tips forward
    to about 45 degrees, then the hips drive forward to stand tall."""
    k = r.k

    def f(e, t, T):
        sp = _hinge_pose(r, st, 0.70 * e, t)
        sp["arms"] = _chest_cross(r, k)
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.8, 0.3, 1.5, 0.4), f)


def _one_leg(r, st, t, side, g, ws, leg, pitch=1.0, roll=0.0, arms="out", spine=0.5, chest=-1.0, head=1.0):
    """Standing on one leg. side = the moving leg; g = 0..1 how far it moves (0: foot planted at home); ws = 0..1 the
    weight shift onto the standing leg; leg(Hj) -> (ankle, ankle->ball direction) for the moving foot at g."""
    k = r.k
    w = 0.095 * k * st["stance"]
    stand = "L" if side == "R" else "R"
    sg_st = 1.0 if stand == "L" else -1.0
    home = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0) for s, sg in SIDES}
    b = breath(t, 4.0, 0.0)
    sp = torso_spec(V(sg_st * 0.045 * k * smooth(ws), r.P0.y + 0.004 * k, 0), pitch=pitch, roll=sg_st * 1.5 * ws + roll,
                    spine=spine, chest=chest, head_pitch=head, br=b * 0.5)
    sp["feet"] = dict(home)
    sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
    z_both = r.fit_z(sp, 0.992)
    z_one = r.fit_z(sp, 0.992, sides=(stand,))
    sp["pos"].z = lerp(z_both, z_one, smooth(ws))
    if g > 0:
        Hj = r.hip_joint(sp, side)
        A, d = leg(Hj)
        A0 = r.ankle(side, home[side])
        bl = smooth(g / 0.18)                                  # leaves exactly from the planted foot
        A = A0.lerp(A, bl)
        f0 = (r.foot_q(side, home[side][1], 0.0) @ r.fv[side]).normalized()
        sp["feet"][side] = r.foot_toward(side, A, f0.lerp(d, bl), yaw=home[side][1])
    if arms == "out":
        sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=0.16 + 0.06 * ws, fwd=0.05, reach=0.985) for s, sg in SIDES}
    elif callable(arms):
        sp["arms"] = arms
    return sp


def single_leg_balance(r, st):
    """Weight onto one leg, the other knee lifts to about hip-flexion 70 degrees, foot relaxed; hold, lower; other side."""
    k = r.k
    segs = [(0.3, 0, 0), (0.6, 0, 1), (1.2, 1, 1), (0.6, 1, 0), (0.3, 0, 0)]       # weight shift around the lift

    def fn(side, e, t):
        g = smooth((e - 0.25) / 0.75) if e > 0.25 else 0.0
        ws = smooth(min(1.0, e / 0.35))

        def leg(Hj, g=g):
            K = Hj + _dir(70.0 * g) * r.l1[side] * 0.999
            A = K + _dir(-4.0) * r.l2[side] * 0.999
            return A, _dir(70.0)
        sp = _one_leg(r, st, t, side, g, ws, leg)
        sg = 1.0 if side == "L" else -1.0
        sp["kpole"][side] = V(sg * 0.10, -1, 0.3 * g)
        return sp
    return _sides(r, st, [(0.3, 0, 0), (1.0, 0, 1), (1.4, 1, 1), (0.9, 1, 0), (0.3, 0, 0)], fn)


def single_leg_rdl(r, st):
    """Single-leg Romanian deadlift (bodyweight): standing knee soft, the body tips forward from the hip as the free leg
    reaches back in line with it, arms hang toward the floor; back up; other side."""
    k = r.k
    w = 0.095 * k * st["stance"]

    def fn(side, e, t):
        stand = "L" if side == "R" else "R"
        sgs = 1.0 if stand == "L" else -1.0
        u = e
        lean = 62.0 * u
        feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0) for s, sg in SIDES}
        b = breath(t, 4.0, 0.0)
        ws = smooth(min(1.0, e / 0.2)) if e > 0 else 0.0
        sp = torso_spec(V(sgs * 0.05 * k * ws, r.P0.y + 0.004 * k + 0.07 * k * u, 0), pitch=1.0 + lean, spine=0.5, chest=-1.0,
                        head_pitch=1.0 + lean * 0.85, br=b * 0.4)
        sp["feet"] = feet
        sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
        z_both = r.fit_z(sp, 0.992)
        z_one = r.fit_z(sp, 0.985, sides=(stand,))
        sp["pos"].z = lerp(z_both, z_one, ws)
        if e > 0:
            Hj = r.hip_joint(sp, side)
            up = Rx(1.0 + lean) @ V(0, 0, 1)
            A_back = Hj - up * (0.975 * r.leg)
            A0 = r.ankle(side, feet[side])
            bl = smooth(e / 0.25)
            A = A0.lerp(A_back, bl) + V(0, 0, 0.03 * k * math.sin(math.pi * min(1.0, e / 0.25)))
            f0 = (r.foot_q(side, feet[side][1], 0.0) @ r.fv[side]).normalized()
            down = (Rx(1.0 + lean) @ V(0, -1.0, 0)).normalized()    # the toes point to the floor, foot square
            sp["feet"][side] = r.foot_toward(side, A, f0.lerp(down, bl), yaw=feet[side][1])
            sg = 1.0 if side == "L" else -1.0
            sp["kpole"][side] = V(sg * 0.05, -1, 0).lerp(down, bl)       # kneecap toward the floor (not along the leg)

        def arms(pts, u=u):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                hangw = hang(r, pts, s, sg, out=0.08, fwd=0.02, reach=0.985)
                down = {"w": S + V(sg * 0.02 * k, -0.04 * k, -0.985 * r.la), "pole": V(sg * 0.3, 1.0, 0.2), "palm": V(-sg, 0.2, 0)}
                res[s] = mix_arm(hangw, down, smooth(u))
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, [(0.4, 0, 0), (1.6, 0, 1), (0.4, 1, 1), (1.4, 1, 0), (0.3, 0, 0)], fn)


def side_leg_raise(r, st):
    """Standing side leg raise: tall posture, the straight leg lifts out to the side about 35 degrees, toes forward,
    and lowers with control; other side."""
    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0
        g = e
        ws = smooth(min(1.0, e / 0.25))

        def leg(Hj, g=g):
            a = math.radians(35.0 * smooth(g))
            A = Hj + V(sg * math.sin(a), -0.02, -math.cos(a)) * (0.985 * r.leg)
            return A, V(0, -1.0, -0.1)
        sp = _one_leg(r, st, t, side, g, ws, leg, roll=-sg * 4.0 * g)
        sp["kpole"][side] = V(sg * 0.05, -1, 0)
        return sp
    return _sides(r, st, _segs(st, 0.35, 1.1, 0.3, 1.2, 0.3), fn)


def glute_kickback(r, st):
    """Standing glute kickback: a small lean forward, the straight leg sweeps back about 25 degrees from the hip without
    arching the lower back, and returns; other side."""
    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0
        ws = smooth(min(1.0, e / 0.25))

        def leg(Hj, g=e):
            A = Hj + _dir(-32.0 * smooth(g)) * (0.96 * r.leg)        # (degrees: _dir converts)
            return A, V(0, 0.15, -1.0).normalized()
        sp = _one_leg(r, st, t, side, e, ws, leg, pitch=1.0 + 13.0 * ws)
        sp["kpole"][side] = V(sg * 0.05, -1, 0)
        return sp
    return _sides(r, st, _segs(st, 0.35, 1.0, 0.3, 1.1, 0.3), fn)


def butt_kicks(r, st):
    """Low-impact butt kicks: walking on the spot, each heel lifts behind toward the seat, thigh stays near vertical,
    arms swing bent."""
    k = r.k
    Ts = 0.95 * st["tempo"]
    steps = 4
    T = Ts * steps
    n = frames(T)
    w = 0.092 * k
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        step = int(t / Ts) % steps
        u = (t / Ts) % 1.0 if i < n - 1 else 0.0
        up = "L" if step % 2 == 0 else "R"
        g = math.sin(math.pi * smoother((u - 0.08) / 0.84))
        stand = "R" if up == "L" else "L"
        sgu = 1.0 if up == "L" else -1.0
        sw = -sgu * math.sin(math.pi * u)
        b = breath(t, T / 2, 0.3)
        home = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0) for s, sg in SIDES}
        sp = torso_spec(V(0.024 * k * sw, r.P0.y + 0.006 * k, 0), roll=2.0 * sw, pitch=4.0, spine=1.0, head_pitch=1.5, br=b * 0.6)
        sp["feet"] = dict(home)
        sp["kpole"] = {s: V(sg * 0.10, -1, 0) for s, sg in SIDES}
        z_both = r.fit_z(sp, 0.994)
        z_st = r.fit_z(sp, 0.994, sides=(stand,))
        sp["pos"].z = lerp(z_both, z_st, 0.5 + 0.5 * math.sin(math.pi * u)) - 0.004 * k
        if g > 0:
            Hj = r.hip_joint(sp, up)
            K = Hj + _dir(14.0 * g) * r.l1[up] * 0.999
            A = K + _dir(14.0 * g - 112.0 * g) * r.l2[up] * 0.999
            A0 = r.ankle(up, home[up])
            bl = smooth(g / 0.12)
            A = A0.lerp(A, bl)
            f0 = (r.foot_q(up, home[up][1], 0.0) @ r.fv[up]).normalized()
            sp["feet"][up] = r.foot_toward(up, A, f0.lerp(_dir(14.0 * g - 112.0 * g + 90.0 + 30.0 * g), bl), yaw=home[up][1])
            sp["kpole"][up] = V(sgu * 0.05, -1, 0)
        aw = -math.sin(math.pi * (t - 0.04) / Ts)

        def arms(pts, aw=aw):
            res = {}
            for s, sg in SIDES:
                wv = (aw if s == "L" else -aw) * 0.8
                a = math.radians(8.0 + 30.0 * wv)
                S = pts["S_" + s]
                E = S + V(sg * 0.10, -math.sin(a), -math.cos(a)).normalized() * r.a1[s]
                ee = a + math.radians(85.0)
                res[s] = {"w": E + V(-sg * 0.12, -math.sin(ee), -math.cos(ee)).normalized() * r.a2[s], "pole": V(sg * 0.25, 1.0, -0.2),
                          "palm": V(-sg, 0.1, 0.1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def torso_twist(r, st):
    """Standing torso twist: feet hip-width, arms bent in front of the chest, the chest turns left and right about 35
    degrees while the hips stay mostly square."""
    k = r.k
    T = 4.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        x = _phases(t, [(0.3, 0, 0), (0.8, 0, 1), (0.25, 1, 1), (1.6, 1, -1), (0.25, -1, -1), (0.9, -1, 0), (0.3, 0, 0)])
        sp = _stand(r, st, t, w=0.11, T=T)
        sp["pel"] = Rz(6.0 * x) @ sp["pel"]
        sp["spi"] = Rz(16.0 * x) @ sp["spi"]
        sp["che"] = Rz(33.0 * x) @ sp["che"]
        sp["nek"] = Rz(30.0 * x) @ sp["nek"]
        sp["hed"] = Rz(26.0 * x) @ sp["hed"]
        r.fit_z(sp, 0.990)

        def arms(pts):
            res = {}
            c = (pts["S_L"] + pts["S_R"]) / 2
            fwd = (pts["S_L"] - pts["S_R"]).cross(V(0, 0, 1)).normalized()        # chest forward
            side = (pts["S_L"] - pts["S_R"]).normalized()
            for s, sg in SIDES:
                res[s] = {"w": c + fwd * (0.26 * k) + side * (sg * 0.05 * k) + V(0, 0, -0.07 * k), "pole": side * sg + V(0, 0, -0.3),
                          "fingers": -side * sg, "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def side_bend(r, st):
    """Standing side bend: one arm reaches up and over, the body bends sideways about 20 degrees, the other hand slides
    down the outside of the thigh; back up; other side."""
    k = r.k

    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0                       # bend toward `side`
        T = 4.0
        sp = _stand(r, st, t, w=0.12, T=T)
        a = 22.0 * e
        sp["pel"] = Ry(sg * 2.0 * e) @ sp["pel"]
        sp["spi"] = Ry(sg * 0.45 * a) @ sp["spi"]
        sp["che"] = Ry(sg * a) @ sp["che"]
        sp["nek"] = Ry(sg * a * 1.05) @ sp["nek"]
        sp["hed"] = Ry(sg * a * 0.9) @ sp["hed"]
        sp["pos"] = sp["pos"] + V(-sg * 0.015 * k * e, 0, 0)
        r.fit_z(sp, 0.990)
        up_side = "R" if side == "L" else "L"

        def arms(pts, e=e):
            res = {}
            for s, s2 in SIDES:
                S = pts["S_" + s]
                h = hang(r, pts, s, s2, out=0.06, fwd=0.01, reach=0.985)
                if s == up_side:
                    ad = lerp(10.0, 165.0, e)          # over the whole lift (QC: over 60 % of it the hand flew at 8 m/s)
                    ra = math.radians(ad)
                    rot = Ry(sg * 22.0 * e)
                    d = (rot @ V(s2 * math.sin(ra), -0.08, -math.cos(ra))).normalized()
                    # the palm turns from facing the thigh, through facing down, to facing forward overhead -- a quarter
                    # turn about the arm (QC: a fixed palm vector ran parallel to the fingers overhead and the hand flipped)
                    p0 = V(-s2 * math.cos(ra), 0.0, -math.sin(ra))
                    pal = (rot @ p0.lerp(V(0, -1.0, 0), smooth((ad - 60.0) / 105.0))).normalized()
                    over = {"w": S + d * (0.975 * r.la), "pole": V(s2 * 0.2, 1.0, 0.3), "fingers": d, "palm": pal}
                    res[s] = mix_arm(h, over, smooth(min(1.0, e / 0.25)))
                else:
                    res[s] = hang(r, pts, s, s2, out=0.07, fwd=0.0, reach=0.985)
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _segs(st, 0.35, 1.8, 0.6, 1.6, 0.3), fn, order=("L", "R"))


def skater_step(r, st):
    """Low-impact skater: a wide side step onto one leg with the knee bent and the chest a little forward, the other
    foot sweeps behind and touches lightly with the toes, arms swing; then to the other side. Always one foot down."""
    k = r.k
    X = 0.22 * k
    Ts = 1.6 * st["tempo"]
    T = 2 * Ts
    n = frames(T)
    out = []

    def hold(side_plant):
        sgp = 1.0 if side_plant == "L" else -1.0
        other = "R" if side_plant == "L" else "L"
        xc = sgp * X
        plant = r.foot(side_plant, xc + sgp * 0.06 * k, r.ankle0[side_plant].y, sgp * 8.0)
        tap = r.foot(other, xc + sgp * 0.01 * k, r.ankle0[other].y + 0.30 * k, -sgp * 6.0, pitch=45.0)
        return {side_plant: plant, other: tap}
    H = {"L": hold("L"), "R": hold("R")}
    for i in range(n):
        t = T * i / (n - 1)
        half = 0 if t < Ts else 1
        u = (t - half * Ts) / Ts if i < n - 1 else 1.0
        src, dst = ("L", "R") if half == 0 else ("R", "L")
        a1 = smoother((u - 0.08) / 0.42)                          # the tapping foot steps out wide and lands
        a2 = smoother((u - 0.45) / 0.40)                          # then the old standing foot sweeps behind
        ab = smoother((u - 0.10) / 0.60)                          # the body travels over
        feet = {}
        for s_, prog, hgt in ((dst, a1, 0.06), (src, a2, 0.05)):
            f0, f1 = H[src][s_], H[dst][s_]
            ball = f0[0].lerp(f1[0], prog) + V(0, 0, hgt * k * math.sin(math.pi * prog))
            pitch = lerp(f0[2], f1[2], prog) + 12.0 * math.sin(math.pi * prog)
            feet[s_] = (ball, lerp(f0[1], f1[1], prog), pitch)
        x_c = lerp(X if src == "L" else -X, X if dst == "L" else -X, ab)
        dip = 1.0 - 0.75 * math.sin(math.pi * ab)                # low on the standing leg, taller in the transfer
        b = breath(t, T, 0.0)
        sp = torso_spec(V(x_c, r.P0.y + 0.04 * k * dip, 0), pitch=4.0 + 14.0 * dip, spine=2.0, chest=2.0, head_pitch=4.0 + 10.0 * dip,
                        roll=-2.0 * x_c / X, br=b * 0.5)
        sp["feet"] = feet
        sp["kpole"] = {s_: V(sg * 0.2, -1, 0) for s_, sg in SIDES}
        z_src = r.fit_z(sp, 0.992, sides=(src,))
        z_dst = r.fit_z(sp, 0.992, sides=(dst,))
        sp["pos"].z = lerp(z_src, z_dst, ab) - 0.075 * k * dip
        sw = x_c / X

        def arms(pts, sw=sw):
            res = {}
            for s_, sg in SIDES:
                S = pts["S_" + s_]
                fw = -sg * sw                                      # the arm away from the standing leg swings forward
                a_ = math.radians(10.0 + 30.0 * fw)
                d = V(sg * 0.12 + 0.14 * sw * max(fw, 0.0), -math.sin(a_), -math.cos(a_)).normalized()
                res[s_] = {"w": S + d * (0.95 * r.la), "pole": V(sg * 0.3, 1.0, 0.0), "palm": V(-sg, 0.1, 0)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def curtsy_lunge(r, st):
    """Curtsy lunge: one foot steps back and across behind the other (like a curtsy), both knees bend, the front knee
    stays over the toes, hips square; back to standing; other side."""
    k = r.k
    w = 0.095 * k * st["stance"]

    def fn(side, e, t):
        back = side
        front = "L" if back == "R" else "R"
        fg = 1.0 if front == "L" else -1.0
        bg = -fg
        step = smooth(min(1.0, e / 0.45))                      # step back first, then lower
        u = smooth((e - 0.40) / 0.60) if e > 0.40 else 0.0
        home = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 6.0) for s, sg in SIDES}
        # back foot: behind the front heel and across to the far side of it, on the ball
        B = r.foot(back, fg * 0.11 * k, r.ankle0[back].y + 0.44 * k, bg * 12.0, pitch=50.0)
        ball = home[back][0].lerp(B[0], smoother(step)) + V(0, 0, 0.05 * k * math.sin(math.pi * step))
        feet = {front: home[front], back: (ball, lerp(home[back][1], B[1], step), 50.0 * smooth(min(1.0, step * 1.3)))}
        b = breath(t, 4.0, 0.0)
        sp = torso_spec(V(fg * 0.03 * k * step, r.P0.y + 0.004 * k + 0.10 * k * step + 0.03 * k * u, 0), pitch=2.0 + 8.0 * u, yaw=-fg * 6.0 * step,
                        spine=0.5, chest=-1.0, chest_yaw=fg * 4.0 * step, head_pitch=2.0 + 4.0 * u, br=b * 0.6)
        sp["feet"] = feet
        sp["kpole"] = {front: V(fg * 0.10, -1, 0), back: V(fg * 0.3, -1, -0.5 * step)}
        z = r.fit_z(sp, 0.992)
        sp["pos"].z = z - 0.30 * k * u
        sp["arms"] = lambda pts: {s: {"w": (pts["S_L"] + pts["S_R"]) / 2 + V(sg * 0.035 * k, -0.25 * k, -0.20 * k),
                                      "pole": V(sg * 0.6, 0.5, -1.0), "fingers": V(-sg * 0.3, -0.2, 1.0), "palm": V(-sg, 0, 0)} for s, sg in SIDES}
        return sp
    return _sides(r, st, [(0.35, 0, 0), (1.8 * st["tempo"], 0, 1), (0.3, 1, 1), (1.6 * st["tempo"], 1, 0), (0.3, 0, 0)], fn)


def squat_calf_raise(r, st):
    """Squat, stand, then rise onto the balls of the feet; lower the heels with control."""
    k = r.k
    kw = dict(arms_mode="chest")
    segs = [(0.35, 0, 0), (1.7, 0, 1), (0.25, 1, 1), (1.3, 1, 0), (0.15, 0, 0)]
    T1 = sum(d for d, _, _ in segs)
    segc = [(0.8, 0, 1), (0.5, 1, 1), (1.1, 1, 0), (0.3, 0, 0)]
    T2 = sum(d for d, _, _ in segc)
    T = T1 + T2
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t <= T1:
            u, c = _phases(t, segs), 0.0
        else:
            u, c = 0.0, _phases(t - T1, segc)
        sp = _squat_pose(r, st, u, 1.0, t, **kw)
        if c > 0:
            z0 = sp["pos"].z
            probe = dict(sp)
            probe["feet"] = dict(sp["feet"])
            zf = r.fit_z(probe, 0.992)
            feet = {}
            for s, (ball, yaw, pitch) in sp["feet"].items():
                feet[s] = (ball, yaw, 26.0 * c)
            sp["feet"] = feet
            z1 = r.fit_z(sp, 0.992)
            sp["pos"].z = z0 + (z1 - zf)
        out.append(sp)
    return out


# =============================================================================================== wall
WALL_GAP = 0.012                                                # m, palm skin to the wall surface


def wall_pushup(r, st):
    """Wall push-up: hands on the wall at shoulder height, body one straight line leaning in from the ankles; the
    elbows bend to bring the chest toward the wall, then press back."""
    k = r.k
    w = 0.10 * k * st["stance"]
    feet = {s: r.foot(s, sg * w, r.ankle0[s].y, sg * 4.0) for s, sg in SIDES}
    A = r.ankle("L", feet["L"])
    mid = (r.hj["L"] + r.hj["R"]) / 2

    def body(phi, t=0.0, b=0.0):
        up = Rx(phi) @ V(0, 0, 1)
        hipj = V(0, A.y, A.z) + up * (r.leg * 0.994)
        sp = torso_spec(V(0, 0, 0), pitch=phi, spine=0.0, chest=0.0, head_pitch=phi - 4.0, br=b)
        sp["pos"] = hipj - sp["pel"] @ mid
        sp["feet"] = dict(feet)
        sp["kpole"] = {s: V(sg * 0.05, -1, 0) for s, sg in SIDES}
        return sp
    phi_top = 17.0
    _, top = r.torso(body(phi_top))
    dx = 0.06 * k
    hand_z = top["S_L"].z - 0.04 * k
    reach = 0.95 * r.la
    y_w = top["S_L"].y - math.sqrt(reach ** 2 - dx ** 2 - (0.04 * k) ** 2)
    wrist = {s: V(top["S_" + s].x + sg * dx, y_w, hand_z) for s, sg in SIDES}
    # bottom: the lean at which the shoulders come within 0.62 of the arm's reach of the hands
    lo, hi = phi_top, 45.0
    for _ in range(40):
        m = (lo + hi) / 2
        _, p = r.torso(body(m))
        if (p["S_L"] - wrist["L"]).length > 0.60 * r.la:
            lo = m
        else:
            hi = m
    phi_bot = (lo + hi) / 2

    def f(d, t, T):
        sp = body(lerp(phi_top, phi_bot, d), t, breath(t, T, 0.0) * 0.3)
        sp["prot"] = {"L": 6.0 - 12.0 * d, "R": 6.0 - 12.0 * d}
        sp["arms"] = {s: {"w": wrist[s], "pole": V(sg * 0.75, 0.3, -0.5), "fingers": V(-sg * 0.15, 0, 1), "palm": V(0, -1, 0)} for s, sg in SIDES}
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.6, 0.25, 1.2, 0.4), f)


WALL_SIT_BACK = 0.135                                           # m (x k), hip joint to the wall at the back of the pelvis


def wall_sit(r, st):
    """Wall sit: back flat against the wall, feet out in front, slide down until the thighs are a little above level,
    hold with steady breathing, slide back up."""
    k = r.k
    w = 0.10 * k * st["stance"]
    yh = 0.20 * k                                                 # hip joints' y (the wall is behind them, +Y)
    th = math.radians(12.0)                                       # thighs 12 deg above level at the bottom
    s_ = "L"
    hz_bot = 0.0
    mid = (r.hj["L"] + r.hj["R"]) / 2
    # bottom: shins vertical under the knees
    sp0 = torso_spec(V(0, 0, 0), pitch=-2.0)
    hj_off = sp0["pel"] @ mid
    A_z = r.ankle0["L"].z
    knee_z = A_z + r.l2[s_] * 0.999
    hz_bot = knee_z + r.l1[s_] * math.sin(th) * 0.999
    knee_y = yh - r.l1[s_] * math.cos(th) * 0.999
    ankle_y = knee_y
    feet = {}
    for s, sg in SIDES:
        f0 = r.foot(s, sg * w, 0.0, sg * 6.0)
        a0 = r.ankle(s, f0)
        feet[s] = (f0[0] + V(0, ankle_y - a0.y, 0), f0[1], f0[2])

    def f(u, t, T):
        b = breath(t, T / 2, 0.0)
        sp = torso_spec(V(0, 0, 0), pitch=-2.0, spine=1.0, chest=-1.0, head_pitch=0.0, br=b * 0.5)
        sp["feet"] = dict(feet)
        sp["kpole"] = {s: V(sg * 0.12, -1, 0) for s, sg in SIDES}
        sp["pos"] = V(0, yh, 0) - V(0, hj_off.y, 0)
        z_top = r.fit_z(sp, 0.985)
        sp["pos"].z = lerp(z_top, hz_bot - hj_off.z, u)

        def arms(pts, u=u):
            res = {}
            for s2, sg in SIDES:
                hangw = hang(r, pts, s2, sg, out=0.10, fwd=0.0, reach=0.985)
                Hj = sp["pos"] + sp["pel"] @ r.hj[s2]
                K = V(Hj.x, knee_y, knee_z)
                # the furthest point along the top of the thigh the hand can rest on with a soft elbow
                S2 = pts["S_" + s2]
                f = 0.55
                while f > 0.05 and (S2 - (Hj.lerp(K, f) + V(sg * 0.01 * k, 0, 0.095 * k))).length > 0.96 * r.la:
                    f -= 0.01
                on = {"w": Hj.lerp(K, f) + V(sg * 0.01 * k, 0, 0.095 * k), "pole": V(sg * 0.6, 0.3, -0.4), "fingers": V(0, -1, -0.2),
                      "palm": V(0, 0, -1)}
                # only near the bottom, where the knee has reached the spot used above (earlier it was out of reach)
                reach_ok = (S2 - on["w"]).length <= 0.985 * r.la      # (shorter arms: the hands stay by the sides)
                res[s2] = mix_arm(hangw, on, smooth((u - 0.75) / 0.25)) if reach_ok else hangw
            return res
        sp["arms"] = arms
        return sp
    return _loop(r, st, [(0.4, 0, 0), (2.0, 0, 1), (2.6, 1, 1), (1.6, 1, 0), (0.4, 0, 0)], f)


# =============================================================================================== equipment
def goblet_squat(r, st):
    """Goblet squat: one dumbbell held upright against the chest, both hands cupping the top end, elbows down; squat
    to about thighs level, knees out over the toes, chest tall; stand."""
    k = r.k

    def f(u, t, T):
        sp = _squat_pose(r, st, 0.92 * u, 0.0, t, lean_max=30.0)
        _effort(sp, 0.4)

        def arms(pts):
            res = {}
            c = (pts["S_L"] + pts["S_R"]) / 2
            fwd = (pts["S_L"] - pts["S_R"]).cross(V(0, 0, 1)).normalized()
            for s, sg in SIDES:
                res[s] = {"w": c + fwd * (0.20 * k) + V(sg * 0.045 * k, 0, -0.09 * k), "pole": V(sg * 0.35, -0.2, -1.0),
                          "fingers": V(-sg * 0.35, 0.15, 1.0), "palm": V(-sg * 0.85, 0.25, 0.3)}
            return res
        sp["arms"] = arms
        return sp
    return _loop(r, st, _segs(st, 0.35, 1.9, 0.3, 1.4, 0.4), f)


def _lying_base(r, st, S_y=0.40, S_z=0.085):
    """On the back, knees bent, feet flat (the glute bridge's start). Returns (spec maker, feet)."""
    k = r.k
    S_z, S_y = S_z * k, S_y * k
    l1, l2 = r.l1["L"], r.l2["L"]
    A_z = r.ankle0["L"].z

    def body(extra_spine=0.0, extra_chest=0.0, head=0.0, br=0.0, pel_pitch=-93.0):
        sp = torso_spec(V(0, 0, 0), pitch=pel_pitch, spine=extra_spine, chest=extra_chest, head_pitch=-90.0 + head, br=br)
        return sp
    sp0 = body()
    _, pts = r.torso(sp0)
    mid = (pts["S_L"] + pts["S_R"]) / 2
    pos = V(0, S_y, S_z) - mid
    # knees up, feet flat about a shin's length in front of the hips
    Hj = pos + sp0["pel"] @ r.hj["L"]
    ankle_y = Hj.y - 0.80 * l1
    w = 0.10 * k * st["stance"]
    feet = {}
    for s, sg in SIDES:
        f = r.foot(s, sg * w, 0.0, sg * 4.0)
        a0 = r.ankle(s, f)
        feet[s] = (f[0] + V(0, ankle_y - a0.y, 0), f[1], f[2])

    def make(**kw):
        sp = body(**kw)
        sp["pos"] = pos.copy()
        sp["feet"] = dict(feet)
        sp["kpole"] = {s: V(sg * 0.12, -0.4, 1.0) for s, sg in SIDES}
        return sp
    return make, feet, pos


def floor_press(r, st):
    """Dumbbell floor press: on the back, knees bent, upper arms on the floor at about 45 degrees from the body, forearms
    up; press the dumbbells up over the chest, lower until the upper arms touch the floor again."""
    k = r.k
    make, _, _ = _lying_base(r, st)

    def f(e, t, T):
        sp = make(br=breath(t, T, 0.0) * 0.4)

        def arms(pts, e=e):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                E = S + V(sg * 0.70, -0.70, 0).normalized() * (r.a1[s] * 0.97) + V(0, 0, -0.035 * k)
                E.z = max(E.z, 0.045 * k)
                lo = E + V(0, 0, r.a2[s] * 0.97)
                hi = S + V(sg * 0.03 * k, -0.04 * k, 0.975 * r.la)
                w = lo.lerp(hi, e)
                res[s] = {"w": w, "pole": V(sg * 0.8, -0.6, -0.2), "fingers": V(0, 0.15, 1.0), "palm": V(0, -1.0, 0.1)}
            return res
        sp["arms"] = arms
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.1, 0.3, 1.7, 0.4), f)


def shrug(r, st):
    """Dumbbell shrug: arms long with the dumbbells at the sides; lift the shoulders straight up toward the ears,
    pause, lower slowly. No rolling."""
    def f(e, t, T):
        sp = _stand(r, st, t, T=T)
        sp["shrug"] = {"L": 2.0 + 22.0 * e, "R": 2.0 + 22.0 * e}
        sp["hed"] = Rx(1.0 * e) @ sp["hed"]
        sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=0.09, fwd=0.0, reach=0.988) for s, sg in SIDES}
        return sp
    return _loop(r, st, _segs(st, 0.4, 0.8, 0.5, 1.2, 0.4), f)


def db_calf_raise(r, st):
    """Calf raise holding dumbbells at the sides."""
    out = ac.calf_raise(r, st)
    for sp in out:
        sp["arms"] = lambda pts: {s: hang(r, pts, s, sg, out=0.10, fwd=0.0, reach=0.988) for s, sg in SIDES}
    return out


KB_REST = 18.0         # deg: at rest the bell hangs a little in front (QC: straight down, the hands met the hips)


def kb_swing(r, st):
    """Two-hand kettlebell swing (hip hinge): the bell swings back high between the thighs as the hips go back, then the
    hips drive forward and the straight arms float up to chest height; the bell falls back into the next hinge. Two
    swings per clip, from and to a standing hold."""
    k = r.k
    Tc = 1.55 * st["tempo"]
    T0 = 0.5
    T = T0 * 2 + 2 * Tc
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t < T0 or t > T - T0:
            # standing hold with the bell hanging in front (start and end of the clip)
            ph = None
            u, a = 0.0, KB_REST
        else:
            ph = ((t - T0) % Tc) / Tc
            cyc = int((t - T0) // Tc)
            # hinge u: deepest when the bell is furthest back (ph 0.18), standing tall at the float (ph 0.65)
            u = 0.5 + 0.5 * math.cos(2 * math.pi * (ph - 0.18))
            # arm angle from hanging (0) forward: back between the legs -28 deg (rel. to the body), up to ~88 at the top
            a = -28.0 + 116.0 * (0.5 - 0.5 * math.cos(2 * math.pi * (ph - 0.18)))
            a = lerp(KB_REST, a, smooth(min(1.0, (t - T0) / 0.35)) if cyc == 0 else 1.0)
            a = lerp(a, KB_REST, smooth((t - (T - T0 - 0.35)) / 0.35)) if t > T - T0 - 0.35 else a
            u = lerp(0.0, u, smooth(min(1.0, (t - T0) / 0.35)) if cyc == 0 else 1.0)
            u = lerp(u, 0.0, smooth((t - (T - T0 - 0.35)) / 0.35)) if t > T - T0 - 0.35 else u
        sp = _squat_pose(r, st, 0.55 * u, 0.0, t, width=1.45, toe=18.0, lean_max=72.0, shin=12.0)
        lean = 72.0 * ((0.55 * u) ** 0.8)

        def arms(pts, a=a):
            res = {}
            wa = math.radians(a)
            Sm = (pts["S_L"] + pts["S_R"]) / 2
            for s, sg in SIDES:
                S = pts["S_" + s]
                dx = S.x - sg * 0.042 * k
                rr = math.sqrt(max((0.985 * r.la) ** 2 - dx * dx, 1e-6))
                w = V(sg * 0.042 * k, S.y - rr * math.sin(wa), S.z - rr * math.cos(wa))
                d = (w - S).normalized()
                res[s] = {"w": w, "pole": V(sg * 0.5, 0.6, 0.2), "fingers": d, "palm": V(0, math.cos(wa), -math.sin(wa))}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


DIP_BENCH_H = 0.45


def bench_dip(r, st):
    """Bench dip (bent knees): hands on the edge of a bench behind you, fingers forward, feet flat with knees bent;
    lower the hips by bending the elbows to about 90 degrees, shoulders down, then press back up."""
    k = r.k
    wrist_h = 0.035 * k
    yb = 0.0
    mid = (r.hj["L"] + r.hj["R"]) / 2
    pitch = 4.0

    def base(z):
        sp = torso_spec(V(0, 0.0, z), pitch=pitch, spine=1.0, chest=-1.0, head_pitch=2.0)
        return sp
    _, p0 = r.torso(base(0.0))
    S0 = (p0["S_L"] + p0["S_R"]) / 2
    back = 0.14 * k                                             # hands behind the shoulders: the seat clears the bench
    z_top = DIP_BENCH_H + wrist_h + math.sqrt((0.955 * r.la) ** 2 - back ** 2) - S0.z
    wrist = {s: V(p0["S_" + s].x + sg * 0.012 * k, p0["S_" + s].y + back, DIP_BENCH_H + wrist_h) for s, sg in SIDES}
    drop = 0.20 * k
    Hj = V(0, 0, z_top) + base(z_top)["pel"] @ mid
    w = 0.10 * k * st["stance"]
    feet = {}
    for s, sg in SIDES:
        f = r.foot(s, sg * w, 0.0, sg * 5.0)
        a0 = r.ankle(s, f)
        feet[s] = (f[0] + V(0, Hj.y - 0.95 * r.l1[s] - a0.y, 0), f[1], f[2])

    def f(d, t, T):
        sp = base(z_top - drop * d)
        sp["pos"] = V(0, -0.01 * k * d, z_top - drop * d)
        sp["feet"] = dict(feet)
        sp["kpole"] = {s: V(sg * 0.10, -1, 0.2) for s, sg in SIDES}
        sp["shrug"] = {"L": -3.0, "R": -3.0}
        sp["arms"] = {s: {"w": wrist[s], "pole": V(sg * 0.15, 1.0, 0.0), "fingers": V(0, -1.0, -0.15), "palm": V(0, 0, -1)} for s, sg in SIDES}
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.5, 0.25, 1.2, 0.4), f)


# =============================================================================================== on the floor
def crunch(r, st):
    """Crunch: on the back, knees bent, feet flat, arms folded on the chest; curl the head and shoulders a little off
    the floor (lower back stays down), pause, lower slowly."""
    k = r.k
    make, _, _ = _lying_base(r, st)

    def f(e, t, T):
        sp = make(extra_spine=13.0 * e, extra_chest=22.0 * e, head=26.0 * e, br=breath(t, T, 0.0) * 0.3)
        sp["arms"] = _chest_cross(r, k)
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.0, 0.5, 1.4, 0.4), f)


def heel_taps(r, st):
    """Heel taps: on the back, knees bent, head and shoulders slightly lifted; side-bend to reach one hand toward the
    heel on that side, then the other, arms long beside the body just above the floor."""
    k = r.k
    make, _, _ = _lying_base(r, st)
    T = 4.0
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        x = _phases(t, [(0.3, 0, 0), (0.7, 0, 1), (0.3, 1, 1), (1.4, 1, -1), (0.3, -1, -1), (0.7, -1, 0), (0.3, 0, 0)])
        on = smoother(min(1.0, t / 0.3)) * smoother(min(1.0, (T - t) / 0.3))
        sp = make(extra_spine=7.0 * on, extra_chest=12.0 * on, head=16.0 * on, br=breath(t, T, 0.0) * 0.3)
        sp["spi"] = Rz(-5.0 * x) @ sp["spi"]
        sp["che"] = Rz(-12.0 * x) @ sp["che"]

        def arms(pts, x=x):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                reach = 0.975 * r.la * (1.0 + 0.0 * x)
                w = S + V(sg * 0.12 * k, -reach, 0)
                w.z = max(0.075 * k, S.z - 0.10 * k)
                d = (w - S)
                d = d * (reach / d.length)
                w = S + d
                res[s] = {"w": w, "pole": V(sg * 0.4, 0, 1.0), "fingers": V(0, -1, 0), "palm": V(-sg * 0.6, 0, -0.8)}
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


def reverse_crunch(r, st):
    """Reverse crunch: on the back, arms on the floor, legs in tabletop (hips and knees 90 deg); curl the hips a little
    off the floor bringing the knees toward the chest, lower slowly. Upper back stays down."""
    k = r.k
    S_z, S_y = 0.085 * k, 0.40 * k

    def f(e, t, T):
        pp = -92.0 - 30.0 * e
        sp = torso_spec(V(0, 0, 0), pitch=pp, spine=22.0 * e, chest=8.0 * e, head_pitch=-90.0, br=breath(t, T, 0.0) * 0.3)
        _, pts = r.torso(sp)
        mid = (pts["S_L"] + pts["S_R"]) / 2
        sp["pos"] = V(0, S_y, S_z) - mid
        R_ = Rx(pp + 92.0)
        feet, poles = {}, {}
        for s, sg in SIDES:
            Hj = sp["pos"] + sp["pel"] @ r.hj[s]
            K = Hj + (R_ @ V(0, -0.05, 1.0)).normalized() * r.l1[s] * 0.999
            A = K + (R_ @ V(0, -1.0, -0.05)).normalized() * r.l2[s] * 0.999
            feet[s] = r.foot_toward(s, A, (R_ @ V(0, -0.35, 1.0)).normalized())
            poles[s] = (R_ @ V(0, 1.0, 1.0)).normalized()
        sp["feet"] = feet
        sp["kpole"] = poles

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                wz = 0.085 * k
                dx = sg * 0.12 * k
                dy = -math.sqrt(max((0.985 * r.la) ** 2 - dx * dx - (S.z - wz) ** 2, 1e-6))
                res[s] = {"w": V(S.x + dx, S.y + dy, wz), "pole": V(sg * 0.4, 0, -1.0), "fingers": V(sg * 0.1, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        return sp
    return _loop(r, st, _segs(st, 0.4, 1.1, 0.3, 1.5, 0.4), f)


def toe_taps(r, st):
    """Tabletop toe taps: on the back, legs in tabletop; one leg lowers from the hip with the knee kept bent until the
    toes touch the floor lightly, and returns; then the other. Lower back stays down."""
    k = r.k
    S_z, S_y = 0.085 * k, 0.40 * k
    sp0 = torso_spec(V(0, 0, 0), pitch=-92.0, head_pitch=-90.0)
    _, pts = r.torso(sp0)
    mid = (pts["S_L"] + pts["S_R"]) / 2
    pos = V(0, S_y, S_z) - mid

    def leg(s, b_deg, sp):
        Hj = sp["pos"] + sp["pel"] @ r.hj[s]
        th = _rot(b_deg) @ V(0, -0.05, 1.0)
        th.normalize()
        K = Hj + th * r.l1[s] * 0.999
        sh = _rot(b_deg) @ V(0, -1.0, -0.05)
        sh.normalize()
        A = K + sh * r.l2[s] * 0.999
        u = min(1.0, b_deg / 60.0)
        return A, (_rot(b_deg) @ V(0, -0.35, 1.0)).normalized().lerp(V(0, -0.75, -0.66), smooth(u))

    # how far the thigh tips toward the feet for the toes to reach the floor
    lo, hi = 0.0, 80.0
    sp_probe = torso_spec(pos.copy(), pitch=-92.0, head_pitch=-90.0)
    for _ in range(30):
        m = (lo + hi) / 2
        A, d = leg("L", m, sp_probe)
        ball = A + (r.foot_toward("L", A, d.normalized())[0] - A)
        if ball.z > r.ball0["L"].z + 0.012 * k:
            lo = m
        else:
            hi = m
    b_tap = (lo + hi) / 2

    def fn(side, e, t):
        sp = torso_spec(pos.copy(), pitch=-92.0, head_pitch=-90.0, br=breath(t, 4.0, 0.0) * 0.3)
        feet, poles = {}, {}
        for s, sg in SIDES:
            b = b_tap * e if s == side else 0.0
            A, d = leg(s, b, sp)
            feet[s] = r.foot_toward(s, A, d.normalized())
            poles[s] = (_rot(b) @ V(0, 1.0, 1.0)).normalized()
        sp["feet"] = feet
        sp["kpole"] = poles

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                wz = 0.085 * k
                dx = sg * 0.12 * k
                dy = -math.sqrt(max((0.985 * r.la) ** 2 - dx * dx - (S.z - wz) ** 2, 1e-6))
                res[s] = {"w": V(S.x + dx, S.y + dy, wz), "pole": V(sg * 0.4, 0, -1.0), "fingers": V(sg * 0.1, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _segs(st, 0.3, 1.2, 0.15, 1.1, 0.3), fn)


def _rot(b_deg):
    """Rotation of the tabletop leg toward the feet (about the X axis)."""
    return Rx(b_deg)


def high_plank(r, st):
    """High plank: hands under the shoulders, arms long (soft elbows), one straight line from head to heels; breathe."""
    geo = _pushup_geometry(r, st)
    T = 4.0
    n = frames(T)
    return [_pushup_pose(r, st, geo, 0.0, T * i / (n - 1)) for i in range(n)]


def shoulder_taps(r, st):
    """Plank shoulder taps: from a high plank with the feet a little wider, one hand lifts to tap the opposite shoulder
    and returns to the same spot; then the other. The hips stay level."""
    k = r.k
    st2 = dict(st)
    geo = _pushup_geometry(r, st2)
    body, phi_top, phi_bot, wrist, blades = geo

    def fn(side, e, t):
        sp = _pushup_pose(r, st2, geo, 0.0, t)
        feet = {}
        for s, (ball, yaw, pitch) in sp["feet"].items():
            sg = 1.0 if s == "L" else -1.0
            feet[s] = (ball + V(sg * 0.05 * k, 0, 0), yaw, pitch)
        sp["feet"] = feet
        sg = 1.0 if side == "L" else -1.0
        # the weight shifts a little over the supporting hand
        sp["pos"] = sp["pos"] + V(-sg * 0.015 * k * smooth(min(1.0, e / 0.3)), 0, 0)
        sp["pel"] = Ry(-sg * 2.0 * e) @ sp["pel"]
        base = sp["arms"]

        def arms(pts, e=e, base=base):
            res = dict(base)
            O = pts["S_" + ("R" if side == "L" else "L")]
            tap = O + V(sg * 0.04 * k, -0.06 * k, -0.07 * k)
            lift = wrist[side] + V(0, 0, 0.10 * k)
            # up off the floor first, then across to the shoulder on one smooth path (no corner), and back the same way
            ex = smoother(max(0.0, (e - 0.12) / 0.88))
            w = wrist[side].lerp(tap, ex) + V(0, 0, 0.09 * k * smooth(min(1.0, e / 0.30)) * (1.0 - ex))
            res[side] = {"w": w, "pole": V(sg * 0.72, 0.68, 0.15).lerp(V(sg * 0.6, 0.2, -1.0), smooth(e)),
                         "fingers": V(sg * 0.14, -1, 0).lerp(V(-sg, 0, 0.3), smooth(e)), "palm": V(0, 0, -1).lerp(V(0, 1.0, 0.0), smooth(e))}
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, [(0.3, 0, 0), (0.7, 0, 1), (0.25, 1, 1), (0.7, 1, 0), (0.3, 0, 0)], fn)


def single_leg_bridge(r, st):
    """Single-leg glute bridge: knees bent, one leg straightens out in line with the thigh; the hips lift on the other
    leg until shoulders, hips and knee form a line, then lower; other side."""
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
    a_top = (lo + hi) / 2 * 0.92                                # a little lower than the two-leg bridge
    K = knee(a_top / 0.92)
    w = 0.10 * k * st["stance"]
    feet0 = {}
    for s, sg in SIDES:
        f = r.foot(s, sg * w, 0.0, sg * 4.0)
        a0 = r.ankle(s, f)
        feet0[s] = (f[0] + V(0, K.y - a0.y, 0), f[1], f[2])
    a_bot = math.radians(3.0)

    def fn(side, e, t):
        ext = min(1.0, e)                                       # 0..1 straighten the leg, then 1..2 lift the hips
        lift = max(0.0, e - 1.0)
        sp = body(lerp(a_bot, a_top, lift))
        sp["feet"] = dict(feet0)
        sp["kpole"] = {s: V(s_ * 0.12, -0.4, 1.0) for s, s_ in SIDES}
        if ext > 0:
            Hj = sp["pos"] + sp["pel"] @ r.hj[side]
            Kp = None
            # the free leg straightens in line with the planted thigh (knees level), so it is in the air throughout
            other = "L" if side == "R" else "R"
            Hp = sp["pos"] + sp["pel"] @ r.hj[other]
            Ap = r.ankle(other, feet0[other])
            dv = Ap - Hp
            dd = min(dv.length, (r.l1[other] + r.l2[other]) * 0.999)
            dn = dv.normalized()
            aa = (r.l1[other] ** 2 + dd * dd - r.l2[other] ** 2) / (2 * dd)
            hh = math.sqrt(max(r.l1[other] ** 2 - aa * aa, 0.0))
            perp = V(0, 0, 1) - dn * dn.z
            perp = perp.normalized() if perp.length > 1e-6 else V(0, 0, 1)
            thigh = ((Hp + dn * aa + perp * hh) - Hp).normalized()
            A0 = r.ankle(side, feet0[side])
            Kp = Hj + thigh * r.l1[side] * 0.999
            K0 = Hj + ((Hp + dn * aa + perp * hh) - Hp)               # the bent knee before the leg straightens
            shin_bent = (A0 - K0).normalized()
            A = Kp + shin_bent.lerp(thigh, ext).normalized() * r.l2[side] * 0.985
            A = A0.lerp(A, smooth(min(1.0, ext / 0.2)))          # leaves exactly from the planted ankle (QC: a 1 cm step)
            d0 = (r.foot_q(side, feet0[side][1], 0.0) @ r.fv[side]).normalized()
            sp["feet"][side] = r.foot_toward(side, A, d0.lerp(V(0, -0.3, 1.0).normalized(), ext), yaw=feet0[side][1])
            # kneecap square to the straightening leg, facing up (the default pole ran almost along the leg: it twisted)
            kp = V(0, thigh.z, -thigh.y).normalized()
            sp["kpole"][side] = sp["kpole"][side].lerp(kp, smooth(min(1.0, ext / 0.3)))

        def arms(pts):
            res = {}
            for s, sg in SIDES:
                S = pts["S_" + s]
                wz = 0.085 * k
                dx = sg * 0.11 * k
                dy = -math.sqrt(max((0.985 * r.la) ** 2 - dx * dx - (S.z - wz) ** 2, 1e-6))
                res[s] = {"w": V(S.x + dx, S.y + dy, wz), "pole": V(sg * 0.4, 0, -1.0), "fingers": V(sg * 0.1, -1, 0), "palm": V(0, 0, -1)}
            return res
        sp["arms"] = arms
        return sp
    tp = st["tempo"]
    # each part has its own time (QC: squeezed into a quarter of the lift, the free foot swung 27 cm a frame)
    return _sides(r, st, [(0.4, 0, 0), (0.9 * tp, 0, 1), (0.2, 1, 1), (1.5 * tp, 1, 2), (0.8, 2, 2), (1.6 * tp, 2, 1), (0.2, 1, 1),
                          (0.9 * tp, 1, 0), (0.3, 0, 0)], fn)


def _quad_leg(r, st, side, thigh, shin, fdir, e):
    """All fours with one leg moved to thigh / shin directions; e blends from the kneeling leg (0) to them (1)."""
    sp, wrists, pitch = _quadruped_base(r, st)
    feet = dict(sp["feet"])
    Hj = sp["pos"] + sp["pel"] @ r.hj[side]
    A0 = r.ankle(side, feet[side])
    K0 = Hj + V(0, 0, -1) * r.l1[side] * 0.998
    K = Hj + (V(0, 0, -1).lerp(thigh.normalized(), e)).normalized() * r.l1[side] * 0.998
    sh0 = (A0 - K0).normalized()
    shb = sh0.lerp(shin.normalized(), e).normalized()
    A = K + shb * r.l2[side] * 0.998
    d0 = (r.foot_q(side, feet[side][1], feet[side][2]) @ r.fv[side]).normalized()
    feet[side] = r.foot_toward(side, A, d0.lerp(fdir.normalized(), e))
    sp["feet"] = feet
    return sp, wrists


def donkey_kick(r, st):
    """Quadruped glute kickback ("donkey kick"): on all fours, one knee stays bent at 90 degrees as the thigh lifts back
    to hip height, sole toward the ceiling; lower with control; other side. No arching."""
    def fn(side, e, t):
        a = math.radians(-90.0 + 90.0 * smooth(e))
        thigh = V(0, math.cos(a), math.sin(a))
        shin = V(0, math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
        sp, wrists = _quad_leg(r, st, side, thigh, shin, V(0, 1.0, -0.25).lerp(V(0, 1.0, 0.1), smooth(e)), smooth(min(1.0, e / 0.15)))
        sp["kpole"] = dict(sp["kpole"])
        sp["kpole"][side] = V(0, -0.3, -1).lerp(thigh.normalized(), smooth(min(1.0, e / 0.15)))   # knee where the thigh points
        sp["arms"] = _hands_on_floor(wrists)
        return sp
    return _sides(r, st, _segs(st, 0.4, 1.2, 0.4, 1.2, 0.3), fn)


def fire_hydrant(r, st):
    """Fire hydrant: on all fours, the bent knee lifts out to the side to about hip height, knee stays at 90 degrees;
    lower with control; other side. Hips stay square."""
    def fn(side, e, t):
        sg = 1.0 if side == "L" else -1.0
        b = math.radians(62.0 * smooth(e))
        thigh = V(sg * math.sin(b), 0.0, -math.cos(b))
        shin = V(0, 1.0, -0.06)
        sp, wrists = _quad_leg(r, st, side, thigh, shin, V(0, 1.0, -0.25), smooth(min(1.0, e / 0.15)))
        sp["kpole"] = dict(sp["kpole"])
        sp["kpole"][side] = V(0, -0.3, -1).lerp(thigh.normalized(), smooth(min(1.0, e / 0.15)))
        sp["pel"] = Ry(-sg * 3.0 * e) @ sp["pel"]
        sp["arms"] = _hands_on_floor(wrists)
        return sp
    return _sides(r, st, _segs(st, 0.4, 1.1, 0.4, 1.1, 0.3), fn)


CHILD_PITCH = 88.0


def childs_pose(r, st):
    """Child's pose: from all fours the hips sink back toward the heels, arms stay long on the floor, forehead toward
    the floor; rest and breathe; come back to all fours."""
    k = r.k
    sp0, wrists, pitch0 = _quadruped_base(r, st)
    kz = 0.055 * k
    knee_y = 0.20 * k
    l1 = r.l1["L"]
    mid_j = (r.hj["L"] + r.hj["R"]) / 2
    th_end = math.degrees(math.acos(max(-1.0, min(1.0, (0.25 * k - kz) / l1))))
    S0 = (lambda p: (p["S_L"] + p["S_R"]) / 2)(r.torso(sp0)[1])
    d0 = (S0 - (wrists["L"] + wrists["R"]) / 2).length

    def pose(e, t):
        # the hips travel back along the arc around the knees; the trunk folds forward over the thighs (head lowest),
        # so the shoulders sink toward the planted hands and the arms end up long on the floor
        th = math.radians(th_end * smoother(e))
        Hm = V(0, knee_y + l1 * 0.998 * math.sin(th), kz + l1 * 0.998 * math.cos(th))
        pitch = lerp(pitch0, CHILD_PITCH, smoother(e))
        sp = torso_spec(V(0, 0, 0), pitch=pitch, spine=6.0 * e, chest=4.0 * e, head_pitch=pitch - 14.0 + 4.0 * e,
                        br=breath(t, 4.0, 0.0) * 0.5 * e)
        sp["pos"] = Hm - sp["pel"] @ mid_j
        sp["feet"] = dict(sp0["feet"])
        sp["kpole"] = dict(sp0["kpole"])
        sp["arms"] = _hands_on_floor(wrists)
        return sp
    segs = [(0.4, 0, 0), (2.0, 0, 1), (2.4, 1, 1), (1.8, 1, 0), (0.4, 0, 0)]
    T = sum(d for d, _, _ in segs)
    n = frames(T)
    return [pose(_phases(T * i / (n - 1), segs), T * i / (n - 1)) for i in range(n)]


BEAR_TIP = 9.0


def bear_hold(r, st):
    """Bear plank hold: on all fours, toes tucked, knees lift a few centimetres off the floor; back flat; breathe."""
    k = r.k
    T = 4.4
    n = frames(T)
    out = []
    sp0, wrists, pitch0 = _quadruped_base(r, st)
    hover = 0.065 * k
    tuck = V(0, -0.6, -1.0).normalized()
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, [(0.4, 0, 0), (0.8, 0, 1), (2.2, 1, 1), (0.7, 1, 0), (0.3, 0, 0)])
        # the knees lift by raising the hips; the trunk tips a little nose-down so the shoulders stay over the hands
        sp, _, _ = _quadruped_base(r, st, pitch_fixed=pitch0 + BEAR_TIP * e)
        sp["pos"] = sp["pos"] + V(0, 0, hover * e)
        feet = {}
        for s, sg in SIDES:
            Hj = sp["pos"] + sp["pel"] @ r.hj[s]
            K = Hj + V(0, 0, -r.l1[s] * 0.998)
            # toes tucked: the ankle sits a foot's length above the ball, the shin slopes up to it from the knee
            # the ball rests exactly at floor height, so the toes flatten onto the floor (the build bends them flat only
            # when the ball is down -- QC: lifted 2.7 cm, the straight toes poked 2-3 cm into the floor)
            Az = r.ball0[s].z - tuck.z * r.fv[s].length
            dz = Az - K.z
            A_t = V(K.x, K.y + math.sqrt(max((r.l2[s] * 0.998) ** 2 - dz * dz, 1e-6)), Az)
            A0 = r.ankle(s, sp0["feet"][s])
            d0 = (r.foot_q(s, sp0["feet"][s][1], sp0["feet"][s][2]) @ r.fv[s]).normalized()
            ee = smooth(min(1.0, e / 0.6))                          # the toes tuck first, then the knees lift
            # the ankle rises ahead of the turn of the foot, so the toes never sweep through the floor
            feet[s] = r.foot_toward(s, A0.lerp(A_t, smooth(min(1.0, ee * 1.7))), d0.lerp(tuck, ee).normalized())
        sp["feet"] = feet
        sp["kpole"] = {s: V(0, -0.3, -1) for s, _ in SIDES}
        sp["arms"] = _hands_on_floor(wrists)
        out.append(sp)
    return out


CLIPS = (
    ("good_morning", good_morning), ("curtsy_lunge", curtsy_lunge), ("squat_calf_raise", squat_calf_raise),
    ("single_leg_balance", single_leg_balance), ("single_leg_rdl", single_leg_rdl), ("side_leg_raise", side_leg_raise),
    ("glute_kickback", glute_kickback), ("butt_kicks", butt_kicks), ("torso_twist", torso_twist), ("side_bend", side_bend),
    ("skater_step", skater_step), ("wall_pushup", wall_pushup), ("wall_sit", wall_sit),
    ("db_goblet_squat", goblet_squat), ("db_floor_press", floor_press), ("db_shrug", shrug), ("db_calf_raise", db_calf_raise),
    ("kb_swing", kb_swing), ("bench_dip", bench_dip),
    ("crunch", crunch), ("heel_taps", heel_taps), ("reverse_crunch", reverse_crunch), ("toe_taps", toe_taps),
    ("high_plank", high_plank), ("shoulder_taps", shoulder_taps), ("single_leg_bridge", single_leg_bridge),
    ("donkey_kick", donkey_kick), ("fire_hydrant", fire_hydrant), ("childs_pose", childs_pose), ("bear_hold", bear_hold),
)

RETIME = {n: (1.0, 1.0) for n in ("butt_kicks", "skater_step", "kb_swing", "high_plank", "bear_hold", "heel_taps", "torso_twist")}
RETIME.update({n: (1.4, 1.0) for n in ("single_leg_bridge", "side_bend", "single_leg_balance", "side_leg_raise", "glute_kickback", "donkey_kick", "fire_hydrant",
                                       "shoulder_taps", "toe_taps", "single_leg_rdl", "childs_pose", "wall_sit")})

PROPS = {
    "db_goblet_squat": ("dumbbell_goblet",), "db_floor_press": ("dumbbell_L", "dumbbell_R"), "db_shrug": ("dumbbell_L", "dumbbell_R"),
    "db_calf_raise": ("dumbbell_L", "dumbbell_R"), "kb_swing": ("kettlebell",), "bench_dip": ("bench_dip",),
    "wall_pushup": ("wall_front",), "wall_sit": ("wall_back",),
}

# contact rules for the rigged mesh pass (rigged_coach.CONTACTS)
CONTACTS = {
    "crunch": ("bridge",), "heel_taps": ("bridge",), "db_floor_press": ("bridge",), "single_leg_bridge": ("bridge",),
    "reverse_crunch": ("back",), "toe_taps": ("back",),
    "high_plank": ("hands",), "shoulder_taps": ("hands",), "bear_hold": ("hands",),
    "donkey_kick": ("kneel",), "fire_hydrant": ("kneel",), "childs_pose": ("kneel",),
}
LIFTING_HANDS = ("shoulder_taps",)
NO_FLOOR_CONTACT = {"reverse_crunch", "toe_taps"}
LIFE_FLOOR = ("crunch", "heel_taps", "reverse_crunch", "toe_taps", "high_plank", "shoulder_taps", "single_leg_bridge",
              "donkey_kick", "fire_hydrant", "childs_pose", "bear_hold", "db_floor_press")
