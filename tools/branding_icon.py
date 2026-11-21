# MOTIONFORGE sports app icon (run from the repo root: python tools/branding_icon.py assets/branding; needs cairosvg + Pillow).
# The Android vector drawables in app/src/main/res/drawable/ic_launcher_*.xml and splash_icon_animated.xml mirror
# this design on the same 108 x 108 adaptive-icon canvas.
import cairosvg, sys
from PIL import Image, ImageDraw
# 108 x 108 adaptive-icon canvas; safe zone = circle r 33 at (54,54)
FIG = {
  "head": (64.5, 29.0, 5.6),
  "strokes": [  # (points, width)
    ([(51.0,57.0),(42.0,66.5),(31.5,72.5)], 6.6),         # rear leg
    ([(53.0,56.0),(63.5,63.0),(66.0,76.0)], 6.6),         # lead leg
    ([(61.5,37.5),(52.0,56.0)], 9.5),                      # torso
    ([(58.0,41.5),(51.0,47.5),(57.5,36.5)], 4.8),         # rear arm: guard, fist at the chin
    ([(61.0,40.0),(70.5,40.5),(80.5,39.5)], 5.6),         # lead arm: straight punch
  ],
}
STREAKS = [((22,43),(37,43)), ((19,51),(34,51)), ((23,59),(36,59))]
def svg(mono=False, bg=True, size=108):
    fg = "#000" if mono else "#C8F542"; acc = "#000" if mono else "#FF7A45"
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 108 108">'
    if bg:
        s += ('<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1B2230"/><stop offset="1" stop-color="#07090D"/></linearGradient></defs>'
              '<rect width="108" height="108" fill="url(#g)"/>')
        # jersey stripes: two diagonal bands behind the athlete
        s += '<path d="M62,108 L108,62 L108,76 L76,108 Z" fill="#FF7A45" fill-opacity="0.22"/>'
        s += '<path d="M44,108 L108,44 L108,54 L54,108 Z" fill="#C8F542" fill-opacity="0.14"/>'
    s += '<g transform="translate(54 55) scale(0.86) translate(-54 -54)">'
    for (a,b) in STREAKS:
        s += f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{acc}" stroke-width="3.6" stroke-linecap="round"/>'
    edge = "#000" if mono else "#0E1218"
    for pts,w in FIG["strokes"]:
        d = "M" + " L".join(f"{x},{y}" for x,y in pts)
        if not mono:   # thin dark edge keeps overlapping limbs readable
            s += f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="{w+2.6}" stroke-linecap="round" stroke-linejoin="round"/>'
        s += f'<path d="{d}" fill="none" stroke="{fg}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
    hx,hy,hr = FIG["head"]
    s += f'<circle cx="{hx}" cy="{hy}" r="{hr}" fill="{fg}"/>'
    s += f'<circle cx="{80.5}" cy="{39.5}" r="4.4" fill="{acc}"/>'      # glove / impact point
    s += '</g>'
    return s + '</svg>'
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/icon"
open(f'{out}/icon.svg','w').write(svg())
cairosvg.svg2png(bytestring=svg().encode(), write_to=f'{out}/icon_512.png', output_width=512, output_height=512)
big = Image.open(f'{out}/icon_512.png').convert('RGBA')
crop = big.crop((int(512*18/108),)*2+(int(512*90/108),)*2).resize((192,192))
W = Image.new('RGB',(192*3+40,250),(240,242,245))
for i,shape in enumerate(['circle','squircle','square']):
    m = Image.new('L',(192,192),0); d=ImageDraw.Draw(m)
    if shape=='circle': d.ellipse((0,0,191,191),fill=255)
    elif shape=='squircle': d.rounded_rectangle((0,0,191,191),radius=60,fill=255)
    else: d.rounded_rectangle((0,0,191,191),radius=18,fill=255)
    W.paste(crop,(10+i*202,10),m)
mm = Image.new('L',(48,48),0); ImageDraw.Draw(mm).ellipse((0,0,47,47),fill=255)
W.paste(crop.resize((48,48)),(10,206),mm); W.paste(crop.resize((32,32)),(70,214))
W.save(f'/tmp/icon_preview.png')
