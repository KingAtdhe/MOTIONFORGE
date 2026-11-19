"""Side-by-side: the owner's sheet views (top) vs renders of the in-app model (bottom), plus poses."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
P = os.path.join(REPO, "assets/blender/previews")
font = lambda s: ImageFont.truetype(os.path.join(REPO, "app/src/main/res/font/barlow_condensed_bold.ttf"), s)
sheet = Image.open(os.path.join(REPO, "assets/blender/references/workout_coach_owner_sheet.png")).convert("RGB")
H = 760
crops = [sheet.crop(b) for b in ((445, 4, 610, 436), (606, 4, 705, 436), (705, 4, 852, 436))]


def fig(im):
    a = np.asarray(im).astype(int)
    bg = a[2, 2]
    ys, xs = np.nonzero(np.abs(a - bg).sum(2) > 40)
    return im.crop((xs.min() - 8, ys.min() - 8, xs.max() + 8, ys.max() + 8))


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def fig_sheet(c):
    a = np.asarray(c).astype(float) / 255
    mx, mn = a.max(2), a.min(2)
    m = ~((mx > 0.70) & ((mx - mn) / np.maximum(mx, 1e-6) < 0.14))
    m[:, :3] = m[:, -3:] = False
    ys, xs = np.nonzero(m)
    return c.crop((max(xs.min() - 4, 0), max(ys.min() - 4, 0), xs.max() + 4, ys.max() + 4))


top = [fit(fig_sheet(c), H) for c in crops]
bot = [fit(fig(Image.open(os.path.join(P, n + ".png")).convert("RGB")), H) for n in ("turn_front", "turn_side", "turn_back")]
poses = [fit(fig(Image.open(os.path.join(P, n + ".png")).convert("RGB")), 520) for n in ("pose_jab", "pose_cross", "pose_squat", "pose_step")]
W = 120 + max(sum(i.width + 60 for i in top), sum(i.width + 60 for i in bot)) + 60
W = max(W, 120 + sum(p.width + 40 for p in poses))
out = Image.new("RGB", (W, 120 + 2 * (H + 90) + 600), (222, 222, 230))
d = ImageDraw.Draw(out)
d.text((60, 30), "COACH v6 — YOUR SHEET (TOP) VS THE IN-APP 3D MODEL (BOTTOM)", font=font(52), fill=(24, 25, 30))
y = 120
for row, label in ((top, "SHEET"), (bot, "3D MODEL (sculpted relief, real lighting)")):
    x = 60
    d.text((x, y), label, font=font(36), fill=(200, 30, 50))
    for im in row:
        out.paste(im, (x, y + 50)); x += im.width + 60
    y += H + 90
x = 60
d.text((x, y), "CLIPS: JAB · CROSS · SQUAT · FOOTWORK", font=font(36), fill=(200, 30, 50))
for p in poses:
    out.paste(p, (x, y + 50)); x += p.width + 40
out.save(os.path.join(REPO, "assets/blender/references/coach_f_v5_vs_sheet.jpg"), quality=88)
print("ok", out.size)
