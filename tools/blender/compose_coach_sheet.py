"""Lays the Cycles renders from build_coach.py --previews out as a concept-art presentation sheet."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
P = os.path.join(ROOT, "assets/blender/previews")
F = os.path.join(ROOT, "app/src/main/res/font")
BG, INK, RED = (214, 215, 222), (24, 25, 30), (224, 38, 58)


def font(size, bold=True):
    return ImageFont.truetype(os.path.join(F, "barlow_condensed_bold.ttf" if bold else "barlow_semibold.ttf"), size)


def load(name, w=None, h=None):
    im = Image.open(os.path.join(P, name + ".png")).convert("RGB")
    if w and h:
        s = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        l, t = (im.width - w) // 2, (im.height - h) // 2
        im = im.crop((l, t, l + w, t + h))
    elif h:
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    return im


W, H = 3200, 2000
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)


def tag(x, y, text, size=46):
    f = font(size)
    w = d.textlength(text, font=f) + 70
    d.polygon([(x + 18, y), (x + w, y), (x + w - 18, y + size + 22), (x, y + size + 22)], fill=INK)
    d.text((x + 34, y + 6), text, font=f, fill=(245, 245, 247))


# hero
hero = load("hero", 1000, H)
sheet.paste(hero, (0, 0))
d.polygon([(0, 0), (640, 0), (500, 330), (0, 330)], fill=INK)
d.polygon([(0, 330), (500, 330), (488, 356), (0, 356)], fill=RED)
d.text((44, 30), "MOTIONFORGE", font=font(92), fill=(245, 245, 247))
d.text((44, 122), "COACH", font=font(128), fill=RED)
d.text((48, 268), "TRAIN  •  IMPROVE  •  BE STRONGER", font=font(34, False), fill=(235, 235, 240))

# turnaround
x0 = 1040
for i, (n, lab) in enumerate((("turn_front", "FRONT"), ("turn_side", "SIDE"), ("turn_back", "BACK"))):
    im = load(n, h=1040)
    x = x0 + 130 + i * 330
    sheet.paste(im.crop((70, 0, im.width - 70, im.height)), (x, 40))
    d.text((x + (im.width - 140) / 2, 1100), lab, font=font(40), fill=INK, anchor="mm")
d.line([(x0 + 70, 80), (x0 + 70, 1030)], fill=INK, width=4)
d.line([(x0 + 52, 80), (x0 + 88, 80)], fill=INK, width=4)
d.line([(x0 + 52, 1030), (x0 + 88, 1030)], fill=INK, width=4)
d.text((x0 + 6, 520), "170", font=font(44), fill=INK)
d.text((x0 + 10, 566), "cm", font=font(34, False), fill=INK)

# poses
tag(2170, 40, "WORKOUT POSES")
for i, n in enumerate(("pose_squat", "pose_jab", "pose_cross", "pose_step")):
    im = load(n, 480, 480)
    sheet.paste(im, (2170 + (i % 2) * 500, 130 + (i // 2) * 500))

# details
tag(1040, 1160, "DETAILS")
for i, n in enumerate(("det_face", "det_core", "det_glove", "det_shoe")):
    im = load(n, 480, 480)
    sheet.paste(im, (1040 + i * 500, 1250))
    d.rectangle([1040 + i * 500, 1250, 1040 + i * 500 + 479, 1729], outline=(120, 122, 130), width=3)

# palette + notes
tag(1040, 1770, "COLOUR PALETTE", 38)
for i, c in enumerate(((27, 28, 33), RED, (197, 133, 86), (59, 36, 24), (236, 234, 230), (43, 79, 168))):
    d.rectangle([1420 + i * 120, 1772, 1420 + i * 120 + 100, 1832], fill=c, outline=(90, 92, 100), width=2)
d.text((1040, 1870), "3D concept render · modelled from scratch in Blender, lit and rendered in Cycles · this is the in-app model", font=font(30, False), fill=(70, 72, 80))
d.text((1040, 1912), "Draft for owner approval — no logo, no real person's likeness", font=font(30, False), fill=(70, 72, 80))
out = os.path.join(ROOT, "assets/blender/references/coach_f_3d_concept_sheet.jpg")
sheet.save(out, quality=90)
print("wrote", out)
