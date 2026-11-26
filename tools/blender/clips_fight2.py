"""Batch 7, fighting fundamentals (2026-11-24): 30 more boxing lessons, built on the validated stance in authored_clips.

Scope (CLAUDE.md): no kicks, no sparring or partner drills, combinations of at most three punches. Every clip starts
and ends in the same guard so it loops, like the earlier boxing clips.
"""
import math

from mathutils import Matrix

import authored_clips as ac
from authored_clips import V, frames, smooth, smoother, _stance_pose, _punch_curve, _phases

PC = _punch_curve


def _seq(r, st, T, fn):
    n = frames(T)
    return [fn(T * i / (n - 1), T) for i in range(n)]


def _punch(key, t, start, out, hold, back, lead=0.06):
    """(arm curve, hip curve): the hips lead the fist a little (kinetic chain), as in the earlier punches."""
    return PC(t, start, out, hold, back), PC(t + lead, start, out, hold, back)


# ---------------------------------------------------------------------------------------------- body shots
def body_cross(r, st):
    """Cross to the body: the knees bend to drop the level first (no bending at the waist), then the straight right."""
    k = r.k

    def f(t, T):
        lv = PC(t, 0.25, 0.40, 0.80, 0.55)
        c, ch = _punch("e_cross", t, 0.45, 0.45, 0.15, 0.50, 0.08)
        return _stance_pose(r, st, t, e_cross=c, dip=0.85 * lv, cross_dz=-0.20 * k, loop=T, hip={"e_cross": ch})
    return _seq(r, st, 2.9, f)


def body_hook(r, st, rear=False):
    """Hook to the body: level drops with the knees, elbow lower than for the head hook, fist to the ribs."""
    k = r.k
    key = "e_rhook" if rear else "e_hook"

    def f(t, T):
        lv = PC(t, 0.25, 0.40, 0.85, 0.55)
        h, hh = _punch(key, t, 0.45, 0.45, 0.20, 0.55, 0.07)
        kw = {key: h, "dip": 0.85 * lv, "loop": T, "hip": {key: hh}}
        kw["rhook_dz" if rear else "hook_dz"] = -0.24 * k
        return _stance_pose(r, st, t, **kw)
    return _seq(r, st, 3.0, f)


def rear_body_hook(r, st):
    return body_hook(r, st, rear=True)


def jab_body_cross(r, st):
    """Jab to the head, then the cross to the body: the level drops as the jab comes home."""
    k = r.k

    def f(t, T):
        j, jh = _punch("e_jab", t, 0.30, 0.38, 0.08, 0.40, 0.05)
        lv = PC(t, 0.70, 0.40, 0.70, 0.55)
        c, ch = _punch("e_cross", t, 0.95, 0.45, 0.15, 0.50, 0.08)
        return _stance_pose(r, st, t, e_jab=j, e_cross=c, dip=0.8 * lv, cross_dz=-0.20 * k * smooth(min(1.0, lv * 1.5)), loop=T,
                            hip={"e_jab": jh, "e_cross": ch})
    return _seq(r, st, 3.2, f)


def body_head_jab(r, st):
    """Jab to the body, then jab to the head: down, back up, and the second jab follows as the level returns."""
    k = r.k

    def f(t, T):
        lv = PC(t, 0.25, 0.38, 0.55, 0.45)
        j1 = PC(t, 0.42, 0.38, 0.12, 0.40)
        j2 = PC(t, 1.45, 0.36, 0.10, 0.42)
        e = min(1.0, j1 + j2)
        dz = -0.20 * k if t < 1.38 else 0.0
        # (the target height is switched only while the hand is home in guard, so the arm never jumps)
        return _stance_pose(r, st, t, e_jab=e, dip=0.85 * lv, jab_dz=dz, loop=T,
                            hip={"e_jab": min(1.0, PC(t + 0.05, 0.42, 0.38, 0.12, 0.40) + PC(t + 0.05, 1.45, 0.36, 0.10, 0.42))})
    return _seq(r, st, 2.8, f)


# ---------------------------------------------------------------------------------------------- defence
def parry(r, st):
    """Rear-hand parry: a small tap across in front of the face, straight back to guard. Twice per clip."""
    def f(t, T):
        p = PC(t, 0.40, 0.28, 0.10, 0.38) + PC(t, 1.70, 0.28, 0.10, 0.38)
        return _stance_pose(r, st, t, e_parry=min(1.0, p), loop=T, bob_amp=0.6)
    return _seq(r, st, 3.0, f)


def catch(r, st):
    """Catch: the rear palm opens a hand's width in front of the face to take a jab, and returns. Twice per clip."""
    def f(t, T):
        c = PC(t, 0.40, 0.25, 0.25, 0.35) + PC(t, 1.75, 0.25, 0.25, 0.35)
        return _stance_pose(r, st, t, e_catch=min(1.0, c), loop=T, bob_amp=0.6)
    return _seq(r, st, 3.0, f)


def high_block(r, st):
    """High block (cover): both gloves up tight to the temples, elbows in, chin down; hold, then back to guard."""
    def f(t, T):
        c = PC(t, 0.40, 0.40, 0.60, 0.50)
        return _stance_pose(r, st, t, e_cover=c, loop=T, bob_amp=0.5)
    return _seq(r, st, 2.6, f)


def body_block(r, st):
    """Elbow block to the body: the lead elbow drops onto the ribs with a small crunch to that side; hold, back to guard."""
    def f(t, T):
        b = PC(t, 0.40, 0.42, 0.55, 0.50)
        return _stance_pose(r, st, t, e_bblock=b, loop=T, bob_amp=0.5)
    return _seq(r, st, 2.6, f)


def duck(r, st):
    """Duck: bend the knees straight down under an imaginary punch, eyes forward, hands up; back up to the stance."""
    def f(t, T):
        d = PC(t, 0.40, 0.40, 0.25, 0.50)
        return _stance_pose(r, st, t, dip=1.6 * d, loop=T, bob_amp=0.4)
    return _seq(r, st, 2.4, f)


def block_cross(r, st):
    """Cover, then answer with the cross as the gloves come down."""
    def f(t, T):
        cv = PC(t, 0.30, 0.38, 0.40, 0.42)
        c, ch = _punch("e_cross", t, 1.40, 0.42, 0.12, 0.50, 0.08)
        return _stance_pose(r, st, t, e_cover=cv, e_cross=c, loop=T, hip={"e_cross": ch})
    return _seq(r, st, 3.1, f)


def jab_slip(r, st):
    """Jab, then slip to the outside (head to the right) as it comes home, back to the middle."""
    def f(t, T):
        j, jh = _punch("e_jab", t, 0.30, 0.38, 0.10, 0.40, 0.05)
        sl = 0.85 * PC(t, 1.05, 0.38, 0.25, 0.45)
        return _stance_pose(r, st, t, e_jab=j, slip=sl, loop=T, hip={"e_jab": jh}, bob_amp=0.4)
    return _seq(r, st, 2.8, f)


def slip_cross(r, st):
    """Slip to the outside (head to the right), then the cross as the head comes back through the middle."""
    def f(t, T):
        sl = 0.85 * PC(t, 0.30, 0.38, 0.20, 0.50)
        c, ch = _punch("e_cross", t, 1.05, 0.42, 0.12, 0.50, 0.08)
        return _stance_pose(r, st, t, slip=sl, e_cross=c, loop=T, hip={"e_cross": ch}, bob_amp=0.4)
    return _seq(r, st, 2.8, f)


def roll_hook(r, st):
    """Roll under to the lead side (a U from right to left), then the lead hook as the body comes back up."""
    def f(t, T):
        x = _phases(t, [(0.35, 0, 0), (0.30, 0, 0.55), (0.85, 0.55, -0.6), (0.85, -0.6, 0), (0.85, 0, 0)])
        dip = _phases(t, [(0.55, 0, 0), (0.40, 0, 1), (0.45, 1, 0), (1.40, 0, 0)])
        h, hh = _punch("e_hook", t, 1.55, 0.42, 0.18, 0.55, 0.07)
        return _stance_pose(r, st, t, slip=x, dip=dip * 0.9, e_hook=h, loop=T, hip={"e_hook": hh}, bob_amp=0.3)
    return _seq(r, st, 3.2, f)


def pull_counter(r, st):
    """Pull back out of range, then come forward with the cross."""
    def f(t, T):
        p = PC(t, 0.30, 0.38, 0.25, 0.45)
        c, ch = _punch("e_cross", t, 1.05, 0.42, 0.12, 0.50, 0.08)
        return _stance_pose(r, st, t, pull=p, e_cross=c, loop=T, hip={"e_cross": ch}, bob_amp=0.4)
    return _seq(r, st, 2.8, f)


# ---------------------------------------------------------------------------------------------- combinations (max 3)
def _combo(r, st, T, punches):
    """punches: list of (key, start, out, hold, back, extra kwargs)."""
    lead = {"e_jab": 0.05, "e_cross": 0.08, "e_hook": 0.07, "e_rhook": 0.07, "e_lup": 0.07, "e_rup": 0.07}

    def f(t, T_):
        kw, hip = {}, {}
        for key, s0, o, h, b in punches:
            kw[key] = min(1.0, kw.get(key, 0.0) + PC(t, s0, o, h, b))          # (sum: max() leaves a corner)
            hip[key] = min(1.0, hip.get(key, 0.0) + PC(t + lead[key], s0, o, h, b))
        return _stance_pose(r, st, t, loop=T_, hip=hip, **kw)
    return _seq(r, st, T, f)


def jab_uppercut(r, st):
    """Jab, then the rear uppercut (1-6)."""
    return _combo(r, st, 2.9, [("e_jab", 0.30, 0.38, 0.10, 0.42), ("e_rup", 0.95, 0.48, 0.15, 0.55)])


def uppercut_hook(r, st):
    """Lead uppercut, then lead hook off the same hand (5-3)."""
    # the hook starts once the uppercut is home: both use the lead arm, and the hook's arm pose replaces the uppercut's
    # (overlapping them made the arm jump -- QC: forearm jerk ~1900 once the punch tempo was slowed)
    return _combo(r, st, 3.2, [("e_lup", 0.30, 0.46, 0.12, 0.45), ("e_hook", 1.47, 0.45, 0.18, 0.55)])


def hook_cross(r, st):
    """Lead hook, then the cross (3-2): the hips turn one way and back the other."""
    return _combo(r, st, 2.9, [("e_hook", 0.30, 0.42, 0.15, 0.45), ("e_cross", 1.05, 0.42, 0.12, 0.50)])


def cross_hook_cross(r, st):
    """Cross, lead hook, cross (2-3-2)."""
    return _combo(r, st, 3.7, [("e_cross", 0.30, 0.40, 0.10, 0.42), ("e_hook", 0.95, 0.42, 0.15, 0.48),
                               ("e_cross", 1.75, 0.42, 0.12, 0.50)])


def one_two_uppercut(r, st):
    """Jab, cross, lead uppercut (1-2-5)."""
    return _combo(r, st, 3.7, [("e_jab", 0.30, 0.38, 0.10, 0.40), ("e_cross", 0.92, 0.42, 0.12, 0.48),
                               ("e_lup", 1.70, 0.46, 0.15, 0.50)])


def uppercuts(r, st):
    """Lead uppercut, then rear uppercut (5-6)."""
    return _combo(r, st, 3.0, [("e_lup", 0.30, 0.46, 0.12, 0.45), ("e_rup", 1.10, 0.48, 0.15, 0.55)])


# ---------------------------------------------------------------------------------------------- rhythm and conditioning
def stance_bounce(r, st):
    """Light bounce on the balls of the feet in the stance, guard up -- rhythm, not jumping."""
    T = 2.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        g = 0.5 - 0.5 * math.cos(2 * math.pi * t / 0.60)          # four bounces per clip
        on = smoother(min(1.0, t / 0.3)) * smoother(min(1.0, (T - t) / 0.3))
        sp = _stance_pose(r, st, t, loop=T, bob_amp=0.2, bounce=on * (0.4 + 0.6 * g))
        sp["pos"] = sp["pos"] + V(0, 0, 0.008 * r.k * on * g)
        out.append(sp)
    return out


def fist_rolls(r, st):
    """Fist rolls in front of the chest (speed-bag style), stance kept; the fists circle round each other, steady."""
    k = r.k
    T = 2.4
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        on = smoother(min(1.0, t / 0.35)) * smoother(min(1.0, (T - t) / 0.35))
        ph = 2 * math.pi * t / 0.60                               # four turns per clip (at 0.4 s a turn the elbow jerk ran ~1800 m/s3)
        sp = _stance_pose(r, st, t, loop=T, bob_amp=0.6)
        base = sp["arms"]

        def arms(pts, ph=ph, on=on, base=base):
            res = base(pts)
            Hc = pts["head"]
            c = Hc + V(0.005 * k, -0.21 * k, -0.20 * k)       # (further out, the male fist left his reach once a turn)
            for s_, sg, off in (("L", 1.0, 0.0), ("R", -1.0, math.pi)):
                w = c + V(sg * 0.035 * k, 0.040 * k * math.sin(ph + off), 0.040 * k * math.cos(ph + off))
                # the guard's own elbow direction throughout, so the elbow only follows the fist (QC: blending to another
                # pole let it swing faster than the fist itself)
                tgt = {"w": w, "pole": res[s_]["pole"], "fingers": V(-sg * 1.0, -0.25, 0.1), "palm": V(0, 0.15, -1.0)}
                res[s_] = ac.mix_arm(res[s_], tgt, on)
            return res
        sp["arms"] = arms
        out.append(sp)
    return out


# ---------------------------------------------------------------------------------------------- footwork
def _push_steps(t, start=0.20):
    # quintic, slightly longer: the cubic started and stopped each 18 cm step with a jolt (QC: circle footwork knee jerk
    # ~730 m/s3 at the first frame of the step)
    first = smoother((t - start) / 0.38)
    second = smoother((t - start - 0.26) / 0.38)
    body = smoother((t - start + 0.02) / 0.60)
    return first, second, body, math.sin(math.pi * first), math.sin(math.pi * second)


def _turn_about(P, deg):
    return Matrix.Translation(P) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation(-P)


def _lateral_and_turn(r, st, direction, turn, T_step=1.6, T_turn=0.8):
    """Side push-step (direction +1 left, lead foot first; -1 right, rear foot first), then a turn on the ball of the
    lead foot to face the opponent again; the same back to the start, so the drill loops."""
    k = r.k
    step = 0.18 * k
    T = 2 * (T_step + T_turn)
    n = frames(T)
    base = _stance_pose(r, st, 0.0, loop=T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        if t < T_step:                                          # step out
            first, second, body, g1, g2 = _push_steps(t)
            lead_first = direction > 0
            sp = _stance_pose(r, st, t, travel_x=direction * step * body, bob_amp=0.0, loop=T,
                              lead_step=g1 if lead_first else g2, rear_step=g2 if lead_first else g1)
            for s_, prog in ((("L", first), ("R", second)) if lead_first else (("R", first), ("L", second))):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball + V(direction * step * (prog - body), 0, 0), yaw, pitch)
            a = 0.0
        elif t < T_step + T_turn:                               # turn on the lead foot
            u = (t - T_step) / T_turn
            a = turn * smoother(u)
            sp = _stance_pose(r, st, t, travel_x=direction * step, bob_amp=0.0, loop=T, rear_step=1.4 * math.sin(math.pi * smooth(u)))
        elif t < T_step + 2 * T_turn:                           # turn back
            u = (t - T_step - T_turn) / T_turn
            a = turn * (1.0 - smoother(u))
            sp = _stance_pose(r, st, t, travel_x=direction * step, bob_amp=0.0, loop=T, rear_step=1.4 * math.sin(math.pi * smooth(u)))
        else:                                                   # step back to the start
            tt = t - T_step - 2 * T_turn
            first, second, body, g1, g2 = _push_steps(tt)
            back_first_lead = direction < 0                     # the foot on the side of travel moves first
            sp = _stance_pose(r, st, t, travel_x=direction * step * (1 - body), bob_amp=0.0, loop=T,
                              lead_step=g1 if back_first_lead else g2, rear_step=g2 if back_first_lead else g1)
            for s_, prog in ((("L", first), ("R", second)) if back_first_lead else (("R", first), ("L", second))):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball - V(direction * step * (prog - body), 0, 0), yaw, pitch)
            a = 0.0
        if a:
            P = base["feet"]["L"][0] + V(direction * step, 0, 0)
            sp["world"] = _turn_about(P, a)
        out.append(sp)
    return out


def circle_left(r, st):
    """Circle left: push-step to the left (lead foot first), then turn on the lead foot to face the target again."""
    return _lateral_and_turn(r, st, 1.0, -22.0)


def circle_right(r, st):
    """Circle right: push-step to the right (rear foot first), then turn on the lead foot to face the target again."""
    return _lateral_and_turn(r, st, -1.0, 22.0)


def angle_step(r, st):
    """Angle step: a push-step forward and out to the left (off the centre line), a turn on the lead foot to face the
    target, then back the same way."""
    k = r.k
    sx, sy = 0.13 * k, 0.13 * k
    T_step, T_turn = 1.6, 0.8
    T = 2 * (T_step + T_turn)
    n = frames(T)
    base = _stance_pose(r, st, 0.0, loop=T)
    turn = -28.0
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        a = 0.0
        if t < T_step:
            first, second, body, g1, g2 = _push_steps(t)
            sp = _stance_pose(r, st, t, travel=sy * body, travel_x=sx * body, bob_amp=0.0, loop=T, lead_step=g1, rear_step=g2)
            for s_, prog in (("L", first), ("R", second)):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball + V(sx * (prog - body), -sy * (prog - body), 0), yaw, pitch)
        elif t < T_step + 2 * T_turn:
            u = (t - T_step) / T_turn
            a = turn * (smoother(u) if u < 1.0 else 1.0 - smoother(u - 1.0))
            uu = u if u < 1.0 else u - 1.0
            sp = _stance_pose(r, st, t, travel=sy, travel_x=sx, bob_amp=0.0, loop=T, rear_step=1.4 * math.sin(math.pi * smooth(uu)))
        else:
            tt = t - T_step - 2 * T_turn
            first, second, body, g1, g2 = _push_steps(tt)
            sp = _stance_pose(r, st, t, travel=sy * (1 - body), travel_x=sx * (1 - body), bob_amp=0.0, loop=T, lead_step=g2, rear_step=g1)
            for s_, prog in (("R", first), ("L", second)):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball - V(sx * (prog - body), -sy * (prog - body), 0), yaw, pitch)
        if a:
            P = base["feet"]["L"][0] + V(sx, -sy, 0)
            sp["world"] = _turn_about(P, a)
        out.append(sp)
    return out


def shuffle(r, st):
    """In and out: two quick, short push-steps forward and back, light on the feet, guard up."""
    k = r.k
    step = 0.14 * k
    T1 = 1.0
    out = []
    n = frames(T1)
    for rep in range(2):
        for direction in (1.0, -1.0):
            for i in range(n):
                if (rep or direction < 0) and i == 0:
                    continue
                t = T1 * i / (n - 1)
                first = smoother((t - 0.10) / 0.28)
                second = smoother((t - 0.30) / 0.28)
                body = smoother((t - 0.08) / 0.50)
                g1, g2 = math.sin(math.pi * first), math.sin(math.pi * second)
                tg = (rep * 2 + (0 if direction > 0 else 1)) * T1 + t
                if direction > 0:
                    sp = _stance_pose(r, st, tg, travel=step * body, lead_step=g1, rear_step=g2, bob_amp=0.0, loop=4 * T1, bounce=0.5)
                    for s_, prog in (("L", first), ("R", second)):
                        ball, yaw, pitch = sp["feet"][s_]
                        sp["feet"][s_] = (ball + V(0, -step * (prog - body), 0), yaw, pitch)
                else:
                    sp = _stance_pose(r, st, tg, travel=step * (1 - body), lead_step=g2, rear_step=g1, bob_amp=0.0, loop=4 * T1, bounce=0.5)
                    for s_, prog in (("R", first), ("L", second)):
                        ball, yaw, pitch = sp["feet"][s_]
                        sp["feet"][s_] = (ball + V(0, step * (prog - body), 0), yaw, pitch)
                out.append(sp)
    return out


def back_jab(r, st):
    """Jab while stepping back: the rear foot pushes back first, the jab lands as the lead foot follows; then a push-step
    forward to where it started."""
    k = r.k
    step = 0.18 * k
    T = 1.7
    n = frames(T)
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        first, second, body, g1, g2 = _push_steps(t)
        e = PC(t, 0.30, 0.34, 0.12, 0.45)
        sp = _stance_pose(r, st, t, e_jab=e, travel=-step * body, lead_step=g2, rear_step=g1, bob_amp=0.0, loop=2 * T,
                          hip={"e_jab": PC(t + 0.05, 0.30, 0.34, 0.12, 0.45)})
        for s_, prog in (("R", first), ("L", second)):
            ball, yaw, pitch = sp["feet"][s_]
            sp["feet"][s_] = (ball + V(0, step * (prog - body), 0), yaw, pitch)
        out.append(sp)
    for i in range(1, n):
        t = T * i / (n - 1)
        first, second, body, g1, g2 = _push_steps(t)
        sp = _stance_pose(r, st, T + t, travel=-step * (1 - body), lead_step=g1, rear_step=g2, bob_amp=0.0, loop=2 * T)
        for s_, prog in (("L", first), ("R", second)):
            ball, yaw, pitch = sp["feet"][s_]
            sp["feet"][s_] = (ball + V(0, -step * (prog - body), 0), yaw, pitch)
        out.append(sp)
    return out


def lateral_jab(r, st):
    """Side-step and jab: push-step to the left with a jab as the lead foot lands, then step back to the right."""
    k = r.k
    step = 0.18 * k
    T = 1.6
    n = frames(T)
    out = []
    for direction in (1.0, -1.0):
        for i in range(n):
            if direction < 0 and i == 0:
                continue
            t = T * i / (n - 1)
            first, second, body, g1, g2 = _push_steps(t)
            base_x = 0.0 if direction > 0 else step
            lead_first = direction > 0
            kw = {}
            if direction > 0:
                # the jab at the plain jab's beginner tempo (QC: at 0.34 s out the arm was extended only ~0.2 s and the
                # camera counter -- validated on the jab lessons -- missed two of three)
                kw = {"e_jab": PC(t, 0.20, 0.42, 0.16, 0.50), "hip": {"e_jab": PC(t + 0.05, 0.20, 0.42, 0.16, 0.50)}}
            sp = _stance_pose(r, st, t + (0 if direction > 0 else T), travel_x=base_x + direction * step * body, bob_amp=0.0, loop=2 * T,
                              lead_step=g1 if lead_first else g2, rear_step=g2 if lead_first else g1, **kw)
            for s_, prog in ((("L", first), ("R", second)) if lead_first else (("R", first), ("L", second))):
                ball, yaw, pitch = sp["feet"][s_]
                sp["feet"][s_] = (ball + V(direction * step * (prog - body), 0, 0), yaw, pitch)
            out.append(sp)
    return out


def jab_pivot(r, st):
    """Jab, then pivot on the lead foot (the rear foot swings round) to take an angle; pivot back."""
    T = 3.6
    n = frames(T)
    base = _stance_pose(r, st, 0.0, loop=T)
    P = base["feet"]["L"][0].copy()
    out = []
    for i in range(n):
        t = T * i / (n - 1)
        j, jh = _punch("e_jab", t, 0.25, 0.36, 0.10, 0.40, 0.05)
        a = 35.0 * _phases(t, [(1.05, 0, 0), (0.6, 0, 1), (0.5, 1, 1), (0.6, 1, 0), (0.85, 0, 0)])
        lift = 0.0
        for s0 in (1.05, 2.15):
            if s0 < t < s0 + 0.6:
                lift = math.sin(math.pi * smooth((t - s0) / 0.6))
        sp = _stance_pose(r, st, t, e_jab=j, hip={"e_jab": jh}, bob_amp=0.0, loop=T, rear_step=lift * 1.4)
        if a:
            sp["world"] = _turn_about(P, a)
        out.append(sp)
    return out


CLIPS = (
    ("boxing_body_cross", body_cross), ("boxing_body_hook", body_hook), ("boxing_rear_body_hook", rear_body_hook),
    ("boxing_jab_body_cross", jab_body_cross), ("boxing_body_head_jab", body_head_jab),
    ("boxing_parry", parry), ("boxing_catch", catch), ("boxing_high_block", high_block), ("boxing_body_block", body_block),
    ("boxing_duck", duck), ("boxing_block_cross", block_cross), ("boxing_jab_slip", jab_slip), ("boxing_slip_cross", slip_cross),
    ("boxing_roll_hook", roll_hook), ("boxing_pull_counter", pull_counter),
    ("boxing_jab_uppercut", jab_uppercut), ("boxing_uppercut_hook", uppercut_hook), ("boxing_hook_cross", hook_cross),
    ("boxing_cross_hook_cross", cross_hook_cross), ("boxing_one_two_uppercut", one_two_uppercut), ("boxing_uppercuts", uppercuts),
    ("boxing_stance_bounce", stance_bounce), ("boxing_fist_rolls", fist_rolls),
    ("footwork_circle_left", circle_left), ("footwork_circle_right", circle_right), ("footwork_angle_step", angle_step),
    ("footwork_shuffle", shuffle), ("boxing_back_jab", back_jab), ("boxing_lateral_jab", lateral_jab), ("boxing_jab_pivot", jab_pivot),
)

# rhythm drills keep their tempo (the default retime speeds holds up 2.2x)
RETIME = {n: (1.0, 1.0) for n in ("boxing_stance_bounce", "boxing_fist_rolls", "footwork_shuffle")}
