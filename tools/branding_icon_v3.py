# MOTIONFORGE app icon v3 (premium monogram). Run from the repo root: python tools/branding_icon.py assets/branding
# (needs cairosvg + Pillow). The Android drawables ic_launcher_*.xml / splash_*.xml mirror this design; the wordmark
# outlines come from tools/branding_wordmark.py (Manrope SemiBold via fontTools).
import cairosvg, sys
from PIL import Image, ImageDraw
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/icon3"
# geometric monoline M with a slight forward lean; ends cut flat on the baseline / cap line by a clip
def lean(x, y, k=0.16, base=72.0): return (round(x + k * (base - y), 2), y)
P = [lean(*p) for p in [(37.5, 76), (37.5, 36), (54, 58), (70.5, 36), (70.5, 76)]]
W = 6.6
def svg(mono=False, bg=True):
    s = '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108"><defs>'
    s += '<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F2DDAA"/><stop offset="0.55" stop-color="#D2AC66"/><stop offset="1" stop-color="#9C7638"/></linearGradient>'
    s += '<radialGradient id="bg" cx="0.5" cy="0.42" r="0.72"><stop offset="0" stop-color="#1E1E23"/><stop offset="1" stop-color="#09090B"/></radialGradient>'
    s += '<clipPath id="c"><rect x="0" y="35" width="108" height="37"/></clipPath></defs>'
    if bg:
        s += '<rect width="108" height="108" fill="url(#bg)"/>'
    if not mono:
        s += '<circle cx="54" cy="54" r="30.5" fill="none" stroke="url(#gold)" stroke-opacity="0.55" stroke-width="0.9"/>'
    d = "M" + " L".join(f"{x},{y}" for x, y in P)
    col = "#000" if mono else "url(#gold)"
    s += f'<g clip-path="url(#c)"><path d="{d}" fill="none" stroke="{col}" stroke-width="{W}" stroke-linejoin="miter" stroke-miterlimit="10"/></g>'
    return s + '</svg>'
open(f'{OUT}/icon.svg', 'w').write(svg())
cairosvg.svg2png(bytestring=svg().encode(), write_to=f'{OUT}/icon_512.png', output_width=512, output_height=512)
big = Image.open(f'{OUT}/icon_512.png').convert('RGBA')
crop = big.crop((int(512*18/108),)*2 + (int(512*90/108),)*2).resize((192, 192))
Wd = Image.new('RGB', (192*3+40, 250), (236, 236, 238))
for i, shape in enumerate(['circle', 'squircle', 'square']):
    m = Image.new('L', (192, 192), 0); d = ImageDraw.Draw(m)
    if shape == 'circle': d.ellipse((0, 0, 191, 191), fill=255)
    elif shape == 'squircle': d.rounded_rectangle((0, 0, 191, 191), radius=60, fill=255)
    else: d.rounded_rectangle((0, 0, 191, 191), radius=18, fill=255)
    Wd.paste(crop, (10+i*202, 10), m)
mm = Image.new('L', (48, 48), 0); ImageDraw.Draw(mm).ellipse((0, 0, 47, 47), fill=255)
Wd.paste(crop.resize((48, 48)), (10, 206), mm); Wd.paste(crop.resize((32, 32)), (70, 214))
Wd.save('/tmp/icon3_preview.png')
print(P)
