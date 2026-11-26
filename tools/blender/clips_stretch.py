"""Batch 8 (2026-11-26): cool-down stretches. Gentle positions held for a few breaths, one side then the other, authored
with the same rig solver and helpers as authored_clips / clips_fit2 (feet as IK targets, pelvis height from the legs,
the life layer added on write). Every clip starts and ends standing in the same position, so it loops.
"""
import math

from authored_clips import V, Ry, SIDES, frames, smooth, smoother, lerp, breath, torso_spec, hang, mix_arm, _stand
from clips_fit2 import _sides, _one_leg, _dir


def _hold_segs(st, go=1.2, hold=3.2, back=1.1):
    """Into the stretch, hold it for a few breaths, out of it."""
    tp = st["tempo"]
    return [(0.4, 0, 0), (go * tp, 0, 1), (hold, 1, 1), (back * tp, 1, 0), (0.4, 0, 0)]


def _reach(r, pts, s, a):
    """The arm target `a` pulled in along the line from the shoulder if it is beyond a comfortable reach (the male
    coach's arms are shorter relative to his frame: held hands would otherwise stop short and the elbow lock)."""
    S = pts["S_" + s]
    d = a["w"] - S
    lim = 0.975 * r.la
    if d.length > lim:
        a = dict(a)
        a["w"] = S + d.normalized() * lim
    return a


def _rest_arms(r, st):
    return lambda pts: {s: hang(r, pts, s, sg, out=st["arm_out"], fwd=0.03) for s, sg in SIDES}


# =============================================================================================== standing quad stretch
def quad_stretch(r, st):
    """Standing on one leg, the other heel comes up behind toward the seat and the same-side hand holds the ankle;
    knees side by side, chest tall; the other arm out a little for balance. Hold, lower, other side."""
    k = r.k

    def fn(side, e, t):
        g = smooth((e - 0.2) / 0.8) if e > 0.2 else 0.0
        ws = smooth(min(1.0, e / 0.3))

        def leg(Hj, g=g):
            K = Hj + _dir(-8.0 * g) * r.l1[side] * 0.999            # thigh straight down, a touch behind
            sh = -8.0 * g - 164.0 * g                                # shin folds right up behind: heel to the seat
            A = K + _dir(sh) * r.l2[side] * 0.999
            return A, _dir(sh + 90.0 - 70.0 * g)                     # foot pointed, toes up behind
        sp = _one_leg(r, st, t, side, g, ws, leg, pitch=2.0 + 3.0 * g, arms="out")
        sg = 1.0 if side == "L" else -1.0
        sp["kpole"][side] = V(sg * 0.05, -0.3, -1.0)                  # the knee points down, not forward
        A = r.ankle(side, sp["feet"][side])
        B = sp["feet"][side][0]                                       # the ball of the foot, up behind the seat
        rest = sp["arms"]

        def arms(pts, A=A, B=B, g=g):
            res = rest(pts)
            # the hand holds the top of the foot (the ankle is out of reach with a tall chest)
            hold = {"w": A.lerp(B, 0.8) + V(sg * 0.045 * k, 0.015 * k, 0.0), "pole": V(sg * 0.35, 1.0, -0.2),
                    "fingers": V(-sg * 0.3, -0.2, -1.0), "palm": V(-sg, 0.2, 0.0)}
            # the hand only goes to the foot once the foot is up near it (on the way the moving foot is out of reach)
            res[side] = mix_arm(res[side], _reach(r, pts, side, hold), smooth(max(0.0, (g - 0.55) / 0.45)))
            o = "R" if side == "L" else "L"
            res[o] = hang(r, pts, o, -sg, out=0.10 + 0.12 * g, fwd=0.04, reach=0.985)
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 1.4, 3.0, 1.2), fn)


# =============================================================================================== cross-body shoulder
def shoulder_stretch(r, st):
    """The arm comes straight across the chest at shoulder height; the other forearm draws it in just above the
    elbow; shoulders down. Hold, release, other side."""
    k = r.k

    def fn(side, e, t):
        sp = _stand(r, st, t, w=0.10, T=4.0)
        sg = 1.0 if side == "L" else -1.0
        o = "R" if side == "L" else "L"
        sp["che"] = Ry(0.0) @ sp["che"]

        def arms(pts, e=e):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            S = pts["S_" + side]
            d = V(-sg * 0.86, -0.50, -0.06).normalized()             # across the front of the chest
            W = S + d * (0.95 * r.la)
            across = {"w": W, "pole": V(sg * 0.1, -0.3, -1.0), "fingers": d, "palm": V(0.0, 1.0, 0.0)}
            res[side] = mix_arm(res[side], across, smooth(e))
            # the helping forearm presses on the arm just above the elbow, from in front
            E = S + d * (0.80 * r.a1[side])
            help_ = {"w": E + V(sg * 0.02 * k, -0.075 * k, -0.02 * k), "pole": V(-sg * 0.25, -0.2, -1.0),
                     "fingers": V(sg * 0.9, -0.1, 0.25).normalized(), "palm": V(0.0, 1.0, 0.0)}
            res[o] = mix_arm(res[o], help_, smooth(max(0.0, (e - 0.25) / 0.75)))
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 1.2, 3.2, 1.1), fn, order=("R", "L"))


# =============================================================================================== overhead triceps
def triceps_stretch(r, st):
    """One arm reaches up and bends so the hand drops behind the head toward the upper back; the other hand rests on
    the raised elbow and draws it gently back. Hold, release, other side."""
    k = r.k

    def fn(side, e, t):
        sp = _stand(r, st, t, w=0.10, pitch=0.0, T=4.0)
        sg = 1.0 if side == "L" else -1.0
        o = "R" if side == "L" else "L"

        def arms(pts, e=e):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            S = pts["S_" + side]
            E = S + V(sg * 0.035 * k, 0.03 * k, r.a1[side] * 0.97)                  # upper arm up beside the ear
            th = math.radians(150.0)
            fd = V(-sg * 0.30, math.sin(th), math.cos(th)).normalized()             # hand behind the head
            up = {"w": E + fd * r.a2[side] * 0.95, "pole": V(sg * 0.2, -0.3, 1.0), "fingers": fd,
                  "palm": V(-sg * 0.2, -1.0, 0.0)}
            res[side] = mix_arm(res[side], up, smooth(e))
            help_ = {"w": E + V(-sg * 0.045 * k, -0.02 * k, 0.025 * k), "pole": V(-sg * 0.5, -1.0, 0.3),
                     "fingers": V(sg * 0.8, 0.1, 0.4).normalized(), "palm": V(sg * 0.2, 0.0, -1.0)}
            res[o] = mix_arm(res[o], help_, smooth(max(0.0, (e - 0.3) / 0.7)))
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 1.3, 3.2, 1.2), fn, order=("R", "L"))


# =============================================================================================== chest opener
def chest_opener(r, st):
    """Hands meet behind the lower back, the shoulders draw back and the chest lifts a little, chin level; hold for a
    few breaths, release."""
    k = r.k
    segs = _hold_segs(st, 1.4, 3.6, 1.3)
    T = sum(d for d, _, _ in segs)
    n = frames(T)
    from authored_clips import _phases
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        e = _phases(t, segs)
        sp = _stand(r, st, t, w=0.10, pitch=0.0, T=4.0)
        b = breath(t, 4.0, 0.0)
        sp2 = torso_spec(sp["pos"], pitch=-1.0 * e, spine=0.5 - 2.0 * e, chest=-1.0 - 7.0 * e, head_pitch=1.0 - 2.0 * e,
                         br=b * (0.6 + 0.4 * e))
        for key in ("pel", "spi", "che", "nek", "hed", "shrug"):
            sp[key] = sp2[key]
        sp["prot"] = {"L": -6.0 * e, "R": -6.0 * e}                   # shoulder blades drawn back

        def arms(pts, e=e):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            H = pts["hips"]
            for s, s2 in SIDES:
                behind = {"w": H + V(s2 * 0.035 * k, 0.13 * k, 0.0), "pole": V(s2 * 0.8, 0.6, 0.1),
                          "fingers": V(-s2 * 0.7, 0.1, -0.7).normalized(), "palm": V(-s2 * 0.3, 1.0, 0.0)}
                res[s] = mix_arm(res[s], _reach(r, pts, s, behind), smooth(e))
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== half-kneeling hip flexor
def hip_flexor_stretch(r, st):
    """Step back into a half-kneel (the back knee lowers gently to the floor, the back foot rolls onto its laces), hips
    tuck under and press forward a little until the front of the back hip stretches, chest tall, hands on the front
    thigh; hold; up and step back in; other side."""
    k = r.k

    def fn(back, e, t):
        front = "L" if back == "R" else "R"
        fg = 1.0 if front == "L" else -1.0
        bg = -fg
        w = 0.095 * k * st["stance"]
        sp = _stand(r, st, t, w=0.10, T=4.0)
        home = dict(sp["feet"])
        step = smoother(min(1.0, e / 0.35))                        # the back foot steps back onto its ball
        low = smoother(max(0.0, (e - 0.35) / 0.55))                # down onto the knee
        push = smoother(max(0.0, (e - 0.9) / 0.1))                 # hips press forward into the stretch
        b = breath(t, 4.3, 0.0)
        # kneeling geometry: back knee on the floor behind the standing hip, the thigh tilted forward by tilt degrees
        tilt = math.radians(12.0 + 10.0 * push)
        Kb = V(bg * (w + 0.01 * k), r.P0.y + 0.30 * k, 0.055 * k)
        Hb = Kb + V(0, -r.l1[back] * math.sin(tilt), r.l1[back] * math.cos(tilt) * 0.998)
        pel_k = torso_spec(V(0, 0, 0), pitch=-3.0 * push)["pel"]
        pos_k = Hb - pel_k @ r.hj[back]
        Hf = pos_k + pel_k @ r.hj[front]
        ff_k = r.foot(front, fg * w, Hf.y - 0.86 * r.l1[front], fg * 6.0)
        Ab = Kb + V(0, r.l2[back] * math.cos(math.radians(6.0)), r.l2[back] * math.sin(math.radians(6.0)))
        fb_k = r.foot_toward(back, Ab, V(0, 1.0, -0.25), yaw=bg * 4.0)
        # stepping: the back foot to its ball behind, the front foot a little forward
        fb_step = r.foot(back, bg * w, r.ankle0[back].y + 0.55 * k, bg * 4.0, pitch=55.0)
        ff_step = r.foot(front, fg * w, lerp(r.ankle0[front].y, ff_k[0].y - (home[front][0].y - r.ankle0[front].y), 0.5), fg * 6.0)
        def blend(a, b_, u):
            return (a[0].lerp(b_[0], u), lerp(a[1], b_[1], u), lerp(a[2], b_[2], u))
        fb = blend(blend(home[back], fb_step, step), fb_k, low)
        ff = blend(blend(home[front], ff_step, step), ff_k, low)
        sp["feet"] = {front: ff, back: fb}
        sp["kpole"] = {front: V(0, -1, 0.1), back: V(0, -1, -0.4 - 0.6 * low)}
        # pelvis: standing -> over the stepped stance -> kneeling
        z_stand = r.fit_z(sp, 0.990)
        y_step = r.P0.y + 0.18 * k * step
        p_step = V(0, y_step, z_stand)
        pos = p_step.lerp(pos_k, low)
        sp2 = torso_spec(pos, pitch=lerp(1.0, -3.0 * push, low), spine=0.5, chest=-1.5 - 1.5 * push, head_pitch=1.5, br=b * 0.6)
        for key in ("pos", "pel", "spi", "che", "nek", "hed", "shrug"):
            sp[key] = sp2[key]
        if low < 0.999:
            sp["pos"].z = min(sp["pos"].z, r.fit_z(sp, 0.990)) if low < 0.05 else sp["pos"].z

        def arms(pts, low=low):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            Hm = pts["hips"]
            # both hands rest on the front thigh above the knee
            tgt = Hm + V(fg * 0.09 * k, -0.22 * k, 0.10 * k)
            for s, s2 in SIDES:
                on = {"w": tgt + V(s2 * 0.045 * k, 0.03 * k * (1 if s != front else -1), 0.0), "pole": V(s2 * 0.7, 1.0, -0.2),
                      "fingers": V(0, -1.0, -0.4).normalized(), "palm": V(0, 0, -1.0)}
                res[s] = mix_arm(res[s], _reach(r, pts, s, on), low)
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 2.2, 3.2, 2.0), fn, order=("R", "L"))


CLIPS = (
    ("quad_stretch", quad_stretch), ("shoulder_stretch", shoulder_stretch), ("triceps_stretch", triceps_stretch),
    ("chest_opener", chest_opener), ("hip_flexor_stretch", hip_flexor_stretch),
)
RETIME = {n: (1.0, 1.0) for n, _ in CLIPS}
