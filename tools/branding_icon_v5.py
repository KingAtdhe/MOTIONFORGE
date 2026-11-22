"""MOTIONFORGE mark v5: a squat as a geometric chronophotograph — four exposures of one stick figure, the last in
timing yellow, on the black plate. Joint positions come from the coach's squat_down clip (side view).

Usage: python tools/branding_icon_v5.py <joints.json> <res_dir> <branding_dir>
(joints.json: list of {bone: [x, y, z]} per exposure, as written by the snippet in docs/BUILD_LOG.md 2026-11-22.)
"""
import json, sys
J = json.load(open(sys.argv[1])); RES = sys.argv[2]; BR = sys.argv[3]
CHAINS = [["Head", "Neck", "Spine2", "Hips"], ["Spine2", "LeftArm", "LeftForeArm", "LeftHand"], ["Hips", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"]]
pts = [{k: (-v[1], v[2]) for k, v in f.items()} for f in J]
xs = [p[0] for f in pts for p in f.values()]; ys = [p[1] for f in pts for p in f.values()]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
BOX = 46.0
s = BOX / max(maxx - minx, maxy - miny)
ox = 54 - (maxx - minx) * s / 2; oy = 56 + (maxy - miny) * s / 2
def P(p): return (ox + (p[0] - minx) * s, oy - (p[1] - miny) * s)
def paths(f, mono=False):
    out = []
    for ch in CHAINS:
        q = [P(f[n]) for n in ch if n != "Head"] if ch[0] == "Head" else [P(f[n]) for n in ch]
        out.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in q))
    return out
STY = [("#FFFFFF", 0.22), ("#FFFFFF", 0.38), ("#FFFFFF", 0.6), ("#FFD60A", 1.0)]
def head(f):
    hx, hy = P(f["Head"]); nx, ny = P(f["Neck"])
    dx, dy = hx - nx, hy - ny; n = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    return hx + dx / n * 4.6, hy + dy / n * 4.6
def vector(mono=False, anim=False):
    body = []
    for i, f in enumerate(pts):
        col, a = STY[i]
        if mono: col, a = "#000000", [0.3, 0.5, 0.7, 1.0][i]
        alpha = f"{int(a * 255):02X}"
        c = "#" + alpha + col[1:]
        hx, hy = head(f)
        grp = []
        for d in paths(f):
            grp.append(f'<path android:pathData="{d}" android:strokeColor="{c}" android:strokeWidth="{3.4 if i == 3 else 2.6}" android:strokeLineCap="round" android:strokeLineJoin="round" android:fillColor="#00000000" />')
        grp.append(f'<path android:pathData="M{hx - 3.4:.2f},{hy:.2f}a3.4,3.4 0 1,0 6.8,0a3.4,3.4 0 1,0 -6.8,0z" android:fillColor="{c}" />')
        name = f' android:name="e{i}"' if anim else ""
        body.append(f'<group{name}>' + "".join(grp) + "</group>")
    return "\n        ".join(body)
HDR = '<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">'
open(f"{RES}/drawable/ic_launcher_foreground.xml", "w").write('<?xml version="1.0" encoding="utf-8"?>\n<!-- MOTIONFORGE mark v5: a squat as a motion study, four exposures, the last in timing yellow (tools/branding_icon_v5.py) -->\n' + HDR + "\n        " + vector() + "\n</vector>\n")
open(f"{RES}/drawable/ic_launcher_monochrome.xml", "w").write('<?xml version="1.0" encoding="utf-8"?>\n' + HDR + "\n        " + vector(mono=True) + "\n</vector>\n")
open(f"{RES}/drawable/ic_launcher_background.xml", "w").write('<?xml version="1.0" encoding="utf-8"?>\n' + HDR + '\n    <path android:pathData="M0,0h108v108h-108z" android:fillColor="#FF000000" />\n</vector>\n')
# launch: the exposures land one after another (about 0.6 s)
targets = "".join(
    f'''
    <target android:name="e{i}">
        <aapt:attr name="android:animation">
            <objectAnimator android:propertyName="alpha" android:valueFrom="0" android:valueTo="1" android:startOffset="{60 + i * 120}" android:duration="140" />
        </aapt:attr>
    </target>''' for i in range(4))
v = vector(anim=True).replace("<group ", '<group android:alpha="0" ')
open(f"{RES}/drawable/splash_icon_animated.xml", "w").write(
    '<?xml version="1.0" encoding="utf-8"?>\n<!-- Launch icon (Android 12+): the four exposures land in turn, like a chronophotograph being taken. -->\n'
    '<animated-vector xmlns:android="http://schemas.android.com/apk/res/android" xmlns:aapt="http://schemas.android.com/aapt">\n'
    '    <aapt:attr name="android:drawable">\n        ' + HDR + "\n        " + v + "\n        </vector>\n    </aapt:attr>" + targets + "\n</animated-vector>\n")
# svg preview for the brand folder
def svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108"><rect width="108" height="108" fill="#000"/>']
    for i, f in enumerate(pts):
        col, a = STY[i]
        for d in paths(f):
            o.append(f'<path d="{d}" stroke="{col}" stroke-opacity="{a}" stroke-width="{3.4 if i == 3 else 2.6}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
        hx, hy = head(f); o.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="3.4" fill="{col}" fill-opacity="{a}"/>')
    return "".join(o) + "</svg>"
open(f"{BR}/icon.svg", "w").write(svg())
import cairosvg
cairosvg.svg2png(bytestring=svg().encode(), write_to=f"{BR}/icon_512.png", output_width=512, output_height=512)
print("icon v5 written")
