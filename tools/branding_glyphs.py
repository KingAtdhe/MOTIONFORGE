import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
font = TTFont(sys.argv[1]); out = sys.argv[2]
def outline(text, wght, wdth, track=0.0):
    inst = instantiateVariableFont(TTFont(sys.argv[1]), {"wght": wght, "wdth": wdth})
    gs = inst.getGlyphSet(); cmap = inst.getBestCmap(); upm = inst["head"].unitsPerEm
    x = 0; cmds = []; bp = BoundsPen(gs)
    for ch in text:
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs); gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, 0))); cmds.append(pen.getCommands())
        gs[g].draw(TransformPen(bp, (1, 0, 0, 1, x, 0)))
        x += gs[g].width + track * upm
    return " ".join(cmds), bp.bounds, inst["OS/2"].sCapHeight
m, mb, cap = outline("M", 900, 125)
w, wb, wcap = outline("MOTIONFORGE", 800, 125, 0.03)
import json
json.dump({"m": m, "mb": mb, "cap": cap, "w": w, "wb": wb, "wcap": wcap}, open(out, "w"))
print(mb, cap, wb)
