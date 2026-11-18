#!/usr/bin/env python3
"""
MOTIONFORGE trainer art sheets (original designs, drawn in code — no reference images, no real likeness).

Draws an orthographic turnaround (front / side / back), head close-ups, palette and build notes for
each trainer design. These sheets are the approved reference the Blender model is built from.

Units inside the figure drawings are centimetres, y up, floor at y = 0.
Usage: python tools/art/trainer_art_sheet.py   -> assets/blender/references/trainer_<id>_art_sheet.{svg,png}
"""
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "assets/blender/references")
LINE = "#101316"


# ----------------------------------------------------------------------------- geometry helpers
def spline(points, closed=True):
    """Catmull-Rom spline through points -> SVG path data."""
    n = len(points)
    if n < 3:
        return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points) + (" Z" if closed else "")
    d = [f"M{points[0][0]:.2f},{points[0][1]:.2f}"]
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = points[(i - 1) % n] if closed or i > 0 else points[i]
        p1, p2 = points[i], points[(i + 1) % n]
        p3 = points[(i + 2) % n] if closed or i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(d) + (" Z" if closed else "")


def mirror(points):
    return [(-x, y) for x, y in points]


def sym(right_side):
    """Closed symmetric outline from the right-hand side listed top to bottom."""
    return right_side + mirror(right_side)[::-1]


def limb(centres, widths):
    """Outline around a centre line with a full width at each centre point."""
    left, right = [], []
    for i, (c, w) in enumerate(zip(centres, widths)):
        a = centres[max(i - 1, 0)]
        b = centres[min(i + 1, len(centres) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy) or 1
        nx, ny = -dy / l, dx / l
        left.append((c[0] + nx * w / 2, c[1] + ny * w / 2))
        right.append((c[0] - nx * w / 2, c[1] - ny * w / 2))
    return left + right[::-1]


def along(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def path(d, fill, stroke=LINE, sw=0.38, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round" {extra}/>'


def shape(points, fill, **kw):
    return path(spline(points), fill, **kw)


def poly(points, fill, sw=0.38):
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z"
    return path(d, fill, sw=sw)


def hand_front(wr, direction, s, k, w, skin, shade, thumb=True):
    """Relaxed open hand seen from front/back: palm, four fingers, thumb on the body side."""
    dx, dy = direction
    nx, ny = -dy, dx  # across the hand
    out = []
    kn = (wr[0] + dx * 9.2 * k, wr[1] + dy * 9.2 * k)
    lengths = (6.6, 8.0, 7.4, 5.8)
    for i, L in enumerate(lengths):
        off = (i - 1.5) * 1.95 * k
        base = (kn[0] + nx * off - dx * 0.8, kn[1] + ny * off - dy * 0.8)
        fan = (i - 1.5) * 0.05
        tip = (base[0] + (dx + nx * fan) * L * k, base[1] + (dy + ny * fan) * L * k)
        out.append(shape(limb([base, along(base, tip, 0.5), tip], [1.9 * k, 1.8 * k, 1.5 * k]), skin, sw=0.28))
    if thumb:
        side = -s  # thumb toward the body
        t0 = (wr[0] + dx * 2.6 * k + nx * side * 0 - s * 2.4 * k, wr[1] + dy * 2.6 * k)
        t1 = (t0[0] - s * 2.6 * k + dx * 3.6 * k, t0[1] + dy * 4.2 * k)
        t2 = (t1[0] - s * 0.4 * k + dx * 3.0 * k, t1[1] + dy * 3.4 * k)
        out.append(shape(limb([t0, t1, t2], [3.0 * k, 2.4 * k, 1.7 * k]), skin, sw=0.28))
    out.append(shape(limb([wr, along(wr, kn, 0.45), kn], [w, w + 2.4 * k, 8.0 * k]), skin, sw=0.32))
    return "".join(out)


def stroke(points, sw=0.3, color=LINE, opacity=1.0):
    return f'<path d="{spline(points, closed=False)}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" opacity="{opacity}"/>'


# ----------------------------------------------------------------------------- designs
DESIGNS = {
    "a": dict(
        id="a", title="TRAINER A", tagline="Athletic male coach · calm, approachable, precise",
        height=180, head=23.2, head_w=7.7, neck_w=6.0, shoulder=21.5, chest=17.8, waist=14.6, hip=16.4,
        arm_w=(10.6, 9.8, 8.0, 8.6, 6.0), thigh=(16.9, 16.3, 12.6, 13.6, 9.4), leg_len_bias=0,
        chest_depth=11.8, back_depth=11.0, glute=12.2, bust=0.0,
        skin="#B8845F", skin_shade="#9C6C4B", hair="#1E1A18", top="#C8F542", top_shade="#A7D12B",
        bottom="#1B1F24", bottom_shade="#12151A", shoe="#F1F0EC", sole="#2B3138", accent="#C8F542", sock="#F1F0EC",
        hair_style="crop", bottom_style="shorts", top_style="tee",
        notes=["Fitted performance tee, volt lime", "Mid-thigh training shorts, charcoal", "Low ankle socks, white trainers with volt heel tab",
               "Short textured crop with low fade", "Neutral, friendly expression — no branding anywhere"],
    ),
    "b": dict(
        id="b", title="TRAINER B", tagline="Athletic female coach · focused, encouraging, light on her feet",
        height=169, head=22.0, head_w=7.2, neck_w=5.2, shoulder=18.6, chest=15.4, waist=12.2, hip=16.6,
        arm_w=(8.8, 8.0, 6.8, 7.2, 5.2), thigh=(17.0, 15.6, 11.6, 12.4, 8.4), leg_len_bias=0,
        chest_depth=10.2, back_depth=9.6, glute=12.6, bust=2.0,
        skin="#D9A988", skin_shade="#BE8C6B", hair="#3A2418", top="#FF7A45", top_shade="#E05F2C",
        bottom="#20252B", bottom_shade="#15191E", shoe="#F1F0EC", sole="#2B3138", accent="#FF7A45", sock="#F1F0EC",
        hair_style="ponytail", bottom_style="leggings", top_style="tank",
        notes=["Racer-back training tank, ember orange", "7/8 leggings, charcoal, flat waistband", "White trainers with ember heel tab",
               "Hair tied back in a high ponytail — keeps face and neck readable", "Neutral, friendly expression — no branding anywhere"],
    ),
}


def metrics(P):
    H = P["height"]
    top = H
    chin = H - P["head"]
    k = H / 180.0
    return dict(
        top=top, chin=chin, neck_base=chin - 5.5 * k, shoulder_y=chin - 11.5 * k, armpit=chin - 21 * k,
        chest_y=chin - 25 * k, waist_y=chin - 48 * k, hip_y=chin - 62 * k, crotch=chin - 72 * k,
        knee=H * 0.283, calf=H * 0.21, ankle=H * 0.05, k=k,
    )


# ----------------------------------------------------------------------------- head
def head_front(P, back=False):
    m = metrics(P)
    top, chin, w = m["top"], m["chin"], P["head_w"]
    hh = P["head"]
    u = hh / 23.0
    out = []
    eye_y = top - 11.6 * u
    # ears
    for s in (1, -1):
        out.append(shape([(s * (w - 0.1), eye_y + 1.6 * u), (s * (w + 1.25), eye_y + 1.2 * u), (s * (w + 1.1), eye_y - 2.0 * u),
                          (s * (w - 0.3), eye_y - 4.2 * u)], P["skin"]))
    jaw = [(0, top), (w * 0.7, top - 1.5 * u), (w * 0.98, top - 6.5 * u), (w, top - 11.5 * u), (w * 0.93, top - 16.2 * u),
           (w * 0.7, top - 20.3 * u), (w * 0.32, chin + 0.5 * u), (0, chin)]
    if P["bust"]:  # softer, slightly narrower jaw for design B
        jaw[5] = (w * 0.64, top - 20.3 * u)
    out.append(shape(sym(jaw), P["skin"]))
    if P["hair_style"] == "ponytail" and back:
        out.append(shape([(-2.6, top - 5 * u), (2.6, top - 5 * u), (3.4, top - 16 * u), (2.2, top - 30 * u), (0, top - 33 * u),
                          (-2.2, top - 30 * u), (-3.4, top - 16 * u)], P["hair"]))
    if back:
        nape = top - (17.5 if P["hair_style"] == "crop" else 16.5) * u
        out.append(shape(sym([(0, top + 1.2 * u), (w * 0.75, top + 0.2 * u), (w * 1.07, top - 5.5 * u), (w * 1.03, top - 11 * u),
                              (w * 0.8, nape + 1.5 * u), (w * 0.35, nape)]), P["hair"]))
        if P["hair_style"] == "crop":
            out.append(stroke([(-w * 0.9, top - 11.5 * u), (0, top - 12.6 * u), (w * 0.9, top - 11.5 * u)], 0.22, "#3a3431"))
        return "".join(out)
    # hair (front)
    if P["hair_style"] == "crop":
        hair = [(-w * 1.02, top - 10.5 * u), (-w * 1.08, top - 5 * u), (-w * 0.72, top + 0.5 * u), (0, top + 1.3 * u), (w * 0.72, top + 0.5 * u),
                (w * 1.08, top - 5 * u), (w * 1.02, top - 10.5 * u), (w * 0.9, top - 8 * u), (w * 0.72, top - 4.6 * u), (w * 0.2, top - 3.7 * u),
                (-w * 0.4, top - 4.2 * u), (-w * 0.74, top - 5.0 * u), (-w * 0.9, top - 8 * u)]
    else:
        hair = [(-w * 1.0, top - 11 * u), (-w * 1.06, top - 5 * u), (-w * 0.72, top + 0.5 * u), (0, top + 1.4 * u), (w * 0.72, top + 0.5 * u),
                (w * 1.06, top - 5 * u), (w * 1.0, top - 11 * u), (w * 0.9, top - 7.5 * u), (w * 0.62, top - 4.6 * u), (0, top - 3.6 * u),
                (-w * 0.62, top - 4.6 * u), (-w * 0.9, top - 7.5 * u)]
        out.append(shape([(-1.6, top + 0.8 * u), (0, top + 3.4 * u), (1.6, top + 0.8 * u)], P["hair"]))  # ponytail tie peeking
    out.append(shape(hair, P["hair"]))
    # face
    for s in (1, -1):
        ex = s * w * 0.42
        out.append(stroke([(ex - s * 1.9 * u, eye_y + 2.3 * u), (ex + s * 0.2 * u, eye_y + 2.75 * u), (ex + s * 1.9 * u, eye_y + 2.2 * u)], 0.62 * u, P["hair"]))
        out.append(shape([(ex - 1.55 * u, eye_y), (ex, eye_y + 0.72 * u), (ex + 1.55 * u, eye_y), (ex, eye_y - 0.6 * u)], "#F6F3EE", sw=0.22))
        out.append(f'<circle cx="{ex:.2f}" cy="{eye_y:.2f}" r="{0.62 * u:.2f}" fill="#2B211C"/>')
        out.append(stroke([(ex - 1.6 * u, eye_y + 0.1 * u), (ex, eye_y + 0.8 * u), (ex + 1.6 * u, eye_y + 0.1 * u)], 0.3))
    ny = top - 16.3 * u
    out.append(stroke([(-1.25 * u, ny + 0.3 * u), (-0.6 * u, ny - 0.35 * u), (0.6 * u, ny - 0.35 * u), (1.25 * u, ny + 0.3 * u)], 0.26))
    out.append(stroke([(0.55 * u, ny + 4.2 * u), (0.75 * u, ny + 1.5 * u)], 0.2, P["skin_shade"]))
    my = top - 19.0 * u
    out.append(stroke([(-2.2 * u, my + 0.12 * u), (-0.7 * u, my - 0.12 * u), (0.7 * u, my - 0.12 * u), (2.2 * u, my + 0.12 * u)], 0.3))
    out.append(stroke([(-1.0 * u, my - 1.05 * u), (0, my - 1.25 * u), (1.0 * u, my - 1.05 * u)], 0.2, P["skin_shade"]))
    return "".join(out)


def head_side(P):
    m = metrics(P)
    top, chin = m["top"], m["chin"]
    u = P["head"] / 23.0
    f = 1.0 if not P["bust"] else 0.96
    out = []
    if P["hair_style"] == "ponytail":
        out.append(shape([(-8.5 * u, top - 3.5 * u), (-12.5 * u, top - 2.5 * u), (-15.5 * u, top - 8 * u), (-15.5 * u, top - 20 * u), (-13 * u, top - 31 * u),
                          (-11.6 * u, top - 22 * u), (-11.5 * u, top - 11 * u), (-9.6 * u, top - 7.5 * u)], P["hair"]))
    face = [(0.5 * u, top), (6.4 * u, top - 2.4 * u), (8.5 * f * u, top - 7.4 * u), (8.3 * f * u, top - 10.4 * u), (9.4 * f * u, top - 13.2 * u),
            (10.7 * f * u, top - 15.2 * u), (8.7 * f * u, top - 16.5 * u), (9.0 * f * u, top - 18.1 * u), (8.5 * f * u, top - 19.5 * u),
            (8.4 * f * u, top - 21.3 * u), (7.0 * f * u, chin), (2.0 * u, chin + 0.9 * u), (-1.6 * u, top - 18.2 * u), (-4.5 * u, top - 15.6 * u),
            (-9.3 * u, top - 14.2 * u), (-10.9 * u, top - 8 * u), (-7.6 * u, top - 1.8 * u)]
    out.append(shape(face, P["skin"]))
    if P["hair_style"] == "crop":
        hair = [(7.0 * u, top - 3.4 * u), (3.6 * u, top - 4.8 * u), (2.0 * u, top - 8.4 * u), (1.2 * u, top - 12.4 * u), (-0.8 * u, top - 10.2 * u),
                (-3.0 * u, top - 11.6 * u), (-4.2 * u, top - 14.6 * u), (-9.4 * u, top - 13.8 * u), (-11.3 * u, top - 8 * u), (-8.2 * u, top - 1.0 * u),
                (0.5 * u, top + 1.2 * u), (5.8 * u, top - 0.8 * u)]
    else:
        hair = [(6.8 * u, top - 3.6 * u), (3.2 * u, top - 5.0 * u), (0.6 * u, top - 8.6 * u), (-2.4 * u, top - 10.8 * u), (-3.6 * u, top - 15.4 * u), (-5.6 * u, top - 16.4 * u),
                (-9.6 * u, top - 15.0 * u), (-11.4 * u, top - 8 * u), (-8.4 * u, top - 1.0 * u), (0.5 * u, top + 1.4 * u), (5.6 * u, top - 0.8 * u)]
    out.append(shape(hair, P["hair"]))
    ey = top - 11.6 * u
    out.append(shape([(-2.0 * u, ey + 1.4 * u), (-0.2 * u, ey + 0.6 * u), (-0.6 * u, ey - 2.6 * u), (-2.2 * u, ey - 3.6 * u), (-3.2 * u, ey - 1.2 * u)], P["skin"]))
    out.append(stroke([(-2.2 * u, ey + 0.2 * u), (-1.3 * u, ey - 0.6 * u), (-2.0 * u, ey - 2.2 * u)], 0.2, P["skin_shade"]))
    out.append(shape([(5.4 * f * u, ey), (6.6 * f * u, ey + 0.65 * u), (7.4 * f * u, ey), (6.6 * f * u, ey - 0.5 * u)], "#F6F3EE", sw=0.22))
    out.append(f'<circle cx="{6.9 * f * u:.2f}" cy="{ey:.2f}" r="{0.55 * u:.2f}" fill="#2B211C"/>')
    out.append(stroke([(5.0 * f * u, ey + 2.1 * u), (6.6 * f * u, ey + 2.7 * u), (8.0 * f * u, ey + 2.2 * u)], 0.6 * u, P["hair"]))
    out.append(stroke([(7.0 * f * u, top - 18.9 * u), (8.6 * f * u, top - 18.8 * u)], 0.28))
    return "".join(out)


# ----------------------------------------------------------------------------- body: front / back
def body_front(P, back=False):
    m = metrics(P)
    k = m["k"]
    S, C, W, Hp = P["shoulder"], P["chest"], P["waist"], P["hip"]
    t0, t1, t2, t3, t4 = P["thigh"]
    out = []
    knee, calf, ankle = m["knee"], m["calf"], m["ankle"]
    hip_y, crotch = m["hip_y"], m["crotch"]

    # ---- legs (skin)
    leg = [(Hp, hip_y), (t0, hip_y - 9 * k), (t1 * 0.97, (crotch + knee) / 2), (t2, knee), (t3, calf), (t4 + 0.4, ankle + 6 * k), (t4, ankle),
           (5.6, ankle), (5.2, ankle + 6 * k), (4.3, calf), (4.9, knee), (2.6, (crotch + knee) / 2 + 4 * k), (1.0, crotch)]
    for s in (1, -1):
        out.append(shape([(s * x, y) for x, y in leg], P["skin"]))
        out.append(stroke([(s * (t2 - 1.6), knee + 2.2 * k), (s * (t2 - 3.6), knee + 0.6 * k), (s * (t2 - 6.0), knee + 2.0 * k)], 0.2, P["skin_shade"]))
    # ---- socks + shoes
    for s in (1, -1):
        out.append(shape([(s * 5.3, ankle + 4.5 * k), (s * (t4 + 0.5), ankle + 4.5 * k), (s * (t4 + 0.3), ankle - 1), (s * 5.4, ankle - 1)], P["sock"], sw=0.3))
        if back:
            shoe = [(s * 4.4, ankle + 1.2), (s * 7.4, ankle + 2.6), (s * 10.8, ankle + 1.2), (s * 11.6, 2.2), (s * 11.0, 0.2), (s * 4.6, 0.2), (s * 3.8, 2.2)]
        else:
            shoe = [(s * 4.6, ankle + 1.0), (s * 7.6, ankle + 2.4), (s * 10.6, ankle + 1.0), (s * 12.4, 3.0), (s * 12.2, 0.2), (s * 4.2, 0.2), (s * 3.6, 3.0)]
        out.append(shape(shoe, P["shoe"]))
        out.append(path(f"M{s * 3.9:.2f},1.5 L{s * 12.2:.2f},1.5 L{s * 12.2:.2f},0.1 L{s * 4.0:.2f},0.1 Z", P["sole"], sw=0.3))
        if back:
            out.append(shape([(s * 6.6, ankle + 2.2), (s * 8.4, ankle + 2.2), (s * 8.2, ankle - 2.2), (s * 6.8, ankle - 2.2)], P["accent"], sw=0.25))
        else:
            out.append(stroke([(s * 6.0, ankle - 0.4), (s * 9.6, ankle - 0.4)], 0.22))
            out.append(stroke([(s * 5.8, ankle - 1.9), (s * 10.2, ankle - 1.9)], 0.22))
    # ---- bottoms
    waist_y = m["waist_y"] - 7 * k
    if P["bottom_style"] == "shorts":
        hem = (crotch + knee) / 2 + 3 * k
        r = [(W + 0.4, waist_y), (Hp + 0.9, hip_y), (t0 + 1.3, hip_y - 9 * k), (t1 + 1.2, hem + 1), (t1 + 1.0, hem), (2.2, hem + 0.6), (1.0, hem + 6 * k), (0, crotch - 1.0)]
        out.append(shape(r + mirror(r)[::-1][1:], P["bottom"]))
        for s in (1, -1):
            out.append(stroke([(s * (t1 + 0.6), hem + 1.4), (s * 2.6, hem + 2.0)], 0.2, "#3A424B"))
    else:
        hem = ankle + 9 * k
        r = [(W + 0.3, waist_y), (Hp + 0.9, hip_y), (t0 + 0.7, hip_y - 9 * k), (t1 * 0.97 + 0.25, (crotch + knee) / 2), (t2 + 0.25, knee), (t3 + 0.25, calf),
             (t4 + 1.6, hem), (5.0, hem), (4.1, calf), (4.7, knee), (2.4, (crotch + knee) / 2 + 4 * k), (0.8, crotch + 0.5), (0, crotch - 0.6)]
        out.append(shape(r + mirror(r)[::-1][1:], P["bottom"]))
        for s in (1, -1):
            out.append(stroke([(s * (t2 - 1.6), knee + 2.2 * k), (s * (t2 - 3.6), knee + 0.6 * k), (s * (t2 - 6.0), knee + 2.0 * k)], 0.2, "#3A424B"))
    out.append(stroke([(-(W + 0.2), waist_y - 2.2), (0, waist_y - 2.6), (W + 0.2, waist_y - 2.2)], 0.22, "#3A424B"))
    if back:
        out.append(stroke([(0, hip_y + 2), (0, crotch + 1)], 0.2, "#3A424B"))

    # ---- arms (skin) — relaxed A-pose, 20 degrees from vertical
    ang = math.radians(20)
    sh_y = m["shoulder_y"]
    aw = P["arm_w"]
    ul, fl = 30.5 * k, 26.5 * k
    for s in (1, -1):
        sh = (s * (S - 2.2), sh_y - 1.5)
        el = (sh[0] + s * ul * math.sin(ang), sh[1] - ul * math.cos(ang))
        wr = (el[0] + s * fl * math.sin(ang * 0.8), el[1] - fl * math.cos(ang * 0.8))
        centres = [sh, along(sh, el, 0.45), el, along(el, wr, 0.3), wr]
        out.append(shape(limb(centres, aw), P["skin"]))
        hd = (math.sin(ang * 0.6) * s, -math.cos(ang * 0.6))
        out.append(hand_front(wr, hd, s, k, aw[4], P["skin"], P["skin_shade"], thumb=True))
        # sleeve
        if P["top_style"] == "tee":
            sl = limb([(sh[0] - s * 3.2, sh[1] - 0.6), along(sh, el, 0.24), along(sh, el, 0.5)], [aw[0] + 1.0, aw[0] + 1.5, aw[1] + 1.8])
            out.append(shape(sl, P["top"]))

    # ---- neck
    nb = m["neck_base"]
    nw = P["neck_w"]
    out.append(shape([(-nw, m["chin"] + 3.5), (nw, m["chin"] + 3.5), (nw + 0.6, nb + 1.5), (nw + 2.6, nb - 0.8), (-nw - 2.6, nb - 0.8), (-nw - 0.6, nb + 1.5)], P["skin"]))

    # ---- top
    hem_y = waist_y - 3.5
    if P["top_style"] == "tee":
        r = [(nw + 1.0, nb + 0.6), (S * 0.62, nb - 1.4), (S, sh_y + 0.4), (S + 0.4, sh_y - 5), (C + 0.6, m["armpit"]), (C - 0.2, m["chest_y"] - 8 * k),
             (W + 0.9, m["waist_y"]), (W + 1.3, hem_y)]
        out.append(shape(r + mirror(r)[::-1], P["top"]))
        if back:
            out.append(stroke([(-(nw + 1.0), nb + 0.4), (0, nb - 0.6), (nw + 1.0, nb + 0.4)], 0.26))
        else:
            out.append(shape([(-(nw + 1.2), nb + 0.8), (0, nb - 3.0), (nw + 1.2, nb + 0.8), (0, nb - 1.2)], P["skin"], sw=0.3))
    else:
        strap = nw + 3.6
        r = [(strap - 2.4, nb + 0.2), (strap + 0.6, nb - 0.2), (C - 2.6, m["armpit"] + 4 * k), (C + 0.2, m["armpit"] - 1.5), (C - 0.6, m["chest_y"] - 8 * k),
             (W + 0.5, m["waist_y"]), (W + 0.8, hem_y)]
        # skin of shoulders/chest under the tank
        sk = [(nw + 0.8, nb + 0.4), (S * 0.62, nb - 1.6), (S - 0.2, sh_y + 0.2), (S + 0.2, sh_y - 5), (C + 0.2, m["armpit"]), (C - 1.0, m["armpit"] - 6)]
        out.append(shape(sk + mirror(sk)[::-1], P["skin"]))
        neck_dip = nb - (2.0 if back else 6.5)
        full = r + mirror(r)[::-1]
        out.append(shape(full, P["top"]))
        out.append(shape([(-(strap - 2.2), nb + 0.6), (-(strap - 3.0), nb - 3), (0, neck_dip), (strap - 3.0, nb - 3), (strap - 2.2, nb + 0.6), (0, nb + 2.0)], P["skin"], sw=0.3))
        if back:
            out.append(shape([(-1.6, nb - 1.0), (1.6, nb - 1.0), (2.4, m["armpit"] + 2), (-2.4, m["armpit"] + 2)], P["top"], sw=0.3))
    # torso form lines
    if not back:
        out.append(stroke([(-C * 0.62, m["chest_y"] - 1.5), (-C * 0.2, m["chest_y"] - 3.4), (0, m["chest_y"] - 2.6)], 0.2, P["top_shade"]))
        out.append(stroke([(C * 0.62, m["chest_y"] - 1.5), (C * 0.2, m["chest_y"] - 3.4), (0, m["chest_y"] - 2.6)], 0.2, P["top_shade"]))
    else:
        out.append(stroke([(0, nb - 4), (0, m["waist_y"] + 4)], 0.2, P["top_shade"]))
        for s in (1, -1):
            out.append(stroke([(s * C * 0.3, m["armpit"] + 5), (s * C * 0.62, m["armpit"] + 1), (s * C * 0.55, m["chest_y"] - 3)], 0.2, P["top_shade"]))
    out.append(head_front(P, back))
    return "".join(out)


# ----------------------------------------------------------------------------- body: side (facing +x)
def body_side(P):
    m = metrics(P)
    k = m["k"]
    out = []
    knee, calf, ankle, hip_y, crotch = m["knee"], m["calf"], m["ankle"], m["hip_y"], m["crotch"]
    cd, bd, gl = P["chest_depth"], P["back_depth"], P["glute"]
    tw = P["thigh"][1] * 0.6
    # leg
    leg = [(cd * 0.78, hip_y), (tw, (crotch + knee) / 2 + 6 * k), (6.6, knee + 2 * k), (5.6, knee - 4 * k), (4.6, calf), (3.4, ankle + 4 * k), (3.6, ankle),
           (-4.6, ankle), (-4.4, ankle + 5 * k), (-8.4 * (P["thigh"][3] / 13.6), calf + 2 * k), (-5.6, knee), (-8.6, (crotch + knee) / 2 + 4 * k), (-gl, hip_y - 4 * k), (-gl * 0.8, hip_y + 6 * k)]
    out.append(shape(leg, P["skin"]))
    # sock + shoe
    out.append(shape([(-4.6, ankle + 4.5 * k), (3.6, ankle + 4.5 * k), (3.8, ankle - 1.5), (-4.8, ankle - 1.5)], P["sock"], sw=0.3))
    out.append(shape([(-5.6, ankle + 1.6), (-2.0, ankle + 2.2), (4.2, ankle + 1.4), (9.5, 5.0), (17.0, 3.4), (19.2, 1.6), (18.6, 0.2), (-6.6, 0.2), (-7.4, 3.2)], P["shoe"]))
    out.append(path("M-7.2,1.8 L19.2,1.6 L18.8,0.1 L-6.8,0.1 Z", P["sole"], sw=0.3))
    out.append(shape([(-7.0, ankle + 1.2), (-5.0, ankle + 1.8), (-4.6, ankle - 3.2), (-7.2, 2.6)], P["accent"], sw=0.25))
    for x in (5.2, 7.6, 10.0):
        out.append(stroke([(x, 5.9 - (x - 5.2) * 0.25), (x + 1.6, 3.6 - (x - 5.2) * 0.1)], 0.22))
    # bottoms
    waist_y = m["waist_y"] - 7 * k
    wf, wb = cd * 0.74 - P["bust"] * 0.6, bd * 0.6
    if P["bottom_style"] == "shorts":
        hem = (crotch + knee) / 2 + 3 * k
        b = [(wf, waist_y), (cd * 0.8 + 0.6, hip_y), (tw + 1.5, hem + 4), (tw + 1.4, hem), (-9.8, hem - 0.6), (-gl - 0.9, hip_y - 4 * k), (-gl * 0.82, hip_y + 6 * k), (-wb, waist_y)]
    else:
        hem = ankle + 9 * k
        b = [(wf, waist_y), (cd * 0.78 + 0.3, hip_y), (tw + 0.3, (crotch + knee) / 2 + 6 * k), (6.9, knee + 2 * k), (5.9, knee - 4 * k), (4.8, calf), (3.8, hem),
             (-4.9, hem), (-8.6 * (P["thigh"][3] / 13.6), calf + 2 * k), (-5.9, knee), (-8.9, (crotch + knee) / 2 + 4 * k), (-gl - 0.3, hip_y - 4 * k), (-gl * 0.82, hip_y + 6 * k), (-wb, waist_y)]
    out.append(shape(b, P["bottom"]))
    # neck
    nb = m["neck_base"]
    out.append(poly([(-6.4, m["chin"] + 7.0), (2.6, m["chin"] + 1.6), (3.9, nb - 0.5), (-7.2, nb + 1.0)], P["skin"]))
    # torso
    hem_y = waist_y - 3.5
    bust = P["bust"]
    torso = [(3.6, nb + 0.4), (cd * 0.7, nb - 5 * k), (cd + bust, m["chest_y"] - 1), (cd * 0.82 + bust * 0.3, m["chest_y"] - 10 * k), (wf + 0.6, m["waist_y"]), (wf + 0.9, hem_y),
             (-wb - 0.8, hem_y), (-wb - 0.4, m["waist_y"] + 2), (-bd, m["chest_y"] + 4 * k), (-bd * 0.92, nb - 4 * k), (-6.6, nb + 1.2)]
    out.append(shape(torso, P["top"]))
    if P["top_style"] == "tank":
        out.append(shape([(-4.0, nb + 1.4), (3.0, nb + 0.6), (2.0, m["armpit"] + 3), (-1.0, m["armpit"] - 2), (-4.8, m["armpit"] + 4)], P["skin"], sw=0.3))
    # arm
    aw = P["arm_w"]
    sh = (-1.2, m["shoulder_y"] - 2.0)
    el = (-2.2, sh[1] - 29.5 * k)
    wr = (1.0, el[1] - 25.5 * k)
    out.append(shape(limb([sh, along(sh, el, 0.45), el, along(el, wr, 0.3), wr], [aw[0] + 0.6, aw[1] + 0.4, aw[2], aw[3], aw[4]]), P["skin"]))
    kn = (wr[0] + 1.6, wr[1] - 9.4 * k)
    f1 = (kn[0] + 1.8, kn[1] - 4.6 * k)
    f2 = (f1[0] + 0.2, f1[1] - 3.4 * k)
    out.append(shape(limb([kn, f1, f2], [3.0 * k, 2.6 * k, 2.0 * k]), P["skin"], sw=0.3))
    out.append(shape(limb([wr, along(wr, kn, 0.5), kn], [aw[4], aw[4] + 1.0, 4.2 * k]), P["skin"], sw=0.32))
    t1 = (wr[0] + 3.4, wr[1] - 5.4 * k)
    out.append(shape(limb([(wr[0] + 1.2, wr[1] - 1.8 * k), t1, (t1[0] + 0.9, t1[1] - 3.4 * k)], [2.8 * k, 2.3 * k, 1.7 * k]), P["skin"], sw=0.28))
    if P["top_style"] == "tee":
        out.append(shape(limb([(sh[0], sh[1] + 2.2), along(sh, el, 0.24), along(sh, el, 0.5)], [aw[0] + 2.6, aw[0] + 2.4, aw[1] + 2.2]), P["top"]))
    out.append(head_side(P))
    return "".join(out)


# ----------------------------------------------------------------------------- sheet
def figure(svg, cx, floor, s):
    return f'<g transform="translate({cx},{floor}) scale({s},-{s})">{svg}</g>'


def text(x, y, t, size=26, weight=600, fill="#F2F4F5", family="Barlow Condensed", anchor="start", spacing=0):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}">{t}</text>'


def build_sheet(P):
    Wd, Ht = 1600, 2260
    s = 4.6
    floor = 1150
    m = metrics(P)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{Ht}" viewBox="0 0 {Wd} {Ht}">',
         f'<rect width="{Wd}" height="{Ht}" fill="#14181D"/>',
         f'<rect x="0" y="0" width="{Wd}" height="150" fill="#0B0D10"/>',
         text(60, 78, f'MOTIONFORGE · {P["title"]}', 58, 700, spacing=1),
         text(60, 120, P["tagline"], 26, 500, "#97A3AE", "Barlow"),
         text(Wd - 60, 78, "CHARACTER ART SHEET v1", 30, 600, P["accent"], anchor="end", spacing=2),
         text(Wd - 60, 120, "For approval before 3D modelling", 24, 500, "#97A3AE", "Barlow", anchor="end")]
    # head-unit guides
    for i in range(0, 9):
        y = floor - (P["height"] - i * P["head"]) * s
        if y > floor + 2:
            break
        o.append(f'<line x1="50" y1="{y:.1f}" x2="{Wd - 50}" y2="{y:.1f}" stroke="#2A323B" stroke-width="1.5" stroke-dasharray="4 8"/>')
        o.append(text(52, y - 6, f"{i}", 20, 600, "#5C6772"))
    o.append(f'<line x1="50" y1="{floor}" x2="{Wd - 50}" y2="{floor}" stroke="#5C6772" stroke-width="2.5"/>')
    for cx, label, svg in ((300, "FRONT", body_front(P)), (800, "SIDE", body_side(P)), (1300, "BACK", body_front(P, back=True))):
        o.append(figure(svg, cx, floor, s))
        o.append(text(cx, floor + 48, label, 30, 600, "#97A3AE", anchor="middle", spacing=3))
    o.append(text(Wd - 56, floor - P["height"] * s - 12, f'{P["height"]} cm · {P["height"] / P["head"]:.1f} heads', 22, 600, "#97A3AE", "Barlow", anchor="end"))

    # ---- lower panels
    y0 = 1260
    o.append(f'<rect x="50" y="{y0}" width="760" height="560" rx="22" fill="#0B0D10" stroke="#2A323B" stroke-width="2"/>')
    o.append(text(80, y0 + 48, "HEAD · FRONT AND SIDE", 28, 600, P["accent"], spacing=2))
    hs = 15.5
    hy = y0 + 500 + (m["chin"] - 9) * hs
    clip = f'<clipPath id="hc"><rect x="50" y="{y0 + 60}" width="760" height="498"/></clipPath>'
    o.append(clip)
    o.append(f'<g clip-path="url(#hc)">{figure(body_front(P), 250, hy, hs)}{figure(body_side(P), 610, hy, hs)}</g>')

    px = 850
    o.append(f'<rect x="{px}" y="{y0}" width="700" height="560" rx="22" fill="#0B0D10" stroke="#2A323B" stroke-width="2"/>')
    o.append(text(px + 30, y0 + 48, "COLOURS", 28, 600, P["accent"], spacing=2))
    sw = [("Skin", P["skin"]), ("Hair", P["hair"]), ("Top", P["top"]), ("Bottoms", P["bottom"]), ("Shoes", P["shoe"]), ("Sole", P["sole"])]
    for i, (name, col) in enumerate(sw):
        x = px + 30 + (i % 3) * 220
        y = y0 + 76 + (i // 3) * 118
        o.append(f'<rect x="{x}" y="{y}" width="196" height="66" rx="12" fill="{col}" stroke="#2A323B" stroke-width="2"/>')
        o.append(text(x, y + 92, f"{name} · {col.upper()}", 21, 500, "#C9D1D8", "Barlow"))
    o.append(text(px + 30, y0 + 348, "OUTFIT &amp; LOOK", 28, 600, P["accent"], spacing=2))
    for i, n in enumerate(P["notes"]):
        o.append(text(px + 30, y0 + 386 + i * 34, "•  " + n.replace("&", "&amp;"), 23, 400, "#E3E7EA", "Barlow"))

    y1 = 1860
    o.append(f'<rect x="50" y="{y1}" width="1500" height="340" rx="22" fill="#0B0D10" stroke="#2A323B" stroke-width="2"/>')
    o.append(text(80, y1 + 48, "HOW THE 3D MODEL WILL FOLLOW THIS SHEET", 28, 600, P["accent"], spacing=2))
    spec = ["Built from scratch in Blender — no base mesh, no scan, no real person's likeness.",
            "Silhouette, proportions and head-unit heights above are traced exactly from the front and side views.",
            "Real face: modelled eyes, brows, nose, lips and ears. Real hands: five separate fingers that can close into a fist.",
            "Clothing is its own geometry with thickness (hems, collar, waistband), not paint on the body.",
            "Shoes modelled with sole, heel tab and laces. Same skeleton and animation names as now, so the app needs no changes.",
            "Target: 25–35k triangles, flat colours plus soft shading — smooth on mid-range Android phones."]
    for i, n in enumerate(spec):
        o.append(text(80, y1 + 92 + i * 38, "•  " + n, 24, 400, "#E3E7EA", "Barlow"))
    o.append(text(Wd / 2, Ht - 22, "Original design drawn for MOTIONFORGE · draft for owner approval", 20, 500, "#5C6772", "Barlow", anchor="middle"))
    o.append("</svg>")
    return "".join(o)


if __name__ == "__main__":
    import cairosvg

    os.makedirs(OUT, exist_ok=True)
    for key, P in DESIGNS.items():
        svg = build_sheet(P)
        base = os.path.join(OUT, f"trainer_{key}_art_sheet")
        with open(base + ".svg", "w") as fh:
            fh.write(svg)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=base + ".png")
        print("wrote", base + ".png")
