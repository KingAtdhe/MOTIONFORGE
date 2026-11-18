#!/usr/bin/env python3
"""
MOTIONFORGE trainer character model sheets, rev. 2 (original designs drawn in code; no reference
images, no real person's likeness).

Each sheet: shaded orthographic turnaround (front / side / back) on a head-unit grid, head studies
with expressions, detail studies, palette and build notes.
Figure units: centimetres, y up, floor at y = 0. Light comes from the upper left.

Usage: python tools/art/trainer_model_sheet.py
Writes assets/blender/references/trainer_<id>_art_sheet.svg (render to PNG with headless Chromium).
"""
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "assets/blender/references")
_uid = [0]


def uid():
    _uid[0] += 1
    return f"u{_uid[0]}"


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(ra[i] + (rb[i] - ra[i]) * t):02X}" for i in range(3))


def dark(c, t=0.45):
    return mix(c, "#0C0A12", t)


def light(c, t=0.3):
    return mix(c, "#FFFFFF", t)


def spline(points, closed=True):
    n = len(points)
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
    return right_side + mirror(right_side)[::-1]


def flip(points, s):
    return [(s * x, y) for x, y in points]


def limb(centres, widths):
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


def part(points, fill, depth=1.5, ao=(), line=None, sw=0.3, shade=0.55, flat=False):
    """Shaded form: base colour, soft form light, core-shadow crescent away from the light,
    optional occlusion blobs [(x, y, rx, ry, opacity)], then a tinted outline."""
    d = spline(points)
    line = line or dark(fill, 0.55)
    if flat:
        return f'<path d="{d}" fill="{fill}" stroke="{line}" stroke-width="{sw}" stroke-linejoin="round"/>'
    c = uid()
    o = [f'<clipPath id="{c}"><path d="{d}"/></clipPath>', f'<path d="{d}" fill="{fill}"/>', f'<g clip-path="url(#{c})">',
         f'<g filter="url(#soft)"><path d="{d}" fill="{dark(fill, 0.42)}" opacity="{shade}"/>'
         f'<path d="{d}" fill="{fill}" transform="translate({-depth:.2f},{depth * 0.55:.2f})"/></g>',
         f'<path d="{d}" fill="url(#formlight)"/>']
    for (x, y, rx, ry, op) in ao:
        o.append(f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" fill="{dark(fill, 0.6)}" opacity="{op}" filter="url(#blur)"/>')
    o.append("</g>")
    o.append(f'<path d="{d}" fill="none" stroke="{line}" stroke-width="{sw}" stroke-linejoin="round"/>')
    return "".join(o)


def ln(points, color, sw=0.22, op=1.0):
    return f'<path d="{spline(points, closed=False)}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" opacity="{op}"/>'


def blob(points, fill, op=1.0, blur=False):
    f = ' filter="url(#blur)"' if blur else ""
    return f'<path d="{spline(points)}" fill="{fill}" opacity="{op}"{f}/>'


def circ(x, y, r, fill, op=1.0):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" opacity="{op}"/>'


DEFS = ('<defs><filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="0.55"/></filter>'
        '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.4"/></filter>'
        '<filter id="ground" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="2.2"/></filter>'
        '<linearGradient id="formlight" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.16"/>'
        '<stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity="0.12"/></linearGradient></defs>')

DESIGNS = {
    "a": dict(
        id="a", title="TRAINER A", role="Lead coach — fitness", tagline="Calm, precise, approachable. Demonstrates every movement slowly and cleanly.",
        height=180, head=24.4, head_w=8.1, neck_w=6.3, shoulder=20.6, chest=17.6, waist=14.6, hip=16.6, limb_k=1.0,
        thigh=(17.4, 16.6, 13.4, 12.6, 13.9, 9.0), chest_depth=11.6, back_depth=11.4, glute=12.0, bust=0.0, female=False,
        skin="#B97F5C", hair="#211A17", iris="#4A2E1F", top="#C6F03C", bottom="#22272E", panel="#2F363F", shoe="#F4F2EE", sole="#D9D5CE",
        outsole="#2A2F36", accent="#C6F03C", sock="#F4F2EE", hair_style="crop", bottom_style="shorts", top_style="tee",
        palette=[("Skin", "skin"), ("Hair", "hair"), ("Tee", "top"), ("Shorts", "bottom"), ("Trainers", "shoe"), ("Outsole", "outsole")],
        callouts=[("Textured crop, low fade", (4, 178), (-235, -30)), ("Fitted performance tee\nribbed crew collar", (-10, 128), (-235, 20)),
                  ("Mid-thigh shorts\nside panel, drawcord", (12, 88), (215, 10)), ("Low sock", (9.5, 12), (215, -40)),
                  ("Lightweight trainer\nvolt heel tab", (-8, 3), (-235, -10))],
    ),
    "b": dict(
        id="b", title="TRAINER B", role="Lead coach — fighting fundamentals", tagline="Focused and encouraging. Light on her feet, relaxed guard, clear rhythm.",
        height=170, head=23.4, head_w=7.5, neck_w=5.3, shoulder=17.8, chest=15.0, waist=12.0, hip=16.4, limb_k=0.84,
        thigh=(17.2, 15.8, 12.2, 11.4, 12.4, 8.0), chest_depth=10.0, back_depth=9.8, glute=12.4, bust=2.2, female=True,
        skin="#DDAA88", hair="#3B2317", iris="#3E5A45", top="#FF7440", bottom="#22272E", panel="#2F363F", shoe="#F4F2EE", sole="#D9D5CE",
        outsole="#2A2F36", accent="#FF7440", sock="#F4F2EE", hair_style="ponytail", bottom_style="leggings", top_style="tank",
        palette=[("Skin", "skin"), ("Hair", "hair"), ("Tank", "top"), ("Leggings", "bottom"), ("Trainers", "shoe"), ("Outsole", "outsole")],
        callouts=[("High ponytail", (3, 168), (-235, -30)), ("Racer-back tank\nbound armholes", (-8, 122), (-235, 20)),
                  ("7/8 leggings\nhigh waistband", (12, 70), (215, 10)), ("No-show sock", (8.5, 12), (215, -40)),
                  ("Lightweight trainer\nember heel tab", (-8, 3), (-235, -10))],
    ),
}


def metrics(P):
    H = P["height"]
    chin = H - P["head"]
    k = H / 180.0
    return dict(top=H, chin=chin, neck_base=chin - 6.6 * k, shoulder_y=chin - 9.0 * k, armpit=chin - 19.5 * k, chest_y=chin - 23.5 * k,
                waist_y=chin - 43.5 * k, hip_y=chin - 61.5 * k, crotch=chin - 71 * k, knee=H * 0.282, calf=H * 0.205, ankle=H * 0.05, k=k)


def head_front(P, back=False, expr="neutral"):
    m = metrics(P)
    top, chin, w = m["top"], m["chin"], P["head_w"]
    u = P["head"] / 24.0
    skin, hair = P["skin"], P["hair"]
    sl = dark(skin, 0.5)
    o = []
    eye_y = top - 12.2 * u
    for s in (1, -1):
        o.append(part(flip([(w - 0.3, eye_y + 1.8 * u), (w + 1.35, eye_y + 1.5 * u), (w + 1.5, eye_y - 0.6 * u), (w + 0.9, eye_y - 2.8 * u), (w - 0.5, eye_y - 4.4 * u)], s), skin, depth=0.6))
        o.append(ln(flip([(w + 0.2, eye_y + 0.9 * u), (w + 0.85, eye_y + 0.2 * u), (w + 0.4, eye_y - 2.2 * u)], s), sl, 0.18, 0.7))
    jw = 0.66 if P["female"] else 0.74
    cw = 0.30 if P["female"] else 0.36
    skull = [(0, top), (w * 0.66, top - 1.6 * u), (w * 0.97, top - 6.4 * u), (w, top - 12 * u), (w * 0.95, top - 16.4 * u), (w * jw, top - 20.8 * u),
             (w * cw, chin + 0.7 * u), (0, chin)]
    if back:
        if P["hair_style"] == "ponytail":
            o.append(part([(-2.4, top - 4 * u), (2.4, top - 4 * u), (3.6, top - 14 * u), (3.0, top - 27 * u), (0.6, top - 34 * u), (-1.6, top - 31 * u), (-3.4, top - 16 * u)], hair, depth=1.0))
        o.append(part(sym(skull), skin))
        nape = top - (17.0 if P["hair_style"] == "crop" else 18.5) * u
        o.append(part(sym([(0, top + 1.1 * u), (w * 0.72, top + 0.2 * u), (w * 1.06, top - 5.6 * u), (w * 1.02, top - 11.5 * u), (w * 0.84, nape + 2.5 * u), (w * 0.4, nape)]), hair, depth=1.2))
        if P["hair_style"] == "crop":
            o.append(blob(sym([(0, top - 11.5 * u), (w * 0.98, top - 10.4 * u), (w * 0.84, nape + 2.3 * u), (w * 0.4, nape + 0.2)]), mix(hair, skin, 0.35), 0.55))
            o.append(ln([(-w * 0.95, top - 10.6 * u), (0, top - 11.8 * u), (w * 0.95, top - 10.6 * u)], dark(hair, 0.3), 0.2))
        else:
            o.append(part([(-2.0, top - 3.0 * u), (2.0, top - 3.0 * u), (1.6, top - 6.0 * u), (-1.6, top - 6.0 * u)], P["accent"], depth=0.4))
            for x in (-3.5, 0, 3.5):
                o.append(ln([(x, top - 0.5 * u), (x * 0.5, top - 3.2 * u)], light(hair, 0.25), 0.2, 0.5))
        return "".join(o)
    o.append(part(sym(skull), skin, depth=1.3, ao=[(0, chin + 0.4, w * 0.5, 1.0, 0.25)]))
    for s in (1, -1):
        o.append(blob(flip([(w * 0.55, eye_y - 3.2 * u), (w * 0.86, eye_y - 4.0 * u), (w * 0.72, eye_y - 7.6 * u), (w * 0.46, eye_y - 6.0 * u)], s), mix(skin, "#C4533F", 0.5), 0.16, blur=True))
    if P["hair_style"] == "crop":
        cap = [(-w * 1.0, top - 10.8 * u), (-w * 1.07, top - 5.2 * u), (-w * 0.74, top + 0.4 * u), (0, top + 1.25 * u), (w * 0.74, top + 0.4 * u), (w * 1.07, top - 5.2 * u),
               (w * 1.0, top - 10.8 * u), (w * 0.9, top - 7.6 * u), (w * 0.74, top - 4.9 * u), (w * 0.3, top - 3.9 * u), (-w * 0.3, top - 4.3 * u), (-w * 0.72, top - 5.3 * u), (-w * 0.9, top - 7.8 * u)]
        o.append(part(cap, hair, depth=1.0))
        for s in (1, -1):
            o.append(blob(flip([(w * 0.9, top - 7.6 * u), (w * 1.04, top - 7.0 * u), (w * 1.0, top - 10.8 * u)], s), mix(hair, skin, 0.45), 0.7))
        for x in (-4.6, -2.2, 0.4, 3.0, 5.2):
            o.append(ln([(x, top - 3.2 * u), (x + 0.6, top - 1.2 * u), (x + 1.7, top + 0.1 * u)], light(hair, 0.22), 0.26, 0.55))
    else:
        cap = [(-w * 0.99, top - 11.5 * u), (-w * 1.05, top - 5.2 * u), (-w * 0.72, top + 0.3 * u), (0, top + 1.1 * u), (w * 0.72, top + 0.3 * u), (w * 1.05, top - 5.2 * u),
               (w * 0.99, top - 11.5 * u), (w * 0.9, top - 7.4 * u), (w * 0.6, top - 4.7 * u), (0, top - 3.7 * u), (-w * 0.6, top - 4.7 * u), (-w * 0.9, top - 7.4 * u)]
        o.append(part([(-1.9, top + 0.4 * u), (-1.2, top + 3.2 * u), (1.2, top + 3.2 * u), (1.9, top + 0.4 * u)], hair, depth=0.4))
        o.append(part(cap, hair, depth=1.0))
        for x in (-5.0, -2.6, 0, 2.6, 5.0):
            o.append(ln([(x, top - 4.0 * u - abs(x) * 0.12), (x * 0.55, top - 1.0 * u), (x * 0.2, top + 0.8 * u)], light(hair, 0.25), 0.22, 0.5))
    bt = {"neutral": 0.0, "smile": 0.25, "focus": -0.5}[expr]
    sq = {"neutral": 1.0, "smile": 0.72, "focus": 0.85}[expr]
    for s in (1, -1):
        ex = s * w * 0.43
        o.append(blob([(ex - 2.3 * u, eye_y + 0.9 * u), (ex, eye_y + 2.0 * u), (ex + 2.3 * u, eye_y + 0.9 * u), (ex, eye_y - 0.4 * u)], dark(skin, 0.35), 0.25, blur=True))
        # inner corner toward the nose (-s), outer corner slightly raised
        eye = [(ex - s * 1.75 * u, eye_y - 0.08 * u), (ex - s * 0.6 * u, eye_y + 0.78 * u * sq), (ex + s * 0.8 * u, eye_y + 0.66 * u * sq), (ex + s * 1.8 * u, eye_y + 0.16 * u),
               (ex + s * 0.6 * u, eye_y - 0.56 * u * sq), (ex - s * 0.8 * u, eye_y - 0.5 * u * sq)]
        c = uid()
        o.append(f'<clipPath id="{c}"><path d="{spline(eye)}"/></clipPath><path d="{spline(eye)}" fill="#F7F3EC"/><g clip-path="url(#{c})">')
        o.append(circ(ex, eye_y + 0.08 * u, 0.88 * u, P["iris"]) + circ(ex, eye_y + 0.08 * u, 0.4 * u, "#120C0A") + circ(ex - 0.3 * u, eye_y + 0.38 * u, 0.2 * u, "#FFFFFF", 0.95))
        o.append(blob([(ex - 2 * u, eye_y + 1.0 * u), (ex + 2 * u, eye_y + 1.0 * u), (ex + 2 * u, eye_y + 0.42 * u), (ex - 2 * u, eye_y + 0.38 * u)], "#3A2A22", 0.25))
        o.append("</g>")
        o.append(ln([(ex - s * 1.85 * u, eye_y - 0.08 * u), (ex - s * 0.6 * u, eye_y + 0.84 * u * sq), (ex + s * 0.8 * u, eye_y + 0.72 * u * sq), (ex + s * 2.0 * u, eye_y + 0.24 * u)],
                    "#1B1210", 0.44 if P["female"] else 0.34))
        o.append(ln([(ex - s * 1.3 * u, eye_y - 0.5 * u * sq), (ex + s * 1.3 * u, eye_y - 0.45 * u * sq)], sl, 0.14, 0.6))
        o.append(ln([(ex - s * 1.5 * u, eye_y + 1.4 * u), (ex, eye_y + 1.75 * u), (ex + s * 1.6 * u, eye_y + 1.3 * u)], sl, 0.14, 0.5))
        bw = 0.5 if P["female"] else 0.78
        inner = (ex - s * 2.0 * u, eye_y + (2.35 + bt * 0.9) * u)
        peak = (ex + s * 0.7 * u, eye_y + (3.0 - bt * 0.2) * u)
        outer = (ex + s * 2.3 * u, eye_y + (2.35 - bt * 0.3) * u)
        o.append(f'<path d="{spline(limb([inner, peak, outer], [bw * u, bw * 0.9 * u, 0.18 * u]))}" fill="{hair}"/>')
    ny = top - 17.2 * u
    o.append(blob([(0.25 * u, eye_y + 1.4 * u), (1.0 * u, eye_y + 0.4 * u), (1.5 * u, ny + 0.9 * u), (0.7 * u, ny + 0.2 * u)], dark(skin, 0.35), 0.22, blur=True))
    o.append(f'<ellipse cx="0" cy="{ny - 0.5 * u:.2f}" rx="{1.5 * u:.2f}" ry="{0.55 * u:.2f}" fill="{dark(skin, 0.5)}" opacity="0.3" filter="url(#soft)"/>')
    for s in (1, -1):
        o.append(f'<ellipse cx="{s * 0.72 * u:.2f}" cy="{ny - 0.02 * u:.2f}" rx="{0.42 * u:.2f}" ry="{0.2 * u:.2f}" fill="{dark(skin, 0.68)}" opacity="0.8"/>')
        o.append(ln(flip([(1.35 * u, ny + 0.9 * u), (1.6 * u, ny + 0.25 * u), (1.2 * u, ny - 0.15 * u)], s), sl, 0.16, 0.6))
    o.append(circ(-0.3 * u, ny + 1.3 * u, 0.55 * u, "#FFFFFF", 0.10))
    my = top - 20.2 * u
    lip = mix(skin, "#A8433D", 0.5 if P["female"] else 0.32)
    mw = (2.5 if expr != "smile" else 3.0) * u
    cv = {"neutral": 0.18, "smile": 0.7, "focus": -0.05}[expr] * u
    o.append(blob([(-mw, my + cv), (-mw * 0.4, my + 0.62 * u), (0, my + 0.42 * u), (mw * 0.4, my + 0.62 * u), (mw, my + cv), (0, my - 0.1 * u)], lip, 0.95))
    o.append(blob([(-mw * 0.9, my + cv * 0.9), (0, my - 0.12 * u), (mw * 0.9, my + cv * 0.9), (mw * 0.45, my - 0.85 * u), (-mw * 0.45, my - 0.85 * u)], light(lip, 0.12), 0.95))
    o.append(ln([(-mw, my + cv), (-mw * 0.4, my - 0.02 * u), (0, my - 0.12 * u), (mw * 0.4, my - 0.02 * u), (mw, my + cv)], dark(lip, 0.5), 0.2))
    if expr == "smile":
        for s in (1, -1):
            o.append(ln(flip([(mw + 0.5 * u, my + cv + 0.7 * u), (mw + 0.9 * u, my + cv - 0.2 * u)], s), sl, 0.14, 0.6))
    o.append(blob([(-1.2 * u, my - 1.5 * u), (1.2 * u, my - 1.5 * u), (0, my - 2.0 * u)], dark(skin, 0.3), 0.2, blur=True))
    return "".join(o)


def head_side(P):
    m = metrics(P)
    top, chin = m["top"], m["chin"]
    u = P["head"] / 24.0
    skin, hair = P["skin"], P["hair"]
    sl = dark(skin, 0.5)
    f = 0.95 if P["female"] else 1.0
    o = []
    if P["hair_style"] == "ponytail":
        o.append(part([(-8.0 * u, top - 2.8 * u), (-12.6 * u, top - 1.6 * u), (-16.2 * u, top - 7 * u), (-16.6 * u, top - 19 * u), (-14.6 * u, top - 31 * u), (-12.4 * u, top - 34 * u),
                       (-12.2 * u, top - 22 * u), (-11.8 * u, top - 11 * u), (-9.8 * u, top - 6.5 * u)], hair, depth=1.2))
    face = [(0.5 * u, top), (6.2 * u, top - 2.2 * u), (8.7 * f * u, top - 7.0 * u), (8.9 * f * u, top - 9.6 * u), (8.3 * f * u, top - 11.6 * u), (9.6 * f * u, top - 14.4 * u),
            (11.0 * f * u, top - 16.4 * u), (9.0 * f * u, top - 17.6 * u), (9.5 * f * u, top - 19.3 * u), (8.9 * f * u, top - 20.4 * u), (9.1 * f * u, top - 21.6 * u),
            (8.2 * f * u, top - 22.8 * u), (7.0 * f * u, chin), (2.4 * u, chin + 1.2 * u), (-1.8 * u, top - 18.6 * u), (-4.4 * u, top - 16.2 * u), (-9.4 * u, top - 14.6 * u),
            (-11.0 * u, top - 8.2 * u), (-7.8 * u, top - 1.8 * u)]
    o.append(part(face, skin, depth=1.3, ao=[(2.5 * u, chin + 1.5 * u, 5 * u, 1.6 * u, 0.3)]))
    o.append(blob([(3.6 * u, top - 15 * u), (6.6 * u, top - 15.4 * u), (5.6 * u, top - 19 * u), (3.2 * u, top - 18 * u)], mix(skin, "#C4533F", 0.5), 0.14, blur=True))
    if P["hair_style"] == "crop":
        cap = [(7.0 * u, top - 3.3 * u), (3.8 * u, top - 4.8 * u), (2.2 * u, top - 8.2 * u), (1.5 * u, top - 12.6 * u), (-0.6 * u, top - 10.6 * u), (-3.0 * u, top - 11.8 * u),
               (-4.4 * u, top - 16.0 * u), (-9.6 * u, top - 15.2 * u), (-11.4 * u, top - 8.2 * u), (-8.2 * u, top - 1.1 * u), (0.5 * u, top + 1.2 * u), (5.6 * u, top - 0.9 * u)]
        o.append(part(cap, hair, depth=1.1))
        o.append(blob([(1.9 * u, top - 9.0 * u), (-2.6 * u, top - 10.2 * u), (-11.0 * u, top - 10.0 * u), (-9.6 * u, top - 15.2 * u), (-4.4 * u, top - 16.0 * u), (-3.0 * u, top - 11.8 * u), (-0.6 * u, top - 10.6 * u),
                       (1.5 * u, top - 12.6 * u)], mix(hair, skin, 0.4), 0.6))
        for x in (-5.5, -2.5, 0.5, 3.4):
            o.append(ln([(x * u, top - 3.6 * u), (x * u + 1.0, top - 1.4 * u), (x * u + 2.3, top - 0.4 * u)], light(hair, 0.22), 0.26, 0.55))
    else:
        cap = [(6.8 * u, top - 3.5 * u), (3.2 * u, top - 5.0 * u), (0.8 * u, top - 8.8 * u), (-2.2 * u, top - 11.0 * u), (-3.6 * u, top - 15.6 * u), (-5.8 * u, top - 17.0 * u),
               (-9.8 * u, top - 15.4 * u), (-11.4 * u, top - 8.2 * u), (-8.4 * u, top - 1.0 * u), (0.5 * u, top + 1.1 * u), (5.4 * u, top - 1.0 * u)]
        o.append(part(cap, hair, depth=1.1))
        o.append(part([(-8.6 * u, top - 1.6 * u), (-10.8 * u, top - 0.6 * u), (-12.2 * u, top - 3.6 * u), (-10.0 * u, top - 5.2 * u)], P["accent"], depth=0.4))
        for y in (3.0, 5.6, 8.4):
            o.append(ln([(4.6 * u - y * 0.25, top - (y + 1.4) * u), (-2 * u, top - y * u * 0.75), (-8.6 * u, top - 3.0 * u)], light(hair, 0.25), 0.22, 0.5))
    ey = top - 12.2 * u
    ear = [(-2.3 * u, ey + 1.8 * u), (-0.5 * u, ey + 1.4 * u), (-0.1 * u, ey - 0.6 * u), (-0.9 * u, ey - 3.0 * u), (-2.4 * u, ey - 4.2 * u), (-3.4 * u, ey - 1.6 * u)]
    o.append(part(ear, skin, depth=0.5))
    o.append(ln([(-2.3 * u, ey + 0.8 * u), (-1.0 * u, ey + 0.5 * u), (-1.3 * u, ey - 1.6 * u), (-2.2 * u, ey - 2.6 * u)], sl, 0.18, 0.75))
    eye = [(5.3 * f * u, ey), (6.4 * f * u, ey + 0.72 * u), (7.5 * f * u, ey + 0.25 * u), (6.6 * f * u, ey - 0.5 * u)]
    c = uid()
    o.append(f'<clipPath id="{c}"><path d="{spline(eye)}"/></clipPath><path d="{spline(eye)}" fill="#F7F3EC"/><g clip-path="url(#{c})">')
    o.append(f'<ellipse cx="{6.95 * f * u:.2f}" cy="{ey + 0.08 * u:.2f}" rx="{0.5 * u:.2f}" ry="{0.82 * u:.2f}" fill="{P["iris"]}"/>')
    o.append(f'<ellipse cx="{7.05 * f * u:.2f}" cy="{ey + 0.08 * u:.2f}" rx="{0.24 * u:.2f}" ry="{0.4 * u:.2f}" fill="#120C0A"/></g>')
    o.append(ln([(5.2 * f * u, ey - 0.05 * u), (6.4 * f * u, ey + 0.8 * u), (7.7 * f * u, ey + 0.3 * u)], "#1B1210", 0.36))
    o.append(f'<path d="{spline(limb([(5.0 * f * u, ey + 2.4 * u), (6.6 * f * u, ey + 3.0 * u), (8.4 * f * u, ey + 2.5 * u)], [0.2 * u, 0.7 * u, 0.6 * u]))}" fill="{hair}"/>')
    o.append(ln([(9.3 * f * u, top - 17.0 * u), (8.6 * f * u, top - 16.7 * u), (8.3 * f * u, top - 17.5 * u)], sl, 0.2))
    lip = mix(skin, "#A8433D", 0.5 if P["female"] else 0.32)
    o.append(blob([(7.4 * f * u, top - 20.3 * u), (9.0 * f * u, top - 18.5 * u), (9.6 * f * u, top - 19.4 * u), (9.0 * f * u, top - 20.4 * u), (9.2 * f * u, top - 21.5 * u), (8.4 * f * u, top - 21.6 * u)], lip, 0.85))
    o.append(ln([(7.2 * f * u, top - 20.2 * u), (9.0 * f * u, top - 20.4 * u)], dark(lip, 0.5), 0.2))
    o.append(ln([(-1.6 * u, top - 18.6 * u), (2.6 * u, chin + 1.4 * u), (6.4 * f * u, chin + 0.3 * u)], sl, 0.16, 0.5))
    return "".join(o)


def hand_front(wr, direction, s, k, w, skin, thumb=True):
    dx, dy = direction
    nx, ny = -dy, dx
    sl = dark(skin, 0.5)
    o = []
    kn = (wr[0] + dx * 8.4 * k, wr[1] + dy * 8.4 * k)
    for i, L in enumerate((7.4, 8.7, 8.1, 6.3)):
        off = (i - 1.5) * 1.95 * k * (-s)
        base = (kn[0] + nx * off - dx * 1.0, kn[1] + ny * off - dy * 1.0)
        fan = (i - 1.5) * 0.06 * (-s)
        mid = (base[0] + (dx + nx * fan) * L * 0.55 * k, base[1] + (dy + ny * fan) * L * 0.55 * k)
        tip = (mid[0] + (dx + nx * fan * 0.2 - s * 0.10) * L * 0.45 * k, mid[1] + (dy + ny * fan) * L * 0.45 * k)
        o.append(part(limb([base, mid, tip], [2.0 * k, 1.85 * k, 1.45 * k]), skin, depth=0.4, sw=0.22))
    palm = limb([wr, along(wr, kn, 0.45), kn], [w, w + 2.2 * k, 8.3 * k])
    if thumb:
        t0 = (wr[0] + dx * 2.8 * k - s * 2.6 * k, wr[1] + dy * 2.8 * k)
        t1 = (t0[0] - s * 2.4 * k + dx * 3.4 * k, t0[1] + dy * 4.4 * k)
        t2 = (t1[0] - s * 0.2 * k + dx * 2.6 * k, t1[1] + dy * 3.6 * k)
        o.append(part(limb([t0, t1, t2], [3.2 * k, 2.4 * k, 1.6 * k]), skin, depth=0.4, sw=0.22))
    o.append(part(palm, skin, depth=0.6, sw=0.26))
    if not thumb:
        for i in range(4):
            off = (i - 1.5) * 1.95 * k
            o.append(circ(kn[0] + nx * off - dx * 0.4, kn[1] + ny * off - dy * 0.4, 0.55 * k, sl, 0.25))
    return "".join(o)


def shoe_front(P, s, ankle, back):
    o = []
    sh, sole, out, acc = P["shoe"], P["sole"], P["outsole"], P["accent"]
    if back:
        body = [(4.6, ankle + 2.0), (7.6, ankle + 3.0), (10.6, ankle + 2.0), (11.6, 3.4), (11.2, 1.6), (4.2, 1.6), (3.8, 3.4)]
    else:
        body = [(4.7, ankle + 1.6), (7.7, ankle + 2.8), (10.7, ankle + 1.6), (12.6, 4.0), (12.8, 1.6), (3.9, 1.6), (3.5, 4.0)]
    o.append(part(flip(body, s), sh, depth=0.8, line=dark(sh, 0.5)))
    x0, x1 = (3.6, 12.9) if not back else (3.7, 11.7)
    o.append(f'<path d="M{s * x0:.2f},2.3 L{s * x1:.2f},2.3 L{s * x1:.2f},0.75 L{s * x0:.2f},0.75 Z" fill="{sole}" stroke="{dark(sole, 0.45)}" stroke-width="0.2"/>')
    o.append(f'<path d="M{s * x0:.2f},0.8 L{s * x1:.2f},0.8 L{s * (x1 - 0.2):.2f},0.05 L{s * (x0 + 0.2):.2f},0.05 Z" fill="{out}"/>')
    if back:
        o.append(part(flip([(6.9, ankle + 2.8), (8.5, ankle + 2.8), (8.3, 2.8), (7.1, 2.8)], s), acc, depth=0.3, sw=0.2))
        o.append(ln(flip([(5.0, 5.2), (7.7, 4.4), (10.6, 5.2)], s), dark(sh, 0.35), 0.18))
    else:
        o.append(ln(flip([(5.4, 4.6), (8.0, 3.4), (11.4, 4.6)], s), dark(sh, 0.35), 0.2))
        for i in range(3):
            y = ankle + 0.8 - i * 1.25
            o.append(ln(flip([(6.3 - i * 0.2, y), (9.5 + i * 0.3, y)], s), dark(sh, 0.55), 0.26))
        o.append(part(flip([(7.0, ankle + 2.9), (8.6, ankle + 2.9), (8.5, ankle + 1.5), (7.1, ankle + 1.5)], s), acc, depth=0.2, sw=0.18))
    return "".join(o)


def shoe_side(P, ankle):
    sh, sole, out, acc = P["shoe"], P["sole"], P["outsole"], P["accent"]
    o = [part([(-5.8, ankle + 2.2), (-2.4, ankle + 2.6), (3.6, ankle + 1.9), (8.2, 6.3), (14.6, 4.9), (18.4, 3.4), (19.3, 2.2), (-6.6, 2.2), (-7.2, 5.0)], sh, depth=0.9, line=dark(sh, 0.5))]
    o.append(f'<path d="{spline([(-7.3, 2.6), (6, 2.4), (19.4, 2.5), (19.9, 1.5), (18.6, 0.75), (-6.9, 0.75), (-7.7, 1.6)])}" fill="{sole}" stroke="{dark(sole, 0.45)}" stroke-width="0.2"/>')
    o.append(f'<path d="{spline([(-6.9, 0.85), (5, 0.7), (18.6, 0.85), (18.2, 0.05), (-6.5, 0.05)])}" fill="{out}"/>')
    o.append(part([(-7.0, ankle + 1.6), (-5.2, ankle + 2.4), (-4.2, 5.4), (-4.8, 2.8), (-7.2, 2.9)], acc, depth=0.3, sw=0.2))
    o.append(ln([(12.6, 5.5), (14.4, 3.9), (18.9, 2.9)], dark(sh, 0.35), 0.2))
    o.append(ln([(-4.0, 6.0), (1.0, 3.6), (7.5, 2.9)], dark(sh, 0.35), 0.18))
    o.append(ln([(3.0, ankle + 1.6), (8.8, 6.0)], dark(sh, 0.4), 0.18))
    for i in range(4):
        x = 4.2 + i * 1.5
        y = ankle + 0.7 - i * 1.15
        o.append(ln([(x - 0.9, y - 0.5), (x + 0.9, y + 0.5)], dark(sh, 0.55), 0.28))
    return "".join(o)


def body_front(P, back=False, expr="neutral"):
    m = metrics(P)
    k, lk = m["k"], P["limb_k"]
    S, C, W, Hp = P["shoulder"], P["chest"], P["waist"], P["hip"]
    t0, t1, t2, t3, t4, t5 = P["thigh"]
    skin, top_c, bot = P["skin"], P["top"], P["bottom"]
    sl = dark(skin, 0.5)
    knee, calf, ankle, hip_y, crotch = m["knee"], m["calf"], m["ankle"], m["hip_y"], m["crotch"]
    mid = (crotch + knee) / 2
    o = ['<ellipse cx="0" cy="0.3" rx="22" ry="2.6" fill="#1A1410" opacity="0.28" filter="url(#ground)"/>']
    leg = [(Hp, hip_y), (t0, hip_y - 8 * k), (t1, mid + 3 * k), (t2, knee + 4.5 * k), (t3, knee), (t3 + 0.5, knee - 5 * k), (t4, calf), (t4 - 1.6, calf - 9 * k), (t5 + 0.3, ankle + 3 * k),
           (t5, ankle), (5.5, ankle), (5.3, ankle + 3 * k), (5.5, calf - 10 * k), (4.0, calf - 1 * k), (4.6, knee - 5 * k), (5.2, knee), (4.4, knee + 5 * k), (2.4, mid + 5 * k), (0.9, crotch)]
    for s in (1, -1):
        o.append(part(flip(leg, s), skin, depth=1.5, ao=[(s * 9, mid + 13 * k, 9, 4, 0.5)]))
        if not back:
            o.append(ln(flip([(t3 - 1.2, knee + 3.2 * k), (t3 - 3.4, knee + 1.0 * k), (t3 - 6.2, knee + 2.6 * k)], s), sl, 0.2, 0.6))
            o.append(ln(flip([(t3 - 2.2, knee - 2.6 * k), (t3 - 4.0, knee - 3.4 * k), (t3 - 5.6, knee - 2.4 * k)], s), sl, 0.16, 0.45))
            o.append(ln(flip([(t4 - 4.6, calf + 6 * k), (t4 - 5.0, calf - 6 * k), (t5 - 1.6, ankle + 8 * k)], s), sl, 0.14, 0.3))
        else:
            o.append(ln(flip([(t3 - 1.6, knee + 0.6 * k), (t3 - 4.0, knee - 0.4 * k), (t3 - 6.6, knee + 0.6 * k)], s), sl, 0.2, 0.55))
            o.append(ln(flip([(8.6, calf + 7 * k), (8.4, calf - 3 * k), (7.6, calf - 10 * k)], s), sl, 0.16, 0.45))
            o.append(ln(flip([(7.4, ankle + 9 * k), (7.3, ankle + 2 * k)], s), sl, 0.2, 0.5))
    for s in (1, -1):
        if not P["female"]:
            o.append(part(flip([(5.2, ankle + 4.6 * k), (t5 + 0.5, ankle + 4.6 * k), (t5 + 0.3, ankle - 1.4), (5.4, ankle - 1.4)], s), P["sock"], depth=0.5, sw=0.22))
            o.append(ln(flip([(5.4, ankle + 3.4 * k), (t5 + 0.3, ankle + 3.4 * k)], s), dark(P["sock"], 0.3), 0.16))
        o.append(shoe_front(P, s, ankle, back))
    wy = m["waist_y"] - 5.5 * k
    if P["bottom_style"] == "shorts":
        hem = mid + 4 * k
        r = [(W + 0.5, wy), (Hp + 1.0, hip_y), (t0 + 1.5, hip_y - 8 * k), (t1 + 1.8, hem + 0.2), (2.0, hem + 0.9), (1.2, hem + 6 * k), (0, crotch - 0.6)]
        o.append(part(r + mirror(r)[::-1][1:], bot, depth=1.5, ao=[(0, wy - 0.5, W + 3, 2.4, 0.5)]))
        for s in (1, -1):
            o.append(blob(flip([(W + 0.2, wy - 2), (Hp + 0.7, hip_y), (t0 + 1.2, hip_y - 8 * k), (t1 + 1.6, hem + 0.8), (t1 - 1.2, hem + 1.0), (Hp - 2.6, hip_y), (W - 2.2, wy - 2)], s), P["panel"], 0.9))
            o.append(ln(flip([(t1 + 1.6, hem + 1.3), (2.2, hem + 2.1)], s), light(bot, 0.22), 0.18))
            o.append(ln(flip([(2.2, crotch - 3), (5.0, crotch - 1.2), (8.0, crotch - 2.0)], s), dark(bot, 0.4), 0.2, 0.7))
            if not back:
                o.append(ln(flip([(0.8, wy - 2.4), (1.5, wy - 6.5), (1.1, wy - 9.5)], s), light(bot, 0.5), 0.26))
        o.append(ln([(-(W + 0.3), wy - 2.2), (0, wy - 2.7), (W + 0.3, wy - 2.2)], light(bot, 0.25), 0.2))
    else:
        hem = ankle + 8.5 * k
        r = [(W + 0.3, wy + 3 * k), (Hp + 0.5, hip_y), (t0 + 0.4, hip_y - 8 * k), (t1 + 0.3, mid + 3 * k), (t2 + 0.3, knee + 4.5 * k), (t3 + 0.3, knee), (t3 + 0.8, knee - 5 * k), (t4 + 0.3, calf),
             (t4 - 1.3, calf - 9 * k), (t5 + 1.0, hem), (5.0, hem), (5.3, calf - 10 * k), (3.8, calf - 1 * k), (4.4, knee - 5 * k), (5.0, knee), (4.2, knee + 5 * k), (2.2, mid + 5 * k), (0.7, crotch + 0.6), (0, crotch - 0.4)]
        o.append(part(r + mirror(r)[::-1][1:], bot, depth=1.5, ao=[(0, wy + 2, W + 3, 2.4, 0.45)]))
        for s in (1, -1):
            o.append(ln(flip([(Hp + 0.1, hip_y - 2), (t1 - 0.4, mid), (t3 - 0.4, knee), (t4 - 0.6, calf), (t5 + 0.4, hem + 1)], s), light(bot, 0.3), 0.2, 0.8))
            o.append(ln(flip([(t3 - 1.6, knee + 3.0 * k), (t3 - 3.6, knee + 1.2 * k), (t3 - 6.0, knee + 2.6 * k)], s), dark(bot, 0.45), 0.2, 0.8))
            o.append(ln(flip([(5.2, hem + 0.7), (t5 + 0.9, hem + 0.7)], s), light(bot, 0.25), 0.16))
        o.append(ln([(-(W + 0.6), wy - 2.0 * k), (0, wy - 3.0 * k), (W + 0.6, wy - 2.0 * k)], light(bot, 0.25), 0.2))
    if back:
        o.append(ln([(0, wy - 3.5), (0, crotch + 1)], dark(bot, 0.4), 0.2, 0.8))
        for s in (1, -1):
            o.append(ln(flip([(2.0, crotch + 2.4), (7.0, crotch + 0.4), (12.5, crotch + 3.0)], s), dark(bot, 0.4), 0.2, 0.6))
    ang = math.radians(17)
    sh_y = m["shoulder_y"]
    ul, fl = 29.0 * k, 25.0 * k
    for s in (1, -1):
        sh = (s * (S - 3.4 * lk), sh_y - 3.4 * lk)
        el = (sh[0] + s * ul * math.sin(ang), sh[1] - ul * math.cos(ang))
        wr = (el[0] + s * fl * math.sin(ang * 0.75), el[1] - fl * math.cos(ang * 0.75))
        centres = [sh, along(sh, el, 0.2), along(sh, el, 0.52), along(sh, el, 0.86), el, along(el, wr, 0.22), along(el, wr, 0.62), wr]
        widths = [w * lk for w in (10.2, 11.4, 10.2, 8.6, 8.3, 9.4, 7.4, 5.9)]
        hd = (math.sin(ang * 0.5) * s, -math.cos(ang * 0.5))
        o.append(hand_front(wr, hd, s, k * (0.92 if P["female"] else 1.0), widths[-1], skin, thumb=not back))
        o.append(part(limb(centres, widths), skin, depth=1.3, ao=[(sh[0], sh[1] - 9 * k, 7, 3.2, 0.5)] if P["top_style"] == "tee" else []))
        e1 = along(el, wr, 0.06)
        o.append(ln([(e1[0] - s * 3.2 * lk, e1[1] + 1.2), (e1[0] - s * 1.0, e1[1] + 0.2)], sl, 0.18, 0.5))
        if P["top_style"] == "tee":
            slv = limb([(sh[0] - s * 2.6, sh[1] + 0.8), along(sh, el, 0.16), along(sh, el, 0.48)], [8.8 * lk, 11.9 * lk, 11.5 * lk])
            o.append(part(slv, top_c, depth=1.2))
            h0 = along(sh, el, 0.44)
            o.append(ln([(h0[0] - s * 5.6, h0[1] + 1.4), (h0[0] + s * 5.6, h0[1] - 1.9)], dark(top_c, 0.35), 0.18))
    nb, nw = m["neck_base"], P["neck_w"]
    neck = [(-nw, m["chin"] + 4.5), (nw, m["chin"] + 4.5), (nw + 0.5, nb + 3.2), (nw + 3.4, nb + 0.2), (S * 0.7, nb - 1.4), (0, nb - 6.0), (-S * 0.7, nb - 1.4), (-nw - 3.4, nb + 0.2), (-nw - 0.5, nb + 3.2)]
    o.append(part(neck, skin, depth=1.2, ao=[(0, m["chin"] + 0.6, nw + 1.5, 3.0, 0.75)]))
    if not back:
        o.append(ln([(-1.6, nb + 1.3), (-0.6, nb + 0.2), (0.6, nb + 0.2), (1.6, nb + 1.3)], sl, 0.16, 0.5))
        for s in (1, -1):
            o.append(ln(flip([(nw - 0.6, m["chin"] + 3.0), (2.0, nb + 1.2)], s), sl, 0.14, 0.4))
    hem_y = wy - 3.0
    if P["top_style"] == "tee":
        r = [(nw + 1.6, nb + 2.2), (S * 0.66, nb + 0.2), (S - 1.4, sh_y - 1.0), (S - 0.2, sh_y - 6.0), (C + 0.4, m["armpit"]), (C + 0.2, m["chest_y"] - 3 * k), (C - 1.2, m["chest_y"] - 12 * k),
             (W + 1.0, m["waist_y"]), (W + 1.2, m["waist_y"] - 6 * k), (W + 1.6, hem_y)]
        dip = [] if back else [(-(nw - 0.2), nb - 0.9), (0, nb - 2.9), (nw - 0.2, nb - 0.9)]
        o.append(part(r + mirror(r)[::-1] + dip, top_c, depth=2.0))
        tl = dark(top_c, 0.38)
        if back:
            o.append(ln([(-(nw + 1.6), nb + 2.0), (0, nb + 1.0), (nw + 1.6, nb + 2.0)], tl, 0.42))
            o.append(ln([(0, nb - 2), (0, m["waist_y"] + 6)], tl, 0.16, 0.5))
            for s in (1, -1):
                o.append(ln(flip([(C * 0.28, m["armpit"] + 6), (C * 0.66, m["armpit"] + 2.5), (C * 0.6, m["chest_y"] - 4)], s), tl, 0.18, 0.55))
        else:
            o.append(ln([(-(nw + 1.9), nb + 1.3), (-(nw - 0.3), nb - 2.0), (0, nb - 4.0), (nw - 0.3, nb - 2.0), (nw + 1.9, nb + 1.3)], tl, 0.26, 0.85))
            for s in (1, -1):
                o.append(ln(flip([(C * 0.18, m["chest_y"] - 2.0 * k), (C * 0.5, m["chest_y"] - 3.6 * k), (C * 0.82, m["chest_y"] - 1.4 * k)], s), tl, 0.2, 0.45))
                o.append(ln(flip([(nw + 2.2, nb + 1.6), (C * 0.86, m["armpit"] + 1.0)], s), tl, 0.16, 0.5))
        for s in (1, -1):
            o.append(ln(flip([(C - 0.8, m["armpit"] - 1.5), (C - 3.6, m["armpit"] - 4.0)], s), tl, 0.2, 0.6))
            o.append(ln(flip([(W + 0.6, m["waist_y"] + 2), (W - 2.6, m["waist_y"] + 0.4), (W - 5.0, m["waist_y"] + 1.4)], s), tl, 0.2, 0.5))
        o.append(ln([(-(W + 1.3), hem_y + 1.3), (0, hem_y + 0.9), (W + 1.3, hem_y + 1.3)], tl, 0.16, 0.7))
    else:
        sk = [(nw + 1.0, nb + 2.6), (S * 0.66, nb + 0.2), (S - 1.2, sh_y - 1.0), (S - 0.4, sh_y - 6), (C + 0.2, m["armpit"] + 1.5), (C - 1.0, m["armpit"] - 7)]
        o.append(part(sk + mirror(sk)[::-1], skin, depth=1.6, line=dark(skin, 0.16), sw=0.18))
        if not back:
            o.append(ln([(-S * 0.62, nb - 0.6), (-S * 0.3, nb - 1.5), (-1.4, nb - 0.6)], sl, 0.16, 0.45))
            o.append(ln([(S * 0.62, nb - 0.6), (S * 0.3, nb - 1.5), (1.4, nb - 0.6)], sl, 0.16, 0.45))
        st = nw + 3.4
        dip = nb - (3.5 if back else 8.5)
        inner = (4.2, m["armpit"] + 7 * k) if back else (C - 3.4, m["armpit"] + 5 * k)
        inner2 = (5.5, m["armpit"] + 1.0) if back else (C - 0.6, m["armpit"] - 1.0)
        r = [(st - 1.9, nb + 1.6), (st + 0.4, nb + 1.2), inner, inner2, (C + 0.1, m["armpit"] - 3.0), (C - 0.8, m["chest_y"] - 10 * k), (W + 0.6, m["waist_y"]),
             (W + 0.9, m["waist_y"] - 4 * k), (W + 1.0, hem_y + 3)]
        full = r + mirror(r)[::-1] + [(-(st - 2.0), nb + 1.6), (-(st - 3.2), nb - 2.5), (0, dip), (st - 3.2, nb - 2.5)]
        o.append(part(full, top_c, depth=1.8))
        tl = dark(top_c, 0.38)
        o.append(ln([(-(st - 2.0), nb + 1.6), (-(st - 3.2), nb - 2.5), (0, dip - 0.9), (st - 3.2, nb - 2.5), (st - 2.0, nb + 1.6)], tl, 0.3, 0.8))
        if not back:
            for s in (1, -1):
                o.append(ln(flip([(C * 0.2, m["chest_y"] - 4.4 * k), (C * 0.5, m["chest_y"] - 5.6 * k), (C * 0.84, m["chest_y"] - 3.2 * k)], s), tl, 0.2, 0.5))
        else:
            o.append(ln([(0, dip - 1.5), (0, m["waist_y"] + 6)], tl, 0.16, 0.5))
        for s in (1, -1):
            o.append(ln(flip([(W + 0.3, m["waist_y"] + 2), (W - 2.4, m["waist_y"] + 0.5), (W - 4.6, m["waist_y"] + 1.3)], s), tl, 0.2, 0.5))
    o.append(head_front(P, back, expr))
    return "".join(o)


def body_side(P):
    m = metrics(P)
    k, lk = m["k"], P["limb_k"]
    skin, top_c, bot = P["skin"], P["top"], P["bottom"]
    sl = dark(skin, 0.5)
    knee, calf, ankle, hip_y, crotch = m["knee"], m["calf"], m["ankle"], m["hip_y"], m["crotch"]
    cd, bd, gl, bust = P["chest_depth"], P["back_depth"], P["glute"], P["bust"]
    q = P["thigh"][1] / 16.6
    mid = (crotch + knee) / 2
    o = ['<ellipse cx="5" cy="0.3" rx="17" ry="2.4" fill="#1A1410" opacity="0.28" filter="url(#ground)"/>']
    leg = [(cd * 0.8, hip_y), (10.2 * q, mid + 12 * k), (9.6 * q, mid), (7.6, knee + 5 * k), (7.0, knee), (5.8, knee - 5 * k), (5.4, calf), (4.4, calf - 12 * k), (3.6, ankle + 3 * k), (3.8, ankle),
           (-4.6, ankle), (-4.3, ankle + 4 * k), (-6.4 * q, calf - 9 * k), (-8.9 * q, calf + 1 * k), (-7.2 * q, knee - 4 * k), (-5.6, knee + 1 * k), (-7.6 * q, mid - 2 * k), (-10.4 * q, mid + 10 * k),
           (-gl, hip_y - 3 * k), (-gl * 0.86, hip_y + 6 * k)]
    o.append(part(leg, skin, depth=1.5, ao=[(0, mid + 13 * k, 11, 4, 0.5)]))
    o.append(ln([(6.6, knee + 2.6 * k), (5.2, knee + 0.4 * k), (5.8, knee - 2.4 * k)], sl, 0.18, 0.5))
    if not P["female"]:
        o.append(part([(-4.5, ankle + 4.6 * k), (3.7, ankle + 4.6 * k), (3.9, ankle - 1.6), (-4.8, ankle - 1.6)], P["sock"], depth=0.5, sw=0.22))
    o.append(shoe_side(P, ankle))
    wy = m["waist_y"] - 5.5 * k
    wf, wb = cd * 0.76 - bust * 0.5, bd * 0.62
    if P["bottom_style"] == "shorts":
        hem = mid + 4 * k
        b = [(wf, wy), (cd * 0.84 + 0.6, hip_y), (9.9 * q + 1.9, hem + 0.3), (-9.6 * q - 0.9, hem - 0.6), (-10.6 * q - 0.8, mid + 11 * k), (-gl - 0.9, hip_y - 3 * k), (-gl * 0.88, hip_y + 6 * k), (-wb, wy)]
        o.append(part(b, bot, depth=1.5, ao=[(0, wy - 0.5, 11, 2.2, 0.5)]))
        o.append(blob([(-1.8, wy - 2.2), (2.0, wy - 2.2), (3.0, hip_y), (3.4, hem + 0.6), (-2.6, hem + 0.2), (-2.4, hip_y)], P["panel"], 0.9))
        o.append(ln([(9.6 * q + 1.6, hem + 1.2), (-9.4 * q - 0.6, hem + 0.3)], light(bot, 0.22), 0.18))
    else:
        hem = ankle + 8.5 * k
        b = [(wf, wy + 3 * k), (cd * 0.8 + 0.3, hip_y), (10.2 * q + 0.3, mid + 12 * k), (9.6 * q + 0.3, mid), (7.9, knee + 5 * k), (7.3, knee), (6.1, knee - 5 * k), (5.7, calf), (4.7, calf - 12 * k), (4.0, hem),
             (-4.7, hem), (-6.6 * q, calf - 9 * k), (-9.1 * q, calf + 1 * k), (-7.4 * q, knee - 4 * k), (-5.9, knee + 1 * k), (-7.8 * q, mid - 2 * k), (-10.6 * q, mid + 10 * k), (-gl - 0.3, hip_y - 3 * k),
             (-gl * 0.88, hip_y + 6 * k), (-wb, wy + 3 * k)]
        o.append(part(b, bot, depth=1.5, ao=[(0, wy + 2, 11, 2.2, 0.45)]))
        o.append(ln([(0.4, wy), (0.2, mid), (0.6, knee), (-0.6, calf), (-0.4, hem + 1)], light(bot, 0.3), 0.2, 0.8))
        o.append(ln([(-wb - 0.2, wy - 2.0 * k), (wf + 0.2, wy - 2.2 * k)], light(bot, 0.25), 0.2))
        o.append(ln([(6.4, knee + 2.8 * k), (4.8, knee + 0.6 * k), (5.6, knee - 2.2 * k)], dark(bot, 0.45), 0.2, 0.8))
    nb = m["neck_base"]
    o.append(part([(-6.6, m["chin"] + 8.0), (2.8, m["chin"] + 2.0), (3.4, nb + 2.4), (4.4, nb - 0.6), (-8.0, nb + 0.6), (-6.6, nb + 4.0)], skin, depth=1.2, ao=[(2.0, m["chin"] + 0.5, 5, 2.4, 0.7)]))
    hem_y = wy - 3.0
    if P["top_style"] == "tank":
        o.append(part([(4.0, nb + 0.6), (cd * 0.66, nb - 5 * k), (cd * 0.8, m["armpit"] + 3), (-bd * 0.85, m["armpit"] + 4), (-bd * 0.94, nb - 4 * k), (-7.4, nb + 1.4)], skin, depth=1.4))
        torso = [(4.2, nb - 2.2), (cd * 0.74, nb - 8 * k), (cd + bust, m["chest_y"] - 2.5 * k), (cd * 0.84 + bust * 0.2, m["chest_y"] - 11 * k), (wf + 0.6, m["waist_y"]), (wf + 0.9, hem_y + 3),
                 (-wb - 0.8, hem_y + 3), (-wb - 0.3, m["waist_y"] + 2), (-bd * 0.98, m["chest_y"] + 2 * k), (-bd * 0.9, m["armpit"] + 3), (-5.8, m["armpit"] + 9 * k), (-3.0, nb - 3.0), (0.8, nb + 0.4)]
    else:
        torso = [(4.2, nb + 1.4), (cd * 0.72, nb - 5 * k), (cd, m["chest_y"] - 1.5 * k), (cd * 0.86, m["chest_y"] - 11 * k), (wf + 0.8, m["waist_y"]), (wf + 1.2, hem_y),
                 (-wb - 1.0, hem_y), (-wb - 0.4, m["waist_y"] + 2), (-bd * 0.98, m["chest_y"] + 2 * k), (-bd, m["armpit"] + 4), (-bd * 0.9, nb - 3 * k), (-7.4, nb + 1.8)]
    o.append(part(torso, top_c, depth=1.9))
    tl = dark(top_c, 0.38)
    o.append(ln([(wf + 0.4, m["waist_y"] + 2.5), (wf - 3.5, m["waist_y"] + 0.6), (-2, m["waist_y"] + 1.6)], tl, 0.2, 0.5))
    if P["top_style"] == "tee":
        o.append(ln([(-wb - 0.8, hem_y + 1.3), (wf + 1.0, hem_y + 1.3)], tl, 0.16, 0.7))
        o.append(ln([(-7.2, nb + 1.6), (-1.5, nb + 0.2), (4.0, nb + 1.2)], tl, 0.4))
    sh = (-1.0, m["shoulder_y"] - 3.6 * lk)
    el = (-2.4, sh[1] - 28.6 * k)
    wr = (1.6, el[1] - 24.6 * k)
    centres = [sh, along(sh, el, 0.2), along(sh, el, 0.52), along(sh, el, 0.86), el, along(el, wr, 0.22), along(el, wr, 0.62), wr]
    widths = [w * lk for w in (10.6, 11.6, 10.6, 9.0, 8.4, 9.2, 7.2, 5.6)]
    hk = k * (0.92 if P["female"] else 1.0)
    kn = (wr[0] + 1.8, wr[1] - 9.4 * hk)
    f1 = (kn[0] + 1.9, kn[1] - 4.4 * hk)
    f2 = (f1[0] - 0.2, f1[1] - 3.4 * hk)
    o.append(part(limb([kn, f1, f2], [3.4 * hk, 2.8 * hk, 2.0 * hk]), skin, depth=0.4, sw=0.22))
    o.append(part(limb([wr, along(wr, kn, 0.5), kn], [widths[-1], widths[-1] + 1.2, 4.6 * hk]), skin, depth=0.5, sw=0.26))
    t1 = (wr[0] + 3.4, wr[1] - 5.6 * hk)
    o.append(part(limb([(wr[0] + 1.4, wr[1] - 1.8 * hk), t1, (t1[0] + 0.7, t1[1] - 3.2 * hk)], [3.0 * hk, 2.3 * hk, 1.6 * hk]), skin, depth=0.4, sw=0.22))
    o.append(part(limb(centres, widths), skin, depth=1.3, ao=[(sh[0], sh[1] - 9 * k, 7, 3.2, 0.5)] if P["top_style"] == "tee" else []))
    if P["top_style"] == "tee":
        o.append(part(limb([(sh[0], sh[1] + 2.6), along(sh, el, 0.16), along(sh, el, 0.48)], [9.6 * lk, 12.2 * lk, 11.8 * lk]), top_c, depth=1.2))
        h0 = along(sh, el, 0.44)
        o.append(ln([(h0[0] - 5.9, h0[1] + 0.3), (h0[0] + 5.9, h0[1] - 0.3)], tl, 0.18))
    o.append(head_side(P))
    return "".join(o)


INK, MUTE, PAPER, CARD, RULE = "#1C1A22", "#6E6A75", "#ECE8E1", "#F6F3EE", "#CFC9BF"


def figure(svg, cx, floor, s):
    return f'<g transform="translate({cx:.1f},{floor:.1f}) scale({s},-{s})">{svg}</g>'


def crop(svg, cx, floor, s, x, y, w, h, r=18):
    c = uid()
    return (f'<clipPath id="{c}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{CARD}"/>'
            f'<g clip-path="url(#{c})">{figure(svg, cx, floor, s)}</g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="{RULE}" stroke-width="2"/>')


def text(x, y, t, size=26, weight=600, fill=INK, family="Barlow Condensed", anchor="start", spacing=0):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}">{t}</text>'


def heading(x, y, t, accent):
    return text(x, y, t, 30, 700, spacing=3) + f'<rect x="{x}" y="{y + 10}" width="60" height="5" fill="{accent}"/>'


def build_sheet(P):
    Wd, Ht = 1800, 2560
    s, floor = 4.9, 1210
    m = metrics(P)
    front, side, back = body_front(P), body_side(P), body_front(P, back=True)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{Ht}" viewBox="0 0 {Wd} {Ht}">', DEFS, f'<rect width="{Wd}" height="{Ht}" fill="{PAPER}"/>',
         f'<rect x="60" y="56" width="14" height="92" fill="{P["accent"]}"/>', text(96, 112, P["title"], 84, 700, spacing=1),
         text(96, 150, f'MOTIONFORGE · {P["role"]}'.upper(), 25, 600, MUTE, spacing=3), text(Wd - 60, 96, "CHARACTER MODEL SHEET", 34, 700, anchor="end", spacing=3),
         text(Wd - 60, 132, "Rev. 2 · for approval before 3D modelling", 23, 500, MUTE, "Barlow", anchor="end"),
         text(96, 196, P["tagline"], 25, 400, INK, "Barlow"), f'<line x1="60" y1="222" x2="{Wd - 60}" y2="222" stroke="{INK}" stroke-width="3"/>']
    n = int(P["height"] // P["head"])
    for i in range(0, n + 1):
        y = floor - (P["height"] - i * P["head"]) * s
        o.append(f'<line x1="60" y1="{y:.1f}" x2="{Wd - 60}" y2="{y:.1f}" stroke="{RULE}" stroke-width="1.5" stroke-dasharray="3 9"/>')
        o.append(text(60, y - 7, f"{i}", 19, 600, MUTE))
    o.append(f'<line x1="60" y1="{floor}" x2="{Wd - 60}" y2="{floor}" stroke="{INK}" stroke-width="2.5"/>')
    xs = (480, 1010, 1440)
    for cx, label, svg in zip(xs, ("FRONT", "SIDE", "BACK"), (front, side, back)):
        o.append(figure(svg, cx, floor, s))
        o.append(text(cx, floor + 44, label, 27, 600, MUTE, anchor="middle", spacing=5))
    hx = Wd - 74
    ty = floor - P["height"] * s
    o.append(f'<line x1="{hx}" y1="{ty}" x2="{hx}" y2="{floor}" stroke="{INK}" stroke-width="2"/><line x1="{hx - 9}" y1="{ty}" x2="{hx + 9}" y2="{ty}" stroke="{INK}" stroke-width="2"/>')
    o.append(f'<text transform="translate({hx - 12},{(ty + floor) / 2}) rotate(-90)" font-family="Barlow Condensed" font-size="23" font-weight="600" fill="{INK}" text-anchor="middle" letter-spacing="2">'
             f'{P["height"]} CM · {P["height"] / P["head"]:.1f} HEADS</text>')
    for label, (fx, fy), (dx, dy) in P["callouts"]:
        px, py = xs[0] + fx * s, floor - fy * s
        lx = xs[0] + dx
        ly = py + dy
        anchor = "end" if dx < 0 else "start"
        ex = lx + (8 if dx < 0 else -8)
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{INK}"/><path d="M{px:.1f},{py:.1f} L{ex:.1f},{ly:.1f}" stroke="{INK}" stroke-width="1.6" fill="none"/>')
        for j, line_ in enumerate(label.split("\n")):
            o.append(text(lx, ly + 7 + j * 25, line_, 21 if j == 0 else 19, 600 if j == 0 else 400, INK if j == 0 else MUTE, "Barlow", anchor=anchor))

    y0 = 1300
    o.append(heading(60, y0, "HEAD STUDIES", P["accent"]))
    hs = 15.0
    hy = y0 + 470 + (m["chin"] - 8.5) * hs
    o.append(crop(front, 280, hy, hs, 60, y0 + 34, 440, 470))
    o.append(crop(side, 715, hy, hs, 520, y0 + 34, 440, 470))
    o.append(text(280, y0 + 530, "FRONT", 18, 600, MUTE, anchor="middle", spacing=2) + text(740, y0 + 530, "PROFILE", 18, 600, MUTE, anchor="middle", spacing=2))
    es = 8.2
    for i, (ex_, name) in enumerate((("neutral", "NEUTRAL · DEFAULT"), ("smile", "ENCOURAGING"), ("focus", "FOCUSED · DEMO"))):
        x = 980 + i * 256
        ey = y0 + 262 + (m["chin"] - 5.5) * es
        o.append(crop(body_front(P, expr=ex_), x + 120, ey, es, x, y0 + 34, 240, 228, r=14))
        o.append(text(x + 120, y0 + 288, name, 18, 600, MUTE, anchor="middle", spacing=2))
    o.append(text(980, y0 + 340, "Face", 24, 700))
    for i, t_ in enumerate(["Modelled eyes with lids, brows, nose, lips and ears — not painted on.", "The three expressions above are built in as blend shapes.",
                            "Friendly, attentive default; never aggressive.", "No real person's likeness."]):
        o.append(text(980, y0 + 376 + i * 31, "—  " + t_, 21, 400, INK, "Barlow"))

    y1 = 1872
    o.append(heading(60, y1, "DETAIL STUDIES", P["accent"]))
    lab = y1 + 350
    ds = 11.5
    o.append(crop(side, 270 - 6 * ds, y1 + 276, ds, 60, y1 + 34, 420, 290))
    a17, a13 = math.radians(17), math.radians(12.75)
    wrx = (P["shoulder"] - 3.4 * P["limb_k"]) + 29 * m["k"] * math.sin(a17) + 25 * m["k"] * math.sin(a13)
    wry = m["shoulder_y"] - 3.4 * P["limb_k"] - 29 * m["k"] * math.cos(a17) - 25 * m["k"] * math.cos(a13)
    hs2 = 11.5
    o.append(crop(front, 640 - (wrx + 1.5) * hs2, y1 + 179 + (wry - 8.5) * hs2, hs2, 500, y1 + 34, 280, 290))
    gs = 8.6
    o.append(crop(front, 1010, y1 + 318 + (m["waist_y"] - 24 * m["k"]) * gs, gs, 800, y1 + 34, 420, 290))
    o.append(crop(back, 1490, y1 + 318 + (m["chin"] - 31 * m["k"]) * gs, gs, 1240, y1 + 34, 500, 290))
    for x, t_ in ((270, "TRAINER · SIDE"), (640, "HAND · RELAXED"), (1010, "GARMENT FIT · WAIST"), (1490, "BACK · SHOULDERS")):
        o.append(text(x, lab, t_, 18, 600, MUTE, anchor="middle", spacing=2))

    y2 = 2272
    o.append(heading(60, y2, "COLOUR", P["accent"]))
    for i, (name, key) in enumerate(P["palette"]):
        x = 60 + (i % 3) * 232
        y = y2 + 36 + (i // 3) * 112
        col = P[key]
        o.append(f'<rect x="{x}" y="{y}" width="214" height="62" rx="10" fill="{col}" stroke="{dark(col, 0.3)}" stroke-width="1.5"/>'
                 f'<path d="M{x + 152},{y} h52 a10,10 0 0 1 10,10 v42 a10,10 0 0 1 -10,10 h-52 Z" fill="{dark(col, 0.42)}" opacity="0.6"/>')
        o.append(text(x, y + 86, name, 20, 600, INK, "Barlow") + text(x + 214, y + 86, col.upper(), 18, 400, MUTE, "Barlow", anchor="end"))
    o.append(heading(800, y2, "3D BUILD NOTES", P["accent"]))
    notes = ["Built from scratch in Blender to this sheet — no base mesh, scan or template.", "Front and side views are orthographic on one head-unit grid, so they are traced 1:1.",
             "Hands: five articulated fingers; closes to a fist for the boxing guard.", "Clothing is separate geometry with real hems, collar and waistband.",
             "Trainers: upper, midsole, outsole, heel tab and laces as separate parts.", "Soft two-tone shading as drawn here; 25–35k triangles for mid-range phones.",
             "Same skeleton and clip names as the current trainer — no app changes."]
    for i, t_ in enumerate(notes):
        o.append(text(800, y2 + 44 + i * 30, "—  " + t_, 21, 400, INK, "Barlow"))
    o.append(text(Wd - 60, Ht - 22, "Original design for MOTIONFORGE · light from upper left · units: cm", 18, 500, MUTE, "Barlow", anchor="end"))
    o.append("</svg>")
    return "".join(o)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key, P in DESIGNS.items():
        _uid[0] = 0
        with open(os.path.join(OUT, f"trainer_{key}_art_sheet.svg"), "w") as fh:
            fh.write(build_sheet(P))
        print("wrote", key)
