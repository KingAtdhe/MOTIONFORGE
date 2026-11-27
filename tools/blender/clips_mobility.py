"""Batch 9 (2026-11-27): mobility. Leg swings, hip circles, a standing hamstring stretch, a squat hold and a calf
stretch, authored with the same rig solver and helpers as authored_clips / clips_fit2 / clips_stretch. Every clip
starts and ends standing in the same position, so it loops.
"""
import math

from authored_clips import V, SIDES, frames, smooth, smoother, lerp, breath, torso_spec, hang, mix_arm, _stand, _phases, _squat_pose
from clips_fit2 import _sides, _one_leg, _dir
from clips_stretch import _hold_segs, _reach


def _env(t, T, ramp=0.5):
    """0 -> 1 over `ramp` s at the start, 1 -> 0 over `ramp` s at the end."""
    return smoother(min(1.0, t / ramp)) * smoother(min(1.0, (T - t) / ramp))


# =============================================================================================== leg swings
def leg_swing(r, st):
    """Standing tall on one leg, the other leg swings forward and back from the hip like a pendulum, knee soft, in a
    controlled range (about 35 degrees forward, 20 back); four swings, then the other leg."""
    swings, Ts = 4, 1.15 * st["tempo"]
    lead, tail = 0.6, 0.6
    T1 = lead + swings * Ts + tail
    n = frames(T1)
    out = []
    for j, side in enumerate(("R", "L")):
        sg = 1.0 if side == "L" else -1.0
        for i in range(n):
            if j and i == 0:
                continue
            t = T1 * i / (n - 1)
            env = _env(t, T1, lead)
            ph = max(0.0, min(1.0, (t - lead * 0.5) / (T1 - lead * 0.5 - tail * 0.5)))
            # forward then back: a sine over the swings, a little more range forward than back
            s_ = math.sin(2.0 * math.pi * swings * ph)
            ang = (35.0 if s_ > 0 else 20.0) * s_ * env
            g = env
            ws = smooth(min(1.0, t / 0.45)) * smooth(min(1.0, (T1 - t) / 0.45))

            def leg(Hj, g, ang=ang, env=env):
                a = ang * (g / env if env > 1e-6 else 0.0)
                K = Hj + _dir(a) * r.l1[side] * 0.999
                A = K + _dir(a - 8.0 * g) * r.l2[side] * 0.999           # the knee stays a little soft
                return A, _dir(a + 80.0)
            sp = _one_leg(r, st, t + j * T1, side, g, ws, leg, pitch=1.0 - 3.0 * (ang / 35.0) * env, arms="out")
            sp["kpole"][side] = V(sg * 0.05, -1, 0)
            out.append(sp)
    return out


# =============================================================================================== hip circles
def hip_circles(r, st):
    """Feet a little wider than the hips, hands on the hips, knees soft: the hips draw slow circles, twice one way and
    twice the other, the head staying over the feet."""
    k = r.k
    Tc = 2.6 * st["tempo"]
    lead = 0.5
    T = lead + 4 * Tc + lead
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        env = _env(t, T, lead + 0.3)
        u = max(0.0, min(4.0, (t - lead) / Tc))
        dirn = 1.0 if u < 2.0 else -1.0
        a = 2.0 * math.pi * u * dirn
        dx, dy = math.sin(a) * env, -math.cos(a) * env              # env brings it in from and back to centre
        sp = _stand(r, st, t, w=0.13, toe=8.0, pitch=1.0, T=4.3)
        rad = 0.055 * k
        sp2 = torso_spec(V(dx * rad, sp["pos"].y + dy * rad, 0), roll=-dx * 6.0, pitch=1.0 - dy * 7.0, spine=0.5 + dy * 3.0,
                         chest=-1.0 + dy * 2.0, head_pitch=1.0 + dy * 3.0, br=breath(t, 4.3, 0.0) * 0.5)
        for key in ("pos", "pel", "spi", "che", "nek", "hed", "shrug"):
            sp[key] = sp2[key]
        r.fit_z(sp, 0.985)

        def arms(pts, env=smooth(min(1.0, t / 0.5)) * smooth(min(1.0, (T - t) / 0.5))):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            H = pts["hips"]
            for s, s2 in SIDES:
                on = {"w": H + V(s2 * 0.165 * k, 0.01 * k, 0.075 * k), "pole": V(s2 * 1.0, 0.4, 0.0),
                      "fingers": V(-s2 * 0.2, -0.5, -0.8).normalized(), "palm": V(-s2, 0.0, 0.0)}
                res[s] = mix_arm(res[s], _reach(r, pts, s, on), env)
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# =============================================================================================== standing hamstring stretch
def hamstring_stretch(r, st):
    """One heel steps forward with the toes up and the leg long; the back knee bends, the hips sit back and the flat
    back tips forward from the hips, hands resting on the front thigh, until the back of the front leg stretches;
    hold; step back in; other side."""
    k = r.k

    def fn(front, e, t):
        fg = 1.0 if front == "L" else -1.0
        w = 0.095 * k * st["stance"]
        sp = _stand(r, st, t, w=0.10, T=4.0)
        home = dict(sp["feet"])
        step = smoother(min(1.0, e / 0.4))                 # the heel steps forward
        lean = smoother(max(0.0, (e - 0.3) / 0.7))          # sit back and tip forward
        A0 = r.ankle(front, home[front])
        Af = V(fg * w, A0.y - 0.34 * k, A0.z + 0.012 * k)   # heel down in front (the ankle a touch higher: toes up)
        A = A0.lerp(Af, step) + V(0, 0, 0.05 * k * math.sin(math.pi * step))
        toes = V(0, -0.72, 0.70 * lean + 0.10).normalized()
        flat = (r.foot_q(front, home[front][1], 0.0) @ r.fv[front]).normalized()
        sp["feet"][front] = r.foot_toward(front, A, flat.lerp(toes, step).normalized(), yaw=home[front][1])
        sp["kpole"][front] = V(fg * 0.05, -1, 0.15)
        b = breath(t, 4.0, 0.0)
        hinge = 34.0 * lean
        sp2 = torso_spec(V(0, r.P0.y + 0.10 * k * lean - 0.10 * k * step * (1 - lean), 0), pitch=1.0 + hinge * 0.92,
                         spine=hinge * 0.04, chest=hinge * 0.03 - 1.0, head_pitch=2.0 + hinge * 0.75, br=b * 0.5)
        for key in ("pos", "pel", "spi", "che", "nek", "hed", "shrug"):
            sp[key] = sp2[key]
        r.fit_z(sp, 0.985)

        def arms(pts, lean=lean):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            Hf = pts["hips"] + V(fg * 0.09 * k, 0, 0)
            Kf = Hf.lerp(r.ankle(front, sp["feet"][front]), 0.42)       # on the thigh above the knee
            for s, s2 in SIDES:
                on = {"w": Kf + V(s2 * 0.04 * k, -0.03 * k, 0.05 * k), "pole": V(s2 * 0.8, 0.6, -0.1),
                      "fingers": V(0, -0.6, -0.8).normalized(), "palm": V(0, 0.2, -1.0)}
                res[s] = mix_arm(res[s], _reach(r, pts, s, on), lean)
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 1.6, 3.2, 1.4), fn)


# =============================================================================================== squat hold
def squat_hold(r, st):
    """Feet wider than the hips, toes turned out, sit down into a deep squat (as low as is comfortable) with the chest
    up and the palms together, elbows gently pressing the knees out; breathe there; stand up slowly."""
    segs = [(0.4, 0, 0), (2.2 * st["tempo"], 0, 1), (3.4, 1, 1), (1.9 * st["tempo"], 1, 0), (0.4, 0, 0)]
    T = sum(d for d, _, _ in segs)
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        u = _phases(t, segs)
        out.append(_squat_pose(r, st, u, 1.0, t, width=1.35, toe=28.0, lean_max=26.0, shin=38.0, arms_mode="chest"))
    return out


# =============================================================================================== calf stretch
def calf_stretch(r, st):
    """One foot steps back, its heel pressed down and the leg long; the front knee bends and the body leans forward in
    one line with the back leg, hands on the front thigh, until the back calf stretches; hold; step in; other side."""
    k = r.k

    def fn(back, e, t):
        front = "L" if back == "R" else "R"
        bg = 1.0 if back == "L" else -1.0
        fg = -bg
        w = 0.095 * k * st["stance"]
        sp = _stand(r, st, t, w=0.10, T=4.0)
        home = dict(sp["feet"])
        step = smoother(min(1.0, e / 0.45))
        lean = smoother(max(0.0, (e - 0.35) / 0.65))
        Ab0 = r.ankle(back, home[back])
        fb = r.foot(back, bg * w * 1.05, Ab0.y + 0.50 * k * step, bg * 6.0, lift=0.05 * k * math.sin(math.pi * step))
        sp["feet"][back] = fb
        sp["kpole"] = {front: V(fg * 0.10, -1, 0), back: V(bg * 0.05, -1, 0)}
        b = breath(t, 4.0, 0.0)
        tilt = 17.0 * lean                                          # body in line with the back leg
        # the hips stay between the feet and move a little forward over the bending front knee (further back, the
        # back knee bent -- first render)
        sp2 = torso_spec(V(0, r.P0.y + 0.10 * k * step - 0.05 * k * lean, 0), pitch=1.0 + tilt, spine=0.5, chest=-1.0,
                         head_pitch=2.0 + tilt * 0.6, br=b * 0.5)
        for key in ("pos", "pel", "spi", "che", "nek", "hed", "shrug"):
            sp[key] = sp2[key]
        r.fit_z(sp, 0.990)                                          # the long back leg sets the height

        def arms(pts, lean=lean):
            res = {s: hang(r, pts, s, s2, out=st["arm_out"], fwd=0.03) for s, s2 in SIDES}
            Hf = pts["hips"] + V(fg * 0.09 * k, -0.02 * k, 0)
            on_ = Hf + V(0, -0.20 * k, -0.17 * k)                        # on the front thigh
            for s, s2 in SIDES:
                on = {"w": on_ + V(s2 * 0.045 * k, 0, 0), "pole": V(s2 * 0.8, 0.6, -0.1),
                      "fingers": V(0, -0.6, -0.8).normalized(), "palm": V(0, 0.2, -1.0)}
                res[s] = mix_arm(res[s], _reach(r, pts, s, on), lean)
            return res
        sp["arms"] = arms
        return sp
    return _sides(r, st, _hold_segs(st, 1.6, 3.2, 1.4), fn)


CLIPS = (
    ("leg_swing", leg_swing), ("hip_circles", hip_circles), ("hamstring_stretch", hamstring_stretch),
    ("squat_hold", squat_hold), ("calf_stretch", calf_stretch),
)
RETIME = {n: (1.0, 1.0) for n, _ in CLIPS}
