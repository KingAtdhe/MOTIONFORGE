import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
font = TTFont(sys.argv[1])
inst = instantiateVariableFont(font, {"wght": 600})
gs = inst.getGlyphSet(); cmap = inst.getBestCmap(); upm = inst["head"].unitsPerEm
text = "MOTIONFORGE"; track = 0.34 * upm
x = 0; paths = []
for ch in text:
    g = cmap[ord(ch)]
    pen = SVGPathPen(gs)
    tp = TransformPen(pen, (1, 0, 0, -1, x, 0))      # flip y (font units: y up)
    gs[g].draw(tp)
    paths.append(pen.getCommands())
    x += gs[g].width + track
width = x - track
cap = inst["OS/2"].sCapHeight
# fit into a 200 x 80 viewport: text height 16 units -> scale, centred
VW, VH = 200.0, 80.0
s = min(15.0 / cap, 172.0 / width)
tx = (VW - width * s) / 2; ty = VH / 2 + cap * s / 2
d = " ".join(paths)
print(f"{s:.6f} {tx:.3f} {ty:.3f}")
open("assets/branding/wordmark_path.txt", "w").write(d)
open("assets/branding/wordmark.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="320" viewBox="0 0 200 80"><rect width="200" height="80" fill="#0B0B0D"/><g transform="translate({tx:.3f} {ty:.3f}) scale({s:.6f})"><path d="{d}" fill="#F3F1EC" fill-opacity="0.86"/></g></svg>')
