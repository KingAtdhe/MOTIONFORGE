# MOTIONFORGE mark v4: Archivo "M" (wdth 125 / wght 900) + chalk-blue square. Needs the outlines from
# tools/branding_glyphs.py (python tools/branding_glyphs.py app/src/main/res/font/archivo.ttf /tmp/icon4/glyphs.json).
import json, sys, cairosvg
from PIL import Image, ImageDraw
G = json.load(open('/tmp/icon4/glyphs.json'))
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/icon4'
x0, x1 = G["mb"][0], G["mb"][2]
S = 46.0 / (x1 - x0)
BASE = 69.35
TX = 26.9 - S * x0
SQ = (75.1, BASE - 6.0, 6.0)          # the blue square, sitting on the baseline like a full stop
def svg(bg=True, mono=False):
    s = '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">'
    if bg:
        s += '<rect width="108" height="108" fill="#000000"/>'
    fg = '#000' if mono else '#FFFFFF'
    s += f'<g transform="translate({TX:.3f} {BASE}) scale({S:.6f})"><path d="{G["m"]}" fill="{fg}"/></g>'
    s += f'<rect x="{SQ[0]}" y="{SQ[1]}" width="{SQ[2]}" height="{SQ[2]}" fill="{"#000" if mono else "#9CC4FF"}"/>'
    return s + '</svg>'
open(f'{OUT}/icon.svg', 'w').write(svg())
cairosvg.svg2png(bytestring=svg().encode(), write_to=f'{OUT}/icon_512.png', output_width=512, output_height=512)
big = Image.open(f'{OUT}/icon_512.png').convert('RGBA')
crop = big.crop((int(512*18/108),)*2 + (int(512*90/108),)*2).resize((192, 192))
Wd = Image.new('RGB', (192*3+40, 250), (232, 232, 230))
for i, shape in enumerate(['circle', 'squircle', 'square']):
    m = Image.new('L', (192, 192), 0); d = ImageDraw.Draw(m)
    if shape == 'circle': d.ellipse((0, 0, 191, 191), fill=255)
    elif shape == 'squircle': d.rounded_rectangle((0, 0, 191, 191), radius=60, fill=255)
    else: d.rounded_rectangle((0, 0, 191, 191), radius=18, fill=255)
    Wd.paste(crop, (10+i*202, 10), m)
mm = Image.new('L', (48, 48), 0); ImageDraw.Draw(mm).ellipse((0, 0, 47, 47), fill=255)
Wd.paste(crop.resize((48, 48)), (10, 206), mm); Wd.paste(crop.resize((32, 32)), (70, 214))
Wd.save('/tmp/icon4_preview.png')
print(f"S={S:.6f} TX={TX:.3f}")
