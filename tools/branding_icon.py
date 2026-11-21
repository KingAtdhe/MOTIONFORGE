# MOTIONFORGE app icon source (run from the repo root with cairosvg + Pillow). The Android vector drawables in
# app/src/main/res/drawable/ic_launcher_*.xml mirror this design (same 108 x 108 adaptive-icon canvas).
import cairosvg
# 108 x 108 adaptive-icon canvas; safe zone = circle r 33 at (54,54)
M = "M33,75 L42,33 L51,33 L55.5,51 L64,33 L73,33 L64,75 L55.5,75 L60.5,52 L53.5,66 L47.5,66 L44,52 L41.5,75 Z"
LINES = [(20,41,31,41),(16,50,28,50),(20,59,30,59)]
def svg(bg=True, mono=False, size=108):
    volt = "#000" if mono else "#C8F542"; ember = "#000" if mono else "#FF7A45"
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 108 108">'
    if bg:
        s += '<defs><radialGradient id="g" cx="0.5" cy="0.38" r="0.75"><stop offset="0" stop-color="#1D2530"/><stop offset="1" stop-color="#0B0E13"/></radialGradient></defs><rect width="108" height="108" fill="url(#g)"/>'
        s += '<circle cx="54" cy="54" r="31" fill="none" stroke="#C8F542" stroke-opacity="0.13" stroke-width="1.2"/>'
    s += '<g transform="translate(54 54) scale(0.8) translate(-50.5 -54)">'
    for x1,y,x2,_ in LINES:
        s += f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{ember}" stroke-width="4" stroke-linecap="round"/>'
    s += f'<path d="{M}" fill="{volt}"/>'
    s += '<circle cx="79" cy="30" r="4.2" fill="%s"/>' % ember
    s += '</g>'
    return s + '</svg>'
open('assets/branding/icon.svg','w').write(svg())
cairosvg.svg2png(bytestring=svg().encode(), write_to='assets/branding/icon_512.png', output_width=512, output_height=512)
# previews: square, circle mask, squircle, at launcher size
from PIL import Image, ImageDraw
big = Image.open('assets/branding/icon_512.png').convert('RGBA')
crop = big.crop((int(512*18/108),)*2+(int(512*90/108),)*2).resize((192,192))   # visible 72dp area
W = Image.new('RGB',(192*3+40,232),(240,242,245))
for i,shape in enumerate(['circle','squircle','square']):
    m = Image.new('L',(192,192),0); d=ImageDraw.Draw(m)
    if shape=='circle': d.ellipse((0,0,191,191),fill=255)
    elif shape=='squircle': d.rounded_rectangle((0,0,191,191),radius=60,fill=255)
    else: d.rounded_rectangle((0,0,191,191),radius=18,fill=255)
    W.paste(crop,(10+i*202,10),m)
small = crop.resize((48,48)); W.paste(small,(10,206)); W.paste(crop.resize((32,32)),(70,212))
W.save('/tmp/icon_preview.png')
